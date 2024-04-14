import configparser, email, imaplib, re
from distribute.dis_logger import dis_log as log
from email.utils import parseaddr


config = configparser.ConfigParser()
config.read('hometemp.ini') 

class Command:

    def __init__(self, id, params, function):
        self.id = id
        self.params = params
        self.function = function
    
    def __str__(self):
        return f"Command[id: {self.id}, parameters: {self.params}, function: {self.function}]"
    
    def __repr__(self):
        return f"Command({self.id}, {self.params}, {self.function})"
    
    def __eq__(self, other):
        """
        A command is identifyed by its id and parameters
        """
        if not isinstance(other, Command):
            return False
        return self.id == other.id and self.params == other.params
    
    def __hash__(self):
        return hash((self.id, self.params, self.function))


class CommandService:

    def __init__(self):
        self.connected = False
        self.email_address = config["distribution"]["from_email"]
        self.password = config["distribution"]["smtp_pw"]
        self.server =  config["distribution"]["imap_server"]
        self.port =  int(config["distribution"]["imap_port"])
        self.allowed_commanders = eval(config["distribution"]["allowed_commanders"])

        # for command validation
        # always treat prefix as case insensitiv
        self.valid_command_prefixes = ['HomeTempCommand'.lower(), 'HomeTempCmd'.lower(), 'HTcmd'.lower()]
        # default supported commands
        # supported commands needs to be added via add_command method before executing get_received_command_requestes
        self.valid_commands = []


    def _login(self):
        try:
            self.mail = imaplib.IMAP4_SSL(self.server, self.port)
            self.mail.login(self.email_address, self.password)
            self.connected = True
        except Exception as e:
            log.error(f"Failed to connect to the mail server: {str(e)}")
            raise

    def _close(self):
        try:
            self.mail.logout()
            self.connected = False
        except Exception as e:
            log.error(f"Error while closing: {str(e)}")

    def _get_emails(self):
        if not self.connected:
            log.error("Cannot receive emails because no connection was etablished")
            return
        try:
            self.mail.select('inbox')
            result, data = self.mail.search(None, 'ALL')
            if result == 'OK':
                email_ids = data[0].split()
                for email_id in email_ids:
                    result, email_data = self.mail.fetch(email_id, '(RFC822)')
                    if result == 'OK':
                        raw_email = email_data[0][1]
                        msg = email.message_from_bytes(raw_email)
                        yield email_id, msg
        except Exception as e:
            log.error(f"Error occurred while fetching emails: {str(e)}")
 

    def _send_email(self, to_address, subject, body):
            try:
                # Code to send email
                pass
            except Exception as e:
                log.error(f"Error occurred while sending email: {str(e)}")

    
    def _delete_email(self, email_id):
            try:
                self.mail.store(email_id, '+FLAGS', '\\Deleted')
                self.mail.expunge()
            except Exception as e:
                log.error(f"Error occurred while deleting email: {str(e)}")

    def _get_and_delete_email_with_command(self, delete_mail=True):
        """
        Iterals over all emails and returns a list containing all found
        plain commander, command header and command body.
        :param delete_mail: (default True) Wether found email with command should be deleted
        :return: list of tuples. Each tuple conains commander, header and body
        """
        found_commands = []
        try:
            received_emails = self._get_emails()
            for email_id, msg in received_emails:
                sender = str(parseaddr(msg['From'])[1])
                header = msg['Subject']
                body = msg.get_payload()
                data_report = r'HomeTemp .*v\d*\.[\.*\d*]*.*[-DEV]*.*[Data Report]*'
                # exclude data reports
                if not re.match(data_report, header) and sender in self.allowed_commanders:
                    found_commands.append((sender, header, body))
                    if delete_mail:
                        self._delete_email(email_id=email_id)
        except Exception as e:
            log.error(f"Error occurred while processing emails: {str(e)}")
        finally:
            return found_commands

    # ------- start command parsing -------  
     
    def _validate_header_prefix(self, header):
        header = str(header).strip().lower().split(' ')
        if header[0] in self.valid_command_prefixes:
            # prefix valid, return tokens
            return header[1:]
        else:
            return None
        
    def _get_command_by_id(self, id):
        """
        currently only validates the command id but not the parameters or function
        """
        command = None
        for cmd in self.valid_commands:
            if id == cmd.id:
                command = cmd
                break
        return command
    
        
    def _parse_received_command(self, commander, header, body):
        """
        parse received tokens and returns command if found
        """
        #log.error("Commander: ", commander)
        #log.error("Command: ", header)
        #log.error("Body: ", body)
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

    # ------- end command parsing -------              

    # ------- start public methods ------- 

    def add_command_syntax(self, cmd_syntax):
        if len(cmd_syntax) == 3:
            self.valid_commands.append(Command(id=cmd_syntax[0], params=cmd_syntax[1], function=cmd_syntax[2]))


    def get_received_command_requestes(self):
        if not self.connected:
            self._login()
        commands = self._get_and_delete_email_with_command(delete_mail=True)
        if self.connected :
            self._close()
        valid_commands = []
        for commander, header, body in commands:
            command = self._parse_received_command(commander, header, body)
            if command is not None:
                valid_commands.append((commander, command))
        return valid_commands

