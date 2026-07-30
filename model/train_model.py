"""
model/train_model.py
Phase 3 — Train an anomaly-detection model on the time-window
features produced by Phase 2 (data_analysis/window_features.csv).

Uses IsolationForest, unsupervised, since the dataset has no
ground-truth "failure" labels — it learns what normal log traffic
looks like and flags windows that deviate (error/warn spikes,
unusual event/component diversity).
"""

import os
import sys
import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

FEATURES = ["total_logs", "error_count", "warn_count",
            "distinct_events", "distinct_components", "error_warn_ratio"]

MODEL_PATH = os.path.join(os.path.dirname(__file__), "failure_model.pkl")
SCALER_PATH = os.path.join(os.path.dirname(__file__), "scaler.pkl")


def load_features():
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data_analysis", "window_features.csv")
    return pd.read_csv(csv_path)


def train():
    df = load_features()
    if df.empty:
        raise ValueError("window_features.csv is empty — run data_analysis/analyze_logs.py first.")

    X = df[FEATURES]
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(
        n_estimators=200,
        contamination=0.1,   # assume ~10% of windows are anomalous — tune as needed
        random_state=42
    )
    model.fit(X_scaled)

    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    print(f"Model saved to {MODEL_PATH}")
    print(f"Scaler saved to {SCALER_PATH}")

    # quick check: how many windows would be flagged on the training data itself
    preds = model.predict(X_scaled)
    print(f"Flagged {(preds == -1).sum()} / {len(preds)} windows as anomalous")


if __name__ == "__main__":
    train()
