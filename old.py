import pandas as pd
import numpy as np
from datetime import timedelta, datetime
from typing import List, Dict, Any
from core.p import last_24h_df

#dataframes_info = [{'df': last_24h_df(ulmde_df), 'name': 'ulm','keys': ['temp']},{'df':last_24h_df(dwd_df),'name': 'dwd', 'keys': ['temp']},{'df':last_24h_df(wettercom_df),'name': 'wettercom', 'keys': ['temp_stat', 'temp_dyn']},{'df': last_24h_df(google_df),'name': 'google', 'keys': ['temp']},{'df': last_24h_df(df),'name': 'main', 'keys': ['room_temp'], 'main': True}]
#dataframes_info = [{'df': ulmde_df, 'name': 'ulm','keys': ['temp']},{'df':dwd_df,'name': 'dwd', 'keys': ['temp']},{'df':wettercom_df,'name': 'wettercom', 'keys': ['temp_stat', 'temp_dyn']},{'df': google_df,'name': 'google', 'keys': ['temp']},{'df': df,'name': 'main', 'keys': ['room_temp'], 'main': True}]

def merge_dataframes_by_timestamp_of_main(dataframes_info: List[Dict[str, Any]], tolerance_min: int = 5) -> pd.DataFrame:
    """
    Merge temperature data of dataframes by timestamp of main DataFrame. The dict in the dataframes_info
    with key 'main': True (only once) is the main DataFrame. 
    This method creates a new DataFrame containing the minimum, maximum and mean temperature calculated 
    from all remaining, none main, DataFrames and the timestamp and temperature for this timestamp from 
    main DataFrame.
   
    Strategy:
    For each timestamp in main DataFrame:
      - In all remaining dataframes find the temperature data within range timestamp +- tolerance_min
        and them to temps_in_interval
      - Calculate min, max and mean of temps_in_interval and add them to oustide_* lists
    - Create Dataframe from collected data
    """
    # Assuming all dataframes are sorted by timestamp, oldest first
    # Identify the main DataFrame (only one dict should have 'main': True)
    temp_dfs = list(filter(lambda df_info: df_info.get('main', False), dataframes_info))
    if len(temp_dfs) != 1:
        raise ValueError("There must be exactly one DataFrame marked as 'main'")
    
    timestamp_col = 'timestamp',
    main_df_info = temp_dfs[0]
    dataframes_info.remove(main_df_info)  
    main_df: pd.DataFrame = main_df_info['df'][[timestamp_col] + main_df_info['keys']]
    main_df_len = len(main_df)
    time_delta = timedelta(minutes=tolerance_min)
    timestamps = np.array([])
    inside_temps = np.array([], dtype=float)
    outside_min = np.array([], dtype=float)
    outside_max = np.array([], dtype=float)
    outside_mean = np.array([], dtype=float)

    start_time = datetime.now()
    show_hint = 0
    show_level = 5
    counter = 0
    for (_,timestamp, room_temp) in main_df.itertuples(name=None):
        per_processed = counter /  main_df_len * 100

        temps_in_interval =  np.array([], dtype=float)
        # there are 4 dataframes with outside data with each one is approx. 50k rows with not more than 2-4 columns
        for outside_data in dataframes_info:
            # from outside_data get df and use only timestamp + names for columns with temperature data
            df = outside_data['df'][[timestamp_col] + outside_data['keys']]
            befores = timestamp - time_delta
            afters =  timestamp + time_delta
            # find all rows with timestamp +- time_delta
            df = df[(df['timestamp'] >= befores) & (df['timestamp'] <= afters)]
            # usualy about 2-4 entries
            findings = np.array(df[outside_data['keys']].values).flatten()
            temps_in_interval= np.append(temps_in_interval, findings)
            
            show_debug_out =  int(per_processed) % show_level  == 0 and int(per_processed) == show_hint
            if show_debug_out:
                print(f"Processing {counter}/{main_df_len} {per_processed} %")
                #print(f"{timestamp} df: {outside_data['name']} found {len(df)} matche(s)")
                #print(f"Found: {findings}")
                #print(f"Current interval {temps_in_interval}")
                show_hint += show_level

        #print("append timestamps")
        timestamps = np.append(timestamps,timestamp)
        #print("append timestamps done")
        inside_temps= np.append(inside_temps,room_temp)
        if temps_in_interval.size > 0:
            outside_min=np.append(outside_min,np.min(temps_in_interval))
            outside_max=np.append(outside_max,np.max(temps_in_interval))
            outside_mean=np.append(outside_mean,np.mean(temps_in_interval))
        else:
            outside_min=np.append(outside_min,None)
            outside_max=np.append(outside_max,None)
            outside_mean=np.append(outside_mean,None)
        counter += 1

    results_df = pd.DataFrame({
        'timestamp': timestamps,
        'inside_temp': inside_temps,
        'outside_min': outside_min,
        'outside_max': outside_max,
        'outside_mean': outside_mean
    })
    print(f"Processed {main_df_len} in {datetime.now() - start_time}")
    return results_df


#result_df: pd.DataFrame = merge_dataframes_by_timestamp_of_main(dataframes_info)
#result_df