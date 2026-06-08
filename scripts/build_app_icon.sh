#!/usr/bin/env bash
# Build AppIcon.icns from assets/app_icon.png (macOS)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC="$PROJECT_DIR/assets/app_icon.png"
ICONSET="$PROJECT_DIR/assets/AppIcon.iconset"
OUT="$PROJECT_DIR/assets/AppIcon.icns"

if [[ "$(uname)" != "Darwin" ]]; then
  echo "App icon build requires macOS (iconutil)."
  exit 1
fi

if [[ ! -f "$SRC" ]]; then
  echo "Missing source icon: $SRC"
  exit 1
fi

rm -rf "$ICONSET"
mkdir -p "$ICONSET"

SQUARE="$PROJECT_DIR/assets/.app_icon_square.png"
sips -z 1024 1024 "$SRC" --padToHeightWidth 1024 1024 --out "$SQUARE" >/dev/null

# Required sizes for macOS iconset
declare -a SIZES=(16 32 128 256 512)
for size in "${SIZES[@]}"; do
  sips -z "$size" "$size" "$SQUARE" --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
  double=$((size * 2))
  sips -z "$double" "$double" "$SQUARE" --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
done

iconutil -c icns "$ICONSET" -o "$OUT"
rm -rf "$ICONSET" "$SQUARE"
echo "Built $OUT"
