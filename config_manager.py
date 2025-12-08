import json
import os
import sys

DEFAULT_CONFIG = {
    "volume": 0.5,
    "folders": [],
    "favorites": [],
    "folder_covers": {},
    "bg_image": "",
    "minimize_to_tray": False,
    "run_on_startup": False,
    "theme_mode": "System",
    "accent_color": "#3B8ED0",
    "accent_name": "Default Blue",
    "language": "zh",
    "online_autoplay": False,  # 新增：在线播放是否自动下一首
    "enabled_sources": ["yt", "sc", "url"],
    "auto_fetch_cover": False
}

class ConfigManager:
    @staticmethod
    def get_exe_dir():
        if getattr(sys, 'frozen', False): return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))

    @staticmethod
    def get_internal_path(relative_path):
        if hasattr(sys, '_MEIPASS'): return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

    @staticmethod
    def get_appdata_path(filename=None):
        base_dir = ConfigManager.get_exe_dir()
        appdata_dir = os.path.join(base_dir, 'appdata')
        if not os.path.exists(appdata_dir):
            try: os.makedirs(appdata_dir)
            except: pass
        if filename: return os.path.join(appdata_dir, filename)
        return appdata_dir
    
    @staticmethod
    def get_download_path():
        base_dir = ConfigManager.get_exe_dir()
        dl_dir = os.path.join(base_dir, 'download')
        if not os.path.exists(dl_dir):
            try: os.makedirs(dl_dir)
            except: pass
        return dl_dir
    
    # --- 新增：获取歌单文件夹 ---
    @staticmethod
    def get_playlist_dir():
        base_dir = ConfigManager.get_exe_dir()
        pl_dir = os.path.join(base_dir, 'playlists')
        if not os.path.exists(pl_dir):
            try: os.makedirs(pl_dir)
            except: pass
        return pl_dir

    @staticmethod
    def get_config_path():
        return os.path.join(ConfigManager.get_exe_dir(), 'config.json')

    # --- 新增：获取在线歌曲缓存文件路径 ---
    @staticmethod
    def get_online_cache_path():
        return os.path.join(ConfigManager.get_exe_dir(), 'saved_online_songs.json')

    # --- 新增：加载在线歌曲缓存 ---
    @staticmethod
    def load_online_cache():
        path = ConfigManager.get_online_cache_path()
        if not os.path.exists(path):
            # 如果没有，创建一个空的并返回
            ConfigManager.save_online_cache({})
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}

    # --- 新增：保存在线歌曲缓存 ---
    @staticmethod
    def save_online_cache(data):
        path = ConfigManager.get_online_cache_path()
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except: pass

    @staticmethod
    def load_config():
        path = ConfigManager.get_config_path()
        if not os.path.exists(path):
            ConfigManager.save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                changed = False
                for k, v in DEFAULT_CONFIG.items():
                    if k not in data:
                        data[k] = v
                        changed = True
                if changed: ConfigManager.save_config(data)
                return data
        except: return DEFAULT_CONFIG.copy()

    @staticmethod
    def save_config(config_data):
        path = ConfigManager.get_config_path()
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
        except: pass

    @staticmethod
    def get_app_version():
        """读取程序目录下的 version.txt"""
        try:
            # 获取 exe 所在目录
            base_dir = ConfigManager.get_exe_dir()
            version_path = os.path.join(base_dir, 'version.txt')
            
            if os.path.exists(version_path):
                with open(version_path, 'r', encoding='utf-8') as f:
                    return f.read().strip() # 去除首尾空格
        except:
            pass
        return "" # 如果不存在或读取失败，返回空字符串
    
    @staticmethod
    def load_language_pack():
        lang_dir = ConfigManager.get_internal_path('language')
        languages = {}
        if not os.path.exists(lang_dir): return languages
        try:
            for filename in os.listdir(lang_dir):
                if filename.endswith('.json'):
                    lang_code = os.path.splitext(filename)[0]
                    full_path = os.path.join(lang_dir, filename)
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                            if not content: continue
                            languages[lang_code] = json.loads(content)
                    except: continue
            return languages
        except: return {}