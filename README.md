# 🎬 AI Movie Maker Pro

A professional cinematic video generation suite optimized for **Streamlit Cloud**, mobile use, and **macOS Desktop**.

## 🌟 Features

- **Industry Transitions**: 10+ pro transitions including Glitch, Whip Pan, Cross Dissolve, and more.
- **Smart Zoom**: Automatically removes watermarks from video edges.
- **Multi-Page Credits**: Create movie-style titles and end credits with multiple pages and lines.
- **Smart Resume**: If a crash occurs, the app remembers previously rendered clips to save time.
- **Safe Mode**: Adjustable resolution (360p-720p) to manage RAM on cloud servers.
- **Audio Mixing**: Balance background music and original video volume.
- **Cloud Optimized**: Automatic font handling for Linux servers.

## ☁️ Deployment (Streamlit Cloud)

1.  **Push to GitHub**: Ensure `movie_maker_app.py` and `requirements.txt` are in your repo.
2.  **Connect to Streamlit**: Go to [share.streamlit.io](https://share.streamlit.io).
3.  **Deploy**: Select your repo and `movie_maker_app.py` as the main file.

## 🚀 Local Run (Best Performance)

Running locally on your Mac uses your full RAM and CPU, allowing for **1080p resolution** and faster rendering.

### 3. Applications App (Recommended — Spotlight / Dock)
Double-click **`Install Mac App.command`** once. This installs **AI Movie Maker Pro** into your **Applications** folder as a **native desktop app** (no browser).

Launch from **Spotlight** (Cmd+Space → "AI Movie Maker") or **Applications**. A normal macOS window opens — not a browser tab.

### 4. Web Interface (Optional)
Double-click `RunWebApp.command` if you prefer the browser version (Streamlit).

## 🛠️ Setup
If the `.command` files don't open, run this in your terminal:
```bash
cd /Users/raaj/movie-maker-Raaj
pip install -r requirements.txt
chmod +x *.command
```
