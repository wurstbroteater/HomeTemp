from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from core.core_configuration import wettercom_config
from endpoint.fetcher import WetterComFetcher


def get_data_dynamic(url):
    display = Display(visible=0, size=(1600, 1200))
    display.start()
    options = Options()
    options.add_argument('--disable-blink-features=AutomationControlled')
    service = webdriver.ChromeService(executable_path='/usr/lib/chromium-browser/chromedriver')
    driver = webdriver.Chrome(service=service, options=options)
    try:
        driver.get(url)
        # ids = driver.find_elements(By.XPATH, '//*[@id]')
        # print(len(ids))
        # for ii in ids:
        #    print('Tag: ' + ii.tag_name)
        #    try:
        #        print('ID: ' + ii.get_attribute('class'))     # element id as string
        #    except TypeError as e:
        #        print('No class')

        found_temp = driver.find_element(By.XPATH, '//div[@class="delta rtw_temp"]')
        return int(found_temp.text.replace('°C', ''))

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None
    finally:
        driver.quit()


if __name__ == "__main__":
    w_conf = wettercom_config()
    temp_fetch_stat = WetterComFetcher.get_data_static(w_conf["url"][1:-1])
    temp_fetch_dyn = get_data_dynamic(w_conf["url"][1:-1])
    # temp_fetch_dyn = WetterComFetcher.get_data_dynamic(w_conf["url"][1:-1])

    print(f"stat vs dyn temp: {temp_fetch_stat} vs {temp_fetch_dyn}")
