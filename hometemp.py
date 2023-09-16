import Adafruit_DHT, configparser, logging, re, schedule, time, threading
from datetime import datetime, timedelta
from gpiozero import CPUTemperature
from distribute.email import EmailDistributor
from persist.database import DwDDataHandler, GoogleDataHandler, PostgresHandler, SensorDataHandler, WetterComHandler
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


# ------------------------------- Raspberry Pi Temps ----------------------------------------------

def get_temperature():
    cpu = CPUTemperature()
    return float(cpu.temperature)


def get_sensor_data():
    """
    Returns temperature and humidity data measures by AM2302 Sensor and the measure timestamp or raise exception 
    if the values could not be retrieved
    """
    DHT_SENSOR = Adafruit_DHT.AM2302
    DHT_PIN = 2
    humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)

    if humidity is not None and temperature is not None:
        # postgres expects timestamp ins ISO 8601 format
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return temperature, humidity, timestamp
    else:
        raise Exception("Failed to retrieve data from AM2302 sensor")


# ------------------------------- Main  ----------------------------------------------

def create_and_backup_visualization():
    log.info("Creating Measurement Data Visualization")
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
    wettercom_handler = WetterComHandler(auth['db_port'], auth['db_host'], auth['db_user'], auth['db_pw'], 'wettercom_data')
    wettercom_handler.init_db_connection()
    wettercom_df = wettercom_handler.read_data_into_dataframe()
    wettercom_df['timestamp'] = wettercom_df['timestamp'].map(lambda x: datetime.strptime(str(x).strip().replace('+00:00', ''), '%Y-%m-%d %H:%M:%S'))
    
    draw_plots(df, google_df=google_df, dwd_df=dwd_df, wettercom_df=wettercom_df)
    log.info("Done")
    EmailDistributor.send_visualization_email(df, google_df=google_df, dwd_df=dwd_df, wettercom_df=wettercom_df)


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
    schedule.every(10).minutes.do(collect_and_save_to_db)
    # run_threaded assumes that we never have overlapping usage of this method or its components
    schedule.every().day.at("06:00").do(run_threaded, create_and_backup_visualization)
    log.info("finished initialization")

    collect_and_save_to_db()
    run_threaded(create_and_backup_visualization)
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
