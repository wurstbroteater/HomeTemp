import time

from core.command import CommandService
from core.core_configuration import load_config, distribution_config
from core.distribute import EmailDistributor

# Global Vars
auth = None
command_service = None


def foo(commander):
    print(f"\nHello World from {commander}")


def main():
    load_config()
    global command_service, auth
    auth = distribution_config()
    command_service = CommandService(eval(auth["allowed_commanders"]))

    # Add command
    cmd_name = 'test'
    cmd_params = []
    function_to_execute = foo
    function_params = ['commander']
    command_service.add_new_command((cmd_name, cmd_params, function_to_execute, function_params))

    # Send email containing command
    mail_service = EmailDistributor(auth)
    message = create_message(subject=f"Htcmd {cmd_name}", content="")
    sender = auth["from_email"]
    receiver = auth["to_email"]
    message["From"] = sender
    message["To"] = receiver
    mail_service.send_email(from_email=sender, to_email=receiver, message=message)
    time.sleep(1)

    # Extract command from emails containing a command name and execute it
    command_service.receive_and_execute_commands()


main()
