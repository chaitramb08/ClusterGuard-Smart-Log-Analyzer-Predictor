import os
import sqlite3
import pandas as pd

DB_NAME = "android_logs.db"
OUTPUT_CSV = "processed_android_ml_dataset.csv"

# Mapping Android single-letter log codes to full names
LEVEL_MAP = {
    "V": "VERBOSE",
    "D": "DEBUG",
    "I": "INFO",
    "W": "WARNING",
    "E": "ERROR",
    "F": "FATAL",
}


def load_data_from_db():
    """Load Android log records directly from SQLite database into Pandas DataFrame."""
    if not os.path.exists(DB_NAME):
        raise FileNotFoundError(
            f"❌ Database '{DB_NAME}' not found! Run db_config.py/main.py first."
        )

    print("⏳ Connecting to SQLite database and fetching logs...")
    conn = sqlite3.connect(DB_NAME)
    query = "SELECT * FROM logs"
    df_logs = pd.read_sql_query(query, conn)
    conn.close()

    print(f"✅ Loaded {len(df_logs):,} log records from '{DB_NAME}'.")
    return df_logs


def preprocess_and_feature_engineer(df):
    """Clean data, map log severity levels, and extract analytical features."""
    print("\n⏳ Preprocessing data and engineering features...")

    # 1. Map single-letter levels to human-readable names
    df["level_full"] = (
        df["level"].map(LEVEL_MAP).fillna(df["level"].str.upper())
    )

    # 2. Binary Anomaly Flagging for ML
    # In system log analysis, Warning, Error, and Fatal levels are flagged as anomalous (1)
    df["is_anomaly"] = df["level"].apply(
        lambda x: 1 if str(x).upper() in ["W", "E", "F", "WARN", "ERROR"] else 0
    )

    # 3. Clean Text Content Metrics
    df["content_length"] = df["content"].apply(lambda x: len(str(x)))
    df["word_count"] = df["content"].apply(lambda x: len(str(x).split()))

    print("✅ Feature engineering completed successfully.")
    return df


def perform_data_analysis(df):
    """Generate exploratory data analysis summary statistics."""
    print("\n" + "=" * 60)
    print("      📊 PHASE 2: ANDROID LOG DATA ANALYSIS REPORT")
    print("=" * 60)

    # Summary 1: Severity Level Distribution (All 5+ Levels)
    print("\n1. Log Severity Level Breakdown:")
    level_counts = df["level_full"].value_counts()
    for lvl, count in level_counts.items():
        pct = (count / len(df)) * 100
        print(f"   • {lvl:<10}: {count:>6,} occurrences ({pct:>5.2f}%)")

    # Summary 2: Normal vs Anomaly Class Balance
    print("\n2. System Health Classification:")
    anomaly_counts = df["is_anomaly"].value_counts()
    normal_cnt = anomaly_counts.get(0, 0)
    anomaly_cnt = anomaly_counts.get(1, 0)
    total = len(df)
    print(
        f"   • Normal Logs (V/D/I): {normal_cnt:>6,} ({normal_cnt / total * 100:>5.2f}%)"
    )
    print(
        f"   • Anomaly Logs (W/E/F): {anomaly_cnt:>6,} ({anomaly_cnt / total * 100:>5.2f}%)"
    )

    # Summary 3: Top Active Components
    print("\n3. Top 5 Software Components Logging Events:")
    top_components = df["component"].value_counts().head(5)
    for comp, count in top_components.items():
        print(f"   • {comp:<25}: {count:>6,} logs")

    # Summary 4: Top Error/Warning Producing Components
    print("\n4. Components with Highest Warning/Error Frequencies:")
    err_df = df[df["is_anomaly"] == 1]
    if not err_df.empty:
        top_err_comps = err_df["component"].value_counts().head(5)
        for comp, count in top_err_comps.items():
            print(f"   • {comp:<25}: {count:>6,} issue logs")
    else:
        print("   • No high-severity logs recorded.")

    # Summary 5: Top Event Templates
    if "event_id" in df.columns:
        print("\n5. Top 3 Frequent Log Event IDs:")
        top_events = df["event_id"].value_counts().head(3)
        for event, count in top_events.items():
            print(f"   • Event ID {event}: {count:>6,} occurrences")

    print("\n" + "=" * 60)


def export_ml_dataset(df, output_file=OUTPUT_CSV):
    """Save processed features into a clean CSV for model training."""
    df.to_csv(output_file, index=False)
    print(f"\n💾 ML-ready dataset saved to '{output_file}' successfully!")


if __name__ == "__main__":
    # Execute Stage 2 Data Analysis Pipeline
    raw_df = load_data_from_db()
    processed_df = preprocess_and_feature_engineer(raw_df)
    perform_data_analysis(processed_df)
    export_ml_dataset(processed_df)