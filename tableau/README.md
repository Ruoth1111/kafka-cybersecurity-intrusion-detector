# Tableau Integration Guide

## Prerequisites

- **Tableau Desktop** (any recent version) installed
- Docker running with PostgreSQL on `localhost:5432`
- Data flowing: at least run the producer for a few minutes before building dashboards

---

## Step 1 — Connect Tableau to PostgreSQL

1. Open **Tableau Desktop**
2. Click **Connect → To a Server → PostgreSQL**
3. Enter:

| Field | Value |
|-------|-------|
| Server | `localhost` |
| Port | `5432` |
| Database | `cybersecurity` |
| Username | `postgres` |
| Password | `password` |
| SSL Mode | Disable |

4. Click **Sign In**
5. Under **Table**, drag `network_stream` into the canvas
6. Also drag `attack_events` — join on `network_stream.id = attack_events.stream_id`

---

## Step 2 — Key Calculated Fields

Create these in **Analysis → Create Calculated Field**:

### `Is Attack`
```
[Attack Category] != "Normal"
```

### `Severity Color`
```
IF [Severity] = "HIGH" THEN "RED"
ELSEIF [Severity] = "MEDIUM" THEN "ORANGE"
ELSE "GREEN"
END
```

### `Traffic Volume (MB)`
```
([Src Bytes] + [Dst Bytes]) / 1000000.0
```

### `Attack Rate %`
```
SUM(IF [Is Attack] THEN 1 ELSE 0 END) / COUNT([Id]) * 100
```

---

## Dashboard 1 — Attack Overview

**Sheets to create:**

### Sheet 1A — KPI Summary
- Drag `CNTD(Id)` → Text
- Create 4 text tiles:
  - Total Events: `COUNT([Id])`
  - Total Attacks: `SUM(IF [Is Attack] THEN 1 ELSE 0 END)`
  - Attack Rate: `[Attack Rate %]`
  - Normal Traffic: `SUM(IF NOT [Is Attack] THEN 1 ELSE 0 END)`

### Sheet 1B — Attack Distribution (Bar Chart)
- Rows: `Attack Category`
- Columns: `COUNT([Id])`
- Colour: Attack Category
- Filter: Exclude "Normal"

### Sheet 1C — Normal vs Malicious (Pie Chart)
- Angle: `COUNT([Id])`
- Colour: `Is Attack`
- Label: Show percentages

### Sheet 1D — Attack Timeline (Line Chart)
- Columns: `Event Time` (truncated to Minute/Hour)
- Rows: `COUNT([Id])`
- Colour: `Attack Category`
- Filter: Last 1 hour

---

## Dashboard 2 — Network Analysis

### Sheet 2A — Protocol Distribution (Bar/Pie)
- Dimension: `Protocol Type`
- Measure: `COUNT([Id])`

### Sheet 2B — Top Services (Treemap)
- Dimension: `Service`
- Size: `COUNT([Id])`
- Colour: `Attack Category` (filtered to attacks only)

### Sheet 2C — Traffic Volume Over Time
- Columns: `Event Time` (by Minute)
- Rows: `SUM([Traffic Volume (MB)])`
- Colour: `Attack Category`

### Sheet 2D — Flag Distribution (Bar)
- Dimension: `Flag`
- Measure: `COUNT([Id])`
- Colour: flag type

---

## Dashboard 3 — Attack Deep Dive

### Sheet 3A — Attack vs Bytes Scatter
- Columns: `AVG([Src Bytes])`
- Rows: `AVG([Dst Bytes])`
- Colour: `Attack Category`
- Size: `COUNT([Id])`

### Sheet 3B — Attack by Service (Heatmap)
- Columns: `Service` (top 10)
- Rows: `Attack Category`
- Colour: `COUNT([Id])`

### Sheet 3C — ML Confidence Distribution (Histogram)
- Continuous bin: `Rf Confidence`
- Colour: `Attack Category`

### Sheet 3D — Anomaly Score Distribution
- Continuous bin: `Anomaly Score`
- Colour: `Is Anomaly`

---

## Dashboard 4 — Live Alerts

### Sheet 4A — Alert Feed (Text Table)
- Rows: `Event Time`, `Attack Category`, `Service`, `Severity`, `Rf Confidence`
- Filter: `Severity IN (HIGH, MEDIUM)`
- Sort: `Event Time` descending
- Enable: **Auto-refresh every 30 seconds** (Data → Auto Update)

### Sheet 4B — Severity Breakdown
- Dimension: `Severity`
- Colour: RED for HIGH, ORANGE for MEDIUM, GREEN for LOW

---

## Enabling Auto-Refresh (Live Data)

1. Right-click on `network_stream` data source
2. Select **Data → Auto Update**
3. Set refresh interval to **30 seconds** or **1 minute**

This makes Tableau dashboards show near-real-time data from PostgreSQL.

---

## Publishing to Tableau Public (Optional)

1. **File → Save to Tableau Public As...**
2. Sign in to your Tableau Public account
3. Share the URL in your project report

---

## Screenshots for Your Report

Recommended screenshots:
1. Overall system architecture slide
2. Dashboard 1 (Attack Overview) — showing attack distribution and timeline
3. Dashboard 2 (Network) — protocol and service analysis
4. Dashboard 3 (Deep Dive) — scatter plot / heatmap
5. Dashboard 4 (Alerts) — live alert feed

Add these to your PPT under "Analytics Layer" section.
