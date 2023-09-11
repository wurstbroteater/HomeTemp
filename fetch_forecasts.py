import logging
import configparser, schedule, time
from datetime import datetime
from api.fetcher import DWDFetcher, GoogleFetcher
from persist.database import DwDDataHandler, GoogleDataHandler

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(filename='dwd_measurement.log',
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
    log.info(f"[DWD] Forecast for Ulm is: {c_time.strftime('%Y-%m-%d %H:%M:%S')} temp={c_temp}°C dev={dev}")
    handler = DwDDataHandler(auth['db_port'], auth['db_host'], auth['db_user'], auth['db_pw'], 'dwd_data')
    handler.init_db_connection()
    if not handler.row_exists_with_timestamp(c_time):
        handler.insert_dwd_data(timestamp=c_time.strftime('%Y-%m-%d %H:%M:%S'), temp=c_temp, temp_dev=dev)
    else:
        handler.update_temp_by_timestamp(c_time.strftime('%Y-%m-%d %H:%M:%S'), c_temp, dev)


def google_fetch_and_save():
    auth = config["db"]
    fetcher = GoogleFetcher()
    google_data = fetcher.get_weather_data(config["google"]["location"])
    if google_data is None:
        log.error("Could not receive google data")
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
        handler.insert_google_data(timestamp=c_time, temp=c_temp, humidity=c_hum, precipitation=c_per)


def main():
    log.info("------------------- Fetch DWD Measurements v0.2 -------------------")
    schedule.every(10).minutes.do(dwd_fetch_and_save)
    schedule.every(10).minutes.do(google_fetch_and_save)

    log.info("finished initialization")
    dwd_fetch_and_save()
    google_fetch_and_save()

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
