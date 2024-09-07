from sensors.sensor_logger import sen_log as log
# pip install pillow
from PIL import Image
import subprocess

# Dimension for 5MP Raspberry Pi camera module static image resolution default
DIMENSION_CAMERA_DEFAULT = (2592, 1944)
# Dimension for 1440 pixel, 4K
DIMENSION_4K = (2560, 1440)
# Dimension for 1080 pixel, Full HD
DIMENSION_FULL_HD = (1920, 1080)
# Dimension for 720 pixel, HD
DIMENSION_HD = (1280, 720)
# Dimension for 480 pixel, SD
DIMENSION_SD = (854, 480)


class RpiCamController:
    """
    Wrapper for rpicam-apps used in Raspberry 4B.
    Tested with 5MP Raspberry Pi camera module with an OV5647 sensor.
    https://www.raspberrypi.com/documentation/computers/camera_software.html#rpicam-apps
    """
    def __init__(self) -> None:
        # https://www.raspberrypi.com/documentation/computers/camera_software.html#encoding
        self.supported_image_endcodings = ["jpg", "png", "bmp", "rgb", "yuv420"]
        pass

    def _run_command(self, 
                    command, 
                    on_success=None,
                    on_failure=None):
        """
        Runs a command and executes custom actions based on the return code.
        
        Args:
        - command: List of command parts to be executed.
        - on_success: Callback function to execute on successful completion (return code 0).
        - on_failure: Callback function to execute on failure (non-zero return code).
        
        Returns:
        if no callback is given then a dictionary with output, return code, and error (if any).
        Otherwise, it returns the output of the used on_success or on_failure function.
        """
        result = subprocess.run(
            command, 
            # No excpetion on returncode != 0 to handle them by calling methods
            check=False,  
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        
        # Check the return code and call appropriate callbacks if provided
        if result.returncode == 0:
            if on_success:
                return on_success(result.stdout.decode())
            return {
                'output': result.stdout.decode(),
                'returncode': result.returncode,
                'error': None
            }
        else:
            if on_failure:
                return on_failure(result.stderr.decode())
            return {
                'output': None,
                'returncode': result.returncode,
                'error': result.stderr.decode()
            }
        
    def _rotate_image(self, image_path: str, rotation:int) -> bool:
        image = Image.open(image_path)
        # 'expand' to resize for the whole image
        rotated_image = image.rotate(rotation, expand=True) 
        rotated_image.save(image_path)
        return True

    def capture_image(self, file_path: str = "test", encoding: str = "png", rotation: int = 0, dimension:tuple[int] = None) -> bool:
        """
        file_path must be the path to the image without endcoding, e.g., /path/to/image and set endcoding to "png"
        results in internal usage of /path/to/image.png
        """
        if rotation < 0 or rotation > 360:
            log.error(f"Unsupported image rotation {rotation} found. Supported range is [0, 360]")
        if encoding not in self.supported_image_endcodings:
            log.error(f"Unsupported image encoding {encoding} found. Supported are {self.supported_image_endcodings}")
            return False
        file_name = f"{file_path}.{encoding}"
        command = ['rpicam-still',
                   '--encoding', encoding,
                   '--output',  file_name]
        if dimension is not None and len(dimension) == 2:
            if (width:= dimension[0]) >= 0 and (height:=dimension[1]) >= 0:
                log.info(f"Using dimension {dimension}")
                command += ['--width', str(width),
                            '--height', str(height)]
            else:
                log.error(f"Unsupported dimension {dimension}.")


        return self._run_command(command,
                                  on_success=lambda _: self._rotate_image(file_name, rotation),
                                  on_failure=lambda error_msg: (log.error(f"Error while capturing picture: {error_msg}"), False)[1])

    def get_version(self) -> str:
        command = ['rpicam-hello', '--version']
        return self._run_command(command)