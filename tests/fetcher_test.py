import pandas as pd
from api.fetcher import DWDFetcher
import configparser

config = configparser.ConfigParser()
config.read("hometemp.ini")

fetcher = DWDFetcher(config["dwd"]["station"])
print(fetcher)
c_time, c_temp = fetcher.get_dwd_data()
print(f"DWD forecast temperature data for Ulm is: {c_time.strftime('%Y-%m-%d %H:%M:%S')} {c_temp}°C")
dwd_data = fetcher.data
# 241 elements
df_temp = pd.DataFrame({
    "temperature": dwd_data["temperature"],
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
print(df_temp.describe())
# print(df_hum.describe())
# print(df_day.describe())
