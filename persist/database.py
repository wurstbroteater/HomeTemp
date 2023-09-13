from persist.persistence_logger import per_log as log
from sqlalchemy import create_engine, text, select, update, insert, inspect, exc, Table, Column, MetaData, Integer, \
    DECIMAL, \
    TIMESTAMP
from abc import ABC, abstractmethod
import pandas as pd


class PostgresHandler(ABC):
    """
    Abstract class for initializing the Postgres database. It provides methods for the initialization, removal of the
    table itself, or its content as well as checking for table existence or how many rows the table has.
    It does not provide a default method for inserting data into the table.

    @Impl
    _create_table needs to be implemented in EVERY extending class.
    """

    def __init__(self, port, host, user, password, table):
        self.port = port
        self.host = host
        self.user = user
        self.password = password
        self.table = table
        self.connection = None
        super().__init__()

    @abstractmethod
    def _create_table(self):
        pass

    def init_db_connection(self, check_table=True):
        """
        Establish the connection to the Postgres database.
        If the check_table flag is true, it checks if the table in 'self.table' exists in the database and
        if not, the table is created.
        """
        try:
            if self.connection is None:
                self.connection = self._init_db()
            log.debug("Connected to the database!")
            if check_table and not self._check_table_existence():
                self._create_table()
        except exc.SQLAlchemyError as e:
            log.error("Problem with database " + str(e))

    def _init_db(self):
        db_url = f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}"
        try:
            return create_engine(db_url)
        except exc.SQLAlchemyError as e:
            log.error("Problems while initialising database access: " + str(e))

    def _remove_table(self):
        try:
            table = Table(self.table, MetaData(), autoload_with=self.connection)
            with self.connection.begin() as con:
                table.drop(con)
                log.info(f"Table '{self.table}' removed successfully.")

        except exc.SQLAlchemyError as e:
            log.error("Problem with database " + str(e))

    def _clear_table(self):
        try:
            table = Table(self.table, MetaData(), autoload_with=self.connection)
            with self.connection.begin() as con:
                con.execute(table.delete())
                log.info(f"Table '{self.table}' cleared successfully.")

        except exc.SQLAlchemyError as e:
            log.error("Problem with database " + str(e))

    def _get_table_size(self):
        try:
            with self.connection.connect() as con:
                result = con.execute(text(f"SELECT COUNT(*) FROM {self.table}"))
                return int(result.scalar())

        except exc.SQLAlchemyError as e:
            log.error("Problem with database " + str(e))
            return -1

    def _check_table_existence(self):
        try:
            return inspect(self.connection).has_table(self.table)

        except exc.SQLAlchemyError as e:
            log.error("Problem with database " + str(e))
            return False

    def read_data_into_dataframe(self):
        try:
            df = pd.read_sql(f"SELECT * FROM {self.table}", self.connection)
            return df

        except exc.SQLAlchemyError as e:
            log.error("Problem with database " + str(e))
            return None


class SensorDataHandler(PostgresHandler):
    """
    Implementation of PostgresHandler with table schema for sensor_data.
    In addition, it provides a method for inserting measurement data into the table.
    """

    def _create_table(self):
        metadata = MetaData()
        table_schema = Table(self.table, metadata,
                             Column('id', Integer, primary_key=True, autoincrement=True),
                             Column('timestamp', TIMESTAMP(timezone=True), nullable=False),
                             Column('humidity', DECIMAL, nullable=False),
                             Column('room_temp', DECIMAL, nullable=False),
                             Column('cpu_temp', DECIMAL, nullable=False))
        try:
            metadata.create_all(self.connection)
            log.info(f"Table '{self.table}' created successfully.")

        except exc.SQLAlchemyError as e:
            log.error("Problem with database " + str(e))

    def insert_measurements_into_db(self, timestamp, humidity, room_temp, cpu_temp):
        try:
            table = Table(self.table, MetaData(), autoload_with=self.connection, extend_existing=True)
            with self.connection.begin() as con:
                data_to_insert = {
                    'timestamp': timestamp,
                    'humidity': humidity,
                    'room_temp': room_temp,
                    'cpu_temp': cpu_temp
                }
                insert_statement = insert(table).values(**data_to_insert)
                con.execute(insert_statement)

        except exc.SQLAlchemyError as e:
            log.error("Problem with database " + str(e))


class DwDDataHandler(PostgresHandler):
    """
    Implementation of PostgresHandler with table schema for data from Deutsche Wetterdienst (DWD).
    In addition, it provides a method for inserting data into the table.
    """

    def _create_table(self):
        metadata = MetaData()
        table_schema = Table(self.table, metadata,
                             Column('id', Integer, primary_key=True, autoincrement=True),
                             Column('timestamp', TIMESTAMP(timezone=True), nullable=False),
                             Column('temp', DECIMAL, nullable=False),
                             Column('temp_dev', DECIMAL, nullable=False))
        try:
            metadata.create_all(self.connection)
            log.info(f"Table '{self.table}' created successfully.")

        except exc.SQLAlchemyError as e:
            log.error("Problem with database " + str(e))

    def row_exists_with_timestamp(self, timestamp_value):
        try:
            table = Table(self.table, MetaData(), autoload_with=self.connection)
            with self.connection.connect() as con:
                select_statement = select(table).where(table.c.timestamp == timestamp_value)
                result = con.execute(select_statement)
                return result.fetchone() is not None

        except exc.SQLAlchemyError as e:
            log.error("Problem with database " + str(e))
            return False

    def insert_dwd_data(self, timestamp, temp, temp_dev):
        try:
            table = Table(self.table, MetaData(), autoload_with=self.connection, extend_existing=True)
            with self.connection.begin() as con:
                data_to_insert = {
                    'timestamp': timestamp,
                    'temp': temp,
                    'temp_dev': temp_dev
                }
                insert_statement = insert(table).values(**data_to_insert)
                con.execute(insert_statement)
                log.info("DWD data inserted successfully.")

        except exc.SQLAlchemyError as e:
            log.error("Problem with database " + str(e))

    def get_temp_for_timestamp(self, timestamp_to_check):
        """
        For every timestamp there is exactly one temperature value. This method returns the
        temperature value of a row identified by its timestamp or None.
        """

        try:
            table = Table(self.table, MetaData(), autoload_with=self.connection, extend_existing=True)
            with self.connection.connect() as con:
                select_statement = select(table.c.temp).where(table.c.timestamp == timestamp_to_check)
                result = con.execute(select_statement)
                row = result.fetchone()
                if row is not None:
                    return float(row[0])
                else:
                    log.warn(f"No row with timestamp {timestamp_to_check} found in the table.")

        except exc.SQLAlchemyError as e:
            log.error("Problem with database " + str(e))

        return None

    def update_temp_by_timestamp(self, timestamp_to_check, new_temp_value, new_temp_dev):
        """
        Search row based on timestamp and update their temp and temp_dev value only if 
        the old and new temp values or not equal.

        returns True if the value was updated otherwise False.
        """
        try:
            table = Table(self.table, MetaData(), autoload_with=self.connection, extend_existing=True)
            with self.connection.begin() as con:
                old_temp_value = self.get_temp_for_timestamp(timestamp_to_check)
                if old_temp_value is not None and old_temp_value != new_temp_value:
                    con.execute(
                        update(table).where(table.c.timestamp == timestamp_to_check).values(temp=new_temp_value,
                                                                                            temp_dev=new_temp_dev))
                    log.info(
                        f"Row with timestamp {timestamp_to_check} updated with new temp value {new_temp_value}°C and dev {new_temp_dev}")
                    return True
                else:
                    log.info(f"Row with timestamp {timestamp_to_check} not updated; values are equal.")

        except exc.SQLAlchemyError as e:
            log.error("Problem with database " + str(e))

        return False


class GoogleDataHandler(PostgresHandler):
    """
    Implementation of PostgresHandler with table schema for data from Google Weather.
    In addition, it provides a method for inserting data into the table.
    """

    def _create_table(self):
        metadata = MetaData()
        # humidity, precipitation are % values and wind is in km/h
        table_schema = Table(self.table, metadata,
                             Column('id', Integer, primary_key=True, autoincrement=True),
                             Column('timestamp', TIMESTAMP(timezone=True), nullable=False),
                             Column('temp', DECIMAL, nullable=False),
                             Column('humidity', DECIMAL, nullable=False),
                             Column('precipitation', DECIMAL, nullable=False),
                             Column('wind', DECIMAL, nullable=False))
        try:
            metadata.create_all(self.connection)
            log.info(f"Table '{self.table}' created successfully.")

        except exc.SQLAlchemyError as e:
            log.error("Problem with database " + str(e))

    def row_exists_with_timestamp(self, timestamp_value):
        try:
            table = Table(self.table, MetaData(), autoload_with=self.connection)
            with self.connection.connect() as con:
                select_statement = select(table).where(table.c.timestamp == timestamp_value)
                result = con.execute(select_statement)
                return result.fetchone() is not None

        except exc.SQLAlchemyError as e:
            log.error("Problem with database " + str(e))
            return False

    def insert_google_data(self, timestamp, temp, humidity, precipitation, wind):
        try:
            table = Table(self.table, MetaData(), autoload_with=self.connection, extend_existing=True)
            with self.connection.begin() as con:
                data_to_insert = {
                    'timestamp': timestamp,
                    'temp': temp,
                    'humidity': humidity,
                    'precipitation': precipitation,
                    'wind': wind
                }
                insert_statement = insert(table).values(**data_to_insert)
                con.execute(insert_statement)
                log.info("Google Weather data inserted successfully.")

        except exc.SQLAlchemyError as e:
            log.error("Problem with database " + str(e))
