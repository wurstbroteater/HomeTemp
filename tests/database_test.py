import configparser
from datetime import datetime, timedelta

from api.fetcher import DWDFetcher
from persist.database import SensorDataHandler, DwDDataHandler

config = configparser.ConfigParser()
config.read('hometemp.ini')
auth = config["db"]


def foo():
    handler = SensorDataHandler(auth['db_port'], auth['db_host'], auth['db_user'], auth['db_pw'], 'sensor_data2')
    handler.init_db_connection()
    print(handler._check_table_existence())
    print(handler._get_table_size())
    handler.insert_measurements_into_db(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 42.0, 21.0, 69.0)
    print(handler.read_data_into_dataframe())
    print(handler._check_table_existence())
    print(handler._get_table_size())
    handler._clear_table()
    print(handler._check_table_existence())
    print(handler._get_table_size())
    handler._remove_table()
    print(handler._check_table_existence())

    # should fail because table does not exists
    # print(handler._get_table_size())


def process_data_updates():
    sanity_threshold = 100
    fetcher = DWDFetcher(config["dwd"]["station"])
    data = fetcher.get_dwd_data()
    handler = DwDDataHandler(auth['db_port'], auth['db_host'], auth['db_user'], auth['db_pw'], 'dwd_data')
    handler.init_db_connection()
    c_time = datetime.strptime('2023-09-12 17:00:00', "%Y-%m-%d %H:%M:%S")
    temp_values = fetcher.data["temperature"]
    temp_std = fetcher.data["temperatureStd"]
    time_diff = timedelta(seconds=(fetcher.data["timeStep"] / 1000))
    timestamp_to_update = c_time - time_diff
    for i in range(fetcher._get_index(timestamp_to_update), -1, -1):
        print(i)
        new_temp = temp_values[i] / 10.0
        new_dev = temp_std[i]
        if new_temp <= sanity_threshold and new_temp >= (sanity_threshold * -1):
            old_temp = handler.get_temp_for_timestamp(timestamp_to_update.strftime("%Y-%m-%d %H:%M:%S"))
            print(timestamp_to_update.strftime("%Y-%m-%d %H:%M:%S") + f" old/new: {old_temp}/{new_temp} {new_dev}")
            if old_temp != new_temp:
                print("update!")
                # handler.update_temp_by_timestamp(timestamp_to_update.strftime("%Y-%m-%d %H:%M:%S"), new_temp, new_dev)
                pass
        else:
            print("Reached sanity threshold for temp updates at " + timestamp_to_update.strftime(
                "%Y-%m-%d %H:%M:%S") + f" new: {new_temp} {new_dev}")
            break
        timestamp_to_update -= time_diff


process_data_updates()
