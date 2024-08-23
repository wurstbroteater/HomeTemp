import configparser, sys,time
from sensors.dht import DHT, DHTResult

config = configparser.ConfigParser()
config.read('hometemp.ini')

        
# Parse command line parameters
if len(sys.argv) == 3:
    sensor = sys.argv[1]
    if sensor not in ("11", "22", "2302"):
        print('Sensor "{}" is not valid. Use 11, 22 or 2302'.format(sensor))
        exit(1)
    isDht11 = sensor == "11"
    try:
        pin = int(sys.argv[2])
        if (pin < 2 or pin > 27):
            raise ValueError
    except:
        print('Gpio {} is not valid'.format(pin))
        exit(1)
else:
    print('usage: dht.py [11|22|2302] [gpio#]')
    exit(1)       


# read data
#DHT_SENSOR = DHT(int(config["hometemp"]["sensor_pin"]), False)
DHT_SENSOR = DHT(int(pin), isDht11)
max_tries = 15
tries = 0
while True:
    if tries >= max_tries:
        #log.error(f"Failed to retrieve data from AM2302 sensor: Maximum retries reached.")
        break
    else:
        time.sleep(2)
        result = DHT_SENSOR.read()
        if result.error_code == DHTResult.ERR_NOT_FOUND:
            tries += 1
            #log.warning(f"({tries}/{max_tries}) Sensor could not be found. Using correct pin?")
            continue
        elif not result.is_valid():
            tries += 1
            #log.warning(f"({tries}/{max_tries}) Sensor could invalid")
            continue
        elif result.is_valid() and result.error_code == DHTResult.ERR_NO_ERROR:
            # postgres expects timestamp ins ISO 8601 format
            #timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print('Temp: {0:0.1f} C  Humidity: {1:0.1f} %'.format(result.temperature, result.humidity))
            break
            