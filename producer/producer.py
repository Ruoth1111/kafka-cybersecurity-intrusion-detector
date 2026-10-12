"""
Kafka Producer — CSV Replay Stream
====================================
Reads kdd_cup_99.csv row by row and publishes each record as a JSON
message to the Kafka topic `network_traffic`, simulating a live
network event stream.

Features:
  - Adds a live `event_time` timestamp to each event
  - Configurable speed via PRODUCER_SLEEP_MS env var
  - --dry-run flag to preview without Kafka
  - --rows N flag to send only N rows (useful for testing)
  - Graceful shutdown on Ctrl+C

Usage:
    python producer/producer.py
    python producer/producer.py --dry-run --rows 10
    PRODUCER_SLEEP_MS=50 python producer/producer.py   # faster replay
"""

import os
import sys
import json
import time
import signal
import argparse
import datetime
import logging
from pathlib import Path

import pandas as pd
from kafka import KafkaProducer
try:
    from kafka.errors import NoBrokersAvailable
except ImportError:
    # kafka-python 3.x renamed this to KafkaConnectionError
    from kafka.errors import KafkaConnectionError as NoBrokersAvailable

# ─────────────────────────────────────────────────────────────────
# Config (from .env or environment)
# ─────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
DATA_PATH = ROOT / "data" / "kdd_cup_99.csv"
BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "network_traffic")
SLEEP_MS = int(os.getenv("PRODUCER_SLEEP_MS", "200"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [PRODUCER] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
# Graceful shutdown
# ─────────────────────────────────────────────────────────────────
_running = True


def _handle_sigint(sig, frame):
    global _running
    log.info("Shutting down producer...")
    _running = False


signal.signal(signal.SIGINT, _handle_sigint)
signal.signal(signal.SIGTERM, _handle_sigint)


# ─────────────────────────────────────────────────────────────────
def create_producer() -> KafkaProducer:
    for attempt in range(1, 6):
        try:
            producer = KafkaProducer(
                bootstrap_servers=BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks="all",
                retries=3,
            )
            log.info(f"Connected to Kafka at {BOOTSTRAP_SERVERS}")
            return producer
        except NoBrokersAvailable:
            log.warning(
                f"Kafka not available (attempt {attempt}/5). "
                "Retrying in 5 seconds..."
            )
            time.sleep(5)
    log.error("Could not connect to Kafka. Is Docker running?")
    log.error("Run: docker compose up -d")
    sys.exit(1)


def stream_csv(producer: KafkaProducer | None, max_rows: int = None, dry_run: bool = False, sleep_sec: float = None, loop: bool = False, shuffle: bool = True):
    if not DATA_PATH.exists():
        log.error(f"Dataset not found: {DATA_PATH}")
        log.error("Run: python data/download_dataset.py")
        sys.exit(1)

    log.info(f"Loading dataset: {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    log.info(f"Loaded {len(df):,} rows")

    if shuffle:
        # Group by attack category and sample evenly so stream has a rich mix of all attack types
        categories = df['attack_category'].unique()
        log.info(f"Shuffling dataset across categories: {list(categories)}")
        dfs = []
        for cat in categories:
            dfs.append(df[df['attack_category'] == cat])
        df = pd.concat(dfs).sample(frac=1).reset_index(drop=True)

    if max_rows:
        df = df.head(max_rows)
        log.info(f"Limited to {max_rows} rows for this run")

    if sleep_sec is None:
        sleep_sec = SLEEP_MS / 1000.0

    rate = 1.0 / sleep_sec if sleep_sec > 0 else 100.0
    log.info(
        f"Streaming to topic '{TOPIC}' at ~{rate:.1f} events/sec "
        f"({'DRY RUN' if dry_run else 'LIVE'})"
    )
    log.info("Press Ctrl+C to stop.\n")

    sent = 0
    attacks = 0

    while True:
        for idx, row in df.iterrows():
            if not _running:
                break

            event = row.to_dict()

            # Add live timestamp with Z suffix for UTC
            event["event_time"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            # Convert numpy types to Python native (JSON serializable)
            for k, v in event.items():
                if hasattr(v, "item"):  # numpy scalar
                    event[k] = v.item()

            category = event.get("attack_category", "Normal")
            is_attack = category != "Normal"

            if dry_run:
                print(json.dumps(event, indent=2))
                print("─" * 60)
            else:
                producer.send(TOPIC, value=event)
                sent += 1
                if is_attack:
                    attacks += 1

                if sent % 50 == 0:
                    log.info(
                        f"Sent: {sent:,} events | "
                        f"Attacks: {attacks} ({100*attacks/sent:.1f}%) | "
                        f"Last: {category}"
                    )

            if sleep_sec > 0:
                time.sleep(sleep_sec)

        if not loop or not _running:
            break
        log.info("Looping dataset replay...")

    if not dry_run and producer:
        producer.flush()
        log.info(
            f"\nProducer finished. Total sent: {sent:,} | Attacks: {attacks}"
        )


def main():
    parser = argparse.ArgumentParser(description="Kafka Network Traffic Producer")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print events to stdout without sending to Kafka",
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=None,
        help="Number of rows to send (default: all)",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=None,
        help="Seconds to sleep between events (e.g. 0.1 for 10 events/sec)",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Continuously loop dataset replay when finished",
    )
    args = parser.parse_args()

    producer = None if args.dry_run else create_producer()

    try:
        stream_csv(producer, max_rows=args.rows, dry_run=args.dry_run, sleep_sec=args.sleep, loop=args.loop)
    finally:
        if producer:
            producer.close()


if __name__ == "__main__":
    main()
