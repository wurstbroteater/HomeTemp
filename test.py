from api.api_logger import api_log as log
from api.fetcher import DWDFetcher

ulm_station_code = '10838'
fetcher = DWDFetcher("https://app-prod-ws.warnwetter.de/v30/stationOverviewExtended", f"stationIds={ulm_station_code}")
fetcher.get_dwd_data()