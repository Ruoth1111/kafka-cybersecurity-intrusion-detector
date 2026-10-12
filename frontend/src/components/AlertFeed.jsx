/**
 * AlertFeed — scrollable live alert list with severity badges
 */
import { useEffect, useRef } from 'react';

const CATEGORY_EMOJI = {
  DoS:   '🔴',
  Probe: '🟠',
  R2L:   '🟡',
  U2R:   '🟣',
};

function timeAgo(isoStr) {
  const diff = (Date.now() - new Date(isoStr).getTime()) / 1000;
  if (diff < 5)  return 'just now';
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

function AlertItem({ alert, isNew }) {
  const cat = alert.attack_category || 'DoS';
  const severity = alert.severity || (cat === 'DoS' || cat === 'U2R' ? 'HIGH' : 'MEDIUM');
  const conf = alert.rf_confidence ? `${(alert.rf_confidence * 100).toFixed(0)}%` : '—';

  return (
    <div
      className={`alert-item ${isNew ? 'animate-slide-in' : ''}`}
      style={{
        '--alert-color':
          cat === 'DoS' ? 'var(--color-dos)'   :
          cat === 'U2R' ? 'var(--color-u2r)'   :
          cat === 'R2L' ? 'var(--color-r2l)'   :
                          'var(--color-probe)',
      }}
    >
      <div className="alert-icon">{CATEGORY_EMOJI[cat] || '⚠️'}</div>
      <div className="alert-content">
        <div className="alert-top">
          <span className="alert-category">{cat}</span>
          <span className={`badge badge-${severity.toLowerCase()}`}>{severity}</span>
          <span className="alert-service mono">{alert.service || alert.attack_label || '—'}</span>
        </div>
        <div className="alert-bottom">
          <span className="text-muted" style={{ fontSize: 11 }}>
            conf: <strong style={{ color: 'var(--alert-color)' }}>{conf}</strong>
          </span>
          <span className="text-muted" style={{ fontSize: 11 }}>
            {alert.protocol_type?.toUpperCase() || '—'}
          </span>
          <span className="text-muted" style={{ fontSize: 11 }}>
            {timeAgo(alert.event_time || alert.created_at)}
          </span>
        </div>
      </div>
    </div>
  );
}

export function AlertFeed({ alerts, recentEvents }) {
  const listRef = useRef(null);

  // Get recent attacks from live WebSocket events
  const liveAttacks = (recentEvents || [])
    .filter(e => e.is_attack)
    .slice(0, 5);

  // Merge: live events first, then REST alerts (deduped by id)
  const merged = [...liveAttacks];
  const liveIds = new Set(liveAttacks.map(e => e.id));
  (alerts || []).forEach(a => {
    if (!liveIds.has(a.id)) merged.push(a);
  });
  const displayed = merged.slice(0, 20);

  return (
    <div className="card alert-feed" id="alert-feed">
      <div className="chart-header">
        <h2 className="chart-title">🚨 Live Alerts</h2>
        <span className="badge badge-dos" style={{ fontSize: 10 }}>
          {displayed.filter(a => (a.severity || '') === 'HIGH' || a.attack_category === 'DoS' || a.attack_category === 'U2R').length} HIGH
        </span>
      </div>

      {displayed.length === 0 ? (
        <div className="alert-empty">
          <div style={{ fontSize: 32, marginBottom: 8 }}>🟢</div>
          <p className="text-muted">No attacks detected yet</p>
          <p className="text-muted" style={{ fontSize: 12 }}>Waiting for traffic...</p>
        </div>
      ) : (
        <div className="alert-list" ref={listRef}>
          {displayed.map((alert, i) => (
            <AlertItem
              key={alert.id || `${alert.event_time}-${i}`}
              alert={alert}
              isNew={i < liveAttacks.length}
            />
          ))}
        </div>
      )}
    </div>
  );
}
