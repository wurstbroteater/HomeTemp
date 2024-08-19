import adafruit_dht, board, configparser, logging, re, schedule, time, threading
from datetime import datetime, timedelta
from gpiozero import CPUTemperature
from distribute.email import EmailDistributor
from distribute.command import CommandService
from persist.database import DwDDataHandler, GoogleDataHandler, UlmDeHandler, SensorDataHandler, WetterComHandler
from util.manager import PostgresDockerManager
from visualize.plots import draw_plots

# only logs from this file will be written to console but all logs will be saved to file
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(filename='measurement.log',
                    encoding='utf-8',
                    level=logging.INFO)
config = configparser.ConfigParser()
config.read('hometemp.ini')
log = logging.getLogger('hometemp')

command_service = None


# ------------------------------- Raspberry Pi Temps ----------------------------------------------

def get_temperature():
    cpu = CPUTemperature()
    return float(cpu.temperature)


def get_sensor_data():
    """
    Returns temperature and humidity data measures by AM2302 Sensor and the measurement timestamp.
    """
    DHT_SENSOR = adafruit_dht.DHT22(board.D2)
    max_tries = 10
    tries = 0
    while tries < max_tries:
        if tries >= max_tries:
            log.error(f"Failed to retrieve data from AM2302 sensor: Maximum retries reached.")
            break 

        try:
            # postgres expects timestamp ins ISO 8601 format
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            temp = DHT_SENSOR.temperature
            hum = DHT_SENSOR.humidity
            DHT_SENSOR.exit()
            if temp is None or hum is None: 
                log.error(f"Retrieved none values from AM2302 sensor")
                break  
            else:
                return temp, hum, timestamp
        except RuntimeError as error:
            # Errors happen fairly often, DHT's are hard to read.
            # Here, RuntimeError usually suggests to retry it.
            tries += 1
            log.warning(f"({tries} / {max_tries}) RuntimeError while reading sensor data: {error.args[0]}")
            time.sleep(2.0)
            continue
        except Exception as error:
            DHT_SENSOR.exit()
            log.error(f"Failed to retrieve data from AM2302 sensor: {error}")
            break

    return None, None, None


def _get__visualization_data():
    auth = config["db"]
    sensor_data_handler = SensorDataHandler(auth['db_port'], auth['db_host'], auth['db_user'], auth['db_pw'],
                                            'sensor_data')
    sensor_data_handler.init_db_connection(check_table=False)
    # sensor data
    df = sensor_data_handler.read_data_into_dataframe()
    df = df.sort_values(by="timestamp")
    df['timestamp'] = df['timestamp'].map(lambda x: datetime.strptime(str(x).strip(), '%Y-%m-%d %H:%M:%S'))
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
    ulmde_df['timestamp'] = ulmde_df['timestamp'].map(lambda x: datetime.strptime(str(x).strip().replace('+00:00', ''), '%Y-%m-%d %H:%M:%S'))

    return (df, google_df, dwd_df, wettercom_df, ulmde_df)


# ------------------------------- Main  ----------------------------------------------

def _create_visualization_commanded(commander):
    log.info("Command: Creating Measurement Data Visualization")
    sensor_data, google_df, dwd_df, wettercom_df, ulmde_df = _get__visualization_data()
    
    name = datetime.now().strftime("%d-%m-%Y")
    save_path = f"plots/commanded/{name}.pdf"
    draw_plots(df=sensor_data, google_df=google_df, dwd_df=dwd_df, wettercom_df=wettercom_df, ulmde_df=ulmde_df, save_path=save_path)
    log.info("Command: Done")
    EmailDistributor().send_visualization_email(df=sensor_data, ulmde_df=ulmde_df, google_df=google_df, dwd_df=dwd_df, wettercom_df=wettercom_df, path_to_pdf=save_path, receiver=commander)

def create_visualization_timed():
    log.info("Timed: Creating Measurement Data Visualization")
    sensor_data, google_df, dwd_df, wettercom_df, ulmde_df = _get__visualization_data()
    draw_plots(df=sensor_data, google_df=google_df, dwd_df=dwd_df, wettercom_df=wettercom_df, ulmde_df=ulmde_df)
    log.info("Timed: Done")
    EmailDistributor().send_visualization_email(df=sensor_data, ulmde_df=ulmde_df, google_df=google_df, dwd_df=dwd_df, wettercom_df=wettercom_df)

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
    room_temp, humidity, timestamp = get_sensor_data()
    if room_temp is not None and humidity is not None and timestamp is not None:
        log.info(
            "[Measurement {0}] CPU={1:f}*C, Room={2:f}*C, Humidity={3:f}%".format(timestamp, cpu_temp, room_temp, humidity))
        handler.insert_measurements_into_db(timestamp=timestamp, humidity=humidity, room_temp=room_temp, cpu_temp=cpu_temp)
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
    main()
