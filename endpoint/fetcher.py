import urllib.parse
from datetime import datetime

import requests
from bs4 import BeautifulSoup as bs
from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from core.core_log import get_logger
from core.database import TIME_FORMAT

log = get_logger(__name__)


# ----------------------------------------------------------------------------------------------------------------
# The fetching module. Contains data fetcher for retrieving data from defined endpoints.
# ----------------------------------------------------------------------------------------------------------------

class UlmDeFetcher:

    @staticmethod
    def get_data():
        """
        Fetches the temperature data from ulm.de
        """
        try:
            # set connect and read timeout to 5 seconds
            response = requests.get('https://www.ulm.de/', timeout=(5, 5))
        except (
                requests.exceptions.TooManyRedirects, requests.exceptions.Timeout,
                requests.exceptions.ConnectionError) as e:
            log.error(f"Ulm.de connection problem: " + str(e))
            return None

        if response.status_code == 200:
            soup = bs(response.text, 'html.parser')
            temperature_element = soup.find('p', class_='temp')
            if temperature_element:
                try:
                    temperature = int(temperature_element.text.replace("°", "").replace("C", "").strip())
                except ValueError as e:
                    log.error(f"Ulm.de could not parse value {str(e)}")
                    return None
                return temperature
            else:
                log.error("Ulm.de: Temperature element not found on the page.")
                return None
        else:
            log.error("Ulm.de: Failed to retrieve weather data.")
            return None


class WetterComFetcher:
    """
    Wetter.com dynamically updates the value for the current temperature.
    Usually, it first displays a static temperature and then reloads it with a more recent (dynamic) value.

    This class provides a method for catching the static value and 
    another for catching the dynamic value.
    """

    @staticmethod
    def get_data_static(url):
        """
        Fetches the static temperature data from Wetter.com link for a city/region
        """
        try:
            # set connect and read timeout to 5 seconds
            response = requests.get(url, timeout=(5, 5))
        except (
                requests.exceptions.TooManyRedirects, requests.exceptions.Timeout,
                requests.exceptions.ConnectionError) as e:
            log.error(f"Wetter.com connection problem: " + str(e))
            return None

        if response.status_code == 200:
            soup = bs(response.text, 'html.parser')
            temperature_element = soup.find('div', class_='delta rtw_temp')
            if temperature_element:
                try:
                    temperature = int(temperature_element.text.strip().replace("°", "").replace("C", ""))
                    return temperature
                except ValueError as e:
                    log.error(f"Wetter.com could not parse value {str(e)}")
            else:
                log.error("Temperature element not found on the page.")
        else:
            log.error("Failed to retrieve weather data.")

        return None

    @staticmethod
    def get_data_dynamic(url):
        """

        Fetches the dynamic temperature data from Wetter.com link for a city/region
        """
        display = Display(visible=False, size=(1600, 1200))
        display.start()
        options = Options()
        options.add_argument('--disable-blink-features=AutomationControlled')
        service = webdriver.ChromeService(executable_path='/usr/bin/chromedriver')
        driver = webdriver.Chrome(service=service, options=options)
        timeout_s = 30
        driver.set_page_load_timeout(timeout_s)
        driver.implicitly_wait(timeout_s)
        out = None
        try:
            driver.get(url)
            found_temp = driver.find_element(By.XPATH, '//div[@class="delta rtw_temp"]')
            out = int(found_temp.text.replace('°C', ''))
        except (WebDriverException, Exception) as e:
            log.error(f"An error occurred while dynamically fetching temperature data: {str(e)}")
            out = None
        finally:
            display.stop()
            driver.quit()

        return out


class GoogleFetcher:

    @staticmethod
    def get_weather_data(location: str):
        """
        Fetches data from Google Weather for a specific location.

        :location: e.g. "New York"
        """

        url = "https://www.google.com/search?lr=lang_en&ie=UTF-8&q=weather%20" + location
        display = Display(visible=False, size=(1600, 1200))
        display.start()
        options = Options()
        options.add_argument('--disable-blink-features=AutomationControlled')
        try:
            service = Service('/usr/bin/chromedriver')
            driver = webdriver.Chrome(service=service, options=options)
            driver.get(url)
            timeout_s = 15
            web_wait_timeout = 10
            driver.set_page_load_timeout(timeout_s)
            driver.implicitly_wait(timeout_s)

            # print(driver.page_source)
            WebDriverWait(driver, web_wait_timeout).until(
                EC.presence_of_element_located((By.ID, "wob_loc"))
            )

            soup = bs(driver.page_source, "html.parser")

            weather_data = {
                "region": soup.find("div", attrs={"id": "wob_loc"}).text,
                "temp_now": float(soup.find("span", attrs={"id": "wob_tm"}).text),
                "precipitation": float(soup.find("span", attrs={"id": "wob_pp"}).text.replace("%", "")),
                "humidity": float(soup.find("span", attrs={"id": "wob_hm"}).text.replace("%", "")),
                "wind": float(soup.find("span", attrs={"id": "wob_ws"}).text.replace(" km/h", ""))
            }
            driver.quit()
            display.stop()
            return weather_data

        except Exception as e:
            print(f"Error fetching weather data: {e}")
            if 'driver' in locals():
                driver.quit()
            display.stop()
            return None


class Fetcher:
    """
    Default class for fetching data.
    It provides methods for handling error and ok responses from the server.
    This methods can be overwritten by an extending class.
    """

    def __init__(self, endpoint: str, params: list = None):
        self.endpoint = endpoint
        self.params = None if not params else urllib.parse.urlencode(params)
        self.api_link = self._create_api_link()
        self.timeouts = (30, 5)  # connect timeout 30s and read timeout 5s

    def __str__(self):
        return f"Fetcher[{self.api_link}]"

    def _create_api_link(self):
        return self.endpoint + "?" + self.params if self.params else self.endpoint

    def _fetch_data(self):
        try:
            response = requests.get(self.api_link, timeout=self.timeouts)
            if (code := response.status_code) == 200:
                return self._handle_ok_status_code(response)
            else:
                return self._handle_bad_status_code(code)
        except (
                requests.exceptions.TooManyRedirects, requests.exceptions.Timeout,
                requests.exceptions.ConnectionError) as e:
            log.error(f"Creating the connection failed with error: {e}")
            return None

    def _handle_ok_status_code(self, response):
        return response.json()

    def _handle_bad_status_code(self, code):
        log.error(f"Error: Failed to fetch weather data. Status code: {code}")
        return None


class DWDFetcher(Fetcher):
    """
    DataFetcher for retrieving data from Deutsche Wetterdienst (DWD).
    One fetcher is responsible for the data of one weather station.
    """

    def __init__(self, station_id):
        super().__init__("https://app-prod-ws.warnwetter.de/v30/stationOverviewExtended", [("stationIds", station_id)])
        self.station_id = station_id
        self.data = None

    def __str__(self):
        return f"DWDFetcher[{self.station_id}, {super().__str__()}]"

    def _handle_ok_status_code(self, response):
        json_res = super()._handle_ok_status_code(response)
        self.data = json_res[str(self.station_id)]["forecast1"]
        return self.data

    def _get_index(self, current_time=None):
        """
        Calculate index for measurement based on current year, month, date and hour.
        Remaining values will be ignored.
        """

        if not current_time:
            current_time = datetime.now()
        if isinstance(current_time, str):
            current_time = datetime.strptime(current_time, TIME_FORMAT)

        current_time = datetime(year=current_time.year, month=current_time.month, day=current_time.day,
                                hour=current_time.hour, minute=0, second=0, microsecond=0, tzinfo=None, fold=0)

        # from milliseconds to seconds
        start_measurement_time_s = self.data["start"] / 1000
        # TODO: Fix deprecated method usage
        m_time = datetime.utcfromtimestamp(start_measurement_time_s)
        diff = current_time - m_time
        return int(diff.total_seconds() / (self.data["timeStep"] / 1000))

    def clear_cached_data(self):
        self.data = None

    def get_dwd_data(self, trigger_new_fetch=True):
        if trigger_new_fetch:
            self.clear_cached_data()

        if self.data is None:
            log.info("Fetching new data")
            self.data = self._fetch_data()
            if self.data is None:
                # fetching data was not possible, abort
                return None, None, None

        temp_values = self.data["temperature"]
        # observation: temperatureStd is 0 for unlikely temperatures such as 3241.6 °C
        temp_std = self.data["temperatureStd"]
        # ignore minutes, seconds and microseconds
        current_time = datetime(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day,
                                hour=datetime.now().hour,
                                minute=0, second=0, microsecond=0, tzinfo=None, fold=0)

        if len(temp_std) != len(temp_values):
            log.error(f"Error: Unable to validate DWD temperature data because temp values and std differ!")
            return current_time, None, None

        current_temp_forecast_index = self._get_index()
        if len(temp_values) < current_temp_forecast_index:
            log.error(
                f"Error: Forecast index out of range, size: {len(temp_values)}, index: {current_temp_forecast_index}")
            return current_time, None, None
        elif temp_std[current_temp_forecast_index] == 0:
            log.error(f"Error: 0 tempStd for found temperature {temp_values[current_temp_forecast_index]}")
            return current_time, None, None
        else:
            temp = float(temp_values[current_temp_forecast_index]) / 10.0
            dev = self.data["temperatureStd"][current_temp_forecast_index]
            # log.info(f"Found: {current_temp_forecast_index}, {current_time}, {temp}°C, dev: {dev}")
            return current_time, temp, dev


# TODO: support openweather and weatherAPI
class WeatherAPI:
    @staticmethod
    def get_weather_data(location: str, api_key: str):
        """
        Fetch weather data from OpenWeatherMap API.

        :param location: Location name, e.g., "New York"
        :param api_key: Your OpenWeatherMap API key
        :return: A dictionary with weather data or None if an error occurs.
        """
        url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&units=metric&appid={api_key}"
        try:
            response = requests.get(url, timeout=(5, 5))
            response.raise_for_status()
            data = response.json()
            return {
                "region": data["name"],
                "temp_now": data["main"]["temp"],
                "humidity": data["main"]["humidity"],
                "wind": data["wind"]["speed"]
            }
        except Exception as e:
            print(f"Error fetching weather data: {e}")
            return None
