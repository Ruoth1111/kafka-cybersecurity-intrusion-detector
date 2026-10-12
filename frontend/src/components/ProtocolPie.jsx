/**
 * ProtocolPie — pie chart showing TCP / UDP / ICMP split
 */
import { useMemo } from 'react';
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';

const COLORS = ['#3b82f6', '#06b6d4', '#8b5cf6', '#f59e0b', '#10b981', '#f97316'];

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0];
  return (
    <div style={{
      background: 'rgba(13,18,38,0.95)',
      border: '1px solid rgba(59,130,246,0.3)',
      borderRadius: 8,
      padding: '10px 14px',
      fontSize: 13,
    }}>
      <p style={{ color: d.payload.fill, fontWeight: 700 }}>{d.name}</p>
      <p style={{ color: '#8b9dc5' }}>Count: <strong style={{ color: '#f0f4ff' }}>{d.value?.toLocaleString()}</strong></p>
      <p style={{ color: '#8b9dc5' }}>Share: <strong style={{ color: '#f0f4ff' }}>{d.payload.percent}%</strong></p>
    </div>
  );
};

const renderCustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }) => {
  if (percent < 0.05) return null;
  const RADIAN = Math.PI / 180;
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);
  return (
    <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central" fontSize={11} fontWeight={600}>
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  );
};

export function ProtocolPie({ stats }) {
  const data = useMemo(() => {
    if (!stats?.by_protocol) return [];
    const total = stats.by_protocol.reduce((s, d) => s + Number(d.count), 0);
    return stats.by_protocol.map((d, i) => ({
      name: (d.protocol_type || 'unknown').toUpperCase(),
      value: Number(d.count),
      percent: total ? ((Number(d.count) / total) * 100).toFixed(1) : 0,
      fill: COLORS[i % COLORS.length],
    }));
  }, [stats]);

  return (
    <div className="card chart-card" id="protocol-distribution">
      <div className="chart-header">
        <h2 className="chart-title">🌐 Protocol Split</h2>
        <span className="text-muted" style={{ fontSize: 12 }}>TCP / UDP / ICMP</span>
      </div>
      <div className="chart-body">
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={80}
              paddingAngle={3}
              dataKey="value"
              labelLine={false}
              label={renderCustomLabel}
            >
              {data.map((entry, i) => (
                <Cell key={i} fill={entry.fill} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
            <Legend
              iconType="circle"
              iconSize={8}
              wrapperStyle={{ fontSize: 12, color: '#8b9dc5' }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
