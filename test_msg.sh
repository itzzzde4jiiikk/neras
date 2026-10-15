#!/usr/bin/env bash

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$DIR/.venv/bin/python3"
MSG="${1:-Привет! Как твои дела? Стрим идёт отлично ✨}"

"$PYTHON" "$DIR/ipc.py" test "$MSG"
