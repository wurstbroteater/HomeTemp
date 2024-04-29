import logging, configparser, time
from distribute.email import EmailDistributor
from distribute.command import CommandService


logging.basicConfig(level=logging.INFO)
log = logging.getLogger('command_test')

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

    # Send email containg command
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