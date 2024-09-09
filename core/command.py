from core.core_log import get_logger
from core.core_configuration import distribution_config
from email.utils import parseaddr
from typing import List, Optional
from core.distribute import EmailDistributor
from core.core_configuration import hometemp_config

log = get_logger(__name__)


# ----------------------------------------------------------------------------------------------------------------
# This module is responsible for parsing, processing and holding command information.
# A Command consists of an id, passed parameters, a function and function parameters to executre when the id was
# parsed. Currently, commands are retrieved via email, so CommandRequest is a data class associating a valid 
# command with its requester, i.e., the sender of the mail.
# Supported commands needs to be added via add_command method before executing get_received_command_requestes
# ----------------------------------------------------------------------------------------------------------------


class Command:

    def __init__(self, id, params, function, function_params):
        self.id = id
        self.params = params
        self.function = function
        self.function_params = function_params

    def __str__(self):
        return f"Command[id: {self.id}, parameters: {self.params}, function: {self.function}, function_params: {self.function_params}]"

    def __repr__(self):
        return f"Command({self.id}, {self.params}, {self.function}, {self.function_params})"

    def __eq__(self, other):
        """
        A command is identified by its id and parameters
        """
        if not isinstance(other, Command):
            return False
        return self.id == other.id and self.params == other.params

    def __hash__(self):
        return hash((self.id, self.params, self.function, self.function_params))


class CommandRequest:

    def __init__(self, email_id: str, commander: str, command: Command):
        self.email_id = email_id
        self.commander = commander
        self.command = command


class CommandService:

    def __init__(self):
        self.allowed_commanders = eval(distribution_config()["allowed_commanders"])
        self.parser = CommandParser()
        self.email_service = EmailDistributor()

    def _get_emails_with_valid_prefix(self):
        found_email_with_command = []

        for email_id, received_message in self.email_service.get_emails(which_emails='ALL'):
            sender = str(parseaddr(received_message['From'])[1])
            subject = received_message['Subject']
            body = received_message.get_payload()
            for valid_prefix in self.parser.valid_command_prefixes:
                if valid_prefix in str(subject).lower():
                    found_email_with_command.append((email_id, sender, subject, body))
                    break
        return found_email_with_command

    def _parse_emails_with_command(self, emails_with_command) -> List[CommandRequest]:
        requests = []
        for email_id, commander, subject, body in emails_with_command:
            received_command = self.parser.parse_received_command(commander=commander, header=subject, body=body)
            if received_command is not None:
                requests.append(CommandRequest(email_id=email_id, commander=commander, command=received_command))
        return requests

    def add_new_command(self, cmd_syntax: str):
        if len(cmd_syntax) == 4:
            self.parser.add_command_syntax(
                Command(id=cmd_syntax[0], params=cmd_syntax[1], function=cmd_syntax[2], function_params=cmd_syntax[3]))
        else:
            log.warning("Tried to add command with invalid syntax!")

    def receive_and_execute_commands(self):
        emails_with_command = self._get_emails_with_valid_prefix()
        command_requests = self._parse_emails_with_command(emails_with_command)

        for command_request in command_requests:
            self.email_service.delete_email_by_id(command_request.email_id)
            command = command_request.command
            log.info(f"Received call from '{command_request.commander}' to execute '{command}'")
            function_params = {}
            for param_key in command.function_params:
                if param_key == 'commander':
                    function_params[param_key] = command_request.commander
                # Add more command parameters here
            try:
                command.function(**function_params)
            except Exception as e:
                log.warning(f"Error while executing command function: {str(e)}")


class CommandParser:

    def __init__(self):
        # always treat prefix as case-insensitive
        self.valid_command_prefixes = list(
            map(lambda p: str(p).lower(), eval(hometemp_config()['valid_command_prefix'])))
        # TODO: should be Set
        self.valid_commands = []

    # ------- start command parsing -------

    def _validate_header_prefix(self, header):
        header = str(header).strip().lower().split(' ')
        if header[0] in self.valid_command_prefixes:
            # prefix valid, return tokens
            return header[1:]
        else:
            return None

    def _get_command_by_id(self, id: str) -> Optional[Command]:
        """
        currently only validates the command id but not the parameters or function
        """
        command = None
        for cmd in self.valid_commands:
            if id == cmd.id:
                command = cmd
                break
        return command

    # ------- end command parsing -------

    # ------- start public methods -------

    def parse_received_command(self, commander, header, body) -> Optional[Command]:
        """
        parse received tokens and returns command if found
        """
        command_tokens = self._validate_header_prefix(header)
        command = None
        if command_tokens is None:
            log.warning(f"Commander '{commander}' passed invalid command '{header}'")
        elif len(command_tokens) == 0:
            log.warning(f"Commander '{commander}' only passed valid prefix but no command")
        else:
            received_cmd_id = command_tokens[0]
            command = self._get_command_by_id(received_cmd_id)
            if command is None:
                log.warning(f"Commander '{commander}' sent unknown command id '{received_cmd_id}'")
            else:
                log.info(f"Commander '{commander}' requested command id '{received_cmd_id}'")
        return command

    def add_command_syntax(self, command: Command) -> None:
        if command not in self.valid_commands:
            self.valid_commands.append(command)
        else:
            log.warning(f"Tried to add a command that is already known: {str(command)}")
