import logging
from core.plotting import *
log = logging.getLogger(__name__)
base_time = datetime(2024, 10, 5, 12, 0, 0)

# Normal Case DataFrame (main)
main_df = pd.DataFrame({
    'timestamp': [base_time, base_time + timedelta(minutes=10), base_time + timedelta(minutes=20)],
    'room_temp': [22.0, 21.8, 22.1] 
})

# DataFrame 1: Aligned timestamps
df1 = pd.DataFrame({
    'timestamp': [base_time, base_time + timedelta(minutes=10), base_time + timedelta(minutes=20)],
    'temp': [15.2, 16.1, 15.8],
    'humidity': [14.9, 15.5, 16.0]
})

# DataFrame 2: Some timestamps are outside the tolerance (edge case 1)
df2 = pd.DataFrame({
    'timestamp': [base_time, base_time + timedelta(minutes=7), base_time + timedelta(minutes=25)],
    'temp': [14.9, 15.5, 16.0]
})

# DataFrame 3: Contains NaN values (edge case 2)
df3 = pd.DataFrame({
    'timestamp': [base_time, base_time + timedelta(minutes=10), base_time + timedelta(minutes=20)],
    'temp_stat': [13.2, None, 14.0],  # One value is NaN
    'temp_dyn': [14.0, 15.0, None]    # Another value is NaN
})



#print(SupportedDataFrames.DWD_DE.temperature_keys)
#print(SupportedDataFrames.DWD_DE.get_inner_plots_params(df2))
#print(SupportedDataFrames.WETTER_COM.get_24h_inner_plots_params(df3))
#test=[PlotData(SupportedDataFrames.Main, main_df, {}),PlotData(SupportedDataFrames.DWD_DE, df2)]
test =[PlotData(SupportedDataFrames.Main, main_df, {}),
       PlotData(SupportedDataFrames.GOOGLE_COM, df1),
       PlotData(SupportedDataFrames.DWD_DE, df2)]
print(draw_complete_summary([],test))


