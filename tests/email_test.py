import configparser
import time
from email.mime.multipart import MIMEMultipart

from distribute.email import EmailDistributor

config = configparser.ConfigParser()
config.read('hometemp.ini')

test_sender = config["distribution"]["from_email"]
test_receiver = config["distribution"]["to_email"]
test_subject = "MEGASUPERDUPERULTATEST"

service = EmailDistributor()
# create message
message_to_send: MIMEMultipart = service.create_message(subject=test_subject, content="Test")
message_to_send["From"] = test_sender
message_to_send["To"] = test_receiver

# send message
service.send_email(from_email=test_sender, to_email=test_receiver, message=message_to_send)

time.sleep(2)

# iterate over all unseen emails (should contain previously sent mail)
mails_to_delete = []
for id, received_message in service.get_emails(which_emails='UNSEEN'):
    sender = received_message['From']
    header = received_message['Subject']
    body = received_message.get_payload()
    print(id, sender, header, body)
    if header == test_subject:
        mails_to_delete.append(id)

if len(mails_to_delete) == 0:
    print("Should be at least 1 containing the previously sent message")

# Delete email from inbox
for id in mails_to_delete:
    service.delete_email_by_id(id)

# print all emails inbox
for id, received_message in service.get_emails(which_emails='ALL'):
    sender = received_message['From']
    header = received_message['Subject']
    body = received_message.get_payload()
    print(id, sender, header, body)
