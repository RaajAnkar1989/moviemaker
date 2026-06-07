import os
import threading
import random
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from moviepy import VideoFileClip, TextClip, CompositeVideoClip, concatenate_videoclips, ColorClip, AudioClip, AudioFileClip, CompositeAudioClip, concatenate_audioclips, ImageClip
import moviepy.video.fx as vfx
import numpy as np

# Set appearance and theme
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class MovieMakerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("AI Movie Maker Pro")
        self.after(0, lambda: self.state('zoomed'))
        self.geometry("1100x850")

        # Variables
        self.selected_files = [] # List of dicts: {"path": p, "is_image": bool, "duration": float, "filter": str}
        self.background_audio_path = None
        self.processing = False
        self.title_pages = [{"text": "THE CINEMATIC JOURNEY", "color": "White", "size": 70}]
        self.end_pages = [{"text": "THE END", "color": "White", "size": 70}, {"text": "THANK YOU FOR WATCHING", "color": "White", "size": 70}]
        self.text_colors = ["White", "Yellow", "Red", "Cyan", "Green", "Orange", "Black"]
        self.bg_colors = {
            "Black": (0, 0, 0),
            "Dark Blue": (0, 0, 50),
            "Dark Red": (50, 0, 0),
            "Dark Green": (0, 50, 0),
            "Deep Purple": (48, 25, 52),
            "Slate": (47, 79, 79),
            "White": (255, 255, 255)
        }

        # UI Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        # Left Panel: Settings (Scrollable)
        self.left_panel = ctk.CTkScrollableFrame(self, width=350)
        self.left_panel.grid(row=0, column=0, rowspan=2, padx=20, pady=20, sticky="nsew")
        self.left_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.left_panel, text="Settings", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=10)

        # Multi-page Title Section
        ctk.CTkLabel(self.left_panel, text="Title Cards (Pages):", font=ctk.CTkFont(weight="bold")).pack(padx=10, pady=(10, 0), anchor="w")
        self.title_frame = ctk.CTkFrame(self.left_panel)
        self.title_frame.pack(padx=10, pady=5, fill="x")
        self.refresh_title_ui()
        ctk.CTkButton(self.left_panel, text="+ Add Title Page", command=self.add_title_page, height=25).pack(padx=10, pady=5)

        # Multi-page End Card Section
        ctk.CTkLabel(self.left_panel, text="End Credits (Pages):", font=ctk.CTkFont(weight="bold")).pack(padx=10, pady=(15, 0), anchor="w")
        self.end_frame = ctk.CTkFrame(self.left_panel)
        self.end_frame.pack(padx=10, pady=5, fill="x")
        self.refresh_end_ui()
        ctk.CTkButton(self.left_panel, text="+ Add Credit Page", command=self.add_end_page, height=25).pack(padx=10, pady=5)

        ctk.CTkLabel(self.left_panel, text="Card Background Color:").pack(padx=10, pady=(15, 0), anchor="w")
        self.color_var = ctk.StringVar(value="Black")
        self.color_menu = ctk.CTkComboBox(self.left_panel, values=list(self.bg_colors.keys()), variable=self.color_var)
        self.color_menu.pack(padx=10, pady=5, fill="x")

        # Aspect Ratio
        ctk.CTkLabel(self.left_panel, text="Aspect Ratio:").pack(padx=10, pady=(15, 0), anchor="w")
        self.aspect_var = ctk.StringVar(value="16:9 (Widescreen)")
        self.aspect_menu = ctk.CTkComboBox(self.left_panel, values=["16:9 (Widescreen)", "9:16 (Vertical)", "1:1 (Square)", "4:3 (Standard)"], variable=self.aspect_var)
        self.aspect_menu.pack(padx=10, pady=5, fill="x")

        # Audio Section
        ctk.CTkLabel(self.left_panel, text="Background Music:", font=ctk.CTkFont(weight="bold")).pack(padx=10, pady=(20, 0), anchor="w")
        self.audio_label = ctk.CTkLabel(self.left_panel, text="No audio selected", font=ctk.CTkFont(size=11), wraplength=300)
        self.audio_label.pack(padx=10, pady=5)
        self.audio_btn = ctk.CTkButton(self.left_panel, text="🎵 Select Audio", command=self.select_audio, fg_color="transparent", border_width=2)
        self.audio_btn.pack(padx=10, pady=5, fill="x")
        
        # Volume
        ctk.CTkLabel(self.left_panel, text="Video Vol:").pack(padx=10, pady=(10, 0), anchor="w")
        self.video_volume_slider = ctk.CTkSlider(self.left_panel, from_=0, to=2)
        self.video_volume_slider.set(1.0)
        self.video_volume_slider.pack(padx=10, pady=5, fill="x")
        
        # Cinematic Effects
        ctk.CTkLabel(self.left_panel, text="Industry Transitions:", font=ctk.CTkFont(weight="bold")).pack(padx=10, pady=(20, 0), anchor="w")
        self.transition_var = ctk.StringVar(value="Cross Dissolve")
        self.transition_menu = ctk.CTkComboBox(self.left_panel, values=[
            "Hard Cut", "Cross Dissolve", "Fade In/Out", "Whip Pan", 
            "Zoom In/Out", "Glitch", "White Flash", "L-Cut", "J-Cut", "Random"
        ], variable=self.transition_var)
        self.transition_menu.pack(padx=10, pady=5, fill="x")

        self.watermark_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(self.left_panel, text="Remove Watermark (Smart Zoom)", variable=self.watermark_var, font=ctk.CTkFont(size=11)).pack(padx=10, pady=10, anchor="w")

        ctk.CTkLabel(self.left_panel, text="").pack(pady=10)
        self.generate_button = ctk.CTkButton(self.left_panel, text="🚀 Generate Movie", command=self.start_processing, state="disabled", height=50, font=ctk.CTkFont(size=16, weight="bold"))
        self.generate_button.pack(padx=10, pady=20, fill="x")

        # Right Panel: Video List
        self.right_panel = ctk.CTkFrame(self)
        self.right_panel.grid(row=0, column=1, rowspan=2, padx=(0, 20), pady=20, sticky="nsew")
        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self.right_panel, text="Media Sequence", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, pady=10)
        self.scroll_frame = ctk.CTkScrollableFrame(self.right_panel)
        self.scroll_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        self.list_controls = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.list_controls.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        ctk.CTkButton(self.list_controls, text="➕ Add Media", command=self.add_files).pack(side="left", padx=5)
        ctk.CTkButton(self.list_controls, text="🗑️ Clear All", command=self.clear_files, fg_color="#d32f2f").pack(side="right", padx=5)

        # Progress
        self.status_frame = ctk.CTkFrame(self, height=60)
        self.status_frame.grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="ew")
        self.status_frame.grid_columnconfigure(0, weight=1)
        self.progress_bar = ctk.CTkProgressBar(self.status_frame)
        self.progress_bar.grid(row=0, column=0, padx=20, pady=(10, 0), sticky="ew")
        self.progress_bar.set(0)
        self.status_label = ctk.CTkLabel(self.status_frame, text="Ready")
        self.status_label.grid(row=1, column=0, padx=20, pady=(0, 10))

    def refresh_title_ui(self):
        for widget in self.title_frame.winfo_children(): widget.destroy()
        for i, page in enumerate(self.title_pages):
            row = ctk.CTkFrame(self.title_frame)
            row.pack(fill="x", pady=5, padx=5)
            txt = ctk.CTkTextbox(row, height=60)
            txt.insert("1.0", page["text"])
            txt.pack(side="top", fill="x", expand=True, padx=5, pady=5)
            txt.bind("<FocusOut>", lambda e, idx=i: self.update_title_data(idx, "text", e.widget.get("1.0", "end-1c")))
            ctrls = ctk.CTkFrame(row, fg_color="transparent")
            ctrls.pack(side="top", fill="x", padx=5, pady=2)
            ctk.CTkLabel(ctrls, text="Size:", font=ctk.CTkFont(size=10)).pack(side="left", padx=2)
            size_entry = ctk.CTkEntry(ctrls, width=40, height=20, font=ctk.CTkFont(size=10))
            size_entry.insert(0, str(page["size"]))
            size_entry.pack(side="left", padx=2)
            size_entry.bind("<FocusOut>", lambda e, idx=i: self.update_title_data(idx, "size", e.widget.get()))
            ctk.CTkLabel(ctrls, text="Color:", font=ctk.CTkFont(size=10)).pack(side="left", padx=(10, 2))
            color_menu = ctk.CTkComboBox(ctrls, values=self.text_colors, width=80, height=20, font=ctk.CTkFont(size=10))
            color_menu.set(page["color"])
            color_menu.pack(side="left", padx=2)
            color_menu.configure(command=lambda val, idx=i: self.update_title_data(idx, "color", val))
            ctk.CTkButton(ctrls, text="✕", width=25, height=20, command=lambda idx=i: self.remove_title_page(idx), fg_color="#d32f2f").pack(side="right", padx=2)

    def refresh_end_ui(self):
        for widget in self.end_frame.winfo_children(): widget.destroy()
        for i, page in enumerate(self.end_pages):
            row = ctk.CTkFrame(self.end_frame)
            row.pack(fill="x", pady=5, padx=5)
            txt = ctk.CTkTextbox(row, height=60)
            txt.insert("1.0", page["text"])
            txt.pack(side="top", fill="x", expand=True, padx=5, pady=5)
            txt.bind("<FocusOut>", lambda e, idx=i: self.update_end_data(idx, "text", e.widget.get("1.0", "end-1c")))
            ctrls = ctk.CTkFrame(row, fg_color="transparent")
            ctrls.pack(side="top", fill="x", padx=5, pady=2)
            ctk.CTkLabel(ctrls, text="Size:", font=ctk.CTkFont(size=10)).pack(side="left", padx=2)
            size_entry = ctk.CTkEntry(ctrls, width=40, height=20, font=ctk.CTkFont(size=10))
            size_entry.insert(0, str(page["size"]))
            size_entry.pack(side="left", padx=2)
            size_entry.bind("<FocusOut>", lambda e, idx=i: self.update_end_data(idx, "size", e.widget.get()))
            ctk.CTkLabel(ctrls, text="Color:", font=ctk.CTkFont(size=10)).pack(side="left", padx=(10, 2))
            color_menu = ctk.CTkComboBox(ctrls, values=self.text_colors, width=80, height=20, font=ctk.CTkFont(size=10))
            color_menu.set(page["color"])
            color_menu.pack(side="left", padx=2)
            color_menu.configure(command=lambda val, idx=i: self.update_end_data(idx, "color", val))
            ctk.CTkButton(ctrls, text="✕", width=25, height=20, command=lambda idx=i: self.remove_end_page(idx), fg_color="#d32f2f").pack(side="right", padx=2)

    def add_title_page(self): self.title_pages.append({"text": "", "color": "White", "size": 70}); self.refresh_title_ui()
    def remove_title_page(self, idx): 
        if len(self.title_pages) > 1: self.title_pages.pop(idx); self.refresh_title_ui()
    def update_title_data(self, idx, key, val):
        if key == "size":
            try: self.title_pages[idx][key] = int(val)
            except: pass
        else: self.title_pages[idx][key] = val

    def add_end_page(self): self.end_pages.append({"text": "", "color": "White", "size": 70}); self.refresh_end_ui()
    def remove_end_page(self, idx): 
        if len(self.end_pages) > 1: self.end_pages.pop(idx); self.refresh_end_ui()
    def update_end_data(self, idx, key, val):
        if key == "size":
            try: self.end_pages[idx][key] = int(val)
            except: pass
        else: self.end_pages[idx][key] = val

    def select_audio(self):
        file = filedialog.askopenfilename(filetypes=[("Audio", "*.mp3 *.wav *.m4a")])
        if file: self.background_audio_path = file; self.audio_label.configure(text=os.path.basename(file))

    def add_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Media Files", "*.mp4 *.mov *.png *.jpg *.jpeg")])
        if files:
            for f in files: 
                if not any(item["path"] == f for item in self.selected_files):
                    is_img = f.lower().endswith(('.png', '.jpg', '.jpeg'))
                    self.selected_files.append({"path": f, "is_image": is_img, "duration": 5, "filter": "None"})
            self.refresh_video_list(); self.generate_button.configure(state="normal")

    def clear_files(self): self.selected_files = []; self.refresh_video_list(); self.generate_button.configure(state="disabled")

    def refresh_video_list(self):
        for widget in self.scroll_frame.winfo_children(): widget.destroy()
        for i, item in enumerate(self.selected_files):
            f = item["path"]
            is_img = item.get("is_image", False)
            row = ctk.CTkFrame(self.scroll_frame)
            row.pack(fill="x", pady=2, padx=5)
            
            top_row = ctk.CTkFrame(row, fg_color="transparent")
            top_row.pack(fill="x", padx=5, pady=(5,0))
            
            ctk.CTkLabel(top_row, text=f"{i+1}.", width=30).pack(side="left", padx=5)
            ctk.CTkLabel(top_row, text=os.path.basename(f), anchor="w").pack(side="left", padx=5, fill="x", expand=True)
            ctk.CTkButton(top_row, text="▲", width=30, command=lambda idx=i: self.move_file(idx, -1)).pack(side="left", padx=2)
            ctk.CTkButton(top_row, text="▼", width=30, command=lambda idx=i: self.move_file(idx, 1)).pack(side="left", padx=2)
            ctk.CTkButton(top_row, text="✕", width=30, command=lambda idx=i: self.remove_file(idx), fg_color="#d32f2f").pack(side="left", padx=2)
            
            bot_row = ctk.CTkFrame(row, fg_color="transparent")
            bot_row.pack(fill="x", padx=5, pady=(0,5))
            
            if is_img:
                ctk.CTkLabel(bot_row, text="Duration(s):", font=ctk.CTkFont(size=11)).pack(side="left", padx=5)
                dur_entry = ctk.CTkEntry(bot_row, width=40, height=20, font=ctk.CTkFont(size=11))
                dur_entry.insert(0, str(item["duration"]))
                dur_entry.pack(side="left", padx=5)
                dur_entry.bind("<FocusOut>", lambda e, idx=i: self.update_file_opt(idx, "duration", e.widget.get()))
            
            ctk.CTkLabel(bot_row, text="Filter:", font=ctk.CTkFont(size=11)).pack(side="left", padx=5)
            filter_menu = ctk.CTkComboBox(bot_row, values=["None", "B&W", "Sepia", "Vibrant", "Dim"], width=80, height=20, font=ctk.CTkFont(size=11))
            filter_menu.set(item["filter"])
            filter_menu.pack(side="left", padx=5)
            filter_menu.configure(command=lambda val, idx=i: self.update_file_opt(idx, "filter", val))

    def update_file_opt(self, idx, key, val):
        if key == "duration":
            try: self.selected_files[idx][key] = float(val)
            except: pass
        else: self.selected_files[idx][key] = val

    def move_file(self, idx, dir):
        new_idx = idx + dir
        if 0 <= new_idx < len(self.selected_files):
            self.selected_files[idx], self.selected_files[new_idx] = self.selected_files[new_idx], self.selected_files[idx]
            self.refresh_video_list()

    def remove_file(self, idx): 
        self.selected_files.pop(idx); self.refresh_video_list()
        if not self.selected_files: self.generate_button.configure(state="disabled")

    def make_silence(self, duration):
        return AudioClip(lambda t: np.zeros((len(t) if isinstance(t, np.ndarray) else 1, 2)), duration=duration, fps=44100)

    def create_text_clip(self, text, duration=4, font_size=70, text_color='white'):
        rgb = self.bg_colors.get(self.color_var.get(), (0, 0, 0))
        target_ratio_str = self.aspect_var.get()
        ratio_map = {"16:9 (Widescreen)": 16/9, "9:16 (Vertical)": 9/16, "1:1 (Square)": 1.0, "4:3 (Standard)": 4/3}
        target_ratio = ratio_map.get(target_ratio_str, 16/9)
        res_h = 720
        target_size = (int(res_h * target_ratio), res_h)

        bg = ColorClip(size=target_size, color=rgb).with_duration(duration)
        try:
            txt = TextClip(text=text, font_size=font_size, color=text_color.lower(), size=target_size, method='caption').with_duration(duration).with_position('center')
        except:
            txt = TextClip(text=text, font_size=font_size, color='white', size=target_size, method='caption').with_duration(duration).with_position('center')
            
        return CompositeVideoClip([bg, txt]).with_audio(self.make_silence(duration))

    def apply_color_filter(self, clip, filter_name):
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

    def start_processing(self):
        self.processing = True; self.generate_button.configure(state="disabled")
        threading.Thread(target=self.process_video, daemon=True).start()

    def update_status(self, text, progress): self.status_label.configure(text=text); self.progress_bar.set(progress)

    def apply_advanced_transition(self, clip, style):
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

    def process_video(self):
        try:
            out = filedialog.asksaveasfilename(defaultextension=".mp4", initialfile="movie_pro.mp4")
            if not out: return self.reset_ui()
            
            v_vol = self.video_volume_slider.get(); trans = self.transition_var.get(); do_zoom = self.watermark_var.get()
            
            target_ratio_str = self.aspect_var.get()
            ratio_map = {"16:9 (Widescreen)": 16/9, "9:16 (Vertical)": 9/16, "1:1 (Square)": 1.0, "4:3 (Standard)": 4/3}
            target_ratio = ratio_map.get(target_ratio_str, 16/9)
            res_h = 720
            
            clips = []
            for page in self.title_pages:
                text = page["text"].strip()
                if text:
                    c = self.create_text_clip(text, font_size=page["size"], text_color=page["color"])
                    if trans != "Hard Cut": c = self.apply_advanced_transition(c, trans)
                    clips.append(c)
                    
            for i, item in enumerate(self.selected_files):
                f = item["path"]
                is_img = item.get("is_image", False)
                dur = item.get("duration", 5)
                fltr = item.get("filter", "None")
                
                self.update_status(f"Processing clip {i+1}...", 0.1 + (i/len(self.selected_files))*0.6)
                
                if is_img:
                    c = ImageClip(f).with_duration(dur)
                    c = c.with_effects([vfx.Resize(lambda t: 1 + 0.1 * (t / c.duration))])
                else:
                    c = VideoFileClip(f)

                w, h = c.size
                clip_ratio = w / h
                if abs(clip_ratio - target_ratio) > 0.05:
                    if clip_ratio > target_ratio:
                        new_w = int(h * target_ratio)
                        c = c.with_effects([vfx.Crop(x_center=w/2, y_center=h/2, width=new_w, height=h)])
                    else:
                        new_h = int(w / target_ratio)
                        c = c.with_effects([vfx.Crop(x_center=w/2, y_center=h/2, width=w, height=new_h)])

                if c.h != res_h: 
                    c = c.with_effects([vfx.Resize(height=res_h)])
                
                if not is_img and do_zoom:
                    w, h = c.size
                    c = c.with_effects([vfx.Crop(x1=int(w*0.1), y1=int(h*0.1), width=int(w*0.8), height=int(h*0.8)), vfx.Resize(height=res_h)])

                c = self.apply_color_filter(c, fltr)
                if trans != "Hard Cut": c = self.apply_advanced_transition(c, trans)
                
                if not is_img:
                    c = c.with_audio(c.audio.with_volume_scaled(v_vol) if c.audio else self.make_silence(c.duration))
                else:
                    c = c.with_audio(self.make_silence(c.duration))
                    
                clips.append(c)
                
            for page in self.end_pages:
                text = page["text"].strip()
                if text:
                    c = self.create_text_clip(text, font_size=page["size"], text_color=page["color"])
                    if trans != "Hard Cut": c = self.apply_advanced_transition(c, trans)
                    clips.append(c)
                    
            self.update_status("Stitching...", 0.85)
            padding = -1 if trans in ["Cross Dissolve", "Whip Pan", "Zoom In/Out", "Glitch", "White Flash", "Random", "J-Cut", "L-Cut"] else 0
            final = concatenate_videoclips(clips, method="compose", padding=padding)
            
            if self.background_audio_path:
                self.update_status("Mixing audio...", 0.9)
                bg = AudioFileClip(self.background_audio_path)
                if bg.duration < final.duration: bg = concatenate_audioclips([bg] * int(np.ceil(final.duration/bg.duration)))
                bg = bg.subclipped(0, final.duration).with_volume_scaled(0.5)
                final = final.with_audio(CompositeAudioClip([final.audio, bg]))
                
            self.update_status("Rendering...", 0.95)
            final.write_videofile(out, fps=24, codec="libx264", audio_codec="aac", logger=None)
            for c in clips: c.close()
            final.close()
            self.update_status("✅ Ready!", 1.0); messagebox.showinfo("Done", f"Saved to {out}")
        except Exception as e: messagebox.showerror("Error", str(e))
        self.reset_ui()

    def reset_ui(self): self.processing = False; self.generate_button.configure(state="normal"); self.status_label.configure(text="Ready"); self.progress_bar.set(0)

if __name__ == "__main__": app = MovieMakerApp(); app.mainloop()
