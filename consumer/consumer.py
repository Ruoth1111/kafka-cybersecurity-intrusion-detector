"""
Kafka Consumer — receive events, run ML, store in PostgreSQL
=============================================================
This is the core pipeline:
    Kafka → Consumer → ML Prediction → PostgreSQL → WebSocket broadcast

Run:
    python consumer/consumer.py

Environment variables (see .env):
    KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
"""

import os
import sys
import json
import logging
import datetime
import threading
from pathlib import Path

from kafka import KafkaConsumer
try:
    from kafka.errors import NoBrokersAvailable
except ImportError:
    # kafka-python 3.x renamed this to KafkaConnectionError
    from kafka.errors import KafkaConnectionError as NoBrokersAvailable

# Add project root to path so we can import from ml/ and consumer/
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from consumer.db import wait_for_db, create_tables, get_connection, return_connection, get_severity
from ml.predict import predict

# ─────────────────────────────────────────────────────────────────
KAFKA_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "network_traffic")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CONSUMER] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
# Shared in-memory broadcast queue (used by FastAPI WebSocket)
# ─────────────────────────────────────────────────────────────────
# consumer/consumer.py writes here; backend/main.py reads from here
broadcast_lock = threading.Lock()
_broadcast_callbacks = []  # List[Callable]


def register_broadcast_callback(fn):
    """Register a function to be called with every new event dict."""
    with broadcast_lock:
        _broadcast_callbacks.append(fn)


def _broadcast(event: dict):
    with broadcast_lock:
        dead = []
        for fn in _broadcast_callbacks:
            try:
                fn(event)
            except Exception:
                dead.append(fn)
        for fn in dead:
            _broadcast_callbacks.remove(fn)


# ─────────────────────────────────────────────────────────────────
INSERT_STREAM = """
    INSERT INTO network_stream (
        event_time, protocol_type, service, flag,
        src_bytes, dst_bytes, duration, land, wrong_fragment, urgent, hot,
        logged_in, count, srv_count, serror_rate, rerror_rate,
        same_srv_rate, diff_srv_rate, dst_host_count, dst_host_srv_count,
        attack_category, attack_label, rf_confidence, anomaly_score, is_anomaly
    ) VALUES (
        %(event_time)s, %(protocol_type)s, %(service)s, %(flag)s,
        %(src_bytes)s, %(dst_bytes)s, %(duration)s, %(land)s,
        %(wrong_fragment)s, %(urgent)s, %(hot)s, %(logged_in)s,
        %(count)s, %(srv_count)s, %(serror_rate)s, %(rerror_rate)s,
        %(same_srv_rate)s, %(diff_srv_rate)s, %(dst_host_count)s,
        %(dst_host_srv_count)s,
        %(attack_category)s, %(attack_label)s,
        %(rf_confidence)s, %(anomaly_score)s, %(is_anomaly)s
    ) RETURNING id;
"""

INSERT_ATTACK = """
    INSERT INTO attack_events (
        stream_id, event_time, attack_category, attack_label,
        rf_confidence, anomaly_score, protocol_type, service,
        src_bytes, dst_bytes, severity
    ) VALUES (
        %(stream_id)s, %(event_time)s, %(attack_category)s, %(attack_label)s,
        %(rf_confidence)s, %(anomaly_score)s, %(protocol_type)s, %(service)s,
        %(src_bytes)s, %(dst_bytes)s, %(severity)s
    );
"""


def _safe_int(val, default=0):
    try:
        return int(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def _safe_float(val, default=0.0):
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def process_message(data: dict, conn) -> dict:
    """Run ML prediction, insert to DB, return enriched event."""

    # ── ML prediction ──────────────────────────────────────────
    prediction = predict(data)

    # ── Parse timestamp ────────────────────────────────────────
    raw_time = data.get("event_time", "")
    try:
        event_time = datetime.datetime.fromisoformat(raw_time)
    except Exception:
        event_time = datetime.datetime.utcnow()

    # ── Build enriched event for DB + broadcast ─────────────────
    record = {
        "event_time": event_time,
        "protocol_type": str(data.get("protocol_type", "tcp"))[:10],
        "service": str(data.get("service", "other"))[:50],
        "flag": str(data.get("flag", "SF"))[:20],
        "src_bytes": _safe_int(data.get("src_bytes")),
        "dst_bytes": _safe_int(data.get("dst_bytes")),
        "duration": _safe_int(data.get("duration")),
        "land": _safe_int(data.get("land")),
        "wrong_fragment": _safe_int(data.get("wrong_fragment")),
        "urgent": _safe_int(data.get("urgent")),
        "hot": _safe_int(data.get("hot")),
        "logged_in": _safe_int(data.get("logged_in")),
        "count": _safe_int(data.get("count")),
        "srv_count": _safe_int(data.get("srv_count")),
        "serror_rate": _safe_float(data.get("serror_rate")),
        "rerror_rate": _safe_float(data.get("rerror_rate")),
        "same_srv_rate": _safe_float(data.get("same_srv_rate")),
        "diff_srv_rate": _safe_float(data.get("diff_srv_rate")),
        "dst_host_count": _safe_int(data.get("dst_host_count")),
        "dst_host_srv_count": _safe_int(data.get("dst_host_srv_count")),
        **prediction,  # attack_category, attack_label, rf_confidence, anomaly_score, is_anomaly
    }

    # ── Insert into network_stream ─────────────────────────────
    with conn.cursor() as cur:
        cur.execute(INSERT_STREAM, record)
        stream_id = cur.fetchone()[0]

        # ── Insert into attack_events if it's an attack ────────
        if record["attack_category"] != "Normal":
            severity = get_severity(record["attack_category"], record["rf_confidence"])
            cur.execute(INSERT_ATTACK, {
                **record,
                "stream_id": stream_id,
                "severity": severity,
            })

    conn.commit()

    # Return JSON-serialisable version for WebSocket broadcast
    return {
        "id": stream_id,
        "event_time": event_time.isoformat() + ("" if "Z" in event_time.isoformat() or "+" in event_time.isoformat() else "Z"),
        "protocol_type": record["protocol_type"],
        "service": record["service"],
        "flag": record["flag"],
        "src_bytes": record["src_bytes"],
        "dst_bytes": record["dst_bytes"],
        "attack_category": record["attack_category"],
        "attack_label": record["attack_label"],
        "rf_confidence": record["rf_confidence"],
        "anomaly_score": record["anomaly_score"],
        "is_anomaly": record["is_anomaly"],
        "is_attack": record["attack_category"] != "Normal",
    }


def run_consumer():
    log.info("Waiting for PostgreSQL...")
    wait_for_db()
    create_tables()
    log.info("Tables ready.")

    log.info(f"Connecting to Kafka at {KAFKA_SERVERS}...")
    try:
        consumer = KafkaConsumer(
            TOPIC,
            bootstrap_servers=KAFKA_SERVERS,
            value_deserializer=lambda x: json.loads(x.decode("utf-8")),
            auto_offset_reset="latest",
            enable_auto_commit=True,
            group_id="cybersecurity-consumer-group",
        )
    except NoBrokersAvailable:
        log.error("Cannot connect to Kafka. Ensure Docker is running.")
        sys.exit(1)

    log.info(f"Subscribed to topic '{TOPIC}'. Waiting for messages...\n")

    conn = get_connection()
    received = 0
    attacks = 0

    try:
        for message in consumer:
            data = message.value
            try:
                enriched = process_message(data, conn)
                received += 1
                if enriched["is_attack"]:
                    attacks += 1
                    log.warning(
                        f"🔴 ATTACK | {enriched['attack_category']:<8} | "
                        f"conf={enriched['rf_confidence']:.2f} | "
                        f"{enriched['service']}"
                    )
                elif received % 50 == 0:
                    log.info(
                        f"✅ Processed {received:,} events | "
                        f"Attacks: {attacks} ({100*attacks/received:.1f}%)"
                    )

                # Broadcast to WebSocket clients
                _broadcast(enriched)

            except Exception as e:
                log.error(f"Error processing message: {e}", exc_info=True)
                conn.rollback()

    except KeyboardInterrupt:
        log.info("Consumer stopped by user.")
    finally:
        return_connection(conn)
        consumer.close()


if __name__ == "__main__":
    run_consumer()
