import os
import joblib
import numpy as np
import pandas as pd
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
import xgboost as xgb

# File Constants
PROCESSED_DATA_PATH = "processed_android_ml_dataset.csv"
MODEL_PATH = "anomaly_detector_model.pkl"
VECTORIZER_PATH = "tfidf_vectorizer.pkl"
ENCODER_PATH = "onehot_encoder.pkl"


def load_data():
    """Load preprocessed dataset generated in Phase 2."""
    if not os.path.exists(PROCESSED_DATA_PATH):
        raise FileNotFoundError(
            f"❌ '{PROCESSED_DATA_PATH}' not found! Please run data_analysis.py first."
        )

    print("⏳ Loading preprocessed Android log dataset...")
    df = pd.read_csv(PROCESSED_DATA_PATH)
    print(f"✅ Loaded {len(df):,} records for ML training.")
    return df


def prepare_features(df):
    """Extract and combine Text, Categorical, and Numeric features for ML training."""
    print("\n⏳ Extracting features (TF-IDF + One-Hot Encoding)...")

    # 1. Fill missing values
    df["content"] = df["content"].fillna("")
    df["component"] = df["component"].fillna("UNKNOWN")
    df["level"] = df["level"].fillna("INFO")

    # 2. Text Feature Extraction using TF-IDF on Log Content
    tfidf = TfidfVectorizer(max_features=300, stop_words="english")
    X_text = tfidf.fit_transform(df["content"])

    # 3. Categorical Encoding (Component & Level)
    ohe = OneHotEncoder(handle_unknown="ignore", sparse_output=True)
    X_cat = ohe.fit_transform(df[["component", "level"]])

    # 4. Numerical Features
    num_cols = ["pid", "tid", "content_length", "word_count"]
    # Normalize/fill numerical features
    X_num = df[num_cols].fillna(0).values

    # 5. Combine all features into a single sparse matrix
    X_combined = hstack([X_text, X_cat, X_num])
    y = df["is_anomaly"].values

    # Save vectorizer and encoder for real-time inference in future phases
    joblib.dump(tfidf, VECTORIZER_PATH)
    joblib.dump(ohe, ENCODER_PATH)
    print("✅ Feature transformers saved successfully.")

    return X_combined, y, tfidf, ohe


def train_and_evaluate_model(X, y):
    """Train XGBoost model and print performance metrics."""
    # 1. Stratified Train-Test Split (80% train, 20% test)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    print(
        f"\n⏳ Data split completed: {X_train.shape[0]:,} train samples, {X_test.shape[0]:,} test samples."
    )

    # 2. Calculate scale_pos_weight to handle class imbalance
    negative_count = np.sum(y_train == 0)
    positive_count = np.sum(y_train == 1)
    scale_weight = (
        negative_count / positive_count if positive_count > 0 else 1.0
    )

    # 3. Initialize and train XGBoost Classifier
    print("⏳ Training XGBoost Anomaly Detection Model...")
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        scale_pos_weight=scale_weight,
        random_state=42,
        eval_metric="logloss",
    )
    model.fit(X_train, y_train)

    # 4. Predictions & Evaluation
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    print("\n" + "=" * 60)
    print("       🎯 PHASE 3: MODEL EVALUATION RESULTS")
    print("=" * 60)

    print("\n📊 Classification Report:")
    print(
        classification_report(
            y_test, y_pred, target_names=["Normal (0)", "Anomaly (1)"]
        )
    )

    print("📊 Confusion Matrix:")
    cm = confusion_matrix(y_test, y_pred)
    print(f"   • True Negatives (Normal detected as Normal): {cm[0][0]}")
    print(f"   • False Positives (Normal misclassified as Anomaly): {cm[0][1]}")
    print(f"   • False Negatives (Anomaly missed): {cm[1][0]}")
    print(f"   • True Positives (Anomaly correctly caught): {cm[1][1]}")

    roc_auc = roc_auc_score(y_test, y_proba)
    print(f"\n📈 ROC-AUC Score: {roc_auc:.4f}")
    print("=" * 60)

    # 5. Save Trained Model
    joblib.dump(model, MODEL_PATH)
    print(f"\n💾 Model exported successfully to '{MODEL_PATH}'")


if __name__ == "__main__":
    df = load_data()
    X, y, tfidf, ohe = prepare_features(df)
    train_and_evaluate_model(X, y)