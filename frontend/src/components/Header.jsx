/**
 * Header — top navigation bar with live status indicator
 */
export function Header({ connected, totalEvents, totalAttacks }) {
  return (
    <header className="header">
      <div className="header-left">
        <div className="header-logo">
          <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
            <path d="M16 2L4 8v8c0 7.2 5.2 13.9 12 15.5C23 29.9 28 23.2 28 16V8L16 2z"
              fill="rgba(59,130,246,0.2)" stroke="#3b82f6" strokeWidth="1.5"/>
            <path d="M12 16l3 3 6-6" stroke="#06b6d4" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
        <div>
          <h1 className="header-title">CyberSec Monitor</h1>
          <p className="header-subtitle">AI-Powered Intrusion Detection System</p>
        </div>
      </div>

      <div className="header-center">
        <div className="header-stat">
          <span className="header-stat-value">{totalEvents?.toLocaleString() || '—'}</span>
          <span className="header-stat-label">Events</span>
        </div>
        <div className="header-divider" />
        <div className="header-stat">
          <span className="header-stat-value" style={{ color: 'var(--color-dos)' }}>
            {totalAttacks?.toLocaleString() || '—'}
          </span>
          <span className="header-stat-label">Attacks</span>
        </div>
      </div>

      <div className="header-right">
        <div className={`live-indicator ${connected ? 'live-indicator--connected' : 'live-indicator--disconnected'}`}>
          <span className="live-dot" />
          {connected ? 'LIVE' : 'OFFLINE'}
        </div>
      </div>
    </header>
  );
}
