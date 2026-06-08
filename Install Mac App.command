#!/bin/bash
# Double-click to install AI Movie Maker Pro into your Applications folder.
cd "$(dirname "$0")"
export AIMM_INSTALL_DIR="$(pwd)"
bash scripts/install_mac_app.sh
