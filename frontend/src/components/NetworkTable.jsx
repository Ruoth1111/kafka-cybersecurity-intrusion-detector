/**
 * NetworkTable — live events table with colour-coded rows
 */

function categoryClass(cat) {
  const map = { Normal: 'normal', DoS: 'dos', Probe: 'probe', R2L: 'r2l', U2R: 'u2r' };
  return map[cat] || 'normal';
}

function formatBytes(n) {
  if (!n) return '0 B';
  if (n < 1024) return `${n} B`;
  if (n < 1_000_000) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1_000_000).toFixed(2)} MB`;
}

function truncTime(iso) {
  if (!iso) return '—';
  return iso.substring(11, 19);
}

export function NetworkTable({ events }) {
  const rows = (events || []).slice(0, 50);

  return (
    <div className="card table-card" id="network-table">
      <div className="chart-header">
        <h2 className="chart-title">🗂 Live Event Stream</h2>
        <span className="text-muted" style={{ fontSize: 12 }}>last 50 events</span>
      </div>
      <div className="table-wrapper">
        <table className="event-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Protocol</th>
              <th>Service</th>
              <th>Flag</th>
              <th>Src Bytes</th>
              <th>Dst Bytes</th>
              <th>Category</th>
              <th>Conf.</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center', padding: '32px', color: '#4a5a7c' }}>
                  Waiting for events...
                </td>
              </tr>
            ) : rows.map((e, i) => {
              const cat = e.attack_category || 'Normal';
              const cls = categoryClass(cat);
              return (
                <tr key={e.id || i} className={`table-row table-row--${cls} ${i === 0 ? 'animate-slide-in' : ''}`}>
                  <td className="mono" style={{ fontSize: 11, color: '#4a5a7c' }}>
                    {truncTime(e.event_time)}
                  </td>
                  <td className="mono" style={{ fontSize: 11 }}>
                    {(e.protocol_type || '—').toUpperCase()}
                  </td>
                  <td className="mono" style={{ fontSize: 11 }}>
                    {e.service || '—'}
                  </td>
                  <td className="mono" style={{ fontSize: 11, color: '#8b9dc5' }}>
                    {e.flag || '—'}
                  </td>
                  <td className="mono" style={{ fontSize: 11, color: '#06b6d4' }}>
                    {formatBytes(e.src_bytes)}
                  </td>
                  <td className="mono" style={{ fontSize: 11, color: '#8b5cf6' }}>
                    {formatBytes(e.dst_bytes)}
                  </td>
                  <td>
                    <span className={`badge badge-${cls}`}>{cat}</span>
                  </td>
                  <td className="mono" style={{ fontSize: 11 }}>
                    {e.rf_confidence ? `${(e.rf_confidence * 100).toFixed(0)}%` : '—'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
