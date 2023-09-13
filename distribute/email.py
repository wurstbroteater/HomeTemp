import configparser, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from distribute.dis_logger import dis_log as log
from datetime import datetime

config = configparser.ConfigParser()
config.read('hometemp.ini')

class EmailDistributor:
    
    @staticmethod
    def send_visualization_email(df, google_df, dwd_df):
        """
        Creates and sends an email with a description for each dataframe
        and attaches the pdf file created for the current day if the file is present.
        """
        file_name = datetime.now().strftime("%d-%m-%Y")
        auth = config["distribution"]

        from_email = auth["from_email"]
        to_email = auth["to_email"]
        pdf_file_path = f"/home/eric/HomeTemp/plots/{file_name}.pdf"
        has_attachment = True
        try:
            attachment = open(pdf_file_path, "rb")
        except FileNotFoundError:
            log.warning(f"Not file to attach found in {pdf_file_path}")
            has_attachment = False
        
        log.info(f"Sending Measurement Data Visualization to {from_email}")

        subject = f"HomeTemp v{config['hometemp']['version']} Data Report {file_name}"
        message = "------------- Sensor Data -------------\n"
        message += str(df[["humidity", "room_temp", "cpu_temp"]].corr()) + "\n\n"
        message += str(df[["humidity", "room_temp", "cpu_temp"]].describe()).format("utf8") + "\n\n"
        message += str(df[["timestamp", "humidity", "room_temp", "cpu_temp"]].tail(6))
        message += "\n\n------------- Google Data -------------\n"
        message += str(google_df.drop(['id', 'timestamp'],axis=1).describe()).format("utf8") + "\n\n"
        message += str(google_df.tail(6))
        message += "\n\n------------- DWD Data -------------\n"
        message += str(dwd_df.drop(['id', 'timestamp'],axis=1).describe()).format("utf8") + "\n\n"
        message += str(dwd_df.tail(6))
        if not has_attachment:
            message += "\n\n !!!!!!!!!!!!!!!!!!!!!!Warning: attachment not found!!!!!!!!!!!!!!!!!!!!!!\n\n"

        msg = MIMEMultipart()
        msg["From"] = from_email
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(MIMEText(message, "plain"))

        if has_attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename= {file_name}.pdf")
            msg.attach(part)

        try:
            server = smtplib.SMTP(auth["smtp_server"], auth["smtp_port"])
            server.starttls()
            server.login(auth["smtp_user"], auth["smtp_pw"])
            server.sendmail(from_email, to_email, msg.as_string())
            server.quit()
            log.info("Email sent successfully.")
        except Exception as e:
            log.error(f"Error sending email: {str(e)}")
        finally:
            if has_attachment:
                attachment.close()
        log.info("Done")