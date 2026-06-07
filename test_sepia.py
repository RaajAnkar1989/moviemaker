from moviepy import ColorClip
import numpy as np

c = ColorClip(size=(100,100), color=(100,100,100)).with_duration(1)

def sepia(t):
    frame = c.get_frame(t)
    sepia_filter = np.array([[0.393, 0.769, 0.189],
                           [0.349, 0.686, 0.168],
                           [0.272, 0.534, 0.131]])
    return np.clip(frame @ sepia_filter.T, 0, 255).astype(np.uint8)

c2 = c.with_updated_frame_function(sepia)
print(c2.get_frame(0.5).shape)
print("SUCCESS")
