import configparser, logging, re, schedule, time, threading
from datetime import datetime, timedelta
from gpiozero import CPUTemperature
from distribute.email import EmailDistributor
from distribute.command import CommandService
from persist.database import SensorDataHandler
from util.manager import PostgresDockerManager
from visualize.plots import draw_plots
from sensors.dht import DHT, DHTResult
from sensors.camera import RpiCamController

# only logs from this file will be written to console but all logs will be saved to file
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(filename='measurement.log',
                    encoding='utf-8',
                    level=logging.INFO)
config = configparser.ConfigParser()
config.read('hometemp.ini')
log = logging.getLogger('basetemp')

command_service = None


# ------------------------------- Raspberry Pi Temps ----------------------------------------------

def get_temperature():
    cpu = CPUTemperature()
    return float(cpu.temperature)


def get_sensor_data(used_pin):
    """
    Returns temperature and humidity data measures by DHT11 Sensor and the measurement timestamp.
    """
    max_tries = 20
    tries = 0
    DHT_SENSOR = DHT(used_pin, True)
    while True:
        if tries >= max_tries:
            log.error(f"Failed to retrieve data from DHT11 sensor: Maximum retries reached.")
            break
        else:
            time.sleep(2)
            result = DHT_SENSOR.read()
            if result.error_code == DHTResult.ERR_NOT_FOUND:
                tries += 1
                log.warning(f"({tries}/{max_tries}) Sensor could not be found. Using correct pin?")
                # maybe exit here but invastige when this error occurs (should never)
                continue
            elif not result.is_valid():
                tries += 1
                log.warning(f"({tries}/{max_tries}) Sensor data invalid")
                continue
            elif result.is_valid() and result.error_code == DHTResult.ERR_NO_ERROR:
                # postgres expects timestamp ins ISO 8601 format
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                return result.temperature, result.humidity, timestamp
    
    return None, None, None


def _get__visualization_data():
    auth = config["db"]
    sensor_data_handler = SensorDataHandler(auth['db_port'], auth['db_host'], auth['db_user'], auth['db_pw'],
                                            'sensor_data')
    sensor_data_handler.init_db_connection(check_table=False)
    # sensor data
    df = sensor_data_handler.read_data_into_dataframe()
    df = df.sort_values(by="timestamp")
    df['timestamp'] = df['timestamp'].map(lambda x: datetime.strptime(str(x).replace("+00:00","").strip(), '%Y-%m-%d %H:%M:%S'))
    
    return df


# ------------------------------- Main  ----------------------------------------------

def _take_picture(name, encoding = "png"):
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
        EmailDistributor().send_picture_email(picture_path=f"{save_path}.{encoding}", df=sensor_data, receiver=commander)
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
    EmailDistributor().send_visualization_email(df=sensor_data, path_to_pdf=save_path, receiver=commander)

def create_visualization_timed():
    log.info("Timed: Creating Measurement Data Visualization")
    sensor_data = _get__visualization_data()
    draw_plots(df=sensor_data)
    log.info("Timed: Done")
    EmailDistributor().send_visualization_email(df=sensor_data)


def run_received_commands():
    log.info("Checking for commands")
    command_service.receive_and_execute_commands()
    log.info("Done")

def run_threaded(job_func):
    job_thread = threading.Thread(target=job_func)
    job_thread.start()


def collect_and_save_to_db():
    log.info("Start Measurement Data Collection")
    auth = config["db"]
    handler = SensorDataHandler(auth['db_port'], auth['db_host'], auth['db_user'], auth['db_pw'], 'sensor_data')
    handler.init_db_connection()
    cpu_temp = get_temperature()
    room_temp, humidity, timestamp = get_sensor_data(int(config["hometemp"]["sensor_pin"]))
    if room_temp is not None or humidity is not None or timestamp is not None:
        log.info(
            "[Measurement {0}] CPU={1:f}*C, Room={2:f}*C, Humidity={3:f}%".format(timestamp, cpu_temp, room_temp, humidity))
        handler.insert_measurements_into_db(timestamp=timestamp, humidity=humidity, room_temp=room_temp, cpu_temp=cpu_temp)
        # heat warning
        max_heat = 34.5
        if room_temp > max_heat:
            log.warning(f"Sending heat warning because room temp is above {max_heat}°C")
            EmailDistributor().send_heat_warning_email(room_temp)

    log.info("Done")


def init_postgres_container():
    log.info("Checking for existing database")
    auth = config["db"]
    docker_manager = PostgresDockerManager(auth["db_name"], auth["db_user"], auth["db_pw"])
    container_name = auth["container_name"]
    if docker_manager.container_exists(container_name):
        log.info("Reusing existing database container")
        return docker_manager.start_container(container_name)
    else:
        log.info("No database container found. Creating database container")
        if docker_manager.pull_postgres_image():
            docker_manager.create_postgres_container(container_name)
            return docker_manager.start_container(container_name)

    return False


def main():
    log = logging.getLogger('hometemp')
    log.addHandler(logging.StreamHandler())
    log.info(f"------------------- HomeTemp v{config['hometemp']['version']} -------------------")
    if not init_postgres_container():
        log.error("Postgres container startup error! Shutting down ...")
        exit(1)
        # after restart, database needs some time to start
    time.sleep(1)

    global command_service
    command_service = CommandService()
    picutre_cmd_name = 'pic'
    picutre_fun_params = ['commander']
    command_service.add_new_command((picutre_cmd_name, [], _take_picture_commanded, picutre_fun_params))
    vis_cmd_name = 'plot'
    vis_fun_params = ['commander']
    command_service.add_new_command((vis_cmd_name, [], _create_visualization_commanded, vis_fun_params))

    schedule.every(10).minutes.do(collect_and_save_to_db)
    schedule.every().day.at("06:07").do(run_threaded, create_visualization_timed)
    schedule.every().day.at("08:00").do(run_threaded, take_picture_timed)
    schedule.every().day.at("12:00").do(run_threaded, take_picture_timed)
    schedule.every().day.at("15:00").do(run_threaded, take_picture_timed)
    schedule.every().day.at("18:30").do(run_threaded, take_picture_timed)
    schedule.every(17).minutes.do(run_threaded, run_received_commands)
    
    log.info("finished initialization")

    collect_and_save_to_db()
    #create_visualization_timed()
    time.sleep(1)
    #take_picture_timed()
    run_received_commands()
    log.info("entering main loop")
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()