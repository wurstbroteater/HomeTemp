from typing import Type
import time
from configparser import SectionProxy
from core.database import PostgresHandler
from core.virtualization import init_postgres_container
from core.core_log import get_logger

log = get_logger(__name__)

# ----------------------------------------------------------------------------------------------------------------
# The core utility module which provides utility methods for using core functionalities.
# Should be used if two or more core components need to work together.
# ----------------------------------------------------------------------------------------------------------------

def init_database(handler_type: Type[PostgresHandler], database_auth: SectionProxy, table_name: str, timelimit_sec: int = 30):
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

    if not init_postgres_container(database_auth):
        log.error("Postgres container startup error! Shutting down ...")
        exit(1)

    handler: PostgresHandler = handler_type(database_auth['db_port'], database_auth['db_host'], database_auth['db_user'], database_auth['db_pw'], table_name)
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
