import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from typing import Tuple, List, Optional,  Dict, Any
from datetime import datetime, timedelta
import logging

log = logging.getLogger(__name__)

custom_theme = {
    'context': 'paper',   # Can be 'paper', 'notebook', 'talk', 'poster'
    'style': 'darkgrid',  # Can be 'darkgrid', 'whitegrid', 'dark', 'white', 'ticks'
    'palette': 'deep'     # Can be 'deep', 'muted', 'bright', 'pastel', etc.
}


# -
# -------------------------------------------------- Main Methods --------------------------------------------------
# -
def draw_plots(df, dwd_df=None, google_df=None, wettercom_df=None, ulmde_df=None, with_save=True, save_path=None):
    df_temp_inner_plt_params = []
    df_temp_24_inner_plt_params = []
    if dwd_df is not None:
        df_temp_inner_plt_params.append(inner_plots_params(dwd_df, "DWD Forecast", "timestamp", "temp"))
        df_temp_24_inner_plt_params.append(inner_24_plots_params(dwd_df, "DWD Forecast", "timestamp", "temp"))
    if google_df is not None:
        df_temp_inner_plt_params.append(inner_plots_params(google_df, "Google Forecast", "timestamp", "temp"),)
        df_temp_24_inner_plt_params.append( inner_24_plots_params(google_df, "Google Forecast", "timestamp", "temp"))
    if wettercom_df is not None:
        df_temp_inner_plt_params.append(inner_plots_params(wettercom_df, "Wetter.com Forecast", "timestamp", "temp_stat"))
        df_temp_inner_plt_params.append(inner_plots_params(wettercom_df, "Wetter.com Live", "timestamp", "temp_dyn"))
        df_temp_24_inner_plt_params.append(inner_24_plots_params(wettercom_df, "Wetter.com Forecast", "timestamp", "temp_stat"))
        df_temp_24_inner_plt_params.append(inner_24_plots_params(wettercom_df, "Wetter.com Live", "timestamp", "temp_dyn", marker="s"))
    if ulmde_df is not None:
        df_temp_inner_plt_params.append(inner_plots_params(ulmde_df, "Ulm Forecast", "timestamp", "temp"))
        df_temp_24_inner_plt_params.append(inner_24_plots_params(ulmde_df, "Ulm Forecast", "timestamp", "temp"))

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
        df_hum_24_plt_params["inner"] = [inner_24_plots_params(google_df, "Google Forecast", "timestamp", "humidity", alpha=None)]

    plots_w_params = [df_temp_plt_params, df_temp_24_plt_params, df_hum_plt_params, df_hum_24_plt_params]
    combined_fig, _ = create_lineplots(plots_w_params, theme=custom_theme, rows=2, cols=2)

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


def _validate_and_sort_timestamp(data: pd.DataFrame) -> pd.DataFrame:
    """
    Private method to validate that the DataFrame contains a 'timestamp' column.
    Parses the 'timestamp' column and sorts the DataFrame by 'timestamp'.

    :param data: The Pandas DataFrame containing the data.
    :return: The validated and sorted DataFrame.
    :raises ValueError: If 'timestamp' column is missing.
    """
    if 'timestamp' not in data.columns:
        raise ValueError("DataFrame must contain a 'timestamp' column.")

    # Parse the 'timestamp' column and sort by it
    data['timestamp'] = data['timestamp'].map(
        lambda x: datetime.strptime(str(x).replace("+00:00", "").strip(), '%Y-%m-%d %H:%M:%S'))
    data = data.sort_values(by="timestamp")

    return data


def merge_temperature_by_timestamp(dataframes_info: List[Dict[str, Any]], timestamp_col: str = 'timestamp', tolerance: int = 5.5) -> pd.DataFrame:
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

    Example
    -------
    >>> main_df = pd.DataFrame({
    ...     'timestamp': [pd.Timestamp('2024-10-05 12:00:00'), pd.Timestamp('2024-10-05 12:10:00')],
    ...     'room_temp': [22.0, 21.8]
    ... })
    >>> df1 = pd.DataFrame({
    ...     'timestamp': [pd.Timestamp('2024-10-05 12:00:00'), pd.Timestamp('2024-10-05 12:10:00')],
    ...     'temp': [15.2, 16.1]
    ... })
    >>> df2 = pd.DataFrame({
    ...     'timestamp': [pd.Timestamp('2024-10-05 12:00:00'), pd.Timestamp('2024-10-05 12:07:00')],
    ...     'temp': [14.9, 15.5]
    ... })
    >>> dataframes_info = [
    ...     {'df': df1, 'keys': ['temp']},
    ...     {'df': df2, 'keys': ['temp']},
    ...     {'df': main_df, 'keys': ['room_temp'], 'main': True}
    ... ]
    >>> result_df = merge_and_calculate_temperature_stats(dataframes_info, tolerance=5)
    >>> log.info(result_df)
              timestamp  inside_temp  outside_min  outside_max  outside_mean
    0 2024-10-05 12:00:00         22.0         14.9         15.2         15.05
    1 2024-10-05 12:10:00         21.8         15.5         16.1         15.80
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
        title = plot_dict.pop('title')
        xlabel = plot_dict.pop('xlabel', plot_dict.get('x'))
        ylabel = plot_dict.pop('ylabel', plot_dict.get('y'))

        log.info(f"plot {idx}: {plot_dict}")
        ax_in_subplot = axes[idx]
        if idx != 0:
            ax = sns.lineplot(data=data, ax=ax_in_subplot, **plot_dict)
            #TODO: use [] instead of None
            inner_plots = wrapper_dict.get('inner', None)
            if inner_plots:
                for inner_plot_dicts in inner_plots:
                    inner_data = inner_plot_dicts.pop("data")
                    #log.info(f"inner plot {idx}: {inner_plot_dicts}")
                    sns.lineplot(data=inner_data, ax=ax, **inner_plot_dicts)
        else:
            inner_plots = wrapper_dict.get('inner', [])
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
                                   x_col: str, 
                                   min_temp_col: str, 
                                   max_temp_col: str, 
                                   room_temp_col: str,
                                   theme: Optional[dict] = None,
                                   ax_in_subplot: Axes = None) -> tuple[plt.Figure, plt.Axes]:
    """
    Creates a Seaborn line plot showing min/max outside temperatures, mean outside temperature,
    and room temperature inside, with a filled area between min and max outside temperatures.

    Parameters:
        df (pd.DataFrame): The input DataFrame containing the temperature data.
        x_col (str): The column name for the x-axis values (time or date).
        min_temp_col (str): The column name for the minimum outside temperature values.
        max_temp_col (str): The column name for the maximum outside temperature values.
        room_temp_col (str): The column name for the room temperature (inside).
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

    #ax.set_title("Outside Min/Max and Mean Temperatures, and Room Temperature Inside", fontsize=18, pad=20)
    #ax.set_xlabel(x_col, fontsize=14)
    #ax.set_ylabel("Temperature (°C)", fontsize=14)
    #ax.legend(loc='upper left', fontsize='large')
    plt.xticks(rotation=45)
    plt.tight_layout()

    return fig, ax
