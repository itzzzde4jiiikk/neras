#!/usr/bin/env bash

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIDFILE="${XDG_RUNTIME_DIR:-/tmp}/neras_chat.pid"
SOCK="${XDG_RUNTIME_DIR:-/tmp}/neras_chat.sock"

if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        kill "$PID" 2>/dev/null
        echo "Killed process $PID"
    fi
    rm -f "$PIDFILE"
fi

# Fallback kill
pkill -f "nera's chat.*main.py" 2>/dev/null || true
pkill -f "\.venv/bin/python3 main\.py" 2>/dev/null || true
rm -f "$SOCK"

echo "Nera Discord Stream Chat overlay stopped."
