import configparser
import os
from configparser import SectionProxy
from typing import Optional

# ----------------------------------------------------------------------------------------------------------------
# Configuration management module
# ----------------------------------------------------------------------------------------------------------------
config: Optional[configparser.ConfigParser] = None


def load_config(config_file: str = 'hometemp.ini') -> None:
    """
    Load the configuration from the specified file.

    Args:
        config_file (str): Path to the configuration file. Defaults to 'hometemp.ini'.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
    """
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Configuration file '{config_file}' not found.")
    global config
    config = configparser.ConfigParser()
    config.read(config_file)
    return None


def hometemp_config() -> SectionProxy:
    used_key = 'hometemp'
    _validate_config(used_key)
    return config[used_key]


def database_config() -> SectionProxy:
    used_key = 'db'
    _validate_config(used_key)
    return config[used_key]


def distribution_config() -> SectionProxy:
    used_key = 'distribution'
    _validate_config(used_key)
    return config[used_key]


def dwd_config() -> SectionProxy:
    used_key = 'dwd'
    _validate_config(used_key)
    return config[used_key]


def google_config() -> SectionProxy:
    used_key = 'google'
    _validate_config(used_key)
    return config[used_key]


def wettercom_config() -> SectionProxy:
    used_key = 'wettercom'
    _validate_config(used_key)
    return config[used_key]


def _validate_config(used_key: str, used_key_present_error: bool = True) -> None:
    """
    Validate that the configuration has been loaded and the specified section exists.

    Args:
        used_key (str): The key of the section to validate.
        used_key_present_error (bool): Whether to raise an error if the section is missing. Defaults to True.

    Raises:
        RuntimeError: If configuration has not been loaded.
        KeyError: If the specified section is not found.
    """
    if config is None:
        raise RuntimeError("Configuration has not been loaded. Call 'load_config()' first.")
    if used_key_present_error and used_key not in config:
        raise KeyError(f"No '{used_key}' section found in the configuration.")
