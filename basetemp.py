from core.core_log import setup_logging, get_logger
from core.core_configuration import load_config, database_config, hometemp_config
import schedule, time, threading
from datetime import datetime
from core.distribute import send_picture_email, send_visualization_email, send_heat_warning_email
from core.command import CommandService
from core.database import SensorDataHandler
from core.sensors.util import get_temperature
from core.virtualization import PostgresDockerManager, init_postgres_container
from core.plotting import draw_plots
from core.sensors.dht import get_sensor_data
from core.sensors.camera import RpiCamController

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

    return df


# ------------------------------- Main  ----------------------------------------------

def _take_picture(name, encoding="png"):
    rpi_cam = RpiCamController()
    # file name is set in capture_image to filepath.encoding which is png on default
    return rpi_cam.capture_image(file_path=name, encoding=encoding, rotation=90)


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
    log.info("Command: Creating Measurement Data Visualization")
    sensor_data = _get__visualization_data()

    name = datetime.now().strftime("%d-%m-%Y")
    save_path = f"plots/commanded/{name}.pdf"
    draw_plots(df=sensor_data, save_path=save_path)
    log.info("Command: Done")
    send_visualization_email(df=sensor_data, path_to_pdf=save_path, receiver=commander)


def create_visualization_timed():
    log.info("Timed: Creating Measurement Data Visualization")
    sensor_data = _get__visualization_data()
    draw_plots(df=sensor_data)
    log.info("Timed: Done")
    send_visualization_email(df=sensor_data)


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
    room_temp, humidity, timestamp = get_sensor_data(int(hometemp_config()["sensor_pin"]), True)
    if room_temp is not None or humidity is not None or timestamp is not None:
        log.info(
            "[Measurement {0}] CPU={1:f}*C, Room={2:f}*C, Humidity={3:f}%".format(timestamp, cpu_temp, room_temp,
                                                                                  humidity))
        handler.insert_measurements_into_db(timestamp=timestamp, humidity=humidity, room_temp=room_temp,
                                            cpu_temp=cpu_temp)
        # heat warning
        max_heat = 28.5
        if room_temp > max_heat:
            log.warning(f"Sending heat warning because room temp is above {max_heat}°C")
            send_heat_warning_email(room_temp)

    log.info("Done")


def main():
    log.info(f"------------------- HomeTemp v{hometemp_config()['version']} -------------------")
    if not init_postgres_container(database_config()):
        log.error("Postgres container startup error! Shutting down ...")
        exit(1)
        # after restart, database needs some time to start
    time.sleep(1)

    picture_cmd_name = 'pic'
    picture_fun_params = ['commander']
    command_service.add_new_command((picture_cmd_name, [], _take_picture_commanded, picture_fun_params))
    vis_cmd_name = 'plot'
    vis_fun_params = ['commander']
    command_service.add_new_command((vis_cmd_name, [], _create_visualization_commanded, vis_fun_params))

    schedule.every(10).minutes.do(collect_and_save_to_db)
    schedule.every().day.at("11:45").do(run_threaded, create_visualization_timed)
    schedule.every().day.at("19:00").do(run_threaded, take_picture_timed)
    schedule.every().day.at("03:00").do(run_threaded, take_picture_timed)
    schedule.every().day.at("10:30").do(run_threaded, take_picture_timed)
    schedule.every(17).minutes.do(run_threaded, run_received_commands)

    log.info("finished initialization")

    collect_and_save_to_db()
    # create_visualization_timed()
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
