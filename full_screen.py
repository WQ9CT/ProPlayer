import customtkinter as ctk
from PIL import Image
import math
import threading
from music_sources import MusicSourceHandler 
import io
import requests

class FullScreenWindow(ctk.CTkToplevel):
    def __init__(self, master_app, player, accent_color):
        super().__init__()
        
        self.master_app = master_app
        self.player = player
        self.accent_color = accent_color
        self._update_loop_id = None
        
        # 引用防止垃圾回收
        self.current_image_ref = None
        
        self.title("Full Screen Mode")
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.configure(fg_color="black")
        
        self.bind("<Escape>", self.exit_fullscreen)
        self.bind("<FocusOut>", self.on_focus_out)
        
        self.setup_ui()
        self.start_update_loop()
        
        # 安全动画
        try: self.attributes("-alpha", 0.0)
        except: pass
        self.after(50, self.animate_fade_in)

    def setup_ui(self):
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.9, relheight=0.9)
        
        # 封面
        self.cover_label = ctk.CTkLabel(self.main_frame, text="", image=None)
        self.cover_label.pack(pady=(0, 30), expand=True)
        
        # 标题
        self.lbl_title = ctk.CTkLabel(self.main_frame, text="Ready", font=("Impact", 80), text_color="white", wraplength=1000)
        self.lbl_title.pack(pady=10)
        
        ctk.CTkLabel(self.main_frame, text=self.master_app.get_text("exit_full_screen"), font=("Arial", 14), text_color="gray50").pack(pady=(0, 50))

        self.ctrl_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.ctrl_frame.pack(fill="x", padx=100)
        
        self.progress_slider = ctk.CTkSlider(
            self.ctrl_frame, from_=0, to=100, 
            progress_color=self.accent_color, button_color="white", button_hover_color=self.accent_color, 
            height=20, command=self.on_seek
        )
        self.progress_slider.pack(fill="x", pady=(0, 30))
        
        btn_row = ctk.CTkFrame(self.ctrl_frame, fg_color="transparent")
        btn_row.pack()
        
        btn_font = ("Arial", 24)
        btn_size = 60
        
        self.btn_mode = ctk.CTkButton(btn_row, text="➡", width=50, height=50, font=("Arial", 20), fg_color="transparent", hover_color="#333", command=self.toggle_mode_fs)
        self.btn_mode.pack(side="left", padx=(0, 20))
        self.update_mode_icon() 

        ctk.CTkButton(btn_row, text="⏮", width=btn_size, height=btn_size, font=btn_font, fg_color="#222", hover_color="#333", command=self.master_app.play_prev).pack(side="left", padx=20)
        
        self.btn_play = ctk.CTkButton(btn_row, text="▶", width=80, height=80, font=("Arial", 40), fg_color=self.accent_color, hover_color=self.accent_color, corner_radius=40, command=self.smart_play)
        self.btn_play.pack(side="left", padx=20)
        
        ctk.CTkButton(btn_row, text="⏭", width=btn_size, height=btn_size, font=btn_font, fg_color="#222", hover_color="#333", command=self.master_app.play_next).pack(side="left", padx=20)

        ctk.CTkLabel(btn_row, text="🔈", font=("Arial", 20), text_color="gray").pack(side="left", padx=(40, 5))
        self.vol_slider = ctk.CTkSlider(btn_row, width=150, from_=0, to=1, progress_color=self.accent_color, command=self.on_volume_change)
        self.vol_slider.set(self.master_app.config['volume'])
        self.vol_slider.pack(side="left")

    def update_cover(self, path, song_title):
        # --- 修复 2: 强制清空旧图片/引用，防止显示上一首的封面 ---
        self.cover_label.configure(image=None)
        self.current_image_ref = None
        
        # 1. 本地封面
        cover_img = self.player.get_embedded_cover(path)
        if cover_img:
            self._display_cover(cover_img)
            return

        # 2. 网络封面
        auto_fetch = self.master_app.config.get("auto_fetch_cover", False)
        has_net = self.master_app.has_network
        
        if auto_fetch and has_net:
            # --- 修复 1: 使用原始标题搜索 (song_title 已经是从 gui 传来的 clean title) ---
            # 去除可能的干扰词，只搜 "歌名 song"
            clean_title = song_title.replace(".mp3", "").replace(".flac", "")
            query = f"{clean_title} song"
            threading.Thread(target=self._fetch_online_cover, args=(query,), daemon=True).start()

    def _fetch_online_cover(self, query):
        try:
            results = self.master_app.downloader.search(query, "yt", limit=1)
            if results:
                video_id = results[0]['id']
                thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
                resp = requests.get(thumbnail_url, timeout=5)
                if resp.status_code == 200:
                    img_data = io.BytesIO(resp.content)
                    pil_img = Image.open(img_data)
                    self.after(0, lambda: self._display_cover(pil_img))
        except: pass

    def _display_cover(self, pil_img):
        # --- 核心修复：保存引用，防止垃圾回收 ---
        try:
            pil_img = pil_img.resize((500, 500), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(500, 500))
            self.current_image_ref = ctk_img # <--- 关键！保存引用
            self.cover_label.configure(image=ctk_img)
        except: pass

    def start_update_loop(self):
        if not self.winfo_exists(): return
        try:
            current_title = self.master_app.lbl_song_name.cget("text")
            current_path = self.player.current_song_path
            if not hasattr(self, '_last_path') or self._last_path != current_path:
                self._last_path = current_path
                self.update_cover(current_path, current_title)
            self.lbl_title.configure(text=current_title)
        except: pass
        
        icon = "⏸" if self.player.is_playing() and not self.player.is_paused() else "▶"
        self.btn_play.configure(text=icon)
        self.update_mode_icon()
        
        if self.player.is_playing():
            try:
                curr = self.player.get_current_position()
                duration = self.player.get_current_length()
                if duration > 0:
                    self.progress_slider.configure(to=duration)
                    self.progress_slider.set(curr)
            except: pass
            
        current_vol = self.master_app.config['volume']
        if abs(self.vol_slider.get() - current_vol) > 0.01:
            self.vol_slider.set(current_vol)
            
        self._update_loop_id = self.after(500, self.start_update_loop)

    def animate_fade_in(self, step=0):
        try:
            if step <= 10:
                alpha = step / 10
                self.attributes("-alpha", alpha)
                self.after(16, lambda: self.animate_fade_in(step + 1))
            else: self.attributes("-alpha", 1.0)
        except: pass

    def smart_play(self):
        if not self.master_app.playlist: self.master_app.play_shuffle_all(); self.btn_play.configure(text="⏸")
        else: self.master_app.toggle_play()
    def toggle_mode_fs(self):
        self.master_app.toggle_mode(); self.update_mode_icon()
    def update_mode_icon(self):
        mode = self.master_app.playback_mode
        if mode == "Order": self.btn_mode.configure(text="➡", text_color="gray")
        elif mode == "LoopOne": self.btn_mode.configure(text="🔂", text_color=self.accent_color)
        elif mode == "Shuffle": self.btn_mode.configure(text="🔀", text_color=self.accent_color)
    def on_seek(self, val): self.master_app.on_seek_drag(val)
    def on_volume_change(self, val): self.master_app.on_volume_change(val)
    def on_focus_out(self, event): self.after(100, self.check_focus)
    def check_focus(self):
        if self.focus_displayof() is None: self.exit_fullscreen()
    def exit_fullscreen(self, event=None):
        if self._update_loop_id: self.after_cancel(self._update_loop_id)
        self.destroy()
        self.master_app.deiconify()