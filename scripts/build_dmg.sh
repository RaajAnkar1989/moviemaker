#!/usr/bin/env bash
# Build a shareable AI Movie Maker Pro.dmg (standalone .app, no Python install needed)
set -euo pipefail

APP_NAME="AI Movie Maker Pro"
BUNDLE_ID="com.raaj.aimoviemaker"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="$PROJECT_DIR/dist"
APP_PATH="$DIST_DIR/${APP_NAME}.app"
DMG_PATH="$DIST_DIR/${APP_NAME}.dmg"

echo "============================================"
echo "  Build ${APP_NAME}.dmg"
echo "============================================"
echo ""

if [[ "$(uname)" != "Darwin" ]]; then
  echo "DMG builds require macOS."
  exit 1
fi

cd "$PROJECT_DIR"

echo "🎨 Building app icon..."
bash "$PROJECT_DIR/scripts/build_app_icon.sh"

if [[ ! -x "$PROJECT_DIR/venv/bin/python" ]]; then
  echo "🐍 Creating Python environment (first time only)..."
  bash "$PROJECT_DIR/scripts/setup_venv.sh"
fi

PY="$PROJECT_DIR/venv/bin/python"
PIP="$PY -m pip"

echo "📦 Installing build tools..."
$PIP install -q -U pip wheel
$PIP install -q pyinstaller
$PIP install -q -r requirements.txt
$PIP install -q -r requirements-desktop.txt

echo "🔨 Building standalone app (this may take a few minutes)..."
rm -rf "$PROJECT_DIR/build" "$DIST_DIR/${APP_NAME}.app" "$DIST_DIR/AIMovieMakerPro"
if [[ "$(uname -m)" == "arm64" ]]; then
  arch -arm64 "$PY" -m PyInstaller "$PROJECT_DIR/AIMovieMakerPro.spec" --noconfirm --clean
else
  "$PY" -m PyInstaller "$PROJECT_DIR/AIMovieMakerPro.spec" --noconfirm --clean
fi

if [[ ! -d "$APP_PATH" ]]; then
  echo "❌ Build failed — ${APP_NAME}.app not found in dist/"
  exit 1
fi

echo "🔏 Ad-hoc signing (helps first launch on other Macs)..."
codesign -s - --force --deep "$APP_PATH" 2>/dev/null || true

echo "💿 Creating DMG..."
STAGE="$(mktemp -d)"
cleanup() { rm -rf "$STAGE"; }
trap cleanup EXIT

cp -R "$APP_PATH" "$STAGE/"
ln -s /Applications "$STAGE/Applications"

cat > "$STAGE/README.txt" << 'README'
AI Movie Maker Pro — Install Instructions
=========================================

1. Drag "AI Movie Maker Pro.app" into the Applications folder.
2. Open Applications and launch AI Movie Maker Pro.

First launch on a new Mac:
  • If macOS blocks the app, right-click the app → Open → Open again.
  • Or: System Settings → Privacy & Security → allow the app.

Requirements:
  • macOS 11 or later (Apple Silicon or Intel)
  • No Python or ffmpeg install needed — everything is bundled.

Share this .dmg via AirDrop, Google Drive, email, etc.
README

rm -f "$DMG_PATH"
hdiutil create \
  -volname "$APP_NAME" \
  -srcfolder "$STAGE" \
  -ov \
  -format UDZO \
  "$DMG_PATH" >/dev/null

SIZE="$(du -h "$DMG_PATH" | awk '{print $1}')"
echo ""
echo "✅ Done!"
echo "   App:  $APP_PATH"
echo "   DMG:  $DMG_PATH  ($SIZE)"
echo ""
echo "Share the .dmg file — recipients drag the app to Applications."
echo ""
