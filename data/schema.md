# Data Schema — KDD Cup 99

## Source

- **Dataset**: KDD Cup 1999 (10% sample)
- **URL**: http://kdd.ics.uci.edu/databases/kddcup99/kddcup99.html
- **Rows**: ~494,021
- **File**: `data/kdd_cup_99.csv`

---

## Original KDD Cup Columns (41 features + label)

| # | Column | Type | Description |
|---|--------|------|-------------|
| 1 | `duration` | int | Duration of connection (seconds) |
| 2 | `protocol_type` | str | tcp / udp / icmp |
| 3 | `service` | str | Network service (http, ftp, smtp…) |
| 4 | `flag` | str | Connection status flag |
| 5 | `src_bytes` | int | Bytes from source to destination |
| 6 | `dst_bytes` | int | Bytes from destination to source |
| 7 | `land` | int | 1 if same src/dst IP:port |
| 8 | `wrong_fragment` | int | Number of wrong fragments |
| 9 | `urgent` | int | Number of urgent packets |
| 10 | `hot` | int | Number of "hot" indicators |
| 11 | `num_failed_logins` | int | Failed login attempts |
| 12 | `logged_in` | int | 1 if logged in successfully |
| 13 | `num_compromised` | int | Compromised conditions |
| 14 | `root_shell` | int | 1 if root shell obtained |
| 15 | `su_attempted` | int | 1 if su root was attempted |
| 16 | `num_root` | int | Root accesses |
| 17 | `num_file_creations` | int | File creation operations |
| 18 | `num_shells` | int | Shell prompts |
| 19 | `num_access_files` | int | Operations on access control files |
| 20 | `num_outbound_cmds` | int | Outbound FTP commands |
| 21 | `is_host_login` | int | 1 if login belongs to host list |
| 22 | `is_guest_login` | int | 1 if guest login |
| 23 | `count` | int | Connections to same host (2 sec) |
| 24 | `srv_count` | int | Connections to same service (2 sec) |
| 25 | `serror_rate` | float | % SYN errors |
| 26 | `srv_serror_rate` | float | % SYN errors (same service) |
| 27 | `rerror_rate` | float | % REJ errors |
| 28 | `srv_rerror_rate` | float | % REJ errors (same service) |
| 29 | `same_srv_rate` | float | % connections to same service |
| 30 | `diff_srv_rate` | float | % connections to diff services |
| 31 | `srv_diff_host_rate` | float | % connections to diff hosts |
| 32 | `dst_host_count` | int | Destination host connection count |
| 33 | `dst_host_srv_count` | int | Destination host service count |
| 34 | `dst_host_same_srv_rate` | float | % same service (dst host) |
| 35 | `dst_host_diff_srv_rate` | float | % diff service (dst host) |
| 36 | `dst_host_same_src_port_rate` | float | % same source port |
| 37 | `dst_host_srv_diff_host_rate` | float | % diff hosts (dst host svc) |
| 38 | `dst_host_serror_rate` | float | % SYN errors (dst host) |
| 39 | `dst_host_srv_serror_rate` | float | % SYN errors (dst host svc) |
| 40 | `dst_host_rerror_rate` | float | % REJ errors (dst host) |
| 41 | `dst_host_srv_rerror_rate` | float | % REJ errors (dst host svc) |
| 42 | `label` | str | Attack label (see mapping below) |

---

## Attack Label Mapping

Raw KDD labels are mapped to 5 categories:

| Category | Raw Labels |
|----------|-----------|
| `Normal` | normal |
| `DoS` | back, land, neptune, pod, smurf, teardrop, apache2, udpstorm, processtable, worm |
| `Probe` | ipsweep, nmap, portsweep, satan, mscan, saint |
| `R2L` | ftp_write, guess_passwd, imap, multihop, phf, spy, warezclient, warezmaster, sendmail, named, snmpgetattack, snmpguess, xlock, xsnoop, httptunnel |
| `U2R` | buffer_overflow, loadmodule, perl, rootkit, sqlattack, xterm, ps |

---

## PostgreSQL Table: `network_stream`

```sql
CREATE TABLE network_stream (
    id              SERIAL PRIMARY KEY,
    event_time      TIMESTAMP NOT NULL,
    protocol_type   VARCHAR(10),
    service         VARCHAR(50),
    flag            VARCHAR(20),
    src_bytes       BIGINT,
    dst_bytes       BIGINT,
    duration        INTEGER,
    land            INTEGER,
    wrong_fragment  INTEGER,
    urgent          INTEGER,
    hot             INTEGER,
    logged_in       INTEGER,
    count           INTEGER,
    srv_count       INTEGER,
    serror_rate     FLOAT,
    rerror_rate     FLOAT,
    same_srv_rate   FLOAT,
    diff_srv_rate   FLOAT,
    dst_host_count  INTEGER,
    dst_host_srv_count INTEGER,
    attack_category VARCHAR(20),   -- Normal / DoS / Probe / R2L / U2R
    attack_label    VARCHAR(50),   -- raw label (e.g. neptune)
    rf_confidence   FLOAT,         -- Random Forest confidence score
    anomaly_score   FLOAT,         -- Isolation Forest score (lower = more anomalous)
    is_anomaly      BOOLEAN,       -- Isolation Forest flag
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_event_time ON network_stream(event_time DESC);
CREATE INDEX idx_attack_category ON network_stream(attack_category);
```

## PostgreSQL Table: `attack_events`

```sql
CREATE TABLE attack_events (
    id              SERIAL PRIMARY KEY,
    stream_id       INTEGER REFERENCES network_stream(id),
    event_time      TIMESTAMP NOT NULL,
    attack_category VARCHAR(20),
    attack_label    VARCHAR(50),
    rf_confidence   FLOAT,
    anomaly_score   FLOAT,
    protocol_type   VARCHAR(10),
    service         VARCHAR(50),
    src_bytes       BIGINT,
    dst_bytes       BIGINT,
    severity        VARCHAR(10),   -- HIGH / MEDIUM / LOW
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_attack_event_time ON attack_events(event_time DESC);
```
