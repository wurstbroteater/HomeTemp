from visualize.vis_logger import vis_log as log
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime, timedelta


def draw_plots(df, temp_outside=None, with_save=True):
    sns.set_theme(style="darkgrid")  # sns.set(style="whitegrid")
    fig = plt.figure(figsize=(25, 12))
    gs = fig.add_gridspec(2, 2, height_ratios=[2, 2])  # 2 rows, 1 column

    # Temperature Measurements
    plt.subplot(gs[0])
    sns.lineplot(label="Home", x="timestamp", y="room_temp", data=df)
    plt.title("Temperature Over Time")
    plt.xlabel("Time")
    plt.ylabel("Temp (°C)")
    plt.legend()
    plt.xticks(rotation=45)
    # plt.tight_layout()
    # plt.show()

    # Humidity Measurement
    plt.subplot(gs[1])
    sns.lineplot(x="timestamp", y="humidity", color='purple', data=df)
    plt.title("Humidity Over Time")
    plt.xlabel("Time")
    plt.ylabel("Humidity (%)")
    plt.xticks(rotation=45, ha='right')
    plt.gca().xaxis.grid(True)
    plt.gca().set_facecolor('#f5f5f5')
    sns.despine(left=True, bottom=True)

    df_last_24h = df[df["timestamp"] >= datetime.now() - timedelta(hours=25)]

    # Temperature Measurements last 24 h
    plt.subplot(gs[2])
    if temp_outside is not None:
        sns.lineplot(label="DWD Forecast", x="timestamp", y="temp", color='orange', marker='o', markersize=6, data=temp_outside)
    sns.lineplot(label="Home", x="timestamp", y="room_temp", marker='o', markersize=6, data=df_last_24h)
    plt.title("Temperature Last 24 Hours")
    plt.xlabel("Time")
    plt.ylabel("Temp (°C)")
    plt.legend()
    plt.xticks(rotation=45)

    # Humidity Measurement last 24 h
    plt.subplot(gs[3])
    sns.lineplot(x="timestamp", y="humidity", marker='o', markersize=6, color='purple', data=df_last_24h)
    plt.title("Humidity Last 24 Hours")
    plt.xlabel("Time")
    plt.ylabel("Humidity (%)")
    plt.xticks(rotation=45, ha='right')
    plt.gca().xaxis.grid(True)
    plt.gca().set_facecolor('#f5f5f5')
    sns.despine(left=True, bottom=True)

    plt.tight_layout()
    if with_save:
        name = datetime.now().strftime("%d-%m-%Y")
        loc = f"plots/{name}.pdf"
        plt.savefig(loc)
        log.info(f"Saved plots to {loc}")
    plt.show()
    plt.close()
    sns.reset_defaults()
