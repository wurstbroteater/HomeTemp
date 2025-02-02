from configparser import SectionProxy

from core.core_log import get_logger
import time
from datetime import datetime
from typing import List, Optional, Tuple, Type

import schedule

from abc import ABC, abstractmethod
from core.command import CommandService
from core.sensors.dht import SUPPORTED_SENSORS
from core.core_configuration import database_config, core_config, get_sensor_type, basetemp_config, \
    update_active_schedule

from core.database import DwDDataHandler, GoogleDataHandler, UlmDeHandler, SensorDataHandler, WetterComHandler

from core.distribute import send_picture_email, send_visualization_email, send_heat_warning_email
from core.plotting import PlotData, SupportedDataFrames, draw_complete_summary
from core.usage_util import init_database, get_data_for_plotting, retrieve_and_save_sensor_data, take_picture

log = get_logger(__name__)

# comparison should always be made with lower case. Casing here is for displaying the name
SUPPORTED_INSTANCES = ["HomeTemp", "BaseTemp"]


# ----------------------------------------------------------------------------------------------------------------
# An extension of CoreSkeleton must implement abstract methods to guarantee minimal features.
# ----------------------------------------------------------------------------------------------------------------
class CoreSkeleton(ABC):
    def __init__(self, instance_name: str):
        self.instance_name = {i.lower(): i for i in SUPPORTED_INSTANCES}.get(instance_name.lower(), None)
        if self.instance_name is None:
            log.error(f"CoreSkeleton got unsupported initializer {instance_name}")

        self.command_service: CommandService = CommandService()

    ## --- Initialization Part ---
    def start(self) -> None:
        log.info(f"------------------- {self.instance_name} v{core_config()['version']} -------------------")
        self._init_components()
        log.info("finished initialization")
        self._methods_after_init()
        time.sleep(1)
        self.run_received_commands()
        log.info("entering main loop")
        self.main_loop()

    def _init_components(self) -> None:
        self._init_database()
        self._add_commands()
        self._setup_scheduling()

    def _init_database(self):
        init_database(SensorDataHandler, database_config(), SupportedDataFrames.Main.table_name)

    @abstractmethod
    def _add_commands(self) -> None:
        pass

    @abstractmethod
    def _setup_scheduling(self) -> None:
        pass

    def _methods_after_init(self) -> None:
        self.collect_and_save_to_db()

    def run_received_commands(self) -> None:
        log.info("Checking for commands")
        self.command_service.receive_and_execute_commands()
        log.info("Done")

    def main_loop(self, check_schedule_delay_s=1) -> None:
        while True:
            schedule.run_pending()
            time.sleep(check_schedule_delay_s)

    ## --- Minimal Supported Features Part ---

    @abstractmethod
    def _get_visualization_data(self) -> Tuple[List[PlotData], List[PlotData]]:
        # first list is plots and second list is merge subplots for
        pass

    @abstractmethod
    def _send_visualization_email(self, data: List[PlotData], save_path: str,
                                  email_receiver: Optional[str] = None) -> None:
        pass

    def _create_visualization(self, mode: str, save_path_template: str, email_receiver: Optional[str] = None) -> None:
        log.info(f"{mode}: Creating Measurement Data Visualization")
        plots, merge_subplots_for = self._get_visualization_data()
        name = datetime.now().strftime("%d-%m-%Y")
        save_path = save_path_template.format(name=name)
        draw_complete_summary(plots, merge_subplots_for=merge_subplots_for, save_path=save_path)
        log.info(f"{mode}: Done")
        self._send_visualization_email(plots, save_path, email_receiver)

    def create_visualization_commanded(self, commander: str) -> None:
        self._create_visualization(mode="Command", save_path_template="plots/commanded/{name}.pdf",
                                   email_receiver=commander)

    def create_visualization_timed(self) -> None:
        self._create_visualization(mode="Timed", save_path_template="plots/{name}.pdf")

    def collect_and_save_to_db(self) -> Optional[Tuple]:
        is_dht11 = get_sensor_type(SUPPORTED_SENSORS) == SUPPORTED_SENSORS[0]
        auth = database_config()
        sensor_pin = int(core_config()["sensor_pin"])
        out = retrieve_and_save_sensor_data(auth, sensor_pin, is_dht11)
        log.info("Done")
        return out


class HomeTemp(CoreSkeleton):

    ## --- Initialization Part ---

    def _add_commands(self) -> None:
        cmd_name = 'plot'
        function_params = ['commander']
        self.command_service.add_new_command((cmd_name, [], self.create_visualization_commanded, function_params))
        pass

    def _setup_scheduling(self) -> None:
        schedule.every(10).minutes.do(lambda _: self.collect_and_save_to_db())
        schedule.every().day.at("06:00").do(lambda _: self.create_visualization_timed())
        schedule.every(10).minutes.do(lambda _: self.run_received_commands())
        pass

    def _methods_after_init(self) -> None:
        super()._methods_after_init()
        self.create_visualization_timed()

    ## --- Minimal Supported Features Part ---

    def _get_visualization_data(self) -> Tuple[List[PlotData], List[PlotData]]:
        auth = database_config()
        df = get_data_for_plotting(auth, SensorDataHandler, SupportedDataFrames.Main)
        google_df = get_data_for_plotting(auth, GoogleDataHandler, SupportedDataFrames.GOOGLE_COM)
        dwd_df = get_data_for_plotting(auth, DwDDataHandler, SupportedDataFrames.DWD_DE)
        wettercom_df = get_data_for_plotting(auth, WetterComHandler, SupportedDataFrames.WETTER_COM)
        ulmde_df = get_data_for_plotting(auth, UlmDeHandler, SupportedDataFrames.ULM_DE)

        out = [
            PlotData(SupportedDataFrames.Main, df, True),
            PlotData(SupportedDataFrames.DWD_DE, dwd_df),
            PlotData(SupportedDataFrames.GOOGLE_COM, google_df),
            PlotData(SupportedDataFrames.WETTER_COM, wettercom_df),
            PlotData(SupportedDataFrames.ULM_DE, ulmde_df)]

        return out, out

    def _send_visualization_email(self, data: List[PlotData], save_path: str,
                                  email_receiver: Optional[str] = None) -> None:
        send_visualization_email(
            df=data[0].data,
            ulmde_df=data[4].data,
            google_df=data[2].data,
            dwd_df=data[1].data,
            wettercom_df=data[3].data,
            path_to_pdf=save_path,
            receiver=email_receiver)


class BaseTemp(CoreSkeleton):
    # TODO: command to switch schedule

    ## --- Initialization Part ---
    def __init__(self, instance_name: str):
        super().__init__(instance_name)
        cfg: SectionProxy = basetemp_config()
        self.max_heat = cfg.get("max_heat", None)
        self.min_heat = cfg.get("min_heat", None)
        self.send_temperature_warning = not (self.max_heat is None and self.min_heat is None)
        self.active_schedule = cfg.get("active_schedule", "").lower()
        # comparison should always be made lower case
        self.supported_schedules = ['phase1', 'phase2', 'common']

    def set_schedule(self, s_name: str) -> None:
        self._set_schedule(s_name)
        update_active_schedule(self.active_schedule)

    def _set_schedule(self, new_schedule: str) -> None:
        new_schedule = new_schedule.lower().strip()
        if new_schedule not in self.supported_schedules:
            log.warning(f"Unsupported schedule {new_schedule}")
        else:
            log.info(f"Setting new schedule: {new_schedule}")
        self.active_schedule = new_schedule

    def _add_commands(self) -> None:
        picture_cmd_name = 'pic'
        picture_fun_params = ['commander']
        self.command_service.add_new_command((picture_cmd_name, [], self.take_picture_commanded, picture_fun_params))
        vis_cmd_name = 'plot'
        vis_fun_params = ['commander']
        self.command_service.add_new_command((vis_cmd_name, [], self.create_visualization_commanded, vis_fun_params))
        pass

    def _get_current_schedule(self) -> List[schedule.Job]:
        if self.active_schedule == 'common':
            return [schedule.every(10).minutes.do(lambda _: self.run_received_commands()),
                    schedule.every(10).minutes.do(lambda _: self.collect_and_save_to_db()),
                    schedule.every().day.at("08:00").do(lambda _: self.create_visualization_timed())]
        elif self.active_schedule == 'phase1':
            # return [schedule.every(10).minutes.do(lambda _: self.run_received_commands()),
            #        schedule.every(10).minutes.do(lambda _: self.collect_and_save_to_db()),
            #        schedule.every().day.at("11:45").do(lambda _: self.create_visualization_timed()),
            #        schedule.every().day.at("19:00").do(lambda _: self.create_visualization_timed()),
            #        schedule.every().day.at("03:00").do(lambda _: self.create_visualization_timed()),
            #        schedule.every().day.at("10:30").do(lambda _: self.create_visualization_timed())]
            pass
        elif self.active_schedule == 'phase2':
            # return [schedule.every(10).minutes.do(lambda _: self.run_received_commands()),
            #        schedule.every(10).minutes.do(lambda _: self.collect_and_save_to_db()),
            #        schedule.every().day.at("08:00").do(lambda _: self.create_visualization_timed()),
            #        schedule.every().day.at("06:00").do(lambda _: self.create_visualization_timed()),
            #        schedule.every().day.at("02:00").do(lambda _: self.create_visualization_timed()),
            #       schedule.every().day.at("20:00").do(lambda _: self.create_visualization_timed())]
            pass
        else:
            log.warning(f"Unsupported schedule {self.active_schedule}")

        return []

    def _setup_scheduling(self) -> None:
        self._get_current_schedule()
        log.info(f"Initialized schedule: {self.active_schedule}")
        pass

    def switch_schedule(self, new_schedule: str) -> None:
        # TODO: Figure out how to reset active schedule instqnce
        # old_tasks = self._get_current_schedule()
        # for job in old_tasks:
        #    job.cancel()
        # self._set_schedule(new_schedule)
        pass

    def _methods_after_init(self) -> None:
        super()._methods_after_init()
        self.create_visualization_timed()

    ## --- Minimal Supported Features Part ---

    def _get_visualization_data(self) -> Tuple[List[PlotData], List[PlotData]]:
        auth = database_config()
        df = get_data_for_plotting(auth, SensorDataHandler, SupportedDataFrames.Main)
        return [PlotData(SupportedDataFrames.Main, df, True)], []

    def _send_visualization_email(self, data: List[PlotData], save_path: str,
                                  email_receiver: Optional[str] = None) -> None:
        send_visualization_email(df=data[0].data, path_to_pdf=save_path, receiver=email_receiver)

    ## --- Instance Specific Features Part ---

    def take_picture_timed(self) -> None:
        log.info("Timed: Taking picture")
        name = f'pictures/{datetime.now().strftime("%Y-%m-%d-%H:%M:%S")}'
        if take_picture(name):
            log.info("Timed: Taking picture done")
        else:
            log.info("Timed: Taking picture was not successful")

    def take_picture_commanded(self, commander: str) -> None:
        log.info("Command: Taking picture")
        name = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
        encoding = "png"
        save_path = f"pictures/commanded/{name}"
        if take_picture(save_path, encoding=encoding):
            log.info("Command: Taking picture done")
            plots, _ = self._get_visualization_data()
            sensor_data = plots[0].data
            send_picture_email(picture_path=f"{save_path}.{encoding}", df=sensor_data, receiver=commander)
            log.info("Command: Done")
        else:
            log.info("Command: Taking picture was not successful")

    def collect_and_save_to_db(self) -> Optional[Tuple]:
        t = super().collect_and_save_to_db()
        if t is None or not self.send_temperature_warning:
            return t

        room_temp = t[2]
        if self.max_heat is not None and room_temp > self.max_heat:
            indicator, extremum = "above", self.max_heat
        elif self.min_heat is not None and room_temp < self.min_heat:
            indicator, extremum = "below", self.min_heat
        else:
            return t

        log.warning(f"Sending heat warning because room temp is {indicator} {extremum}°C")
        send_heat_warning_email(room_temp)
        return t


# ----------------------------------------------------------------------------------------------------------------
# Static utility methods
# ----------------------------------------------------------------------------------------------------------------

def get_supported_instance_type(instance_name: str) -> Type[CoreSkeleton]:
    # see comment on SUPPORTED_INSTANCES for details
    if instance_name == SUPPORTED_INSTANCES[0].lower():
        return HomeTemp
    elif instance_name == SUPPORTED_INSTANCES[1].lower():
        return BaseTemp
    log.error(f"Unsupported Instance {instance_name}")
    exit(1)
