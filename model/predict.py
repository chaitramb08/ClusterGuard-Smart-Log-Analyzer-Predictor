"""
model/predict.py
Phase 3 — Load the trained model and score a time window's log
statistics for failure risk. Called from app.py's /predict endpoint.
"""

import os
import sys
import joblib
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

FEATURES = ["total_logs", "error_count", "warn_count",
            "distinct_events", "distinct_components", "error_warn_ratio"]

MODEL_PATH = os.path.join(os.path.dirname(__file__), "failure_model.pkl")
SCALER_PATH = os.path.join(os.path.dirname(__file__), "scaler.pkl")

_model = None
_scaler = None


def _load_artifacts():
    global _model, _scaler
    if _model is None or _scaler is None:
        _model = joblib.load(MODEL_PATH)
        _scaler = joblib.load(SCALER_PATH)
    return _model, _scaler


def predict_window(total_logs, error_count, warn_count,
                    distinct_events, distinct_components):
    """Score one time window's stats for failure risk."""
    model, scaler = _load_artifacts()

    error_warn_ratio = (error_count + warn_count) / total_logs if total_logs else 0
    X = pd.DataFrame([{
        "total_logs": total_logs,
        "error_count": error_count,
        "warn_count": warn_count,
        "distinct_events": distinct_events,
        "distinct_components": distinct_components,
        "error_warn_ratio": error_warn_ratio,
    }])[FEATURES]

    X_scaled = scaler.transform(X)
    prediction = model.predict(X_scaled)[0]        # 1 = normal, -1 = anomaly
    score = model.decision_function(X_scaled)[0]     # lower = more anomalous

    is_anomaly = prediction == -1
    return {
        "is_anomaly": bool(is_anomaly),
        "anomaly_score": float(score),
        "message": "Potential failure risk detected" if is_anomaly else "Normal behavior"
    }


def predict_latest_window():
    """
    Convenience helper — recomputes the most recent window from the
    live DB and scores it. Useful for a 'current health' check.
    """
    from database.db_connection import get_connection
    from data_analysis.analyze_logs import build_timestamp, build_window_features

    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM logs", conn)
    conn.close()

    if df.empty:
        return {"error": "no logs in database"}

    df = build_timestamp(df)
    features = build_window_features(df)
    latest = features.iloc[-1]

    return predict_window(
        total_logs=latest["total_logs"],
        error_count=latest["error_count"],
        warn_count=latest["warn_count"],
        distinct_events=latest["distinct_events"],
        distinct_components=latest["distinct_components"],
    )

def predict_trend():
    """
    Forecasts near-term risk by extrapolating the trend of the last 3
    anomaly scores, rather than training a new classifier on a handful
    of data points (which would be statistically unreliable on a small
    sample). Returns a forward-looking risk call for the *next* window.
    """
    import numpy as np
    import pandas as pd
    from database.db_connection import get_connection
    from data_analysis.analyze_logs import build_timestamp, build_window_features, WINDOW

    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM logs", conn)
    conn.close()
    if df.empty:
        return {"error": "no logs in database"}

    df = build_timestamp(df)
    features = build_window_features(df)
    if len(features) < 2:
        return {"error": "not enough windows yet to compute a trend"}

    scores = []
    for _, row in features.iterrows():
        pred = predict_window(
            row["total_logs"], row["error_count"], row["warn_count"],
            row["distinct_events"], row["distinct_components"]
        )
        scores.append(pred["anomaly_score"])

    recent = scores[-3:] if len(scores) >= 3 else scores
    slope = np.polyfit(range(len(recent)), recent, 1)[0] if len(recent) > 1 else 0
    current_score = scores[-1]

    # worsening trend + already low score => flag risk ahead
    will_be_at_risk = slope < -0.01 and current_score < 0.05

    return {
        "will_be_at_risk": bool(will_be_at_risk),
        "current_score": float(current_score),
        "trend_slope": float(slope),
        "horizon_seconds": int(WINDOW.rstrip("s")),
        "message": (
            f"System predicted to become AT RISK within the next {WINDOW} — "
            f"anomaly score trending down ({slope:.4f}/window)."
            if will_be_at_risk else
            f"System predicted to remain STABLE for the next {WINDOW}."
        ),
    }