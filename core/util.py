import os, socket
from datetime import datetime
from functools import wraps
from typing import Callable, Any

import cv2

from core.core_configuration import PICTURE_NAME_FORMAT
from core.core_log import get_logger

log = get_logger(__name__)


# ----------------------------------------------------------------------------------------------------------------
# The python utility module which provides utility methods for code not using any core internal datastructures.
# Should only be used for imported python frameworks.
# ----------------------------------------------------------------------------------------------------------------

def create_timelapse(input_folder: str, output_video_path: str, image_encoding="png", fps: int = 2) -> None:
    # List to store the image file paths
    image_files = []
    image_encoding = "." + image_encoding
    for filename in os.listdir(input_folder):
        if filename.endswith(image_encoding):
            try:
                datetime.strptime(str(filename).replace(image_encoding, ""), PICTURE_NAME_FORMAT)
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
        with socket.create_connection((host, port)):
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
