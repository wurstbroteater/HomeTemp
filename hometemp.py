import threading
import time
from datetime import datetime
from typing import Optional

import schedule

from core.command import CommandService
from core.sensors.dht import SUPPORTED_SENSORS
from core.core_configuration import load_config, database_config, core_config, get_sensor_type
from core.core_log import setup_logging, get_logger
from core.database import DwDDataHandler, GoogleDataHandler, UlmDeHandler, SensorDataHandler, WetterComHandler
from core.distribute import send_visualization_email
from core.plotting import PlotData, SupportedDataFrames, draw_complete_summary
from core.usage_util import init_database, get_data_for_plotting, retrieve_and_save_sensor_data

# GLOBAL Variables
log = None
command_service = None


def _get__visualization_data():
    auth = database_config()
    df = get_data_for_plotting(auth, SensorDataHandler, SupportedDataFrames.Main)
    google_df = get_data_for_plotting(auth, GoogleDataHandler, SupportedDataFrames.GOOGLE_COM)
    dwd_df = get_data_for_plotting(auth, DwDDataHandler, SupportedDataFrames.DWD_DE)
    wettercom_df = get_data_for_plotting(auth, WetterComHandler, SupportedDataFrames.WETTER_COM)
    ulmde_df = get_data_for_plotting(auth, UlmDeHandler, SupportedDataFrames.ULM_DE)
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
    _create_visualization(mode="Command", save_path_template="plots/commanded/{name}.pdf", email_receiver=commander)


def create_visualization_timed():
    _create_visualization(mode="Timed", save_path_template="plots/{name}.pdf")


def run_received_commands():
    log.info("Checking for commands")
    command_service.receive_and_execute_commands()
    log.info("Done")


def run_threaded(job_func):
    job_thread = threading.Thread(target=job_func)
    job_thread.start()


def collect_and_save_to_db():
    is_dht11 = get_sensor_type(SUPPORTED_SENSORS) == SUPPORTED_SENSORS[0]
    auth = database_config()
    sensor_pin = int(core_config()["sensor_pin"])
    retrieve_and_save_sensor_data(auth, sensor_pin, is_dht11)
    log.info("Done")


def main():
    log.info(f"------------------- HomeTemp v{core_config()['version']} -------------------")
    init_database(SensorDataHandler, database_config(), 'sensor_data')

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
