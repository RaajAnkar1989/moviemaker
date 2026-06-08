#!/bin/bash
cd "$(dirname "$0")"
if [ -d venv ]; then
  PY="./venv/bin/python"
else
  PY="python3"
fi
if [[ "$(uname -m)" == "arm64" ]]; then
  exec arch -arm64 "$PY" desktop_app.py
else
  exec "$PY" desktop_app.py
fi
