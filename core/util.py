from core.core_log import get_logger
import cv2
import os
from datetime import datetime

log = get_logger(__name__)


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
