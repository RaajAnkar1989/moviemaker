#!/bin/bash
cd "$(dirname "$0")"
echo "🚀 Starting AI Movie Maker Pro (Local Mode)..."
echo "----------------------------------------------"
echo "Check the sidebar for the Mobile Access link!"
python3 -m streamlit run movie_maker_app.py --server.maxUploadSize=1000
