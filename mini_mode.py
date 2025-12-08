import customtkinter as ctk
import tkinter as tk # 引入原生 tkinter
import os
import math

class MiniPlayerWindow(tk.Toplevel):
    def __init__(self, master_app, player, restore_callback, accent_color="#3B8ED0"):
        super().__init__()
        
        self.master_app = master_app
        self.player = player
        self.restore_callback = restore_callback
        self.accent_color = accent_color
        self._update_loop_id = None
        self.can_use_alpha = True
        
        self.title("Mini Player")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        
        # 1. 初始隐藏 (防止闪烁)
        self.withdraw()
        
        # 2. 定义透明键色
        self.transparent_key = "#000001"
        
        # 3. 设置原生背景色 (修复 fg_color 报错)
        try:
            self.config(bg=self.transparent_key)
        except: pass

        # 4. 尝试设置透明色抠图
        try:
            self.attributes("-transparentcolor", self.transparent_key)
        except:
            # 不支持则回退深色
            self.config(bg="#1a1a1a")
            self.can_use_alpha = False

        # 屏幕定位
        try:
            screen_w = self.winfo_screenwidth()
            width = 340
            height = 120
            x_pos = screen_w - width - 30
            y_pos = 30
            self.geometry(f"{width}x{height}+{x_pos}+{y_pos}")
        except: pass

        self._offsetx = 0
        self._offsety = 0

        self.setup_ui()
        self.start_update_loop()
        
        # 5. 准备动画
        # 先设为透明
        if self._safe_set_alpha(0.0):
            # 显示窗口 (此时它是透明的)
            self.deiconify()
            # 开始淡入
            self.after(50, self.animate_fade_in)
        else:
            self.can_use_alpha = False
            self.deiconify()

    def _safe_set_alpha(self, value):
        if not self.can_use_alpha: return False
        try:
            self.attributes("-alpha", value)
            return True
        except:
            self.can_use_alpha = False
            return False

    def animate_fade_in(self, step=0):
        if not self.can_use_alpha: return
        try:
            if step <= 15:
                alpha = 1.0 - math.pow(1 - (step / 15), 3)
                if self._safe_set_alpha(alpha):
                    # 原生窗口不需要 update_idletasks 通常也能流畅
                    self.after(16, lambda: self.animate_fade_in(step + 1))
            else:
                self._safe_set_alpha(1.0)
        except: 
            self._safe_set_alpha(1.0)

    def close_with_fade(self):
        if self._update_loop_id:
            try: self.after_cancel(self._update_loop_id)
            except: pass
            self._update_loop_id = None
        self.animate_fade_out(self._destroy_and_restore)

    def animate_fade_out(self, callback, step=0):
        if not self.can_use_alpha:
            callback()
            return

        try:
            if step <= 15:
                alpha = 1.0 - (step / 15)
                if self._safe_set_alpha(alpha):
                    self.after(16, lambda: self.animate_fade_out(callback, step + 1))
                else:
                    callback()
            else:
                callback()
        except:
            callback()
            
    def restore_main_window(self):
        self.close_with_fade()

    def _destroy_and_restore(self):
        self.destroy()
        self.restore_callback()

    def setup_ui(self):
        container_bg = ("white", "#1a1a1a")
        
        # 内部容器依然是 CTkFrame，可以使用 fg_color
        self.container = ctk.CTkFrame(
            self, 
            fg_color=container_bg, 
            bg_color=self.transparent_key, 
            border_width=2, 
            border_color=self.accent_color, 
            corner_radius=20
        )
        self.container.pack(fill="both", expand=True, padx=0, pady=0)
        
        self.container.bind("<Button-1>", self.start_move)
        self.container.bind("<B1-Motion>", self.do_move)

        top_row = ctk.CTkFrame(self.container, fg_color="transparent", height=30)
        top_row.pack(fill="x", padx=15, pady=(10, 0))
        top_row.bind("<Button-1>", self.start_move)
        top_row.bind("<B1-Motion>", self.do_move)

        text_col = ("black", "white")
        self.lbl_name = ctk.CTkLabel(top_row, text="Ready", font=("Arial", 13, "bold"), text_color=text_col, width=200, anchor="w")
        self.lbl_name.pack(side="left")
        self.lbl_name.bind("<Button-1>", self.start_move)
        self.lbl_name.bind("<B1-Motion>", self.do_move)

        btn_fg = ("#e0e0e0", "#333333")
        btn_hover = ("#d0d0d0", "#444444")
        restore_btn = ctk.CTkButton(top_row, text="⤢", width=24, height=24, fg_color=btn_fg, hover_color=btn_hover, text_color=text_col, corner_radius=8, font=("Arial", 14), command=self.restore_main_window)
        restore_btn.pack(side="right")

        ctrl_row = ctk.CTkFrame(self.container, fg_color="transparent")
        ctrl_row.pack(fill="x", padx=15, pady=(5, 0))
        ctrl_row.bind("<Button-1>", self.start_move)
        ctrl_row.bind("<B1-Motion>", self.do_move)

        btn_style = {"width": 32, "height": 32, "fg_color": "transparent", "text_color": ("gray40", "#cccccc"), "hover_color": ("#e0e0e0", "#333333"), "corner_radius": 16, "font": ("Arial", 18)}

        ctk.CTkButton(ctrl_row, text="⏮", command=self.master_app.play_prev, **btn_style).pack(side="left", padx=(0, 5))
        
        self.btn_play = ctk.CTkButton(ctrl_row, text="▶", width=38, height=38, fg_color=self.accent_color, hover_color=self.accent_color, text_color="white", corner_radius=19, font=("Arial", 20), command=self.master_app.toggle_play)
        self.btn_play.pack(side="left", padx=8)
        
        ctk.CTkButton(ctrl_row, text="⏭", command=self.master_app.play_next, **btn_style).pack(side="left", padx=5)

        slider_btn_col = ("gray50", "white")
        self.vol_slider = ctk.CTkSlider(ctrl_row, from_=0, to=1, height=14, width=100, progress_color=self.accent_color, button_color=slider_btn_col, button_hover_color=self.accent_color, command=self.on_volume_change)
        self.vol_slider.set(self.master_app.config['volume'])
        self.vol_slider.pack(side="right", padx=5)

    def start_move(self, event):
        self._offsetx = event.x; self._offsety = event.y
    def do_move(self, event):
        x = self.winfo_x() + (event.x - self._offsetx)
        y = self.winfo_y() + (event.y - self._offsety)
        self.geometry(f"+{x}+{y}")
    def on_volume_change(self, value):
        self.master_app.on_volume_change(value)

    def start_update_loop(self):
        if not self.winfo_exists(): return
        if self.player.current_song_path:
            try:
                current_title = self.master_app.lbl_song_name.cget("text")
                welcome_msg = self.master_app.get_text("welcome")
                if not current_title or current_title == welcome_msg:
                    self.lbl_name.configure(text="Mini Player")
                else:
                    if len(current_title) > 25: current_title = current_title[:22] + "..."
                    self.lbl_name.configure(text=current_title)
            except: self.lbl_name.configure(text="Music Player")
        else: self.lbl_name.configure(text="Music Player")
        icon = "⏸" if self.player.is_playing() and not self.player.is_paused() else "▶"
        self.btn_play.configure(text=icon)
        current_vol = self.master_app.config['volume']
        if hasattr(self, 'vol_slider') and abs(self.vol_slider.get() - current_vol) > 0.01: self.vol_slider.set(current_vol)
        self._update_loop_id = self.after(500, self.start_update_loop)