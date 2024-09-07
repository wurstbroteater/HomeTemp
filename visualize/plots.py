from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import seaborn as sns

from visualize.vis_logger import vis_log as log


def draw_plots(df, dwd_df=None, google_df=None, wettercom_df=None, ulmde_df=None, with_save=True, save_path=None):
    sns.set_theme(style="darkgrid")
    fig = plt.figure(figsize=(25, 12))
    gs = fig.add_gridspec(2, 2, height_ratios=[2, 2])

    # Temperature Measurements
    plt.subplot(gs[0])
    sns.lineplot(label="Home", x="timestamp", y="room_temp", data=df)
    if dwd_df is not None:
        sns.lineplot(label="DWD Forecast", x="timestamp", y="temp", alpha=0.6, data=dwd_df)
    if google_df is not None:
        sns.lineplot(label="Google Forecast", x="timestamp", y="temp", alpha=0.6, data=google_df)
    if wettercom_df is not None:
        sns.lineplot(label="Wetter.com Forecast", x="timestamp", y="temp_stat", alpha=0.6, data=wettercom_df)
        sns.lineplot(label="Wetter.com Live", x="timestamp", y="temp_dyn", alpha=0.6, data=wettercom_df)
    if ulmde_df is not None:
        sns.lineplot(label="Ulm.de Forecast", x="timestamp", y="temp", alpha=0.6, data=ulmde_df)
    plt.title("Temperature Over Time")
    plt.xlabel("Time")
    plt.ylabel("Temp (°C)")
    plt.legend()
    plt.xticks(rotation=45)
    # plt.tight_layout()
    # plt.show()

    # Humidity Measurement
    plt.subplot(gs[1])
    sns.lineplot(label="Home", x="timestamp", y="humidity", color='purple', data=df)
    if google_df is not None:
        sns.lineplot(label="Google Forecast", x="timestamp", y="humidity", data=google_df)
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
    sns.lineplot(label="Home", x="timestamp", y="room_temp", marker='o', markersize=6, data=df_last_24h)
    if dwd_df is not None:
        dwd_df_last_24h = dwd_df[dwd_df["timestamp"] >= datetime.now() - timedelta(hours=25)]
        sns.lineplot(label="DWD Forecast", x="timestamp", y="temp", marker='o', markersize=6, data=dwd_df_last_24h)
    if google_df is not None:
        google_df_last_24h = google_df[google_df["timestamp"] >= datetime.now() - timedelta(hours=25)]
        sns.lineplot(label="Google Forecast", x="timestamp", y="temp", marker='o', markersize=6,
                     data=google_df_last_24h)
    if wettercom_df is not None:
        wettercom_df_last_24h = wettercom_df[wettercom_df["timestamp"] >= datetime.now() - timedelta(hours=25)]
        sns.lineplot(label="Wetter.com Forecast", x="timestamp", y="temp_stat", marker='o', data=wettercom_df_last_24h)
        sns.lineplot(label="Wetter.com Live", x="timestamp", y="temp_dyn", marker='s', data=wettercom_df_last_24h)
    if ulmde_df is not None:
        ulmde_df_last_24h = ulmde_df[ulmde_df["timestamp"] >= datetime.now() - timedelta(hours=25)]
        sns.lineplot(label="Ulm.de Forecast", x="timestamp", y="temp", alpha=0.6, marker='o', data=ulmde_df_last_24h)
    plt.title("Temperature Last 24 Hours")
    plt.xlabel("Time")
    plt.ylabel("Temp (°C)")
    plt.legend()
    plt.xticks(rotation=45)

    # Humidity Measurement last 24 h
    plt.subplot(gs[3])
    sns.lineplot(label="Home", x="timestamp", y="humidity", marker='o', markersize=6, color='purple', data=df_last_24h)
    if google_df is not None:
        sns.lineplot(label="Google Forecast", x="timestamp", y="humidity", marker='o', markersize=6,
                     data=google_df_last_24h)
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
        if save_path is None:
            loc = f"plots/{name}.pdf"
        else:
            loc = save_path
        plt.savefig(loc)
        log.info(f"Saved plots to {loc}")
    plt.show()
    plt.close()
    sns.reset_defaults()
