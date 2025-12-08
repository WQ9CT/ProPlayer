import time
import customtkinter as ctk
import math

class SleepTimer:
    def __init__(self):
        self.target_time = None
        self.action = "stop" 

    def start(self, minutes, action):
        self.target_time = time.time() + (minutes * 60)
        self.action = action

    def stop(self):
        self.target_time = None

    def is_active(self):
        return self.target_time is not None

    def check_expired(self):
        if self.target_time and time.time() > self.target_time:
            self.target_time = None
            return True
        return False

    def get_remaining_text(self):
        if not self.target_time: return ""
        remaining = int(self.target_time - time.time())
        if remaining < 0: return "0m"
        m, s = divmod(remaining, 60)
        h, m = divmod(m, 60)
        if h > 0: return f"{h}h {m}m"
        return f"{m}m {s}s"


class TimerInputDialog(ctk.CTkToplevel):
    def __init__(self, master, current_accent, on_start_callback):
        super().__init__(master)
        self.master_app = master
        self.on_start = on_start_callback
        self.accent = current_accent
        
        # 熔断开关
        self.can_use_alpha = True
        
        self.title(master.get_text("timer_title"))
        self.geometry("350x280")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        
        # 尝试初始透明
        if not self._safe_set_alpha(0.0):
            self.can_use_alpha = False
        
        try:
            x = master.winfo_x() + (master.winfo_width() // 2) - 175
            y = master.winfo_y() + (master.winfo_height() // 2) - 140
            self.geometry(f"+{x}+{y}")
        except: pass

        self.setup_ui()
        
        # 启动淡入
        self.after(100, self.lift)
        self.after(50, self.animate_fade_in)

    # --- 核心修复：安全动画逻辑 ---
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
        
        if step <= 15:
            alpha = 1.0 - math.pow(1 - (step / 15), 3)
            if self._safe_set_alpha(alpha):
                self.after(16, lambda: self.animate_fade_in(step + 1))
        else:
            self._safe_set_alpha(1.0)

    def close_with_fade(self):
        """淡出并关闭"""
        self.animate_fade_out(self.destroy)

    def animate_fade_out(self, callback, step=0):
        # 如果不支持动画，直接关闭
        if not self.can_use_alpha:
            callback()
            return

        if step <= 15:
            alpha = 1.0 - (step / 15)
            if self._safe_set_alpha(alpha):
                self.after(16, lambda: self.animate_fade_out(callback, step + 1))
            else:
                callback()
        else:
            callback()

    def setup_ui(self):
        ctk.CTkLabel(self, text=self.master_app.get_text("timer_title"), font=("Arial", 18, "bold")).pack(pady=(20, 15))
        
        # 这里的 placeholder 已经包含了提示，不自动聚焦
        self.entry = ctk.CTkEntry(self, placeholder_text=self.master_app.get_text("timer_placeholder"), width=200)
        self.entry.pack(pady=5)
        
        self.var_action = ctk.StringVar(value="stop")
        radio_frame = ctk.CTkFrame(self, fg_color="transparent")
        radio_frame.pack(pady=15, padx=40, fill="x")
        
        r1 = ctk.CTkRadioButton(radio_frame, text=self.master_app.get_text("timer_action_stop"), variable=self.var_action, value="stop", fg_color=self.accent, hover_color=self.accent)
        r1.pack(anchor="w", pady=5)
        r2 = ctk.CTkRadioButton(radio_frame, text=self.master_app.get_text("timer_action_quit"), variable=self.var_action, value="quit", fg_color=self.accent, hover_color=self.accent)
        r2.pack(anchor="w", pady=5)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10, fill="x", padx=40)
        
        # 取消按钮绑定淡出关闭
        ctk.CTkButton(btn_frame, text=self.master_app.get_text("timer_cancel"), fg_color="transparent", border_width=1, text_color=("gray10", "gray90"), width=100, command=self.close_with_fade).pack(side="left", padx=(0, 10))
        
        ctk.CTkButton(btn_frame, text=self.master_app.get_text("timer_start"), fg_color=self.accent, hover_color=self.accent, width=150, command=self.confirm).pack(side="right")

    def confirm(self):
        try:
            val = self.entry.get().strip()
            if not val: return
            minutes = float(val)
            if minutes <= 0: return
            self.on_start(minutes, self.var_action.get())
            self.close_with_fade()
        except ValueError:
            self.entry.delete(0, "end")
            self.entry.configure(placeholder_text="Number only!")
            self.after(100, self.entry.focus_set)