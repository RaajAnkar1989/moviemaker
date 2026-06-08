#!/bin/bash
cd "$(dirname "$0")"
echo "🚀 Starting AI Movie Maker Pro (Local Mode)..."
echo "----------------------------------------------"
echo "Check the sidebar for the Mobile Access link!"
if [ -d venv ]; then
  source venv/bin/activate
fi
if [[ "$(uname -m)" == "arm64" ]]; then
  exec arch -arm64 python3 -m streamlit run movie_maker_app.py --server.maxUploadSize=1000
else
  exec python3 -m streamlit run movie_maker_app.py --server.maxUploadSize=1000
fi
