#🎵 ProPlayer - Python Music Player
中文说明 | English Documentation
🇨🇳 中文说明
ProPlayer 是一款基于 Python 开发的现代桌面音乐播放器。它不仅支持播放本地音频文件，还集成了强大的网络搜索功能，让您可以直接搜索并播放 YouTube 和 SoundCloud 上的音乐。
#✨ 主要功能
双模播放：无缝支持本地文件（MP3, FLAC, WAV等）和网络流媒体。
全能搜索：支持 YouTube、SoundCloud 搜索，甚至可以直接粘贴 Bilibili 等网站的链接播放。
沉浸体验：提供 迷你模式 (悬浮窗) 和 全屏专注模式。
歌单管理：支持创建自定义歌单，混合添加本地和网络歌曲。
贴心工具：内置 睡眠定时器，支持自动提取专辑封面。
自动更新：软件内置自动更新功能，无需手动重复下载新版本。
个性化：支持深色/浅色模式及多种主题配色。
#📥 下载与安装指南 (新用户必读)
ProPlayer 是绿色免安装软件 (Portable)，下载解压即可使用。
第一步：下载
点击页面右侧的 Releases (发行版)。
找到最新的版本（例如 v1.0.0）。
在 "Assets" 区域，下载压缩包文件（通常命名为 ProPlayer_vX.X.zip）。
注意：请勿只下载源代码 (Source code)，除非您是开发者。
第二步：解压 (非常重要！)
下载完成后，请不要直接在压缩包里双击运行！
请右键点击压缩包，选择 “全部解压缩” 或 “解压到当前文件夹”。
将解压出来的文件夹放在您喜欢的地方（例如桌面或 D 盘）。
第三步：启动程序
打开解压后的文件夹。
找到并双击 ProPlayer.exe (或者 ProPlayer)。
这是启动器，它会自动检查更新并启动主程序。
🎉 享受音乐吧！
⚠️ 注意事项：
请不要移动或删除文件夹内的 bin, vlc_libs, language 等文件夹，否则程序将无法运行。
bin/Core.exe 是核心程序，请不要直接点击它，始终通过 ProPlayer.exe 启动以确保存档和更新功能正常。
#🇺🇸 English Documentation
ProPlayer is a modern desktop music player built with Python. It seamlessly integrates local file playback with powerful online streaming capabilities, allowing you to search and play music directly from YouTube and SoundCloud.
#✨ Key Features
Hybrid Playback: Seamlessly plays local files (MP3, FLAC, WAV, etc.) and online streams.
Universal Search: Search YouTube, SoundCloud, or paste direct links (e.g., from Bilibili/Bandcamp).
Immersive Modes: Includes a Mini Mode (floating widget) and a Full Screen Mode.
Playlist Management: Create custom playlists with mixed local and online tracks.
Utilities: Built-in Sleep Timer and automatic album art fetching.
Auto Updates: The software updates itself automatically via the launcher.
Customization: Supports Dark/Light modes and multiple color themes.
#📥 Installation Guide (For New Users)
ProPlayer is Portable, meaning no installation wizard is required. Just unzip and run.
Step 1: Download
Click on Releases on the right side of this page.
Find the latest version tag (e.g., v1.0.0).
Under "Assets", download the zip file (usually named ProPlayer_vX.X.zip).
Note: Do not download the "Source code" unless you are a developer.
Step 2: Unzip (Crucial!)
Once downloaded, DO NOT run the file directly inside the zip archive.
Right-click the zip file and select "Extract All" or "Extract Here".
Place the extracted folder wherever you like (e.g., Desktop or Documents).
Step 3: Run
Open the extracted folder.
Find and double-click ProPlayer.exe (application with the icon).
This is the Launcher. It checks for updates and starts the main app.
🎉 Enjoy your music!
⚠️ Important Notes:
Please DO NOT move or delete internal folders like bin, vlc_libs, or language. They are required for the app to function.
bin/Core.exe is the internal core file. Please always start with ProPlayer.exe to ensure updates and data saving work correctly.
👨‍💻 For Developers / 开发者信息
Language: Python 3.11+
GUI Framework: CustomTkinter
Audio Engine: VLC (python-vlc) & Pygame (Initial version)
Streaming: yt-dlp
Build Tool: PyInstaller
Run from source / 源码运行:
code
Bash
pip install customtkinter yt-dlp python-vlc mutagen pillow pystray packaging requests
python main.py
Made by wq with ❤️
