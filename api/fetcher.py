import logging
from api.api_logger import api_log as log
import requests
from datetime import datetime
log = logging.getLogger('api.fetcher') 


class DataFetcher():

    def __init__(self, endpoint:str, params=None):
        self.endpoint = endpoint
        self.params = params
        self.api_link = self._create_api_link()

    def __str__(self):
        return f"{self.api_link}"

    def _create_api_link(self):
        return self.endpoint + "?" + self.params if self.params else self.endpoint

    def _fetch_data(self):
        response = requests.get(self.api_link)
        if (code := response.status_code) == 200:
            return self._handle_ok_status_code(response)
        else:
           self._handle_bad_status_code(code)

    def _handle_ok_status_code(self, response):
        return response.json()

    def _handle_bad_status_code(self, code:int) -> int:
        log.error(f"Error: Failed to fetch weather data. Status code: {code}")
        return code
    
    
class DWDFetcher(DataFetcher):
            
    def __init__(self, endpoint:str, params=None):
        super().__init__(endpoint, params)
        self.data = None
        self.station_code = params.replace("stationIds=", "")


    def __str__(self):
        return f"DWDFetcher[{self.station_code}, {super().__str__()}]"
    
    def _handle_ok_status_code(self, response):
            json_res = super()._handle_ok_status_code(response)
            self.data = json_res[self.station_code]["forecast1"]
            return self.data
    
    def clear_cached_data(self):
            self.data = None

    def get_dwd_data(self, trigger_new_fetch=True):
        if trigger_new_fetch:
            self.clear_cached_data()

        if self.data is None:
            log.info("Fetching new data")
            self.data = self._fetch_data()

        temp_values = self.data["temperature"]
        #observation: temperatureStd is 0 for unlikly temperatures such as 3241.6 °C
        temp_std = self.data["temperatureStd"]
        # ignore minutes, seconds and microseconds
        current_time = datetime(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day, hour=datetime.now().hour, 
                                minute=0, second=0, microsecond=0, tzinfo=None, fold=0)

        if len(temp_std) != len(temp_values):
            log.error(f"Error: Unable to validate DWD temperature data because temp values and std differ!")
            return current_time, float('nan')

        # Calculate index of current temperature measurement
        # from milliseconds to seconds
        start_measurment_time_s  = self.data["start"] / 1000
        m_time = datetime.utcfromtimestamp(start_measurment_time_s)
        diff = current_time - m_time
        current_temp_forecast_index = int(diff.total_seconds() / (self.data["timeStep"] / 1000))
        if len(temp_values) < current_temp_forecast_index:
            log.error(f"Error: Forecast index out of range, size: {len(temp_values)}, index: {current_temp_forecast_index}")
            return current_time, float('nan')
        elif temp_std[current_temp_forecast_index] == 0:
            log.error(f"Error: 0 tempStd for found temperature {temp_values[current_temp_forecast_index]}")
            return current_time, float('nan')
        else:
            temp = float(temp_values[current_temp_forecast_index])
            log.info(f"Found: {current_temp_forecast_index}, {current_time}, {temp / 10.0}°C, dev: {self.data['temperatureStd'][current_temp_forecast_index]}")
            return current_time, temp 


            
            
                