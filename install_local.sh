#!/usr/bin/env bash
# AI Movie Maker Pro — local installer (macOS / Linux)
set -euo pipefail

REPO_URL="https://github.com/RaajAnkar1989/moviemaker.git"
INSTALL_DIR="${AIMM_INSTALL_DIR:-$HOME/AIMovieMakerPro}"
APP_NAME="AI Movie Maker Pro"

echo "============================================"
echo "  $APP_NAME — Local Installer"
echo "============================================"
echo ""

if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ Python 3 is required."
  echo "   Install from https://www.python.org/downloads/"
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo "❌ Git is required."
  echo "   macOS: xcode-select --install"
  echo "   Linux: sudo apt install git   (or your package manager)"
  exit 1
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "⚠️  ffmpeg not found (needed for video export)."
  if [[ "$(uname)" == "Darwin" ]] && command -v brew >/dev/null 2>&1; then
    echo "   Installing ffmpeg with Homebrew..."
    brew install ffmpeg
  else
    echo "   Install ffmpeg, then re-run this script."
    echo "   macOS: brew install ffmpeg"
    echo "   Linux: sudo apt install ffmpeg"
    exit 1
  fi
fi

mkdir -p "$(dirname "$INSTALL_DIR")"
if [[ -d "$INSTALL_DIR/.git" ]]; then
  echo "📂 Updating existing install at $INSTALL_DIR"
  git -C "$INSTALL_DIR" pull --ff-only
else
  echo "📥 Downloading app to $INSTALL_DIR"
  git clone "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

bash "$INSTALL_DIR/scripts/setup_venv.sh"

chmod +x RunWebApp.command MovieMaker.command InstallLocal.command "Install Mac App.command" 2>/dev/null || true
chmod +x scripts/install_mac_app.sh 2>/dev/null || true

if [[ "$(uname)" == "Darwin" ]]; then
  echo "🍎 Installing Applications app..."
  AIMM_INSTALL_DIR="$INSTALL_DIR" bash "$INSTALL_DIR/scripts/install_mac_app.sh" <<< "n" || true
fi

DESKTOP=""
if [[ "$(uname)" == "Darwin" ]] && [[ -d "$HOME/Desktop" ]]; then
  DESKTOP="$HOME/Desktop/Start AI Movie Maker.command"
  cat > "$DESKTOP" << LAUNCHER
#!/bin/bash
open "$HOME/Applications/AI Movie Maker Pro.app"
LAUNCHER
  chmod +x "$DESKTOP"
  echo "🖥️  Desktop shortcut: $DESKTOP"
fi

echo ""
echo "✅ Install complete!"
echo "   Folder: $INSTALL_DIR"
echo ""
echo "🚀 Starting local app (native desktop window)..."
echo ""

if [[ "$(uname -m)" == "arm64" ]]; then
  exec arch -arm64 venv/bin/python desktop_app.py
else
  exec venv/bin/python desktop_app.py
fi
