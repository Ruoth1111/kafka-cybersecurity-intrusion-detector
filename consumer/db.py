"""
Database Helper — PostgreSQL connection + table creation
=========================================================
Used by both the consumer (writes) and backend (reads).
"""

import os
import time
import logging
import psycopg2
from psycopg2 import pool

log = logging.getLogger(__name__)

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5433"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "cybersecurity")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")

_pool: pool.ThreadedConnectionPool | None = None

# ─────────────────────────────────────────────────────────────────
DDL = """
CREATE TABLE IF NOT EXISTS network_stream (
    id                          SERIAL PRIMARY KEY,
    event_time                  TIMESTAMP NOT NULL,
    protocol_type               VARCHAR(10),
    service                     VARCHAR(50),
    flag                        VARCHAR(20),
    src_bytes                   BIGINT,
    dst_bytes                   BIGINT,
    duration                    INTEGER,
    land                        INTEGER,
    wrong_fragment              INTEGER,
    urgent                      INTEGER,
    hot                         INTEGER,
    logged_in                   INTEGER,
    count                       INTEGER,
    srv_count                   INTEGER,
    serror_rate                 FLOAT,
    rerror_rate                 FLOAT,
    same_srv_rate               FLOAT,
    diff_srv_rate               FLOAT,
    dst_host_count              INTEGER,
    dst_host_srv_count          INTEGER,
    attack_category             VARCHAR(20),
    attack_label                VARCHAR(50),
    rf_confidence               FLOAT,
    anomaly_score               FLOAT,
    is_anomaly                  BOOLEAN,
    created_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ns_event_time
    ON network_stream(event_time DESC);

CREATE INDEX IF NOT EXISTS idx_ns_attack_category
    ON network_stream(attack_category);

CREATE TABLE IF NOT EXISTS attack_events (
    id                SERIAL PRIMARY KEY,
    stream_id         INTEGER REFERENCES network_stream(id),
    event_time        TIMESTAMP NOT NULL,
    attack_category   VARCHAR(20),
    attack_label      VARCHAR(50),
    rf_confidence     FLOAT,
    anomaly_score     FLOAT,
    protocol_type     VARCHAR(10),
    service           VARCHAR(50),
    src_bytes         BIGINT,
    dst_bytes         BIGINT,
    severity          VARCHAR(10),
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ae_event_time
    ON attack_events(event_time DESC);
"""


def get_connection():
    """Get a connection from the pool (creates pool on first call)."""
    global _pool
    if _pool is None:
        _pool = pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
        )
    return _pool.getconn()


def return_connection(conn):
    if _pool:
        _pool.putconn(conn)


def wait_for_db(retries: int = 10, delay: int = 3):
    """Block until PostgreSQL is ready (useful at container startup)."""
    for i in range(retries):
        try:
            conn = psycopg2.connect(
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                dbname=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
            )
            conn.close()
            log.info("PostgreSQL is ready.")
            return
        except psycopg2.OperationalError:
            log.warning(
                f"PostgreSQL not ready (attempt {i+1}/{retries}). "
                f"Retrying in {delay}s..."
            )
            time.sleep(delay)
    raise RuntimeError("Cannot connect to PostgreSQL. Is Docker running?")


def create_tables():
    """Create tables if they don't exist."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(DDL)
        conn.commit()
        log.info("Database tables ready.")
    finally:
        return_connection(conn)


# ─────────────────────────────────────────────────────────────────
# SEVERITY helper
# ─────────────────────────────────────────────────────────────────
def get_severity(attack_category: str, rf_confidence: float) -> str:
    if attack_category == "Normal":
        return "LOW"
    if attack_category in ("DoS", "U2R") or rf_confidence >= 0.90:
        return "HIGH"
    if attack_category in ("Probe", "R2L") or rf_confidence >= 0.70:
        return "MEDIUM"
    return "LOW"
