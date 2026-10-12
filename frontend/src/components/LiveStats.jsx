/**
 * LiveStats — 4 KPI cards: Total Traffic, Attacks, Normal, Alert Rate
 */
export function LiveStats({ stats, recentCount }) {
  const totals = stats?.totals || {};

  const kpis = [
    {
      id: 'kpi-traffic',
      label: 'Total Events',
      value: totals.total_events?.toLocaleString() || '0',
      icon: '📡',
      color: 'var(--accent-blue)',
      glow: 'rgba(59,130,246,0.2)',
      sub: `${recentCount || 0} in last batch`,
    },
    {
      id: 'kpi-attacks',
      label: 'Attacks Detected',
      value: totals.total_attacks?.toLocaleString() || '0',
      icon: '🔴',
      color: 'var(--color-dos)',
      glow: 'rgba(239,68,68,0.2)',
      sub: totals.total_events
        ? `${((totals.total_attacks / totals.total_events) * 100).toFixed(1)}% attack rate`
        : '—',
    },
    {
      id: 'kpi-normal',
      label: 'Normal Traffic',
      value: totals.total_normal?.toLocaleString() || '0',
      icon: '✅',
      color: 'var(--color-normal)',
      glow: 'rgba(16,185,129,0.2)',
      sub: totals.total_events
        ? `${((totals.total_normal / totals.total_events) * 100).toFixed(1)}% clean`
        : '—',
    },
    {
      id: 'kpi-bytes',
      label: 'Data Processed',
      value: totals.total_bytes
        ? `${(totals.total_bytes / 1_000_000).toFixed(1)} MB`
        : '0 MB',
      icon: '💾',
      color: 'var(--accent-purple)',
      glow: 'rgba(139,92,246,0.2)',
      sub: 'Total src + dst bytes',
    },
  ];

  return (
    <div className="kpi-grid">
      {kpis.map(kpi => (
        <div
          key={kpi.id}
          id={kpi.id}
          className="kpi-card card"
          style={{ '--kpi-color': kpi.color, '--kpi-glow': kpi.glow }}
        >
          <div className="kpi-icon">{kpi.icon}</div>
          <div className="kpi-content">
            <div className="kpi-value" style={{ color: kpi.color }}>{kpi.value}</div>
            <div className="kpi-label">{kpi.label}</div>
            <div className="kpi-sub text-muted">{kpi.sub}</div>
          </div>
          <div className="kpi-glow-ring" />
        </div>
      ))}
    </div>
  );
}
