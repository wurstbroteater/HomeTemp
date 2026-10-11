from datetime import datetime
import time
import pandas as pd
from typing import Optional, Tuple, Type
from configparser import SectionProxy
from gpiozero import CPUTemperature
from core.sensors.dht import get_sensor_data
from core.database import PostgresHandler, SensorDataHandler, TIME_FORMAT
from core.plotting import SupportedDataFrames
from core.sensors.camera import RpiCamController
from core.core_log import get_logger

log = get_logger(__name__)


# ----------------------------------------------------------------------------------------------------------------
# The core utility module which provides utility methods for using core functionalities.
# Should be used if two or more core components need to work together.
# ----------------------------------------------------------------------------------------------------------------

def get_cpu_temperature() -> float:
    cpu = CPUTemperature()
    return float(cpu.temperature)


def init_database(handler_type: Type[PostgresHandler], database_auth: SectionProxy, table_name: str,
                  timelimit_sec: int = 30):
    """
    Initializes a PostgreSQL database handler and waits until the database is ready for transactions.

    Parameters:
        handler_type (Type[PostgresHandler]): The class type of the database handler (must be a subclass of PostgresHandler).
        database_auth (SectionProxy): Authentication configuration containing database credentials (port, host, user, password).
        table_name (str): Name of the database table to be managed.
        timelimit_sec (int, optional): Maximum time in seconds to wait for the database to be ready. Defaults to 30.

    Raises:
        SystemExit: If the database container fails to start or the database is not ready within the time limit.
    """

    handler: PostgresHandler = handler_type(database_auth['db_port'], database_auth['db_host'],
                                            database_auth['db_user'], database_auth['db_pw'], table_name)
    is_ready = handler.is_db_ready()

    passed_seconds = 0
    sleep_sec = 1
    log.info("Waiting for database to be ready...")

    while not is_ready:
        time.sleep(sleep_sec)
        passed_seconds += sleep_sec

        if passed_seconds >= timelimit_sec:
            log.error(f"Database readiness timeout of {timelimit_sec}s reached! Shutting down...")
            handler.close()
            exit(1)

        is_ready = handler.is_db_ready()

    log.info(f"Database ready after {passed_seconds}s")
    handler.close()


def take_picture(name, encoding):
    rpi_cam = RpiCamController()
    # file name is set in capture_image to filepath.encoding which is png on default
    return rpi_cam.capture_image(file_path=name, encoding=encoding)


def get_data_for_plotting(database_auth: SectionProxy, handler_type: Type[PostgresHandler],
                          transformer: SupportedDataFrames) -> pd.DataFrame:
    handler: PostgresHandler = handler_type(database_auth['db_port'], database_auth['db_host'],
                                            database_auth['db_user'], database_auth['db_pw'], transformer.table_name)
    handler.init_db_connection(check_table=False)
    data = handler.read_data_into_dataframe()
    return transformer.prepare_data(data)

def retrieve_temp_data(sensor_pin: int ,is_dht11_sensor: bool) ->  Optional[Tuple]:
    room_temp, humidity = get_sensor_data(sensor_pin, is_dht11_sensor)
    if room_temp is None or humidity is None:
        return None
    return datetime.now().strftime(TIME_FORMAT), get_cpu_temperature(), room_temp, humidity

def save_temp_data_to_db(database_auth: SectionProxy,data: Optional[Tuple]) ->  Optional[Tuple]:

    if data is None:
        log.debug("No temp data to save to database")
        return None
    handler = SensorDataHandler(database_auth['db_port'], database_auth['db_host'], database_auth['db_user'],
                                database_auth['db_pw'], SupportedDataFrames.Main.table_name)
    handler.init_db_connection()

    timestamp, cpu_temp, room_temp, humidity = data
    if timestamp is not None and cpu_temp is not None and room_temp is not None and humidity is not None:
        handler.insert_measurements_into_db(timestamp=timestamp, humidity=humidity, room_temp=room_temp,
                                            cpu_temp=cpu_temp)
        return timestamp, cpu_temp, room_temp, humidity

    return None
