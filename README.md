# 🎬 AI Movie Maker Pro

A professional cinematic video generation suite optimized for **Streamlit Cloud**, mobile use, and **macOS Desktop**.

## 🌟 Features

- **Industry Transitions**: 10+ pro transitions including Glitch, Whip Pan, Cross Dissolve, and more.
- **Smart Zoom**: Automatically removes watermarks from video edges.
- **Multi-Page Credits**: Create movie-style titles and end credits with multiple pages and lines.
- **Audio Mixing**: Balance background music and original video volume.
- **Cloud Optimized**: Automatic font handling for Linux servers.

## ☁️ Deployment (Streamlit Cloud)

1.  **Push to GitHub**: Ensure `movie_maker_app.py` and `requirements.txt` are in your repo.
2.  **Connect to Streamlit**: Go to [share.streamlit.io](https://share.streamlit.io).
3.  **Deploy**: Select your repo and `movie_maker_app.py` as the main file.
4.  **Font Fix**: This version automatically handles font issues on Linux by using the system default if "Arial" is missing.

## 🚀 Local Run (Desktop App)
1. Double-click `MovieMaker.command` on macOS.
2. Or run via terminal:
   ```bash
   pip install -r requirements.txt
   python3 desktop_app.py
   ```

## 📱 Mobile/Web Run
```bash
streamlit run movie_maker_app.py
```
