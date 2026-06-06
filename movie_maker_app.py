import streamlit as st
import os
import tempfile
import random
import time
import gc
from moviepy import VideoFileClip, TextClip, CompositeVideoClip, concatenate_videoclips, ColorClip, AudioClip, AudioFileClip, CompositeAudioClip, concatenate_audioclips
import moviepy.video.fx as vfx
import numpy as np

# --- CLOUD OPTIMIZATION ---
# Streamlit Cloud has ~1GB RAM. Processing 300MB+ files requires extreme care.
MAX_RES = 720 # Limit resolution to 720p for cloud stability

st.set_page_config(page_title="AI Movie Maker Pro", page_icon="🎬", layout="wide")

# UI Styling
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #FF4B4B; color: white; font-weight: bold; }
    .video-info { background-color: #262730; padding: 10px; border-radius: 5px; border: 1px solid #444; margin-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

# Initialization
if 'temp_dir' not in st.session_state:
    st.session_state.temp_dir = tempfile.mkdtemp()
if 'video_sequence' not in st.session_state:
    st.session_state.video_sequence = []
if 'title_pages' not in st.session_state:
    st.session_state.title_pages = [{"text": "THE CINEMATIC JOURNEY", "color": "White", "size": 60}]
if 'end_pages' not in st.session_state:
    st.session_state.end_pages = [{"text": "THE END", "color": "White", "size": 60}]

def make_silence(duration, fps=44100):
    return AudioClip(lambda t: np.zeros((len(t) if isinstance(t, np.ndarray) else 1, 2)), duration=duration, fps=fps)

def create_text_clip(text, duration=4, color_rgb=(0,0,0), font_size=60, text_color='white'):
    bg = ColorClip(size=(1280, 720), color=color_rgb).with_duration(duration)
    try:
        txt = TextClip(text=text, font_size=font_size, color=text_color.lower(), size=(1280, 720), method='caption').with_duration(duration).with_position('center')
    except:
        txt = TextClip(text=text, font_size=font_size, color='white', size=(1280, 720), method='caption').with_duration(duration).with_position('center')
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
            if random.random() > 0.92:
                frame = np.roll(frame, random.randint(-10, 10), axis=1)
            return frame
        return clip.with_updated_frame_function(glitch_effect)
    return clip

def main():
    st.title("🎬 AI Movie Maker Pro")
    st.warning("⚠️ Cloud RAM is limited (1GB). For 300MB+ files, please use 1-2 clips at a time or lower resolution.")

    with st.sidebar:
        st.header("🎨 Card Style")
        bg_colors = {"Black": (0, 0, 0), "Dark Blue": (0, 0, 50), "Dark Red": (50, 0, 0), "Deep Purple": (48, 25, 52), "White": (255, 255, 255)}
        color_choice = st.selectbox("Background Color", list(bg_colors.keys()))
        
        st.divider()
        st.header("🎞️ Cinematic")
        do_watermark = st.checkbox("Remove Watermarks (Smart Zoom)", value=True)
        transition_style = st.selectbox("Transition Style", ["Hard Cut", "Cross Dissolve", "Fade In/Out", "Whip Pan", "Zoom In/Out", "Glitch", "White Flash", "Random"], index=1)
        
        st.divider()
        st.header("🔊 Audio")
        video_vol = st.slider("Original Volume", 0.0, 2.0, 1.0)
        bg_vol = st.slider("Music Volume", 0.0, 2.0, 0.5)

    tab1, tab2, tab3 = st.tabs(["📁 Files", "📝 Credits", "🚀 Create"])

    with tab1:
        uploaded_videos = st.file_uploader("Upload Clips (MP4/MOV up to 500MB)", type=["mp4", "mov"], accept_multiple_files=True)
        if uploaded_videos:
            for f in uploaded_videos:
                t_path = os.path.join(st.session_state.temp_dir, f.name)
                if not os.path.exists(t_path):
                    with open(t_path, "wb") as tmp: tmp.write(f.getbuffer())
                    st.session_state.video_sequence.append({"name": f.name, "path": t_path})
        
        uploaded_audio = st.file_uploader("Background Music (Optional)", type=["mp3", "wav", "m4a"])

        if st.session_state.video_sequence:
            st.subheader("Arrange Clips")
            for i, video in enumerate(st.session_state.video_sequence):
                cols = st.columns([6, 1, 1, 1])
                cols[0].markdown(f"<div class='video-info'>{i+1}. {video['name']}</div>", unsafe_allow_html=True)
                if cols[1].button("▲", key=f"u_{i}") and i > 0:
                    st.session_state.video_sequence[i], st.session_state.video_sequence[i-1] = st.session_state.video_sequence[i-1], st.session_state.video_sequence[i]
                    st.rerun()
                if cols[2].button("▼", key=f"d_{i}") and i < len(st.session_state.video_sequence)-1:
                    st.session_state.video_sequence[i], st.session_state.video_sequence[i+1] = st.session_state.video_sequence[i+1], st.session_state.video_sequence[i]
                    st.rerun()
                if cols[3].button("✕", key=f"r_{i}"):
                    st.session_state.video_sequence.pop(i)
                    st.rerun()

    with tab2:
        for i, page in enumerate(st.session_state.title_pages):
            with st.expander(f"Title Card {i+1}", expanded=(i==0)):
                st.session_state.title_pages[i]["text"] = st.text_area("Text", page["text"], key=f"tt_{i}")
                c1, c2 = st.columns(2)
                st.session_state.title_pages[i]["size"] = c1.number_input("Size", 10, 150, page["size"], key=f"ts_{i}")
                st.session_state.title_pages[i]["color"] = c2.selectbox("Color", ["White", "Yellow", "Cyan", "Red"], index=0, key=f"tc_{i}")
        if st.button("+ Add Title"): st.session_state.title_pages.append({"text": "", "color": "White", "size": 60}); st.rerun()

    with tab3:
        if st.button("🎬 GENERATE CINEMATIC MOVIE"):
            if not st.session_state.video_sequence:
                st.error("No videos uploaded!")
                return
            
            try:
                with st.status("🎬 Production Started...", expanded=True) as status:
                    processed_clips = []
                    
                    # 1. Titles
                    for page in st.session_state.title_pages:
                        if page["text"].strip():
                            c = create_text_clip(page["text"], 3, bg_colors[color_choice], page["size"], page["color"])
                            processed_clips.append(apply_transition(c, transition_style))

                    # 2. Main Clips (Memory Optimized)
                    for video in st.session_state.video_sequence:
                        status.update(label=f"Optimizing {video['name']}...")
                        clip = VideoFileClip(video['path'])
                        
                        # Resize for RAM safety
                        if clip.h > MAX_RES: clip = clip.with_effects([vfx.Resize(height=MAX_RES)])
                        
                        if do_watermark:
                            w, h = clip.size
                            clip = clip.with_effects([vfx.Crop(x1=int(w*0.1), y1=int(h*0.1), width=int(w*0.8), height=int(h*0.8)), vfx.Resize(width=w, height=h)])
                        
                        clip = apply_transition(clip, transition_style)
                        clip = clip.with_audio(clip.audio.with_volume_scaled(video_vol) if clip.audio else make_silence(clip.duration))
                        processed_clips.append(clip)

                    # 3. Credits
                    for page in st.session_state.end_pages:
                        if page["text"].strip():
                            c = create_text_clip(page["text"], 3, bg_colors[color_choice], page["size"], page["color"])
                            processed_clips.append(apply_transition(c, transition_style))

                    # 4. Concatenate
                    status.update(label="Stitching Scenes...")
                    pad = -1 if transition_style != "Hard Cut" else 0
                    final = concatenate_videoclips(processed_clips, method="compose", padding=pad)

                    # 5. Audio
                    if uploaded_audio:
                        status.update(label="Mixing Soundtrack...")
                        a_p = os.path.join(st.session_state.temp_dir, uploaded_audio.name)
                        with open(a_p, "wb") as t: t.write(uploaded_audio.getbuffer())
                        bg_a = AudioFileClip(a_p)
                        if bg_a.duration < final.duration: bg_a = concatenate_audioclips([bg_a] * int(np.ceil(final.duration/bg_a.duration)))
                        bg_a = bg_a.subclipped(0, final.duration).with_volume_scaled(bg_vol)
                        final = final.with_audio(CompositeAudioClip([final.audio, bg_a]))

                    # 6. Render
                    out = os.path.join(st.session_state.temp_dir, f"mov_{int(time.time())}.mp4")
                    status.update(label="Rendering (RAM-Safe Mode)...")
                    final.write_videofile(out, fps=24, codec="libx264", audio_codec="aac", preset="ultrafast", threads=2) # Fewer threads to save RAM
                    
                    final.close()
                    for c in processed_clips: c.close()
                    gc.collect() # Force garbage collection
                    
                    status.update(label="✅ Movie Ready!", state="complete")
                
                st.balloons()
                with open(out, "rb") as f:
                    st.download_button("⬇️ DOWNLOAD MOVIE", f, file_name="ai_movie.mp4")
            except Exception as e:
                st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
