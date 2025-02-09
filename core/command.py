from email.utils import parseaddr
from typing import List, Optional, Tuple

from core.core_configuration import distribution_config
from core.core_configuration import core_config
from core.core_log import get_logger
from core.distribute import EmailDistributor

log = get_logger(__name__)


# ----------------------------------------------------------------------------------------------------------------
# This module is responsible for parsing, processing and holding command information.
# A Command consists of an id, passed parameters, a function and function parameters to execute when the id was
# parsed. Currently, commands are retrieved via email, so CommandRequest is a data class associating a valid 
# command with its requester, i.e., the sender of the mail.
# Supported commands needs to be added via add_command method before executing receive_and_execute_commands
# ----------------------------------------------------------------------------------------------------------------


class Command:

    def __init__(self, id_, params, function, function_params):
        self.id = id_
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

    def __init__(self, email_id: str, commander: str, cmd_tokens: List[str], command: Command):
        self.email_id = email_id
        self.commander = commander
        self.command = command
        self.cmd_tokens = cmd_tokens

    def __str__(self):
        return f"CommandRequest[id: {self.email_id}, commander: {self.commander}, tokens: {self.cmd_tokens}, command: {self.command}"


class CommandService:

    def __init__(self):
        self.allowed_commanders = eval(distribution_config()["allowed_commanders"])
        self.parser = CommandParser()
        self.email_service = EmailDistributor()

    def _get_emails_with_valid_prefix(self):
        found_email_with_command = []

        mails = self.email_service.get_emails(which_emails='ALL')
        for email_id, received_message in [] if mails is None else mails:
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
            received_command, tokens = self.parser.parse_received_command(commander=commander, header=subject,
                                                                          body=body)
            if received_command is not None:
                requests.append(
                    CommandRequest(email_id=email_id, commander=commander, command=received_command, cmd_tokens=tokens))
        return requests

    def add_new_command(self, cmd_syntax: tuple):
        if len(cmd_syntax) == 4:
            c = Command(id_=cmd_syntax[0], params=cmd_syntax[1], function=cmd_syntax[2], function_params=cmd_syntax[3])
            self.parser.add_command_syntax(c)
            log.debug(f"Added command: {c}")
        else:
            log.warning("Tried to add command with invalid syntax!")

    def receive_and_execute_commands(self):
        emails_with_command = self._get_emails_with_valid_prefix()
        command_requests: List[CommandRequest] = self._parse_emails_with_command(emails_with_command)

        for command_request in command_requests:
            self.email_service.delete_email_by_id(command_request.email_id)
            command: Command = command_request.command
            log.info(f"Received call from '{command_request.commander}' to execute '{command}'")
            function_params = {}
            for param_key in command.function_params:
                if param_key == 'commander':
                    function_params[param_key] = command_request.commander
                if command.id == 'phase' and param_key == 'phase':
                    tokens = command_request.cmd_tokens
                    if len(tokens) <= 1:
                        log.info(f"Commander '{command_request.commander}' requested phase but didnt specify which.")
                        return
                    if len(tokens) > 2:
                        log.info(f"Commander '{command_request.commander}' requested phase with too many parameters.")
                    function_params[param_key] = tokens[1]
                # Add more command parameters here   
            try:
                command.function(**function_params)
            except Exception as e:
                log.warning(f"Error while executing command function: {str(e)}")


class CommandParser:

    def __init__(self):
        # always treat prefix as case-insensitive
        self.valid_command_prefixes = list(
            map(lambda p: str(p).lower(), eval(core_config()['valid_command_prefix'])))
        # should be treated as Set
        self.valid_commands = []

    # ------- start command parsing -------

    def _validate_header_prefix(self, header):
        header = str(header).strip().lower().split(' ')
        if header[0] in self.valid_command_prefixes:
            # prefix valid, return tokens
            return header[1:]
        else:
            return None

    def _get_command_by_id(self, id_: str) -> Optional[Command]:
        """
        currently only validates the command id but not the parameters or function
        """
        command = None
        for cmd in self.valid_commands:
            if id_ == cmd.id:
                command = cmd
                break
        return command

    # ------- end command parsing -------

    # ------- start public methods -------

    def parse_received_command(self, commander, header, body) -> Optional[Tuple[Command, List[str]]]:
        """
        parse received tokens and returns command if found.
        command_tokens if found, it contains all received tokens, including command name at index 0.
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
        return command, command_tokens

    def add_command_syntax(self, command: Command) -> None:
        if command not in self.valid_commands:
            self.valid_commands.append(command)
        else:
            log.warning(f"Tried to add a command that is already known: {str(command)}")
