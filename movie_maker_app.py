import streamlit as st
import os
import tempfile
import time
import gc
import shutil
import math
from moviepy import VideoFileClip, TextClip, CompositeVideoClip, concatenate_videoclips, ColorClip, AudioFileClip, CompositeAudioClip, concatenate_audioclips
from video_utils import (
    apply_transition,
    build_media_clip,
    estimate_movie_duration,
    even,
    get_runtime_profile,
    get_write_kwargs,
    is_streamlit_cloud_env,
    make_silence,
    preprocess_upload,
    probe_video_duration,
    RenderProgressLogger,
)

import socket
import qrcode
from io import BytesIO

# --- EXTREME STABILITY & PERFORMANCE CONFIG ---
PROFILE = get_runtime_profile()
IS_LOCAL = PROFILE["name"] == "local"
MAX_UPLOAD_MB = PROFILE["max_upload_mb"]
TEMP_ROOT = tempfile.gettempdir()


def resolve_is_local():
    """Only true on localhost / LAN — never on streamlit.app."""
    if is_streamlit_cloud_env():
        return False
    try:
        url = str(getattr(st.context, "url", "") or "").lower()
        host = ""
        if getattr(st.context, "headers", None):
            host = str(st.context.headers.get("Host", "")).lower()
        combined = f"{url} {host}"
        if "streamlit.app" in combined or "share.streamlit.io" in combined:
            return False
        if "localhost" in url or "127.0.0.1" in url:
            return True
        import re
        if re.search(r"https?://(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.)", url):
            return True
    except Exception:
        pass
    return False


def refresh_deployment_settings():
    global IS_LOCAL, PROFILE, MAX_UPLOAD_MB, LOCAL_IP
    IS_LOCAL = resolve_is_local()
    PROFILE = get_runtime_profile(force_cloud=not IS_LOCAL)
    MAX_UPLOAD_MB = PROFILE["max_upload_mb"]
    LOCAL_IP = get_local_ip() if IS_LOCAL else "127.0.0.1"

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except: return "127.0.0.1"

LOCAL_IP = "127.0.0.1"

# Page Setup
st.set_page_config(page_title="AI Movie Maker Pro", page_icon="🎬", layout="wide")

# UI Styling
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    [data-testid="stSidebarNav"] {display: none;}
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FF4B4B; color: white; font-weight: bold; }
    .stButton>button:hover { background-color: #FF3333; border-color: white; }
    .video-info { background-color: #262730; padding: 10px; border-radius: 5px; border: 1px solid #444; margin-bottom: 5px; }
    .upload-stats { font-size: 0.8rem; color: #888; margin-top: -10px; margin-bottom: 10px; }
    .error-box { background-color: #3e1a1a; padding: 15px; border-radius: 8px; border-left: 5px solid #ff4b4b; margin-bottom: 20px; }
    .success-box { background-color: #1a3e1a; padding: 15px; border-radius: 8px; border-left: 5px solid #4bff4b; margin-bottom: 20px; }
    @media (max-width: 768px) {
        .stTabs [data-baseweb="tab-list"] { gap: 0px; }
        .stTabs [data-baseweb="tab"] { padding: 10px 5px; font-size: 0.8rem; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- RECOVERY & STATE MANAGEMENT ---
def init_state():
    if 'app_id' not in st.session_state:
        st.session_state.app_id = str(int(time.time()))
        st.session_state.temp_dir = tempfile.mkdtemp(prefix=f"mpy_{st.session_state.app_id}_")
    if 'video_sequence' not in st.session_state: st.session_state.video_sequence = []
    if 'processed_uploads' not in st.session_state: st.session_state.processed_uploads = set()
    if 'title_pages' not in st.session_state: st.session_state.title_pages = [{"text": "THE CINEMATIC JOURNEY", "color": "White", "size": 50}]
    if 'end_pages' not in st.session_state: st.session_state.end_pages = [{"text": "THE END", "color": "White", "size": 50}]
    if 'gen_error' not in st.session_state: st.session_state.gen_error = None
    if 'last_config' not in st.session_state: st.session_state.last_config = {}
    if 'processed_clips' not in st.session_state: st.session_state.processed_clips = {}
    if 'last_output' not in st.session_state: st.session_state.last_output = None

init_state()

def reset_app():
    if os.path.exists(st.session_state.temp_dir):
        shutil.rmtree(st.session_state.temp_dir, ignore_errors=True)
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

def clear_cache():
    st.session_state.processed_clips = {}
    for f in os.listdir(st.session_state.temp_dir):
        if f.endswith(".mp4") and (f.startswith("t_") or f.startswith("v_") or f.startswith("e_")):
            try: os.remove(os.path.join(st.session_state.temp_dir, f))
            except: pass
    st.toast("Render cache cleared!")

# --- CORE UTILITIES ---
def create_text_clip(text, duration=4, color_rgb=(0,0,0), font_size=50, text_color='white', res_h=480, target_ratio=16/9):
    res_h = even(res_h)
    target_size = (even(int(res_h * target_ratio)), res_h)
    bg = ColorClip(size=target_size, color=color_rgb).with_duration(duration)
    try:
        txt = TextClip(text=text, font_size=font_size, color=text_color.lower(), size=target_size, method='caption').with_duration(duration).with_position('center')
    except:
        txt = TextClip(text=text, font_size=font_size, color='white', size=target_size, method='caption').with_duration(duration).with_position('center')
    return CompositeVideoClip([bg, txt]).with_audio(make_silence(duration))

INSTALL_REPO = "https://github.com/RaajAnkar1989/moviemaker.git"
INSTALL_ONE_LINER_MAC = 'curl -fsSL https://raw.githubusercontent.com/RaajAnkar1989/moviemaker/main/install_local.sh | bash'
INSTALL_ONE_LINER_WIN = 'git clone https://github.com/RaajAnkar1989/moviemaker.git %USERPROFILE%\\AIMovieMakerPro && cd %USERPROFILE%\\AIMovieMakerPro && install_local.bat'


def _read_install_file(name):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), name)
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    return ""


def render_local_install_section(compact=False):
    if not compact:
        st.header("💾 Install Locally")

    if IS_LOCAL:
        st.info(
            "You're on a **local** copy (localhost/LAN). "
            "Download below to install on another computer."
        )
    else:
        st.markdown(
            "You're on the **free cloud site** (slow, 360p). "
            "Install on **your Mac/PC** for **1080p** and much faster renders (~2 min setup)."
        )

    mac_sh = _read_install_file("install_local.sh")
    mac_cmd = _read_install_file("InstallLocal.command")
    win_bat = _read_install_file("install_local.bat")

    st.markdown("#### ⬇️ Download & run")
    col1, col2, col3 = st.columns(3)
    with col1:
        if mac_cmd:
            st.download_button(
                "🍎 Mac (double-click)",
                mac_cmd,
                file_name="InstallLocal.command",
                mime="application/x-sh",
                key="dl_mac_cmd_main" if compact else "dl_mac_cmd",
                use_container_width=True,
            )
    with col2:
        if mac_sh:
            st.download_button(
                "🐧 Mac/Linux script",
                mac_sh,
                file_name="install_local.sh",
                mime="application/x-sh",
                key="dl_mac_sh_main" if compact else "dl_mac_sh",
                use_container_width=True,
            )
    with col3:
        if win_bat:
            st.download_button(
                "🪟 Windows",
                win_bat,
                file_name="install_local.bat",
                mime="application/octet-stream",
                key="dl_win_bat_main" if compact else "dl_win_bat",
                use_container_width=True,
            )

    st.markdown("**Or paste in Terminal (Mac/Linux):**")
    st.code(INSTALL_ONE_LINER_MAC, language="bash")
    st.caption(f"Installs to `~/AIMovieMakerPro` · Requires Python 3, Git, ffmpeg")
    st.caption("Mac: if blocked, right-click the downloaded file → **Open** the first time.")

    with st.expander("📋 What gets installed"):
        st.markdown(
            """
            1. Clones the app to `~/AIMovieMakerPro` (Mac/Linux) or `%USERPROFILE%\\AIMovieMakerPro` (Windows)
            2. Creates a Python virtual environment
            3. Installs dependencies (Streamlit, MoviePy, ffmpeg tools)
            4. Adds a **Desktop shortcut** (Mac)
            5. Opens the app at **http://localhost:8501**

            **Requirements:** Python 3, Git, ffmpeg
            """
        )

# --- MAIN APP ---
def main():
    refresh_deployment_settings()
    st.title("🎬 AI Movie Maker Pro")

    if not IS_LOCAL:
        st.warning(
            "☁️ **Cloud site** — limited speed & 360p. "
            "Tap the **💾 Install App** tab to download the local installer (1080p, full speed)."
        )
    else:
        st.success("💻 **Running locally** — full 1080p speed enabled.")
    
    if st.session_state.gen_error:
        with st.container():
            st.markdown(f"""<div class='error-box'><b>⚠️ System Recovery:</b> The last generation attempt failed. 
            Your files and edits are still saved below. You can try again with fewer clips or lower settings.<br><br>
            <i>Error Detail: {st.session_state.gen_error}</i></div>""", unsafe_allow_html=True)
            if st.button("🔄 Full Reset (Start Fresh)"): reset_app()
            st.divider()

    total_size_mb = sum([v['size'] for v in st.session_state.video_sequence]) / (1024 * 1024)
    remaining_mb = MAX_UPLOAD_MB - total_size_mb

    with st.sidebar:
        st.markdown("### 💾 Install Locally")
        mac_cmd = _read_install_file("InstallLocal.command")
        if mac_cmd:
            st.download_button(
                "⬇️ Download Mac Installer",
                mac_cmd,
                file_name="InstallLocal.command",
                mime="application/x-sh",
                key="dl_mac_sidebar",
                use_container_width=True,
            )
        if not IS_LOCAL:
            st.caption("Cloud site — install for 1080p speed")
        else:
            st.caption("Share installer with friends")
        st.caption("Full options in **Install App** tab →")
        st.divider()

        if IS_LOCAL:
            mobile_url = f"http://{LOCAL_IP}:8501"
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(mobile_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            buf = BytesIO()
            img.save(buf, format="PNG")
            st.image(buf.getvalue(), caption="Scan to open on phone", width=200)
            st.code(mobile_url)
            st.divider()

        st.header("🎨 Card Style")
        bg_colors = {"Black": (0, 0, 0), "Dark Blue": (0, 0, 50), "Dark Red": (50, 0, 0), "Deep Purple": (48, 25, 52), "White": (255, 255, 255)}
        color_choice = st.selectbox("Background Color", list(bg_colors.keys()))
        
        st.divider()
        st.header("🎞️ Cinematic")
        aspect_options = {"16:9 (Widescreen)": 16/9, "9:16 (Vertical)": 9/16, "1:1 (Square)": 1.0, "4:3 (Standard)": 4/3}
        aspect_choice = st.selectbox("Aspect Ratio", list(aspect_options.keys()), index=0)
        target_ratio = aspect_options[aspect_choice]

        do_watermark = st.checkbox("Remove Watermarks (Smart Zoom)", value=PROFILE["default_watermark"])
        transition_style = st.selectbox(
            "Transition Style",
            ["Hard Cut", "Cross Dissolve", "Fade In/Out", "Whip Pan", "Zoom In/Out", "Glitch", "White Flash", "Random"],
            index=PROFILE["default_transition_index"],
        )
        res_h = st.select_slider("Resolution (Height)", options=PROFILE["res_options"], value=PROFILE["default_res"])
        
        st.header("💎 Quality & Size")
        quality_map = {"Small (Low Bitrate)": "1500k", "Standard (Medium)": "3000k", "Cinematic (High)": "6000k", "Pro (Ultra)": "12000k"}
        quality_choice = st.select_slider(
            "Export Quality",
            options=PROFILE["quality_options"],
            value=PROFILE["default_quality"],
        )
        target_bitrate = quality_map[quality_choice]
        
        st.divider()
        st.header("🔊 Audio")
        video_vol = st.slider("Original Volume", 0.0, 2.0, 1.0)
        bg_vol = st.slider("Music Volume", 0.0, 2.0, 0.5)
        st.divider()
        if st.button("🗑️ Clear Render Cache"): clear_cache()
        if st.button("🔄 Full Reset"): reset_app()

    tab1, tab2, tab3, tab4 = st.tabs(["📁 Files & Order", "📝 Titles & Credits", "🚀 Production", "💾 Install App"])

    with tab4:
        render_local_install_section(compact=True)

    with tab1:
        st.markdown(f"<div class='upload-stats'>Storage Used: {total_size_mb:.1f}MB / {MAX_UPLOAD_MB}MB</div>", unsafe_allow_html=True)
        uploaded_videos = st.file_uploader(
            "Upload Clips & Photos", type=["mp4", "mov", "jpg", "jpeg", "png", "webp"], accept_multiple_files=True
        )
        
        if uploaded_videos:
            new_files_added = False
            running_mb = total_size_mb
            for f in uploaded_videos:
                file_id = f"{f.name}_{f.size}"
                if file_id not in st.session_state.processed_uploads:
                    if running_mb + f.size / (1024 * 1024) > MAX_UPLOAD_MB:
                        st.error(f"Upload limit reached ({MAX_UPLOAD_MB}MB). Remove clips or run locally.")
                        continue
                    if len(st.session_state.video_sequence) >= PROFILE["max_clips"]:
                        st.error(f"Clip limit reached ({PROFILE['max_clips']} max on cloud).")
                        continue
                    t_path = os.path.join(st.session_state.temp_dir, f.name)
                    with open(t_path, "wb") as tmp:
                        tmp.write(f.getbuffer())
                    is_img = f.name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
                    with st.spinner(f"Optimizing {f.name}..." if PROFILE["preprocess_uploads"] else f"Saving {f.name}..."):
                        t_path, new_size = preprocess_upload(t_path, is_img, res_h)
                    native_duration = None if is_img else probe_video_duration(t_path)
                    st.session_state.video_sequence.append({
                        "name": f.name, "path": t_path, "size": new_size,
                        "is_image": is_img, "duration": 5, "filter": "None",
                        "native_duration": native_duration,
                    })
                    st.session_state.processed_uploads.add(file_id)
                    running_mb += new_size / (1024 * 1024)
                    new_files_added = True
            if new_files_added:
                st.rerun()
        elif len(st.session_state.processed_uploads) > 0 and not uploaded_videos:
            st.session_state.processed_uploads = set()
        
        uploaded_audio = st.file_uploader("Background Music (Optional)", type=["mp3", "wav", "m4a"])

        if st.session_state.video_sequence:
            st.subheader("Arrange Media")
            for i, video in enumerate(st.session_state.video_sequence):
                with st.container():
                    cols = st.columns([4, 2, 2, 1, 1, 1])
                    cols[0].markdown(f"<div class='video-info'>{i+1}. {video['name']} ({video['size']/(1024*1024):.1f}MB)</div>", unsafe_allow_html=True)
                    
                    if video.get("is_image", False):
                        video["duration"] = cols[1].number_input("Duration (s)", min_value=1, max_value=60, value=video.get("duration", 5), key=f"dur_{i}")
                    else:
                        cols[1].markdown("<div style='padding-top:10px;color:grey;font-size:12px;'>Native Dur</div>", unsafe_allow_html=True)
                    
                    filter_idx = ["None", "B&W", "Sepia", "Vibrant", "Dim"].index(video.get("filter", "None"))
                    video["filter"] = cols[2].selectbox("Filter", ["None", "B&W", "Sepia", "Vibrant", "Dim"], index=filter_idx, key=f"fil_{i}", label_visibility="collapsed")

                    if cols[3].button("▲", key=f"u_{i}") and i > 0:
                        st.session_state.video_sequence[i], st.session_state.video_sequence[i-1] = st.session_state.video_sequence[i-1], st.session_state.video_sequence[i]
                        st.rerun()
                    if cols[4].button("▼", key=f"d_{i}") and i < len(st.session_state.video_sequence)-1:
                        st.session_state.video_sequence[i], st.session_state.video_sequence[i+1] = st.session_state.video_sequence[i+1], st.session_state.video_sequence[i]
                        st.rerun()
                    if cols[5].button("✕", key=f"r_{i}"):
                        st.session_state.video_sequence.pop(i)
                        st.rerun()

    with tab2:
        st.subheader("📝 Title Cards")
        for i, page in enumerate(st.session_state.title_pages):
            with st.expander(f"Title Card {i+1}", expanded=(i==0)):
                st.session_state.title_pages[i]["text"] = st.text_area("Text", page["text"], key=f"tt_{i}")
                c1, c2 = st.columns(2)
                st.session_state.title_pages[i]["size"] = c1.number_input("Size", 10, 150, page["size"], key=f"ts_{i}")
                st.session_state.title_pages[i]["color"] = c2.selectbox("Color", ["White", "Yellow", "Cyan", "Red"], index=0, key=f"tc_{i}")
        if st.button("+ Add Title Card"): st.session_state.title_pages.append({"text": "", "color": "White", "size": 50}); st.rerun()
        
        st.divider()
        st.subheader("🎬 End Credits")
        for i, page in enumerate(st.session_state.end_pages):
            with st.expander(f"End Card {i+1}", expanded=(i==0)):
                st.session_state.end_pages[i]["text"] = st.text_area("Text", page["text"], key=f"et_{i}")
                c1, c2 = st.columns(2)
                st.session_state.end_pages[i]["size"] = c1.number_input("Size", 10, 150, page["size"], key=f"es_{i}")
                st.session_state.end_pages[i]["color"] = c2.selectbox("Color", ["White", "Yellow", "Cyan", "Red"], index=0, key=f"ec_{i}")
        if st.button("+ Add End Card"): st.session_state.end_pages.append({"text": "", "color": "White", "size": 50}); st.rerun()

    with tab3:
        if st.session_state.video_sequence:
            est_duration = estimate_movie_duration(
                st.session_state.video_sequence, st.session_state.title_pages, st.session_state.end_pages, PROFILE
            )
            clip_count = len(st.session_state.video_sequence)
            st.info(
                f"Ready to render **{clip_count}** clip(s) · ~**{est_duration:.0f}s** total · "
                f"**{res_h}p** @ {PROFILE['output_fps']}fps · {get_write_kwargs(profile=PROFILE)['codec']}"
            )
            if not IS_LOCAL and est_duration > PROFILE["max_duration_sec"]:
                st.error(f"Movie too long for cloud ({est_duration:.0f}s). Max ~{PROFILE['max_duration_sec']}s — use fewer/shorter clips.")
            elif transition_style != "Hard Cut":
                st.caption("Tip: Hard Cut transitions render much faster on cloud.")

        if st.session_state.last_output and os.path.exists(st.session_state.last_output):
            with open(st.session_state.last_output, "rb") as f:
                st.download_button(
                    "⬇️ DOWNLOAD LAST MOVIE",
                    f,
                    file_name="ai_movie_pro.mp4",
                    key="download_last",
                )

        if st.button("🎬 GENERATE CINEMATIC MOVIE"):
            if not st.session_state.video_sequence:
                st.error("No media uploaded!")
                return
            est_duration = estimate_movie_duration(
                st.session_state.video_sequence, st.session_state.title_pages, st.session_state.end_pages, PROFILE
            )
            if len(st.session_state.video_sequence) > PROFILE["max_clips"]:
                st.error(f"Too many clips for cloud ({PROFILE['max_clips']} max). Remove some first.")
                return
            if est_duration > PROFILE["max_duration_sec"]:
                st.error(f"Movie too long ({est_duration:.0f}s). Cloud max is ~{PROFILE['max_duration_sec']}s.")
                return
            
            pending_cache = []
            try:
                st.session_state.gen_error = None
                gen_progress = st.progress(0)
                gen_status = st.empty()
                
                all_clips = []
                pending_cache.clear()
                clip_count = sum(1 for p in st.session_state.title_pages if p["text"].strip())
                clip_count += len(st.session_state.video_sequence)
                clip_count += sum(1 for p in st.session_state.end_pages if p["text"].strip())
                total_steps = clip_count + 2
                step = 0
                render_start = 0.65

                current_config = {
                    "bg_color": color_choice,
                    "transition": transition_style,
                    "res_h": res_h,
                    "target_ratio": target_ratio,
                    "do_watermark": do_watermark,
                    "video_vol": video_vol
                }
                if st.session_state.last_config != current_config:
                    st.session_state.processed_clips = {}
                    st.session_state.last_config = current_config

                def update_build_progress(label):
                    nonlocal step
                    step += 1
                    build_pct = (step / max(total_steps, 1)) * render_start
                    gen_status.text(f"Step {step}/{total_steps}: {label}")
                    gen_progress.progress(build_pct)

                # 1. Process Titles
                for i, page in enumerate(st.session_state.title_pages):
                    if page["text"].strip():
                        p = os.path.join(st.session_state.temp_dir, f"t_{i}.mp4")
                        cache_key = f"t_{i}_{page['text']}_{page['size']}_{page['color']}"
                        if cache_key in st.session_state.processed_clips and os.path.exists(p):
                            update_build_progress("Titles (Restored)")
                            all_clips.append(VideoFileClip(p))
                        else:
                            update_build_progress("Titles...")
                            c = create_text_clip(
                                page["text"], PROFILE["title_duration"], bg_colors[color_choice],
                                page["size"], page["color"], res_h=res_h, target_ratio=target_ratio,
                            )
                            c = apply_transition(c, transition_style)
                            all_clips.append(c)
                            pending_cache.append((cache_key, p, c))

                # 2. Process Main Clips
                for i, video in enumerate(st.session_state.video_sequence):
                    p = os.path.join(st.session_state.temp_dir, f"v_{i}.mp4")
                    cache_key = f"v_{i}_{video['name']}_{video['size']}_{video.get('duration', 0)}_{video.get('filter', 'None')}"

                    if cache_key in st.session_state.processed_clips and os.path.exists(p):
                        update_build_progress(f"{video['name']} (Restored)")
                        all_clips.append(VideoFileClip(p))
                    else:
                        update_build_progress(f"Processing {video['name']}...")
                        clip = build_media_clip(
                            video["path"],
                            video.get("is_image", False),
                            video.get("duration", 5),
                            res_h,
                            target_ratio,
                            do_watermark,
                            video_vol,
                            video.get("filter", "None"),
                            PROFILE,
                        )
                        clip = apply_transition(clip, transition_style)
                        all_clips.append(clip)
                        pending_cache.append((cache_key, p, clip))

                # 3. Credits
                for i, page in enumerate(st.session_state.end_pages):
                    if page["text"].strip():
                        p = os.path.join(st.session_state.temp_dir, f"e_{i}.mp4")
                        cache_key = f"e_{i}_{page['text']}_{page['size']}_{page['color']}"
                        if cache_key in st.session_state.processed_clips and os.path.exists(p):
                            update_build_progress("Credits (Restored)")
                            all_clips.append(VideoFileClip(p))
                        else:
                            update_build_progress("Credits...")
                            c = create_text_clip(
                                page["text"], PROFILE["title_duration"], bg_colors[color_choice],
                                page["size"], page["color"], res_h=res_h, target_ratio=target_ratio,
                            )
                            c = apply_transition(c, transition_style)
                            all_clips.append(c)
                            pending_cache.append((cache_key, p, c))

                # 4. Final Join
                step += 1
                gen_status.text(f"Step {step}/{total_steps}: Stitching clips...")
                gen_progress.progress(render_start)

                pad = -1 if transition_style != "Hard Cut" else 0
                final_video = concatenate_videoclips(all_clips, method="compose", padding=pad)

                # 5. Audio
                if uploaded_audio:
                    a_p = os.path.join(st.session_state.temp_dir, uploaded_audio.name)
                    with open(a_p, "wb") as t: t.write(uploaded_audio.getbuffer())
                    bg_a = AudioFileClip(a_p)
                    if bg_a.duration < final_video.duration:
                        bg_a = concatenate_audioclips([bg_a] * int(math.ceil(final_video.duration / bg_a.duration)))
                    bg_a = bg_a.subclipped(0, final_video.duration).with_volume_scaled(bg_vol)
                    final_video = final_video.with_audio(CompositeAudioClip([final_video.audio, bg_a]))

                # 6. Final Render (single encode, multi-threaded)
                step += 1
                gen_status.text(f"Step {step}/{total_steps}: Rendering final video... 0%")

                def on_render_progress(fraction):
                    pct = render_start + fraction * (1.0 - render_start)
                    gen_progress.progress(pct)
                    gen_status.text(f"Step {step}/{total_steps}: Rendering final video... {int(fraction * 100)}%")

                out = os.path.join(st.session_state.temp_dir, f"final_{int(time.time())}.mp4")
                render_logger = RenderProgressLogger(on_render_progress)
                final_video.write_videofile(
                    out, **get_write_kwargs(bitrate=target_bitrate, logger=render_logger, profile=PROFILE)
                )
                final_video.close()
                for c in all_clips: c.close()
                gc.collect()
                
                st.session_state.last_output = out
                gen_status.markdown("<div class='success-box'>✅ Movie Ready! You can download it below.</div>", unsafe_allow_html=True)
                gen_progress.progress(1.0)
                st.balloons()
                with open(out, "rb") as f:
                    st.download_button("⬇️ DOWNLOAD MOVIE", f, file_name="ai_movie_pro.mp4", key="download_new")
            except Exception as e:
                for cache_key, p, clip in pending_cache:
                    if cache_key not in st.session_state.processed_clips:
                        try:
                            clip.write_videofile(p, **get_write_kwargs(bitrate="1500k", profile=PROFILE))
                            st.session_state.processed_clips[cache_key] = p
                        except Exception:
                            pass
                st.session_state.gen_error = str(e)
                st.rerun()

if __name__ == "__main__":
    main()
