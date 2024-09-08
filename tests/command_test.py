from core.core_log import setup_logging, get_logger
import time

from core.command import CommandService
from core.distribute import EmailDistributor

log = get_logger(__name__)

# Global Vars
config = configparser.ConfigParser()
config.read('hometemp.ini')
auth = config["distribution"]
command_service = None


def foo(commander):
    print(f"\nHello World from {commander}")


def main():
    global command_service
    command_service = CommandService()
    # Add command
    cmd_name = 'test'
    cmd_params = []
    function_to_execute = foo
    function_params = ['commander']
    command_service.add_new_command((cmd_name, cmd_params, function_to_execute, function_params))

    # Send email containing command
    mail_service = EmailDistributor()
    message = mail_service.create_message(subject=f"Htcmd {cmd_name}", content="")
    sender = auth["from_email"]
    receiver = auth["to_email"]
    message["From"] = sender
    message["To"] = receiver
    mail_service.send_email(from_email=sender, to_email=receiver, message=message)
    time.sleep(1)

    # Extract command from emails containing a command name and execute it
    command_service.receive_and_execute_commands()


main()
