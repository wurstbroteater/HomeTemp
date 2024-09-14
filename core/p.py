import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import os
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from typing import Tuple, List, Optional
from datetime import datetime, timedelta
import matplotlib.gridspec as gridspec
import logging

log = logging.getLogger(__name__)

custom_theme = {
    #'context': 'notebook',   # Can be 'paper', 'notebook', 'talk', 'poster'
    'style': 'darkgrid',    # Can be 'darkgrid', 'whitegrid', 'dark', 'white', 'ticks'
    'palette': 'deep'        # Can be 'deep', 'muted', 'bright', 'pastel', etc.
}

def last_24h_df(_df:pd.DataFrame) -> pd.DataFrame:
    last_24h = datetime.now() - timedelta(hours=24)
    return _df[_df['timestamp'] >= last_24h]



def draw_plots(df, dwd_df=None, google_df=None, wettercom_df=None, ulmde_df=None, with_save=True, save_path=None):
    df_temp_inner_plt_params = [
                inner_plots_params(dwd_df, "DWD Forecast", "timestamp", "temp"),
                inner_plots_params(google_df, "Google Forecast", "timestamp", "temp"),
                inner_plots_params(wettercom_df, "Wetter.com Forecast", "timestamp", "temp_stat"),
                inner_plots_params(wettercom_df, "Wetter.com Live", "timestamp", "temp_dyn"),
                inner_plots_params(ulmde_df, "Ulm Forecast", "timestamp", "temp")
                ]
    df_temp_24_inner_plt_params = [
                inner_24_plots_params(dwd_df, "DWD Forecast", "timestamp", "temp"),
                inner_24_plots_params(google_df, "Google Forecast", "timestamp", "temp"),
                inner_24_plots_params(wettercom_df, "Wetter.com Forecast", "timestamp", "temp_stat"),
                inner_24_plots_params(wettercom_df, "Wetter.com Live", "timestamp", "temp_dyn", marker="s"),
                inner_24_plots_params(ulmde_df, "Ulm Forecast", "timestamp", "temp")
                ]
    df_temp_plt_params = {"main": main_plot_params(df, "Temperature Over Time"), "inner": df_temp_inner_plt_params}
    df_temp_24_plt_params = {'main': main_plot_params(last_24h_df(df),"Temperature Last 24 Hours", marker='o', markersize=6), "inner": df_temp_24_inner_plt_params}

    df_hum_plt_params = {"main": main_plot_params(df, "Humidity Over Time", y="humidity",  color="purple"), "inner": [inner_plots_params(google_df, "Google Forecast", "timestamp", "humidity")]}
    df_hum_24_plt_params = {'main': main_plot_params(last_24h_df(df),"Humidity Last 24 Hours", marker='o', markersize=6, color="purple",ylabel="Humidity (%)", y="humidity"), "inner": [inner_24_plots_params(google_df, "Google Forecast", "timestamp", "humidity", alpha=None)]}
    
    plots_w_params = [df_temp_plt_params, df_temp_24_plt_params,df_hum_plt_params, df_hum_24_plt_params]
    combined_fig, _ = create_multiple_lineplots(plots_w_params, theme=custom_theme, rows=2, cols=2)
    return combined_fig









def main_plot_params(fr,title, label= "Home",xlabel="Time", x= "timestamp", ylabel="Temp (°C)",y="room_temp", marker=None, color=None, alpha=None, markersize=None):
    out = {
        "title": title,
        # if set overwrite x/y label with this
        "xlabel": xlabel,
        "ylabel":ylabel,
    }
    return {**out, **seaborn_lineplot_params(fr, label, x, y, marker=marker, color=color,alpha=alpha,markersize=markersize)}



def inner_24_plots_params(fr, label, x, y, marker="o",markersize=6,alpha=0.6, color=None):
    return seaborn_lineplot_params(last_24h_df(fr), label, x, y, marker=marker, color=color,alpha=alpha,markersize=markersize)

def inner_plots_params(fr, label, x, y, marker=None, color=None, markersize=None):
    return seaborn_lineplot_params(fr, label, x, y, marker=marker, color=color,alpha=0.6,markersize=markersize)


def seaborn_lineplot_params(fr, label, x, y,marker=None, color=None, alpha=None, markersize=None) -> dict:
    out = {
        "data": fr,
        "label": label,
        "x": x,
        "y" : y,
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


# TODO: rename as it can create any combination of lineplots
def create_multiple_lineplots(plot_params: List[dict], 
                              fig_size: Tuple[int, int] = (25, 12), 
                              rows:int = 1,
                              cols:int = 1,
                              theme: Optional[dict] = None, 
                              save_path: str = None,
                              despine=False) -> Tuple[plt.Figure, List[plt.Axes]]:
    """
    Create multiple subplots of line plots using a list of dictionaries for plot parameters.

    :param plot_params: A list of dictionaries, where each dictionary contains:
                        {"data": pd.DataFrame, **sns.lineplot keyword arguments}
    :param fig_size: The overall size of the figure (default is (15, 10)).
    :param theme: Optional dictionary to customize Seaborn theme (default is None).
    :param save_path: Optional path to save the figure as a file (default is None).
    :return: A tuple containing the Figure and list of Axes objects.
    """
    num_plots = len(plot_params)
    if num_plots == 0:
        print("Noting to draw, nothing to return")
        return None, None
    if rows <= 0 or cols <=0:
        print(f"Rows and columns must be greater than zero but are {rows}, {cols}")
        return None, None

    if theme:
        sns.set_theme(**theme)

    is_one_dimensional = (rows == 1 and cols >= 1) or (rows >=1 and cols == 1)
    print(f"Creating {'1-dim' if is_one_dimensional else 'mult-dim'} {rows}x{cols} lineplots")
    fig, axes = plt.subplots(rows,cols, figsize=fig_size)
    
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

        print(f"plot {idx}: {plot_dict}")
        
        ax_in_subplot = axes[idx]
        ax = sns.lineplot(data=data, ax=ax_in_subplot, **plot_dict)
        inner_plots = wrapper_dict.get('inner', None)
        if inner_plots:
            for inner_plot_dicts in inner_plots:
                inner_data = inner_plot_dicts.pop("data")
                print(f"inner plot {idx}: {inner_plot_dicts}")
                sns.lineplot(data=inner_data, ax=ax,**inner_plot_dicts)
            
        if despine:
            sns.despine(left=True, bottom=True)

        ax_in_subplot.set_xlabel(xlabel)
        ax_in_subplot.tick_params(axis="x", rotation=45)
        ax_in_subplot.set_ylabel(ylabel)

        ax_in_subplot.set_title(title)
        ax_in_subplot.legend()
  

    plt.tight_layout()

    if save_path is not None:
        save_file = os.path.join(save_path, 'multiple_plots.pdf')
        fig.savefig(save_file)
        log.info(f'Plot saved to {save_file}')

    plt.close(fig)
    return fig, axes



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
    data['timestamp'] = data['timestamp'].map(lambda x: datetime.strptime(str(x).replace("+00:00", "").strip(), '%Y-%m-%d %H:%M:%S'))
    data = data.sort_values(by="timestamp")
    
    return data

##TODO: REMOVE
def create_single_lineplot(data: pd.DataFrame, label: str, x_id: str, y_id: str, marker: str = "o", color: str = "blue", 
                           fig_size: Tuple[int, int] = (10, 6), save_path: str = None, 
                           theme: Optional[dict] = None) -> Tuple[Figure, Axes]:
    """
    Creates a single line plot from the provided data using Seaborn and Matplotlib.

    :param data: The Pandas DataFrame containing the data. Must contain a 'timestamp' column.
    :param label: The label for the plot.
    :param x_id: The column name for the x-axis data.
    :param y_id: The column name for the y-axis data.
    :param marker: The marker style for the plot (default is 'o').
    :param color: The color of the line (default is 'blue').
    :param fig_size: The size of the figure (default is (10, 6)).
    :param save_path: Optional path to save the figure as a file (default is None).
    :param theme: Optional dictionary to customize Seaborn theme (default is None).
    :return: A tuple containing the Figure and Axes objects.
    """
    data = _validate_and_sort_timestamp(data)

    if theme:
        sns.set_theme(**theme)

    fig, ax = plt.subplots(figsize=fig_size)
    sns.lineplot(label=label, x=x_id, y=y_id, color=color, marker=marker, data=data, ax=ax)
    ax.set_xlabel(x_id)
    ax.set_ylabel(y_id)

    if save_path is not None:
        save_file = os.path.join(save_path, 'TODO_FILENAME.pdf')
        fig.savefig(save_file)
        log.info(f'Plot saved to {save_file}')

    plt.close(fig)
    return fig, ax