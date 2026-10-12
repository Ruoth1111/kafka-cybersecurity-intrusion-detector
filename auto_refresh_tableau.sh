#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# Tableau Desktop Auto-Refresh Script (5-Second Interval)
# ─────────────────────────────────────────────────────────────

INTERVAL=${1:-5}

echo "=================================================="
echo "🔄 Tableau Desktop Live Auto-Refresher"
echo "   Interval: Every $INTERVAL seconds"
echo "   Press Ctrl+C to stop"
echo "=================================================="

while true; do
    # Trigger refresh in Tableau Desktop on Mac (Cmd+R / F5 signal)
    osascript -e '
        if application "Tableau" is running then
            tell application "System Events"
                tell process "Tableau"
                    keystroke "r" using command down
                end tell
            end tell
        end if
    ' 2>/dev/null || true
    sleep "$INTERVAL"
done
