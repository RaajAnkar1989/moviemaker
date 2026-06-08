#!/bin/bash
# Double-click this file on macOS to install and run AI Movie Maker Pro locally.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"

if [[ -f "$DIR/install_local.sh" ]]; then
  bash "$DIR/install_local.sh"
else
  # Downloaded standalone — fetch installer from GitHub
  TMP="$(mktemp)"
  curl -fsSL "https://raw.githubusercontent.com/RaajAnkar1989/moviemaker/main/install_local.sh" -o "$TMP"
  bash "$TMP"
fi
