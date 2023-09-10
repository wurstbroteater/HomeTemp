import configparser, logging
from api.fetcher import DWDFetcher
import schedule, time
from persist.database import DwDDataHandler

config = configparser.ConfigParser()
config.read("hometemp.ini")

logging.basicConfig(filename='dwd_measurement.log',
                    encoding='utf-8',
                    level=logging.INFO)

log = logging.getLogger('dwdfetcher')
log.addHandler(logging.StreamHandler())


def fetch_and_save():
    auth = config["db"]
    fetcher = DWDFetcher(config["dwd"]["station"])
    c_time, c_temp = fetcher.get_dwd_data()
    log.info(f"[DWD] Forecast for Ulm is: {c_time.strftime('%Y-%m-%d %H:%M:%S')} temp={c_temp}°C")
    handler = DwDDataHandler(auth['db_port'], auth['db_host'], auth['db_user'], auth['db_pw'], 'dwd_data')
    handler.init_db_connection()
    handler.insert_dwd_data(timestamp=c_time.strftime('%Y-%m-%d %H:%M:%S'), temp=c_temp)


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