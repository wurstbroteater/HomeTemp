import pandas as pd
from datetime import datetime, timedelta
from core.plotting import last_24h_df, merge_temperature_by_timestamp

base_time = datetime(2024, 10, 5, 12, 0, 0)

# Normal Case DataFrame (main)
main_df = pd.DataFrame({
    'timestamp': [base_time, base_time + timedelta(minutes=10), base_time + timedelta(minutes=20)],
    'room_temp': [22.0, 21.8, 22.1] 
})

# DataFrame 1: Aligned timestamps
df1 = pd.DataFrame({
    'timestamp': [base_time, base_time + timedelta(minutes=10), base_time + timedelta(minutes=20)],
    'temp': [15.2, 16.1, 15.8] 
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

# DataFrame 4: Empty DataFrame (edge case 3)
df4 = pd.DataFrame({
    'timestamp': [],  # Empty DataFrame
    'temp': []
})

dataframes_info = [
    {'data': df1, 'name': 'df1', 'keys': ['temp']},
    {'data': df2, 'name': 'df2', 'keys': ['temp']},
    {'data': df3, 'name': 'df3', 'keys': ['temp_stat', 'temp_dyn']},
    #{'df': df4, 'name': 'df4', 'keys': ['temp']},  # Empty dataframe
    {'data': main_df, 'name': 'main', 'keys': ['room_temp'], 'main': True}
]

#dataframes_info = [{'df': last_24h_df(ulmde_df), 'name': 'ulm','keys': ['temp']},{'df':last_24h_df(dwd_df),'name': 'dwd', 'keys': ['temp']},{'df':last_24h_df(wettercom_df),'name': 'wettercom', 'keys': ['temp_stat', 'temp_dyn']},{'df': last_24h_df(google_df),'name': 'google', 'keys': ['temp']},{'df': last_24h_df(df),'name': 'main', 'keys': ['room_temp'], 'main': True}]
#dataframes_info = [{'df': ulmde_df, 'name': 'ulm','keys': ['temp']},{'df':dwd_df,'name': 'dwd', 'keys': ['temp']},{'df':wettercom_df,'name': 'wettercom', 'keys': ['temp_stat', 'temp_dyn']},{'df': google_df,'name': 'google', 'keys': ['temp']},{'df': df,'name': 'main', 'keys': ['room_temp'], 'main': True}]

result_df = merge_temperature_by_timestamp(dataframes_info)
print(result_df)
