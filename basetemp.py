from datetime import datetime
from typing import Optional

import schedule
import threading
import time

from core.command import CommandService
from core.sensors.dht import SUPPORTED_SENSORS
from core.core_configuration import load_config, database_config, hometemp_config, get_sensor_type
from core.core_log import setup_logging, get_logger
from core.database import SensorDataHandler
from core.distribute import send_picture_email, send_visualization_email, send_heat_warning_email
from core.plotting import PlotData, SupportedDataFrames, draw_complete_summary
from core.usage_util import init_database, _take_picture, get_data_for_plotting, retrieve_and_save_sensor_data

# GLOBAL Variables
log = None
command_service = None
SEND_TEMPERATURE_WARNING = False


def _get__visualization_data():
    auth = database_config()
    df = get_data_for_plotting(auth, SensorDataHandler, SupportedDataFrames.Main)
    return df


# ------------------------------- Main  ----------------------------------------------


def take_picture_timed():
    log.info("Timed: Taking picture")
    name = f'pictures/{datetime.now().strftime("%Y-%m-%d-%H:%M:%S")}'
    if _take_picture(name):
        log.info("Timed: Taking picture done")
    else:
        log.info("Timed: Taking picture was not successful")


def _take_picture_commanded(commander):
    log.info("Command: Taking picture")
    name = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
    encoding = "png"
    save_path = f"pictures/commanded/{name}"
    if _take_picture(save_path, encoding=encoding):
        log.info("Command: Taking picture done")
        sensor_data = _get__visualization_data()
        send_picture_email(picture_path=f"{save_path}.{encoding}", df=sensor_data, receiver=commander)
        log.info("Command: Done")
    else:
        log.info("Command: Taking picture was not successful")


def _create_visualization_commanded(commander):
    _create_visualization(mode="Command", save_path_template="plots/commanded/{name}.pdf", email_receiver=commander)


def create_visualization_timed():
    _create_visualization(mode="Timed", save_path_template="plots/commanded/{name}.pdf")


def _create_visualization(mode: str, save_path_template: str, email_receiver: Optional[str] = None):
    log.info(f"{mode}: Creating Measurement Data Visualization")
    sensor_data = _get__visualization_data()
    name = datetime.now().strftime("%d-%m-%Y")
    save_path = save_path_template.format(name=name)

    draw_complete_summary([PlotData(SupportedDataFrames.Main, sensor_data, True)], save_path=save_path)
    log.info(f"{mode}: Done")

    send_visualization_email(df=sensor_data, path_to_pdf=save_path, receiver=email_receiver)


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
    sensor_pin = int(hometemp_config()["sensor_pin"])
    data_tuple = retrieve_and_save_sensor_data(auth, sensor_pin, is_dht11)

    if data_tuple is not None:
        room_temp = data_tuple[2]
        # TODO: make customizable
        # heat warning
        max_heat = 28.9
        is_overheating = room_temp > max_heat
        min_heat = 16.5
        if SEND_TEMPERATURE_WARNING and (is_overheating or room_temp < min_heat):
            indicator = "above" if is_overheating else "below"
            extremum = max_heat if is_overheating else min_heat
            log.warning(f"Sending heat warning because room temp is {indicator} {extremum}°C")
            send_heat_warning_email(room_temp)

    log.info("Done")


def main():
    log.info(f"------------------- HomeTemp v{hometemp_config()['version']} -------------------")
    init_database(SensorDataHandler, database_config(), 'sensor_data')

    picture_cmd_name = 'pic'
    picture_fun_params = ['commander']
    command_service.add_new_command((picture_cmd_name, [], _take_picture_commanded, picture_fun_params))
    vis_cmd_name = 'plot'
    vis_fun_params = ['commander']
    command_service.add_new_command((vis_cmd_name, [], _create_visualization_commanded, vis_fun_params))

    schedule.every(10).minutes.do(collect_and_save_to_db)
    # Phase 1
    # schedule.every().day.at("11:45").do(run_threaded, create_visualization_timed)
    # schedule.every().day.at("19:00").do(run_threaded, take_picture_timed)
    # schedule.every().day.at("03:00").do(run_threaded, take_picture_timed)
    # schedule.every().day.at("10:30").do(run_threaded, take_picture_timed)
    # Phase 2
    schedule.every().day.at("08:00").do(run_threaded, create_visualization_timed)
    # schedule.every().day.at("06:00").do(run_threaded, take_picture_timed)
    # schedule.every().day.at("02:00").do(run_threaded, take_picture_timed)
    # schedule.every().day.at("20:00").do(run_threaded, take_picture_timed)

    # Common
    schedule.every(17).minutes.do(run_threaded, run_received_commands)

    log.info("finished initialization")

    collect_and_save_to_db()
    create_visualization_timed()
    time.sleep(1)
    # take_picture_timed()
    run_received_commands()
    log.info("entering main loop")
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    setup_logging(log_file='basetemp.log')
    load_config()
    # Define all global variables
    log = get_logger(__name__)
    command_service = CommandService()
    main()
