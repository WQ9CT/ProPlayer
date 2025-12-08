import customtkinter as ctk
import math

class StartupScreen(ctk.CTkToplevel):
    def __init__(self, parent, accent_color="#3B8ED0", app_title="Python Pro Player", version_text=""):
        super().__init__(parent)
        
        self.is_running = True
        
        # 1. 窗口设置
        self.overrideredirect(True) 
        self.attributes("-topmost", True) 
        self.configure(fg_color="#1a1a1a")
        
        # 2. 居中计算
        try:
            ws = self.winfo_screenwidth()
            hs = self.winfo_screenheight()
            w, h = 400, 280
            x = (ws - w) // 2
            y = (hs - h) // 2
            self.geometry(f"{w}x{h}+{x}+{y}")
        except:
            self.geometry("400x280")
            
        # 3. UI 构建
        self.container = ctk.CTkFrame(self, fg_color="#1a1a1a", border_width=2, border_color=accent_color, corner_radius=0)
        self.container.pack(fill="both", expand=True)
        
        self.lbl_icon = ctk.CTkLabel(self.container, text="♫", font=("Impact", 80), text_color=accent_color)
        self.lbl_icon.pack(pady=(30, 10))
        
        self.lbl_title = ctk.CTkLabel(self.container, text=app_title, font=("Arial", 20, "bold"), text_color="white")
        self.lbl_title.pack()

        self.lbl_load = ctk.CTkLabel(self.container, text="Initializing...", font=("Arial", 12), text_color="gray")
        self.lbl_load.pack(side="bottom", pady=(0, 20))

        # 进度条
        self.progress_bar = ctk.CTkProgressBar(self.container, width=300, height=4, corner_radius=2, progress_color=accent_color, fg_color="#333")
        self.progress_bar.set(0.0)
        self.progress_bar.pack(side="bottom", pady=(0, 10))

        # 版本号
        if version_text:
            self.lbl_ver = ctk.CTkLabel(self.container, text=version_text, font=("Arial", 10), text_color="gray30")
            self.lbl_ver.place(relx=0.98, rely=0.98, anchor="se")
        
        # --- 核心修改：直接设置为不透明，不搞淡入动画 ---
        try: 
            self.attributes("-alpha", 1.0)
        except: pass
        
        # 强制刷新显示
        self.deiconify()
        self.update()

    def set_status(self, text, progress_val):
        """更新状态和进度条"""
        if not self.winfo_exists(): return
        try:
            self.lbl_load.configure(text=text)
            self.progress_bar.set(progress_val)
            # 关键：强制刷新 UI，否则主程序忙碌时界面不会动
            self.update() 
        except: pass

    def close(self):
        """加载完成，执行淡出关闭"""
        self.animate_fade_out()

    def animate_fade_out(self, step=0):
        if not self.winfo_exists(): return
        try:
            if step <= 15:
                # 快速淡出
                alpha = 1.0 - math.pow(step / 15, 2)
                self.attributes("-alpha", alpha)
                self.update_idletasks()
                self.after(16, lambda: self.animate_fade_out(step + 1))
            else:
                self.safe_destroy()
        except: 
            self.safe_destroy()
            
    def safe_destroy(self):
        self.is_running = False
        try:
            self.destroy()
            self.update()
        except: pass