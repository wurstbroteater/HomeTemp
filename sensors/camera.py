from sensors.sensor_logger import sen_log as log
import subprocess

class RpiCamController:
    """
    Wrapper for rpicam-apps used in Raspberry Pi 5 (and 4B?) 
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
        if no callback is given then  dictionary with output, return code, and error (if any).
        Otherwise, it returns the output of the usedon_success or on_success function.
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

    def capture_image(self, filename: str = "test", encoding: str = "png") -> bool:

        if encoding not in self.supported_image_endcodings:
            print(f"Unsupported image encoding {encoding} found. Supported are {self.supported_image_endcodings}")
            return False
        command = ['rpicam-still',
                   '--encoding', encoding,
                   '--output', f"{filename}.{encoding}"]
        return self._run_command(command, on_success=lambda _: True, on_failure=lambda error_msg: (log.error(f"Error while capturing picture: {error_msg}"), False)[1])

    def get_version(self) -> str:
        command = ['rpicam-hello', '--version']
        return self._run_command(command)