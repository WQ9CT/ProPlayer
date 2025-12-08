import pystray
from pystray import MenuItem as item, Menu
from PIL import Image, ImageDraw
import threading
import os

class TrayHandler:
    def __init__(self, app_instance, on_show_window, on_quit, custom_icon_path=None):
        self.app = app_instance
        self.on_show = on_show_window
        self.on_quit = on_quit
        self.custom_icon_path = custom_icon_path
        self.icon = None
        self.thread = None

    def _truncate(self, text):
        """强制截断文本，防止超过 Windows 托盘限制 (128字符)"""
        if not text: return "Music Player"
        if len(text) > 120:
            return text[:117] + "..."
        return text

    def create_image(self):
        if self.custom_icon_path and os.path.exists(self.custom_icon_path):
            try: return Image.open(self.custom_icon_path)
            except: pass
        width = 64; height = 64
        color = getattr(self.app, 'accent_color', '#3B8ED0')
        image = Image.new('RGB', (width, height), (30, 30, 30))
        dc = ImageDraw.Draw(image)
        dc.ellipse((8, 8, 56, 56), fill="#1a1a1a", outline=color, width=3)
        dc.polygon([(24, 18), (24, 46), (46, 32)], fill=color)
        return image

    def get_title(self):
        """获取托盘悬停文字"""
        if hasattr(self.app, 'lbl_song_name'):
            try:
                song_name = self.app.lbl_song_name.cget("text")
                if song_name and song_name != "Music Player" and "Welcome" not in song_name:
                    return self._truncate(f"Playing: {song_name}")
            except: pass

        if hasattr(self.app, 'player') and self.app.player.current_song_path:
            name = os.path.basename(self.app.player.current_song_path)
            return self._truncate(f"Playing: {name}")
            
        return "Music Player"

    def safe_call(self, func, *args): 
        self.app.after(0, func, *args)

    def set_vol(self, val): 
        self.safe_call(self.app.on_volume_change, val)

    def toggle_loop(self):
        """切换循环模式的逻辑"""
        def _logic():
            # 如果当前不是单曲循环，则切换为单曲循环
            if self.app.playback_mode != "LoopOne":
                self.app.playback_mode = "LoopOne"
                if hasattr(self.app, 'btn_mode'):
                    color = getattr(self.app, 'accent_color', '#3B8ED0')
                    self.app.btn_mode.configure(text="🔂", text_color=color)
            # 否则切换回顺序播放
            else:
                self.app.playback_mode = "Order"
                if hasattr(self.app, 'btn_mode'):
                    self.app.btn_mode.configure(text="➡", text_color=("black", "white"))
        self.safe_call(_logic)

    def run(self):
        if self.icon is not None: return
        image = self.create_image()
        
        def T(key): return self.app.get_text(key)

        # --- 新增：动态获取菜单文字的函数 ---
        def get_loop_mode_text(menu_item):
            # 如果当前是单曲循环，提示用户点击后变回顺序
            if self.app.playback_mode == "LoopOne":
                return T('tray_goto_order')
            # 如果当前是顺序/随机，提示用户点击后变单曲
            return T('tray_goto_loop')

        menu = Menu(
            item(T('tray_show'), self.on_show, default=True),
            Menu.SEPARATOR,
            item(T('tray_play_pause'), lambda: self.safe_call(self.app.toggle_play)),
            item(T('tray_prev'), lambda: self.safe_call(self.app.play_prev)),
            item(T('tray_next'), lambda: self.safe_call(self.app.play_next)),
            Menu.SEPARATOR,
            
            # 使用函数 get_loop_mode_text 作为标题
            # Pystray 会在每次显示菜单时调用这个函数
            item(get_loop_mode_text, self.toggle_loop),
            
            item(T('tray_volume'), Menu(
                item('Mute (0%)', lambda: self.set_vol(0.0)),
                item('25%', lambda: self.set_vol(0.25)),
                item('50%', lambda: self.set_vol(0.50)),
                item('75%', lambda: self.set_vol(0.75)),
                item('100%', lambda: self.set_vol(1.0)),
            )),
            Menu.SEPARATOR,
            item(T('tray_quit'), self.on_quit)
        )

        self.icon = pystray.Icon("MusicPlayer", image, title=self.get_title(), menu=menu)
        self.thread = threading.Thread(target=self.icon.run, daemon=True)
        self.thread.start()

    def stop(self):
        if self.icon:
            self.icon.stop()
            self.icon = None

    def update_tooltip(self, text):
        if self.icon:
            try: 
                self.icon.title = self._truncate(text)
            except: pass