#!/usr/bin/env bash
# Install ~/Applications/AI Movie Maker Pro.app — native desktop app (no browser)
set -euo pipefail

APP_NAME="AI Movie Maker Pro"
BUNDLE_ID="com.raaj.aimoviemaker"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
INSTALL_DIR="${AIMM_INSTALL_DIR:-$PROJECT_DIR}"
APPLICATIONS_APP="$HOME/Applications/${APP_NAME}.app"

echo "============================================"
echo "  Install ${APP_NAME} (Native Desktop App)"
echo "============================================"
echo ""

if [[ "$(uname)" != "Darwin" ]]; then
  echo "This installer is for macOS only."
  exit 1
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "⚠️  ffmpeg not found (required for video export)."
  if command -v brew >/dev/null 2>&1; then
    echo "Installing ffmpeg..."
    brew install ffmpeg
  else
    echo "Install ffmpeg: brew install ffmpeg"
    exit 1
  fi
fi

cd "$INSTALL_DIR"

echo "🐍 Setting up Python environment..."
bash "$INSTALL_DIR/scripts/setup_venv.sh"

echo "📦 Project folder: $INSTALL_DIR"

echo "🎨 Building app icon..."
bash "$INSTALL_DIR/scripts/build_app_icon.sh"
ICON_SRC="$INSTALL_DIR/assets/AppIcon.icns"
if [[ ! -f "$ICON_SRC" ]]; then
  echo "⚠️  App icon not built; app will use default icon."
fi

MACOS_DIR="$APPLICATIONS_APP/Contents/MacOS"
RES_DIR="$APPLICATIONS_APP/Contents/Resources"
mkdir -p "$MACOS_DIR" "$RES_DIR"

printf '%s' "$INSTALL_DIR" > "$RES_DIR/install_dir"

cat > "$APPLICATIONS_APP/Contents/Info.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key>
  <string>en</string>
  <key>CFBundleExecutable</key>
  <string>launch</string>
  <key>CFBundleIdentifier</key>
  <string>${BUNDLE_ID}</string>
  <key>CFBundleInfoDictionaryVersion</key>
  <string>6.0</string>
  <key>CFBundleName</key>
  <string>${APP_NAME}</string>
  <key>CFBundleDisplayName</key>
  <string>${APP_NAME}</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>2.4.0</string>
  <key>CFBundleVersion</key>
  <string>2.4.0</string>
  <key>CFBundleIconFile</key>
  <string>AppIcon</string>
  <key>LSMinimumSystemVersion</key>
  <string>11.0</string>
  <key>NSHighResolutionCapable</key>
  <true/>
</dict>
</plist>
PLIST

cat > "$MACOS_DIR/launch" << 'LAUNCHER'
#!/bin/bash
APP_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
INSTALL_DIR="$(cat "$APP_DIR/Contents/Resources/install_dir" 2>/dev/null || echo "$HOME/AIMovieMakerPro")"
LOG="$HOME/Library/Logs/AIMovieMakerPro.log"

alert() {
  osascript -e "display alert \"AI Movie Maker Pro\" message \"$1\"" 2>/dev/null || true
}

if [[ ! -d "$INSTALL_DIR" ]]; then
  alert "App files not found at: $INSTALL_DIR"
  exit 1
fi

if [[ ! -f "$INSTALL_DIR/desktop_app.py" ]]; then
  alert "desktop_app.py missing in: $INSTALL_DIR"
  exit 1
fi

if [[ ! -x "$INSTALL_DIR/venv/bin/python" ]]; then
  alert "Run Install Mac App.command once from the project folder to set up."
  exit 1
fi

cd "$INSTALL_DIR"
PY="$INSTALL_DIR/venv/bin/python"

# Native window app — no browser, runs in foreground
if [[ "$(uname -m)" == "arm64" ]]; then
  exec arch -arm64 "$PY" desktop_app.py >> "$LOG" 2>&1
else
  exec "$PY" desktop_app.py >> "$LOG" 2>&1
fi
LAUNCHER

chmod +x "$MACOS_DIR/launch"

if [[ -f "$ICON_SRC" ]]; then
  cp "$ICON_SRC" "$RES_DIR/AppIcon.icns"
  # Refresh Finder / Dock icon cache for this app
  touch "$APPLICATIONS_APP"
fi

echo ""
echo "✅ Installed: $APPLICATIONS_APP"
echo ""
echo "Opens the native desktop app (no browser)."
echo ""
echo "Launch from:"
echo "  • Spotlight (Cmd+Space) → AI Movie Maker"
echo "  • Finder → Applications → AI Movie Maker Pro"
echo "  • Dock — right-click → Keep in Dock"
echo ""

read -r -p "Open the app now? [Y/n] " OPEN_NOW
OPEN_NOW="${OPEN_NOW:-Y}"
if [[ "$OPEN_NOW" =~ ^[Yy] ]]; then
  open "$APPLICATIONS_APP"
fi
