import logging
import requests, schedule, time
from datetime import datetime, timedelta
import pandas as pd

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(filename='dwd_measurement.log',
                    encoding='utf-8',
                    level=logging.INFO)

log = logging.getLogger('dwdfetcher')
log.addHandler(logging.StreamHandler())


def _describe(l: list, name) -> str:
    return pd.DataFrame(l, columns=[name]).describe()

def _get_dwd_data():
    # Station code for Ulm
    s_code = '10838'
    response = requests.get(f"https://app-prod-ws.warnwetter.de/v30/stationOverviewExtended?stationIds={s_code}")
    if response.status_code == 200:
        return response.json()[s_code]["forecast1"]
    else:
        log.error(f"Error: Failed to fetch weather data. Status code: {response.status_code}")

def dwd_get_current_temp_forecast():
    dwd_data = _get_dwd_data()
    temp_values = dwd_data["temperature"]
    #observation: temperatureStd is 0 for unlikly temperatures such as 3241.6 °C
    temp_std = dwd_data["temperatureStd"]
    # ignore minutes, seconds and microseconds
    current_time = datetime(datetime.now().year, datetime.now().month, datetime.now().day, hour=datetime.now().hour, minute=0, second=0, microsecond=0, tzinfo=None, fold=0)

    if len(temp_std) != len(temp_values):
        log.error(f"Error: Unable to validate DWD temperature data because temp values and std differ!")
        #return current_time, float('nan')


    # Calculate index of current temperature measurement
    # from milliseconds to seconds
    start_measurment_time_s  = dwd_data["start"] / 1000
    m_time = datetime.utcfromtimestamp(start_measurment_time_s)
    diff = current_time - m_time
    current_temp_forecast_index = int(diff.total_seconds() / (dwd_data["timeStep"] / 1000))
    
    if len(temp_values) < current_temp_forecast_index:
        log.error(f"Error: Forecast index out of range, size: {len(temp_values)}, index: {current_temp_forecast_index}")
        #return current_time, float('nan')
    elif temp_std[current_temp_forecast_index] == 0:
        log.error(f"Error: 0 tempStd for found temperature {temp_values[current_temp_forecast_index]}")
        #return current_time, float('nan')
    else:
        temp = float(temp_values[current_temp_forecast_index])
        log.info(f"Found: {current_temp_forecast_index}, {current_time}, {temp / 10.0}°C, dev: {dwd_data['temperatureStd'][current_temp_forecast_index]}")
        #return current_time, temp 


    #step_size_s = timedelta(seconds=dwd_data["timeStep"] / 1000)
    #loop_time = m_time
    #print()
    #for i, temp in enumerate(temp_values):
    #    if loop_time == current_time:
    #        print("Found:",i, loop_time, f"{temp / 10.0}°C", f"dev: {dwd_data['temperatureStd'][i]}")
    #        return loop_time, float(temp / 10.0)
    #    loop_time = loop_time + step_size_s

    #print("Unable to find temperature forecast for " + str(current_time))
    #return float('nan')



def main():
    log.info("------------------- Fetch DWD Measurments -------------------")
    if False:
        dwd_data =_get_dwd_data()
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

    schedule.every(10).minutes.do(dwd_get_current_temp_forecast)
    dwd_get_current_temp_forecast()
    while True:
        schedule.run_pending()
        time.sleep(1)

    #c_time, temp = dwd_get_current_temp_forecast()


if __name__ == "__main__":
    main()