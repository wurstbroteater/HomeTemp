import logging
from api.fetcher import DWDFetcher
import requests, schedule, time
from datetime import datetime, timedelta
import pandas as pd

logging.basicConfig(filename='dwd_measurement.log',
                    encoding='utf-8',
                    level=logging.INFO)

log = logging.getLogger('dwdfetcher')
log.addHandler(logging.StreamHandler())


def _describe(l: list, name) -> str:
    return pd.DataFrame(l, columns=[name]).describe()


def main():
    log.info("------------------- Fetch DWD Measurments -------------------")
    ulm_station_code = '10838'
    fetcher = DWDFetcher("https://app-prod-ws.warnwetter.de/v30/stationOverviewExtended", f"stationIds={ulm_station_code}")

    if False:
        dwd_data = fetcher.data
        # 241 elements
        df_temp = pd.DataFrame({
            "temperature":  dwd_data["temperature"],
            "temperatureStd": dwd_data["temperatureStd"],
        })
        # 72 elements
        df_day = pd.DataFrame({
            "isDay": dwd_data["isDay"],
            "precipitationTotal": dwd_data["precipitationTotal"]
        })
        # 64 elements
        df_hum = pd.DataFrame({
            "humidity": dwd_data["humidity"],
            "sunshine": dwd_data["sunshine"],
            "surfacePressure": dwd_data["surfacePressure"],
        })
        #print(df_temp.describe())
        #print(df_hum.describe())
        #print(df_day.describe())

    schedule.every(10).minutes.do(fetcher.get_dwd_data())
    m_time, temp = fetcher.get_dwd_data()
    while True:
        schedule.run_pending()
        time.sleep(1)

    #c_time, temp = dwd_get_current_temp_forecast()


if __name__ == "__main__":
    main()