from core.core_log import setup_logging, get_logger
from core.core_configuration import load_config, database_config, hometemp_config
import re
import schedule
import threading
import time
from datetime import datetime

from core.command import CommandService
from core.distribute import send_visualization_email
from core.database import DwDDataHandler, GoogleDataHandler, UlmDeHandler, SensorDataHandler, WetterComHandler
from core.sensors.dht import get_sensor_data
from core.sensors.util import get_temperature
from core.virtualization import init_postgres_container
from core.plotting import PlotData,SupportedDataFrames, draw_complete_summary
from typing import Callable, Tuple, List, Optional, Dict, Any

# GLOBAL Variables
log = None
command_service = None


def _get__visualization_data():
    auth = database_config()
    sensor_data_handler = SensorDataHandler(auth['db_port'], auth['db_host'], auth['db_user'], auth['db_pw'],
                                            'sensor_data')
    sensor_data_handler.init_db_connection(check_table=False)
    # sensor data
    df = sensor_data_handler.read_data_into_dataframe()
    df = df.sort_values(by="timestamp")
    df['timestamp'] = df['timestamp'].map(
        lambda x: datetime.strptime(str(x).replace("+00:00", "").strip(), '%Y-%m-%d %H:%M:%S'))
    # Google weather data
    google_handler = GoogleDataHandler(auth['db_port'], auth['db_host'], auth['db_user'], auth['db_pw'], 'google_data')
    google_handler.init_db_connection(check_table=False)
    google_df = google_handler.read_data_into_dataframe()
    google_df['timestamp'] = google_df['timestamp'].map(
        lambda x: datetime.strptime(re.sub('\..*', '', str(x).strip()), '%Y-%m-%d %H:%M:%S'))
    google_df = google_df.sort_values(by="timestamp")
    # DWD weather data
    dwd_handler = DwDDataHandler(auth['db_port'], auth['db_host'], auth['db_user'], auth['db_pw'], 'dwd_data')
    dwd_handler.init_db_connection(check_table=False)
    dwd_df = dwd_handler.read_data_into_dataframe()
    dwd_df['timestamp'] = dwd_df['timestamp'].map(
        lambda x: datetime.strptime(str(x).strip().replace('+00:00', ''), '%Y-%m-%d %H:%M:%S'))
    dwd_df = dwd_df.sort_values(by="timestamp")
    # Wetter.com data
    wettercom_handler = WetterComHandler(auth['db_port'], auth['db_host'], auth['db_user'], auth['db_pw'],
                                         'wettercom_data')
    wettercom_handler.init_db_connection()
    wettercom_df = wettercom_handler.read_data_into_dataframe()
    wettercom_df['timestamp'] = wettercom_df['timestamp'].map(
        lambda x: datetime.strptime(str(x).strip().replace('+00:00', ''), '%Y-%m-%d %H:%M:%S'))
    # Ulm.de data
    ulmde_handler = UlmDeHandler(auth['db_port'], auth['db_host'], auth['db_user'], auth['db_pw'], 'ulmde_data')
    ulmde_handler.init_db_connection()
    ulmde_df = ulmde_handler.read_data_into_dataframe()
    ulmde_df['timestamp'] = ulmde_df['timestamp'].map(
        lambda x: datetime.strptime(str(x).strip().replace('+00:00', ''), '%Y-%m-%d %H:%M:%S'))

    return (df, google_df, dwd_df, wettercom_df, ulmde_df)


# ------------------------------- Main  ----------------------------------------------

def _create_visualization(mode: str, save_path_template: str, email_receiver: Optional[str] = None):
    log.info(f"{mode}: Creating Measurement Data Visualization")
    sensor_data, google_df, dwd_df, wettercom_df, ulmde_df = _get__visualization_data()
    plots = [
        PlotData(SupportedDataFrames.Main, sensor_data, True),
        PlotData(SupportedDataFrames.DWD_DE, dwd_df),
        PlotData(SupportedDataFrames.GOOGLE_COM, google_df),
        PlotData(SupportedDataFrames.WETTER_COM, wettercom_df),
        PlotData(SupportedDataFrames.ULM_DE, ulmde_df),
    ]
    name = datetime.now().strftime("%d-%m-%Y")
    save_path = save_path_template.format(name=name)
    
    draw_complete_summary(plots, merge_subplots_for=plots, save_path=save_path)
    log.info(f"{mode}: Done")
    
    send_visualization_email(
        df=sensor_data,
        ulmde_df=ulmde_df,
        google_df=google_df,
        dwd_df=dwd_df,
        wettercom_df=wettercom_df,
        path_to_pdf=save_path,
        receiver=email_receiver)


def _create_visualization_commanded(commander):
    _create_visualization(mode="Command",save_path_template="plots/commanded/{name}.pdf",email_receiver=commander)


def create_visualization_timed():
    _create_visualization(mode="Timed",save_path_template="plots/{name}.pdf")

def run_received_commands():
    log.info("Checking for commands")
    command_service.receive_and_execute_commands()
    log.info("Done")


def run_threaded(job_func):
    job_thread = threading.Thread(target=job_func)
    job_thread.start()


def collect_and_save_to_db():
    log.info("Start Measurement Data Collection")
    auth = database_config()
    handler = SensorDataHandler(auth['db_port'], auth['db_host'], auth['db_user'], auth['db_pw'], 'sensor_data')
    handler.init_db_connection()
    cpu_temp = get_temperature()
    room_temp, humidity, timestamp = get_sensor_data(int(hometemp_config()["sensor_pin"]), False)
    if room_temp is not None and humidity is not None and timestamp is not None:
        log.info(
            "[Measurement {0}] CPU={1:f}*C, Room={2:f}*C, Humidity={3:f}%".format(timestamp, cpu_temp, room_temp,
                                                                                  humidity))
        handler.insert_measurements_into_db(timestamp=timestamp, humidity=humidity, room_temp=room_temp,
                                            cpu_temp=cpu_temp)
    log.info("Done")


def main():
    log.info(f"------------------- HomeTemp v{hometemp_config()['version']} -------------------")
    if not init_postgres_container(database_config()):
        log.error("Postgres container startup error! Shutting down ...")
        exit(1)
        # after restart, database needs some time to start
    time.sleep(1)

    cmd_name = 'plot'
    function_params = ['commander']
    command_service.add_new_command((cmd_name, [], _create_visualization_commanded, function_params))

    schedule.every(10).minutes.do(collect_and_save_to_db)
    # run_threaded assumes that we never have overlapping usage of this method or its components
    schedule.every().day.at("06:00").do(run_threaded, create_visualization_timed)
    schedule.every(10).minutes.do(run_threaded, run_received_commands)
    log.info("finished initialization")

    collect_and_save_to_db()
    create_visualization_timed()
    time.sleep(1)
    run_received_commands()
    log.info("entering main loop")
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    setup_logging(log_file='hometemp.log')
    load_config()
    # Define all global variables
    log = get_logger(__name__)
    command_service = CommandService()
    main()
