#!/bin/bash
cd "$(dirname "$0")"
bash scripts/build_dmg.sh
echo ""
read -r -p "Press Enter to close..."
