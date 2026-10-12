#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# Service Status Checker
# ─────────────────────────────────────────────────────────────
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "=================================================="
echo "📊 System Component Status"
echo "=================================================="

# Docker Containers
echo "🐳 Docker Containers:"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
docker ps --format "   • {{.Names}}: {{.Status}} ({{.Ports}})" 2>/dev/null || echo "   ❌ Docker not running"

# FastAPI Backend
echo ""
echo "🐍 FastAPI Backend (port 8000):"
if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    echo "   ✅ ONLINE (http://localhost:8000)"
else
    echo "   ❌ OFFLINE"
fi

# React Frontend
echo ""
echo "⚛️  React Dashboard (port 5173):"
if curl -s http://localhost:5173 >/dev/null 2>&1; then
    echo "   ✅ ONLINE (http://localhost:5173)"
else
    echo "   ❌ OFFLINE"
fi

# Traffic Producer
echo ""
echo "📡 Traffic Producer Daemon:"
if [ -f logs/producer.pid ] && kill -0 $(cat logs/producer.pid) 2>/dev/null; then
    echo "   ✅ RUNNING (PID: $(cat logs/producer.pid))"
else
    echo "   ❌ INACTIVE"
fi

echo "=================================================="
