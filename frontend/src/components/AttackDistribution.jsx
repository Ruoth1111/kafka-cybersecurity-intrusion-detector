/**
 * AttackDistribution — bar chart breakdown by attack category
 */
import { useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, LabelList,
} from 'recharts';

const COLORS = {
  Normal: '#10b981',
  DoS:    '#ef4444',
  Probe:  '#f97316',
  R2L:    '#f59e0b',
  U2R:    '#8b5cf6',
};

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div style={{
      background: 'rgba(13,18,38,0.95)',
      border: '1px solid rgba(59,130,246,0.3)',
      borderRadius: 8,
      padding: '10px 14px',
      fontSize: 13,
    }}>
      <p style={{ color: COLORS[d.attack_category] || '#fff', fontWeight: 700 }}>
        {d.attack_category}
      </p>
      <p style={{ color: '#8b9dc5' }}>Count: <strong style={{ color: '#f0f4ff' }}>{d.count?.toLocaleString()}</strong></p>
    </div>
  );
};

export function AttackDistribution({ stats }) {
  const data = useMemo(() => {
    if (!stats?.by_category) return [];
    return stats.by_category.map(d => ({
      attack_category: d.attack_category,
      count: Number(d.count),
    }));
  }, [stats]);

  return (
    <div className="card chart-card" id="attack-distribution">
      <div className="chart-header">
        <h2 className="chart-title">⚡ Attack Distribution</h2>
        <span className="text-muted" style={{ fontSize: 12 }}>by category</span>
      </div>
      <div className="chart-body">
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 5 }} barSize={36}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
            <XAxis
              dataKey="attack_category"
              tick={{ fill: '#8b9dc5', fontSize: 11 }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              tick={{ fill: '#4a5a7c', fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              width={35}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(59,130,246,0.05)' }} />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              <LabelList
                dataKey="count"
                position="top"
                formatter={v => v?.toLocaleString()}
                style={{ fill: '#8b9dc5', fontSize: 10 }}
              />
              {data.map((entry, i) => (
                <Cell key={i} fill={COLORS[entry.attack_category] || '#3b82f6'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
