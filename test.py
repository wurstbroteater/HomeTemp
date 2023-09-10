from persist.database import SensorDataHandler
import configparser
from datetime import datetime

config = configparser.ConfigParser()
config.read('hometemp.ini')
auth = config["db"]

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
#print(handler._get_table_size())
