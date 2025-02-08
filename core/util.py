import os, socket, shutil
from datetime import datetime
from functools import wraps
from typing import Callable, Any, Optional, List, Literal
from pathlib import Path

import cv2

from core.core_log import get_logger

log = get_logger(__name__)


# ----------------------------------------------------------------------------------------------------------------
# The python utility module which provides utility methods for code not using any core internal datastructures.
# Should only be used for imported python frameworks.
# ----------------------------------------------------------------------------------------------------------------

class FileManager:
    def __init__(self, base_path: str, permissions: int = 0o755) -> None:
        self.base_path = Path(base_path).resolve()
        self.permissions = permissions

        # Ensure the base directory exists
        self.create_folder("", create_if_not_exists=True)

    def _resolve_path(self, path: str) -> Path:
        """Resolves a path relative to base_path if not absolute."""
        return self.base_path / path if not Path(path).is_absolute() else Path(path)

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
        """Creates a default folder structure."""
        for folder in structure:
            self.create_folder(folder, create_if_not_exists=True)

    def create_file(
        self, path: str, content: str = "", create_folders: bool = True, exist_behavior: Literal["overwrite", "skip"] = "overwrite"
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
                self.create_folder(file_path.parent, create_if_not_exists=True)

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
                self.create_folder(file_path.parent, create_if_not_exists=True)

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



def create_timelapse(input_folder: str, output_video_path: str, image_encoding="png", fps: int = 2) -> None:
    # List to store the image file paths
    image_files = []
    image_encoding = "." + image_encoding
    for filename in os.listdir(input_folder):
        if filename.endswith(image_encoding):
            try:
                datetime.strptime(str(filename).replace(image_encoding, ""), '%Y-%m-%d-%H:%M:%S')
                image_files.append(os.path.join(input_folder, filename))
            except ValueError:
                log.info(f"Skipping file: {filename}, invalid date format")
    # Sort based on the timestamp
    image_files.sort()

    if len(image_files) > 0:
        # Read the first image to get the dimensions
        frame = cv2.imread(image_files[0])
        height, width, layers = frame.shape
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
        for image_file in image_files:
            img = cv2.imread(image_file)
            if img.shape[0] != height or img.shape[1] != width:
                # Resize image to match the first frame's dimensions
                img = cv2.resize(img, (width, height))
            video.write(img)
        video.release()
        log.info(f"Timelapse video saved as {output_video_path}")
    else:
        log.info("No valid images found.")


def web_access_available(host: str = "8.8.8.8", port: int = 53, timeout_s: float = 3.0) -> bool:
    try:
        socket.setdefaulttimeout(timeout_s) 
        with socket.create_connection((host,port)):
            return True
    except (OSError, socket.timeout, socket.error):
        return False



def require_web_access(f: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that prevents execution if no internet is available.

    Returns:
        A wrapped function that executes only if the web is available.
    """
    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not web_access_available():
            log.info(f"Skipping '{f.__name__}' due to no internet connection.")
            return None
        return f(*args, **kwargs)

    return wrapper