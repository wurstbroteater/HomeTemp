import logging 
import re
import time
import psycopg2
from psycopg2 import sql
from datetime import datetime, timedelta
from humidity import init_db_connection, _clear_table, insert_measurements_into_db
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(filename='fixing.log',
                    encoding='utf-8',
                    level=logging.INFO)
log = logging.getLogger('recoverytool')

log.addHandler(logging.StreamHandler())

log.info('Start Database fix')
con = init_db_connection()
#_clear_table(con)
con.close()    
counter = 0
start_time = datetime.now()
with open("/home/eric/HomeTemp/measurement.log") as file:
    for line in file: 
        line = line.strip() 
        if line.startswith("INFO:root:[Measurement") or line.startswith("INFO:hometemp:[Measurement"):
            values = re.search(r".*\[Measurement (\d*\-\d*\-\d* \d*:\d*:\d*)\] CPU=(\d*\.\d*)\*C, Room=(\d*\.\d*)\*C, Humidity=(\d*\.\d*)\%", line)
            # fix date times format
            #log.info(f"Line: {line}")
            capture_time = values.group(1)
            if not str(capture_time).startswith("2023"): 
                # logs from before v0.2      
                capture_time = datetime.strptime(capture_time, "%d-%m-%Y %H:%M:%S")
                capture_time = capture_time.strftime("%Y-%m-%d %H:%M:%S")
            cpu_temp = values.group(2)
            room_temp = values.group(3)
            humidity = values.group(4)
            log.info(f"found: time {capture_time}, cpu {cpu_temp}, room {room_temp},hum {humidity}")
            # assures transaction is completed before the next one to avoid errors 
            #con = init_db_connection()
            #insert_measurements_into_db(con, timestamp=capture_time, cpu_temp=cpu_temp, room_temp=room_temp, humidity=humidity)
            #con.close()
            log.info(f"Progress ~ {counter / 2337 * 100}%")
            counter = counter + 1
  

log.info(f"Data inserted successfully. Recoverd {counter} {'column' if counter == 0 else 'columns'} in {datetime.now() - start_time}")