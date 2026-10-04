from core.core_log import get_logger
from typing import Dict, List, Optional
            # TODO: Summary instead of histogram
from prometheus_client import Counter,Info, Gauge, generate_latest, Histogram, Summary, start_http_server
from prometheus_client.metrics import MetricWrapperBase
from prometheus_client.exposition import CONTENT_TYPE_LATEST
from starlette.responses import Response
import time
import functools
import psutil

log = get_logger(__name__)

"""
Singleton Prometheus Manager. Needs to instantiated once in start.py and then every subseeding instance will automatically use the singleton manager.
"""

class PrometheusManager:
    """
    Cannot be used as class constant!
    """
    _instance = None
    _instance_name = None

    #General
    UPTIME:str = "app_uptime_seconds"
    WEB_ACCESS:str = "web_accessible"
    USAGE_CPU:str = "cpu_usage_percent"
    USAGE_RAM:str = "ram_usage_percent"
    USAGE_DISK:str = "disk_usage_percent"
    SENT_MAILS:str = "emails_sent_total"
    #HomeTemp
    ROOM_TEMP:str = "temperature_room"
    ROOM_TEMP_READ_FAILS:str = "sensor_read_errors_total"
    ROOM_HUM:str ="humidity_room"
    #Ecowitt
    ECWOITT_INDOOR_TEMP:str = "ecowitt_indoor_temperature"
    ECWOITT_INDOOR_HUM:str = "ecowitt_indoor_humidity"
    ECOWITT_OUTDOOR_TEMP:str = "ecowitt_outdoor_temperature"
    ECOWITT_OUTDOOR_HUM:str = "ecowitt_outdoor_humidity"
    ECOWITT_OUTDOOR_FEEL_LIKE:str = "ecowitt_outdoor_feellike"
    ECOWITT_OUTDOOR_DEW_POINT:str = "ecowitt_outdoor_dewpoint"
    ECOWITT_OUTDOOR_RAIN_EVENT:str = "ecowitt_outdoor_rainevent"
    ECOWITT_OUTDOOR_RAIN_RATE:str = "ecowitt_outdoor_rainrate"
    ECOWITT_OUTDOOR_RAIN_LAST_24H:str = "ecowitt_outdoor_rainlast24h"
    ECOWITT_RAIN_LAST_HOUR:str = "ecowitt_outdoor_rainlasthour"
    ECOWITT_RAIN_DAILY:str = "ecowitt_outdoor_raindaily"
    #BaseTemp
    LATEST_PICTURE_TIMED:str = "latest_picture_timed"
    LATEST_PICTURE_COMMANDED:str = "latest_picture_commanded"
    #Fetcher
    ALL_WEATHER_TIME:str = "weather_fetch_duration_seconds"
    All_OUTSIDE_TEMP:str = "current_weather_data"


    # use singleton to avoid metric conflicts as prometheus expects global, singleton-like metrics. do not override __init__ !!
    def __new__(cls, instance_name: str = None):
        if cls._instance is None:
            if instance_name is None:
                raise ValueError("First instantiation must provide an instance name!")
            cls._instance = super(PrometheusManager, cls).__new__(cls)
            cls._instance.__init_metrics(instance_name)
            cls._instance_name = instance_name

        return cls._instance
    
    @classmethod
    def get_instance_name(cls):
        """Get the instance name of the singleton"""
        return cls._instance_name
    
    def __init_metrics(self, instance_name: str):
        self.instance_name = instance_name
        self.start_time = time.time()
        self.label_instance = ['instance']
        self.label_fetcher_for_instance =   self.label_instance  + ['fetcher_id']

        self.metrics: Dict[str, MetricWrapperBase] = {
            # General
            # uptime should be timer
            self.UPTIME: Gauge(self.UPTIME, "Application uptime in seconds", self.label_instance),
            self.WEB_ACCESS: Gauge(self.WEB_ACCESS, "Web connectivity status (1 = up, 0 = down)", self.label_instance),
            self.USAGE_CPU: Gauge(self.USAGE_CPU, "Current CPU usage in percent", self.label_instance),
            self.USAGE_RAM: Gauge(self.USAGE_RAM, "Current RAM usage in percent", self.label_instance),
            self.USAGE_DISK: Gauge(self.USAGE_DISK, "Current Disk usage in percent", self.label_instance),
            self.SENT_MAILS: Counter(self.SENT_MAILS, "Number of sent emails", self.label_instance),
            # HomeTemp
            self.ROOM_TEMP: Gauge(self.ROOM_TEMP, 'Current room temperature', self.label_instance),
            self.ROOM_TEMP_READ_FAILS: Counter(self.ROOM_TEMP_READ_FAILS, 'Number of failed sensor readings', self.label_instance),
            self.ROOM_HUM: Gauge(self.ROOM_HUM, 'Current room humidity', self.label_instance),
            #Ecowitt
            self.ECWOITT_INDOOR_TEMP: Gauge(self.ECWOITT_INDOOR_TEMP, "Ecowitt indoor temperature", self.label_instance),
            self.ECWOITT_INDOOR_HUM: Gauge(self.ECWOITT_INDOOR_HUM, "Ecowitt indoor humidity", self.label_instance),
            self.ECOWITT_OUTDOOR_TEMP: Gauge(self.ECOWITT_OUTDOOR_TEMP, "Ecowitt outdoor temperature", self.label_instance),
            self.ECOWITT_OUTDOOR_HUM: Gauge(self.ECOWITT_OUTDOOR_HUM, "Ecowitt outdoor humidity", self.label_instance),
            self.ECOWITT_OUTDOOR_FEEL_LIKE: Gauge(self.ECOWITT_OUTDOOR_FEEL_LIKE, "Ecowitt outdoor feel-like temperature", self.label_instance),
            self.ECOWITT_OUTDOOR_DEW_POINT: Gauge(self.ECOWITT_OUTDOOR_DEW_POINT, "Ecowitt outdoor dew point", self.label_instance),
            self.ECOWITT_OUTDOOR_RAIN_EVENT: Gauge(self.ECOWITT_OUTDOOR_RAIN_EVENT, "Ecowitt rain event", self.label_instance),
            self.ECOWITT_OUTDOOR_RAIN_RATE: Gauge(self.ECOWITT_OUTDOOR_RAIN_RATE, "Ecowitt rain rate", self.label_instance),
            self.ECOWITT_RAIN_DAILY: Gauge(self.ECOWITT_RAIN_DAILY, "Ecowitt rain daily", self.label_instance),
            self.ECOWITT_OUTDOOR_RAIN_LAST_24H: Gauge(self.ECOWITT_OUTDOOR_RAIN_LAST_24H, "Ecowitt rain last 24h ", self.label_instance),
            self.ECOWITT_RAIN_LAST_HOUR: Gauge(self.ECOWITT_RAIN_LAST_HOUR, "Ecowitt rain last hour", self.label_instance),

            # BaseTemp
            self.LATEST_PICTURE_TIMED: Info(self.LATEST_PICTURE_TIMED, "Filename of latest timed picture", self.label_instance),
            self.LATEST_PICTURE_COMMANDED: Info(self.LATEST_PICTURE_COMMANDED, "Filename of latest commandedf picture", self.label_instance),
            # Weather
            # TODO: Summary instead of histogram
            self.ALL_WEATHER_TIME: Histogram(self.ALL_WEATHER_TIME, 'Time to fetch online weather data', self.label_instance),
            self.All_OUTSIDE_TEMP: Gauge(self.All_OUTSIDE_TEMP, 'Current fetched weather data', self.label_fetcher_for_instance)
        }

   
    def __get_metric(self, key:str) -> Optional[MetricWrapperBase]:
        out = self.metrics[key]
        if out is None:
              log.error(f"Could not update metric {key} because it was none.")
        return out
    
    def _get_instance_metric(self, key:str) -> Optional[MetricWrapperBase]:
        out = None
        m = self.__get_metric(key)
        if m is not None:
            out = m.labels(self.instance_name)
            if out is None:
                log.error(f"Could instance metric for {self.instance_name}.")
        
        return out
    
    def _get_fetcher_metric(self, key:str, fetcher_id:str) -> Optional[MetricWrapperBase]:
        if key is None or fetcher_id is None:
              log.error("Coulrd not get fetcher metric because at least one parameter was None.")
              return None
        out = None
        m = self.__get_metric(key)
        if m is not None:
            out = m.labels(self.instance_name, fetcher_id)
            if out is None:
                log.error(f"Could fetcher metric for instance {self.instance_name} and fetcher {fetcher_id}.")

        return out
    
    def publish_latest_picture_name(self, latest_picture_name:str, timed:bool) -> None:
        metric = self._get_instance_metric(self.LATEST_PICTURE_TIMED if timed else self.LATEST_PICTURE_COMMANDED)
        if metric is not None and latest_picture_name is not None:
            metric.info({"latest_picture_name": latest_picture_name})
        return None

    def update_general_system_metrics(self) -> None:
        """Update uptime gauge."""
        metric = self._get_instance_metric(self.UPTIME)
        if metric is not None:
            metric.set(time.time() - self.start_time)
            self._update_system_metrics()
        return None
    
    def _update_system_metrics(self):
        """Update CPU, RAM, and Disk usage metrics."""
        self._get_instance_metric(self.USAGE_CPU).set(psutil.cpu_percent(interval=1))
        #psutil.sensors_temperatures() -> {'cpu_thermal': [shwtemp(label='', current=50.15, high=None, critical=None)], 'rp1_adc': [shwtemp(label='', current=50.242, high=None, critical=None)]}
        #TODO: self._get_instance_metric(self.TEMP_CPU).set( )
        self._get_instance_metric(self.USAGE_RAM).set(psutil.virtual_memory().percent)
        self._get_instance_metric(self.USAGE_DISK).set(psutil.disk_usage('/').percent)

    def measure_room_values(self, room_temp:float, humidity:float) -> None:
        if room_temp is not None and humidity is not None:
            m_temp = self._get_instance_metric(self.ROOM_TEMP)
            m_hum = self._get_instance_metric(self.ROOM_HUM)
            if m_temp is not None and m_hum is not None:
                m_temp.set(room_temp)
                m_hum.set(humidity)
        else:
            log.warning("Unable to publish room temp and humidtiy because at least one is None")
        return None 
    
    def measure_outside_temperature(self, fechter_id:str, temperature:float) -> None:
        if fechter_id is not None and temperature is not None:
            m_temp = self._get_fetcher_metric(self.All_OUTSIDE_TEMP, fechter_id)
            if m_temp is not None:
                m_temp.set(temperature)
        else:
            log.warning("Unable to publish measured outside temperature because at least one parameter is None")
        return None

    def observe_fetch_duration(self, duration: float) -> None:
        if duration is None:
            log.warning("Unable to observer fetching time because duration is None")
            return None
        m = self._get_instance_metric(self.ALL_WEATHER_TIME)
        if m is not None:
            m.observe(duration)

    def set_web_available(self, available: bool) -> None:
        metric = self._get_instance_metric(self.WEB_ACCESS)
        if metric is not None:
            metric.set(1 if available else 0)
        return None

    # ------------------- Increase Counter methods ----------------------
    def inc_failed_temp_senor_read(self) -> None:
        metric = self._get_instance_metric(self.ROOM_TEMP_READ_FAILS)
        if metric is not None:
            metric.inc()
        return None
    
    def inc_sent_email(self) -> None:
        metric = self._get_instance_metric(self.SENT_MAILS)
        if metric is not None:
            metric.inc()
        return None
