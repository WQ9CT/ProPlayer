import os
import sys
import time
from mutagen import File 
from PIL import Image
import io

# 1. 智能识别 VLC 路径
if hasattr(sys, '_MEIPASS'):
    vlc_path = os.path.join(sys._MEIPASS, 'vlc_libs')
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    vlc_path = os.path.join(base_dir, 'vlc_libs')

if os.name == 'nt':
    if os.path.exists(os.path.join(vlc_path, 'libvlc.dll')):
        os.environ['PYTHON_VLC_MODULE_PATH'] = vlc_path
        os.environ['PATH'] = vlc_path + ";" + os.environ['PATH']
    else:
        print(f"Warning: VLC libs not found at {vlc_path}")

import vlc

class AudioPlayer:
    def __init__(self):
        try:
            self.instance = vlc.Instance()
            self.media_player = self.instance.media_player_new()
        except Exception as e:
            print(f"VLC Init Error: {e}")
            self.instance = None
            self.media_player = None

        self.current_song_path = None
        self.is_playing_flag = False

    def load_and_play(self, path, start_time=0.0):
        try:
            self.current_song_path = path
            if not self.instance: return

            media = self.instance.media_new(path)
            self.media_player.set_media(media)
            self.media_player.play()
            self.is_playing_flag = True
            
            if start_time > 0:
                # 给一点缓冲时间再跳转
                time.sleep(0.2) 
                self.media_player.set_time(int(start_time * 1000))
                
        except Exception as e:
            print(f"VLC Play Error: {e}")
            self.is_playing_flag = False

    def pause(self):
        if self.media_player: self.media_player.pause()

    def unpause(self):
        if self.media_player: self.media_player.play()

    def stop(self):
        if self.media_player: self.media_player.stop()
        self.is_playing_flag = False

    def set_volume(self, volume):
        if self.media_player:
            # VLC 音量是 0-100
            vol_int = int(volume * 100)
            self.media_player.audio_set_volume(vol_int)

    def get_volume(self):
        if self.media_player:
            return self.media_player.audio_get_volume() / 100.0
        return 0.5

    def seek(self, time_pos):
        if self.media_player:
            # VLC 跳转单位是毫秒
            self.media_player.set_time(int(time_pos * 1000))

    def get_current_length(self):
        if self.media_player:
            length_ms = self.media_player.get_length()
            # --- 核心修复：毫秒转秒，除以 1000.0 ---
            if length_ms > 0: 
                return length_ms / 1000.0
        return 0
    
    def get_current_position(self):
        if self.media_player:
            # --- 核心修复：毫秒转秒，除以 1000.0 ---
            return self.media_player.get_time() / 1000.0
        return 0

    def is_playing(self):
        if not self.media_player: return False
        state = self.media_player.get_state()
        return state in [vlc.State.Playing, vlc.State.Buffering, vlc.State.Opening]

    def is_paused(self):
        if not self.media_player: return False
        return self.media_player.get_state() == vlc.State.Paused

    def check_if_song_finished(self):
        if not self.media_player: return False
        return self.media_player.get_state() == vlc.State.Ended

    def get_embedded_cover(self, file_path):
        if not os.path.exists(file_path): return None 
        try:
            file = File(file_path)
            if not file: return None
            artwork_data = None
            if hasattr(file, 'tags') and file.tags:
                for key in file.tags.keys():
                    if key.startswith('APIC'):
                        artwork_data = file.tags[key].data
                        break
            if not artwork_data and hasattr(file, 'pictures') and file.pictures:
                artwork_data = file.pictures[0].data
            if artwork_data:
                return Image.open(io.BytesIO(artwork_data))
        except: pass
        return None