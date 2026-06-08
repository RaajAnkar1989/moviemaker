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

if [[ ! -d venv ]]; then
  echo "🐍 Creating Python environment..."
  python3 -m venv venv
fi

# shellcheck disable=SC1091
source venv/bin/activate
python -m pip install -U pip wheel
pip install -r requirements.txt
if [[ -f requirements-desktop.txt ]]; then
  pip install -r requirements-desktop.txt
fi

chmod +x RunWebApp.command MovieMaker.command InstallLocal.command 2>/dev/null || true

DESKTOP=""
if [[ "$(uname)" == "Darwin" ]] && [[ -d "$HOME/Desktop" ]]; then
  DESKTOP="$HOME/Desktop/Start AI Movie Maker.command"
  cat > "$DESKTOP" << LAUNCHER
#!/bin/bash
cd "$INSTALL_DIR"
source venv/bin/activate
exec python -m streamlit run movie_maker_app.py --server.maxUploadSize=1000
LAUNCHER
  chmod +x "$DESKTOP"
  echo "🖥️  Desktop shortcut: $DESKTOP"
fi

echo ""
echo "✅ Install complete!"
echo "   Folder: $INSTALL_DIR"
echo ""
echo "🚀 Starting local app (1080p, full speed)..."
echo "   Browser will open at http://localhost:8501"
echo ""

exec python -m streamlit run movie_maker_app.py --server.maxUploadSize=1000
