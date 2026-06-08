import os
import numpy as np
from PIL import Image
from moviepy import ImageClip
from proglog import ProgressBarLogger


def get_thread_count():
    return max(1, (os.cpu_count() or 4) - 1)


def get_write_kwargs(bitrate="3000k", logger=None):
    return {
        "fps": 24,
        "codec": "libx264",
        "audio_codec": "aac",
        "preset": "ultrafast",
        "threads": get_thread_count(),
        "bitrate": bitrate,
        "logger": logger,
        "ffmpeg_params": ["-movflags", "+faststart"],
    }


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


def create_ken_burns_image_clip(path, duration, res_h, target_ratio):
    """Build a photo clip with Ken Burns using crop (not per-frame resize)."""
    img = Image.open(path).convert("RGB")
    img = crop_image_to_ratio(img, target_ratio)

    target_w = int(res_h * target_ratio)
    zoom_w = int(target_w * 1.1)
    zoom_h = int(res_h * 1.1)
    img = img.resize((zoom_w, zoom_h), Image.Resampling.LANCZOS)
    frame = np.array(img)

    margin_x = max(0, zoom_w - target_w)
    margin_y = max(0, zoom_h - res_h)
    safe_duration = max(duration, 0.001)

    def ken_burns(t):
        progress = min(1.0, t / safe_duration)
        x1 = int(margin_x * progress * 0.5)
        y1 = int(margin_y * progress * 0.3)
        return frame[y1:y1 + res_h, x1:x1 + target_w]

    return ImageClip(frame).with_duration(duration).with_updated_frame_function(ken_burns)


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
