import streamlit as st
import os
import tempfile
import random
import time
import moviepy.video.fx as vfx
from moviepy import VideoFileClip, TextClip, CompositeVideoClip, concatenate_videoclips, ColorClip, AudioClip, AudioFileClip, CompositeAudioClip, concatenate_audioclips
import numpy as np

# Page config for mobile friendliness
st.set_page_config(page_title="AI Movie Maker Pro", page_icon="🎬", layout="wide")

# Custom CSS for high-performance Dark Mode and UI speed
st.markdown("""
    <style>
    /* Dark Theme Overrides */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3.5em;
        background-color: #FF4B4B;
        color: white;
        font-weight: bold;
        transition: transform 0.1s;
    }
    .stButton>button:active {
        transform: scale(0.98);
    }
    .video-row {
        background-color: #262730;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        border: 1px solid #333;
    }
    .stTextArea textarea {
        background-color: #1A1C23;
        color: white;
        border-radius: 8px;
    }
    /* Fast Mobile Tweaks */
    @media (max-width: 640px) {
        .main .block-container {
            padding: 0.5rem;
        }
        .stButton>button {
            height: 4em;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# Persistent storage for uploaded files to avoid re-loading slowness
if 'temp_dir' not in st.session_state:
    st.session_state.temp_dir = tempfile.mkdtemp()
if 'video_sequence' not in st.session_state:
    st.session_state.video_sequence = []
if 'title_pages' not in st.session_state:
    st.session_state.title_pages = [{"text": "THE CINEMATIC JOURNEY", "color": "White", "size": 70}]
if 'end_pages' not in st.session_state:
    st.session_state.end_pages = [{"text": "THE END", "color": "White", "size": 70}]

def make_silence(duration, fps=44100):
    return AudioClip(lambda t: np.zeros((len(t) if isinstance(t, np.ndarray) else 1, 2)), duration=duration, fps=fps)

def create_text_clip(text, duration=4, color_rgb=(0,0,0), font_size=70, text_color='white'):
    bg = ColorClip(size=(1280, 720), color=color_rgb).with_duration(duration)
    try:
        txt = TextClip(
            text=text,
            font_size=font_size,
            color=text_color.lower(),
            size=(1280, 720),
            method='caption'
        ).with_duration(duration).with_position('center')
    except Exception:
        txt = TextClip(
            text=text,
            font_size=font_size,
            color='white',
            size=(1280, 720),
            method='caption'
        ).with_duration(duration).with_position('center')
        
    video = CompositeVideoClip([bg, txt])
    video = video.with_audio(make_silence(duration))
    return video

def apply_advanced_transition(clip, style):
    if style == "Hard Cut": return clip
    s = style if style != "Random" else random.choice([
        "Cross Dissolve", "Fade In/Out", "Whip Pan", "Zoom In/Out", "Glitch", "White Flash"
    ])
    
    if s == "Cross Dissolve": return clip.with_effects([vfx.CrossFadeIn(1), vfx.CrossFadeOut(1)])
    if s == "Fade In/Out": return clip.with_effects([vfx.FadeIn(1), vfx.FadeOut(1)])
    if s == "Whip Pan": return clip.with_effects([vfx.SlideIn(0.5, 'right'), vfx.SlideOut(0.5, 'left')])
    if s == "Zoom In/Out": return clip.with_effects([vfx.Resize(lambda t: 1 + 0.05 * t)])
    if s == "White Flash": 
        flash = ColorClip(size=clip.size, color=(255, 255, 255)).with_duration(0.3).with_effects([vfx.FadeOut(0.3)])
        return CompositeVideoClip([clip, flash.with_start(0)])
    if s == "Glitch":
        def glitch_effect(t):
            frame = clip.get_frame(t)
            if random.random() > 0.90:
                h, w, c = frame.shape
                shift = random.randint(-15, 15)
                frame = np.roll(frame, shift, axis=1)
            return frame
        return clip.with_updated_frame_function(glitch_effect)
    return clip

def main():
    st.title("🎬 AI Movie Maker Pro")
    st.markdown("Professional Cinematic Studio — Optimized for iPhone & High-Res Clips")

    # Sidebar for Pro Settings
    with st.sidebar:
        st.header("🎨 Style & Effects")
        
        bg_colors = {
            "Black": (0, 0, 0),
            "Dark Blue": (0, 0, 50),
            "Dark Red": (50, 0, 0),
            "Dark Green": (0, 50, 0),
            "Deep Purple": (48, 25, 52),
            "White": (255, 255, 255)
        }
        color_choice = st.selectbox("Card Background Color", list(bg_colors.keys()))
        
        st.divider()
        st.header("🎞️ Cinematic Options")
        do_watermark = st.checkbox("Remove Watermarks (Smart Zoom)", value=True)
        transition_style = st.selectbox("Transition Style", [
            "Hard Cut", "Cross Dissolve", "Fade In/Out", "Whip Pan", 
            "Zoom In/Out", "Glitch", "White Flash", "Random"
        ], index=1)
        
        st.divider()
        st.header("🔊 Audio Mixing")
        video_vol = st.slider("Original Video Volume", 0.0, 2.0, 1.0)
        bg_vol = st.slider("Background Music Volume", 0.0, 2.0, 0.5)

    # Main Content Area
    tab1, tab2, tab3 = st.tabs(["📁 Upload & Order", "📝 Titles & Credits", "🎬 Generate"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Upload Media")
            # Added .mov support for iPhone users
            uploaded_videos = st.file_uploader("Select Video clips (MP4, MOV)", type=["mp4", "mov"], accept_multiple_files=True)
            
            if uploaded_videos:
                for f in uploaded_videos:
                    # Save to persistent temp dir if not already there
                    t_path = os.path.join(st.session_state.temp_dir, f.name)
                    if not os.path.exists(t_path):
                        with open(t_path, "wb") as tmp:
                            tmp.write(f.getbuffer())
                        # Add to sequence only once
                        st.session_state.video_sequence.append({"name": f.name, "path": t_path})
        
        with col2:
            st.subheader("Background Music")
            uploaded_audio = st.file_uploader("Select MP3/WAV/M4A", type=["mp3", "wav", "m4a"])

        if st.session_state.video_sequence:
            st.divider()
            st.subheader("Arrange Video Sequence")
            st.caption("Top clip plays first. Move clips using the arrows.")
            
            # Using a loop with session state to keep UI snappy
            for i, video in enumerate(st.session_state.video_sequence):
                with st.container():
                    c_name, c_up, c_down, c_rm = st.columns([6, 1, 1, 1])
                    c_name.markdown(f"**{i+1}.** `{video['name']}`")
                    
                    if c_up.button("▲", key=f"up_{i}_{video['name']}"):
                        if i > 0:
                            st.session_state.video_sequence[i], st.session_state.video_sequence[i-1] = \
                                st.session_state.video_sequence[i-1], st.session_state.video_sequence[i]
                            st.rerun()
                    
                    if c_down.button("▼", key=f"down_{i}_{video['name']}"):
                        if i < len(st.session_state.video_sequence) - 1:
                            st.session_state.video_sequence[i], st.session_state.video_sequence[i+1] = \
                                st.session_state.video_sequence[i+1], st.session_state.video_sequence[i]
                            st.rerun()
                    
                    if c_rm.button("✕", key=f"rm_{i}_{video['name']}"):
                        st.session_state.video_sequence.pop(i)
                        st.rerun()
            
            if st.button("🗑️ Clear Sequence"):
                st.session_state.video_sequence = []
                st.rerun()
        else:
            st.info("Upload videos from your library or camera to begin.")

    with tab2:
        st.subheader("Title Cards")
        for i, page in enumerate(st.session_state.title_pages):
            with st.expander(f"Title Page {i+1}", expanded=(i==0)):
                st.session_state.title_pages[i]["text"] = st.text_area(f"Text for Page {i+1}", value=page["text"], key=f"t_text_{i}")
                c1, c2 = st.columns(2)
                st.session_state.title_pages[i]["size"] = c1.number_input("Size", 10, 200, page["size"], key=f"t_size_{i}")
                st.session_state.title_pages[i]["color"] = c2.selectbox("Color", ["White", "Yellow", "Cyan", "Green", "Red"], index=0, key=f"t_color_{i}")
                if st.button(f"Remove Page {i+1}", key=f"t_rm_{i}"):
                    st.session_state.title_pages.pop(i)
                    st.rerun()
        if st.button("+ Add Title Page"):
            st.session_state.title_pages.append({"text": "", "color": "White", "size": 70})
            st.rerun()

        st.divider()
        st.subheader("End Credits")
        for i, page in enumerate(st.session_state.end_pages):
            with st.expander(f"Credit Page {i+1}", expanded=(i==0)):
                st.session_state.end_pages[i]["text"] = st.text_area(f"Text for Page {i+1}", value=page["text"], key=f"e_text_{i}")
                c1, c2 = st.columns(2)
                st.session_state.end_pages[i]["size"] = c1.number_input("Size", 10, 200, page["size"], key=f"e_size_{i}")
                st.session_state.end_pages[i]["color"] = c2.selectbox("Color", ["White", "Yellow", "Cyan", "Green", "Red"], index=0, key=f"e_color_{i}")
                if st.button(f"Remove Page {i+1}", key=f"e_rm_{i}"):
                    st.session_state.end_pages.pop(i)
                    st.rerun()
        if st.button("+ Add Credit Page"):
            st.session_state.end_pages.append({"text": "", "color": "White", "size": 70})
            st.rerun()

    with tab3:
        if st.button("🚀 GENERATE CINEMATIC MOVIE (HIGH SPEED)"):
            if not st.session_state.video_sequence:
                st.error("Please upload videos first!")
            else:
                try:
                    with st.status("🎬 Production in progress...", expanded=True) as status:
                        clips = []
                        
                        # 1. Titles
                        status.update(label="Creating cinematic titles...")
                        for page in st.session_state.title_pages:
                            if page["text"].strip():
                                c = create_text_clip(page["text"], 4, bg_colors[color_choice], page["size"], page["color"])
                                clips.append(apply_advanced_transition(c, transition_style))

                        # 2. Clips (Optimized for large files)
                        for idx, video in enumerate(st.session_state.video_sequence):
                            status.update(label=f"Processing {video['name']} (High-Res Load)...")
                            # We load each clip once and apply effects
                            clip = VideoFileClip(video['path'])
                            
                            if do_watermark:
                                w, h = clip.size
                                clip = clip.with_effects([
                                    vfx.Crop(x1=int(w*0.1), y1=int(h*0.1), width=int(w*0.8), height=int(h*0.8)),
                                    vfx.Resize(width=w, height=h)
                                ])
                            
                            clip = apply_advanced_transition(clip, transition_style)
                            if clip.audio is None:
                                clip = clip.with_audio(make_silence(clip.duration))
                            else:
                                clip = clip.with_audio(clip.audio.with_volume_scaled(video_vol))
                            clips.append(clip)

                        # 3. Credits
                        status.update(label="Adding end credits...")
                        for page in st.session_state.end_pages:
                            if page["text"].strip():
                                c = create_text_clip(page["text"], 4, bg_colors[color_choice], page["size"], page["color"])
                                clips.append(apply_advanced_transition(c, transition_style))

                        # 4. Concatenate
                        status.update(label="Stitching final sequence...")
                        padding = -1 if transition_style in ["Cross Dissolve", "Whip Pan", "Zoom In/Out", "Random"] else 0
                        final_video = concatenate_videoclips(clips, method="compose", padding=padding)

                        # 5. Audio
                        if uploaded_audio:
                            status.update(label="Mastering background audio...")
                            a_path = os.path.join(st.session_state.temp_dir, uploaded_audio.name)
                            with open(a_path, "wb") as tmp:
                                tmp.write(uploaded_audio.getbuffer())
                            bg_audio = AudioFileClip(a_path)
                            if bg_audio.duration < final_video.duration:
                                n_loops = int(np.ceil(final_video.duration / bg_audio.duration))
                                bg_audio = concatenate_audioclips([bg_audio] * n_loops)
                            bg_audio = bg_audio.subclipped(0, final_video.duration)
                            final_video = final_video.with_audio(CompositeAudioClip([final_video.audio, bg_audio.with_volume_scaled(bg_vol)]))

                        # 6. Render - MAXIMUM SPEED
                        out_path = os.path.join(st.session_state.temp_dir, f"movie_{int(time.time())}.mp4")
                        status.update(label="Exporting High-Res MP4 (Optimized)...")
                        
                        # Use 'ultrafast' and multi-threading for the best industry speed
                        final_video.write_videofile(
                            out_path, 
                            fps=24, 
                            codec="libx264", 
                            audio_codec="aac",
                            preset="ultrafast",
                            threads=8 # Increased threads for 300MB+ files
                        )
                        status.update(label="✅ Cinematic Movie Ready!", state="complete")

                    st.balloons()
                    with open(out_path, "rb") as file:
                        st.download_button("⬇️ DOWNLOAD MOVIE", data=file, file_name="ai_movie_pro.mp4", mime="video/mp4")
                        
                except Exception as e:
                    st.error(f"Error during production: {str(e)}")

if __name__ == "__main__":
    main()
