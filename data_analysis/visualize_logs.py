"""
data_analysis/visualize_logs.py
Phase 2 — Generates chart images from the log data and window
features so you have visuals for your report/demo.

Run after analyze_logs.py has produced window_features.csv:
    python data_analysis/visualize_logs.py

Saves PNGs into data_analysis/charts/:
    - level_distribution.png     bar chart of log level counts
    - top_components.png         bar chart of noisiest components
    - log_volume_over_time.png   line chart of total logs per window
    - error_warn_ratio.png       line chart of error/warn ratio per window,
                                  with anomalous windows highlighted if the
                                  model has been trained
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import matplotlib
matplotlib.use("Agg")  # no display needed, just save files
import matplotlib.pyplot as plt

from database.db_connection import get_connection
from data_analysis.analyze_logs import build_timestamp

CHARTS_DIR = os.path.join(os.path.dirname(__file__), "charts")
FEATURES_CSV = os.path.join(os.path.dirname(__file__), "window_features.csv")


def load_logs_df():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM logs", conn)
    conn.close()
    return df


def plot_level_distribution(df, out_dir):
    counts = df["level"].value_counts().reindex(["V", "D", "I", "W", "E"]).fillna(0)
    plt.figure(figsize=(6, 4))
    counts.plot(kind="bar", color=["#999", "#4c72b0", "#55a868", "#dd8452", "#c44e52"])
    plt.title("Log Level Distribution")
    plt.xlabel("Level")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "level_distribution.png"), dpi=150)
    plt.close()


def plot_top_components(df, out_dir, top_n=10):
    counts = df["component"].value_counts().head(top_n)
    plt.figure(figsize=(8, 5))
    counts.sort_values().plot(kind="barh", color="#4c72b0")
    plt.title(f"Top {top_n} Noisiest Components")
    plt.xlabel("Log Count")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "top_components.png"), dpi=150)
    plt.close()


def plot_log_volume(features, out_dir):
    plt.figure(figsize=(9, 4))
    plt.plot(features["timestamp"], features["total_logs"], marker="o", color="#4c72b0")
    plt.title("Log Volume Over Time (per window)")
    plt.xlabel("Time")
    plt.ylabel("Total logs")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "log_volume_over_time.png"), dpi=150)
    plt.close()


def plot_error_warn_ratio(features, out_dir):
    plt.figure(figsize=(9, 4))
    plt.plot(features["timestamp"], features["error_warn_ratio"], marker="o", color="#c44e52")

    # if the model has been trained, highlight anomalous windows
    try:
        from model.predict import predict_window
        anomaly_mask = features.apply(
            lambda r: predict_window(
                r["total_logs"], r["error_count"], r["warn_count"],
                r["distinct_events"], r["distinct_components"]
            )["is_anomaly"],
            axis=1
        )
        plt.scatter(features.loc[anomaly_mask, "timestamp"],
                    features.loc[anomaly_mask, "error_warn_ratio"],
                    color="black", zorder=5, label="Flagged anomalous")
        plt.legend()
    except FileNotFoundError:
        pass  # model not trained yet — just show the raw ratio

    plt.title("Error/Warn Ratio Over Time (per window)")
    plt.xlabel("Time")
    plt.ylabel("Error+Warn / Total")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "error_warn_ratio.png"), dpi=150)
    plt.close()


if __name__ == "__main__":
    os.makedirs(CHARTS_DIR, exist_ok=True)

    df = load_logs_df()
    if df.empty:
        print("No logs found — run crud/import_csv.py first.")
        sys.exit(1)

    plot_level_distribution(df, CHARTS_DIR)
    plot_top_components(df, CHARTS_DIR)
    print("Saved level_distribution.png and top_components.png")

    if not os.path.exists(FEATURES_CSV):
        print("window_features.csv not found — run data_analysis/analyze_logs.py first "
              "to generate the time-series charts.")
    else:
        features = pd.read_csv(FEATURES_CSV, parse_dates=["timestamp"])
        plot_log_volume(features, CHARTS_DIR)
        plot_error_warn_ratio(features, CHARTS_DIR)
        print("Saved log_volume_over_time.png and error_warn_ratio.png")

    print(f"\nAll charts saved to {CHARTS_DIR}")
