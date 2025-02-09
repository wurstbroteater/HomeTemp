import configparser
import os
import shutil
from configparser import SectionProxy
from datetime import datetime
from pathlib import Path
from time import sleep
from typing import Optional, List, Literal, Tuple

from core.core_log import get_logger

log = get_logger(__name__)

# ----------------------------------------------------------------------------------------------------------------
# Configuration management module
# ----------------------------------------------------------------------------------------------------------------

config: Optional[configparser.ConfigParser] = None


def load_config(config_file: str = 'config.ini') -> None:
    """
    Load the configuration from the specified file.

    Args:
        config_file (str): Path to the configuration file. Defaults to 'config.ini'.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
    """
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Configuration file '{config_file}' not found.")
    global config
    config = configparser.ConfigParser()
    config.read(config_file)
    return None


def update_config(section: str, key: str, value: str, filename: str = "config.ini") -> None:
    """Updates the value and saves it in the ini file"""
    config[section][key] = value
    with open(filename, "w") as configfile:
        config.write(configfile)
    load_config(filename)


def hometemp_config() -> SectionProxy:
    used_key = 'hometemp'
    _validate_config(used_key)
    return config[used_key]


def basetemp_config() -> SectionProxy:
    used_key = 'basetemp'
    _validate_config(used_key)
    return config[used_key]


def update_active_schedule(new_value: str) -> None:
    update_config('basetemp', 'active_schedule', new_value)


def core_config() -> SectionProxy:
    used_key = 'core'
    _validate_config(used_key)
    return config[used_key]


def get_instance_name() -> str:
    return core_config()['instance'].lower().strip()


def get_sensor_type(supported_sensors: list) -> Optional[str]:
    out: str = core_config().get('sensor_type', '').lower().strip()
    if out not in supported_sensors:
        raise TypeError(f"Instance is configured with unsupported sensor type {out}")
    return out


def get_data_root() -> str:
    return core_config()['data_path'].lower().strip()


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


def backend_config() -> SectionProxy:
    used_key = 'backend'
    _validate_config(used_key, False)
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


## ----------------------------------------------------------------------------------------------------------------
# The FileManager is coupled to the configuration as it reads the root dir from the config.ini
# -----------------------------------------------------------------------------------------------------------------
PICTURE_NAME_FORMAT = "%Y-%m-%d-%H:%M:%S"
PLOT_NAME_FORMAT = "%d-%m-%Y"


class FileManager:
    _commanded_folder = "commanded"
    TIMED_PICTURES = "pictures"
    COMMANDED_PICTURES = f"{TIMED_PICTURES}/{_commanded_folder}"
    TIMED_PLOTS = "plots"
    COMMANDED_PLOTS = f"{TIMED_PLOTS}/{_commanded_folder}"
    DEFAULT_STRUCTURE = [COMMANDED_PICTURES, COMMANDED_PLOTS]

    def __init__(self, base_path: str, permissions: int = 0o755) -> None:

        self.base_path = Path(base_path).resolve()
        self.permissions = permissions

        # Ensure the base directory exists
        self.create_folder("", create_if_not_exists=True)

    def _resolve_path(self, path: str) -> Path:
        """Resolves a path relative to base_path if not absolute."""
        return self.base_path / path if not Path(path).is_absolute() else Path(path)

    # ------------------- General Utility Methods ---------------------------------------------
    def create_folder(self, path: str, create_if_not_exists: bool = True) -> None:
        """Creates a folder with optional subfolder creation.
        If `create_if_not_exists` is False, logs and skips if the folder doesn't exist."""
        folder_path = self._resolve_path(path)

        if folder_path.exists():
            return

        if create_if_not_exists:
            try:
                folder_path.mkdir(parents=True, exist_ok=True)
                folder_path.chmod(self.permissions)
                log.info(f"Created folder: {folder_path} with permissions {oct(self.permissions)}")
            except Exception as e:
                log.error(f"Failed to create folder {folder_path}: {e}")
        else:
            log.info(f"Skipped creating folder: {folder_path} (does not exist)")

    def create_structure(self, structure: List[str]) -> None:
        """Creates a folder structure."""
        for folder in structure:
            self.create_folder(folder, create_if_not_exists=True)

    def create_file(
            self, path: str, content: str = "", create_folders: bool = True,
            exist_behavior: Literal["overwrite", "skip"] = "overwrite"
    ) -> None:
        """Creates a file with configurable behavior if it already exists.

        Parameters:
            path (str): Path to the file.
            content (str): Content to write.
            create_folders (bool): Whether to create missing folders.
            exist_behavior (Literal["overwrite", "skip"]):
                - "overwrite" (default) overwrites the file if it exists.
                - "skip" does nothing if the file already exists.
        """
        file_path = self._resolve_path(path)

        try:
            if create_folders:
                self.create_folder(str(file_path.parent), create_if_not_exists=True)

            if file_path.exists() and exist_behavior == "skip":
                log.info(f"Skipped file creation: {file_path} (already exists)")
                return

            file_path.write_text(content)
            log.info(f"Created file: {file_path}")

        except Exception as e:
            log.error(f"Failed to create file {file_path}: {e}")

    def write_file(self, path: str, content: str, mode: str = "w", create_folders: bool = True) -> None:
        """Writes content to a file."""
        file_path = self._resolve_path(path)

        try:
            if create_folders:
                self.create_folder(str(file_path.parent), create_if_not_exists=True)

            with file_path.open(mode) as f:
                f.write(content)
            log.info(f"Wrote to file: {file_path}")
        except Exception as e:
            log.error(f"Failed to write to file {file_path}: {e}")

    def read_file(self, path: str) -> Optional[str]:
        """Reads content from a file."""
        file_path = self._resolve_path(path)

        try:
            content = file_path.read_text()
            log.info(f"Read file: {file_path}")
            return content
        except Exception as e:
            log.error(f"Failed to read file {file_path}: {e}")
            return None

    def delete_file(self, path: str) -> None:
        """Deletes a file if it exists."""
        file_path = self._resolve_path(path)

        try:
            if file_path.exists():
                file_path.unlink()
                log.info(f"Deleted file: {file_path}")
        except Exception as e:
            log.error(f"Failed to delete file {file_path}: {e}")

    def delete_folder(self, path: str) -> None:
        """Deletes a folder and its contents if it exists."""
        folder_path = self._resolve_path(path)

        try:
            if folder_path.exists():
                shutil.rmtree(folder_path)
                log.info(f"Deleted folder: {folder_path}")
        except Exception as e:
            log.error(f"Failed to delete folder {folder_path}: {e}")

    def list_files(self, path: str = "", pattern: str = "*") -> List[Path]:
        """Lists files in a folder matching a pattern."""
        folder_path = self._resolve_path(path)

        try:
            files = list(folder_path.glob(pattern))
            log.info(f"Listed files in {folder_path}: {files}")
            return files
        except Exception as e:
            log.error(f"Failed to list files in {folder_path}: {e}")
            return []

    # ----------------- Project Specific Utility Methods -------------------------------------------------------
    def root_data_structure(self) -> None:
        """Creates the default folder structure for data storage."""

        for folder in self.DEFAULT_STRUCTURE:
            self.create_folder(folder, create_if_not_exists=True)

    def picture_file_name(self, timed: bool, filename="", encoding="png") -> Tuple[str, str]:
        """
        Returns the absolute path to store a png file (default).
        filename is just name without extension.
        encoding is the target file exenstion.
        """
        root_path = str(self.base_path)
        filename = datetime.now().strftime(PICTURE_NAME_FORMAT) if filename == "" else filename
        if timed:
            return f"{root_path}/{self.TIMED_PICTURES}/{filename}", encoding
        return f"{root_path}/{self.COMMANDED_PICTURES}/{filename}", encoding

    def plot_file_name(self, timed: bool, filename="") -> str:
        """
        Returns the absolute path to store a pdf file.
        filename is just name without extension.
        """
        root_path = str(self.base_path)
        filename = datetime.now().strftime(PLOT_NAME_FORMAT) if filename == "" else filename
        encoding = ".pdf"
        if timed:
            return f"{root_path}/{self.TIMED_PICTURES}/{filename}{encoding}"
        return f"{root_path}/{self.COMMANDED_PICTURES}/{filename}{encoding}"


_file_manager: Optional[FileManager] = None


## ----------------------------------------------------------------------------------------------------------------
# Main Methods for initialization. This is a crucial part, as every module may depends on information
# from the config file and FileManager. As FileManger is coupled to the config file, the initialization()
# method assures the correct setup. However, it is crucial that core_log.setup_logging() was called 
# before accessing the initialization() metho
# -----------------------------------------------------------------------------------------------------------------


def set_file_manager(file_manager: FileManager) -> None:
    global _file_manager
    _file_manager = file_manager
    pass


def get_file_manager() -> FileManager:
    global _file_manager
    if _file_manager is None:
        log.info("Waiting for file manager to be initialized")
        max_attempts = 5
        attempts = 0

        while _file_manager is None:
            if attempts == max_attempts:
                raise RuntimeError(f"Failed to initialize file manager after {max_attempts} attempts")
            attempts += 1
            sleep(1)

        log.info(f"File manager initialized after {max_attempts} attempts")
    return _file_manager


def initialize() -> FileManager:
    """
    Loads the config.ini and sets up the file manager.
    core_log.setup_logging() has to be called before using this method!
    """
    load_config()
    set_file_manager(FileManager(get_data_root()))
    return get_file_manager()
