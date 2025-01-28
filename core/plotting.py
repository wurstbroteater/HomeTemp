from core.core_log import get_logger
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from enum import Enum
from matplotlib.axes import Axes
from typing import Callable, Tuple, List, Optional, Dict, Any
from datetime import datetime, timedelta

log = get_logger(__name__)

# ----------------------------------------------------------------------------------------------------------------
# The visualization module. Provides means to create a plot for sensor data and is able to save them to pdf.
# A goal of the architecture is to easliy incorporate new plots and and new plot configurations, i.e., 
# plot arrangements, plot theme, label names and seaborn parameters. 
# See changelog.md 0.5 for class details.
# ----------------------------------------------------------------------------------------------------------------


custom_theme = {
    'context': 'paper',  # Can be 'paper', 'notebook', 'talk', 'poster'
    'style': 'darkgrid',  # Can be 'darkgrid', 'whitegrid', 'dark', 'white', 'ticks'
    'palette': 'deep'  # Can be 'deep', 'muted', 'bright', 'pastel', etc.
}

#@formatter:off
TEMP_TUPLE_DEFAULT = ("temp", None)

# These functions represent direct seaborn plot parameters
MINIMAL_INNER = lambda df, label, y: {"data": df, "label": label, "x": "timestamp", "y": y, "alpha": 0.6}
MINIMAL_INNER_24 = lambda df, label, y: {"data": df, "label": label, "x": "timestamp", "y": y, "alpha": 0.6, "marker": "o", "markersize": 6}

NOT_DIRECT_PARAMS = ["title", "xlabel", "ylabel"]
# These functions represent seaborn plot configurations, i.e., direct seaborn plot parameters and some for configurinig main plot, see NOT_DIRECT_PARAMS
MINIMAL_MAIN = lambda title, ylabel, y: {"title": title, "xlabel": "Time", "ylabel": ylabel, "label": "Home", "x": "timestamp", "y": y}
MINIMAL_MAIN_24 = lambda title, ylabel, y: {"title": title, "xlabel": "Time", "ylabel": ylabel, "label": "Home", "x": "timestamp", "y": y, "marker": "o", "markersize": 6}
# @formatter:on

class SupportedDataFrames(Enum):
    # enumIdx, name, temperature keys list of tuple (df key, plot label with None for default see _label) , humidity key
    Main = 1, "Room", [("room_temp", None)], "humidity"
    DWD_DE = 2, "DWD", [TEMP_TUPLE_DEFAULT], None
    GOOGLE_COM = 3, "Google.de", [TEMP_TUPLE_DEFAULT], "humidity"
    WETTER_COM = 4, "Wetter.com", [("temp_stat", "Forecast"), ("temp_dyn", "Live")], None
    ULM_DE = 5, "Ulm.de", [TEMP_TUPLE_DEFAULT], None

    def __init__(self, enum_idx: int, display_name: str, temperature_keys: list, humidity_key: str):
        self.enum_idx = enum_idx
        self.display_name = display_name
        self.temperature_keys = temperature_keys
        self.humidity_key = humidity_key

    def _label(self, label_overwrite: Optional[str] = None) -> str:
        if label_overwrite is None:
            return f"{self.display_name} Forecast"
        else:
            return f"{self.display_name} {label_overwrite}"

    def get_temperature_keys(self) -> list[str]:
        return list(map(lambda x: x[0], [] if self.temperature_keys is None else self.temperature_keys))

    def get_temperatures(self, data: pd.DataFrame, optional_keys: list = None) -> pd.DataFrame:
        if optional_keys is None:
            optional_keys = []
        return data[self.get_temperature_keys() + optional_keys]

    def get_humidity(self, data: pd.DataFrame, optional_keys: list = []) -> pd.DataFrame:
        keys = [] if self.humidity_key is None else [self.humidity_key]
        return data[keys + optional_keys]

    # --- parameters for configuring seaborn. ---
    def get_temp_inner_plots_params(self, data: pd.DataFrame) -> Optional[list]:

        if self is SupportedDataFrames.Main:
            return None
        return list(
            map(lambda temp_keys: MINIMAL_INNER(data, self._label(temp_keys[1]), temp_keys[0]), self.temperature_keys))

    def get_hum_inner_plots_params(self, data: pd.DataFrame) -> Optional[list]:
        if self.humidity_key is not None:
            return [MINIMAL_INNER(data, self._label(), self.humidity_key)]
        return None

    def get_temp_24h_inner_plots_params(self, data: pd.DataFrame) -> Optional[list]:
        # TODO: ASSURE 24 h ?
        if self is SupportedDataFrames.Main:
            return None
        elif self is SupportedDataFrames.WETTER_COM:
            return [MINIMAL_INNER_24(data, self._label(self.temperature_keys[0][1]), self.temperature_keys[0][0]),
                    MINIMAL_INNER_24(data, self._label(self.temperature_keys[1][1]), self.temperature_keys[1][0]) | {
                        "marker": "s"}]

        return list(map(lambda temp_keys: MINIMAL_INNER_24(data, self._label(temp_keys[1]), temp_keys[0]),
                        self.temperature_keys))

    def get_hum_24h_inner_plots_params(self, data: pd.DataFrame) -> Optional[list]:
        if self.humidity_key is not None:
            return [MINIMAL_INNER_24(data, self._label(), self.humidity_key) | {"alpha": 1}]
        return None


class PlotData:

    def __init__(self, support: SupportedDataFrames, data: pd.DataFrame, is_main_plot: bool = False):
        self.support: SupportedDataFrames = support
        self.data: pd.DataFrame = data
        self.main: bool = is_main_plot

    def __str__(self):
        return f"{self.main} {self.support} {len(self.data)}"

    def inner_params(self) -> list:
        return self.support.get_temp_inner_plots_params(self.data)

    def inner_params_hum(self) -> list:
        return self.support.get_hum_inner_plots_params(self.data)

    def inner_24_params(self) -> list:
        return self.support.get_temp_24h_inner_plots_params(last_24h_df(self.data))

    def inner_24_params_hum(self) -> list:
        return self.support.get_hum_24h_inner_plots_params(last_24h_df(self.data))

    def get_temperatures(self, optional_keys=[]) -> pd.DataFrame:
        return self.support.get_temperatures(data=self.data, optional_keys=optional_keys)

    def get_humidity(self) -> pd.DataFrame:
        return self.support.get_humidity(self.data, optional_keys=["timestamp"])

    def get_24_temperatures(self, optional_keys=[]) -> pd.DataFrame:
        return self.support.get_temperatures(data=last_24h_df(self.data), optional_keys=optional_keys)

    def get_24_humidity(self) -> pd.DataFrame:
        return self.support.get_humidity(last_24h_df(self.data), optional_keys=["timestamp"])


class PlotDataSelector(Enum):
    HUMIDITY24 = 1
    HUMIDITYALL = 2
    TEMP24 = 3
    TEMPALL = 4

    def __init__(self, enum_idx: int):
        self.enum_idx = enum_idx

    def select_data(self, plot_data: PlotData) -> Callable:
        data_method_map = {
            PlotDataSelector.HUMIDITY24: plot_data.get_24_humidity,
            PlotDataSelector.HUMIDITYALL: plot_data.get_humidity,
            PlotDataSelector.TEMP24: plot_data.get_24_temperatures,
            PlotDataSelector.TEMPALL: plot_data.get_temperatures
        }
        return data_method_map[self]

    def select_params(self, plot_data: PlotData) -> Callable:
        param_method_map = {
            PlotDataSelector.HUMIDITY24: plot_data.inner_24_params_hum,
            PlotDataSelector.HUMIDITYALL: plot_data.inner_params_hum,
            PlotDataSelector.TEMP24: plot_data.inner_24_params,
            PlotDataSelector.TEMPALL: plot_data.inner_params,
        }
        return param_method_map[self]


class DefaultPlotCategory:
    @staticmethod
    def MERGED(plot_data: List[PlotData], merge_subplots_for: List[PlotData], ax_in_subplot: plt.Axes) -> plt.Axes:
        main_plot = DefaultPlotCategory._get_main(plot_data)
        merged = DefaultPlotCategory._merge_temperature_by_timestamp(main_plot, merge_subplots_for)
        return DefaultPlotCategory._create_merged_temperature_plot(merged, ax_in_subplot=ax_in_subplot)[1]

    @staticmethod
    def MERGED24(plot_data: List[PlotData], merge_subplots_for: List[PlotData], ax_in_subplot: plt.Axes) -> plt.Axes:
        main_plot = DefaultPlotCategory._get_main(plot_data)
        merged = DefaultPlotCategory._merge_temperature_by_timestamp(main_plot, merge_subplots_for,
                                                                     df_filter_fun=last_24h_df)
        return DefaultPlotCategory._create_merged_temperature_plot(merged, ax_in_subplot=ax_in_subplot)[1]

    @staticmethod
    def _get_main(plot_data: List[PlotData]) -> PlotData:
        main_plot = [p for p in plot_data if p.main]
        l = len(main_plot)
        if l == 0:
            msg = "Unable to draw plots without main PlotData!"
            log.error(msg)
            raise AssertionError(msg)
        elif l > 1:
            log.info("Found more than 1 main plot. Using first one for plotting")
        return main_plot[0]

    @staticmethod
    def _merge_temperature_by_timestamp(main_data: PlotData, dataframes_info: List[PlotData],
                                        timestamp_col: str = 'timestamp', tolerance: int = 5.5,
                                        df_filter_fun=None) -> pd.DataFrame:

        main_df = main_data.get_temperatures([timestamp_col]) if df_filter_fun is None else df_filter_fun(
            main_data.get_temperatures([timestamp_col]))
        main_df_len = len(main_df)
        time_delta = timedelta(minutes=tolerance)
        inside_temp_base = main_data.get_temperatures().values if df_filter_fun is None else \
            df_filter_fun(main_data.get_temperatures([timestamp_col]))[main_data.support.get_temperature_keys()].values
        inside_temps = list(map(lambda packed_value: packed_value[0], inside_temp_base))

        outside_min = np.full(main_df_len, np.nan)
        outside_max = np.full(main_df_len, np.nan)
        outside_mean = np.full(main_df_len, np.nan)

        for p_data in dataframes_info:
            if main_df_len == 0:
                break
            df = p_data.get_temperatures([timestamp_col]) if df_filter_fun is None else df_filter_fun(
                p_data.get_temperatures([timestamp_col]))
            if len(df) == 0:
                log.debug("skipping empty dataframe")
                continue
            if p_data.main:
                log.debug("MERGED main df should not be contained in this list. skipping it.")
                continue

            aligned_df = pd.merge_asof(
                left=main_df[[timestamp_col]],
                right=df,
                on=timestamp_col,
                tolerance=time_delta,
                direction='nearest'
            )

            temps_in_interval = aligned_df[p_data.support.get_temperature_keys()].values

            # ignoring NaN values
            row_min = np.nanmin(temps_in_interval, axis=1)
            row_max = np.nanmax(temps_in_interval, axis=1)
            row_mean = np.nanmean(temps_in_interval, axis=1)

            # Update outside min, max, mean using np.nanmin/max/mean to handle overlapping DataFrames
            outside_min = np.nanmin([outside_min, row_min], axis=0)
            outside_max = np.nanmax([outside_max, row_max], axis=0)
            outside_mean = np.nanmean([outside_mean, row_mean], axis=0)

        out = {
            timestamp_col: main_df[timestamp_col],
            'inside_temp': inside_temps,
            'outside_min': outside_min,
            'outside_max': outside_max,
            'outside_mean': outside_mean
        }
        return pd.DataFrame(out)

    @staticmethod
    def _create_merged_temperature_plot(df: pd.DataFrame,
                                        x_col: str = 'timestamp',
                                        min_temp_col: str = 'outside_min',
                                        max_temp_col: str = 'outside_max',
                                        room_temp_col: str = 'inside_temp',
                                        theme: Optional[dict] = None,
                                        ax_in_subplot: Axes = None) -> tuple[plt.Figure, plt.Axes]:

        df['mean_temp_outside'] = (df[min_temp_col] + df[max_temp_col]) / 2

        if theme:
            sns.set_theme(**theme)

        if ax_in_subplot:
            fig = None
            ax = ax_in_subplot
        else:
            fig, ax = plt.subplots(figsize=(25, 12))

        sns.lineplot(x=x_col, y=min_temp_col, data=df, label='Min Outside Temp',
                     color='lightblue', linewidth=2, linestyle='--', ax=ax)
        sns.lineplot(x=x_col, y=max_temp_col, data=df, label='Max Outside Temp',
                     color='lightblue', linewidth=2, linestyle='--', ax=ax)
        sns.lineplot(x=x_col, y='mean_temp_outside', data=df, label='Mean Outside Temp',
                     color='purple', alpha=0.4, linewidth=2, linestyle='-.', ax=ax)
        sns.lineplot(x=x_col, y=room_temp_col, data=df, label='Room Temp Inside', ax=ax)

        ax.fill_between(df[x_col], df[min_temp_col], df[max_temp_col], color='lightblue', alpha=0.4)

        plt.xticks(rotation=45)
        plt.tight_layout()

        return fig, ax

    @staticmethod
    def DISTINCT(selector: PlotDataSelector, plot_data: List[PlotData], ax_in_subplot: plt.Axes,
                 main_cfg: dict) -> plt.Axes:
        return DefaultPlotCategory._plot_distinct(selector=selector, plot_data=plot_data, ax_in_subplot=ax_in_subplot,
                                                  main_cfg=main_cfg)

    @staticmethod
    def DISTINCT24(selector: PlotDataSelector, plot_data: List[PlotData], ax_in_subplot: plt.Axes,
                   main_cfg: dict) -> plt.Axes:
        return DefaultPlotCategory._plot_distinct(selector=selector, plot_data=plot_data, ax_in_subplot=ax_in_subplot,
                                                  main_cfg=main_cfg, transform_main_data=last_24h_df)

    @staticmethod
    def _plot_distinct(selector: PlotDataSelector, plot_data: List[PlotData], ax_in_subplot: plt.Axes, main_cfg: dict,
                       transform_main_data: Callable[[pd.DataFrame], pd.DataFrame] = lambda data: data) -> plt.Axes:
        main: PlotData = DefaultPlotCategory._get_main(plot_data)
        main_data = transform_main_data(main.data)

        ax = sns.lineplot(data=main_data, ax=ax_in_subplot, **_direct_seaborn_only(main_cfg))

        inner_plots = [d for d in plot_data if not d.main]
        for inner_plot in inner_plots:
            selected_params = selector.select_params(inner_plot)()
            if selected_params is None:
                log.debug(f"Skipping, could not select parameters for {inner_plot}")
            else:
                for ipd in selected_params:
                    if len(inner_plot.data) > 0:
                        sns.lineplot(ax=ax, **_direct_seaborn_only(ipd))
                    else:
                        log.info(f"Skipping empty INNER dataframe with config {ipd}")

        return ax


class PlotsConfiguration:
    def __init__(self, category: Callable, main_plot: dict):
        self.category = category
        self.main_plot = main_plot

    def __repr__(self):
        return f"PlotsConfiguration(category={self.category}, main_plot={self.main_plot})"

    def draw_main_plot(self, ax_in_subplot: plt.Axes):
        plot_dict: dict = self.main_plot
        title = plot_dict['title']
        xlabel = plot_dict.get('xlabel', plot_dict.get('x'))
        ylabel = plot_dict.get('ylabel', plot_dict.get('y'))

        self.category(ax_in_subplot, self.main_plot)

        ax_in_subplot.set_xlabel(xlabel)
        ax_in_subplot.tick_params(axis="x", rotation=45)
        ax_in_subplot.set_ylabel(ylabel)

        ax_in_subplot.set_title(title)
        ax_in_subplot.legend()


# -
# -------------------------------------------------- Util Methods --------------------------------------------------
# -
def last_24h_df(_df: pd.DataFrame, start_time=None) -> pd.DataFrame:
    start = datetime.now()
    last_24h = (start if start_time is None else start_time) - timedelta(hours=24)
    return _df[_df['timestamp'] >= last_24h]


def _direct_seaborn_only(main_plot: dict) -> dict:
    keys_to_remove = NOT_DIRECT_PARAMS
    return {key: main_plot[key] for key in {*main_plot} - set(keys_to_remove)}


def _save_to_pdf(fig: plt.Figure, save_path: str):
    if fig is None or save_path is None:
        return
    expected_file_type = ".pdf"
    if not save_path.lower().endswith(expected_file_type):
        log.info(f"Cannot save plot because file does not end with {expected_file_type}")
        return
    fig.savefig(save_path)
    log.info(f"Saved plots to {save_path}")


def _create_lineplots(plot_configs: List[PlotsConfiguration],
                      fig_size: Tuple[int, int] = (25, 12),
                      rows: int = 1,
                      cols: int = 1,
                      theme: Optional[dict] = None) -> Tuple[plt.Figure, List[plt.Axes]]:
    num_plots = len(plot_configs)
    if num_plots == 0:
        log.info("Noting to draw, nothing to return")
        return None, None
    if rows <= 0 or cols <= 0:
        log.info(f"Rows and columns must be greater than zero but are {rows}, {cols}")
        return None, None

    if theme:
        sns.set_theme(**theme)

    is_one_dimensional = (rows == 1 and cols >= 1) or (rows >= 1 and cols == 1)
    log.info(f"Creating {'1-dim' if is_one_dimensional else 'mult-dim'} {rows}x{cols} lineplots")
    fig, axes = plt.subplots(rows, cols, figsize=fig_size)

    if num_plots == 1:
        # Ensure axes is a list even if there's only one plot
        axes = [axes]
    if not is_one_dimensional:
        # 1-dim case axes is List[Axes]
        # in multi dim its a List[...List[Axes]]
        axes = axes.T.flatten()

    for idx, plot_config in enumerate(plot_configs):
        log.debug(f"Plot {idx} with {plot_config}")
        plot_config.draw_main_plot(axes[idx])

    plt.tight_layout()
    plt.close(fig)
    return fig, axes


# -
# -------------------------------------------------- Main Methods --------------------------------------------------
# -

def draw_complete_summary(plot_data: List[PlotData], merge_subplots_for: List[PlotData] = None, save_path: str = None):
    nothing_to_merge = merge_subplots_for is None or len(merge_subplots_for) == 0
    #@formatter:off
    complete_summary = [
        PlotsConfiguration(
            lambda ax, main_plot_cfg: DefaultPlotCategory.DISTINCT(PlotDataSelector.TEMPALL, plot_data, ax, main_plot_cfg) if nothing_to_merge else DefaultPlotCategory.MERGED(plot_data, merge_subplots_for, ax),
            MINIMAL_MAIN("Temperature Over Time", "Temp (°C)", "room_temp"),
        ),
        PlotsConfiguration(
            lambda ax, main_plot_cfg: DefaultPlotCategory.DISTINCT24(PlotDataSelector.TEMP24, plot_data, ax, main_plot_cfg) if nothing_to_merge else DefaultPlotCategory.MERGED24(plot_data, merge_subplots_for, ax),
            MINIMAL_MAIN_24("Temperature Last 24 Hours", "Temp (°C)", "room_temp")
        ),
        PlotsConfiguration(
            lambda ax, main_plot_cfg: DefaultPlotCategory.DISTINCT(PlotDataSelector.HUMIDITYALL, plot_data, ax, main_plot_cfg),
            MINIMAL_MAIN("Humidity Over Time", "Humidity (%)", "humidity") | {"color": "purple"}
        ),
        PlotsConfiguration(
            lambda ax, main_plot_cfg: DefaultPlotCategory.DISTINCT24(PlotDataSelector.HUMIDITY24, plot_data, ax, main_plot_cfg),
            MINIMAL_MAIN_24("Humidity Last 24 Hours", "Humidity (%)", "humidity") | {"color": "purple"}
        )
    ]
    # @formatter:on
    fig, _ = _create_lineplots(complete_summary, rows=2, cols=2, theme=custom_theme)
    _save_to_pdf(fig, save_path)
    return fig
