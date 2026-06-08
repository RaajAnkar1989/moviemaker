import os
import platform
import random
import subprocess

import numpy as np
from PIL import Image
from moviepy import (
    AudioClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
)
import moviepy.video.fx as vfx
from proglog import ProgressBarLogger

MAX_IMAGE_PIXELS = 12_000_000
PHOTO_FPS = 20
OUTPUT_FPS = 24
SEPIA_MATRIX = np.array(
    [[0.393, 0.769, 0.189], [0.349, 0.686, 0.168], [0.272, 0.534, 0.131]]
)
_use_videotoolbox = None


def even(value):
    value = int(value)
    return value - (value % 2)


def get_thread_count():
    return max(1, (os.cpu_count() or 4) - 1)


def is_streamlit_cloud():
    return bool(os.getenv("STREAMLIT_CLOUD_APP_ID"))


def get_runtime_profile():
    if is_streamlit_cloud():
        return {
            "name": "cloud",
            "max_upload_mb": 200,
            "max_clips": 12,
            "max_duration_sec": 90,
            "max_image_pixels": 1_500_000,
            "default_res": 360,
            "res_options": [360, 480],
            "default_quality": "Small (Low Bitrate)",
            "quality_options": ["Small (Low Bitrate)", "Standard (Medium)"],
            "default_transition_index": 0,
            "default_watermark": False,
            "output_fps": 18,
            "photo_fps": 12,
            "threads": 2,
            "preprocess_uploads": True,
            "title_duration": 2,
        }
    return {
        "name": "local",
        "max_upload_mb": 1000,
        "max_clips": 50,
        "max_duration_sec": 600,
        "max_image_pixels": MAX_IMAGE_PIXELS,
        "default_res": 720,
        "res_options": [360, 480, 720, 1080],
        "default_quality": "Standard (Medium)",
        "quality_options": ["Small (Low Bitrate)", "Standard (Medium)", "Cinematic (High)", "Pro (Ultra)"],
        "default_transition_index": 1,
        "default_watermark": True,
        "output_fps": OUTPUT_FPS,
        "photo_fps": PHOTO_FPS,
        "threads": get_thread_count(),
        "preprocess_uploads": False,
        "title_duration": 3,
    }


PROFILE = get_runtime_profile()


def _videotoolbox_available():
    global _use_videotoolbox
    if _use_videotoolbox is not None:
        return _use_videotoolbox
    _use_videotoolbox = False
    if platform.system() != "Darwin":
        return _use_videotoolbox
    try:
        from moviepy import ColorClip
        from tempfile import mkstemp

        fd, path = mkstemp(suffix=".mp4")
        os.close(fd)
        clip = ColorClip(size=(even(320), even(240)), color=(0, 0, 0)).with_duration(0.1)
        clip.write_videofile(
            path,
            fps=24,
            codec="h264_videotoolbox",
            audio=False,
            logger=None,
            ffmpeg_params=["-movflags", "+faststart"],
        )
        clip.close()
        os.remove(path)
        _use_videotoolbox = True
    except Exception:
        _use_videotoolbox = False
    return _use_videotoolbox


def get_video_codec():
    if is_streamlit_cloud():
        return "libx264"
    if _videotoolbox_available():
        return "h264_videotoolbox"
    return "libx264"


def get_write_kwargs(bitrate="3000k", logger=None, profile=None):
    profile = profile or PROFILE
    kwargs = {
        "fps": profile["output_fps"],
        "codec": get_video_codec(),
        "audio_codec": "aac",
        "bitrate": bitrate,
        "logger": logger,
        "ffmpeg_params": ["-movflags", "+faststart", "-tune", "zerolatency"],
    }
    if kwargs["codec"] == "libx264":
        kwargs["preset"] = "ultrafast"
        kwargs["threads"] = profile["threads"]
    return kwargs


def make_silence(duration, fps=44100):
    return AudioClip(
        lambda t: np.zeros((len(t) if isinstance(t, np.ndarray) else 1, 2)),
        duration=duration,
        fps=fps,
    )


def crop_image_to_ratio(img, target_ratio):
    w, h = img.size
    clip_ratio = w / h
    if abs(clip_ratio - target_ratio) <= 0.05:
        return img
    if clip_ratio > target_ratio:
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        return img.crop((left, 0, left + new_w, h))
    new_h = int(w / target_ratio)
    top = (h - new_h) // 2
    return img.crop((0, top, w, top + new_h))


def load_working_image(path, profile=None):
    profile = profile or PROFILE
    img = Image.open(path)
    img = img.convert("RGB")
    max_pixels = profile["max_image_pixels"]
    if img.width * img.height > max_pixels:
        scale = (max_pixels / (img.width * img.height)) ** 0.5
        img = img.resize(
            (max(1, int(img.width * scale)), max(1, int(img.height * scale))),
            Image.Resampling.LANCZOS,
        )
    return img


def preprocess_cloud_image(path, res_h=360):
    profile = PROFILE
    img = load_working_image(path, profile)
    max_edge = even(max(res_h * 2, 640))
    if max(img.size) > max_edge:
        img.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    out = os.path.splitext(path)[0] + "_cloud.jpg"
    img.save(out, "JPEG", quality=82, optimize=True)
    return out, os.path.getsize(out)


def preprocess_cloud_video(path, res_h=360):
    out = os.path.splitext(path)[0] + "_cloud.mp4"
    if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(path):
        return out, os.path.getsize(out)
    target_h = even(res_h)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", path,
        "-vf", f"scale=-2:{target_h}",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
        "-c:a", "aac", "-b:a", "96k",
        "-movflags", "+faststart",
        out,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out, os.path.getsize(out)


def preprocess_upload(path, is_image, res_h=360):
    if not PROFILE["preprocess_uploads"]:
        return path, os.path.getsize(path)
    if is_image:
        return preprocess_cloud_image(path, res_h)
    return preprocess_cloud_video(path, res_h)


def probe_video_duration(path):
    try:
        with VideoFileClip(path) as clip:
            return clip.duration
    except Exception:
        return None


def create_ken_burns_image_clip(path, duration, res_h, target_ratio, profile=None):
    """Build a photo clip with Ken Burns using crop (not per-frame resize)."""
    profile = profile or PROFILE
    photo_fps = profile["photo_fps"]
    img = load_working_image(path, profile)
    img = crop_image_to_ratio(img, target_ratio)

    target_w = even(int(res_h * target_ratio))
    res_h = even(res_h)
    zoom_w = int(target_w * 1.1)
    zoom_h = int(res_h * 1.1)
    img = img.resize((zoom_w, zoom_h), Image.Resampling.LANCZOS)
    frame = np.array(img)

    margin_x = max(0, zoom_w - target_w)
    margin_y = max(0, zoom_h - res_h)
    safe_duration = max(duration, 0.001)

    def ken_burns(_t):
        progress = min(1.0, _t / safe_duration)
        x1 = int(margin_x * progress * 0.5)
        y1 = int(margin_y * progress * 0.3)
        return frame[y1 : y1 + res_h, x1 : x1 + target_w]

    return (
        ImageClip(frame)
        .with_duration(duration)
        .with_fps(photo_fps)
        .with_updated_frame_function(ken_burns)
    )


def apply_transition(clip, style):
    if style == "Hard Cut":
        return clip
    s = (
        style
        if style != "Random"
        else random.choice(
            ["Cross Dissolve", "Fade In/Out", "Whip Pan", "Zoom In/Out", "Glitch", "White Flash"]
        )
    )
    if s == "Cross Dissolve":
        return clip.with_effects([vfx.CrossFadeIn(1), vfx.CrossFadeOut(1)])
    if s == "Fade In/Out":
        return clip.with_effects([vfx.FadeIn(1), vfx.FadeOut(1)])
    if s == "Whip Pan":
        return clip.with_effects([vfx.SlideIn(0.5, "right"), vfx.SlideOut(0.5, "left")])
    if s == "Zoom In/Out":
        return clip.with_effects([vfx.Resize(lambda t: 1 + 0.04 * t)])
    if s == "White Flash":
        flash = (
            ColorClip(size=clip.size, color=(255, 255, 255))
            .with_duration(0.2)
            .with_effects([vfx.FadeOut(0.2)])
        )
        return CompositeVideoClip([clip, flash.with_start(0)])
    if s == "Glitch":
        def glitch_effect(t):
            frame = clip.get_frame(t)
            if random.random() > 0.92:
                frame = np.roll(frame, random.randint(-10, 10), axis=1)
            return frame

        return clip.with_updated_frame_function(glitch_effect)
    return clip


def apply_color_filter(clip, filter_name):
    if filter_name == "None":
        return clip
    if filter_name == "B&W":
        return clip.with_effects([vfx.BlackAndWhite()])
    if filter_name == "Sepia":
        def sepia(_t):
            frame = clip.get_frame(_t)
            return np.clip(frame @ SEPIA_MATRIX.T, 0, 255).astype(np.uint8)

        return clip.with_updated_frame_function(sepia)
    if filter_name == "Vibrant":
        return clip.with_effects([vfx.MultiplyColor(1.5)])
    if filter_name == "Dim":
        return clip.with_effects([vfx.MultiplyColor(0.7)])
    return clip


def fit_video_clip(clip, res_h, target_ratio, do_watermark=True):
    w, h = clip.size
    clip_ratio = w / h
    if abs(clip_ratio - target_ratio) > 0.05:
        if clip_ratio > target_ratio:
            new_w = int(h * target_ratio)
            clip = clip.with_effects(
                [vfx.Crop(x_center=w / 2, y_center=h / 2, width=new_w, height=h)]
            )
        else:
            new_h = int(w / target_ratio)
            clip = clip.with_effects(
                [vfx.Crop(x_center=w / 2, y_center=h / 2, width=w, height=new_h)]
            )
    if clip.h != res_h:
        clip = clip.with_effects([vfx.Resize(height=even(res_h))])
    if do_watermark:
        w, h = clip.size
        clip = clip.with_effects(
            [
                vfx.Crop(x1=int(w * 0.1), y1=int(h * 0.1), width=int(w * 0.8), height=int(h * 0.8)),
                vfx.Resize(height=even(res_h)),
            ]
        )
    return clip


def build_media_clip(path, is_image, duration, res_h, target_ratio, do_watermark, video_vol, filter_name, profile=None):
    profile = profile or PROFILE
    if is_image:
        clip = create_ken_burns_image_clip(path, duration, res_h, target_ratio, profile)
        clip = clip.with_audio(make_silence(clip.duration))
    else:
        clip = VideoFileClip(path)
        clip = fit_video_clip(clip, res_h, target_ratio, do_watermark)
        clip = clip.with_audio(
            clip.audio.with_volume_scaled(video_vol) if clip.audio else make_silence(clip.duration)
        )
    clip = apply_color_filter(clip, filter_name)
    return clip


def estimate_movie_duration(video_sequence, title_pages, end_pages, profile=None):
    profile = profile or PROFILE
    title_dur = profile["title_duration"]
    total = 0.0
    for page in title_pages:
        if page.get("text", "").strip():
            total += title_dur
    for video in video_sequence:
        if video.get("is_image"):
            total += float(video.get("duration", 5))
        elif video.get("duration") is not None:
            total += float(video["duration"])
        else:
            probed = probe_video_duration(video["path"])
            total += probed if probed else 5
    for page in end_pages:
        if page.get("text", "").strip():
            total += title_dur
    return total


class RenderProgressLogger(ProgressBarLogger):
    """Maps moviepy/ffmpeg render progress to a callback."""

    def __init__(self, on_progress):
        super().__init__()
        self.on_progress = on_progress

    def bars_callback(self, bar, attr, value, old_value=None):
        total = self.bars[bar].get("total") or 1
        if total <= 0:
            return
        fraction = min(1.0, max(0.0, value / total))
        self.on_progress(fraction)
