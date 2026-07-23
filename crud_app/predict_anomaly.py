import joblib
import numpy as np
import pandas as pd
from scipy.sparse import hstack


def predict_log_anomaly(level, component, content, pid=0, tid=0):
    """Pass any raw log line to classify it in real-time."""
    # Load saved artifacts
    model = joblib.load("anomaly_detector_model.pkl")
    tfidf = joblib.load("tfidf_vectorizer.pkl")
    ohe = joblib.load("onehot_encoder.pkl")

    # Engineer single-sample features
    content_len = len(content)
    word_cnt = len(content.split())

    df_sample = pd.DataFrame(
        [{"component": component, "level": level.upper()}]
    )

    X_text = tfidf.transform([content])
    X_cat = ohe.transform(df_sample)
    X_num = np.array([[pid, tid, content_len, word_cnt]])

    X_combined = hstack([X_text, X_cat, X_num])

    prediction = model.predict(X_combined)[0]
    confidence = model.predict_proba(X_combined)[0][prediction]

    status = "🚨 ANOMALY" if prediction == 1 else "✅ NORMAL"
    return status, confidence


if __name__ == "__main__":
    # Test Case 1: Normal Log
    status, conf = predict_log_anomaly(
        level="D",
        component="WindowManager",
        content="Performing layout pass for all windows",
    )
    print(f"Test 1: {status} (Confidence: {conf * 100:.2f}%)")

    # Test Case 2: Anomaly Log
    status, conf = predict_log_anomaly(
        level="E",
        component="ActivityManager",
        content="NullPointer Exception occurred while launching service",
    )
    print(f"Test 2: {status} (Confidence: {conf * 100:.2f}%)")