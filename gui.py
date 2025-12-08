import os
import random
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, Menu
import customtkinter as ctk
from PIL import Image, ImageFilter
import sys
import math
import shutil
import time
import io
import threading
import socket
import mutagen 

from config_manager import ConfigManager
from audio_player import AudioPlayer
from tray_handler import TrayHandler
from mini_mode import MiniPlayerWindow
from music_sources import MusicSourceHandler
from timer import SleepTimer, TimerInputDialog
from full_screen import FullScreenWindow
from startup import StartupScreen
from playlist_manager import PlaylistManager

if os.name == 'nt':
    import winreg

COLOR_THEMES = {
    "Default Blue": "#3B8ED0",
    "Sakura Pink": "#F48FB1",
    "Cyber Cyan": "#00E5FF",
    "Emerald Green": "#00C853",
    "Royal Gold": "#FFD700",
    "Violet Purple": "#AA00FF",
    "Sunset Orange": "#FF6D00",
    "Midnight Red": "#D32F2F",
    "Neon Lime": "#C6FF00"
}

class MusicPlayerGUI(ctk.CTk):
    def reorder_playlist_item(self, pl_name, index, direction):
        """
        独立处理歌单排序，防止闭包作用域导致的索引错误
        direction: -1 (上/前), 1 (下/后)
        """
        # 1. 重新加载最新列表
        items = PlaylistManager.load_playlist(pl_name)
        
        new_idx = index + direction
        
        # 2. 检查边界
        if 0 <= new_idx < len(items):
            # 3. 交换
            items[index], items[new_idx] = items[new_idx], items[index]
            
            # 4. 保存
            PlaylistManager.save_playlist(pl_name, items)
            
            # 5. 刷新视图
            self.load_playlist_view(pl_name)
    
    def open_full_screen(self):
        """打开全屏专注模式"""
        # 创建全屏窗口
        FullScreenWindow(self, self.player, self.accent_color)
        
        # 可选：隐藏主窗口（如果不隐藏，全屏覆盖在上面也可以）
        # self.withdraw() 
        # 建议不 withdraw，因为全屏窗口销毁时逻辑更简单，
        # 而且 FullScreenWindow 设置了 FocusOut 自动退出，不隐藏主窗口切换更自然。

    def is_audio_file(self, filename):
        """判断文件是否为支持的音频格式"""
        return filename.lower().endswith(('.mp3', '.wav', '.ogg', '.flac', '.m4a'))
    
    def __init__(self):
        super().__init__()
        
        # 1. 隐藏主窗口
        self.withdraw() 
        self.can_use_alpha = True
        
        # 2. 预加载少量配置
        temp_config = ConfigManager.load_config()
        accent = temp_config.get("accent_color", "#3B8ED0")

        #  获取版本号 ---
        self.app_version = ConfigManager.get_app_version()
        if not self.app_version: self.app_version = "" # 防止 None
        #  传给 StartupScreen ---
        # 3. 启动画面 (只在这里创建！)
        self.splash = StartupScreen(self, accent, "Python Pro Player", self.app_version)
        
        # --- 进度 10%: 加载配置 ---
        self.splash.set_status("Loading configurations...", 0.1)
        self.config = temp_config
        self.current_theme_mode = self.config.get("theme_mode", "System")
        self.accent_color = accent
        
        # --- 进度 20%: 加载语言包 ---
        self.splash.set_status("Loading languages...", 0.2)
        self.all_languages = ConfigManager.load_language_pack()
        self.current_lang_code = self.config.get("language", "zh")
        self.lang = self.all_languages.get(self.current_lang_code, {})
        
        # --- 进度 30%: 加载缓存 ---
        self.splash.set_status("Loading database...", 0.3)
        self.online_song_cache = ConfigManager.load_online_cache()
        
        # --- 进度 40%: 网络检测 ---
        self.splash.set_status("Connecting to network...", 0.4)
        self.has_network = self.check_network_connection()
        
        # --- 进度 50%: 设置外观 ---
        self.splash.set_status("Applying theme...", 0.5)
        ctk.set_appearance_mode(self.current_theme_mode)
        ctk.set_default_color_theme("dark-blue")
        
        self.title(self.get_text("app_title"))
        self.geometry("1100x750")
        self.load_app_resources()

        # --- 进度 60%: 初始化音频引擎 (最耗时) ---
        self.splash.set_status("Initializing Audio Engine (VLC)...", 0.6)
        self.player = AudioPlayer()
        
        # 变量初始化
        self.playlist = []
        self.current_index = 0
        self.playback_mode = "Order"
        self.current_song_duration = 0 
        self.duration_locked = False
        self.last_seek_time = 0
        self.is_switching_song = False
        self.online_titles = {} 
        self.settings_window = None
        self.timer_window = None
        self._monitor_loop_id = None
        self._progress_loop_id = None

        # --- 进度 70%: 加载模块 ---
        self.splash.set_status("Loading modules...", 0.7)
        self.timer_logic = SleepTimer()
        self.downloader = MusicSourceHandler(ConfigManager.get_download_path())
        
        self.song_widgets = [] 
        self.folder_widgets = []
        self.star_widgets = []
        self.nav_buttons = []
        
        self.tray_handler = None 
        self.mini_window = None 
        self.current_view = "Home"
        self.current_path_memory = None 
        
        self.player.set_volume(self.config['volume'])

        # --- 进度 80%: 构建界面 ---
        self.splash.set_status("Building Interface...", 0.8)
        self.setup_main_ui()
        self.init_background()
        self.update_treeview_style()
        
        # --- 进度 90%: 渲染内容 ---
        self.splash.set_status("Loading library...", 0.9)
        self.refresh_sidebar_tree()
        self.show_home_view()
        
        self.protocol("WM_DELETE_WINDOW", self.on_close_window)
        self.monitor_music_status()
        self.update_progress_loop()
        self.bind_hotkeys()
        
        if self.config['minimize_to_tray']: self.start_tray_icon()

        # --- 进度 100%: 完成 ---
        self.splash.set_status("Ready!", 1.0)
        
        # 关闭启动画面 (带淡出)
        self.splash.close()
        
        # 稍微延迟后，主界面淡入
        self.after(500, self.animate_fade_in_elastic)

    # 临时的 get_text，用于 init 阶段
    def get_text_temp(self, config, key):
        lang_code = config.get("language", "zh")
        # 这里简单处理，因为还没加载完整语言包
        if lang_code == "zh":
            return "正在加载..." if key == "loading_app" else key
        return "Loading..."
        
    # --- 1. 增强版网络检测 ---
    def check_network_connection(self):
        """检测网络连接 (尝试连接 Google 和 Cloudflare DNS)"""
        try:
            # 尝试 Google DNS
            socket.create_connection(("8.8.8.8", 53), timeout=1.5)
            return True
        except:
            try:
                # 备用：Cloudflare DNS
                socket.create_connection(("1.1.1.1", 53), timeout=1.5)
                return True
            except:
                return False


        # 不需要启动动画，直接运行即可
    def _safe_set_alpha(self, value):
        """
        尝试设置透明度。
        如果系统不支持 (TclError)，永久禁用动画功能，防止崩溃。
        """
        if not self.can_use_alpha:
            return False # 熔断器已跳闸，不再尝试

        try:
            self.attributes("-alpha", value)
            return True
        except Exception:
            print("系统不支持透明度，已禁用动画效果。")
            self.can_use_alpha = False # 关掉开关
            return False

    def animate_fade_in_elastic(self, step=0):
        # 第一步：准备
        if step == 0:
            self.deiconify()
            self.lift()
            if not self._safe_set_alpha(0.0):
                return

        if not self.can_use_alpha: return

        try:
            # 增加步数到 25，让变化更细腻
            if step <= 25:
                # 使用 ease-out 曲线 (alpha 变化快 -> 慢)
                alpha = 1.0 - math.pow(1 - (step / 25), 3)
                self.attributes("-alpha", alpha)
                
                # --- 关键：强制刷新 UI，确保每一帧都被肉眼看到 ---
                self.update_idletasks() 
                
                # 间隔 8ms (~120fps)，极其丝滑
                self.after(8, lambda: self.animate_fade_in_elastic(step + 1))
            else: 
                self.attributes("-alpha", 1.0)
        except:
            # 容错
            try: self.attributes("-alpha", 1.0)
            except: pass

    def animate_fade_out(self, callback, step=0):
        if not self.can_use_alpha:
            callback()
            return

        try:
            if step <= 20:
                alpha = 1.0 - math.pow(step / 20, 2)
                self.attributes("-alpha", alpha)
                self.update_idletasks() # 关键
                self.after(8, lambda: self.animate_fade_out(callback, step + 1))
            else:
                callback()
        except:
            callback()

    def animate_fade_out(self, callback, step=0):
        try:
            if step <= 20: # 增加步数 (15 -> 20)
                alpha = 1.0 - math.pow(step / 20, 2) # 使用二次曲线，更自然
                self.attributes("-alpha", alpha)
                
                # --- 优化：移除 update_idletasks() ---
                
                self.after(10, lambda: self.animate_fade_out(callback, step + 1))
            else:
                # 动画结束，执行回调 (隐藏或退出)
                callback()
        except:
            callback()

    def get_text(self, key):
        val = self.lang.get(key)
        if val: return val
        en_lang = self.all_languages.get("en", {})
        val = en_lang.get(key)
        if val: return val
        return key

    def load_app_resources(self):
        icon_path = ConfigManager.get_appdata_path("icon.ico")
        if os.path.exists(icon_path):
            try: self.iconbitmap(icon_path)
            except: pass
        self.tray_icon_path = ConfigManager.get_appdata_path("tray.png")

    def init_background(self):
        bg_candidates = ["background.jpg", "background.png"]
        appdata_bg = None
        for name in bg_candidates:
            p = ConfigManager.get_appdata_path(name)
            if os.path.exists(p):
                appdata_bg = p
                break
        final_bg = appdata_bg if appdata_bg else self.config.get('bg_image')
        if final_bg and os.path.exists(final_bg): self.update_background(final_bg)
        else: self.right_panel.configure(fg_color=("white", "#181818"))

    # --- 移除所有动画函数 ---

    def animate_button_press(self, widget):
        # 这个只改颜色，不涉及 alpha，可以保留
        try:
            orig_color = widget.cget("fg_color")
            widget.configure(fg_color="gray50")
            self.after(100, lambda: widget.configure(fg_color=orig_color))
        except: pass

    def _on_key_press(self, event, command):
        """
        统一按键处理：如果在打字，忽略快捷键；否则执行命令。
        """
        try:
            # 获取当前拥有焦点的组件
            focused_widget = self.focus_get()
            
            # 检查该组件是否是输入框 (Tkinter 的 Entry)
            # 注意：CTkEntry 的底层核心就是 tkinter.Entry
            if isinstance(focused_widget, tk.Entry):
                # 如果正在输入框里，什么都不做，让系统处理打字
                return
            
            # 同样，如果是文本域 (Text) 也要忽略（虽然目前没用到 Text 组件）
            if isinstance(focused_widget, tk.Text):
                return

            # 如果焦点不在输入框，执行快捷键命令
            command()
        except:
            pass

    def bind_hotkeys(self):
        """绑定键盘快捷键 (带防误触检测)"""
        # 使用 lambda e: ... 接收事件并传递给处理函数
        
        # 空格：播放/暂停
        self.bind("<space>", lambda e: self._on_key_press(e, self.toggle_play))
        
        # 左键：上一首 (防止在输入框移动光标时切歌)
        self.bind("<Left>", lambda e: self._on_key_press(e, self.play_prev))
        
        # 右键：下一首
        self.bind("<Right>", lambda e: self._on_key_press(e, self.play_next))
        
        # 点击背景重置焦点 (保持不变)
        self.bg_label.bind("<Button-1>", lambda event: self.focus_set())
        self.main_container.bind("<Button-1>", lambda event: self.focus_set())
    def setup_main_ui(self):
        self.bg_label = ctk.CTkLabel(self, text="", image=None)
        self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True)

        # --- 左侧面板 ---
        self.left_panel = ctk.CTkFrame(self.main_container, width=260, corner_radius=0, fg_color=("#f3f3f3", "#1a1a1a"))
        self.left_panel.pack(side="left", fill="y")
        self.left_panel.pack_propagate(False)

        self.logo_box = ctk.CTkFrame(self.left_panel, fg_color="transparent", height=220)
        self.logo_box.pack(pady=(40, 20), fill="x", padx=20)
        
        self.logo_frame_default = ctk.CTkFrame(self.logo_box, fg_color="transparent")
        self.logo_frame_default.pack()
        self.logo_icon = ctk.CTkLabel(self.logo_frame_default, text="♫", font=("Impact", 28), text_color=self.accent_color)
        self.logo_icon.pack(side="left", padx=5)
        self.lbl_logo_text = ctk.CTkLabel(self.logo_frame_default, text=self.get_text("music_hub"), font=("Impact", 24), text_color=("gray20", "gray90"))
        self.lbl_logo_text.pack(side="left")
        self.cover_label = ctk.CTkLabel(self.logo_box, text="", image=None)

        btn_style = {"fg_color": "transparent", "border_width": 1, "border_color": ("gray70", "gray40"), "text_color": ("black", "white"), "hover_color": ("gray85", "gray25"), "height": 35, "corner_radius": 8}
        
        self.btn_add_folder = ctk.CTkButton(self.left_panel, text=self.get_text("add_folder"), command=self.add_folder_action, **btn_style)
        self.btn_add_folder.pack(fill="x", padx=20, pady=5)
        
        self.btn_settings = ctk.CTkButton(self.left_panel, text=self.get_text("settings"), command=self.open_settings, **btn_style)
        self.btn_settings.pack(fill="x", padx=20, pady=5)

        self.lbl_nav_title = ctk.CTkLabel(self.left_panel, text=self.get_text("nav_title"), font=("Arial", 12, "bold"), text_color="gray")
        self.lbl_nav_title.pack(anchor="w", padx=20, pady=(30, 5))
        
        #self.lbl_credit = ctk.CTkLabel(self.left_panel, text=self.get_text("footer_credit"), font=("Arial", 10), text_color=("gray60", "gray40"))
        #self.lbl_credit.pack(side="bottom", pady=15)

        self.tree_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.tree = ttk.Treeview(self.tree_frame, show="tree")
        self.tree.pack(fill="both", expand=True)
        vsb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Button-3>", self.show_tree_context_menu)

        # --- 右侧面板 ---
        self.right_panel = ctk.CTkFrame(self.main_container, fg_color="transparent", corner_radius=0)
        self.right_panel.pack(side="right", fill="both", expand=True)

        # 顶部栏
        self.top_toolbar = ctk.CTkFrame(self.right_panel, height=50, fg_color=("#f3f3f3", "#1a1a1a"), corner_radius=0)
        self.top_toolbar.pack(fill="x", padx=0, pady=0)
        inner_toolbar = ctk.CTkFrame(self.top_toolbar, fg_color="transparent")
        inner_toolbar.pack(fill="x", padx=20, pady=15)
        
        # 搜索容器
        search_bg = ("#ffffff", "#2b2b2b")
        self.search_container = ctk.CTkFrame(inner_toolbar, fg_color=search_bg, corner_radius=20, border_width=1, border_color=("gray70", "gray30"), height=36)
        self.search_container.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.source_map = {"yt": "search_filter_yt", "sc": "search_filter_sc", "url": "search_filter_url"}
        enabled_codes = self.config.get("enabled_sources", ["yt", "sc", "url"])
        if not enabled_codes: enabled_codes = ["yt", "sc", "url"]
        init_values = [self.get_text("search_filter_local")]
        init_values.extend([self.get_text(self.source_map[code]) for code in enabled_codes])

        self.search_filter = ctk.CTkOptionMenu(self.search_container, values=init_values, width=110, height=32, fg_color=search_bg, button_color=("gray70", "gray30"), text_color=("black", "white"), corner_radius=0)
        self.search_filter.pack(side="left", padx=(5, 0))
        self.search_filter.set(init_values[0])

        self.lbl_search_icon = ctk.CTkLabel(self.search_container, text="🔍", font=("Arial", 16), text_color="gray")
        self.lbl_search_icon.pack(side="left", padx=(5, 5))
        self.search_entry = ctk.CTkEntry(self.search_container, placeholder_text=self.get_text("search_placeholder"), border_width=0, fg_color=search_bg, height=32, font=("Arial", 14))
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.bind("<Return>", self.perform_search)
        self.btn_clear_search = ctk.CTkButton(self.search_container, text="✕", width=28, height=28, fg_color="transparent", text_color=("gray60", "gray40"), hover_color=("gray90", "#3a3a3a"), corner_radius=14, font=("Arial", 14, "bold"), command=self.clear_search)
        self.btn_clear_search.pack(side="right", padx=(0, 5))

        # 右侧按钮
        self.btn_timer = ctk.CTkButton(inner_toolbar, text=self.get_text("timer_off"), width=110, height=36, fg_color=("white", "#333"), text_color=("black", "white"), corner_radius=18, border_width=1, border_color=("gray70", "gray40"), hover_color=self.accent_color, command=self.open_timer_dialog)
        self.btn_timer.pack(side="right", padx=(0, 10))
        self.btn_mini = ctk.CTkButton(inner_toolbar, text=self.get_text("mini_mode"), width=120, height=36, fg_color=("white", "#333"), text_color=("black", "white"), corner_radius=18, border_width=1, border_color=("gray70", "gray40"), hover_color=self.accent_color, command=self.start_mini_mode)
        self.btn_mini.pack(side="right")
        self.btn_fullscreen = ctk.CTkButton(
            self.top_toolbar, 
            text=self.get_text("full_screen_btn"), 
            width=110, height=36, 
            fg_color=("white", "#333"), 
            text_color=("black", "white"), 
            corner_radius=18, 
            border_width=1, border_color=("gray70", "gray40"), 
            hover_color=self.accent_color, 
            command=self.open_full_screen
        )
        self.btn_fullscreen.pack(side="right", padx=(0, 10))

        # 内容区域
        self.content_area = ctk.CTkScrollableFrame(self.right_panel, fg_color="transparent", corner_radius=0)
        self.content_area.pack(fill="both", expand=True, padx=20, pady=(10, 10))

        # 底部控制栏
        self.controls_frame = ctk.CTkFrame(self.right_panel, height=140, fg_color=("white", "#2b2b2b"), corner_radius=20, border_width=2, border_color=self.accent_color)
        self.controls_frame.pack(fill="x", side="bottom", padx=20, pady=20)

        self.progress_slider = ctk.CTkSlider(self.controls_frame, from_=0, to=100, command=self.on_seek_drag, height=16, border_width=0, progress_color=self.accent_color, button_color=self.accent_color, button_hover_color=self.accent_color)
        self.progress_slider.set(0)
        self.progress_slider.pack(fill="x", padx=25, pady=(20, 5))

        info_box = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        info_box.pack(fill="x", padx=30)
        self.lbl_curr = ctk.CTkLabel(info_box, text="00:00", font=("Arial", 12), text_color="gray")
        self.lbl_curr.pack(side="left")
        self.lbl_song_name = ctk.CTkLabel(info_box, text=self.get_text("welcome"), font=("Arial", 15, "bold"))
        self.lbl_song_name.pack(side="left", expand=True)
        self.lbl_total = ctk.CTkLabel(info_box, text="00:00", font=("Arial", 12), text_color="gray")
        self.lbl_total.pack(side="right")

        btn_box = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        btn_box.pack(pady=(5, 0)) # 减少下边距，给 status label 留空间
        ctl_style = {"fg_color": "transparent", "text_color": ("black", "white"), "hover_color": ("gray90", "gray35"), "width": 50, "corner_radius": 10}
        
        self.btn_mode = ctk.CTkButton(btn_box, text="➡", font=("Arial", 20), command=self.toggle_mode, **ctl_style)
        self.btn_mode.pack(side="left", padx=10)
        ctk.CTkButton(btn_box, text="⏮", font=("Arial", 22), command=lambda: [self.animate_button_press(self.btn_play), self.play_prev()], **ctl_style).pack(side="left", padx=10)
        self.btn_play = ctk.CTkButton(btn_box, text="▶", width=64, height=64, corner_radius=32, font=("Arial", 30), command=lambda: [self.animate_button_press(self.btn_play), self.toggle_play()], fg_color=self.accent_color, hover_color=self.accent_color)
        self.btn_play.pack(side="left", padx=20)
        ctk.CTkButton(btn_box, text="⏭", font=("Arial", 22), command=lambda: [self.animate_button_press(self.btn_play), self.play_next()], **ctl_style).pack(side="left", padx=10)
        
        vol_box = ctk.CTkFrame(btn_box, fg_color="transparent")
        vol_box.pack(side="left", padx=20)
        ctk.CTkLabel(vol_box, text="🔈", text_color="gray").pack(side="left")
        self.vol_slider = ctk.CTkSlider(vol_box, width=100, from_=0, to=1, command=self.on_volume_change, progress_color=self.accent_color, button_color=self.accent_color, button_hover_color=self.accent_color)
        self.vol_slider.set(self.config['volume'])
        self.vol_slider.pack(side="left", padx=5)

        # --- 新增：状态信息标签 (位于按钮下方) ---
        self.lbl_status = ctk.CTkLabel(self.controls_frame, text="", font=("Arial", 11), text_color="gray")
        self.lbl_status.pack(side="bottom", pady=(0, 10))
        # --- 左侧底部信息 ---
        # 1. 版权
        self.lbl_credit = ctk.CTkLabel(self.left_panel, text=self.get_text("footer_credit"), font=("Arial", 10), text_color=("gray60", "gray40"))
        
        # 2. 版本号 (如果有)
        if self.app_version:
            self.lbl_version = ctk.CTkLabel(self.left_panel, text=self.app_version, font=("Arial", 9), text_color=("gray50", "gray30"))
            
            # 注意 pack 顺序 (side=bottom 是从下往上堆叠)
            self.lbl_version.pack(side="bottom", pady=(0, 10)) # 最下面
            self.lbl_credit.pack(side="bottom", pady=(2, 0))   # 在版本号上面
        else:
            self.lbl_credit.pack(side="bottom", pady=15)

        #self.lbl_nav_title = ctk.CTkLabel(self.left_panel, text=self.get_text("nav_title"), font=("Arial", 12, "bold"), text_color="gray")
        #self.lbl_nav_title.pack(anchor="w", padx=20, pady=(30, 5))

        
    def play_shuffle_all(self):
        """全库随机播放"""
        all_songs = []
        for root_folder in self.config['folders']:
            if not os.path.exists(root_folder): continue
            for dirpath, _, filenames in os.walk(root_folder):
                for f in filenames:
                    if self.is_audio_file(f):
                        all_songs.append(os.path.join(dirpath, f))

        if not all_songs:
            messagebox.showinfo("Info", self.get_text("no_results") or "No songs found.")
            return

        self.playlist = all_songs
        self.playback_mode = "Shuffle"
        self.btn_mode.configure(text="🔀", text_color=self.accent_color)
        
        # --- 修复 1: 显示状态信息 ---
        if hasattr(self, 'lbl_status'):
            self.lbl_status.configure(text=self.get_text("msg_shuffle_all"))
        
        idx = random.randint(0, len(all_songs) - 1)
        self.play_song(self.playlist[idx])
    def refresh_ui_appearance(self):
        # 1. 颜色刷新 (保持不变)
        self.controls_frame.configure(border_color=self.accent_color)
        self.logo_icon.configure(text_color=self.accent_color)
        self.btn_play.configure(fg_color=self.accent_color, hover_color=self.accent_color)
        self.progress_slider.configure(progress_color=self.accent_color, button_color=self.accent_color, button_hover_color=self.accent_color)
        self.vol_slider.configure(progress_color=self.accent_color, button_color=self.accent_color, button_hover_color=self.accent_color)
        if self.playback_mode != "Order": self.btn_mode.configure(text_color=self.accent_color)
        if hasattr(self, 'btn_mini'): self.btn_mini.configure(hover_color=self.accent_color)
        if self.timer_logic.is_active(): self.btn_timer.configure(fg_color=self.accent_color, text_color="white")
        else: self.btn_timer.configure(fg_color=("white", "#333"), text_color=("black", "white"))
        
        self.update_treeview_style()

        # 2. 文本刷新 (保持不变)
        self.title(self.get_text("app_title"))
        self.lbl_logo_text.configure(text=self.get_text("music_hub"))
        self.btn_add_folder.configure(text=self.get_text("add_folder"))
        self.btn_settings.configure(text=self.get_text("settings"))
        self.lbl_nav_title.configure(text=self.get_text("nav_title"))
        self.lbl_credit.configure(text=self.get_text("footer_credit"))
        self.btn_mini.configure(text=self.get_text("mini_mode"))
        # 刷新全屏按钮文本和颜色
        if hasattr(self, 'btn_fullscreen'):
            self.btn_fullscreen.configure(text=self.get_text("full_screen_btn"), hover_color=self.accent_color)
        
        if not self.timer_logic.is_active(): self.btn_timer.configure(text=self.get_text("timer_off"))
        if hasattr(self, 'search_entry'): self.search_entry.configure(placeholder_text=self.get_text("search_placeholder"))

        # --- 修复 2: 更新下拉菜单内容 (不创建新对象) ---
        if hasattr(self, 'search_filter'): 
            # 获取当前启用的源
            enabled_codes = self.config.get("enabled_sources", ["yt", "sc", "url"])
            if not enabled_codes: enabled_codes = ["yt", "sc", "url"]
            
            # 构建显示列表: [本地] + [启用源的翻译]
            # get_text(self.source_map[code]) 会获取 "search_filter_url" 对应的 "万能链接"
            display_values = [self.get_text("search_filter_local")]
            display_values.extend([self.get_text(self.source_map[code]) for code in enabled_codes])
            
            # 更新菜单选项
            self.search_filter.configure(values=display_values)
            # 重置选中项为"本地库"，确保显示的文字也是当前语言
            self.search_filter.set(display_values[0])

        if not self.player.current_song_path: self.lbl_song_name.configure(text=self.get_text("welcome"))
        
        if self.current_view == "List" and self.current_path_memory: self.load_songs_view(self.current_path_memory)
        elif self.current_view == "Home": self.show_home_view()

    # --- 定时器逻辑 ---
    def open_timer_dialog(self):
        # 如果定时器正在运行，点击则是停止
        if self.timer_logic.is_active():
            self.timer_logic.stop()
            self.refresh_ui_appearance()
            return
            
        # --- 修复：防止多开 ---
        if self.timer_window is not None and self.timer_window.winfo_exists():
            self.timer_window.lift()
            self.timer_window.focus_force()
            return

        # 创建并赋值
        self.timer_window = TimerInputDialog(self, self.accent_color, self.start_timer_action)

    def start_timer_action(self, minutes, action):
        self.timer_logic.start(minutes, action)
        self.btn_timer.configure(fg_color=self.accent_color, text_color="white")

    def toggle_sleep_timer(self): 
        pass

    # --- 搜索与下载逻辑 ---
    def perform_search(self, event=None):
        query = self.search_entry.get().strip() # URL 不要 lower()
        if not query: return
        
        # 获取当前选中的文字 (例如 "万能链接" 或 "Direct URL")
        display_val = self.search_filter.get()
        
        # 反查对应的 code
        # source_map: {'yt': 'search_filter_yt', 'url': 'search_filter_url'}
        source_code = "yt" # 默认 fallback
        
        # 检查是否是本地
        if display_val == self.get_text("search_filter_local"):
            self.perform_local_search(query.lower())
            return

        # 检查是哪个网络源
        for code, key_name in self.source_map.items():
            # 比较翻译后的文字
            if self.get_text(key_name) == display_val:
                source_code = code
                break
        
        if source_code == "url":
            # 万能链接模式
            self.perform_online_search(query, "url")
        else:
            # yt 或 sc
            self.perform_online_search(query, source_code)

    def perform_local_search(self, query):
        self.current_view = "Search"; self.current_path_memory = None; self.clear_content()
        self.content_area._parent_canvas.yview_moveto(0.0)
        header = ctk.CTkFrame(self.content_area, fg_color="transparent"); header.pack(fill="x", pady=(0, 20))
        ctk.CTkButton(header, text=self.get_text("nav_home"), width=80, fg_color="transparent", border_width=1, text_color=("black", "white"), command=self.show_home_view).pack(side="left")
        ctk.CTkLabel(header, text=f"{self.get_text('search_results')}: '{query}'", font=("Arial", 18, "bold")).pack(side="left", padx=20)
        self.playlist = []; self.song_widgets = []; self.star_widgets = []; found_count = 0
        for root_folder in self.config['folders']:
            if not os.path.exists(root_folder): continue
            for dirpath, _, filenames in os.walk(root_folder):
                for f in filenames:
                    if self.is_audio_file(f):
                        if query in f.lower():
                            full_path = os.path.join(dirpath, f)
                            self.add_song_to_list_ui(full_path, found_count)
                            found_count += 1
        if found_count == 0: ctk.CTkLabel(self.content_area, text=self.get_text("no_results"), font=("Arial", 16), text_color="gray").pack(pady=50)

    def perform_online_search(self, query, source):
        self.current_view = "OnlineSearch"; self.clear_content()
        self.loading_lbl = ctk.CTkLabel(self.content_area, text="Searching online...", font=("Arial", 16)); self.loading_lbl.pack(pady=50)
        def run_search():
            results = self.downloader.search(query, source)
            self.after(0, lambda: self.show_online_results(results, query, source))
        threading.Thread(target=run_search, daemon=True).start()

    def show_online_results(self, results, query, source_code):
        # ... (前面代码保持不变) ...
        self.clear_content(); self.content_area._parent_canvas.yview_moveto(0.0)
        header = ctk.CTkFrame(self.content_area, fg_color="transparent"); header.pack(fill="x", pady=(0, 20))
        ctk.CTkButton(header, text=self.get_text("nav_home"), width=80, fg_color="transparent", border_width=1, text_color=("black", "white"), command=self.show_home_view).pack(side="left")
        ctk.CTkLabel(header, text=f"{self.get_text('online_results')}: '{query}'", font=("Arial", 18, "bold")).pack(side="left", padx=20)
        
        if not results: ctk.CTkLabel(self.content_area, text=self.get_text("no_results"), font=("Arial", 16), text_color="gray").pack(pady=50); return
        
        cols = ctk.CTkFrame(self.content_area, fg_color="transparent"); cols.pack(fill="x", padx=10)
        ctk.CTkLabel(cols, text=self.get_text("source_label"), width=80, anchor="w", font=("Arial", 12, "bold")).pack(side="left")
        ctk.CTkLabel(cols, text="Title / Uploader", font=("Arial", 12, "bold")).pack(side="left", padx=10, expand=True, anchor="w")
        ctk.CTkLabel(cols, text="", width=80).pack(side="right", padx=10)
        ctk.CTkLabel(cols, text=self.get_text("duration_label"), width=60, font=("Arial", 12, "bold")).pack(side="right", padx=5)

        self.temp_online_playlist = [r['url'] for r in results]
        if not hasattr(self, 'online_titles'): self.online_titles = {}
        for r in results: self.online_titles[r['url']] = r['title']

        for index, res in enumerate(results):
            row = ctk.CTkFrame(self.content_area, fg_color=("white", "#252525")); row.pack(fill="x", pady=4, padx=5)
            ctk.CTkLabel(row, text=res['source'], width=80, anchor="w", text_color="gray").pack(side="left", padx=10)
            
            # 星星
            is_fav = res['url'] in self.config.get('favorites', [])
            star_char = "★" if is_fav else "☆"
            star_col = "#FFD700" if is_fav else "gray"
            def on_star_click(r=res, btn_ref=None):
                self.toggle_favorite(r)
                if btn_ref:
                    curr = btn_ref.cget("text")
                    new_t = "★" if curr == "☆" else "☆"
                    new_c = "#FFD700" if curr == "☆" else "gray"
                    btn_ref.configure(text=new_t, text_color=new_c)
            star_btn = ctk.CTkButton(row, text=star_char, width=30, height=30, fg_color="transparent", text_color=star_col, font=("Arial", 16), hover_color=("gray85", "#333"))
            star_btn.configure(command=lambda r=res, b=star_btn: on_star_click(r, b))
            star_btn.pack(side="left", padx=5)

            # 标题
            title_text = f"{res['title']}\n{res['uploader']}"
            lbl_title = ctk.CTkLabel(row, text=title_text, anchor="w", font=("Arial", 13))
            lbl_title.pack(side="left", padx=10, expand=True, fill="x")
            
            # --- 核心修复：右键菜单使用 res['title'] (完整标题) ---
            def show_online_menu(event, res_item=res):
                menu = Menu(self, tearoff=0)
                # 添加到歌单 (传递完整标题)
                menu.add_command(
                    label=self.get_text("ctx_add_to_playlist"), 
                    command=lambda: self.open_add_to_playlist_dialog(res_item['url'], res_item['title'], "online")
                )
                is_curr_fav = res_item['url'] in self.config.get('favorites', [])
                star_text = self.get_text("ctx_unstar") if is_curr_fav else "🌟 Star"
                menu.add_command(label=star_text, command=lambda: self.toggle_favorite(res_item))
                menu.post(event.x_root, event.y_root)

            lbl_title.bind("<Button-3>", show_online_menu)
            row.bind("<Button-3>", show_online_menu)
            
            play_btn = ctk.CTkButton(row, text="▶ Play", width=80, height=30, fg_color=self.accent_color, hover_color=self.accent_color, command=lambda idx=index, r_list=results: self.prepare_online_play(idx, r_list))
            play_btn.pack(side="right", padx=10, pady=5)
            
            duration_str = MusicSourceHandler.format_seconds(res['duration'])
            ctk.CTkLabel(row, text=duration_str, width=60, text_color="gray").pack(side="right", padx=5)

    def prepare_online_play(self, index, custom_list=None):
        # --- 修复：上锁 ---
        self.is_switching_song = True
        
        if hasattr(self, 'lbl_status'):
            self.lbl_status.configure(text="")

        if custom_list:
            self.playlist = [r['url'] for r in custom_list]
            for r in custom_list:
                self.online_titles[r['url']] = r['title']
        
        self.current_index = index
        if index < 0 or index >= len(self.playlist): 
            self.is_switching_song = False
            return
        
        current_url = self.playlist[index]
        title = self.online_titles.get(current_url, "Unknown Title")
        self.lbl_song_name.configure(text=f"Buffering: {title}...")
        
        def on_url_ready(real_url, fetched_title):
            if real_url:
                self.after(0, lambda: self.start_stream_playback(real_url, current_url))
            else:
                self.is_switching_song = False # 失败也要解锁
                self.after(0, lambda: messagebox.showerror("Error", "Failed to load stream"))

        self.downloader.get_stream_url(current_url, on_url_ready)
    
    def start_stream_playback(self, real_url, original_url, duration=0):
        """开始播放流媒体"""
        self.player.stop()
        self.player.load_and_play(real_url)
        
        # --- 修复：解锁，允许监控继续 ---
        self.is_switching_song = False
        
        title = self.online_titles.get(original_url, "Unknown")
        self.lbl_song_name.configure(text=title)
        
        self.progress_slider.set(0)
        self.lbl_curr.configure(text="00:00")
        
        self.duration_locked = False
        
        if duration:
            self.current_song_duration = duration
            self.progress_slider.configure(to=duration)
            m, s = divmod(int(duration), 60)
            self.lbl_total.configure(text=f"{m:02d}:{s:02d}")
        
        self.update_play_icon()
        self.cover_label.pack_forget()
        self.logo_frame_default.pack()
        
        if self.tray_handler:
            self.tray_handler.update_tooltip(f"Playing: {title}")

    def start_download(self, result_info, btn_widget):
        if btn_widget: btn_widget.configure(state="disabled", text=self.get_text("dl_downloading"), fg_color="gray")
        def on_progress(d): pass
        def on_complete(success, path_or_msg): self.after(0, lambda: self.finish_download_ui(success, path_or_msg, btn_widget, result_info['title']))
        self.downloader.download(result_info['webpage_url'], result_info['title'], on_progress, on_complete)

    def finish_download_ui(self, success, msg, btn, title):
        if success:
            btn.configure(text=self.get_text("dl_success"), fg_color="green")
            dl_path = ConfigManager.get_download_path()
            if dl_path not in self.config['folders']:
                if messagebox.askyesno("Info", f"Downloaded to: {dl_path}\nAdd this folder to library?"):
                    self.config['folders'].append(dl_path); ConfigManager.save_config(self.config); self.refresh_sidebar_tree()
        else:
            btn.configure(text=self.get_text("dl_error"), fg_color="red"); print(f"Download error: {msg}")
            self.after(3000, lambda: btn.configure(state="normal", text=self.get_text("dl_btn"), fg_color=self.accent_color))

    def clear_search(self):
        if hasattr(self, 'search_entry'): self.search_entry.delete(0, 'end'); self.main_container.focus_set()
        if self.current_view != "Home": self.show_home_view()

    def load_songs_view(self, path):
        self.current_view = "List"
        self.current_path_memory = path
        self.clear_content()
        
        # 清除状态栏信息
        if hasattr(self, 'lbl_status'):
            self.lbl_status.configure(text="")
        
        top = ctk.CTkFrame(self.content_area, fg_color="transparent")
        top.pack(fill="x", pady=(0, 20))
        
        self.nav_buttons = []
        btn_home = ctk.CTkButton(top, text=self.get_text("nav_home"), width=80, fg_color="transparent", border_width=1, text_color=("black", "white"), command=self.show_home_view)
        btn_home.pack(side="left")
        self.nav_buttons.append(btn_home)
        
        display_name = os.path.basename(path)
        if not display_name: display_name = path
        ctk.CTkLabel(top, text=f"📂 {display_name}", font=("Arial", 18, "bold")).pack(side="left", padx=20)

        self.playlist = []
        self.song_widgets = []
        self.folder_widgets = []
        self.star_widgets = []
        
        try: all_items = os.listdir(path)
        except: return

        sub_folders = []
        audio_files = []
        for item in all_items:
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                sub_folders.append(full_path)
            elif self.is_audio_file(item):
                audio_files.append(full_path)

        # 排序
        sub_folders.sort(key=lambda x: os.path.basename(x).lower())
        audio_files.sort(key=self.get_music_sort_key)

        if not sub_folders and not audio_files:
            ctk.CTkLabel(self.content_area, text=self.get_text("empty_folder"), font=("Arial", 16), text_color="gray").pack(pady=50)
            return

        # 子文件夹
        if sub_folders:
            ctk.CTkLabel(self.content_area, text=self.get_text("subdirs"), font=("Arial", 12, "bold"), text_color="gray").pack(anchor="w", pady=(5,5))
            for p in sub_folders:
                n = os.path.basename(p)
                btn = ctk.CTkButton(
                    self.content_area, text=f"📁  {n}", anchor="w", height=40, 
                    fg_color=("white", "#2b2b2b"), text_color=("black", "white"), 
                    hover_color=self.accent_color, 
                    command=lambda x=p: self.load_songs_view(x)
                )
                btn.pack(fill="x", pady=2)
                self.folder_widgets.append(btn)

        # 音频文件
        if audio_files:
            if sub_folders: 
                ctk.CTkLabel(self.content_area, text=self.get_text("audio_files"), font=("Arial", 12, "bold"), text_color="gray").pack(anchor="w", pady=(15, 5))
            
            for i, p in enumerate(audio_files):
                n = os.path.basename(p)
                self.playlist.append(p)
                
                row_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
                row_frame.pack(fill="x", pady=2)
                
                # 星号按钮
                is_fav = p in self.config.get('favorites', [])
                star_char = "★" if is_fav else "☆"
                star_color = "#FFD700" if is_fav else ("gray" if self.current_theme_mode=="Light" else "gray60")
                
                btn_star = ctk.CTkButton(
                    row_frame, text=star_char, width=30, height=45,
                    fg_color="transparent", text_color=star_color,
                    font=("Arial", 18), hover_color=("gray85", "#333"),
                    command=lambda x=p: self.toggle_favorite(x)
                )
                btn_star.pack(side="left", padx=(0, 5))
                self.star_widgets.append(btn_star)
                
                # 歌曲名按钮
                btn_song = ctk.CTkButton(
                    row_frame, text=f"{i+1}.  {n}", anchor="w", height=45, corner_radius=10, 
                    fg_color=("white", "#252525"), text_color=("black", "white"), 
                    hover_color=self.accent_color,
                    command=lambda x=p: [self.animate_button_press(self.btn_play), self.play_song(x)]
                )
                btn_song.pack(side="left", fill="x", expand=True)
                self.song_widgets.append(btn_song)

                # --- 绑定右键菜单 (添加到歌单) ---
                def show_context_menu(event, path=p, name=n):
                    menu = Menu(self, tearoff=0)
                    menu.add_command(
                        label=self.get_text("ctx_add_to_playlist"), 
                        command=lambda: self.open_add_to_playlist_dialog(path, name, "local")
                    )
                    menu.post(event.x_root, event.y_root)
                
                btn_song.bind("<Button-3>", show_context_menu)
        
        # 初始化高亮
        if self.player.current_song_path and self.player.current_song_path in self.playlist:
            self.highlight_current_song_only()

    def add_song_to_list_ui(self, path, index):
        n = os.path.basename(path); self.playlist.append(path)
        row_frame = ctk.CTkFrame(self.content_area, fg_color="transparent"); row_frame.pack(fill="x", pady=2)
        is_fav = path in self.config.get('favorites', []); star_char = "★" if is_fav else "☆"; star_color = "#FFD700" if is_fav else ("gray" if self.current_theme_mode=="Light" else "gray60")
        btn_star = ctk.CTkButton(row_frame, text=star_char, width=30, height=45, fg_color="transparent", text_color=star_color, font=("Arial", 18), hover_color=("gray85", "#333"), command=lambda x=path: self.toggle_favorite(x))
        btn_star.pack(side="left", padx=(0, 5)); self.star_widgets.append(btn_star)
        folder_name = os.path.basename(os.path.dirname(path)); display_text = f"{index+1}. {n}  [{folder_name}]"
        btn_song = ctk.CTkButton(row_frame, text=display_text, anchor="w", height=45, corner_radius=10, fg_color=("white", "#252525"), text_color=("black", "white"), hover_color=self.accent_color, command=lambda x=path: [self.animate_button_press(self.btn_play), self.play_song(x)])
        btn_song.pack(side="left", fill="x", expand=True); self.song_widgets.append(btn_song)

    def get_music_sort_key(self, file_path):
        filename = os.path.basename(file_path).lower()
        try:
            f = mutagen.File(file_path)
            if f is not None:
                track_str = None
                if 'TRCK' in f.tags: track_str = str(f.tags['TRCK'])
                elif 'TRACKNUMBER' in f.tags: track_str = str(f.tags['TRACKNUMBER'][0])
                elif 'tracknumber' in f.tags: track_str = str(f.tags['tracknumber'][0])
                if track_str:
                    if '/' in track_str: track_str = track_str.split('/')[0]
                    if track_str.isdigit(): return (int(track_str), filename)
        except: pass
        return (999999, filename)

    def show_home_view(self):
        self.current_view = "Home"
        self.clear_content()
        self.home_images_ref = [] 

        # 刷新背景 & 网络检测
        try:
            self.update_idletasks()
            self.content_area.configure(fg_color="transparent")
        except: pass
        
        self.has_network = self.check_network_connection()

        header = ctk.CTkFrame(self.content_area, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(header, text=self.get_text("home_view_title"), font=("Arial", 24, "bold")).pack(side="left")
        
        # 收集收藏
        all_favs_config = self.config.get('favorites', [])
        valid_items = [] 
        
        if not self.online_song_cache:
            self.online_song_cache = ConfigManager.load_online_cache()

        for f in all_favs_config:
            if os.path.exists(f):
                valid_items.append({"type": "local", "path": f, "name": os.path.basename(f)})
            elif f.startswith("http"):
                if self.has_network and f in self.online_song_cache:
                    data = self.online_song_cache[f]
                    valid_items.append({"type": "online", "path": f, "name": data.get("title", "Unknown")})

        # 渲染收藏栏
        if valid_items or True:
            title_text = f"{self.get_text('favorites_title')} ({len(valid_items)})" if valid_items else self.get_text('favorites_title')
            ctk.CTkLabel(self.content_area, text=title_text, font=("Arial", 14, "bold"), text_color=self.accent_color).pack(anchor="w", pady=(10, 5))
            
            fav_scroll = ctk.CTkScrollableFrame(self.content_area, height=110, orientation="horizontal", fg_color="transparent")
            fav_scroll.pack(fill="x", pady=(0, 20))
            
            # Shuffle 按钮
            shuffle_card = ctk.CTkFrame(fav_scroll, width=140, fg_color=self.accent_color, corner_radius=10)
            shuffle_card.pack(side="left", padx=5, fill="y")
            ctk.CTkButton(shuffle_card, text=f"{self.get_text('btn_shuffle_all')}", font=("Arial", 14, "bold"), width=130, height=80, fg_color="transparent", text_color="white", hover_color=self.accent_color, command=self.play_shuffle_all).pack(padx=5, pady=5, fill="both", expand=True)

            # 收藏条目
            for item in valid_items:
                path = item["path"]
                real_name = item["name"] # --- 核心：保留完整名字 ---
                
                # UI 显示用的名字 (截断)
                display_name = real_name
                if len(display_name) > 15: 
                    display_name = display_name[:12] + "..."
                
                card = ctk.CTkFrame(fav_scroll, width=140, fg_color=("white", "#2b2b2b"), corner_radius=10)
                card.pack(side="left", padx=5, fill="y")
                
                prefix = "☁️ " if item["type"] == "online" else "♫ "
                
                btn = ctk.CTkButton(card, text=f"{prefix}\n{display_name}", font=("Arial", 13), width=130, height=80, fg_color="transparent", text_color=("black", "white"), hover_color=self.accent_color, command=lambda x=path: self.play_from_favorites(x))
                btn.pack(padx=5, pady=5, fill="both", expand=True)
                
                # 右键菜单
                # --- 核心修复：传参使用 real_name ---
                def show_fav_menu(event, p=path, n=real_name, t=item["type"]):
                    menu = Menu(self, tearoff=0)
                    # 添加到歌单
                    menu.add_command(label=self.get_text("ctx_add_to_playlist"), 
                                     command=lambda: self.open_add_to_playlist_dialog(p, n, t))
                    menu.add_separator()
                    menu.add_command(label=self.get_text("ctx_move_left"), command=lambda: self.move_favorite(p, -1))
                    menu.add_command(label=self.get_text("ctx_move_right"), command=lambda: self.move_favorite(p, 1))
                    menu.add_separator()
                    menu.add_command(label=self.get_text("ctx_unstar"), command=lambda: self.toggle_favorite(p))
                    menu.post(event.x_root, event.y_root)
                btn.bind("<Button-3>", show_fav_menu)

        # 渲染文件夹 (保持不变)
        ctk.CTkLabel(self.content_area, text=self.get_text("folders_title"), font=("Arial", 14, "bold"), text_color="gray").pack(anchor="w", pady=(0, 10))
        if not self.config['folders']: ctk.CTkLabel(self.content_area, text=self.get_text("no_folders"), text_color="gray").pack(pady=20); return
        grid = ctk.CTkFrame(self.content_area, fg_color="transparent"); grid.pack(fill="both", expand=True); cols = 4
        if "folder_covers" not in self.config: self.config["folder_covers"] = {}
        for idx, p in enumerate(self.config['folders']):
            n = os.path.basename(p) or p; dn = n[:16]+"..." if len(n)>18 else n; r, c = divmod(idx, cols)
            cover_path = self.config['folder_covers'].get(p); btn_image = None; btn_text = f"{n[0].upper() if n else '?'}\n\n{dn}"; btn_fg = ("white", "#2b2b2b")
            if cover_path and os.path.exists(cover_path):
                try:
                    pil_img = Image.open(cover_path); btn_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(120, 120))
                    self.home_images_ref.append(btn_image); btn_text = f"\n\n\n\n\n{dn}"; btn_fg = ("#e0e0e0", "#202020")
                except: pass
            b = ctk.CTkButton(grid, text=btn_text, image=btn_image, compound="top", font=("Arial", 15, "bold"), width=180, height=170, corner_radius=20, fg_color=btn_fg, text_color=("black", "white"), hover_color=self.accent_color, command=lambda path=p: self.load_songs_view(path))
            b.grid(row=r, column=c, padx=12, pady=12)

    def play_from_favorites(self, path):
        # --- 修复：防崩溃检查 ---
        # 如果 online_titles 意外丢失，立刻重新创建
        if not hasattr(self, 'online_titles'):
            self.online_titles = {}

        # 清除状态信息
        if hasattr(self, 'lbl_status'):
            self.lbl_status.configure(text="")

        # 检查是否在线播放
        is_online = path.startswith("http")
        if is_online:
            if not self.check_network_connection():
                messagebox.showerror("Error", "No Network Connection!\n无法播放网络音乐。")
                return
            # 填充标题缓存
            if path in self.online_song_cache:
                self.online_titles[path] = self.online_song_cache[path]['title']

        all_favs = self.config.get('favorites', [])
        valid_favs = []
        has_net = self.check_network_connection()
        
        for f in all_favs:
            if os.path.exists(f):
                valid_favs.append(f)
            elif f.startswith("http") and has_net:
                valid_favs.append(f)
                # 再次确认字典存在
                if f in self.online_song_cache:
                    self.online_titles[f] = self.online_song_cache[f]['title']
        
        if not valid_favs: return
        self.playlist = valid_favs
        
        if path in self.playlist:
            idx = self.playlist.index(path)
            if path.startswith("http"):
                self.prepare_online_play(idx)
            else:
                self.current_index = idx
                self.play_song(path)

    def highlight_current_song_only(self):
        if self.current_view != "List": return
        current_name = os.path.basename(self.player.current_song_path) if self.player.current_song_path else ""
        for btn in self.song_widgets:
            try:
                if current_name and current_name in btn.cget("text"): btn.configure(fg_color=self.accent_color, text_color="white")
                else: btn.configure(fg_color=("white", "#252525"), text_color=("black", "white"))
            except: pass

    def play_song(self, path):
        # --- 核心：本地播放立即解锁 ---
        self.is_switching_song = False
        
        if path not in self.playlist: self.playlist.append(path)
        try:
            self.current_index = self.playlist.index(path)
            self.player.load_and_play(path)
        except Exception as e: return

        name = os.path.basename(path)
        self.lbl_song_name.configure(text=name)
        self.progress_slider.set(0)
        self.lbl_curr.configure(text="00:00")
        self.update_play_icon()
        
        # 锁定时长 (本地文件)
        self.current_song_duration = self.player.get_current_length()
        if self.current_song_duration > 0:
            self.progress_slider.configure(to=self.current_song_duration)
            m, s = divmod(int(self.current_song_duration), 60)
            self.lbl_total.configure(text=f"{m:02d}:{s:02d}")
            self.duration_locked = True
        else:
            self.progress_slider.configure(to=100)
            self.lbl_total.configure(text="00:00")
            self.duration_locked = False

        self.highlight_current_song_only()
        if self.tray_handler: self.tray_handler.update_tooltip(f"Playing: {name}")
        
        cover_img = self.player.get_embedded_cover(path)
        if cover_img:
            self.logo_frame_default.pack_forget(); w, h = (220, 220); cover_img = cover_img.resize((w, h), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=cover_img, dark_image=cover_img, size=(w, h)); self.cover_label.configure(image=ctk_img); self.cover_label.pack()
        else: self.cover_label.pack_forget(); self.logo_frame_default.pack()
    def toggle_favorite(self, item):
        """
        切换收藏状态。
        item: 可以是本地路径(str) 或 在线歌曲信息(dict)
        """
        if 'favorites' not in self.config: self.config['favorites'] = []
        
        target_id = None
        is_online = False
        
        if isinstance(item, dict):
            # 在线歌曲：item 是一个包含 url, title 等的字典
            target_id = item['url']
            is_online = True
            # 如果是新收藏，保存元数据到 saved_online_songs.json
            if target_id not in self.config['favorites']:
                self.online_song_cache[target_id] = {
                    "title": item.get('title', 'Unknown'),
                    "duration": item.get('duration', 0),
                    "source": item.get('source', 'Web')
                }
                ConfigManager.save_online_cache(self.online_song_cache)
        else:
            # 本地文件：item 是路径字符串
            target_id = item
            
        # 切换逻辑
        if target_id in self.config['favorites']:
            self.config['favorites'].remove(target_id)
            # 注意：我们不删除 online_song_cache 里的数据，留作缓存
        else:
            self.config['favorites'].append(target_id)
            
        ConfigManager.save_config(self.config)
        
        # 刷新界面
        if self.current_view == "Home": 
            self.show_home_view()
        elif self.current_view == "List" and self.current_path_memory: 
            self.load_songs_view(self.current_path_memory)
        elif self.current_view == "OnlineSearch": 
            # 在线搜索界面需要重新渲染以更新星星状态
            # 这里比较复杂，最简单的办法是只更新当前按钮，或者重新触发一次显示逻辑（不重新搜索）
            # 为了简单，我们暂不刷新整个 Online 视图，用户下次搜索会看到变化
            pass
    def play_playlist_item(self, index):
        if index < 0 or index >= len(self.playlist): return

        target = self.playlist[index]
        
        # 1. 尝试从缓存获取原始标题 (在 load_playlist_view 里存好的)
        # 如果找不到，回退到文件名
        clean_title = self.online_titles.get(target, os.path.basename(target))
        
        # 2. 设置当前索引
        self.current_index = index

        if target.startswith("http"):
            if not self.check_network_connection():
                messagebox.showerror("Error", "No Network Connection!")
                return
            self.prepare_online_play(index)
        else:
            if os.path.exists(target):
                # 播放
                self.play_song(target)
                # 3. 强制覆盖显示的歌名 (用干净的标题，而不是文件名)
                self.lbl_song_name.configure(text=clean_title)
                # 这里的覆盖很重要，因为 play_song 默认用 os.path.basename
                # 更新托盘
                if self.tray_handler: self.tray_handler.update_tooltip(f"Playing: {clean_title}")
            else:
                messagebox.showerror("Error", "File not found.")
    def update_progress_loop(self):
        """统一的UI更新循环"""
        # --- 修复 1: 安全检查 ---
        try:
            if not self.winfo_exists():
                return
        except: return

        # 1. 检查定时器
        if self.timer_logic.check_expired():
            if self.timer_logic.action == "quit": 
                self.quit_app()
                return # 退出后不再继续
            else: 
                self.player.stop()
                self.update_play_icon()
                self.refresh_ui_appearance()

        # 2. 更新定时器按钮文字
        if self.timer_logic.is_active():
            txt = self.timer_logic.get_remaining_text()
            prefix = self.get_text("timer_running")
            try: self.btn_timer.configure(text=f"{prefix}{txt}")
            except: pass

        # 3. 强制同步图标
        self.update_play_icon()

        # 4. 更新播放进度
        if self.player.is_playing():
            try:
                if time.time() - self.last_seek_time < 2.0:
                    # 冷却中，跳过更新但继续循环
                    self._progress_loop_id = self.after(1000, self.update_progress_loop)
                    return

                curr = self.player.get_current_position()
                
                if not self.duration_locked:
                    real_len = self.player.get_current_length()
                    if real_len > 0 and abs(real_len - self.current_song_duration) > 2:
                        self.current_song_duration = real_len
                        self.progress_slider.configure(to=real_len)
                        m, s = divmod(int(real_len), 60)
                        self.lbl_total.configure(text=f"{m:02d}:{s:02d}")

                self.progress_slider.set(curr)
                m, s = divmod(int(curr), 60)
                self.lbl_curr.configure(text=f"{m:02d}:{s:02d}")
            except: pass
        
        # --- 修复 2: 记录 ID ---
        self._progress_loop_id = self.after(1000, self.update_progress_loop)
    def on_seek_drag(self, value): 
        """拖拽进度条"""
        # 1. 记录当前时间，作为"最后一次拖拽的时间"
        self.last_seek_time = time.time()
        
        # 2. 执行 VLC 跳转
        self.player.seek(float(value))
        
        # 3. (可选) 立即更新时间标签，让反馈更即时
        m, s = divmod(int(value), 60)
        self.lbl_curr.configure(text=f"{m:02d}:{s:02d}")
    def on_volume_change(self, value):
        val = float(value); self.player.set_volume(val); self.config['volume'] = val
        if hasattr(self, 'vol_slider') and abs(self.vol_slider.get() - val) > 0.01: self.vol_slider.set(val)
    
    # --- 这里是你之前缺失的部分，现在补上了 ---
    def add_folder_action(self):
        path = filedialog.askdirectory()
        if path and path not in self.config['folders']:
            self.config['folders'].append(path); ConfigManager.save_config(self.config)
            self.refresh_sidebar_tree()
            if self.current_view == "Home": self.show_home_view()
            
    def show_tree_context_menu(self, event):
        item_id = self.tree.identify_row(event.y)
        if item_id:
            self.tree.selection_set(item_id)
            menu = Menu(self, tearoff=0)
            menu.add_command(label=self.get_text("ctx_change_cover"), command=self.change_folder_cover)
            menu.add_separator()
            menu.add_command(label=self.get_text("ctx_remove_folder"), command=self.remove_selected_folder)
            menu.post(event.x_root, event.y_root)
            
    def remove_selected_folder(self):
        sel = self.tree.selection()
        if not sel: return
        
        # 获取 values (元组)
        values = self.tree.item(sel[0], "values")
        
        # 修复 IndexError: 如果选中了没有 values 的节点 (例如根节点)，直接返回
        if not values:
            return

        path = values[0]
        
        # 1. 删除歌单逻辑
        if path.startswith("playlist::"):
            pl_name = path.replace("playlist::", "")
            if messagebox.askyesno(self.get_text("confirm_remove"), f"Playlist: {pl_name}?"):
                from playlist_manager import PlaylistManager
                PlaylistManager.delete_playlist(pl_name)
                self.refresh_sidebar_tree()
                # 如果当前正在看这个歌单，回首页
                if self.current_view == "Playlist" and self.current_path_memory == path:
                    self.show_home_view()
        
        # 2. 删除文件夹逻辑
        elif path in self.config['folders']:
            if messagebox.askyesno(self.get_text("confirm_remove"), f"Folder: {path}?"):
                self.config['folders'].remove(path)
                ConfigManager.save_config(self.config)
                self.refresh_sidebar_tree()
                if self.current_view == "Home": self.show_home_view()
                
    def change_folder_cover(self):
        sel = self.tree.selection()
        if not sel: return
        folder_path = self.tree.item(sel[0], "values")[0]
        file_path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg;*.png;*.jpeg")])
        if not file_path: return
        try:
            covers_dir = ConfigManager.get_appdata_path("covers")
            if not os.path.exists(covers_dir): os.makedirs(covers_dir)
            import time
            safe_foldername = "".join([c for c in os.path.basename(folder_path) if c.isalnum() or c in (' ', '_')]).strip() or "folder"
            ext = os.path.splitext(file_path)[1]
            new_filename = f"{safe_foldername}_{int(time.time())}{ext}"
            target_path = os.path.join(covers_dir, new_filename)
            shutil.copy(file_path, target_path)
            if "folder_covers" not in self.config: self.config["folder_covers"] = {}
            old_path = self.config["folder_covers"].get(folder_path)
            if old_path and os.path.exists(old_path) and "covers" in old_path:
                try: os.remove(old_path)
                except: pass
            self.config["folder_covers"][folder_path] = target_path
            ConfigManager.save_config(self.config)
            messagebox.showinfo(self.get_text("msg_success"), self.get_text("success_cover"))
            self.show_home_view()
        except Exception as e: messagebox.showerror(self.get_text("msg_error"), str(e))
        
    def refresh_sidebar_tree(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        
        # 1. 物理文件夹
        for root in self.config['folders']:
            name = os.path.basename(root) or root
            node = self.tree.insert("", "end", text=f"📁 {name}", values=(root,), open=True)
            self.build_tree(node, root)
            
        # 2. 歌单 (Playlists)
        playlists = PlaylistManager.get_all_playlists()
        if playlists:
            # 创建一个根节点 "My Playlists"
            pl_root = self.tree.insert("", "end", text=self.get_text("playlist_title"), open=True)
            for pl in playlists:
                # 使用特殊前缀标识歌单
                self.tree.insert(pl_root, "end", text=f"📜 {pl}", values=(f"playlist::{pl}",))
            
    def build_tree(self, parent, path):
        try:
            for item in os.listdir(path):
                full = os.path.join(path, item)
                if os.path.isdir(full):
                    node = self.tree.insert(parent, "end", text=item, values=(full,), open=False)
                    self.build_tree(node, full)
        except: pass

    def load_playlist_view(self, pl_name):
        self.current_view = "Playlist"
        self.current_path_memory = f"playlist::{pl_name}"
        self.clear_content()
        
        if hasattr(self, 'lbl_status'): self.lbl_status.configure(text="")
        
        top = ctk.CTkFrame(self.content_area, fg_color="transparent"); top.pack(fill="x", pady=(0, 20))
        ctk.CTkButton(top, text=self.get_text("nav_home"), width=80, fg_color="transparent", border_width=1, text_color=("black", "white"), command=self.show_home_view).pack(side="left")
        ctk.CTkLabel(top, text=f"📜 {pl_name}", font=("Arial", 18, "bold")).pack(side="left", padx=20)

        items = PlaylistManager.load_playlist(pl_name)
        
        self.playlist = [] 
        self.song_widgets = []
        has_net = self.check_network_connection()

        if not items:
             ctk.CTkLabel(self.content_area, text=self.get_text("empty_folder"), text_color="gray").pack(pady=50)
             return

        for i, item in enumerate(items):
            path = item.get('path') or item.get('url')
            name = item.get('name') or item.get('title') or "Unknown"
            type_ = item.get('type', 'local')
            
            if not path: continue 
            
            # 本地文件获取实时名称，网络文件用缓存名称
            if type_ == "local" and os.path.exists(path):
                real_name = os.path.basename(path)
            else:
                real_name = name

            self.playlist.append(path)
            if not hasattr(self, 'online_titles'): self.online_titles = {}
            self.online_titles[path] = real_name
            
            row = ctk.CTkFrame(self.content_area, fg_color="transparent")
            row.pack(fill="x", pady=2)
            
            icon = "♫"
            if type_ == "online":
                icon = "☁️" if has_net else "☁️(❌)"
            
            # --- 核心修复：调用独立的排序方法 ---
            # 注意 lambda idx=i: ... 确保闭包捕获当前的 i
            ctk.CTkButton(
                row, text="▲", width=20, fg_color="transparent", text_color="gray", 
                command=lambda idx=i: self.reorder_playlist_item(pl_name, idx, -1)
            ).pack(side="left")
            
            ctk.CTkButton(
                row, text="▼", width=20, fg_color="transparent", text_color="gray", 
                command=lambda idx=i: self.reorder_playlist_item(pl_name, idx, 1)
            ).pack(side="left")
            
            # 移除按钮
            def remove_item(idx=i):
                # 重新读取并删除，防止索引偏移
                current_items = PlaylistManager.load_playlist(pl_name)
                if 0 <= idx < len(current_items):
                    current_items.pop(idx)
                    PlaylistManager.save_playlist(pl_name, current_items)
                    self.load_playlist_view(pl_name)

            ctk.CTkButton(row, text="🗑", width=30, fg_color="transparent", text_color="red", hover_color="#440000", command=remove_item).pack(side="right", padx=5)

            # 播放按钮
            display_text = f"{i+1}. {icon} {real_name}"
            btn = ctk.CTkButton(
                row, text=display_text, anchor="w", height=40, corner_radius=10, 
                fg_color=("white", "#252525"), text_color=("black", "white"), 
                hover_color=self.accent_color, 
                command=lambda idx=i: [self.animate_button_press(self.btn_play), self.play_playlist_item(idx)]
            )
            btn.pack(side="left", fill="x", expand=True, padx=5)
            self.song_widgets.append(btn)
            
        if self.player.current_song_path and self.player.current_song_path in self.playlist:
            self.highlight_current_song_only()
        
    def on_tree_select(self, event):
        sel = self.tree.selection()
        if sel: 
            val = self.tree.item(sel[0], "values")
            if not val: return # 可能是父节点
            
            path = val[0]
            if path.startswith("playlist::"):
                # 加载歌单视图
                pl_name = path.replace("playlist::", "")
                self.load_playlist_view(pl_name)
            else:
                # 加载普通文件夹
                self.load_songs_view(path)
        
    def update_treeview_style(self):
        mode = ctk.get_appearance_mode()
        style = ttk.Style()
        style.theme_use("clam")
        bg, fg = ("#f3f3f3", "black") if mode == "Light" else ("#1a1a1a", "white")
        sel = self.accent_color
        style.configure("Treeview", background=bg, foreground=fg, fieldbackground=bg, borderwidth=0, font=("Arial", 11), rowheight=28)
        style.map('Treeview', background=[('selected', sel)], foreground=[('selected', 'white')])

    def open_settings(self):
        # --- 修复：防止多开 ---
        if self.settings_window is not None and self.settings_window.winfo_exists():
            self.settings_window.lift() # 只是置顶
            self.settings_window.focus_force()
            return
        top = ctk.CTkToplevel(self)
        self.settings_window = top
        top.title(self.get_text("settings_title"))
        top.geometry("360x800") # 高度增加以容纳更多选项
        top.attributes("-topmost", True)
        
        # --- 动画准备 ---
        try: top.attributes("-alpha", 0.0)
        except: pass
        
        def close_settings_window():
            try:
                def animate_close(step=0):
                    try:
                        if step <= 15:
                            alpha = 1.0 - (step / 15)
                            top.attributes("-alpha", alpha)
                            top.after(10, lambda: animate_close(step + 1))
                        else:
                            top.destroy()
                            self.settings_window = None # 记得置空
                    except: 
                        top.destroy()
                        self.settings_window = None
                animate_close()
            except: 
                top.destroy()
                self.settings_window = None

        top.protocol("WM_DELETE_WINDOW", close_settings_window)
        
        # --- UI 内容 ---
        
        # 标题
        ctk.CTkLabel(top, text=self.get_text("settings_title"), font=("Arial", 20, "bold")).pack(pady=(20, 10))
        
        # 1. 语言设置
        ctk.CTkLabel(top, text=self.get_text("language"), anchor="w", font=("Arial", 12, "bold")).pack(fill="x", padx=30, pady=(10, 5))
        
        display_map = {"zh": "简体中文", "en": "English", "jp": "日本語", "fr": "Français", "de": "Deutsch"}
        loaded_codes = list(self.all_languages.keys())
        if not loaded_codes: loaded_codes = ["zh"]
        display_list = [display_map.get(code, code) for code in loaded_codes]
        current_display_name = display_map.get(self.current_lang_code, self.current_lang_code)
        
        def change_lang(val):
            selected_code = val
            for code, name in display_map.items():
                if name == val: selected_code = code; break
            if selected_code not in loaded_codes and val in loaded_codes: selected_code = val
            
            if selected_code != self.current_lang_code:
                self.current_lang_code = selected_code
                self.config["language"] = selected_code
                self.lang = self.all_languages.get(selected_code, {})
                ConfigManager.save_config(self.config)
                self.refresh_ui_appearance()
                top.destroy()
                self.open_settings()
        
        ctk.CTkOptionMenu(top, values=display_list, command=change_lang, variable=ctk.StringVar(value=current_display_name)).pack(fill="x", padx=30)

        # 2. 音乐源设置
        ctk.CTkLabel(top, text=self.get_text("source_settings"), anchor="w", font=("Arial", 12, "bold")).pack(fill="x", padx=30, pady=(15, 5))
        
        available_sources = [("yt", "source_yt"), ("sc", "source_sc"), ("url", "source_url")]
        self.source_vars = {} 
        current_enabled = self.config.get("enabled_sources", ["yt", "sc", "url"])

        def update_sources():
            new_enabled = [code for code, var in self.source_vars.items() if var.get()]
            if not new_enabled: 
                new_enabled = ["yt"]
                self.source_vars["yt"].set(True)
            
            self.config["enabled_sources"] = new_enabled
            ConfigManager.save_config(self.config)
            self.refresh_ui_appearance()

        for code, text_key in available_sources:
            is_checked = code in current_enabled
            var = ctk.BooleanVar(value=is_checked)
            self.source_vars[code] = var
            ctk.CTkCheckBox(top, text=self.get_text(text_key), variable=var, command=update_sources, border_width=2, fg_color=self.accent_color).pack(anchor="w", padx=30, pady=2)

        # 3. 外观模式
        ctk.CTkLabel(top, text=self.get_text("appearance"), anchor="w", font=("Arial", 12, "bold")).pack(fill="x", padx=30, pady=(15, 5))
        def change_theme_mode(val):
            ctk.set_appearance_mode(val)
            self.config['theme_mode'] = val
            self.after(100, self.update_treeview_style) # 强制刷新 treeview
            self.refresh_ui_appearance() # 强制刷新搜索框背景
        ctk.CTkSegmentedButton(top, values=["System", "Light", "Dark"], command=change_theme_mode, variable=ctk.StringVar(value=self.config.get("theme_mode", "System"))).pack(fill="x", padx=30, pady=5)
        
        # 4. 主题配色
        ctk.CTkLabel(top, text=self.get_text("theme_color"), anchor="w", font=("Arial", 12, "bold")).pack(fill="x", padx=30, pady=(15, 5))
        def change_accent_color(choice):
            color_code = COLOR_THEMES[choice]
            self.config['accent_color'] = color_code
            self.config['accent_name'] = choice
            self.accent_color = color_code
            self.refresh_ui_appearance()
            ConfigManager.save_config(self.config)
        color_menu = ctk.CTkOptionMenu(top, values=list(COLOR_THEMES.keys()), command=change_accent_color, fg_color=("gray75", "gray25"), button_color=("gray70", "gray20"), text_color=("black", "white"))
        color_menu.set(self.config.get("accent_name", "Default Blue"))
        color_menu.pack(fill="x", padx=30)

        # 5. 自定义资源
        ctk.CTkLabel(top, text=self.get_text("custom_res"), anchor="w", font=("Arial", 12, "bold")).pack(fill="x", padx=30, pady=(15, 5))
        def open_appdata():
            path = ConfigManager.get_appdata_path()
            try: os.startfile(path)
            except: messagebox.showinfo("Path", path)
        ctk.CTkButton(top, text=self.get_text("open_res_folder"), command=open_appdata, height=30, fg_color="transparent", border_width=1, text_color=("black", "white")).pack(fill="x", padx=30)
        
        # 6. 行为设置
        ctk.CTkLabel(top, text=self.get_text("behavior"), anchor="w", font=("Arial", 12, "bold")).pack(fill="x", padx=30, pady=(15, 5))
        
        # 最小化到托盘
        self.var_tray = ctk.BooleanVar(value=self.config['minimize_to_tray'])
        ctk.CTkSwitch(top, text=self.get_text("minimize_tray"), variable=self.var_tray, command=self.save_settings_ui, progress_color=self.accent_color).pack(padx=30, pady=5, anchor="w")
        
        # 在线自动播放
        self.var_online_auto = ctk.BooleanVar(value=self.config.get('online_autoplay', False))
        ctk.CTkSwitch(top, text=self.get_text("online_autoplay") if self.get_text("online_autoplay") != "online_autoplay" else "Online Autoplay", variable=self.var_online_auto, command=self.save_settings_ui, progress_color=self.accent_color).pack(padx=30, pady=5, anchor="w")
        
        # 自动下载封面 (新功能)
        self.var_auto_cover = ctk.BooleanVar(value=self.config.get('auto_fetch_cover', False))
        ctk.CTkSwitch(
            top, 
            text=self.get_text("auto_fetch_cover"), 
            variable=self.var_auto_cover, 
            command=self.save_settings_ui, 
            progress_color=self.accent_color
        ).pack(padx=30, pady=5, anchor="w")

        # 开机自启
        if os.name == 'nt':
            self.var_startup = ctk.BooleanVar(value=self.config['run_on_startup'])
            ctk.CTkSwitch(top, text=self.get_text("startup"), variable=self.var_startup, command=self.toggle_startup, progress_color=self.accent_color).pack(padx=30, pady=5, anchor="w")

        # 启动动画
        def fade_in(step=0):
            try:
                if step <= 15:
                    alpha = 1.0 - math.pow(1 - (step / 15), 3)
                    top.attributes("-alpha", alpha)
                    top.after(10, lambda: fade_in(step + 1))
                else:
                    top.attributes("-alpha", 1.0)
            except: pass 
            
        top.after(50, fade_in)

    def save_settings_ui(self):
        self.config['minimize_to_tray'] = self.var_tray.get()
        self.config['online_autoplay'] = self.var_online_auto.get()
        
        # 修复：保存封面设置
        if hasattr(self, 'var_auto_cover'):
            self.config['auto_fetch_cover'] = self.var_auto_cover.get()
            
        ConfigManager.save_config(self.config)
        
        if self.config['minimize_to_tray']: self.start_tray_icon()
        else: self.stop_tray_icon()

    def toggle_startup(self):
        val = self.var_startup.get()
        self.config['run_on_startup'] = val
        ConfigManager.save_config(self.config)
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_ALL_ACCESS)
            if val: winreg.SetValueEx(key, "PythonMusicPlayer", 0, winreg.REG_SZ, os.path.abspath(sys.argv[0]))
            else: winreg.DeleteValue(key, "PythonMusicPlayer")
            winreg.CloseKey(key)
        except: pass
    
    def start_mini_mode(self):
        """启动迷你模式 (带淡出动画)"""
        
        # 定义回调：淡出完成后执行
        def _switch_to_mini():
            # 1. 隐藏主窗口
            self.withdraw()
            
            # 如果配置了托盘，确保托盘存在
            if self.config['minimize_to_tray'] and self.tray_handler is None:
                self.start_tray_icon()
            
            # 2. 创建迷你窗口
            self.mini_window = MiniPlayerWindow(
                master_app=self, 
                player=self.player, 
                restore_callback=self.restore_from_mini, 
                accent_color=self.accent_color
            )

        # 执行淡出
        self.animate_fade_out(_switch_to_mini)

    def toggle_mode(self):
        """切换播放模式: 顺序 -> 单曲 -> 随机 -> 顺序"""
        # 清除可能存在的 "Shuffle All" 状态文字
        if hasattr(self, 'lbl_status'):
            self.lbl_status.configure(text="")

        # 状态机逻辑
        if self.playback_mode == "Order":
            self.playback_mode = "LoopOne"
            self.btn_mode.configure(text="🔂", text_color=self.accent_color)
        
        elif self.playback_mode == "LoopOne":
            self.playback_mode = "Shuffle"
            self.btn_mode.configure(text="🔀", text_color=self.accent_color)
        
        else:
            # --- 核心修复 2: 从 Shuffle 切回 Order 时的智能逻辑 ---
            # 如果当前正在播放本地文件，尝试锁定到该文件夹
            self.playback_mode = "Order"
            self.btn_mode.configure(text="➡", text_color=("black", "white"))
            
            current_path = self.player.current_song_path
            
            # 只有当路径存在，且不是网络链接，且当前列表不是该文件夹的内容时才重置
            if current_path and os.path.exists(current_path) and not current_path.startswith("http"):
                parent_dir = os.path.dirname(current_path)
                
                # 获取该文件夹下所有音频
                new_playlist = []
                try:
                    for f in os.listdir(parent_dir):
                        if self.is_audio_file(f):
                            new_playlist.append(os.path.join(parent_dir, f))
                    
                    # 排序 (按音轨或文件名)
                    new_playlist.sort(key=self.get_music_sort_key)
                    
                    # 更新列表
                    if new_playlist:
                        self.playlist = new_playlist
                        # 更新当前索引，确保继续播放时不跳歌
                        if current_path in self.playlist:
                            self.current_index = self.playlist.index(current_path)
                        
                        # 如果当前在列表视图，可能需要刷新UI显示新列表(可选)
                        # print(f"已锁定播放列表到文件夹: {parent_dir}")
                except: pass

    def move_favorite(self, path, direction):
        """
        调整收藏顺序
        direction: -1 (向前/左), 1 (向后/右)
        """
        favs = self.config.get('favorites', [])
        if path not in favs: return
        
        current_idx = favs.index(path)
        new_idx = current_idx + direction
        
        # 检查边界
        if 0 <= new_idx < len(favs):
            # 交换位置
            favs[current_idx], favs[new_idx] = favs[new_idx], favs[current_idx]
            
            # 保存配置
            self.config['favorites'] = favs
            ConfigManager.save_config(self.config)
            
            # 刷新首页显示
            self.show_home_view()

    def toggle_play(self):
        """播放/暂停开关"""
        if not self.playlist: return
        
        # 1. 如果正在播放 -> 暂停
        if self.player.is_playing():
            self.player.pause()
            
        # 2. 如果处于暂停状态 -> 恢复
        elif self.player.is_paused():
            self.player.unpause()
            
        # 3. 如果是停止状态 (既没播也没暂停) -> 重新开始
        else:
            # 检查当前是否是在线歌曲 (通过播放列表中的链接判断)
            current_item = self.playlist[self.current_index]
            
            if current_item.startswith("http"):
                # 在线歌曲：需要重新解析流地址并播放
                # 传入 current_index 以便重新触发流程
                self.prepare_online_play(self.current_index)
            else:
                # 本地歌曲：直接播放
                self.play_song(current_item)
            
        self.update_play_icon()

    def show_tree_context_menu(self, event):
        # 检查点击位置
        item_id = self.tree.identify_row(event.y)
        menu = Menu(self, tearoff=0)
        
        if item_id:
            # 点击了文件夹
            self.tree.selection_set(item_id)
            menu.add_command(label=self.get_text("ctx_change_cover"), command=self.change_folder_cover)
            menu.add_separator()
            menu.add_command(label=self.get_text("ctx_remove_folder"), command=self.remove_selected_folder)
        else:
            # 点击了空白处 -> 新建歌单
            menu.add_command(label=self.get_text("ctx_create_playlist"), command=self.create_playlist_dialog)
            
        menu.post(event.x_root, event.y_root)

    def open_add_to_playlist_dialog(self, path, name, type_):
        """弹出窗口选择歌单"""
        playlists = PlaylistManager.get_all_playlists()
        
        if not playlists:
            messagebox.showinfo("Info", "No playlists found.\nPlease create a playlist first (Right click on sidebar).")
            return

        # 创建选择窗口
        pl_win = ctk.CTkToplevel(self)
        pl_win.title(self.get_text("playlist_select_title"))
        pl_win.geometry("300x400")
        pl_win.attributes("-topmost", True)
        
        # 标题
        ctk.CTkLabel(pl_win, text=f"Add: {name[:15]}...", font=("Arial", 14, "bold")).pack(pady=10)
        
        # 滚动区域显示所有歌单
        scroll = ctk.CTkScrollableFrame(pl_win, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        def add_and_close(pl_name):
            # 准备数据
            info = {
                "type": type_,
                "name": name,
                # 只有对应类型的字段才有值
                "path": path if type_ == "local" else None,
                "url": path if type_ == "online" else None
            }
            # 清理 None 字段，保持 json 干净
            if info["path"] is None: del info["path"]
            if info["url"] is None: del info["url"]
            
            PlaylistManager.add_song(pl_name, info)
            
            # 提示并关闭
            # messagebox.showinfo("Success", f"{self.get_text('msg_added_to_playlist')} : {pl_name}")
            pl_win.destroy()

        # 渲染列表
        for pl in playlists:
            ctk.CTkButton(
                scroll, 
                text=f"📜 {pl}", 
                anchor="w",
                fg_color=("white", "#333"),
                text_color=("black", "white"),
                hover_color=self.accent_color,
                command=lambda x=pl: add_and_close(x)
            ).pack(fill="x", pady=2)

    def create_playlist_dialog(self):
        """创建歌单对话框"""
        dialog = ctk.CTkInputDialog(
            text=self.get_text("playlist_input_msg"), 
            title=self.get_text("playlist_input_title")
        )
        name = dialog.get_input()
        if name:
            if PlaylistManager.create_playlist(name):
                self.refresh_sidebar_tree()
            else:
                messagebox.showerror("Error", self.get_text("err_playlist_exists"))


    def update_play_icon(self):
        """根据状态更新播放按钮图标"""
        # 逻辑：
        # 1. 如果正在播放 (包括缓冲中) -> 显示 ⏸
        # 2. 如果是暂停 -> 显示 ▶
        # 3. 如果是停止 (既不播也不停) -> 显示 ▶
        
        if self.player.is_playing() and not self.player.is_paused():
            txt = "⏸"
        else:
            txt = "▶"
            
        try:
            self.btn_play.configure(text=txt)
        except: pass

    def play_next(self, auto=False):
        """播放下一首"""
        if not self.playlist: return
        
        # --- 修复：移除这里的锁检查，允许强制切歌 ---
        # if self.is_switching_song: return 

        next_idx = 0
        
        if self.playback_mode == "LoopOne" and auto:
            next_idx = self.current_index
        elif self.playback_mode == "Shuffle":
            if len(self.playlist) > 1:
                new_idx = self.current_index
                # 防止随机到同一首
                while new_idx == self.current_index:
                    new_idx = random.randint(0, len(self.playlist)-1)
                next_idx = new_idx
            else:
                next_idx = 0
        else:
            # Order 模式
            next_idx = (self.current_index + 1) % len(self.playlist)
            
        # 获取下一首
        next_item = self.playlist[next_idx]
        
        # 执行播放
        if next_item.startswith("http"):
            # 在线：上锁，进入异步流程
            self.is_switching_song = True
            self.prepare_online_play(next_idx)
        else:
            # 本地：直接播放 (play_song 内部会重置锁)
            self.play_song(next_item)
            if next_item in self.online_titles:
                clean_title = self.online_titles[next_item]
                self.lbl_song_name.configure(text=clean_title)
                if self.tray_handler: self.tray_handler.update_tooltip(f"Playing: {clean_title}")

    def play_prev(self):
        """播放上一首"""
        if not self.playlist: return
        prev_idx = (self.current_index - 1) % len(self.playlist)
        
        # --- 修复：检查是否为在线链接 ---
        prev_item = self.playlist[prev_idx]
        if prev_item.startswith("http"):
            self.prepare_online_play(prev_idx)
        else:
            self.play_song(self.playlist[prev_idx])

    def clear_content(self):
        """清空右侧内容区域的所有控件 (增强版)"""
        for w in self.content_area.winfo_children(): 
            w.destroy()
        
        # 强制刷新 UI，确保销毁操作立即生效，防止重复加载
        self.content_area.update_idletasks()

    def on_volume_change(self, value):
        """调节音量"""
        val = float(value)
        self.player.set_volume(val)
        self.config['volume'] = val
        # 同步滑块位置 (防止循环触发)
        if hasattr(self, 'vol_slider') and abs(self.vol_slider.get() - val) > 0.01: 
            self.vol_slider.set(val)

    def monitor_music_status(self):
        """监控歌曲是否播放结束，自动切歌 (高容错版)"""
        try:
            # 1. 基础检查
            if not self.winfo_exists(): return
            
            # 2. 自动解锁机制 (防止卡死)
            # 如果播放器已经开始播放了，说明切歌动作肯定完成了，强制解锁
            if self.player.is_playing():
                self.is_switching_song = False

            # 3. 检查锁
            if self.is_switching_song:
                self._monitor_loop_id = self.after(1000, self.monitor_music_status)
                return
            
            # 4. 冷却锁 (防止拖拽进度条时误判)
            if time.time() - self.last_seek_time < 2.0:
                self._monitor_loop_id = self.after(1000, self.monitor_music_status)
                return

            # 5. 检测是否播放结束
            if self.player.check_if_song_finished():
                # 获取当前播放的项 (用于判断类型)
                current_item = ""
                if self.playlist and 0 <= self.current_index < len(self.playlist):
                    current_item = self.playlist[self.current_index]
                
                is_online = current_item.startswith("http")
                
                # --- 决策逻辑 ---
                should_play_next = False
                
                if self.playback_mode == "LoopOne":
                    # 单曲循环：总是重播
                    should_play_next = True
                
                elif is_online:
                    # 在线歌曲：看设置
                    if self.config.get("online_autoplay", False):
                        should_play_next = True
                    else:
                        # 如果没开自动播放，但模式是 Shuffle，通常也希望能切歌？
                        # 根据你的需求：只要设置关闭，就停下 (除非单曲)
                        should_play_next = False
                
                else:
                    # 本地歌曲：总是切下一首 (Order/Shuffle)
                    should_play_next = True

                # --- 执行动作 ---
                if should_play_next:
                    # 打印调试信息 (可选)
                    # print(f"Auto playing next... Mode: {self.playback_mode}")
                    self.play_next(auto=True)
                else:
                    self.player.stop()
                    self.update_play_icon()
        
        except Exception as e:
            print(f"Monitor Error: {e}")
            # 即使出错，也要重置锁，保证下次循环能跑
            self.is_switching_song = False

        # 6. 继续循环
        self._monitor_loop_id = self.after(1000, self.monitor_music_status)
    def restore_from_mini(self):
        """从迷你模式恢复"""
        # 1. 先把窗口设为透明 (用户不可见)
        self._safe_set_alpha(0.0)
        
        # 2. 唤醒窗口
        self.deiconify()
        
        self.mini_window = None
        self.update_play_icon()
        
        try:
            self.lift()
            self.focus_force()
        except: pass

        # 3. 延迟一小会儿开始动画 (确保 deiconify 已完成)
        self.after(50, lambda: self.animate_fade_in_elastic(step=1))

    def start_tray_icon(self):
        """启动系统托盘图标 (常驻)"""
        if self.tray_handler is not None:
            return # 已经在运行，不重复创建

        icon_p = self.tray_icon_path if os.path.exists(self.tray_icon_path) else None
        # 注意：这里的 quit_app 是彻底退出
        self.tray_handler = TrayHandler(self, self.restore_from_tray, self.quit_app, icon_p)
        self.tray_handler.run()

    def stop_tray_icon(self):
        """停止系统托盘图标"""
        if self.tray_handler:
            self.tray_handler.stop()
            self.tray_handler = None
            
    def restore_from_tray(self, icon=None, item=None):
        # 1. 先隐身
        self._safe_set_alpha(0.0)
        
        # 2. 显示
        self.deiconify()
        
        # 3. 停止托盘 (如果设置了常驻，可以注释掉这行，根据你的需求)
        # self.stop_tray_icon() 
        
        if self.mini_window:
            self.mini_window.destroy()
            self.mini_window = None

        try:
            self.lift()
            self.focus_force()
        except: pass
        
        # 4. 延迟淡入
        self.after(50, lambda: self.animate_fade_in_elastic(step=1))

    def on_close_window(self):
        """点击关闭按钮的行为"""
        ConfigManager.save_config(self.config)
        if self.config['minimize_to_tray']: 
            # 确保托盘已启动
            self.start_tray_icon()
            # 淡出并隐藏窗口 (不退出程序)
            self.animate_fade_out(self.withdraw)
        else:
            # 彻底退出
            self.animate_fade_out(self.quit_app)

    def quit_app(self, icon=None, item=None):
        """彻底退出程序"""
        # --- 修复：强制取消所有挂起的循环 ---
        if self._monitor_loop_id:
            try: self.after_cancel(self._monitor_loop_id)
            except: pass
            self._monitor_loop_id = None
            
        if self._progress_loop_id:
            try: self.after_cancel(self._progress_loop_id)
            except: pass
            self._progress_loop_id = None
            
        self.stop_tray_icon()
        self.player.stop()
        self.destroy()
        sys.exit()
        #Attributions
        #App Icon : Icon made by Freepik from www.flaticon.com