import './App.css';
import { useWebSocket } from './hooks/useWebSocket';
import { Header } from './components/Header';
import { LiveStats } from './components/LiveStats';
import { TrafficChart } from './components/TrafficChart';
import { AttackDistribution } from './components/AttackDistribution';
import { ProtocolPie } from './components/ProtocolPie';
import { AlertFeed } from './components/AlertFeed';
import { NetworkTable } from './components/NetworkTable';

function App() {
  const { connected, events, stats, alerts } = useWebSocket();

  const totals = stats?.totals || {};

  return (
    <div className="app">
      <Header
        connected={connected}
        totalEvents={totals.total_events}
        totalAttacks={totals.total_attacks}
      />

      <main className="main-content">
        {/* ── KPI Row ─────────────────────────────────────────── */}
        <LiveStats stats={stats} recentCount={events.length} />

        {/* ── Charts Row ──────────────────────────────────────── */}
        <div className="charts-row">
          <div className="charts-main">
            <TrafficChart events={events} />
          </div>
          <div className="charts-side">
            <AttackDistribution stats={stats} />
            <ProtocolPie stats={stats} />
          </div>
        </div>

        {/* ── Bottom Row ──────────────────────────────────────── */}
        <div className="bottom-row">
          <div className="alerts-col">
            <AlertFeed alerts={alerts} recentEvents={events} />
          </div>
          <div className="table-col">
            <NetworkTable events={events} />
          </div>
        </div>
      </main>

      <footer className="footer">
        <span>🛡 CyberSec Monitor</span>
        <span className="text-muted">KDD Cup 99 · Kafka · PostgreSQL · FastAPI · React</span>
        <span className="text-muted">FDS Intrusion Detection Project</span>
      </footer>
    </div>
  );
}

export default App;
