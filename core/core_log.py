import logging
import logging.config

# ----------------------------------------------------------------------------------------------------------------
# TODO: Docu
# setup_logging() should be used in main
# get_logger should be used in modules to register to logging
# ----------------------------------------------------------------------------------------------------------------


def setup_logging(log_file: str = 'app.log', logging_level: int = logging.INFO) -> None:
    """
    Configure logging to file and console, assures utf-8 file encoding and uses basic logging format.

    Args:
        log_file (str): Path to the log file. Defaults to 'app.log'.
        logging_level (int): Logging level to set. Defaults to logging.INFO.
    """
    # Root logger
    logger = logging.getLogger()
    logger.setLevel(logging_level)

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging_level)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging_level)

    # Create a formatter and set it for both handlers
    formatter = logging.Formatter(logging.BASIC_FORMAT)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add the handlers to the logger but prevent adding handlers multiple times
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)


def get_logger(module_name: str) -> logging.Logger:
    """
    Get a logger for the specified module name.

    Args:
        module_name (str): The name of the module for which to get a logger.

    Returns:
        logging.Logger: The logger for the specified module.
    """
    return logging.getLogger(module_name)
