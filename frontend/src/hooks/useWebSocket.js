/**
 * useWebSocket — connects to the FastAPI WebSocket endpoint
 * and pushes each incoming event into a local state queue.
 *
 * Usage:
 *   const { events, connected, stats } = useWebSocket('ws://localhost:8000/ws');
 */

import { useState, useEffect, useRef, useCallback } from 'react';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const MAX_EVENTS = 200;

export function useWebSocket() {
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState([]);
  const [stats, setStats] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);

  // ── Fetch initial statistics from REST API ──────────────────
  const fetchStats = useCallback(async () => {
    try {
      const [statsRes, alertsRes, trafficRes] = await Promise.all([
        fetch(`${API_URL}/statistics`),
        fetch(`${API_URL}/alerts?limit=15`),
        fetch(`${API_URL}/traffic?limit=100`),
      ]);
      if (statsRes.ok) setStats(await statsRes.json());
      if (alertsRes.ok) {
        const d = await alertsRes.json();
        setAlerts(d.data || []);
      }
      if (trafficRes.ok) {
        const t = await trafficRes.json();
        if (t.data && t.data.length > 0) {
          setEvents(prev => (prev.length === 0 ? t.data : prev));
        }
      }
    } catch {
      // API not ready yet — ignore
    }
  }, []);

  // ── Connect WebSocket ───────────────────────────────────────
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      fetchStats();
    };

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.type === 'ping') return;

      setEvents(prev => {
        const next = [data, ...prev];
        return next.slice(0, MAX_EVENTS);
      });

      // Update alerts list if it's an attack
      if (data.is_attack) {
        setAlerts(prev => {
          const next = [data, ...prev];
          return next.slice(0, 50);
        });
      }

      // Refresh full stats every 20 events
      setEvents(prev => {
        if (prev.length % 20 === 0) fetchStats();
        return prev;
      });
    };

    ws.onclose = () => {
      setConnected(false);
      // Reconnect after 3 seconds
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [fetchStats]);

  useEffect(() => {
    connect();
    // Poll stats every 10s as fallback
    const statsPoll = setInterval(fetchStats, 10000);
    return () => {
      wsRef.current?.close();
      clearTimeout(reconnectTimer.current);
      clearInterval(statsPoll);
    };
  }, [connect, fetchStats]);

  return { connected, events, stats, alerts };
}
