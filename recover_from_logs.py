import logging
import configparser, re, time
import time
from datetime import datetime, timedelta
from persist.database import SensorDataHandler

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(filename='fixing.log',
                    encoding='utf-8',
                    level=logging.INFO)
log = logging.getLogger('recoverytool')
log.addHandler(logging.StreamHandler())

config = configparser.ConfigParser()
config.read('hometemp.ini')
auth = config["db"]

log.info('Start Database fix')
handler = SensorDataHandler(auth['db_port'], auth['db_host'], auth['db_user'], auth['db_pw'], 'sensor_data2')
handler.init_db_connection()
# handler._clear_table()
counter = 0
start_time = datetime.now()
contains_measure_lines = 0
startswith_measure_lines = 0
with open("/home/eric/HomeTemp/measurement.log") as file:
    for line in file:
        if '[Measurement' in line:
            contains_measure_lines = contains_measure_lines + 1

        if line.startswith("INFO:root:[Measurement") or line.startswith("INFO:hometemp:[Measurement"):
            startswith_measure_lines = startswith_measure_lines + 1

print('Lines containing [Measurment', contains_measure_lines)
print('Lines starting with ...', startswith_measure_lines)

with open("/home/eric/HomeTemp/measurement.log") as file:
    for line in file:
        line = line.strip()
        if line.startswith("INFO:root:[Measurement") or line.startswith("INFO:hometemp:[Measurement"):
            values = re.search(
                r".*\[Measurement (\d*\-\d*\-\d* \d*:\d*:\d*)\] CPU=(\d*\.\d*)\*C, Room=(\d*\.\d*)\*C, Humidity=(\d*\.\d*)\%",
                line)
            # fix date times format
            # log.info(f"Line: {line}")
            capture_time = values.group(1)
            if not str(capture_time).startswith("2023"):
                # logs from before v0.2      
                capture_time = datetime.strptime(capture_time, "%d-%m-%Y %H:%M:%S")
                capture_time = capture_time.strftime("%Y-%m-%d %H:%M:%S")
            cpu_temp = values.group(2)
            room_temp = values.group(3)
            humidity = values.group(4)
            # log.info(f"found: time {capture_time}, cpu {cpu_temp}, room {room_temp},hum {humidity}")
            handler.insert_measurements_into_db(timestamp=capture_time, cpu_temp=cpu_temp, room_temp=room_temp,
                                                humidity=humidity)
            if counter % 100 == 0:
                log.info(f"Progress ~ {counter / startswith_measure_lines * 100}%")

            counter = counter + 1

log.info(
    f"Data inserted successfully. Recoverd {counter} {'column' if counter == 0 else 'columns'} in {datetime.now() - start_time}")
