"""
FastAPI Backend — REST API + WebSocket for the React dashboard
==============================================================
Endpoints:
    GET  /health          — liveness probe
    GET  /traffic         — latest N events from network_stream
    GET  /attacks         — latest N attack events
    GET  /statistics      — aggregate counts + breakdown
    GET  /alerts          — recent HIGH/MEDIUM severity attacks
    WS   /ws              — WebSocket: push new events in real time

Run:
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
"""

import os
import sys
import json
import asyncio
import logging
import threading
from pathlib import Path
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import psycopg2.extras

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from consumer.db import (
    wait_for_db, create_tables, get_connection, return_connection
)
import consumer.consumer as consumer_module

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [BACKEND] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="CyberSecurity Intrusion Detection API",
    description="Real-time network traffic analytics powered by ML",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────
# WebSocket Connection Manager
# ─────────────────────────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self._clients: List[WebSocket] = []
        self._lock = asyncio.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._clients.append(ws)
        log.info(f"WebSocket client connected. Total: {len(self._clients)}")

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            if ws in self._clients:
                self._clients.remove(ws)
        log.info(f"WebSocket client disconnected. Total: {len(self._clients)}")

    def broadcast_from_thread(self, event: dict):
        """Thread-safe broadcast called from the consumer thread."""
        if self._loop and self._clients:
            asyncio.run_coroutine_threadsafe(
                self._broadcast(event), self._loop
            )

    async def _broadcast(self, event: dict):
        msg = json.dumps(event)
        async with self._lock:
            dead = []
            for ws in self._clients:
                try:
                    await ws.send_text(msg)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self._clients.remove(ws)


manager = ConnectionManager()


# ─────────────────────────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────────────────────────
def _query(sql: str, params=None) -> list:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]
    finally:
        return_connection(conn)


def _query_one(sql: str, params=None) -> dict:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else {}
    finally:
        return_connection(conn)


# ─────────────────────────────────────────────────────────────────
# Startup / shutdown
# ─────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    log.info("Waiting for PostgreSQL...")
    wait_for_db()
    create_tables()
    log.info("DB ready.")

    # Capture the asyncio event loop so consumer thread can broadcast
    loop = asyncio.get_running_loop()
    manager.set_loop(loop)

    # Register consumer broadcast callback
    consumer_module.register_broadcast_callback(manager.broadcast_from_thread)

    # Start consumer in a background thread
    def _run_consumer():
        try:
            consumer_module.run_consumer()
        except SystemExit:
            log.warning("Consumer exited (Kafka may not be available).")
        except Exception as e:
            log.error(f"Consumer crashed: {e}", exc_info=True)

    t = threading.Thread(target=_run_consumer, daemon=True, name="kafka-consumer")
    t.start()
    log.info("Kafka consumer started in background thread.")


# ─────────────────────────────────────────────────────────────────
# REST Endpoints
# ─────────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "service": "cybersecurity-api"}


@app.get("/traffic", tags=["Data"])
def get_traffic(limit: int = Query(default=50, le=500)):
    """Return the latest N network stream events."""
    rows = _query(
        "SELECT * FROM network_stream ORDER BY event_time DESC LIMIT %s",
        (limit,)
    )
    # Convert timestamps to ISO strings with Z suffix for UTC
    for r in rows:
        for k in ("event_time", "created_at"):
            if r.get(k):
                s = r[k].isoformat() if hasattr(r[k], 'isoformat') else str(r[k])
                s = s.replace(" ", "T")
                if not s.endswith("Z"):
                    s += "Z"
                r[k] = s
    return {"data": rows, "count": len(rows)}


@app.get("/attacks", tags=["Data"])
def get_attacks(limit: int = Query(default=50, le=500)):
    """Return the latest N attack events."""
    rows = _query(
        "SELECT * FROM attack_events ORDER BY event_time DESC LIMIT %s",
        (limit,)
    )
    for r in rows:
        for k in ("event_time", "created_at"):
            if r.get(k):
                s = r[k].isoformat() if hasattr(r[k], 'isoformat') else str(r[k])
                s = s.replace(" ", "T")
                if not s.endswith("Z"):
                    s += "Z"
                r[k] = s
    return {"data": rows, "count": len(rows)}


@app.get("/statistics", tags=["Analytics"])
def get_statistics():
    """Return aggregate counts and breakdowns."""
    totals = _query_one("""
        SELECT
            COUNT(*)                                        AS total_events,
            SUM(CASE WHEN attack_category != 'Normal' THEN 1 ELSE 0 END) AS total_attacks,
            SUM(CASE WHEN attack_category  = 'Normal' THEN 1 ELSE 0 END) AS total_normal,
            SUM(COALESCE(src_bytes,0) + COALESCE(dst_bytes,0))           AS total_bytes
        FROM network_stream
    """)

    by_category = _query("""
        SELECT attack_category, COUNT(*) AS count
        FROM network_stream
        GROUP BY attack_category
        ORDER BY count DESC
    """)

    by_protocol = _query("""
        SELECT protocol_type, COUNT(*) AS count
        FROM network_stream
        GROUP BY protocol_type
        ORDER BY count DESC
    """)

    by_service = _query("""
        SELECT service, COUNT(*) AS count
        FROM network_stream
        GROUP BY service
        ORDER BY count DESC
        LIMIT 10
    """)

    traffic_timeline = _query("""
        SELECT
            DATE_TRUNC('minute', event_time) AS minute,
            COUNT(*) AS events,
            SUM(CASE WHEN attack_category != 'Normal' THEN 1 ELSE 0 END) AS attacks
        FROM network_stream
        WHERE event_time >= NOW() - INTERVAL '30 minutes'
        GROUP BY minute
        ORDER BY minute
    """)
    for r in traffic_timeline:
        if r.get("minute"):
            r["minute"] = str(r["minute"])

    return {
        "totals": {k: (int(v) if v is not None else 0) for k, v in totals.items()},
        "by_category": by_category,
        "by_protocol": by_protocol,
        "by_service": by_service,
        "traffic_timeline": traffic_timeline,
    }


@app.get("/alerts", tags=["Analytics"])
def get_alerts(limit: int = Query(default=20, le=100)):
    """Return recent HIGH and MEDIUM severity alerts."""
    rows = _query(
        """
        SELECT * FROM attack_events
        WHERE severity IN ('HIGH', 'MEDIUM')
        ORDER BY event_time DESC
        LIMIT %s
        """,
        (limit,)
    )
    for r in rows:
        for k in ("event_time", "created_at"):
            if r.get(k):
                s = r[k].isoformat() if hasattr(r[k], 'isoformat') else str(r[k])
                s = s.replace(" ", "T")
                if not s.endswith("Z"):
                    s += "Z"
                r[k] = s
    return {"data": rows, "count": len(rows)}


# ─────────────────────────────────────────────────────────────────
# WebSocket
# ─────────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive; send ping every 30s
            await asyncio.sleep(30)
            await websocket.send_text('{"type":"ping"}')
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception:
        await manager.disconnect(websocket)
