import yt_dlp
import threading
import os
from config_manager import ConfigManager

class MusicSourceHandler:
    def __init__(self, download_folder=None):
        pass

    def _get_ffmpeg_location(self):
        # 获取 ffmpeg 路径 (如果需要下载功能)
        base_dir = ConfigManager.get_exe_dir()
        bin_dir = os.path.join(base_dir, 'bin')
        ffmpeg_exe = os.path.join(bin_dir, 'ffmpeg.exe')
        if os.path.exists(ffmpeg_exe): return bin_dir
        # 尝试内部路径
        internal_bin = ConfigManager.get_internal_path('bin')
        if os.path.exists(os.path.join(internal_bin, 'ffmpeg.exe')): return internal_bin
        return None

    def search(self, query, source="yt", limit=10):
        """搜索并返回信息"""
        results = []
        
        # 万能链接模式
        if source == "url":
            return [{
                'title': 'Direct Link',
                'uploader': 'External Source',
                'duration': 0,
                'url': query,
                'source': 'Direct URL',
                'id': 'url'
            }]

        prefix = "ytsearch" if source == "yt" else "scsearch"
        search_query = f"{prefix}{limit}:{query}"
        
        # 优化搜索参数
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'extract_flat': True, # 关键：只提取元数据，不解析流
            'ignoreerrors': True,
            'no_warnings': True,
            'default_search': 'auto',
            'source_address': '0.0.0.0', # 有时候能解决 ipv6 问题
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                if 'entries' in info:
                    for entry in info['entries']:
                        if not entry: continue
                        # 提取信息，提供默认值防止报错
                        results.append({
                            'title': entry.get('title', 'Unknown Title'),
                            'uploader': entry.get('uploader', 'Unknown Artist'),
                            'duration': entry.get('duration', 0),
                            'url': entry.get('url') or entry.get('webpage_url'),
                            'source': 'YouTube' if source == 'yt' else 'SoundCloud',
                            'id': entry.get('id')
                        })
        except Exception as e:
            print(f"Search Error: {e}")
            
        return results

    def get_stream_url(self, webpage_url, callback):
        """获取真实的媒体流地址"""
        def run():
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'noplaylist': True,
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(webpage_url, download=False)
                    real_url = info.get('url')
                    title = info.get('title')
                    callback(real_url, title)
            except Exception as e:
                print(f"Stream extraction error: {e}")
                callback(None, None)

        threading.Thread(target=run, daemon=True).start()

    @staticmethod
    def format_seconds(seconds):
        if not seconds: return "00:00"
        try:
            seconds = int(seconds)
            m, s = divmod(seconds, 60)
            return f"{m:02d}:{s:02d}"
        except: return "00:00"