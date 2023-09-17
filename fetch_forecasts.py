import logging
import configparser, schedule, time
from datetime import datetime, timedelta
from api.fetcher import DWDFetcher, GoogleFetcher, WetterComFetcher
from persist.database import DwDDataHandler, GoogleDataHandler, WetterComHandler
from hometemp import run_threaded

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(filename='fetching.log',
                    encoding='utf-8',
                    level=logging.INFO)

log = logging.getLogger('dwdfetcher')
log.addHandler(logging.StreamHandler())

config = configparser.ConfigParser()
config.read("hometemp.ini")


def dwd_fetch_and_save():
    auth = config["db"]
    fetcher = DWDFetcher(config["dwd"]["station"])
    c_time, c_temp, dev = fetcher.get_dwd_data()
    if c_time is None or c_temp is None or dev is None:
        log.error(f"[DWD] Could not receive DWD data")
    else:
        log.info(f"[DWD] Forecast for Ulm is: {c_time.strftime('%Y-%m-%d %H:%M:%S')} temp={c_temp}°C dev={dev}")
        handler = DwDDataHandler(auth['db_port'], auth['db_host'], auth['db_user'], auth['db_pw'], 'dwd_data')
        handler.init_db_connection()
        if not handler.row_exists_with_timestamp(c_time.strftime('%Y-%m-%d %H:%M:%S')):
            handler.insert_dwd_data(timestamp=c_time.strftime('%Y-%m-%d %H:%M:%S'), temp=c_temp, temp_dev=dev)
        else:
            update_detected = handler.update_temp_by_timestamp(c_time.strftime('%Y-%m-%d %H:%M:%S'), c_temp, dev)
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
                        old_temp = handler.get_temp_for_timestamp(timestamp_to_update.strftime("%Y-%m-%d %H:%M:%S"))
                        log.info(timestamp_to_update.strftime(
                            "%Y-%m-%d %H:%M:%S") + f" old/new: {old_temp}/{new_temp} {new_dev}")
                        if old_temp != new_temp:
                            handler.update_temp_by_timestamp(timestamp_to_update.strftime("%Y-%m-%d %H:%M:%S"),
                                                             new_temp,
                                                             new_dev)
                    else:
                        log.warning(
                            "[DWD] Reached sanity threshold for temp updates at " + timestamp_to_update.strftime(
                                "%Y-%m-%d %H:%M:%S") + f" new: {new_temp} {new_dev}")
                        break
                    timestamp_to_update -= time_diff


def google_fetch_and_save():
    auth = config["db"]
    fetcher = GoogleFetcher()
    google_data = fetcher.get_weather_data(config["google"]["location"])
    if google_data is None:
        log.error("[Google] Could not receive google data")
    else:
        c_time = datetime.now()
        c_temp = google_data["temp_now"]
        c_per = google_data["precipitation"]
        c_hum = google_data["humidity"]
        c_wind = google_data["wind"]
        c_region = google_data["region"]
        msg = f"[Google] Forecast for {c_region} is: {c_time.strftime('%Y-%m-%d %H:%M:%S')} temp={c_temp}°C hum={c_hum}% per={c_per}% wind={c_wind} km/h"
        log.info(msg)
        handler = GoogleDataHandler(auth['db_port'], auth['db_host'], auth['db_user'], auth['db_pw'], 'google_data')
        handler.init_db_connection()
        handler.insert_google_data(timestamp=c_time, temp=c_temp, humidity=c_hum, precipitation=c_per, wind=c_wind)


def wettercom_fetch_and_save():
    # dyn is allowed to be null in database
    wettercom_temp_dyn = WetterComFetcher.get_data_dynamic(config["wettercom"]["url"][1:-1])
    wettercom_temp_static = WetterComFetcher().get_data_static(config["wettercom"]["url"][1:-1])
    c_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if wettercom_temp_static is None:
        log.error("[Wetter.com] Error while retrieving temperature")
    else:
        log.info(
            f"[Wetter.com] Static vs Dynamic Temperature at {c_time} is {wettercom_temp_static}°C vs {wettercom_temp_dyn}°C")
        auth = config["db"]
        handler = WetterComHandler(auth['db_port'], auth['db_host'], auth['db_user'], auth['db_pw'], 'wettercom_data')
        handler.init_db_connection()
        handler.insert_wettercom_data(timestamp=c_time, temp_stat=wettercom_temp_static, temp_dyn=wettercom_temp_dyn)


def main():
    # Todo: integrate into hometemp for final release
    log.info(f"------------------- Fetch DWD Measurements v{config['hometemp']['version']} -------------------")
    schedule.every(10).minutes.do(dwd_fetch_and_save)
    schedule.every(10).minutes.do(google_fetch_and_save)
    schedule.every(10).minutes.do(run_threaded, wettercom_fetch_and_save)

    log.info("finished initialization")
    dwd_fetch_and_save()
    google_fetch_and_save()
    run_threaded(wettercom_fetch_and_save)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
