import json
from typing import Optional
import requests
from core.core_log import get_logger
import re
import pprint

log = get_logger(__name__)


# ----------------------------------------------------------------------------------------------------------------
# This module is responsible for interacting with Ecowitt weather stations and parsing their data.
# It supports the Ecowitt HTTP API interface and provides functions to retrieve and normalize data from
# Ecowitt devices. Currently tested with WS69 and WS3800 Dasbhboard. The unit in the mappings below define 
# the final expected unit of the value. If the unit in the Ecowitt response is different, it will be 
# converted to the expected unit.
# ----------------------------------------------------------------------------------------------------------------


# https://oss.ecowitt.net/uploads/20260114/HTTP%20API%20interface%20Protocol%20(Generic)-(V1.0.6-2026-1-14)%20.pdf
# As of 6th sep 2026, the API documentation for common list is incomplete. Its missing docuemntation for the field
# 0x06D. However, https://github.com/jantman/prometheus-ecowitt-exporter describes it as
# "10-minute average wind direction".
SUPPORTED_API_VERSION = "1.0.6"
COMMON_LIST_ID_MAPPING = {
    "0x02": {"name":"Outdoor Temperature", "unit":"C"},
    "0x03": {"name":"Dew point", "unit":"C"},
    "0x04": {"name":"Wind chill", "unit":"C"},
    "0x07": {"name":"Outdoor Humidity", "unit":"%"},
    "0x0B": {"name":"Wind Speed", "unit":"m/s"},
    "0x0C": {"name":"Gust Speed", "unit":"m/s"},
    "0x15": {"name":"Light", "unit":"lux"},
    "0x17": {"name":"UVI", "unit":"0-15 index"},
    "0x19": {"name":"Day max wind", "unit":"m/s"},
    "0x0A": {"name":"Wind Direction", "unit":"360°"},
    "3": {"name":"Feel like", "unit":"C"},
    "5": {"name":"Vapor Pressure Deficit", "unit":"kPa"},
    "0x6D":{"name":"10-minute average wind direction", "unit":"°"},
}

# Ecowitt documentation for WS3800 https://www.ecowitt.com/api/quickstart/product?id=298 (also contains HTTP API Interface docu for LAN)
# Not in Ecowitt documentation but homeseer states 0x7D as hourly rain https://plugins.homeseer.com/releasenotes?productid=464.
# For 0x7C, I found:
# - this comment in jantman's prometheus-ecowitt-exporter code https://github.com/jantman/prometheus-ecowitt-exporter/blob/main/main.py#L302:
#   "0x7C = hourly rain: it is the one live accumulation id with no counterpart in the gateway's
#   labeled get_rain_totals / get_piezo_rain endpoints (which expose only day/week/month/year),
#   leaving hourly as the sole fit."
# - Home Assistant ecowitt integration (https://community.home-assistant.io/t/ecowitt-wittboy-how-to-use-hourly-rain-rate-properly/595074)
#     last24hrain* is handled as a rolling measurement, while dailyrain*
#     is handled as TOTAL_INCREASING (a counter that periodically resets).
# ==> This leads to the following conclusion:
# 0x7C = rain during the previous 24 hours ("last 24h rain"). This is a rolling 24-hour window, so it may contain rain from
#        yesterday even after the daily rain counter has been reset.
# 0x10 = daily rain. This is the rain accumulated for the current Ecowitt "day" and resets according to the station/gateway's 
#        configured daily reset.
RAIN_ID_MAPPING = {
    "0x0D": {"name":"Rain Event", "unit":"mm"},
    "0x0E": {"name":"Rain Rate", "unit":"mm/h"},
    "0x0F": {"name":"Rain Gain", "unit":"mm"},
    "0x10": {"name":"Rain Day", "unit":"mm"},
    "0x11": {"name":"Rain Week", "unit":"mm"},
    "0x12": {"name":"Rain Month", "unit":"mm"},
    "0x13": {"name":"Rain Year", "unit":"mm"},
    "0x14": {"name":"Rain Totals", "unit":"mm"},
    "0x7C": {"name":"Rain Last 24 Hours", "unit":"mm"},
    "0x7D": {"name":"Rain Last Hour", "unit":"mm"},
}

WH25_ID_MAPPING = {
    "intemp": {"name":"Indoor Temperature", "unit":"C"},
    "inhumi": {"name":"Indoor Humidity", "unit":"%"},
    "abs": {"name":"Absolutely Barometric", "unit":"hpa"},
    "rel": {"name":"Relative Barometric", "unit":"hpa"},
}

# Found in ecowitt documentation but seem to be not published by WS3800 + WS69 in the current version.
ID_MAPPING = {
    "0x01": {"name":"Indoor Temperature", "unit":"C"},
    "0x05": {"name":"Heat index", "unit":"C"},
    "0x06": {"name":"Indoor Humidity", "unit":"%"},
    "0x08": {"name":"Absolutely Barometric", "unit":"hpa"},
    "0x09": {"name":"Relative Barometric", "unit":"hpa"},
    "0x16": {"name":"UV", "unit":"uW/m2}"},
    "0x18": {"name":"Date and time", "unit":"DateTime"},
}


class EcowittEntry:

    def __init__(self, id_:str, display_name:str, value:float, unit:str):
        # the id parsed from the ecowitt response
        self.id = id_
        # the name according to ecowitt documentation
        self.display_name = display_name
        self.value = value
        # the unit according to ecowitt documentation
        self.unit = unit

    def __str__(self):
        return f"EcowittEntry[id: {self.id}, display_name: {self.display_name}, value: {self.value}, unit: {self.unit}]"

    def __repr__(self):
        return f"EcowittEntry({self.display_name}, {self.value}, {self.unit})"

    def __eq__(self, other):
        if not isinstance(other, EcowittEntry):
            return False
        return self.id == other.id and self.display_name == other.display_name and self.value == other.value and self.unit == other.unit

    def __hash__(self):
        return hash((self.id, self.display_name, self.value, self.unit))


def get_ecowitt_data(url:str, timeout_s=5) -> list[EcowittEntry]:
    ecowitt_endpoint = f"{url}/get_livedata_info"
    data = None
    try:
        response = requests.get(ecowitt_endpoint, timeout=timeout_s)
        data = response.json()
    except (requests.exceptions.ConnectTimeout, requests.exceptions.Timeout) as e:
        log.error(f"Connection to Ecowitt device timed out: {e}")
    except (requests.exceptions.TooManyRedirects,requests.exceptions.ConnectionError,
            requests.exceptions.RequestException) as e:
        log.error(f"Error occurred while making the request: {e}")
    except json.JSONDecodeError as e:
        log.error(f"Error decoding JSON response: {e}")

    if data is None:
        return []

    commonlist:dict[str, dict] =_parse_common_list(data)
    rain:dict[str, dict] = _parse_rain(data)
    wh25:dict[str, dict] = _parse_wh25(data)

    to_entry = lambda key,d: EcowittEntry(d["id"], key, d["val"], d["unit"])
    
    #pprint.pp(commonlist.items())
    #pprint.pp(rain.items())
    #pprint.pp(wh25.items())
    out = [to_entry(key, d) for key, d in commonlist.items()] + [to_entry(key, d) for key, d in rain.items()] + [to_entry(key, d) for key, d in wh25.items()]
    #pprint.pp(out)
    return out


def _parse_common_list(data: dict) -> dict[str, dict]:
    translated, unknown = _translate_fields(data["common_list"], COMMON_LIST_ID_MAPPING)
    if unknown:
        log.warning("Unknown common list fields: %s", unknown)
    return translated

def _parse_rain(data: dict) -> dict[str, dict]:
    rain_data: list[dict] = data["rain"]
    rainlist, unknown_rl = _translate_fields(rain_data, RAIN_ID_MAPPING)
    if unknown_rl:
        log.warning("Unknown rain list fields: %s", unknown_rl)
    return rainlist

def _parse_wh25(data: dict) -> dict[str, dict]:
    wh_25: list[dict] = data["wh25"]
    if len(wh_25) == 0:
        log.warning("Ecowitt device returned empty WH25 data")
        return {}
    if len(wh_25) > 1:
        log.warning("Ecowitt device returned multiple WH25 entries, using first")
        return {}

    whs_25_data = wh_25[0]
    if not (_is_keys_subdict(WH25_ID_MAPPING, whs_25_data) and "unit" in whs_25_data.keys()):
        log.warning("Ecowitt device returned WH25 missing supported fields: %s", whs_25_data)
        return {}

    out = {}
    for key, field_info in WH25_ID_MAPPING.items():
        value = whs_25_data[key]
        name = field_info["name"]
        if key == "intemp":
            out[name] = {"id": "intemp", "val":value, "unit": whs_25_data['unit']}
        else:
            out[name] = _normalize({"id":key, "val": value}, field_info["unit"])

    return out


def _is_keys_subdict(small: dict, big: dict) -> bool:
    s = set(small.keys())
    b = set(big.keys())
    for ss in s:
        if ss not in b:
            return False
    return True

def _number_with_unit(val:str) -> Optional[re.Match]:
    pattern = re.compile(r"\-*[0-9]*\.+[0-9]*\ (.*)")
    return pattern.fullmatch(val)


def _translate_fields(fields: list[dict], mapping: dict[str, dict[str,str]]) -> tuple[dict[str, dict], list[dict]]:
    translated = {}
    unknown = []

    for field in fields:
        field_id = field.get("id")

        if field_id is None:
            log.warning(f"Ecowitt field without id: {field}")
            unknown.append(field)
            continue

        field_info = mapping.get(field_id)
        name = field_info["name"]

        if name is None:
            log.warning(f"Ecowitt field without mapping: {field}")
            unknown.append(field)
            continue

        expected_unit = field_info["unit"]
        if normalized:= _normalize(field, expected_unit):
            translated[name] = normalized

    return translated, unknown

def _normalize(field: dict, expected_unit:str) -> Optional[dict]:
    val = field["val"].strip()
    match = _number_with_unit(val)
    if field.get("unit") and match:
        log.warning(f"Ecowitt field has unit field and unit in the value: {field}")
        return None
    elif match:
        unit = match.group(1)
        field["val"] = val.replace(unit, "").strip()
        field["unit"] = unit
    elif "%" in val:
        field["val"] = val.replace("%", "").strip()
        field["unit"] = "%"

    field_unit = field.get("unit")
    # casefold for case-insensitive string comparsion
    if field_unit and field_unit.casefold() != expected_unit.casefold():
        log.debug(f"Ecowitt field has unexpected unit {field_unit} {expected_unit}")
        converted = _convert_value(field["val"], expected_unit, field_unit)
        if converted is None:
            # skip because the unit does not match expected and could not be converted
            # warning should have been logged in _convert_value
            log.warning(f"Ecowitt field had unexpected unit: {field_unit} which could not be converted to {expected_unit}")
            return None
        
        field["val"] = converted
        field["unit"] = expected_unit
        log.debug(f"Convertetd field unit from {field_unit} to {expected_unit}")

    # still no unit field so use expected unit
    if field.get("unit") is None:
        field["unit"] = expected_unit
    
    return field

def _convert_value(value: str, expected_unit: str, actual_unit: str) -> Optional[float]:
    expected_unit = expected_unit.strip().casefold()
    actual_unit = actual_unit.strip().casefold()

    supported_units = {"c","f","mm","in","m/s","km/h", "mm/hr", "mm/h", "klux", "lux", "hpa", "inhg"}
    if expected_unit not in supported_units or actual_unit not in supported_units:
        log.warning(f"Unsupported unit conversion: {actual_unit} to {expected_unit}")
        return None

    try:
        out = float(value)
    except ValueError:
        log.warning(f"Could not convert value: {value} to float")
        return None

    # treat mm/h and mm/hr as equivalent
    if {expected_unit, actual_unit} <= {"mm/h", "mm/hr"}:
        return out

    if expected_unit == "c" and actual_unit == "f":
        return (out - 32) * 5.0 / 9.0
    elif expected_unit == "f" and actual_unit == "c":
        return (out * 9.0 / 5.0) + 32
    elif expected_unit == "mm" and actual_unit == "in":
        return out * 25.4
    elif expected_unit == "in" and actual_unit == "mm":
        return out / 25.4
    elif expected_unit == "m/s" and actual_unit == "km/h":
        return out / 3.6
    elif expected_unit == "km/h" and actual_unit == "m/s":
        return out * 3.6
    elif expected_unit == "klux" and actual_unit == "lux":
        return out * 1000
    elif expected_unit == "lux" and actual_unit == "klux":
        return out / 1000
    elif expected_unit == "hpa" and actual_unit == "inhg":
        return out * 33.8638866667
    elif expected_unit == "inhg" and actual_unit == "hpa":
        return out / 33.8638866667
    else:
        log.warning(f"Converting from {actual_unit} to {expected_unit} is not supported")
        return None
