import imaplib
import os
import smtplib
from datetime import datetime
from email import encoders, message_from_bytes
from email.message import Message
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional, Tuple

from core.core_configuration import distribution_config, hometemp_config
from core.core_log import get_logger

log = get_logger(__name__)


# ----------------------------------------------------------------------------------------------------------------
# The data distribution module. Contains EmailDistributor for publishing emails with content.
# Also includes static util methods for creating certain types of mails.
# ----------------------------------------------------------------------------------------------------------------

class EmailDistributor:

    def __init__(self):
        self.config = distribution_config()

    def _get_imap_connection(self) -> Optional[imaplib.IMAP4_SSL]:
        """
        has to be closed after usage!!!
        """
        imap_server = self.config["imap_server"]
        imap_port = int(self.config["imap_port"])
        imap_user = self.config["imap_user"]
        imap_pw = self.config["imap_pw"]
        server = None
        try:
            server = imaplib.IMAP4_SSL(imap_server, imap_port)
            server.login(imap_user, imap_pw)
        except Exception as e:
            log.error(f"Error while connecting to {imap_server}:{imap_port} : {str(e)}")

        return server

    def get_emails(self, which_emails='UNSEEN') -> Optional[List[Tuple[str, Message]]]:
        """
        which emails possibilities: 'ALL' 'UNSEEN'
        """
        server = self._get_imap_connection()
        if server is None:
            return None

        # list of tuples containing the email id and message
        received_emails = []
        try:
            server.select('inbox')
            result, data = server.search(None, which_emails)
            if result == 'OK':
                email_ids = data[0].split()
                for email_id in email_ids:
                    result, email_data = server.fetch(email_id, '(RFC822)')
                    if result == 'OK':
                        raw_email = email_data[0][1]
                        msg = message_from_bytes(raw_email)
                        received_emails.append((email_id, msg))
        except Exception as e:
            log.error(f"Error occurred while fetching emails: {str(e)}")
        finally:
            server.close()
            server.logout()

        return received_emails

    def delete_email_by_id(self, email_id: str) -> bool:
        server = self._get_imap_connection()
        was_successful = False
        if server is None:
            return was_successful

        try:
            server.select('inbox')
            server.store(email_id, '+FLAGS', '\\Deleted')
            server.expunge()
            log.info("Email deleted successfully.")
            was_successful = True
        except Exception as e:
            log.error(f"Error occurred while deleting email: {str(e)}")
        finally:
            server.close()
            server.logout()

        return was_successful

    def send_email(self, from_email: str, to_email: str, message: MIMEMultipart) -> bool:
        smtp_server = self.config["smtp_server"]
        smtp_port = int(self.config["smtp_port"])
        smtp_user = self.config["smtp_user"]
        smtp_pw = self.config["smtp_pw"]

        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_user, smtp_pw)
            server.sendmail(from_email, to_email, message.as_string())
            server.quit()
            log.info("Email sent successfully.")
            return True
        except Exception as e:
            log.error(f"Error sending email: {str(e)}")

        return False


# ----------------------------------------------------------------------------------------------------------------
# Util methods
# ----------------------------------------------------------------------------------------------------------------

def create_message(subject: str, content: str, attachment_paths=None) -> MIMEMultipart:
    """
    from and to email have to be added by the receiving logic.
    """
    if attachment_paths is None:
        attachment_paths = []
    message = MIMEMultipart()
    message["Subject"] = subject

    message.attach(MIMEText(content, "plain"))

    for attachment_path in attachment_paths:
        try:
            attachment = open(attachment_path, "rb")
            attachment_content = attachment.read()
            attachment.close()

            file_name = os.path.basename(attachment_path)

            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment_content)
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename= {file_name}")
            message.attach(part)

        except FileNotFoundError:
            log.warning(f"No file to attach found in {attachment_path}")
            continue

    return message


def send_visualization_email(df, google_df=None, dwd_df=None, ulmde_df=None, wettercom_df=None, path_to_pdf=None,
                             receiver=None):
    hometemp_params_not_set = google_df is None or dwd_df is None or ulmde_df is None or wettercom_df is None
    if hometemp_params_not_set:
        _send_base_temp_vis(df=df, path_to_pdf=path_to_pdf, receiver=receiver)
    else:
        _send_home_temp_vis_email(df=df, ulmde_df=ulmde_df, google_df=google_df, dwd_df=dwd_df,
                                  wettercom_df=wettercom_df, path_to_pdf=path_to_pdf, receiver=receiver)


def _send_base_temp_vis(df, path_to_pdf=None, receiver=None):
    """
    Creates and sends an email with a description for each dataframe
    and attaches the pdf file created for the current day if the file is present.
    """
    today = datetime.now().strftime("%d-%m-%Y")
    if path_to_pdf is None:
        file_name = today + ".pdf"
        # TODO: change hardcoded link
        path_to_pdf = f"/home/ericl/BaseTemp/plots/{file_name}"
    else:
        file_name = os.path.basename(path_to_pdf)

    email_config = distribution_config()
    from_email = email_config["from_email"]
    receiver = receiver if receiver is not None else email_config["to_email"]

    log.info(f"Sending Measurement Data Visualization to {receiver}")

    subject = f"BaseTemp v{hometemp_config()['version']} Data Report {today}"
    message = create_sensor_data_message(df)

    distributor = EmailDistributor()
    msg = create_message(subject=subject, content=message, attachment_paths=[path_to_pdf])
    msg["From"] = from_email
    msg["To"] = receiver

    _ = distributor.send_email(from_email=from_email, to_email=receiver, message=msg)


def _send_home_temp_vis_email(df, google_df, dwd_df, ulmde_df, wettercom_df, path_to_pdf=None, receiver=None):
    """
    Creates and sends an email with a description for each dataframe
    and attaches the pdf file created for the current day if the file is present.
    """
    today = datetime.now().strftime("%d-%m-%Y")
    if path_to_pdf is None:
        file_name = today + ".pdf"
        # TODO: change hardcoded link
        path_to_pdf = f"/home/ericl/HomeTemp/plots/{file_name}"
    else:
        file_name = os.path.basename(path_to_pdf)

    email_config = distribution_config()
    from_email = email_config["from_email"]
    receiver = receiver if receiver is not None else email_config["to_email"]

    log.info(f"Sending Measurement Data Visualization to {receiver}")

    subject = f"HomeTemp v{hometemp_config()['version']} Data Report {today}"
    message = create_sensor_data_message(df)
    message += "\n\n------------- Google Data -------------\n"
    message += str(google_df.drop(['timestamp'], axis=1, errors='ignore').describe()).format("utf8") + "\n\n"
    message += str(google_df.tail(6))
    message += "\n\n------------- DWD Data -------------\n"
    message += str(dwd_df.drop(['timestamp'], axis=1, errors='ignore').describe()).format("utf8") + "\n\n"
    message += str(dwd_df.tail(6))
    message += "\n\n------------- Wetter.com Data -------------\n"
    message += str(wettercom_df.drop(['timestamp'], axis=1, errors='ignore').describe()).format("utf8") + "\n\n"
    message += str(wettercom_df.tail(6))
    message += "\n\n------------- Ulm.de Data -------------\n"
    message += str(ulmde_df.drop(['timestamp'], axis=1, errors='ignore').describe()).format("utf8") + "\n\n"
    message += str(ulmde_df.tail(6))

    distributor = EmailDistributor()
    msg = create_message(subject=subject, content=message, attachment_paths=[path_to_pdf])
    msg["From"] = from_email
    msg["To"] = receiver

    _ = distributor.send_email(from_email=from_email, to_email=receiver, message=msg)


def send_picture_email(picture_path, df, receiver):
    today = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
    log.info(f"Sending picture to {receiver}")
    subject = f"BaseTemp v{hometemp_config()['version']} Live Picture of {today}"
    message = create_sensor_data_message(df)

    email_config = distribution_config()
    from_email = email_config["from_email"]
    distributor = EmailDistributor()
    msg = create_message(subject=subject, content=message, attachment_paths=[picture_path])
    msg["From"] = from_email
    msg["To"] = receiver

    _ = distributor.send_email(from_email=from_email, to_email=receiver, message=msg)


def send_heat_warning_email(current_temp):
    distributor = EmailDistributor()
    msg = create_message(
        subject=f"BaseTemp v{hometemp_config()['version']} HEAT WARNING OF {current_temp}°C",
        content="Its the heat of the moment")
    email_config = distribution_config()
    from_email = email_config["from_email"]
    receiver = email_config["to_email"]
    msg["From"] = from_email
    msg["To"] = receiver
    _ = distributor.send_email(from_email=from_email, to_email=receiver, message=msg)


def create_sensor_data_message(df):
    message = "------------- Sensor Data -------------\n"
    message += str(df[["humidity", "room_temp", "cpu_temp"]].corr()) + "\n\n"
    message += str(df[["humidity", "room_temp", "cpu_temp"]].describe()).format("utf8") + "\n\n"
    message += str(df[["timestamp", "humidity", "room_temp", "cpu_temp"]].tail(6))
    return message
