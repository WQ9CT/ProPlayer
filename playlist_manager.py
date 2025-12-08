import json
import os
from config_manager import ConfigManager

class PlaylistManager:
    @staticmethod
    def get_all_playlists():
        """返回所有歌单名称 (不含后缀)"""
        pl_dir = ConfigManager.get_playlist_dir()
        files = [f for f in os.listdir(pl_dir) if f.endswith('.json')]
        return [os.path.splitext(f)[0] for f in files]

    @staticmethod
    def create_playlist(name):
        """创建新歌单"""
        pl_dir = ConfigManager.get_playlist_dir()
        path = os.path.join(pl_dir, f"{name}.json")
        if os.path.exists(path): return False
        
        data = {"name": name, "items": []}
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        return True

    @staticmethod
    def load_playlist(name):
        """加载歌单内容"""
        pl_dir = ConfigManager.get_playlist_dir()
        path = os.path.join(pl_dir, f"{name}.json")
        if not os.path.exists(path): return []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("items", [])
        except: return []

    @staticmethod
    def add_song(playlist_name, song_info):
        """添加歌曲到歌单 (智能查重)"""
        pl_dir = ConfigManager.get_playlist_dir()
        path = os.path.join(pl_dir, f"{playlist_name}.json")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # --- 修复：智能查重逻辑 ---
            # 获取新歌曲的唯一标识 (本地是 path, 网络是 url)
            new_id = song_info.get('path') or song_info.get('url')
            
            if not new_id: return # 数据无效
            
            for item in data['items']:
                # 获取现有歌曲的唯一标识
                existing_id = item.get('path') or item.get('url')
                
                # 如果标识符相同，视为重复，不添加
                if existing_id == new_id:
                    return 
            
            data['items'].append(song_info)
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception as e: 
            print(f"Add to playlist error: {e}")

    @staticmethod
    def save_playlist(name, items):
        """保存整个歌单列表 (用于排序/删除)"""
        pl_dir = ConfigManager.get_playlist_dir()
        path = os.path.join(pl_dir, f"{name}.json")
        data = {"name": name, "items": items}
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except: pass

    @staticmethod
    def delete_playlist(name):
        pl_dir = ConfigManager.get_playlist_dir()
        path = os.path.join(pl_dir, f"{name}.json")
        try: os.remove(path)
        except: pass