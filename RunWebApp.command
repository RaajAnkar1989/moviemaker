#!/bin/bash
cd "$(dirname "$0")"
echo "🚀 Starting AI Movie Maker Pro (Web App)..."
echo "To use on mobile, connect to the same WiFi and use the IP in the sidebar."
python3 -m streamlit run movie_maker_app.py
