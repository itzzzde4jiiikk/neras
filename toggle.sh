#!/usr/bin/env bash

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$DIR/.venv/bin/python3"
SOCK="${XDG_RUNTIME_DIR:-/tmp}/neras_chat.sock"
LOG="$DIR/overlay.log"

# Check if daemon is already responding
if [ -S "$SOCK" ]; then
    if "$PYTHON" "$DIR/ipc.py" toggle >/dev/null 2>&1; then
        exit 0
    else
        # Stale socket from dead process
        rm -f "$SOCK"
    fi
fi

# Launch daemon in background with setsid and disown
echo "Starting Nera Discord Stream Chat overlay..."
setsid nohup env PYTHONUNBUFFERED=1 "$PYTHON" "$DIR/main.py" >> "$LOG" 2>&1 & disown

# Wait for socket to become ready, then show
for i in {1..25}; do
    if [ -S "$SOCK" ]; then
        sleep 0.1
        "$PYTHON" "$DIR/ipc.py" show >/dev/null 2>&1
        exit 0
    fi
    sleep 0.1
done
