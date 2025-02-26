from configparser import SectionProxy
from datetime import datetime, timedelta
from core.core_log import get_logger
from core.database import DwDDataHandler, GoogleDataHandler, UlmDeHandler, WetterComHandler, TIME_FORMAT
from core.util import require_web_access
from endpoint.fetcher import DWDFetcher, GoogleFetcher, UlmDeFetcher, WetterComFetcher

log = get_logger(__name__)


@require_web_access
def dwd_fetch_and_save(database_auth: SectionProxy, dwd_config: SectionProxy) -> None:
    auth = database_auth
    fetcher = DWDFetcher(dwd_config["station"])
    c_time, c_temp, dev = fetcher.get_dwd_data()
    if c_time is None or c_temp is None or dev is None:
        log.error(f"[DWD] Could not receive DWD data")
    else:
        log.info(f"[DWD] Forecast for Ulm is: {c_time.strftime(TIME_FORMAT)} temp={c_temp}°C dev={dev}")
        handler = DwDDataHandler(auth['db_port'], auth['db_host'], auth['db_user'], auth['db_pw'], 'dwd_data')
        handler.init_db_connection()
        if not handler.row_exists_with_timestamp(c_time.strftime(TIME_FORMAT)):
            handler.insert_dwd_data(timestamp=c_time.strftime(TIME_FORMAT), temp=c_temp, temp_dev=dev)
        else:
            update_detected = handler.update_temp_by_timestamp(c_time.strftime(TIME_FORMAT), c_temp, dev)
            log.info(f"[DWD] Temperature for timestamp already exists")
            # process DWD data update for all found temperatures found by timestamp
            if update_detected:
                log.info("[DWD] Data update detected.")
                # skip updates for temperatures if not in range [-100, 100] °C sometimes measures with a temp value of 32767 and dev 0 occur.
                sanity_threshold = 100
                temp_values = fetcher.data["temperature"]
                temp_std = fetcher.data["temperatureStd"]
                time_diff = timedelta(seconds=(fetcher.data["timeStep"] / 1000))
                timestamp_to_update = c_time - time_diff
                for i in range(fetcher._get_index(timestamp_to_update), -1, -1):
                    new_temp = temp_values[i] / 10.0
                    new_dev = temp_std[i]
                    if new_temp <= sanity_threshold and new_temp >= (sanity_threshold * -1):
                        old_temp = handler.get_temp_for_timestamp(timestamp_to_update.strftime(TIME_FORMAT))
                        log.info(timestamp_to_update.strftime(
                            TIME_FORMAT) + f" old/new: {old_temp}/{new_temp} {new_dev}")
                        if old_temp is None:
                            handler.insert_dwd_data(timestamp_to_update.strftime(TIME_FORMAT), new_temp,
                                                    new_dev)
                        elif old_temp != new_temp:
                            handler.update_temp_by_timestamp(timestamp_to_update.strftime(TIME_FORMAT),
                                                             new_temp,
                                                             new_dev)
                    else:
                        log.warning(
                            "[DWD] Reached sanity threshold for temp updates at " + timestamp_to_update.strftime(
                                TIME_FORMAT) + f" new: {new_temp} {new_dev}")
                        break
                    timestamp_to_update -= time_diff


@require_web_access
def google_fetch_and_save(database_auth: SectionProxy, google_config: SectionProxy) -> None:
    auth = database_auth
    fetcher = GoogleFetcher()
    google_data = fetcher.get_weather_data(google_config["location"])
    if google_data is None:
        log.error("[Google] Could not receive google data")
    else:
        c_time = datetime.now().strftime(TIME_FORMAT)
        c_temp = google_data["temp_now"]
        c_per = google_data["precipitation"]
        c_hum = google_data["humidity"]
        c_wind = google_data["wind"]
        c_region = google_data["region"]
        msg = f"[Google] Forecast for {c_region} is: {c_time} temp={c_temp}°C hum={c_hum}% per={c_per}% wind={c_wind} km/h"
        log.info(msg)
        handler = GoogleDataHandler(auth['db_port'], auth['db_host'], auth['db_user'], auth['db_pw'], 'google_data')
        handler.init_db_connection()
        handler.insert_google_data(timestamp=c_time, temp=c_temp, humidity=c_hum, precipitation=c_per, wind=c_wind)


@require_web_access
def wettercom_fetch_and_save(database_auth: SectionProxy, wettercom_config: SectionProxy) -> None:
    # dyn is allowed to be null in database
    wettercom_temp_static = WetterComFetcher().get_data_static(wettercom_config["url"][1:-1])
    if wettercom_temp_static is None:
        log.error("[Wetter.com] Failed to fetch static temp data. Skipping!")
        return
    wettercom_temp_dyn = WetterComFetcher.get_data_dynamic(wettercom_config["url"][1:-1])
    c_time = datetime.now().strftime(TIME_FORMAT)
    if wettercom_temp_dyn is None:
        log.warning("[Wetter.com] Failed to fetch dynamic temp data.")
    log.info(
        f"[Wetter.com] Static vs Dynamic Temperature at {c_time} is {wettercom_temp_static}°C vs {wettercom_temp_dyn}°C")
    auth = database_auth
    handler = WetterComHandler(auth['db_port'], auth['db_host'], auth['db_user'], auth['db_pw'], 'wettercom_data')
    handler.init_db_connection()
    handler.insert_wettercom_data(timestamp=c_time, temp_stat=wettercom_temp_static, temp_dyn=wettercom_temp_dyn)


@require_web_access
def ulmde_fetch_and_save(database_auth: SectionProxy) -> None:
    auth = database_auth
    ulm_temp = UlmDeFetcher.get_data()
    if ulm_temp is None:
        log.error("[Ulm] Could not receive google data")
    else:
        c_time = datetime.now().strftime(TIME_FORMAT)
        msg = f"[Ulm] Forecast is: {c_time} temp={ulm_temp}°C"
        log.info(msg)
        handler = UlmDeHandler(auth['db_port'], auth['db_host'], auth['db_user'], auth['db_pw'], 'ulmde_data')
        handler.init_db_connection()
        handler.insert_ulmde_data(timestamp=c_time, temp=ulm_temp)
