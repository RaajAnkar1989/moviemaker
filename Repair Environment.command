#!/bin/bash
# Fix numpy / architecture errors — rebuilds the Python environment.
cd "$(dirname "$0")"
bash scripts/setup_venv.sh
echo ""
echo "Re-installing Applications app launcher..."
export AIMM_INSTALL_DIR="$(pwd)"
bash scripts/install_mac_app.sh <<< "n"
echo ""
echo "Done. Open 'AI Movie Maker Pro' from Applications again."
