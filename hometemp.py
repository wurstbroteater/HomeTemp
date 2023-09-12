import Adafruit_DHT, configparser, logging, re, schedule, smtplib, time, threading
from datetime import datetime, timedelta
from gpiozero import CPUTemperature
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from persist.database import DwDDataHandler, GoogleDataHandler, SensorDataHandler 
from visualize.plots import draw_plots

# only logs from this file will be written to console but all logs will be saved to file
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(filename='measurement.log',
                    encoding='utf-8',
                    level=logging.INFO)
config = configparser.ConfigParser()
config.read('hometemp.ini')
log = logging.getLogger('hometemp')


# ------------------------------- Raspberry Pi Temps ----------------------------------------------

def get_temperature():
    cpu = CPUTemperature()
    return float(cpu.temperature)


def get_sensor_data():
    """
    Returns temperature and humidity data measures by AM2302 Sensor and the measure timestamp or raise exception 
    if the values could not be retrieved
    """
    DHT_SENSOR = Adafruit_DHT.AM2302
    DHT_PIN = 2
    humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)

    if humidity is not None and temperature is not None:
        # postgres expects timestamp ins ISO 8601 format
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return temperature, humidity, timestamp
    else:
        raise Exception("Failed to retrieve data from humidity sensor")


# ------------------------------- Data Distribution ----------------------------------------------

def send_visualization_email(df, google_df, dwd_df):
    file_name = datetime.now().strftime("%d-%m-%Y")
    auth = config["distribution"]

    from_email = auth["from_email"]
    to_email = auth["to_email"]
    log.info(f"Sending Measurement Data Visualization to {from_email}")

    subject = f"HomeTemp Data Report {file_name}"
    message = "------------- Sensor Data -------------\n"
    message += str(df[["humidity", "room_temp", "cpu_temp"]].corr()) + "\n\n"
    message += str(df[["humidity", "room_temp", "cpu_temp"]].describe()).format("utf8") + "\n\n"
    message += str(df[["timestamp", "humidity", "room_temp", "cpu_temp"]].tail(6))
    message += "\n\n------------- Google Data -------------\n"
    message += str(google_df.describe()).format("utf8") + "\n\n"
    message += str(google_df.tail(6))
    message += "\n\n------------- DWD Data -------------\n"
    message += str(dwd_df.describe()).format("utf8") + "\n\n"
    message += str(dwd_df.tail(6))

    pdf_file_path = f"/home/eric/HomeTemp/plots/{file_name}.pdf"
    attachment = open(pdf_file_path, "rb")

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(message, "plain"))

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
        attachment.close()
    log.info("Done")


# ------------------------------- Main  ----------------------------------------------

def create_and_backup_visualization():
    log.info("Creating Measurement Data Visualization")
    auth = config["db"]
    sensor_data_handler = SensorDataHandler(auth['db_port'], auth['db_host'], auth['db_user'], auth['db_pw'], 'sensor_data')
    sensor_data_handler.init_db_connection(check_table=False)
    # sensor data
    df = sensor_data_handler.read_data_into_dataframe()
    df = df.sort_values(by="timestamp")
    df['timestamp'] = df['timestamp'].map(lambda x: datetime.strptime(str(x).strip(), '%Y-%m-%d %H:%M:%S'))
    # Google weather data
    google_handler = GoogleDataHandler(auth['db_port'], auth['db_host'], auth['db_user'], auth['db_pw'], 'google_data')
    google_handler.init_db_connection(check_table=False)
    google_df = google_handler.read_data_into_dataframe()
    google_df['timestamp'] = google_df['timestamp'].map(lambda x: datetime.strptime(re.sub('\..*', '', str(x).strip()), '%Y-%m-%d %H:%M:%S'))
    google_df = google_df.sort_values(by="timestamp")
    # DWD weather data
    dwd_handler = DwDDataHandler(auth['db_port'], auth['db_host'], auth['db_user'], auth['db_pw'], 'dwd_data')
    dwd_handler.init_db_connection(check_table=False)
    dwd_df = dwd_handler.read_data_into_dataframe()
    dwd_df['timestamp'] = dwd_df['timestamp'].map(lambda x: datetime.strptime(str(x).strip().replace('+00:00', ''), '%Y-%m-%d %H:%M:%S'))
    dwd_df = dwd_df.sort_values(by="timestamp")
    draw_plots(df, google_df=google_df, dwd_df=dwd_df)
    log.info("Done")
    send_visualization_email(df, google_df=google_df, dwd_df=dwd_df)


def run_threaded(job_func):
    job_thread = threading.Thread(target=job_func)
    job_thread.start()


def collect_and_save_to_db():
    log.info("Start Measurement Data Collection")
    auth = config["db"]
    handler = SensorDataHandler(auth['db_port'], auth['db_host'], auth['db_user'], auth['db_pw'], 'sensor_data')
    handler.init_db_connection()
    # log.debug(_get_table_size(con))
    # _clear_table(con)
    cpu_temp = get_temperature()
    room_temp, humidity, timestamp = get_sensor_data()
    log.info(
        "[Measurement {0}] CPU={1:f}*C, Room={2:f}*C, Humidity={3:f}%".format(timestamp, cpu_temp, room_temp, humidity))
    handler.insert_measurements_into_db(timestamp=timestamp, humidity=humidity, room_temp=room_temp, cpu_temp=cpu_temp)
    log.info("Done")


def main():
    log = logging.getLogger('hometemp')
    log.addHandler(logging.StreamHandler())
    log.info(f"------------------- HomeTemp v{config['hometemp']['version']} -------------------")
    schedule.every(10).minutes.do(collect_and_save_to_db)
    # run_threaded assumes that we never have overlapping usage of this method or its components
    schedule.every().day.at("06:00").do(run_threaded, create_and_backup_visualization)

    #collect_and_save_to_db()
    #run_threaded(create_and_backup_visualization)
    log.info("finished initialization")
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
