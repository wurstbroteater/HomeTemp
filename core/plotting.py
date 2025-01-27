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
# The NEW visualization module. Provides means to create a plot for sensor data and is able to save them to pdf.
# ----------------------------------------------------------------------------------------------------------------


custom_theme = {
    'context': 'paper',  # Can be 'paper', 'notebook', 'talk', 'poster'
    'style': 'darkgrid',  # Can be 'darkgrid', 'whitegrid', 'dark', 'white', 'ticks'
    'palette': 'deep'  # Can be 'deep', 'muted', 'bright', 'pastel', etc.
}

TEMP_TUPLE_DEFAULT = ("temp", None)

# These functions represent direct seaborn plot parameters
MINIMAL_INNER = lambda df, label, y: {"data": df, "label": label, "x": "timestamp", "y": y, "alpha": 0.6}
MINIMAL_INNER_24 = lambda df, label, y: {"data": df, "label": label, "x": "timestamp", "y": y, "alpha": 0.6, "marker": "o", "markersize": 6}

NOT_DIRECT_PARAMS = ["title", "xlabel", "ylabel"]
# These functions represent seaborn plot configurations, i.e., direct seaborn plot parameters and some for configurinig main plot, see NOT_DIRECT_PARAMS
MINIMAL_MAIN = lambda title, ylabel, y : {"title": title,"xlabel":"Time", "ylabel":ylabel, "label":"Home", "x":"timestamp", "y":y}
MINIMAL_MAIN_24 = lambda title, ylabel, y : {"title": title,"xlabel":"Time", "ylabel":ylabel, "label":"Home", "x":"timestamp", "y":y,  "marker":"o", "markersize":6} 


class SupportedDataFrames(Enum):
    """
        Supported data frames to plot parameters
    
    """
    # enumIdx, name, temperature keys list of tuple (df key, plot label with None for default see _label) , humidity key
    Main = 1, "Room", [("room_temp", None)], "humidity"
    DWD_DE = 2, "DWD", [TEMP_TUPLE_DEFAULT], None
    GOOGLE_COM = 3, "Google.de", [TEMP_TUPLE_DEFAULT], "humidity"
    WETTER_COM = 4, "Wetter.com", [("temp_stat", "Forecast"), ("temp_dyn", "Live")], None
    ULM_DE = 5, "Ulm.de", [TEMP_TUPLE_DEFAULT], None

    def __init__(self, enum_idx: int, display_name: str, temperature_keys: list, humidiy_key: str):
        self.enum_idx = enum_idx
        self.display_name = display_name
        self.temperature_keys = temperature_keys
        self.humidiy_key = humidiy_key

    def _label(self, label_overwrite: str | None = None) -> str:
        if label_overwrite is None:
            return f"{self.display_name} Forecast"
        else:
            return f"{self.display_name} {label_overwrite}"

    def get_temperature_keys(self) -> list[str]:
        return list(map(lambda x: x[0], [] if self.temperature_keys is None else self.temperature_keys))

    def get_temperatures(self, data: pd.DataFrame, optional_keys:list=None) -> pd.DataFrame:
        if optional_keys is None:
            optional_keys = []
        return data[self.get_temperature_keys() + optional_keys]

    def get_humidity(self, data: pd.DataFrame, optional_keys:list=[]) -> pd.DataFrame:
        keys = [] if self.humidiy_key is None else [self.humidiy_key]
        return data[keys + optional_keys]


    # --- parameters for configuring seaborn. ---
    def get_temp_inner_plots_params(self, data: pd.DataFrame) -> list | None:

        if self is SupportedDataFrames.Main:
            return None
        return list(map(lambda temp_keys: MINIMAL_INNER(data, self._label(temp_keys[1]), temp_keys[0]), self.temperature_keys))


    def get_hum_inner_plots_params(self, data: pd.DataFrame) -> list | None:
        if self.humidiy_key is not None:
            return [MINIMAL_INNER(data, self._label(), self.humidiy_key)]
        return None

    def get_temp_24h_inner_plots_params(self, data: pd.DataFrame) -> list | None:
        # TODO: ASSURE 24 h ?
        if self is SupportedDataFrames.Main:
            return None
        elif self is SupportedDataFrames.WETTER_COM:
            return [MINIMAL_INNER_24(data, self._label(self.temperature_keys[0][1]), self.temperature_keys[0][0]),
                    MINIMAL_INNER_24(data, self._label(self.temperature_keys[1][1]), self.temperature_keys[1][0]) | {
                        "marker": "s"}]

        return list(map(lambda temp_keys: MINIMAL_INNER_24(data, self._label(temp_keys[1]), temp_keys[0]),
                        self.temperature_keys))

    def get_hum_24h_inner_plots_params(self, data: pd.DataFrame) -> list | None:
        if self.humidiy_key is not None:
            return [MINIMAL_INNER_24(data, self._label(), self.humidiy_key) | {"alpha": 1}]
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
    
    def select_params(self, plot_data:PlotData) -> Callable:
        param_method_map = {
            PlotDataSelector.HUMIDITY24: plot_data.inner_24_params_hum,
            PlotDataSelector.HUMIDITYALL: plot_data.inner_params_hum,
            PlotDataSelector.TEMP24: plot_data.inner_24_params,
            PlotDataSelector.TEMPALL: plot_data.inner_params,
        }
        return param_method_map[self]


class DefaultPlotCategory:
    @staticmethod
    def MERGED(plot_data: List[PlotData], merge_subplots_for: List[PlotData], ax_in_subplot:plt.Axes) ->  plt.Axes:
        main_plot =DefaultPlotCategory._get_main(plot_data)
        merged = DefaultPlotCategory._merge_temperature_by_timestamp(main_plot, merge_subplots_for)
        return DefaultPlotCategory._create_merged_temperature_plot(merged, ax_in_subplot=ax_in_subplot)[1]
    
    @staticmethod
    def MERGED24(plot_data: List[PlotData], merge_subplots_for: List[PlotData], ax_in_subplot:plt.Axes) ->  plt.Axes:
        main_plot =DefaultPlotCategory._get_main(plot_data)
        merged = DefaultPlotCategory._merge_temperature_by_timestamp(main_plot, merge_subplots_for, df_filter_fun=last_24h_df)
        return DefaultPlotCategory._create_merged_temperature_plot(merged, ax_in_subplot=ax_in_subplot)[1]

    @staticmethod
    def _get_main(plot_data: List[PlotData]) -> PlotData:
        main_plot = [p for p in plot_data if p.main]
        l =  len(main_plot)
        if l == 0:
            msg = "Unable to draw plots without main PlotData!"
            log.error(msg)
            raise AssertionError(msg)
        elif l > 1:
            log.info("Found more than 1 main plot. Using first one for plotting")
        return main_plot[0]
    @staticmethod
    def _merge_temperature_by_timestamp(main_data: PlotData, dataframes_info: List[PlotData], timestamp_col: str = 'timestamp', tolerance: int = 5.5, df_filter_fun=None) -> pd.DataFrame:

   
        main_df =  main_data.get_temperatures([timestamp_col]) if df_filter_fun is None else df_filter_fun(main_data.get_temperatures([timestamp_col]))
        main_df_len = len(main_df)
        time_delta = timedelta(minutes=tolerance)
        inside_temp_base = main_data.get_temperatures().values if df_filter_fun is None else df_filter_fun(main_data.get_temperatures([timestamp_col]))[main_data.support.get_temperature_keys()].values
        inside_temps = list(map(lambda packed_value: packed_value[0], inside_temp_base))

        outside_min = np.full(main_df_len, np.nan)
        outside_max = np.full(main_df_len, np.nan)
        outside_mean = np.full(main_df_len, np.nan)

        for p_data in dataframes_info:
            if main_df_len == 0:
                break
            df = p_data.get_temperatures([timestamp_col]) if df_filter_fun is None else df_filter_fun(p_data.get_temperatures([timestamp_col]))
            if len(df) == 0:
                log.info("skipping empty dataframe")
                continue
            if p_data.main :
                log.info("MERGED main df should not be contained in this list. skipping it.")
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

        #log.info(f"{out}")
        #log.info(f"Lengths: timestamp_col={len(main_df[timestamp_col])}, "
        # f"inside_temp={len(inside_temps)}, "
        # f"outside_min={len(outside_min)}, "
        # f"outside_max={len(outside_max)}, "
        # f"outside_mean={len(outside_mean)}")        
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

        # ax.set_title("Outside Min/Max and Mean Temperatures, and Room Temperature Inside", fontsize=18, pad=20)
        # ax.set_xlabel(x_col, fontsize=14)
        # ax.set_ylabel("Temperature (°C)", fontsize=14)
        # ax.legend(loc='upper left', fontsize='large')
        plt.xticks(rotation=45)
        plt.tight_layout()

        return fig, ax
    
    @staticmethod
    def DISTINCT(selector: PlotDataSelector, plot_data: List[PlotData], ax_in_subplot: plt.Axes, main_cfg: dict) -> plt.Axes:
        return DefaultPlotCategory._plot_distinct(selector=selector,plot_data=plot_data,ax_in_subplot=ax_in_subplot,main_cfg=main_cfg)


    @staticmethod
    def DISTINCT24(selector: PlotDataSelector, plot_data: List[PlotData], ax_in_subplot: plt.Axes, main_cfg: dict) -> plt.Axes:
        return DefaultPlotCategory._plot_distinct(selector=selector,plot_data=plot_data,ax_in_subplot=ax_in_subplot,main_cfg=main_cfg,transform_main_data=last_24h_df)
    
    @staticmethod
    def _plot_distinct(selector: PlotDataSelector,plot_data: List[PlotData],ax_in_subplot: plt.Axes,main_cfg: dict,transform_main_data: Callable[[pd.DataFrame], pd.DataFrame] = lambda data: data) -> plt.Axes:
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
    def __init__(self,category: DefaultPlotCategory, main_plot: dict):
        self.category = category
        self.main_plot = main_plot

    def __repr__(self):
        return f"PlotsConfiguration(category={self.category}, main_plot={self.main_plot})"
    
    def draw_main_plot(self, ax_in_subplot:plt.Axes):
        plot_dict:dict = self.main_plot
        title = plot_dict['title']
        xlabel = plot_dict.get('xlabel', plot_dict.get('x'))
        ylabel = plot_dict.get('ylabel', plot_dict.get('y'))

        self.category(ax_in_subplot, self.main_plot)

        ax_in_subplot.set_xlabel(xlabel)
        ax_in_subplot.tick_params(axis="x", rotation=45)
        ax_in_subplot.set_ylabel(ylabel)

        ax_in_subplot.set_title(title)
        ax_in_subplot.legend()


def _direct_seaborn_only(main_plot:dict) -> dict:
    keys_to_remove = NOT_DIRECT_PARAMS
    return {key: main_plot[key] for key in set([*main_plot]) - set(keys_to_remove)}

def _save_to_pdf(fig:plt.Figure, save_path:str):
    if fig is None or save_path is None:
        return
    expected_file_type = ".pdf"
    if not save_path.lower().endswith(expected_file_type):
        log.info(f"Cannot save plot because file does not end with {expected_file_type}")
        return
    fig.savefig(save_path)
    log.info(f"Saved plots to {save_path}")



# -
# -------------------------------------------------- Main Methods --------------------------------------------------
# -

def draw_complete_summary(plot_data: List[PlotData], merge_subplots_for: List[PlotData]=None, save_path:str=None):
    nothing_to_merge = merge_subplots_for is None or len(merge_subplots_for) == 0
    COMPLETE_SUMMARY = [
        PlotsConfiguration(
            lambda ax, main_plot_cfg: DefaultPlotCategory.DISTINCT(PlotDataSelector.TEMPALL, plot_data, ax, main_plot_cfg) if nothing_to_merge else DefaultPlotCategory.MERGED(plot_data,merge_subplots_for, ax),
            MINIMAL_MAIN("Temperature Over Time", "Temp (°C)", "room_temp"),
        ),
       PlotsConfiguration(
           lambda ax, main_plot_cfg:  DefaultPlotCategory.DISTINCT24(PlotDataSelector.TEMP24, plot_data, ax, main_plot_cfg) if nothing_to_merge else DefaultPlotCategory.MERGED24(plot_data, merge_subplots_for, ax),
            MINIMAL_MAIN_24("Temperature Last 24 Hours", "Temp (°C)", "room_temp")
        ),
        PlotsConfiguration(
            lambda ax, main_plot_cfg: DefaultPlotCategory.DISTINCT(PlotDataSelector.HUMIDITYALL, plot_data, ax, main_plot_cfg),
            MINIMAL_MAIN("Humidity Over Time", "Humidity (%)", "humidity") | {"color": "purple"}
        ),
        PlotsConfiguration(
            lambda ax, main_plot_cfg: DefaultPlotCategory.DISTINCT24(PlotDataSelector.HUMIDITY24,plot_data, ax, main_plot_cfg),
            MINIMAL_MAIN_24("Humidity Last 24 Hours", "Humidity (%)", "humidity") | {"color": "purple"}
        )
        ]
    fig, _ = n_create_lineplots(COMPLETE_SUMMARY, rows=2, cols=2, theme=custom_theme)
    _save_to_pdf(fig, save_path)
    return fig



def n_create_lineplots(plot_configs: List[PlotsConfiguration],
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
        log.info(f"Plot {idx} with {plot_config}")
        plot_config.draw_main_plot(axes[idx])

   
    plt.tight_layout()
    plt.close(fig)
    return fig, axes


def draw_plots(df, dwd_df=None, google_df=None, wettercom_df=None, ulmde_df=None, with_save=True, save_path=None):
    df_temp_inner_plt_params = []
    df_temp_24_inner_plt_params = []
    dataframes_info = [{'df': df, 'name': 'main', 'keys': ['room_temp'], 'main': True}]
    if dwd_df is not None:
        df_temp_inner_plt_params.append(inner_plots_params(dwd_df, "DWD Forecast", "timestamp", "temp"))
        df_temp_24_inner_plt_params.append(inner_24_plots_params(dwd_df, "DWD Forecast", "timestamp", "temp"))
        dataframes_info.append({'df': dwd_df, 'name': 'dwd', 'keys': ['temp']})
    if google_df is not None:
        df_temp_inner_plt_params.append(inner_plots_params(google_df, "Google Forecast", "timestamp", "temp"), )
        df_temp_24_inner_plt_params.append(inner_24_plots_params(google_df, "Google Forecast", "timestamp", "temp"))
        dataframes_info.append({'df': google_df, 'name': 'google', 'keys': ['temp']})
    if wettercom_df is not None:
        df_temp_inner_plt_params.append(
            inner_plots_params(wettercom_df, "Wetter.com Forecast", "timestamp", "temp_stat"))
        df_temp_inner_plt_params.append(inner_plots_params(wettercom_df, "Wetter.com Live", "timestamp", "temp_dyn"))
        df_temp_24_inner_plt_params.append(
            inner_24_plots_params(wettercom_df, "Wetter.com Forecast", "timestamp", "temp_stat"))
        df_temp_24_inner_plt_params.append(
            inner_24_plots_params(wettercom_df, "Wetter.com Live", "timestamp", "temp_dyn", marker="s"))
        dataframes_info.append({'df': wettercom_df, 'name': 'wettercom', 'keys': ['temp_stat', 'temp_dyn']})
    if ulmde_df is not None:
        df_temp_inner_plt_params.append(inner_plots_params(ulmde_df, "Ulm Forecast", "timestamp", "temp"))
        df_temp_24_inner_plt_params.append(inner_24_plots_params(ulmde_df, "Ulm Forecast", "timestamp", "temp"))
        dataframes_info.append({'df': ulmde_df, 'name': 'ulm', 'keys': ['temp']})

    df_temp_plt_params = {"main": main_plot_params(df, "Temperature Over Time"), "inner": df_temp_inner_plt_params}
    df_temp_24_plt_params = {
        'main': main_plot_params(last_24h_df(df), "Temperature Last 24 Hours", marker='o', markersize=6),
        "inner": df_temp_24_inner_plt_params}

    df_hum_plt_params = {"main": main_plot_params(df, "Humidity Over Time", y="humidity", color="purple")}
    if google_df is not None:
        df_hum_plt_params["inner"] = [inner_plots_params(google_df, "Google Forecast", "timestamp", "humidity")]
    df_hum_24_plt_params = {
        'main': main_plot_params(last_24h_df(df), "Humidity Last 24 Hours", marker='o', markersize=6, color="purple",
                                 ylabel="Humidity (%)", y="humidity")}
    if google_df is not None:
        df_hum_24_plt_params["inner"] = [
            inner_24_plots_params(google_df, "Google Forecast", "timestamp", "humidity", alpha=None)]

    plots_w_params = [df_temp_plt_params, df_temp_24_plt_params, df_hum_plt_params, df_hum_24_plt_params]
    combined_fig, _ = create_lineplots(plots_w_params, dataframes_info=dataframes_info, theme=custom_theme, rows=2,
                                       cols=2)

    if with_save:
        name = datetime.now().strftime("%d-%m-%Y")
        if save_path is None:
            loc = f"plots/{name}.pdf"
        else:
            loc = save_path
        combined_fig.savefig(loc)
        log.info(f"Saved plots to {loc}")

    return combined_fig


# -
# -------------------------------------------------- Util Methods --------------------------------------------------
# -
def last_24h_df(_df: pd.DataFrame, start_time=None) -> pd.DataFrame:
    start = datetime.now()
    last_24h = (start if start_time is None else start_time) - timedelta(hours=24)
    return _df[_df['timestamp'] >= last_24h]


def main_plot_params(fr, title,
                     label="Home", xlabel="Time", x="timestamp", ylabel="Temp (°C)", y="room_temp",
                     marker=None, color=None, alpha=None, markersize=None) -> dict:
    out = {
        "title": title,
        # if set overwrite x/y label with this
        "xlabel": xlabel,
        "ylabel": ylabel,
    }
    return {**out,
            **seaborn_lineplot_params(fr, label, x, y, marker=marker, color=color, alpha=alpha, markersize=markersize)}


def inner_24_plots_params(fr, label, x, y, marker="o", markersize=6, alpha=0.6, color=None) -> dict:
    return seaborn_lineplot_params(last_24h_df(fr), label, x, y, marker=marker, color=color, alpha=alpha,
                                   markersize=markersize)


def inner_plots_params(fr, label, x, y, marker=None, color=None, markersize=None) -> dict:
    return seaborn_lineplot_params(fr, label, x, y, marker=marker, color=color, alpha=0.6, markersize=markersize)


# supported seaborn
def seaborn_lineplot_params(fr, label, x, y, marker=None, color=None, alpha=None, markersize=None) -> dict:
    out = {
        "data": fr,
        "label": label,
        "x": x,
        "y": y,
    }

    # optional seaborn parameters
    if color:
        out["color"] = color
    if marker:
        out["marker"] = marker
    if alpha:
        out["alpha"] = alpha
    if markersize:
        out["markersize"] = markersize
    return out


def merge_temperature_by_timestamp(dataframes_info: List[Dict[str, Any]], timestamp_col: str = 'timestamp',
                                   tolerance: int = 5.5) -> pd.DataFrame:
    """
    Merges multiple DataFrames based on aligned timestamps (within a tolerance window) and calculates the 
    minimum, maximum, and mean temperatures for each timestamp interval. 

    The method works with a list of dictionaries where each dictionary contains:
    - A DataFrame with a 'timestamp' column and one or more temperature columns.
    - A 'keys' list specifying the temperature column names in that DataFrame.
    - An optional 'main' flag indicating which DataFrame is the primary one. The primary DataFrame's timestamps 
      are used as the reference to align the others.

    The function aligns timestamps between the main DataFrame and the others using a time tolerance and computes
    the minimum, maximum, and mean temperatures for each timestamp interval from the secondary DataFrames. The 
    results are returned in a new DataFrame.

    Parameters
    ----------
    dataframes_info : List[Dict[str, Any]]
        A list of dictionaries, where each dictionary represents a DataFrame with the following keys:
        - 'df': The pandas DataFrame containing a 'timestamp' column and temperature columns.
        - 'keys': A list of strings indicating the temperature columns in the DataFrame.
        - 'main' (optional): A boolean flag indicating whether this is the primary DataFrame. Only one DataFrame 
          should be marked as the main DataFrame.
    
    timestamp_col : str, optional (default is 'timestamp')

    tolerance : int, optional (default is 5)
        The maximum allowable time difference, in minutes, to align timestamps from the secondary DataFrames to the 
        main DataFrame. Only timestamps within this tolerance will be considered a match.

    Returns
    -------
    pd.DataFrame
        A new DataFrame with the following columns:
        - 'timestamp': The aligned timestamps from the main DataFrame.
        - 'inside_temp': The inside temperature from the main DataFrame.
        - 'outside_min': The minimum temperature from the aligned secondary DataFrames.
        - 'outside_max': The maximum temperature from the aligned secondary DataFrames.
        - 'outside_mean': The mean temperature from the aligned secondary DataFrames, ignoring NaN values.

    Raises
    ------
    ValueError
        If no DataFrame is marked as 'main', or if more than one DataFrame is marked as 'main'.

    Notes
    -----
    - The function uses pandas' `merge_asof` to align timestamps between DataFrames. This function assumes that 
      all DataFrames are sorted by the timestamp column.
    - NaN values in temperature columns are handled gracefully, and will not affect the calculation of min, max, 
      or mean values for each row.
    - If a DataFrame is empty or has no valid data within the tolerance, its contribution to the result will be ignored.
    """

    main_df_info = next((df_info for df_info in dataframes_info if df_info.get('main', False)), None)
    if not main_df_info:
        raise ValueError("There must be exactly one DataFrame marked as 'main'")

    main_df = main_df_info['df'][[timestamp_col] + main_df_info['keys']]
    main_df_len = len(main_df)
    time_delta = timedelta(minutes=tolerance)
    inside_temps = main_df[main_df_info['keys'][0]].values

    outside_min = np.full(main_df_len, np.nan)
    outside_max = np.full(main_df_len, np.nan)
    outside_mean = np.full(main_df_len, np.nan)

    for df_info in dataframes_info:
        df = df_info['df'][[timestamp_col] + df_info['keys']]
        skip_dataframe = df_info is main_df_info or len(df) == 0
        if skip_dataframe:
            continue

        aligned_df = pd.merge_asof(
            left=main_df[[timestamp_col]],
            right=df,
            on=timestamp_col,
            tolerance=time_delta,
            direction='nearest'
        )

        temps_in_interval = aligned_df[df_info['keys']].values

        # ignoring NaN values
        row_min = np.nanmin(temps_in_interval, axis=1)
        row_max = np.nanmax(temps_in_interval, axis=1)
        row_mean = np.nanmean(temps_in_interval, axis=1)

        # Update outside min, max, mean using np.nanmin/max/mean to handle overlapping DataFrames
        outside_min = np.nanmin([outside_min, row_min], axis=0)
        outside_max = np.nanmax([outside_max, row_max], axis=0)
        outside_mean = np.nanmean([outside_mean, row_mean], axis=0)

    return pd.DataFrame({
        timestamp_col: main_df[timestamp_col],
        'inside_temp': inside_temps,
        'outside_min': outside_min,
        'outside_max': outside_max,
        'outside_mean': outside_mean
    })


# -
# -------------------------------------------------- Draw Methods --------------------------------------------------
# -
def create_lineplots(plot_params: List[dict],
                     dataframes_info: List[dict] = None,
                     fig_size: Tuple[int, int] = (25, 12),
                     rows: int = 1,
                     cols: int = 1,
                     theme: Optional[dict] = None,
                     despine=False) -> Tuple[plt.Figure, List[plt.Axes]]:
    """
    Create multiple or one dimensional subplots of line plots using a list of dictionaries for plot parameters.

    :param plot_params: A list of dictionaries, where each dictionary contains the key "main" which is a dict of
                        parameters for the main plot. It may contain the key "inner" which is a list of dict of
                        parameters for echo inner plot.
    :dataframes_info TODO .
    :param fig_size: The overall size of the figure (default is (15, 10)).
    :param rows: The number of rows in the figure (default is 1).
    :param cols: The number of columns in the figure (default is 1).
    :param theme: Optional dictionary to customize Seaborn theme (default is None).
    :param despine: Optional flag to despine the subplots (default is False).
    :return: A tuple containing the Figure and list of Axes objects.
    """
    num_plots = len(plot_params)
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

    for idx, wrapper_dict in enumerate(plot_params):
        plot_dict = wrapper_dict["main"]
        data = plot_dict.pop('data')
        if len(data) == 0:
            log.info(f"skipping empty MAIN dataframe")
            continue
        title = plot_dict.pop('title')
        xlabel = plot_dict.pop('xlabel', plot_dict.get('x'))
        ylabel = plot_dict.pop('ylabel', plot_dict.get('y'))

        # log.info(f"plot {idx}: {plot_dict}")
        ax_in_subplot = axes[idx]
        if dataframes_info is not None and idx == 0:
            merged = merge_temperature_by_timestamp(dataframes_info)
            ax = create_merged_temperature_plot(merged, 'timestamp', 'outside_min', 'outside_max', 'inside_temp',
                                                ax_in_subplot=ax_in_subplot)[1]
        else:
            ax = sns.lineplot(data=data, ax=ax_in_subplot, **plot_dict)
            inner_plots = wrapper_dict.get('inner', [])
            for inner_plot_dicts in inner_plots:
                # log.info(f"inner plot {idx}: {type(inner_plot_dicts)}{inner_plot_dicts}")
                # TODO: this should be a workaround until everyhing supports new?
                if type(inner_plot_dicts) is list:
                    # support new version rework
                    log.info("supporting new")
                    if len(inner_plot_dicts) == 0:
                        log.warning("inner plot with no content!")
                    for ipd in inner_plot_dicts:
                        inner_data = ipd.pop("data")
                        if len(inner_data) > 0:
                            sns.lineplot(data=inner_data, ax=ax, **ipd)
                        else:
                            log.info(f"skipping empty INNER dataframe with config {ipd}")
                elif type(inner_plot_dicts) is dict:
                    log.info("supporting old")
                    # support for old version untill draw_plots is gone
                    inner_data = inner_plot_dicts.pop("data")
                    sns.lineplot(data=inner_data, ax=ax, **inner_plot_dicts)
                else:
                    log.warning(f"Skipping unsupported type {type(inner_plot_dicts)} {str(inner_plot_dicts)}")

        # TODO: still neeeded ? What does it do?
        if despine:
            sns.despine(left=True, bottom=True)

        ax_in_subplot.set_xlabel(xlabel)
        ax_in_subplot.tick_params(axis="x", rotation=45)
        ax_in_subplot.set_ylabel(ylabel)

        ax_in_subplot.set_title(title)
        ax_in_subplot.legend()

    plt.tight_layout()
    plt.close(fig)
    return fig, axes


def create_merged_temperature_plot(df: pd.DataFrame,
                                   x_col: str = 'timestamp',
                                   min_temp_col: str = 'outside_min',
                                   max_temp_col: str = 'outside_max',
                                   room_temp_col: str = 'inside_temp',
                                   theme: Optional[dict] = None,
                                   ax_in_subplot: Axes = None) -> tuple[plt.Figure, plt.Axes]:
    """
    Creates a Seaborn line plot showing min/max outside temperatures, mean outside temperature,
    and room temperature inside, with a filled area between min and max outside temperatures.

    Parameters:
        df (pd.DataFrame): The input DataFrame containing the temperature data.
        x_col (str): The column name for the x-axis values (time or date).
        min_temp_col (str): Optional, the column name for the minimum outside temperature values.
        max_temp_col (str): Optional, the column name for the maximum outside temperature values.
        room_temp_col (str): Optional, the column name for the room temperature (inside).
        theme (dict): Optional dictionary to customize Seaborn theme (default is None).
        ax_in_subplot (Axes): Optional Axes to use for plotting.

    Returns:
        tuple[plt.Figure, plt.Axes]: A tuple containing the Matplotlib Figure and Axes objects.
    """
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

    # ax.set_title("Outside Min/Max and Mean Temperatures, and Room Temperature Inside", fontsize=18, pad=20)
    # ax.set_xlabel(x_col, fontsize=14)
    # ax.set_ylabel("Temperature (°C)", fontsize=14)
    # ax.legend(loc='upper left', fontsize='large')
    plt.xticks(rotation=45)
    plt.tight_layout()

    return fig, ax
