import Adafruit_DHT, configparser, logging, schedule, smtplib, time
from sqlalchemy import create_engine, text, insert, inspect, exc, Table, Column, MetaData, Integer, DECIMAL, TIMESTAMP
from datetime import datetime, timedelta
from gpiozero import CPUTemperature
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

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
    if could not be retrieved
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


# ------------------------------- POSTGRES ----------------------------------------------

def _create_table(connection, table_name="sensor_data"):
    metadata = MetaData()
    table_schema = Table(table_name, metadata,
                         Column('id', Integer, primary_key=True, autoincrement=True),
                         Column('timestamp', TIMESTAMP(timezone=True), nullable=False),
                         Column('humidity', DECIMAL, nullable=False),
                         Column('room_temp', DECIMAL, nullable=False),
                         Column('cpu_temp', DECIMAL, nullable=False))
    try:
        metadata.create_all(connection)
        log.info(f"Table '{table_name}' created successfully.")

    except exc.SQLAlchemyError as e:
        log.error("Problem with database " + str(e))


def _remove_table(connection, table_name="sensor_data"):
    try:
        table = Table(table_name, MetaData(), autoload_with=connection)
        with connection.begin() as con:
            table.drop(con)
            log.info(f"Table '{table_name}' removed successfully.")

    except exc.SQLAlchemyError as e:
        log.error("Problem with database " + str(e))


def _get_table_size(connection, table_name="sensor_data"):
    try:
        with connection.connect() as con:
            result = con.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            return int(result.scalar())

    except exc.SQLAlchemyError as e:
        log.error("Problem with database " + str(e))
        return -1


def _clear_table(connection, table_name="sensor_data"):
    try:
        table = Table(table_name, MetaData(), autoload_with=connection)
        with connection.begin() as con:
            con.execute(table.delete())
            log.info(f"Table '{table_name}' cleared successfully.")

    except exc.SQLAlchemyError as e:
        log.error("Problem with database " + str(e))


def _check_table_existence(connection, table_name="sensor_data"):
    try:
        return inspect(connection).has_table(table_name)

    except exc.SQLAlchemyError as e:
        log.error("Problem with database " + str(e))
        return False


def _init_db():
    auth = config["db"]
    db_url = f"postgresql://{auth['db_user']}:{auth['db_pw']}@{auth['db_host']}:{auth['db_port']}/{auth['db_name']}"
    try:
        return create_engine(db_url)
    except exc.SQLAlchemyError as e:
        log.error("Problem with database " + str(e))


def init_db_connection(table_name="sensor_data"):
    """
    Establish the connection to postgres database and creates table it not existent.
    """
    try:
        con = _init_db()
        log.info("Connected to the database!")
        if not _check_table_existence(con, table_name):
            _create_table(con, table_name)
        return con
    except exc.SQLAlchemyError as e:
        log.error("Problem with database " + str(e))


def insert_measurements_into_db(connection, timestamp, humidity, room_temp, cpu_temp, table_name="sensor_data"):
    try:
        table = Table(table_name, MetaData(), autoload_with=connection, extend_existing=True)
        with connection.begin() as con:
            data_to_insert = {
                'timestamp': timestamp,
                'humidity': humidity,
                'room_temp': room_temp,
                'cpu_temp': cpu_temp
            }
            insert_statement = insert(table).values(**data_to_insert)
            con.execute(insert_statement)

    except exc.SQLAlchemyError as e:
        log.error("Problem with database " + str(e))


def read_data_into_dataframe(connection, table_name="sensor_data"):
    try:
        df = pd.read_sql(f"SELECT * FROM {table_name}", connection)
        return df

    except exc.SQLAlchemyError as e:
        log.error("Problem with database " + str(e))
        return None


# ------------------------------- Data Distribution ----------------------------------------------

def send_visualization_email(df):
    file_name = datetime.now().strftime("%d-%m-%Y")
    auth = config["distribution"]

    from_email = auth["from_email"]
    to_email = auth["to_email"]
    log.info(f"Sending Measurement Data Visualization to {from_email}")

    subject = f"Measurement Data Report {file_name}"
    message = str(df[["humidity", "room_temp", "cpu_temp"]].corr()) + "\n\n" + str(
        df[["humidity", "room_temp", "cpu_temp"]].describe()).format("utf8") + "\n\n" + str(
        df[["timestamp", "humidity", "room_temp", "cpu_temp"]].tail(6))

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


# ------------------------------- Visualization ----------------------------------------------

def draw_plots(df, show_heatmap=True):
    subplots = 3 if show_heatmap else 2
    sns.set_theme(style="darkgrid")  # sns.set(style="whitegrid")
    fig = plt.figure(figsize=(25, 12))
    gs = fig.add_gridspec(2, 2, height_ratios=[2, 2])  # 2 rows, 1 column

    # Temperature Measurements
    plt.subplot(gs[0])
    sns.lineplot(label="Home", x="timestamp", y="room_temp", data=df)
    plt.title("Temperature Over Time")
    plt.xlabel("Time")
    plt.ylabel("Temp (°C)")
    plt.legend()
    plt.xticks(rotation=45)
    # plt.tight_layout()
    # plt.show()

    # Humidity Measurement
    plt.subplot(gs[1])
    sns.lineplot(x="timestamp", y="humidity", color='purple', data=df)
    plt.title("Humidity Over Time")
    plt.xlabel("Time")
    plt.ylabel("Humidity (%)")
    plt.xticks(rotation=45, ha='right')
    plt.gca().xaxis.grid(True)
    plt.gca().set_facecolor('#f5f5f5')
    sns.despine(left=True, bottom=True)

    df_last_24h = df[df["timestamp"] >= datetime.now() - timedelta(hours=25)]

    # Temperature Measurements last 24 h
    plt.subplot(gs[2])
    sns.lineplot(label="Home", x="timestamp", y="room_temp", marker='o', markersize=6, data=df_last_24h)
    plt.title("Temperature Last 24 Hours")
    plt.xlabel("Time")
    plt.ylabel("Temp (°C)")
    plt.legend()
    plt.xticks(rotation=45)

    # Humidity Measurement last 24 h
    plt.subplot(gs[3])
    sns.lineplot(x="timestamp", y="humidity", marker='o', markersize=6, color='purple', data=df_last_24h)
    plt.title("Humidity Last 24 Hours")
    plt.xlabel("Time")
    plt.ylabel("Humidity (%)")
    plt.xticks(rotation=45, ha='right')
    plt.gca().xaxis.grid(True)
    plt.gca().set_facecolor('#f5f5f5')
    sns.despine(left=True, bottom=True)

    plt.tight_layout()
    name = datetime.now().strftime("%d-%m-%Y")
    plt.savefig(f"plots/{name}.pdf")
    plt.show()
    plt.close()
    sns.reset_defaults()


# ------------------------------- Main  ----------------------------------------------

def create_and_backup_visualization():
    log.info("Creating Measurement Data Visualization")
    con = init_db_connection()
    df = read_data_into_dataframe(con)
    df = df.sort_values(by="timestamp")
    df['timestamp'] = df['timestamp'].map(lambda x: datetime.strptime(str(x).strip(), '%Y-%m-%d %H:%M:%S'))
    draw_plots(df, show_heatmap=False)
    log.info("Done")
    send_visualization_email(df)


def collect_and_save_to_db():
    log.info("Start Measurement Data Collection")
    con = init_db_connection()
    # log.debug(_get_table_size(con))
    # _clear_table(con)
    cpu_temp = get_temperature()
    room_temp, humidity, timestamp = get_sensor_data()
    log.info(
        "[Measurement {0}] CPU={1:f}*C, Room={2:f}*C, Humidity={3:f}%".format(timestamp, cpu_temp, room_temp, humidity))
    insert_measurements_into_db(connection=con, timestamp=timestamp, humidity=humidity, room_temp=room_temp,
                                cpu_temp=cpu_temp)
    log.info("Done")


def main():
    log = logging.getLogger('hometemp')
    log.addHandler(logging.StreamHandler())
    log.info("------------------- HomeTemp v0.2.1 -------------------")
    schedule.every(10).minutes.do(collect_and_save_to_db)
    schedule.every().day.at("06:00").do(create_and_backup_visualization)

    collect_and_save_to_db()
    #create_and_backup_visualization()
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
