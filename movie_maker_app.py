import streamlit as st
import os
import tempfile
import random
import time
import gc
import shutil
from moviepy import VideoFileClip, TextClip, CompositeVideoClip, concatenate_videoclips, ColorClip, AudioClip, AudioFileClip, CompositeAudioClip, concatenate_audioclips, ImageClip
import moviepy.video.fx as vfx
import numpy as np

import socket
import qrcode
from io import BytesIO

# --- EXTREME STABILITY & PERFORMANCE CONFIG ---
MAX_UPLOAD_MB = 1000 # Increased for local use
TEMP_ROOT = tempfile.gettempdir()

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except: return "127.0.0.1"

# Robust Cloud Detection
IS_LOCAL = not os.getenv("STREAMLIT_CLOUD_APP_ID") and not os.getenv("DYNO")
LOCAL_IP = get_local_ip()

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
def make_silence(duration, fps=44100):
    return AudioClip(lambda t: np.zeros((len(t) if isinstance(t, np.ndarray) else 1, 2)), duration=duration, fps=fps)

def create_text_clip(text, duration=4, color_rgb=(0,0,0), font_size=50, text_color='white', res_h=480, target_ratio=16/9):
    target_size = (int(res_h * target_ratio), res_h)
    bg = ColorClip(size=target_size, color=color_rgb).with_duration(duration)
    try:
        txt = TextClip(text=text, font_size=font_size, color=text_color.lower(), size=target_size, method='caption').with_duration(duration).with_position('center')
    except:
        txt = TextClip(text=text, font_size=font_size, color='white', size=target_size, method='caption').with_duration(duration).with_position('center')
    return CompositeVideoClip([bg, txt]).with_audio(make_silence(duration))

def apply_transition(clip, style):
    if style == "Hard Cut": return clip
    s = style if style != "Random" else random.choice(["Cross Dissolve", "Fade In/Out", "Whip Pan", "Zoom In/Out", "Glitch", "White Flash"])
    if s == "Cross Dissolve": return clip.with_effects([vfx.CrossFadeIn(1), vfx.CrossFadeOut(1)])
    if s == "Fade In/Out": return clip.with_effects([vfx.FadeIn(1), vfx.FadeOut(1)])
    if s == "Whip Pan": return clip.with_effects([vfx.SlideIn(0.5, 'right'), vfx.SlideOut(0.5, 'left')])
    if s == "Zoom In/Out": return clip.with_effects([vfx.Resize(lambda t: 1 + 0.04 * t)])
    if s == "White Flash": 
        flash = ColorClip(size=clip.size, color=(255, 255, 255)).with_duration(0.2).with_effects([vfx.FadeOut(0.2)])
        return CompositeVideoClip([clip, flash.with_start(0)])
    if s == "Glitch":
        def glitch_effect(t):
            frame = clip.get_frame(t)
            if random.random() > 0.92: frame = np.roll(frame, random.randint(-10, 10), axis=1)
            return frame
        return clip.with_updated_frame_function(glitch_effect)
    return clip

def apply_color_filter(clip, filter_name):
    if filter_name == "None": return clip
    if filter_name == "B&W": return clip.with_effects([vfx.BlackAndWhite()])
    if filter_name == "Sepia":
        def sepia(t):
            frame = clip.get_frame(t)
            sepia_filter = np.array([[0.393, 0.769, 0.189],
                                   [0.349, 0.686, 0.168],
                                   [0.272, 0.534, 0.131]])
            return np.clip(frame @ sepia_filter.T, 0, 255).astype(np.uint8)
        return clip.with_updated_frame_function(sepia)
    if filter_name == "Vibrant": return clip.with_effects([vfx.MultiplyColor(1.5)])
    if filter_name == "Dim": return clip.with_effects([vfx.MultiplyColor(0.7)])
    return clip

# --- MAIN APP ---
def main():
    st.title("🎬 AI Movie Maker Pro")
    
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
        if IS_LOCAL:
            st.success("💻 **Running Locally** (Full Power)")
            st.markdown("### 📱 Mobile App Link")
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

        do_watermark = st.checkbox("Remove Watermarks (Smart Zoom)", value=True)
        transition_style = st.selectbox("Transition Style", ["Hard Cut", "Cross Dissolve", "Fade In/Out", "Whip Pan", "Zoom In/Out", "Glitch", "White Flash", "Random"], index=1)
        res_options = [360, 480, 720, 1080] if IS_LOCAL else [360, 480, 720]
        default_res = 720 if IS_LOCAL else 480
        res_h = st.select_slider("Resolution (Height)", options=res_options, value=default_res)
        
        st.header("💎 Quality & Size")
        quality_map = {"Small (Low Bitrate)": "1500k", "Standard (Medium)": "3000k", "Cinematic (High)": "6000k", "Pro (Ultra)": "12000k"}
        quality_choice = st.select_slider("Export Quality", options=list(quality_map.keys()), value="Standard (Medium)")
        target_bitrate = quality_map[quality_choice]
        
        st.divider()
        st.header("🔊 Audio")
        video_vol = st.slider("Original Volume", 0.0, 2.0, 1.0)
        bg_vol = st.slider("Music Volume", 0.0, 2.0, 0.5)
        st.divider()
        if st.button("🗑️ Clear Render Cache"): clear_cache()
        if st.button("🔄 Full Reset"): reset_app()

    tab1, tab2, tab3 = st.tabs(["📁 Files & Order", "📝 Titles & Credits", "🚀 Production"])

    with tab1:
        st.markdown(f"<div class='upload-stats'>Storage Used: {total_size_mb:.1f}MB / {MAX_UPLOAD_MB}MB</div>", unsafe_allow_html=True)
        uploaded_videos = st.file_uploader("Upload Clips & Photos", type=["mp4", "mov", "jpg", "jpeg", "png"], accept_multiple_files=True)
        
        if uploaded_videos:
            new_files_added = False
            for f in uploaded_videos:
                file_id = f"{f.name}_{f.size}"
                if file_id not in st.session_state.processed_uploads:
                    t_path = os.path.join(st.session_state.temp_dir, f.name)
                    with open(t_path, "wb") as tmp: tmp.write(f.getbuffer())
                    is_img = f.name.lower().endswith(('.png', '.jpg', '.jpeg'))
                    st.session_state.video_sequence.append({
                        "name": f.name, "path": t_path, "size": f.size, 
                        "is_image": is_img, "duration": 5, "filter": "None"
                    })
                    st.session_state.processed_uploads.add(file_id)
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
        if st.button("🎬 GENERATE CINEMATIC MOVIE"):
            if not st.session_state.video_sequence:
                st.error("No media uploaded!")
                return
            
            try:
                st.session_state.gen_error = None
                gen_progress = st.progress(0)
                gen_status = st.empty()
                
                processed_paths = []
                total_steps = len(st.session_state.title_pages) + len(st.session_state.video_sequence) + len(st.session_state.end_pages) + 2
                step = 0

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

                # 1. Process Titles
                for i, page in enumerate(st.session_state.title_pages):
                    if page["text"].strip():
                        step += 1
                        gen_status.text(f"Step {step}/{total_steps}: Titles...")
                        gen_progress.progress(step/total_steps)
                        
                        p = os.path.join(st.session_state.temp_dir, f"t_{i}.mp4")
                        cache_key = f"t_{i}_{page['text']}_{page['size']}_{page['color']}"
                        
                        if cache_key in st.session_state.processed_clips and os.path.exists(p):
                            gen_status.text(f"Step {step}/{total_steps}: Titles (Restored)")
                        else:
                            c = create_text_clip(page["text"], 3, bg_colors[color_choice], page["size"], page["color"], res_h=res_h, target_ratio=target_ratio)
                            c = apply_transition(c, transition_style)
                            c.write_videofile(p, fps=24, codec="libx264", logger=None, preset="ultrafast")
                            c.close(); gc.collect()
                            st.session_state.processed_clips[cache_key] = p
                        processed_paths.append(p)

                # 2. Process Main Clips
                for i, video in enumerate(st.session_state.video_sequence):
                    step += 1
                    gen_status.text(f"Step {step}/{total_steps}: Processing {video['name']}...")
                    gen_progress.progress(step/total_steps)
                    
                    p = os.path.join(st.session_state.temp_dir, f"v_{i}.mp4")
                    # Cache key includes filename, size, duration, filter
                    cache_key = f"v_{i}_{video['name']}_{video['size']}_{video.get('duration', 0)}_{video.get('filter', 'None')}"
                    
                    if cache_key in st.session_state.processed_clips and os.path.exists(p):
                        gen_status.text(f"Step {step}/{total_steps}: {video['name']} (Restored)")
                    else:
                        is_img = video.get("is_image", False)
                        if is_img:
                            clip = ImageClip(video['path']).with_duration(video.get("duration", 5))
                            # Ken Burns dynamic pan/zoom (slow 10% zoom)
                            clip = clip.with_effects([vfx.Resize(lambda t: 1 + 0.1 * (t / clip.duration))])
                        else:
                            clip = VideoFileClip(video['path'])

                        # Crop to target_ratio
                        w, h = clip.size
                        clip_ratio = w / h
                        if abs(clip_ratio - target_ratio) > 0.05:
                            if clip_ratio > target_ratio:
                                new_w = int(h * target_ratio)
                                clip = clip.with_effects([vfx.Crop(x_center=w/2, y_center=h/2, width=new_w, height=h)])
                            else:
                                new_h = int(w / target_ratio)
                                clip = clip.with_effects([vfx.Crop(x_center=w/2, y_center=h/2, width=w, height=new_h)])

                        # Resize to target res_h
                        if clip.h != res_h: 
                            clip = clip.with_effects([vfx.Resize(height=res_h)])
                            
                        # Watermark removal
                        if not is_img and do_watermark:
                            w, h = clip.size
                            clip = clip.with_effects([vfx.Crop(x1=int(w*0.1), y1=int(h*0.1), width=int(w*0.8), height=int(h*0.8)), vfx.Resize(height=res_h)])

                        clip = apply_color_filter(clip, video.get("filter", "None"))
                        clip = apply_transition(clip, transition_style)
                        
                        if not is_img:
                            clip = clip.with_audio(clip.audio.with_volume_scaled(video_vol) if clip.audio else make_silence(clip.duration))
                        else:
                            clip = clip.with_audio(make_silence(clip.duration))
                            
                        clip.write_videofile(p, fps=24, codec="libx264", audio_codec="aac", logger=None, preset="ultrafast", bitrate=target_bitrate)
                        clip.close(); gc.collect()
                        st.session_state.processed_clips[cache_key] = p
                    processed_paths.append(p)

                # 3. Credits
                for i, page in enumerate(st.session_state.end_pages):
                    if page["text"].strip():
                        step += 1
                        gen_status.text(f"Step {step}/{total_steps}: Credits...")
                        gen_progress.progress(step/total_steps)
                        
                        p = os.path.join(st.session_state.temp_dir, f"e_{i}.mp4")
                        cache_key = f"e_{i}_{page['text']}_{page['size']}_{page['color']}"
                        
                        if cache_key in st.session_state.processed_clips and os.path.exists(p):
                            gen_status.text(f"Step {step}/{total_steps}: Credits (Restored)")
                        else:
                            c = create_text_clip(page["text"], 3, bg_colors[color_choice], page["size"], page["color"], res_h=res_h, target_ratio=target_ratio)
                            c = apply_transition(c, transition_style)
                            c.write_videofile(p, fps=24, codec="libx264", logger=None, preset="ultrafast")
                            c.close(); gc.collect()
                            st.session_state.processed_clips[cache_key] = p
                        processed_paths.append(p)

                # 4. Final Join
                step += 1
                gen_status.text(f"Step {step}/{total_steps}: Final Stitching...")
                gen_progress.progress(step/total_steps)
                
                final_clips = [VideoFileClip(p) for p in processed_paths]
                pad = -1 if transition_style != "Hard Cut" else 0
                final_video = concatenate_videoclips(final_clips, method="compose", padding=pad)

                # 5. Audio
                if uploaded_audio:
                    a_p = os.path.join(st.session_state.temp_dir, uploaded_audio.name)
                    with open(a_p, "wb") as t: t.write(uploaded_audio.getbuffer())
                    bg_a = AudioFileClip(a_p)
                    if bg_a.duration < final_video.duration: bg_a = concatenate_audioclips([bg_a] * int(np.ceil(final_video.duration/bg_a.duration)))
                    bg_a = bg_a.subclipped(0, final_video.duration).with_volume_scaled(bg_vol)
                    final_video = final_video.with_audio(CompositeAudioClip([final_video.audio, bg_a]))

                # 6. Final Render
                out = os.path.join(st.session_state.temp_dir, f"final_{int(time.time())}.mp4")
                final_video.write_videofile(out, fps=24, codec="libx264", audio_codec="aac", preset="ultrafast", threads=1, bitrate=target_bitrate)
                final_video.close(); [c.close() for c in final_clips]; gc.collect()
                
                gen_status.markdown("<div class='success-box'>✅ Movie Ready! You can download it below.</div>", unsafe_allow_html=True)
                gen_progress.progress(1.0)
                st.balloons()
                with open(out, "rb") as f: st.download_button("⬇️ DOWNLOAD MOVIE", f, file_name="ai_movie_pro.mp4")
            except Exception as e:
                st.session_state.gen_error = str(e)
                st.rerun()

if __name__ == "__main__":
    main()
