import logging
import requests
import urllib.parse
from datetime import datetime

log = logging.getLogger('api.fetcher')
import configparser


class Fetcher:
    """
    Default class for fetching data.
    It provides methods for handling error and ok responses from the server.
    This methods can be overwritten by an extending class.
    """

    def __init__(self, endpoint: str, params: list = None):
        self.endpoint = endpoint
        self.params = None if not params else urllib.parse.urlencode(params)
        self.api_link = self._create_api_link()

    def __str__(self):
        return f"Fetcher[{self.api_link}]"

    def _create_api_link(self):
        return self.endpoint + "?" + self.params if self.params else self.endpoint

    def _fetch_data(self):
        response = requests.get(self.api_link)
        if (code := response.status_code) == 200:
            return self._handle_ok_status_code(response)
        else:
            self._handle_bad_status_code(code)

    def _handle_ok_status_code(self, response):
        return response.json()

    def _handle_bad_status_code(self, code: int) -> int:
        log.error(f"Error: Failed to fetch weather data. Status code: {code}")
        return code


class DWDFetcher(Fetcher):
    """
    DataFetcher for retrieving data from Deutsche Wetterdienst (DWD).
    One fetcher is responsible for the data of one weather station.
    """

    def __init__(self, station_id):
        super().__init__("https://app-prod-ws.warnwetter.de/v30/stationOverviewExtended", [("stationIds", station_id)])
        self.station_id = station_id
        self.data = None

    def __str__(self):
        return f"DWDFetcher[{self.station_id}, {super().__str__()}]"

    def _handle_ok_status_code(self, response):
        json_res = super()._handle_ok_status_code(response)
        self.data = json_res[str(self.station_id)]["forecast1"]
        return self.data

    def _get_index(self, current_time=None):
        """
        Calculate index for measurement based on current year, month, date and hour.
        Remaining values will be ignored.
        """

        if not current_time:
            current_time = datetime(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day,
                                    hour=datetime.now().hour, minute=0, second=0, microsecond=0, tzinfo=None, fold=0)

        # from milliseconds to seconds
        start_measurement_time_s = self.data["start"] / 1000
        m_time = datetime.utcfromtimestamp(start_measurement_time_s)
        diff = current_time - m_time
        return int(diff.total_seconds() / (self.data["timeStep"] / 1000))

    def clear_cached_data(self):
        self.data = None

    def get_dwd_data(self, trigger_new_fetch=True):
        if trigger_new_fetch:
            self.clear_cached_data()

        if self.data is None:
            log.info("Fetching new data")
            self.data = self._fetch_data()

        temp_values = self.data["temperature"]
        # observation: temperatureStd is 0 for unlikely temperatures such as 3241.6 °C
        temp_std = self.data["temperatureStd"]
        # ignore minutes, seconds and microseconds
        current_time = datetime(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day,
                                hour=datetime.now().hour,
                                minute=0, second=0, microsecond=0, tzinfo=None, fold=0)

        if len(temp_std) != len(temp_values):
            log.error(f"Error: Unable to validate DWD temperature data because temp values and std differ!")
            return current_time, float('nan'), float('nan')

        current_temp_forecast_index = self._get_index()
        if len(temp_values) < current_temp_forecast_index:
            log.error(
                f"Error: Forecast index out of range, size: {len(temp_values)}, index: {current_temp_forecast_index}")
            return current_time, float('nan'), float('nan')
        elif temp_std[current_temp_forecast_index] == 0:
            log.error(f"Error: 0 tempStd for found temperature {temp_values[current_temp_forecast_index]}")
            return current_time, float('nan'), float('nan')
        else:
            temp = float(temp_values[current_temp_forecast_index]) / 10.0
            dev = self.data['temperatureStd'][current_temp_forecast_index]
            # log.info(f"Found: {current_temp_forecast_index}, {current_time}, {temp}°C, dev: {dev}")
            return current_time, temp, dev
