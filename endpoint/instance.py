import schedule
from typing import List, Tuple, Optional
from core.core_log import get_logger
from core.database import UlmDeHandler
from core.instance import CoreSkeleton
from core.plotting import PlotData, SupportedDataFrames
from core.usage_util import init_database
from core.util import require_web_access
from core.core_configuration import database_config, dwd_config, google_config, wettercom_config

from endpoint.usage_util import ulmde_fetch_and_save, wettercom_fetch_and_save, google_fetch_and_save, \
    dwd_fetch_and_save

log = get_logger(__name__)

# comparison should always be made with lower case. Casing here is for displaying the name
SUPPORTED_INSTANCES = ["FetchTemp"]


class FetchTemp(CoreSkeleton):

    ## --- Initialization Part ---

    # extending constructor
    def __init__(self, instance_name: str,  core_instance_validation: List[str] = SUPPORTED_INSTANCES):
        super().__init__(instance_name=instance_name, core_instance_validation=core_instance_validation)
        
    def _setup_scheduling(self) -> None:
        schedule.every(10).minutes.do(lambda: self.collect_and_save_to_db())

    def _add_commands(self) -> None:
        pass

    # overwrite
    def run_received_commands(self) -> None:
        pass

    def _get_visualization_data(self) -> Tuple[List[PlotData], List[PlotData]]:
        pass

    def _send_visualization_email(self, data: List[PlotData], save_path: str,
                                  email_receiver: Optional[str] = None) -> None:
        pass

    # overwrite
    def _init_database(self):
        init_database(UlmDeHandler, database_config(), SupportedDataFrames.ULM_DE.table_name)

    # overwrite
    @require_web_access
    def collect_and_save_to_db(self) -> Optional[Tuple]:
        db_auth = database_config()
        ulmde_fetch_and_save(db_auth)
        dwd_fetch_and_save(db_auth, dwd_config())
        google_fetch_and_save(db_auth, google_config())
        wettercom_fetch_and_save(db_auth, wettercom_config())
