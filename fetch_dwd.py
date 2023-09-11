import logging
import configparser, schedule, time
from datetime import datetime
from api.fetcher import DWDFetcher
from persist.database import DwDDataHandler

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(filename='dwd_measurement.log',
                    encoding='utf-8',
                    level=logging.INFO)

log = logging.getLogger('dwdfetcher')
log.addHandler(logging.StreamHandler())

config = configparser.ConfigParser()
config.read("hometemp.ini")


def fetch_and_save():
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
    


def main():
    log.info("------------------- Fetch DWD Measurements v0.1 -------------------")
    schedule.every(10).minutes.do(fetch_and_save)

    log.info("finished initialization")
    fetch_and_save()

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
