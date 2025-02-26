import queue
import socket
import threading
import time
from typing import Any, Generator

from core_configuration import load_config, backend_config
from core_log import setup_logging, get_logger

setup_logging()
load_config()
SERVER_HOST = backend_config()["ip"]
PORT = int(backend_config()["port"])
MAX_RETRIES = 3
RETRY_DELAY_S = 2
log = get_logger(__name__)


####
## THIS IS WORK IN PROGRESS; NOTHING FOR RELEASE!
####
def simulate_command_processing(command: str) -> Generator[str, Any, None]:
    """Simulate processing steps for the given command."""
    for step in ["processing", "command completed"]:
        time.sleep(5)
        log.info(str(step))
        yield step


class RequestProcessor:
    _instance: 'RequestProcessor' = None  # Class variable to hold the singleton instance

    def __new__(cls) -> 'RequestProcessor':
        # Assure Singleton usage
        if cls._instance is None:
            cls._instance = super(RequestProcessor, cls).__new__(cls)
            cls._instance.command_queue = queue.Queue()
            cls._instance.is_processing = False
            cls._instance.lock = threading.Lock()
        return cls._instance

    def add_command(self, command: str) -> None:
        """Add a new command to the queue."""
        self.command_queue.put(command)

    def process_commands(self, server_socket: socket.socket) -> None:
        """Process commands from the queue."""
        while True:
            if not self.command_queue.empty():
                with self.lock:
                    if not self.is_processing:
                        command = self.command_queue.get()
                        self.is_processing = True
                        log.info(f"Processing command: {command}")
                        self.send_status_update(server_socket, "queued")

                        for status in simulate_command_processing(command):
                            self.send_status_update(server_socket, status)

                        self.send_status_update(server_socket, "success: command ended with status 'completed'")
                        self.is_processing = False

    def send_status_update(self, server_socket: socket.socket, message: str) -> None:
        """Send a status update to the server."""
        try:
            server_socket.send(message.encode())
            log.info("Status update sent: " + str(message))
        except socket.error:
            log.info("Failed to send status update. Server may be disconnected.")


def connect_to_server() -> socket.socket:
    """Attempt to connect to the server with retries."""
    attempts = 0
    log.info(f"Connecting to {SERVER_HOST}:{PORT}")
    while attempts < MAX_RETRIES:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((SERVER_HOST, PORT))
            log.info("Connected!")
            return s
        except (socket.error, ConnectionRefusedError):
            attempts += 1
            log.info(f"Attempt {attempts} failed. Retrying in {RETRY_DELAY_S}s.")
            time.sleep(RETRY_DELAY_S)
    log.info("Max attempts reached. Exiting.")
    return None


def is_socket_closed(sock: socket.socket) -> bool:
    out = False
    try:
        # this will try to read bytes without blocking and also without removing them from buffer (peek only)
        data = sock.recv(16, socket.MSG_DONTWAIT | socket.MSG_PEEK)
        if len(data) == 0:
            out = True
    except BlockingIOError:
        out = False  # socket is open and reading from it would block
    except ConnectionResetError:
        out = True  # socket was closed for some other reason
    except Exception as e:
        log.exception("unexpected exception when checking if a socket is closed")
        out = False
    if not out:
        log.info("Server connection closed")
    return out


def main() -> None:
    """Main client function to handle connections and command processing."""
    processor = RequestProcessor()
    command_thread = None
    server_socket = connect_to_server()
    while True:
        try:
            if command_thread is None:
                command_thread = threading.Thread(target=processor.process_commands, args=(server_socket,), daemon=True)
                command_thread.start()

            while True:
                log.info("Checking for commands")
                try:
                    # Wait for command from server
                    command = server_socket.recv(1024).decode()
                    if command:
                        processor.add_command(command)
                    time.sleep(2)
                except (socket.error):
                    log.info("Error receiving command. Reconnecting...")
                    break

                if is_socket_closed(server_socket):
                    break
        except KeyboardInterrupt:
            log.info("User initiated shutdown")
            break

        time.sleep(2)

    log.info("Client shutting down.")
    server_socket.close()


if __name__ == "__main__":
    main()
