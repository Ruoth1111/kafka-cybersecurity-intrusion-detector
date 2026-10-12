"""
ML Training Script — Random Forest + Isolation Forest
======================================================
Trains two models on the KDD Cup 99 dataset:

  1. Random Forest Classifier  → classifies: Normal / DoS / Probe / R2L / U2R
  2. Isolation Forest          → anomaly score (detects unknown attacks)

Outputs:
    ml/models/rf_model.pkl     — Random Forest + LabelEncoder
    ml/models/iso_model.pkl    — Isolation Forest
    ml/models/feature_cols.pkl — ordered list of feature columns

Usage:
    python ml/train.py

Requirements: scikit-learn, pandas, joblib, numpy
"""

import os
import sys
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

# ─────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, "data", "kdd_cup_99.csv")
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(MODELS_DIR, exist_ok=True)

RF_MODEL_PATH = os.path.join(MODELS_DIR, "rf_model.pkl")
ISO_MODEL_PATH = os.path.join(MODELS_DIR, "iso_model.pkl")
FEATURE_COLS_PATH = os.path.join(MODELS_DIR, "feature_cols.pkl")
ENCODERS_PATH = os.path.join(MODELS_DIR, "encoders.pkl")

# ─────────────────────────────────────────────────────────────────
# Features used for ML
# ─────────────────────────────────────────────────────────────────
CATEGORICAL_COLS = ["protocol_type", "service", "flag"]

NUMERIC_COLS = [
    "duration", "src_bytes", "dst_bytes", "land", "wrong_fragment",
    "urgent", "hot", "num_failed_logins", "logged_in", "num_compromised",
    "root_shell", "su_attempted", "num_root", "num_file_creations",
    "num_shells", "num_access_files", "count", "srv_count",
    "serror_rate", "srv_serror_rate", "rerror_rate", "srv_rerror_rate",
    "same_srv_rate", "diff_srv_rate", "srv_diff_host_rate",
    "dst_host_count", "dst_host_srv_count",
    "dst_host_same_srv_rate", "dst_host_diff_srv_rate",
    "dst_host_same_src_port_rate", "dst_host_srv_diff_host_rate",
    "dst_host_serror_rate", "dst_host_srv_serror_rate",
    "dst_host_rerror_rate", "dst_host_srv_rerror_rate",
]

TARGET_COL = "attack_category"  # Normal / DoS / Probe / R2L / U2R


# ─────────────────────────────────────────────────────────────────
def load_data():
    if not os.path.exists(DATA_PATH):
        print(f"[ERROR] Dataset not found at {DATA_PATH}")
        print("        Run: python data/download_dataset.py")
        sys.exit(1)

    print(f"[INFO] Loading dataset from {DATA_PATH}...")
    df = pd.read_csv(DATA_PATH)
    print(f"[INFO] Loaded {len(df):,} rows, {len(df.columns)} columns")
    return df


def encode_features(df, encoders=None, fit=True):
    """Label-encode categoricals and return (X, encoders_dict)."""
    df = df.copy()

    if encoders is None:
        encoders = {}

    for col in CATEGORICAL_COLS:
        if col not in df.columns:
            df[col] = "unknown"
        if fit:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str))
            encoders[col] = le
        else:
            le = encoders[col]
            # Handle unseen labels gracefully
            known = set(le.classes_)
            df[col] = df[col].astype(str).apply(
                lambda x: x if x in known else le.classes_[0]
            )
            df[col] = le.transform(df[col])

    all_cols = CATEGORICAL_COLS + NUMERIC_COLS
    available = [c for c in all_cols if c in df.columns]
    X = df[available].fillna(0).values
    return X, encoders, available


def train():
    df = load_data()

    print("\n[INFO] Attack distribution:")
    print(df[TARGET_COL].value_counts())

    # ── Encode features ────────────────────────────────────────
    X, encoders, feature_cols = encode_features(df)
    y = df[TARGET_COL].values

    print(f"\n[INFO] Feature count: {len(feature_cols)}")
    print(f"[INFO] Features: {feature_cols[:10]}...")

    # ── Train/Test split ───────────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\n[INFO] Train: {len(X_train):,}  Test: {len(X_test):,}")

    # ── Random Forest ──────────────────────────────────────────
    print("\n[INFO] Training Random Forest Classifier...")
    rf = RandomForestClassifier(
        n_estimators=100,
        max_depth=20,
        min_samples_split=5,
        n_jobs=-1,
        random_state=42,
        verbose=1,
    )
    rf.fit(X_train, y_train)

    y_pred = rf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\n[RESULT] Random Forest Accuracy: {acc:.4f} ({acc*100:.2f}%)")
    print("\n[RESULT] Classification Report:")
    print(classification_report(y_test, y_pred))

    # Feature importances
    importances = pd.Series(rf.feature_importances_, index=feature_cols)
    print("\n[INFO] Top 10 Feature Importances:")
    print(importances.nlargest(10).to_string())

    # ── Isolation Forest (anomaly detection) ───────────────────
    print("\n[INFO] Training Isolation Forest (anomaly detector)...")
    # Train on Normal traffic only — learns the "normal" distribution
    normal_mask = y_train == "Normal"
    X_normal = X_train[normal_mask]
    print(f"[INFO] Training Isolation Forest on {len(X_normal):,} normal samples")

    iso = IsolationForest(
        n_estimators=100,
        contamination=0.05,  # Expect ~5% anomalies in production
        random_state=42,
        n_jobs=-1,
        verbose=0,
    )
    iso.fit(X_normal)

    # Evaluate on test set
    iso_scores = iso.decision_function(X_test)
    iso_preds = iso.predict(X_test)  # -1 = anomaly, 1 = normal
    attack_mask = y_test != "Normal"
    # Higher anomaly detection rate on attacks = better
    anomaly_detected = np.sum(iso_preds[attack_mask] == -1)
    total_attacks = np.sum(attack_mask)
    print(
        f"[RESULT] Isolation Forest detected {anomaly_detected}/{total_attacks} "
        f"attacks as anomalies ({100*anomaly_detected/max(total_attacks,1):.1f}%)"
    )

    # ── Save models ────────────────────────────────────────────
    joblib.dump(rf, RF_MODEL_PATH)
    joblib.dump(iso, ISO_MODEL_PATH)
    joblib.dump(feature_cols, FEATURE_COLS_PATH)
    joblib.dump(encoders, ENCODERS_PATH)

    print(f"\n[SUCCESS] Models saved:")
    print(f"  → {RF_MODEL_PATH}")
    print(f"  → {ISO_MODEL_PATH}")
    print(f"  → {FEATURE_COLS_PATH}")
    print(f"  → {ENCODERS_PATH}")
    print("\nTraining complete! You can now start the producer and consumer.")


if __name__ == "__main__":
    train()
