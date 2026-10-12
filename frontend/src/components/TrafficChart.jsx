/**
 * TrafficChart — real-time line chart of events per second
 * Uses a rolling 60-second window.
 */
import { useMemo } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from 'recharts';

const CATEGORY_COLORS = {
  Normal: '#10b981',
  DoS:    '#ef4444',
  Probe:  '#f97316',
  R2L:    '#f59e0b',
  U2R:    '#8b5cf6',
};

function parseTs(tStr) {
  if (!tStr) return Date.now();
  if (typeof tStr === 'number') return tStr;
  let str = String(tStr).trim().replace(' ', 'T');
  if (!str.endsWith('Z') && !str.includes('+') && !str.includes('-')) {
    str += 'Z';
  }
  const parsed = new Date(str).getTime();
  return isNaN(parsed) ? Date.now() : parsed;
}

// Bucket events into 5-second intervals
function buildTimeSeries(events) {
  if (!events || !events.length) return [];

  const parsedEvents = events.map(e => ({
    ...e,
    _ts: parseTs(e.event_time),
  }));

  const latestEventTs = Math.max(...parsedEvents.map(e => e._ts));
  const now = Date.now();

  // If latest event is within the last 5 minutes, anchor at current time.
  // Otherwise anchor at the latest event time so historical batches render cleanly.
  const anchorTime = (Math.abs(now - latestEventTs) < 300000) ? now : latestEventTs;

  const buckets = {};
  for (let i = 0; i < 60; i++) {
    const ts = Math.floor((anchorTime - i * 5000) / 5000) * 5000;
    buckets[ts] = { time: ts, Normal: 0, DoS: 0, Probe: 0, R2L: 0, U2R: 0, total: 0 };
  }

  parsedEvents.forEach(e => {
    const ts = Math.floor(e._ts / 5000) * 5000;
    if (buckets[ts]) {
      const cat = e.attack_category || 'Normal';
      buckets[ts][cat] = (buckets[ts][cat] || 0) + 1;
      buckets[ts].total += 1;
    }
  });

  return Object.values(buckets)
    .sort((a, b) => a.time - b.time)
    .map(b => ({
      ...b,
      label: new Date(b.time).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
    }));
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'rgba(13,18,38,0.95)',
      border: '1px solid rgba(59,130,246,0.3)',
      borderRadius: 8,
      padding: '10px 14px',
      fontSize: 13,
    }}>
      <p style={{ color: '#8b9dc5', marginBottom: 6 }}>{label}</p>
      {payload.map(p => (
        <p key={p.name} style={{ color: CATEGORY_COLORS[p.name] || '#fff' }}>
          {p.name}: <strong>{p.value}</strong>
        </p>
      ))}
    </div>
  );
};

export function TrafficChart({ events }) {
  const data = useMemo(() => buildTimeSeries(events), [events]);

  return (
    <div className="card chart-card" id="traffic-chart">
      <div className="chart-header">
        <h2 className="chart-title">📈 Live Network Traffic</h2>
        <span className="text-muted" style={{ fontSize: 12 }}>5-second buckets · last 5 min</span>
      </div>
      <div className="chart-body">
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <defs>
              {Object.entries(CATEGORY_COLORS).map(([name, color]) => (
                <linearGradient key={name} id={`grad-${name}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={color} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={color} stopOpacity={0.02} />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis
              dataKey="label"
              tick={{ fill: '#4a5a7c', fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fill: '#4a5a7c', fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              width={30}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ fontSize: 12, color: '#8b9dc5' }}
              iconType="circle"
              iconSize={8}
            />
            {['Normal', 'DoS', 'Probe', 'R2L', 'U2R'].map(cat => (
              <Area
                key={cat}
                type="monotone"
                dataKey={cat}
                stackId="1"
                stroke={CATEGORY_COLORS[cat]}
                fill={`url(#grad-${cat})`}
                strokeWidth={1.5}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
