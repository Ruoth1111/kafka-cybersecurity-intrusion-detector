"""
Download and preprocess the KDD Cup 99 dataset.

Usage:
    python data/download_dataset.py

Output:
    data/kdd_cup_99.csv   — cleaned CSV ready for streaming

Uses scikit-learn's built-in fetch_kddcup99() which downloads from
a reliable source (avoids UCI 403 Forbidden errors on direct URLs).
"""

import os
import pandas as pd
from sklearn.datasets import fetch_kddcup99

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "kdd_cup_99.csv")

# ─────────────────────────────────────────────────────────────────
# Attack category mapping
# ─────────────────────────────────────────────────────────────────
DOS_ATTACKS = {
    "back", "land", "neptune", "pod", "smurf", "teardrop",
    "apache2", "udpstorm", "processtable", "worm",
}
PROBE_ATTACKS = {"ipsweep", "nmap", "portsweep", "satan", "mscan", "saint"}
R2L_ATTACKS = {
    "ftp_write", "guess_passwd", "imap", "multihop", "phf", "spy",
    "warezclient", "warezmaster", "sendmail", "named",
    "snmpgetattack", "snmpguess", "xlock", "xsnoop", "httptunnel",
}
U2R_ATTACKS = {
    "buffer_overflow", "loadmodule", "perl", "rootkit",
    "sqlattack", "xterm", "ps",
}


def map_attack_category(label: str) -> str:
    label = label.lower().strip().rstrip(".")
    if label == "normal":
        return "Normal"
    elif label in DOS_ATTACKS:
        return "DoS"
    elif label in PROBE_ATTACKS:
        return "Probe"
    elif label in R2L_ATTACKS:
        return "R2L"
    elif label in U2R_ATTACKS:
        return "U2R"
    else:
        return "DoS"  # unknown variants are mostly DoS


def decode(val):
    """Decode bytes → str (sklearn returns byte strings for categoricals)."""
    if isinstance(val, bytes):
        return val.decode("utf-8").strip().rstrip(".")
    return str(val).strip().rstrip(".")


def download_and_prepare():
    if os.path.exists(OUTPUT_PATH):
        print(f"[INFO] Dataset already exists at {OUTPUT_PATH}")
        df = pd.read_csv(OUTPUT_PATH)
        print(f"[INFO] Rows: {len(df):,}  Columns: {len(df.columns)}")
        print(f"[INFO] Attack distribution:\n{df['attack_category'].value_counts()}")
        return

    print("[INFO] Downloading KDD Cup 99 via scikit-learn (10% sample)...")
    print("[INFO] This may take 30-90 seconds on first run...")
    print("[INFO] Data is cached in ~/scikit_learn_data/ for future use.\n")

    # fetch_kddcup99 downloads from a reliable sklearn mirror and caches locally
    bunch = fetch_kddcup99(
        percent10=True,
        download_if_missing=True,
        as_frame=False,
        shuffle=False,
        random_state=42,
    )

    print("[INFO] Building DataFrame...")

    # Standard KDD Cup 99 feature names
    feature_names = [
        "duration", "protocol_type", "service", "flag",
        "src_bytes", "dst_bytes", "land", "wrong_fragment", "urgent",
        "hot", "num_failed_logins", "logged_in", "num_compromised",
        "root_shell", "su_attempted", "num_root", "num_file_creations",
        "num_shells", "num_access_files", "num_outbound_cmds",
        "is_host_login", "is_guest_login", "count", "srv_count",
        "serror_rate", "srv_serror_rate", "rerror_rate", "srv_rerror_rate",
        "same_srv_rate", "diff_srv_rate", "srv_diff_host_rate",
        "dst_host_count", "dst_host_srv_count",
        "dst_host_same_srv_rate", "dst_host_diff_srv_rate",
        "dst_host_same_src_port_rate", "dst_host_srv_diff_host_rate",
        "dst_host_serror_rate", "dst_host_srv_serror_rate",
        "dst_host_rerror_rate", "dst_host_srv_rerror_rate",
    ]

    df = pd.DataFrame(bunch.data, columns=feature_names)

    # Decode bytes columns (sklearn returns bytes for categoricals)
    for col in df.columns:
        sample = df[col].iloc[0] if len(df) > 0 else None
        if isinstance(sample, (bytes, bytearray)):
            df[col] = df[col].apply(decode)
        else:
            try:
                df[col] = pd.to_numeric(df[col])
            except Exception:
                df[col] = df[col].apply(decode)

    # Labels come as bytes like b'normal.', b'neptune.' etc.
    df["label"] = [decode(t) for t in bunch.target]

    # Map to 5-category attack taxonomy
    df["attack_category"] = df["label"].apply(map_attack_category)

    df.to_csv(OUTPUT_PATH, index=False)

    print(f"\n[SUCCESS] Saved {len(df):,} rows → {OUTPUT_PATH}")
    print(f"\n[INFO] Attack distribution:")
    print(df["attack_category"].value_counts())
    print(f"\n[INFO] Protocol distribution:")
    print(df["protocol_type"].value_counts())
    print(f"\n[INFO] Top labels: {list(df['label'].value_counts().head(6).index)}")


if __name__ == "__main__":
    download_and_prepare()
