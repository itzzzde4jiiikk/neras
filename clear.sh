#!/usr/bin/env bash

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$DIR/.venv/bin/python3"
[ ! -f "$PYTHON" ] && PYTHON="python3"
SOCK="${XDG_RUNTIME_DIR:-/tmp}/neras_chat.sock"

if [ -S "$SOCK" ]; then
    "$PYTHON" "$DIR/ipc.py" clear
fi
