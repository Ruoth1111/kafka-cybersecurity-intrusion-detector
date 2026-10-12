#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# Start All Services — Background Daemon Launcher
# ─────────────────────────────────────────────────────────────
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

mkdir -p logs

echo "=================================================="
echo "🛡  Starting Real-Time Cybersecurity Analytics "
echo "=================================================="

export PATH="$PROJECT_DIR/venv/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

# 1. Start Docker Containers (Kafka, Zookeeper, Postgres)
echo "1️⃣  Checking Docker containers..."
docker compose up -d
echo "   ✅ Docker containers active (Postgres port 5433, Kafka port 9092)"

# 2. Activate Python Venv
source venv/bin/activate

# 3. Start FastAPI Backend Server
echo "2️⃣  Starting FastAPI Backend Server (port 8000)..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
nohup python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > logs/backend.log 2>&1 &
echo $! > logs/backend.pid
echo "   ✅ Backend started in background (PID: $(cat logs/backend.pid))"

# 4. Start React Frontend Dashboard
echo "3️⃣  Starting React Dashboard (port 5173)..."
lsof -ti:5173 | xargs kill -9 2>/dev/null || true
cd "$PROJECT_DIR/frontend"
export PATH="/opt/homebrew/bin:$PATH"
nohup npm run dev > ../logs/frontend.log 2>&1 &
echo $! > ../logs/frontend.pid
cd "$PROJECT_DIR"
echo "   ✅ React Dashboard started in background (PID: $(cat logs/frontend.pid))"

# 5. Stop any old producer and start fresh Shuffled Traffic Producer Daemon
echo "4️⃣  Starting Fresh Shuffled Traffic Producer (Kafka Replay Stream)..."
if [ -f logs/producer.pid ]; then
    kill -9 $(cat logs/producer.pid) 2>/dev/null || true
    rm -f logs/producer.pid
fi
pkill -f "producer.py" 2>/dev/null || true

nohup python producer/producer.py --sleep 0.1 --loop > logs/producer.log 2>&1 &
echo $! > logs/producer.pid
echo "   ✅ Shuffled Traffic Producer started in background (PID: $(cat logs/producer.pid))"

echo ""
echo "=================================================="
echo "🚀 All services running cleanly in the background!"
echo "   • React Dashboard: http://localhost:5173"
echo "   • FastAPI Backend: http://localhost:8000"
echo "   • API Health:      http://localhost:8000/health"
echo "   • Log Files:       logs/backend.log, logs/frontend.log, logs/producer.log"
echo "=================================================="
