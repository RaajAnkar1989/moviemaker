import streamlit as st
import os
import tempfile
import random
import moviepy.video.fx as vfx
from moviepy import VideoFileClip, TextClip, CompositeVideoClip, concatenate_videoclips, ColorClip, AudioClip, AudioFileClip, CompositeAudioClip, concatenate_audioclips
import numpy as np

# Page config for mobile friendliness
st.set_page_config(page_title="AI Movie Maker Pro", page_icon="🎬", layout="wide")

# Custom CSS for better mobile appearance
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #FF4B4B;
        color: white;
    }
    .stTextArea textarea {
        height: 100px;
    }
    .video-row {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 5px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    @media (max-width: 640px) {
        .main .block-container {
            padding: 1rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)

def make_silence(duration, fps=44100):
    return AudioClip(lambda t: np.zeros((len(t) if isinstance(t, np.ndarray) else 1, 2)), duration=duration, fps=fps)

def create_text_clip(text, duration=4, color_rgb=(0,0,0), font_size=70, text_color='white'):
    bg = ColorClip(size=(1280, 720), color=color_rgb).with_duration(duration)
    
    # FONT FIX: We omit the 'font' parameter or set it to None. 
    # This allows MoviePy/Pillow to use the system's default font, avoiding the "Arial" error on Linux/Streamlit Cloud.
    try:
        txt = TextClip(
            text=text,
            font_size=font_size,
            color=text_color.lower(),
            size=(1280, 720),
            method='caption'
        ).with_duration(duration).with_position('center')
    except Exception:
        # Fallback if there's still a font issue
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
    st.markdown("Professional Cinematic Video Generation — Optimized for Performance!")

    # State for Title and End pages
    if 'title_pages' not in st.session_state:
        st.session_state.title_pages = [{"text": "THE CINEMATIC JOURNEY", "color": "White", "size": 70}]
    if 'end_pages' not in st.session_state:
        st.session_state.end_pages = [{"text": "THE END", "color": "White", "size": 70}]
    
    # State for video sequence management
    if 'video_sequence' not in st.session_state:
        st.session_state.video_sequence = []

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
            st.subheader("Upload Videos")
            uploaded_videos = st.file_uploader("Select MP4 clips (Up to 500MB)", type=["mp4"], accept_multiple_files=True)
            if uploaded_videos:
                # Add new uploads to sequence if they aren't there
                current_names = [v.name for v in st.session_state.video_sequence]
                for f in uploaded_videos:
                    if f.name not in current_names:
                        st.session_state.video_sequence.append(f)
        with col2:
            st.subheader("Background Music")
            uploaded_audio = st.file_uploader("Select MP3/WAV", type=["mp3", "wav", "m4a"])

        if st.session_state.video_sequence:
            st.subheader("Arrange Video Sequence (Drag-and-Drop Style)")
            st.info("Use the buttons to move clips up or down. Top clip plays first.")
            
            for i, f in enumerate(st.session_state.video_sequence):
                col_name, col_up, col_down, col_rm = st.columns([6, 1, 1, 1])
                col_name.write(f"**{i+1}.** {f.name}")
                
                if col_up.button("▲", key=f"up_{i}"):
                    if i > 0:
                        st.session_state.video_sequence[i], st.session_state.video_sequence[i-1] = \
                            st.session_state.video_sequence[i-1], st.session_state.video_sequence[i]
                        st.rerun()
                
                if col_down.button("▼", key=f"down_{i}"):
                    if i < len(st.session_state.video_sequence) - 1:
                        st.session_state.video_sequence[i], st.session_state.video_sequence[i+1] = \
                            st.session_state.video_sequence[i+1], st.session_state.video_sequence[i]
                        st.rerun()
                
                if col_rm.button("✕", key=f"rm_v_{i}"):
                    st.session_state.video_sequence.pop(i)
                    st.rerun()
            
            if st.button("🗑️ Clear Sequence"):
                st.session_state.video_sequence = []
                st.rerun()
        else:
            st.info("Upload videos to arrange sequence.")

    with tab2:
        st.subheader("Title Cards")
        for i, page in enumerate(st.session_state.title_pages):
            with st.expander(f"Title Page {i+1}", expanded=True):
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
            with st.expander(f"Credit Page {i+1}", expanded=True):
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
        if st.button("🚀 GENERATE FULL CINEMATIC MOVIE"):
            if not st.session_state.video_sequence:
                st.error("Please upload videos first!")
            else:
                try:
                    with st.status("🎬 Processing movie...", expanded=True) as status:
                        temp_dir = tempfile.mkdtemp()
                        clips = []
                        
                        # Use the manually arranged sequence from session state
                        sorted_uploads = st.session_state.video_sequence

                        # 1. Titles
                        status.update(label="Creating title cards...")
                        for page in st.session_state.title_pages:
                            if page["text"].strip():
                                c = create_text_clip(page["text"], 4, bg_colors[color_choice], page["size"], page["color"])
                                clips.append(apply_advanced_transition(c, transition_style))

                        # 2. Clips
                        for idx, f in enumerate(sorted_uploads):
                            status.update(label=f"Processing {f.name}...")
                            t_path = os.path.join(temp_dir, f.name)
                            with open(t_path, "wb") as tmp:
                                tmp.write(f.getbuffer())
                            
                            clip = VideoFileClip(t_path)
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
                        status.update(label="Creating credit pages...")
                        for page in st.session_state.end_pages:
                            if page["text"].strip():
                                c = create_text_clip(page["text"], 4, bg_colors[color_choice], page["size"], page["color"])
                                clips.append(apply_advanced_transition(c, transition_style))

                        # 4. Concatenate
                        status.update(label="Stitching everything together...")
                        padding = -1 if transition_style in ["Cross Dissolve", "Whip Pan", "Zoom In/Out", "Random"] else 0
                        final_video = concatenate_videoclips(clips, method="compose", padding=padding)

                        # 5. Audio
                        if uploaded_audio:
                            status.update(label="Mixing background music...")
                            a_path = os.path.join(temp_dir, uploaded_audio.name)
                            with open(a_path, "wb") as tmp:
                                tmp.write(uploaded_audio.getbuffer())
                            bg_audio = AudioFileClip(a_path)
                            if bg_audio.duration < final_video.duration:
                                n_loops = int(np.ceil(final_video.duration / bg_audio.duration))
                                bg_audio = concatenate_audioclips([bg_audio] * n_loops)
                            bg_audio = bg_audio.subclipped(0, final_video.duration)
                            final_video = final_video.with_audio(CompositeAudioClip([final_video.audio, bg_audio.with_volume_scaled(bg_vol)]))

                        # 6. Render - SPEED OPTIMIZED
                        out_path = os.path.join(temp_dir, "final_movie.mp4")
                        status.update(label="Rendering (High-Speed Optimized)...")
                        
                        # Performance settings: ultrafast preset and multiple threads
                        final_video.write_videofile(
                            out_path, 
                            fps=24, 
                            codec="libx264", 
                            audio_codec="aac",
                            preset="ultrafast",
                            threads=4
                        )
                        status.update(label="✅ Movie Complete!", state="complete")

                    st.balloons()
                    with open(out_path, "rb") as file:
                        st.download_button("⬇️ DOWNLOAD MOVIE", data=file, file_name="movie_pro.mp4", mime="video/mp4")
                        
                except Exception as e:
                    st.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
