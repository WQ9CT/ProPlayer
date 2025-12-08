import tkinter
import sys
import os
import shutil

# ==================================================================
# 🛡️ 底层拦截透明度指令 (Monkey Patch) - 最终放行版
# ==================================================================

_original_wm_attributes = tkinter.Wm.wm_attributes

def safe_wm_attributes(self, *args, **kwargs):
    """
    这是 Tkinter 底层方法的替身。
    修正逻辑：不再主动拦截 -alpha，而是大胆尝试执行。
    只有当操作系统抛出 TclError (不支持) 时，才捕获并忽略。
    这样支持透明度的电脑就能看到丝滑动画了。
    """
    
    # 移除之前的 forbidden_keys 列表，不再主动封杀
    # forbidden_keys = ['-alpha'] <-- 删除这行逻辑

    try:
        # 尝试直接调用原始方法
        return _original_wm_attributes(self, *args, **kwargs)
    except tkinter.TclError as e:
        # 只有在真正报错时才介入
        err_msg = str(e).lower()
        if "transparency" in err_msg or "alpha" in err_msg:
            # print(f"🛡️ 系统不支持透明度，已忽略错误: {e}") # 调试用
            return
        # 如果是其他错误，照常抛出（方便调试）
        raise e

# 偷梁换柱
tkinter.Wm.wm_attributes = safe_wm_attributes
tkinter.Wm.attributes = safe_wm_attributes

# ==================================================================

from gui import MusicPlayerGUI

if __name__ == "__main__":
    try:
        # 1. 清理缓存
        base_dir = os.path.dirname(os.path.abspath(__file__))
        cache_dir = os.path.join(base_dir, "__pycache__")
        if os.path.exists(cache_dir):
            try: shutil.rmtree(cache_dir)
            except: pass
            
        # 2. 启动主程序
        # (StartupScreen 会在 MusicPlayerGUI 内部自动调用)
        app = MusicPlayerGUI()
        app.mainloop()
        
    except Exception as e:
        try:
            import tkinter.messagebox
            tkinter.messagebox.showerror("Critical Error", f"程序无法启动:\n{e}")
        except:
            print(f"CRASH: {e}")
            input("Press Enter...")