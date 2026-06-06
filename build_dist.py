import os
import subprocess
import sys

def create_bundle():
    print("📦 AI Movie Maker Pro - Distribution Bundler")
    print("------------------------------------------")
    
    # 1. Install PyInstaller if missing
    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # 2. Package the Desktop App (Tkinter version)
    # This is the easiest for users to run as a single file.
    print("\n🔨 Building Desktop Standalone App...")
    subprocess.check_call([
        "pyinstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", "AIMovieMakerPro",
        "--add-data", "requirements.txt:.",
        "desktop_app.py"
    ])

    print("\n✅ DONE!")
    print("Your 'AIMovieMakerPro' app is now in the 'dist' folder.")
    print("You can send this file to anyone on macOS, and it will run using THEIR RAM/CPU.")

if __name__ == "__main__":
    create_bundle()
