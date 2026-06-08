@echo off
setlocal EnableExtensions
title AI Movie Maker Pro - Local Installer

set "REPO=https://github.com/RaajAnkar1989/moviemaker.git"
set "INSTALL_DIR=%USERPROFILE%\AIMovieMakerPro"

echo ============================================
echo   AI Movie Maker Pro - Local Installer
echo ============================================
echo.

where python >nul 2>nul || (
  echo Python not found. Install from https://www.python.org/downloads/
  echo Check "Add Python to PATH" during install.
  pause
  exit /b 1
)

where git >nul 2>nul || (
  echo Git not found. Install from https://git-scm.com/download/win
  pause
  exit /b 1
)

where ffmpeg >nul 2>nul || (
  echo ffmpeg not found. Install with: winget install ffmpeg
  echo Or download from https://ffmpeg.org/download.html
  pause
  exit /b 1
)

if exist "%INSTALL_DIR%\.git" (
  echo Updating existing install...
  git -C "%INSTALL_DIR%" pull --ff-only
) else (
  echo Downloading app to %INSTALL_DIR%...
  git clone "%REPO%" "%INSTALL_DIR%"
)

cd /d "%INSTALL_DIR%"

if not exist venv (
  echo Creating Python environment...
  python -m venv venv
)

call venv\Scripts\activate.bat
python -m pip install -U pip wheel
pip install -r requirements.txt

echo.
echo Install complete!
echo Starting local app at http://localhost:8501
echo.

python -m streamlit run movie_maker_app.py --server.maxUploadSize=1000
pause
