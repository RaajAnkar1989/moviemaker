#!/usr/bin/env bash
# Pick native Python and create a consistent venv (fixes arm64/x86_64 numpy errors on Mac).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

pick_python() {
  if [[ "$(uname -m)" == "arm64" ]]; then
    for candidate in /opt/homebrew/bin/python3 /usr/bin/python3; do
      if [[ -x "$candidate" ]] && arch -arm64 "$candidate" -c "import sys" >/dev/null 2>&1; then
        echo "$candidate"
        return 0
      fi
    done
  fi
  command -v python3
}

PYTHON="$(pick_python)"
echo "Using Python: $PYTHON"
"$PYTHON" -c "import platform, sys; print('  version:', sys.version.split()[0]); print('  arch:', platform.machine())"

if [[ -d venv ]]; then
  echo "Removing old venv..."
  rm -rf venv
fi

echo "Creating venv..."
if [[ "$(uname -m)" == "arm64" ]]; then
  arch -arm64 "$PYTHON" -m venv venv
  PIP="arch -arm64 venv/bin/python -m pip"
else
  "$PYTHON" -m venv venv
  PIP="venv/bin/python -m pip"
fi

$PIP install -U pip wheel
$PIP install -r requirements.txt
if [[ -f requirements-desktop.txt ]]; then
  $PIP install -r requirements-desktop.txt
fi

echo "Verifying numpy..."
if [[ "$(uname -m)" == "arm64" ]]; then
  arch -arm64 venv/bin/python -c "import numpy; import streamlit; print('OK numpy', numpy.__version__)"
else
  venv/bin/python -c "import numpy; import streamlit; print('OK numpy', numpy.__version__)"
fi

echo "✅ Environment ready."
