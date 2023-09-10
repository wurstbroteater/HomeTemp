from persistence_logger import per_log as log
from sqlalchemy import create_engine, text, insert, inspect, exc, Table, Column, MetaData, Integer, DECIMAL, TIMESTAMP
from abc import ABC, abstractmethod
import pandas as pd

class DatabaseHandler(ABC):
    """
    Abstract method for default database Create/Delete/Sanitize methods and initialization of a postgres database.
    Insert methods should be implemented by the extending class because it might get to complex to provide a default.
    """

    def __init__(self, port, host, user, password, table):
        self.port = port
        self.host = host
        self.user = user
        self.password = password
        self.table = table
        self.connection = self._init_db()
        super().__init__()

    def _init_db(self):
        db_url = f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.table}"
        try:
            return create_engine(db_url)
        except exc.SQLAlchemyError as e:
            log.error("Problems while initialising database access: " + str(e))

    
    @abstractmethod
    def _create_table(self):
        pass

    @abstractmethod
    def _remove_table(self):
       pass

    @abstractmethod
    def _clear_table(self):
        pass

    @abstractmethod
    def _get_table_size(self):
        return -1   
      
    @abstractmethod
    def _check_table_existence(self):
        return False


class SensorDataHandler(DatabaseHandler):
    """
    Implementation of DatabaseHandler for table 'sensor_data'.
    Assures table structure and creates
    """

    # ------ implementation of abstract methods ------
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


    # ------ implementation of additional and public methods ------
    def init_db_connection(self):
        """
        Establish the connection to postgres database and creates table it not existent.
        """
        try:
            con = self._init_db()
            log.info("Connected to the database!")
            if not self._check_table_existence():
               self._create_table()
            return con
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


    def read_data_into_dataframe(self):
        try:
            df = pd.read_sql(f"SELECT * FROM {self.table}", self.connection)
            return df

        except exc.SQLAlchemyError as e:
            log.error("Problem with database " + str(e))
            return None
