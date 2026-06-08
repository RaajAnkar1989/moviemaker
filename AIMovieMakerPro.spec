# PyInstaller spec — standalone macOS app for DMG distribution
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

project_dir = Path(SPECPATH)
icon_path = project_dir / "assets" / "AppIcon.icns"

datas = [
    (str(project_dir / "assets" / "app_icon.png"), "assets"),
    (str(project_dir / "assets" / "AppIcon.icns"), "assets"),
]

binaries = []
hiddenimports = [
    "PIL._tkinter_finder",
]

for package in ("customtkinter", "moviepy", "imageio", "imageio_ffmpeg", "proglog"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

try:
    import imageio_ffmpeg

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    if ffmpeg_exe and Path(ffmpeg_exe).is_file():
        binaries.append((ffmpeg_exe, "."))
except Exception:
    pass

a = Analysis(
    ["desktop_app.py"],
    pathex=[str(project_dir)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["streamlit", "matplotlib", "scipy", "pandas", "pytest"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AIMovieMakerPro",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="AIMovieMakerPro",
)

app = BUNDLE(
    coll,
    name="AI Movie Maker Pro.app",
    icon=str(icon_path) if icon_path.is_file() else None,
    bundle_identifier="com.raaj.aimoviemaker",
    info_plist={
        "CFBundleDisplayName": "AI Movie Maker Pro",
        "CFBundleShortVersionString": "2.4.0",
        "CFBundleVersion": "2.4.0",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
    },
)
