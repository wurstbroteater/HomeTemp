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


def main_plot_params(fr,title, marker=None, color=None, alpha=None, markersize=None):
    out = {
        "data": fr,
        "title": title,
        # if set overwrite x/y label with this
        "xlabel": "Time",
        "ylabel": "Temp (°C)",
        # mandatory seaborn parameters
        "label": "Home",
        "x": "timestamp",
        "y" : "room_temp",
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

def inner_plots_params(fr, label, x, y, alpha=0.6):
    return {
        "data": fr,
        "label": "Home",
        "x": "timestamp",
        "y" : "room_temp",
       "alpha" :alpha
    }


def create_multiple_lineplots(plot_params: List[dict], 
                              fig_size: Tuple[int, int] = (25, 12), 
                              theme: Optional[dict] = None, 
                              save_path: str = None,
                              rows=2,
                              cols=1,
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

    if num_plots < 2:
        raise ValueError("there must be at least 2 plot to draw")
    
    if theme:
        sns.set_theme(**theme)


    #rows =  1 if num_plots >= 2 else (n if r == 0 else n +1)
    n, r = divmod(num_plots, rows)
    #cols = 2 if num_plots >= 2 else 1
    print(f"rows{rows} cols{cols}")
    fig, axes = plt.subplots(rows,cols, figsize=fig_size)
    
    if num_plots == 1:
        # Ensure axes is a list even if there's only one plot
        axes = [axes]  
    
    for idx, wrapper_dict in enumerate(plot_params):
        plot_dict = wrapper_dict["main"]
        data = plot_dict.pop('data')
        title = plot_dict.pop('title')
        xlabel = plot_dict.pop('xlabel', plot_dict.get('x'))
        ylabel = plot_dict.pop('ylabel', plot_dict.get('y'))
        ax_in_subplot = axes[idx]
        print(plot_dict)
        sns.lineplot(data=data, ax=ax_in_subplot, **plot_dict)
        inner_plots = wrapper_dict.get('inner', None)
        if inner_plots:
            for inner_plot_dicts in inner_plots:
                    sns.lineplot(label="Wetter.com Live", x="timestamp", y="temp_dyn", alpha=0.6, data=wettercom_df)
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