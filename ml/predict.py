"""
ML Prediction Module — Singleton loader for inference
=====================================================
Provides a single `predict(event_dict)` function used by the consumer.

Returns:
    {
        "attack_category":  "DoS" | "Normal" | "Probe" | "R2L" | "U2R",
        "attack_label":     original raw label (pass-through from event),
        "rf_confidence":    float (0.0 – 1.0),
        "anomaly_score":    float (negative = more anomalous),
        "is_anomaly":       bool
    }
"""

import os
import joblib
import numpy as np

# ─────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────
_MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
_RF_PATH = os.path.join(_MODELS_DIR, "rf_model.pkl")
_ISO_PATH = os.path.join(_MODELS_DIR, "iso_model.pkl")
_FEATURES_PATH = os.path.join(_MODELS_DIR, "feature_cols.pkl")
_ENCODERS_PATH = os.path.join(_MODELS_DIR, "encoders.pkl")

# ─────────────────────────────────────────────────────────────────
# Lazy singleton — load models once
# ─────────────────────────────────────────────────────────────────
_rf_model = None
_iso_model = None
_feature_cols = None
_encoders = None
_models_loaded = False


def _load_models():
    global _rf_model, _iso_model, _feature_cols, _encoders, _models_loaded

    if _models_loaded:
        return True

    if not all(os.path.exists(p) for p in [_RF_PATH, _ISO_PATH, _FEATURES_PATH, _ENCODERS_PATH]):
        print(
            "[WARN] ML models not found. Run: python ml/train.py\n"
            "       Predictions will be skipped."
        )
        return False

    _rf_model = joblib.load(_RF_PATH)
    _iso_model = joblib.load(_ISO_PATH)
    _feature_cols = joblib.load(_FEATURES_PATH)
    _encoders = joblib.load(_ENCODERS_PATH)
    _models_loaded = True
    print("[INFO] ML models loaded successfully.")
    return True


def _build_feature_vector(event: dict) -> np.ndarray:
    """Convert raw event dict → numpy array matching training features."""
    row = {}

    # Categorical columns — encode with saved LabelEncoders
    for col in ["protocol_type", "service", "flag"]:
        val = str(event.get(col, "tcp"))
        le = _encoders.get(col)
        if le is not None:
            known = set(le.classes_)
            if val not in known:
                val = le.classes_[0]
            row[col] = int(le.transform([val])[0])
        else:
            row[col] = 0

    # Numeric columns — fill 0 for missing
    numeric_defaults = {
        "duration": 0, "src_bytes": 0, "dst_bytes": 0, "land": 0,
        "wrong_fragment": 0, "urgent": 0, "hot": 0,
        "num_failed_logins": 0, "logged_in": 0, "num_compromised": 0,
        "root_shell": 0, "su_attempted": 0, "num_root": 0,
        "num_file_creations": 0, "num_shells": 0, "num_access_files": 0,
        "count": 0, "srv_count": 0,
        "serror_rate": 0.0, "srv_serror_rate": 0.0,
        "rerror_rate": 0.0, "srv_rerror_rate": 0.0,
        "same_srv_rate": 0.0, "diff_srv_rate": 0.0,
        "srv_diff_host_rate": 0.0,
        "dst_host_count": 0, "dst_host_srv_count": 0,
        "dst_host_same_srv_rate": 0.0, "dst_host_diff_srv_rate": 0.0,
        "dst_host_same_src_port_rate": 0.0,
        "dst_host_srv_diff_host_rate": 0.0,
        "dst_host_serror_rate": 0.0, "dst_host_srv_serror_rate": 0.0,
        "dst_host_rerror_rate": 0.0, "dst_host_srv_rerror_rate": 0.0,
    }
    for col, default in numeric_defaults.items():
        row[col] = event.get(col, default)

    # Build ordered vector matching training feature_cols
    vector = [row.get(col, 0) for col in _feature_cols]
    return np.array(vector, dtype=float).reshape(1, -1)


def predict(event: dict) -> dict:
    """
    Run inference on a single network event.

    Args:
        event: dict with KDD Cup 99 fields

    Returns:
        dict with prediction results (see module docstring)
    """
    if not _load_models():
        # Models not available — return the label from the event itself
        return {
            "attack_category": event.get("attack_category", "Normal"),
            "attack_label": event.get("label", "normal"),
            "rf_confidence": 1.0,
            "anomaly_score": 0.0,
            "is_anomaly": False,
        }

    X = _build_feature_vector(event)

    # ── Random Forest prediction ───────────────────────────────
    rf_pred = _rf_model.predict(X)[0]  # e.g. "DoS"
    rf_proba = _rf_model.predict_proba(X)[0]
    rf_confidence = float(np.max(rf_proba))

    # ── Isolation Forest anomaly score ─────────────────────────
    # decision_function: lower (more negative) = more anomalous
    anomaly_score = float(_iso_model.decision_function(X)[0])
    is_anomaly = bool(_iso_model.predict(X)[0] == -1)

    return {
        "attack_category": rf_pred,
        "attack_label": event.get("label", rf_pred.lower()),
        "rf_confidence": round(rf_confidence, 4),
        "anomaly_score": round(anomaly_score, 4),
        "is_anomaly": is_anomaly,
    }
