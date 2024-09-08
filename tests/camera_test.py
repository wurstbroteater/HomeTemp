from core.sensors.camera import RpiCamController
from datetime import datetime
from typing import Callable
import concurrent.futures
from PIL import Image

def run_in_background(func: Callable, *args, **kwargs) -> concurrent.futures.Future:
    """
    Runs a given function in a background thread using ThreadPoolExecutor.
    
    Args:
    - func: The function to run in the background.
    - *args: Positional arguments for the function.
    - **kwargs: Keyword arguments for the function.
    
    Returns:
    A concurrent.futures.Future object representing the execution of the function.
    """
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(func, *args, **kwargs)
    executor.shutdown(wait=False)
    return future


rpi_cam = RpiCamController()
version_result = rpi_cam.get_version()
#print(version_result)
print("start taking picture")
name = f'pictures/{datetime.now().strftime("%Y-%m-%d-%H:%M:%S")}'
print(f"BLOCKING Was sucessfull? {rpi_cam.capture_image(file_path=name)}")
#name = name + ".png"
#image = Image.open(name)
#rotated_image = image.rotate(90, expand=True)  # Rotate by 45 degrees, 'expand' to resize for the whole image
#rotated_image.save(name)


## Problem: when two threads run at the same time, only one finishes
#future = run_in_background(RpiCamController().capture_image, filename=name)
#name1 = f'pictures/commanded/{datetime.now().strftime("%Y-%m-%d-%H:%M:%S")}'
#future1 = run_in_background(RpiCamController().capture_image, filename=name1)
#print("The image is being captured in the background...")
