#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# Stop All Services — Shutdown Script
# ─────────────────────────────────────────────────────────────
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "=================================================="
echo "🛑 Stopping Real-Time Cybersecurity System Services..."
echo "=================================================="

if [ -f logs/producer.pid ]; then
    PID=$(cat logs/producer.pid)
    kill $PID 2>/dev/null || true
    rm logs/producer.pid
    echo "   Stopped Producer (PID: $PID)"
fi

if [ -f logs/backend.pid ]; then
    PID=$(cat logs/backend.pid)
    kill $PID 2>/dev/null || true
    rm logs/backend.pid
    echo "   Stopped Backend (PID: $PID)"
fi

if [ -f logs/frontend.pid ]; then
    PID=$(cat logs/frontend.pid)
    kill $PID 2>/dev/null || true
    rm logs/frontend.pid
    echo "   Stopped Frontend (PID: $PID)"
fi

# Clean up ports if lingering
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:5173 | xargs kill -9 2>/dev/null || true

echo "✅ All background services stopped."
