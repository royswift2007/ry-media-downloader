import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font
import subprocess
import threading
import json
import os
import re
import sys
import urllib.request
import queue
import time
import uuid
import zipfile
import io
import glob
import shutil
import socket
import random
from dataclasses import dataclass, asdict
from pathlib import Path
from queue import Queue, Empty

# ---------------- 统一的全局样式配置 ----------------
FONT_FAMILY = "Microsoft YaHei"  # 全局字体：微软雅黑
FONT_SIZE_TITLE = 10  # 标题文字大小
FONT_SIZE_NORMAL = 10  # 普通文字大小
FONT_SIZE_BUTTON = 10  # 按钮文字大小
FONT_SIZE_PERCENT = 14  # 百分比显示文字大小
COMBOBOX_WIDTH = 70  # 下拉框宽度
URL_ENTRY_WIDTH = 70  # URL输入框宽度
BUTTON_WIDTH_OP = 10  # 操作按钮宽度
BUTTON_WIDTH_MAIN = 12  # 主按钮宽度

# ---------------- 基础路径 ----------------
try:
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
except NameError:
    base_path = os.getcwd()

yt_dlp_path = os.path.join(base_path, "yt-dlp.exe")  # yt-dlp下载工具路径
ffmpeg_path = os.path.join(base_path, "ffmpeg.exe")  # ffmpeg音视频处理工具路径
N_M3U8DL_RE_PATH = os.path.join(base_path, "N_M3U8DL-RE.exe")  # M3U8下载工具路径
CONFIG_FILE = os.path.join(base_path, "window_pos.json")  # 窗口位置配置文件

# [新增] Cookies 文件路径定义
COOKIES_FILE_PATH = os.path.join(base_path, "www.youtube.com_cookies.txt")  # YouTube Cookies文件路径

startupinfo = None
if os.name == "nt":
    startupinfo = subprocess.STARTUPINFO()
    try:
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    except AttributeError:
        startupinfo.dwFlags |= 1

# ---------------- 配置 & 历史文件路径 ----------------
HISTORY_FILES = {  # 各下载器的历史记录文件路径
    'ytdlp': os.path.join(base_path, "download_history_ytdlp.json"),  # yt-dlp统一视频下载历史
    'm3u8': os.path.join(base_path, "download_history_m3u8.json"),  # M3U8下载历史
    'aria2': os.path.join(base_path, "download_history_aria2.json"),  # Aria2下载历史
}

# Aria2 相关路径
ARIA2_EXE = os.path.join(base_path, "aria2c.exe")  # Aria2下载器可执行文件路径
ARIA2_HISTORY_FILE = os.path.join(base_path, "history_aria2.jsonl")  # Aria2下载历史记录文件（JSONL格式）
ARIA2_LOG_FILE = os.path.join(base_path, "download_log_aria2.txt")  # Aria2下载日志文件

LAST_SAVE_PATH_DEFAULT = os.path.expanduser("~/Downloads")  # 默认保存路径：用户下载文件夹

# ---------------- 任务状态常量 ----------------
TASK_STATUS_WAITING = "等待中"  # 任务状态：等待开始
TASK_STATUS_RUNNING = "下载中"  # 任务状态：正在下载
TASK_STATUS_SUCCESS = "完成"  # 任务状态：下载成功
TASK_STATUS_FAILED = "失败"  # 任务状态：下载失败
TASK_STATUS_STOPPED = "已停止"  # 任务状态：用户停止

# ---------------- 快捷格式定义 ----------------
AUDIO_FMT = "bestaudio[ext=m4a]/bestaudio"  # 音频格式：优先m4a格式的最佳音频
P1080_FMT = "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]"  # 1080P视频格式：mp4+m4a
P720_FMT = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]"  # 720P视频格式：mp4+m4a

# ---------------- 正则表达式 ----------------
PROGRESS_PATTERN = re.compile(r'(\d+)/(\d+)')  # 匹配下载进度格式：已完成/总数
SPEED_PATTERN = re.compile(r'([\d.]+)([KMGT]?Bps)')  # 匹配下载速度格式：数值+单位
YTDLP_PROGRESS_RE = re.compile(r"\[download\]\s+([\d\.]+)\%\s+of\s+.*?at\s+([\d\.]+)(B/s|KiB/s|MiB/s|GiB/s)\s+.*")  # yt-dlp下载进度解析

# ============ 静音消息框替代类 ============
class SilentMessagebox:
    """静音消息框替代类 - 无系统提示音"""
    @staticmethod
    def _create_dialog(title, message, bg_color="#ffffff", fg_color="#333333"):
        dialog = tk.Toplevel()
        dialog.title(title)
        dialog.configure(bg=bg_color)
        dialog.withdraw()
        
        content_frame = tk.Frame(dialog, bg=bg_color, padx=20, pady=20)
        content_frame.pack(expand=True, fill='both')
        
        tk.Label(content_frame, text=message, bg=bg_color, fg=fg_color, 
                 wraplength=300, justify='left', font=("Microsoft YaHei", 10)).pack(expand=True)
                 
        btn_frame = tk.Frame(dialog, bg=bg_color, pady=10)
        btn_frame.pack(fill='x')
        return dialog, btn_frame

    @staticmethod
    def _show_modal(dialog, parent=None):
        dialog.update_idletasks()
        width = 350
        height = dialog.winfo_reqheight()
        # 简单居中
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        dialog.geometry(f'{width}x{height}+{int(x)}+{int(y)}')
        
        dialog.deiconify()
        dialog.transient(parent) if parent else None
        dialog.grab_set()
        dialog.wait_window()

    @staticmethod
    def showinfo(title, message, parent=None):
        dialog, btn_frame = SilentMessagebox._create_dialog(title, message)
        tk.Button(btn_frame, text="确定", command=dialog.destroy, 
                 bg="#e6f7ff", relief='flat', padx=15, font=("Microsoft YaHei", 9)).pack(pady=5)
        SilentMessagebox._show_modal(dialog, parent)

    @staticmethod
    def showwarning(title, message, parent=None):
        dialog, btn_frame = SilentMessagebox._create_dialog(title, message)
        tk.Button(btn_frame, text="确定", command=dialog.destroy, 
                 bg="#fff7e6", relief='flat', padx=15, font=("Microsoft YaHei", 9)).pack(pady=5)
        SilentMessagebox._show_modal(dialog, parent)

    @staticmethod
    def showerror(title, message, parent=None):
        dialog, btn_frame = SilentMessagebox._create_dialog(title, message)
        tk.Button(btn_frame, text="确定", command=dialog.destroy, 
                 bg="#fff1f0", relief='flat', padx=15, font=("Microsoft YaHei", 9)).pack(pady=5)
        SilentMessagebox._show_modal(dialog, parent)

    @staticmethod
    def askyesno(title, message, parent=None):
        dialog, btn_frame = SilentMessagebox._create_dialog(title, message)
        result = [False]
        def on_yes():
            result[0] = True
            dialog.destroy()
        def on_no():
            result[0] = False
            dialog.destroy()
            
        tk.Button(btn_frame, text="是", command=on_yes, 
                 bg="#e6f7ff", relief='flat', padx=15, width=6).pack(side='left', padx=20, expand=True)
        tk.Button(btn_frame, text="否", command=on_no, 
                 bg="#f5f5f5", relief='flat', padx=15, width=6).pack(side='right', padx=20, expand=True)
        SilentMessagebox._show_modal(dialog, parent)
        return result[0]

# ============ 通用辅助函数 (无状态) ============
def convert_to_MBps(speed_val, speed_unit):
    """将不同单位的速度转换为 MB/s"""
    try:
        val = float(speed_val)
    except ValueError:
        return 0.0
    if speed_unit.startswith('Ki'):
        return val * (1024 / 1000000)
    elif speed_unit.startswith('Mi'):
        return val * (1048576 / 1000000)
    elif speed_unit.startswith('Gi'):
        return val * (1073741824 / 1000000)
    elif speed_unit.startswith('B/s'):
        return val / 1000000
    return 0.0

def detect_cookies_error(error_output):
    """检测是否为cookies失效相关错误"""
    if not error_output:
        return False
    
    error_lower = error_output.lower()
    
    # 常见的cookies失效/需要登录的错误关键词
    cookies_error_keywords = [
        "sign in to confirm",
        "not a bot",
        "video is private",
        "video is unavailable",
        "this video is not available",
        "http error 403",
        "forbidden",
        "members-only",
        "requires payment",
        "join this channel",
        "account associated",
        "confirm your age",
        "content is age-restricted",
        "video requires purchase",
        "login required",
        "authentication required",
        "please sign in"
    ]
    
    return any(keyword in error_lower for keyword in cookies_error_keywords)

def init_log_red_tag(log_text_widget):
    """为 Text 控件配置 ERROR 标签:红色 + 加粗 + 9号字体"""
    log_text_widget.tag_config(
        "ERROR",
        foreground="red",
        font=('Courier New', 9, 'bold')
    )

def load_window_pos(root_window):
    """加载窗口位置"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                pos = json.load(f)
            geo = f"{pos['width']}x{pos['height']}+{pos['x']}+{pos['y']}"
            root_window.geometry(geo)
        except:
            pass  # 失败则使用默认位置

def save_window_pos(root_window):
    """保存窗口位置"""
    pos = {
        "x": root_window.winfo_x(),
        "y": root_window.winfo_y(),
        "width": root_window.winfo_width(),
        "height": root_window.winfo_height()
    }
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(pos, f)
    except:
        pass  # 保存失败也无妨

# ============ Aria2 相关辅助函数 ============
def bytes_human(n):
    """将字节数转换为人类可读格式"""
    try:
        n = int(n)
    except Exception:
        return "0 B"
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    f = float(n)
    i = 0
    while f >= 1024 and i < len(units) - 1:
        f /= 1024.0
        i += 1
    if i == 0:
        return f"{int(f)} {units[i]}"
    return f"{f:.2f} {units[i]}"

def speed_human(bps):
    """将速度(字节/秒)转换为人类可读格式"""
    if bps <= 0:
        return "0 B/s"
    return f"{bytes_human(bps)}/s"

def try_get_free_port():
    """获取一个空闲端口"""
    for _ in range(50):
        port = random.randint(20000, 45000)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return 6800

def guess_url_type(url):
    """猜测URL类型"""
    u = url.strip()
    if u.startswith("magnet:"):
        return "magnet"
    if u.lower().endswith(".torrent"):
        return "torrent"
    parsed = urllib.parse.urlparse(u)
    if parsed.scheme in ("http", "https"):
        return "http"
    if parsed.scheme in ("ftp", "sftp"):
        return parsed.scheme
    return parsed.scheme or "unknown"

def display_aria2_status(status):
    """显示Aria2任务状态"""
    m = {
        "active": "下载中",
        "waiting": "等待中",
        "paused": "已暂停",
        "complete": "已完成",
        "error": "失败",
        "removed": "已移除",
    }
    return m.get(status, status or "未知")

def detect_video_url_type(url):
    """检测视频URL类型：youtube/bilibili/tiktok/general"""
    if 'youtube.com' in url or 'youtu.be' in url:
        return 'youtube'
    elif 'bilibili.com' in url or 'b23.tv' in url:
        return 'bilibili'
    elif 'tiktok.com' in url:  # [新增] 识别 TikTok
        return 'tiktok'
    else:
        return 'general'

# ============ Torrent 文件解析 ============
def bdecode(data):
    """简单的 Bencode 解码器"""
    def decode_next(data, index):
        if data[index:index+1] == b'i':
            # 整数: i<number>e
            end = data.index(b'e', index)
            return int(data[index+1:end]), end + 1
        elif data[index:index+1] == b'l':
            # 列表: l<items>e
            result = []
            index += 1
            while data[index:index+1] != b'e':
                item, index = decode_next(data, index)
                result.append(item)
            return result, index + 1
        elif data[index:index+1] == b'd':
            # 字典: d<key><value>...e
            result = {}
            index += 1
            while data[index:index+1] != b'e':
                key, index = decode_next(data, index)
                if isinstance(key, bytes):
                    key = key.decode('utf-8', errors='replace')
                value, index = decode_next(data, index)
                result[key] = value
            return result, index + 1
        elif data[index:index+1].isdigit():
            # 字符串: <length>:<string>
            colon = data.index(b':', index)
            length = int(data[index:colon])
            start = colon + 1
            return data[start:start+length], start + length
        else:
            raise ValueError(f"无效的 bencode 数据: index={index}")
    
    result, _ = decode_next(data, 0)
    return result

def parse_torrent_files(torrent_data):
    """解析 torrent 文件，返回文件列表
    
    返回: [(文件索引, 文件路径, 文件大小), ...]
    """
    try:
        torrent = bdecode(torrent_data)
        info = torrent.get('info', {})
        
        files = []
        if 'files' in info:
            # 多文件种子
            base_name = info.get('name', b'').decode('utf-8', errors='replace') if isinstance(info.get('name'), bytes) else info.get('name', '')
            for idx, file_info in enumerate(info['files']):
                path_parts = file_info.get('path', [])
                path_str = '/'.join(
                    p.decode('utf-8', errors='replace') if isinstance(p, bytes) else p 
                    for p in path_parts
                )
                full_path = f"{base_name}/{path_str}" if base_name else path_str
                size = file_info.get('length', 0)
                files.append((idx + 1, full_path, size))  # aria2 文件索引从1开始
        else:
            # 单文件种子
            name = info.get('name', b'').decode('utf-8', errors='replace') if isinstance(info.get('name'), bytes) else info.get('name', 'unknown')
            size = info.get('length', 0)
            files.append((1, name, size))
        
        return files
    except Exception as e:
        print(f"解析 torrent 失败: {e}")
        return []

def format_file_size(size_bytes):
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

class TorrentFileSelectDialog:
    """BT种子文件选择对话框"""
    def __init__(self, parent, files, torrent_name):
        self.result = None  # 用户选择的文件索引列表
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"选择要下载的文件 - {torrent_name}")
        self.dialog.geometry("700x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 说明文字
        ttk.Label(self.dialog, text="请选择要下载的文件（取消选中的文件不会下载）:",
                 font=(FONT_FAMILY, FONT_SIZE_NORMAL)).pack(anchor='w', padx=10, pady=(10, 5))
        
        # 创建带滚动条的Treeview
        tree_frame = ttk.Frame(self.dialog)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.tree = ttk.Treeview(tree_frame, columns=('select', 'name', 'size'), show='headings', selectmode='extended')
        self.tree.heading('select', text='✓')
        self.tree.heading('name', text='文件名')
        self.tree.heading('size', text='大小')
        
        self.tree.column('select', width=30, anchor='center')
        self.tree.column('name', width=500, anchor='w')
        self.tree.column('size', width=100, anchor='e')
        
        vsb = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        
        # 存储选择状态
        self.file_states = {}  # {item_id: (file_index, selected)}
        
        # 添加文件到列表
        for file_idx, file_path, file_size in files:
            item_id = self.tree.insert('', 'end', values=('☑', file_path, format_file_size(file_size)))
            self.file_states[item_id] = [file_idx, True]
        
        # 绑定点击事件切换选择状态
        self.tree.bind('<ButtonRelease-1>', self._toggle_selection)
        
        # 按钮栏
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(btn_frame, text="全选", command=self._select_all).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="全不选", command=self._select_none).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="反选", command=self._invert_selection).pack(side='left', padx=5)
        
        ttk.Button(btn_frame, text="确定下载", command=self._on_ok).pack(side='right', padx=5)
        ttk.Button(btn_frame, text="取消", command=self._on_cancel).pack(side='right', padx=5)
        
        # 统计信息
        self.stats_var = tk.StringVar()
        ttk.Label(self.dialog, textvariable=self.stats_var, font=(FONT_FAMILY, FONT_SIZE_NORMAL)).pack(anchor='w', padx=10, pady=(0, 10))
        self._update_stats(files)
        
        # 保存文件信息供统计使用
        self.files = files
        
        # 居中显示
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        parent.wait_window(self.dialog)
    
    def _toggle_selection(self, event):
        """切换选择状态"""
        item = self.tree.identify_row(event.y)
        if item and item in self.file_states:
            self.file_states[item][1] = not self.file_states[item][1]
            current_values = list(self.tree.item(item, 'values'))
            current_values[0] = '☑' if self.file_states[item][1] else '☐'
            self.tree.item(item, values=current_values)
            self._update_stats(self.files)
    
    def _select_all(self):
        for item in self.file_states:
            self.file_states[item][1] = True
            current_values = list(self.tree.item(item, 'values'))
            current_values[0] = '☑'
            self.tree.item(item, values=current_values)
        self._update_stats(self.files)
    
    def _select_none(self):
        for item in self.file_states:
            self.file_states[item][1] = False
            current_values = list(self.tree.item(item, 'values'))
            current_values[0] = '☐'
            self.tree.item(item, values=current_values)
        self._update_stats(self.files)
    
    def _invert_selection(self):
        for item in self.file_states:
            self.file_states[item][1] = not self.file_states[item][1]
            current_values = list(self.tree.item(item, 'values'))
            current_values[0] = '☑' if self.file_states[item][1] else '☐'
            self.tree.item(item, values=current_values)
        self._update_stats(self.files)
    
    def _update_stats(self, files):
        selected_count = sum(1 for s in self.file_states.values() if s[1])
        total_count = len(self.file_states)
        
        # 计算选中文件的总大小
        selected_size = 0
        for item, (file_idx, selected) in self.file_states.items():
            if selected:
                for idx, path, size in files:
                    if idx == file_idx:
                        selected_size += size
                        break
        
        self.stats_var.set(f"已选择 {selected_count}/{total_count} 个文件，共 {format_file_size(selected_size)}")
    
    def _on_ok(self):
        # 获取选中的文件索引
        self.result = [file_idx for file_idx, selected in self.file_states.values() if selected]
        if not self.result:
            messagebox.showwarning("提示", "请至少选择一个文件")
            return
        self.dialog.destroy()
    
    def _on_cancel(self):
        self.result = None
        self.dialog.destroy()

# ============ 通用任务类 (DownloadTask) ============
class DownloadTask:
    """通用下载任务类 (数据模型)"""
    def __init__(self, task_type, url, save_path, **kwargs):
        self.id = str(uuid.uuid4())[:8]
        self.type = task_type
        self.url = url
        self.save_path = save_path
        self.status = TASK_STATUS_WAITING
        self.progress = "0%"
        self.speed = "0 M/s"
        self.process = None
        self.stop_flag = False
        self.kwargs = kwargs
        # final_title: 存储 yt-dlp 获取的网页标题 或 m3u8 的用户文件名
        self.final_title = kwargs.get('filename')  # M3U8 在创建时就设置了
        # [新增] 标记是否需要使用cookies (由获取标题/格式时决定)
        self.needs_cookies = False

    def get_display_name(self):
        """获取显示名称 (用于队列列表)"""
        if self.final_title:
            return self.final_title
        if self.type == "youtube":
            fmt = self.kwargs.get('format')
            if not fmt:
                return "YouTube-默认"
            if fmt == AUDIO_FMT: return "YouTube-音频"
            if fmt == P1080_FMT: return "YouTube-1080p"
            if fmt == P720_FMT: return "YouTube-720p"
            return f"YouTube-{fmt.split('+')[0]}"
        elif self.type == "bilibili":
            fmt = self.kwargs.get('format')
            if not fmt:
                return "Bilibili-默认"
            return "Bilibili"
        elif self.type == "tiktok":
            return "TikTok"
        elif self.type == "general":
            return "通用视频"
        elif self.type == "m3u8":
            return "M3U8"
        return "Unknown"

    def build_command(self):
        """根据任务类型和参数构建命令行。"""
        # 获取自定义文件名
        custom_name = self.kwargs.get('custom_filename')
        
        # 只要用户输入了自定义文件名，就应用该文件名模板 [cite: 18, 269]
        if custom_name:
            output_template = os.path.join(self.save_path, f"{custom_name}.%(ext)s")
        else:
            # 否则使用原程序规则：抓取网页标题 
            output_template = os.path.join(self.save_path, "%(title)s.%(ext)s")
            
        if self.type in ["youtube", "bilibili", "tiktok", "general"]:
            return self._build_ytdlp_command(output_template)
        elif self.type == "m3u8":
            return self._build_m3u8_command()
        raise ValueError(f"Unknown task type: {self.type}")

    def _build_ytdlp_command(self, output_template):
        """构建 yt-dlp 命令"""
        cmd = [yt_dlp_path]
        
        # [修改] 使用 needs_cookies 标记来决定是否使用cookies
        if self.type == "youtube" and self.needs_cookies:
            if os.path.exists(COOKIES_FILE_PATH):
                cmd.extend(["--cookies", COOKIES_FILE_PATH])
        
        if self.type == "youtube":
            fmt = self.kwargs.get('format')
            sub_lang = self.kwargs.get('sub_lang')
            speed_limit = self.kwargs.get('speed_limit', 0)
            
            # 如果有指定格式则使用，否则使用默认best
            if fmt:
                cmd.extend(["-f", fmt])
            
            cmd.extend(["-o", output_template,
                       "--merge-output-format", "mp4", "--ffmpeg-location", ffmpeg_path,
                       "--newline"])
            if fmt == AUDIO_FMT:
                # 找到--merge-output-format的位置并修改
                for i, arg in enumerate(cmd):
                    if arg == "--merge-output-format" and i + 1 < len(cmd):
                        cmd[i + 1] = "m4a"
                        break
            if speed_limit > 0:
                cmd.extend(["-r", f"{speed_limit}M"])
            if sub_lang:
                cmd.extend(["--write-subs", "--sub-lang", sub_lang, "--embed-subs"])
        
        elif self.type == "bilibili":
            fmt = self.kwargs.get('format')
            speed_limit = self.kwargs.get('speed_limit', 0)
            
            # 如果有指定格式则使用，否则使用默认best
            if fmt:
                cmd.extend(["-f", fmt])
            
            cmd.extend(["-o", output_template,
                       "--merge-output-format", "mp4", "--ffmpeg-location", ffmpeg_path,
                       "--newline"])
            if speed_limit > 0:
                cmd.extend(["-r", f"{speed_limit}M"])
        
        elif self.type == "tiktok":
            cmd.extend(["-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
                       "-o", output_template, "--merge-output-format", "mp4",
                       "--ffmpeg-location", ffmpeg_path, "--newline"])
        
        else: # [新增] 处理 General/通用 类型，确保应用路径
            fmt = self.kwargs.get('format')
            speed_limit = self.kwargs.get('speed_limit', 0)
            
            # 如果有指定格式则使用
            if fmt:
                cmd.extend(["-f", fmt])
            
            # 关键：应用 output_template (包含保存路径)
            cmd.extend(["-o", output_template, 
                       "--merge-output-format", "mp4", 
                       "--ffmpeg-location", ffmpeg_path, 
                       "--newline"])
            
            if speed_limit > 0:
                cmd.extend(["-r", f"{speed_limit}M"])
        
        cmd.append(self.url)
        return cmd

    def _build_m3u8_command(self):
        """构建 M3U8 命令"""
        filename = self.kwargs.get('filename', 'output')
        threads = self.kwargs.get('threads', 16)
        headers = self.kwargs.get('headers', '')
        extra_args = self.kwargs.get('extra_args', '')
        speed_limit = self.kwargs.get('speed_limit', 0)  # [新增] 限速 (MB/s)
        
        command = [N_M3U8DL_RE_PATH, self.url]
        command.extend(["--save-dir", self.save_path])
        command.extend(["--save-name", filename])
        command.extend(["--tmp-dir", self.save_path])
        
        if threads > 0 and threads != 16:
            command.extend(["--thread-count", str(threads)])
        if headers:
            command.extend(["--headers", headers])
        if extra_args:
            command.extend(extra_args.split())
        # [新增] 限速设置 (N_M3U8DL-RE使用--max-speed, 单位M表示MB/s)
        if speed_limit > 0:
            command.extend(["--max-speed", f"{speed_limit}M"])
        
        return command

# ============ Aria2 RPC 客户端和守护进程 ============
class Aria2RpcError(RuntimeError):
    pass

class Aria2RpcClient:
    """Aria2 RPC 客户端"""
    def __init__(self, endpoint, secret):
        self.endpoint = endpoint
        self.secret = secret
        self._id = 0
        self._lock = threading.Lock()

    def _rpc(self, method, params=None):
        if params is None:
            params = []
        with self._lock:
            self._id += 1
            rid = self._id

        payload = {
            "jsonrpc": "2.0",
            "id": rid,
            "method": method,
            "params": [f"token:{self.secret}"] + list(params),
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=6) as resp:
                raw = resp.read()
            obj = json.loads(raw.decode("utf-8", errors="ignore"))
        except Exception as e:
            raise Aria2RpcError(f"RPC 传输错误：{e}") from e

        if "error" in obj:
            raise Aria2RpcError(str(obj["error"]))
        return obj.get("result")

    def tell_active(self, keys=None):
        return self._rpc("aria2.tellActive", [keys or []])

    def tell_waiting(self, offset=0, num=1000, keys=None):
        return self._rpc("aria2.tellWaiting", [offset, num, keys or []])

    def tell_stopped(self, offset=0, num=1000, keys=None):
        return self._rpc("aria2.tellStopped", [offset, num, keys or []])

    def tell_status(self, gid, keys=None):
        return self._rpc("aria2.tellStatus", [gid, keys or []])

    def add_uri(self, uris, options=None, position=None):
        params = [[u for u in uris], options or {}]
        if position is not None:
            params.append(int(position))
        return self._rpc("aria2.addUri", params)

    def pause(self, gid, force=False):
        return self._rpc("aria2.forcePause" if force else "aria2.pause", [gid])

    def unpause(self, gid):
        return self._rpc("aria2.unpause", [gid])

    def remove(self, gid, force=False):
        return self._rpc("aria2.forceRemove" if force else "aria2.remove", [gid])

    def remove_download_result(self, gid):
        return self._rpc("aria2.removeDownloadResult", [gid])

    def change_global_option(self, options):
        return self._rpc("aria2.changeGlobalOption", [options])

    def get_global_option(self):
        return self._rpc("aria2.getGlobalOption", [])

    def change_option(self, gid, options):
        """修改单个任务的选项"""
        return self._rpc("aria2.changeOption", [gid, options])

    def shutdown(self):
        return self._rpc("aria2.shutdown", [])

    def add_torrent(self, torrent_data, options=None):
        """添加BT种子任务"""
        import base64
        torrent_b64 = base64.b64encode(torrent_data).decode('utf-8')
        params = [torrent_b64, [], options or {}]
        return self._rpc("aria2.addTorrent", params)

class Aria2Daemon:
    """Aria2 守护进程管理器"""
    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        self.aria2_path = self.base_dir / "aria2c.exe"
        self.port = try_get_free_port()
        self.secret = uuid.uuid4().hex
        self.proc = None
        self.endpoint = f"http://127.0.0.1:{self.port}/jsonrpc"
        self.client = Aria2RpcClient(self.endpoint, self.secret)

    def start(self, global_max_concurrent, global_max_tries, console_log_level="notice"):
        if not self.aria2_path.exists():
            raise FileNotFoundError(f"未找到 aria2c.exe，请把程序与 aria2c.exe 放在同一目录：{self.base_dir}")

        args = [
            str(self.aria2_path),
            "--enable-rpc=true",
            "--rpc-listen-all=false",
            f"--rpc-listen-port={self.port}",
            f"--rpc-secret={self.secret}",
            "--rpc-allow-origin-all=false",
            "--check-certificate=false",
            "--enable-color=false",
            f"--console-log-level={console_log_level}",
            f"--max-concurrent-downloads={int(global_max_concurrent)}",
            f"--max-tries={int(global_max_tries)}",
            "--retry-wait=3",
            "--follow-torrent=mem",
            "--bt-save-metadata=true",
            "--seed-time=0",
            "--auto-save-interval=10",
        ]

        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NO_WINDOW

        self.proc = subprocess.Popen(
            args,
            cwd=str(self.base_dir),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )

        deadline = time.time() + 6.0
        last_err = None
        while time.time() < deadline:
            try:
                self.client.get_global_option()
                return
            except Exception as e:
                last_err = e
                time.sleep(0.15)
        raise RuntimeError(f"aria2 RPC 未就绪：{last_err}")

    def stop(self):
        try:
            self.client.shutdown()
        except Exception:
            pass
        try:
            if self.proc and self.proc.poll() is None:
                self.proc.terminate()
        except Exception:
            pass

# Aria2 任务元数据
@dataclass
class Aria2TaskMeta:
    gid: str
    url: str
    save_dir: str
    url_type: str
    title_hint: str = ""
    created_time: str = ""
    status: str = "unknown"
    total: int = 0
    completed: int = 0
    speed: int = 0
    error: str = ""
    filenames: list = None
    filepaths: list = None
    info_hash: str = ""


# ============ 通用任务管理器 (TaskManager) ============
class TaskManager:
    """通用任务管理器 (业务逻辑)"""
    def __init__(self, app_instance, mode, max_concurrent=2):
        self.app = app_instance
        self.mode = mode
        self.max_concurrent = max_concurrent
        self.task_queue = []
        self.running_tasks = {}
        self.log_queue = queue.Queue()
        self.treeview = None  # [修改] 从Listbox改为Treeview
        self.log_text = None

    def add_task(self, task):
        """添加任务 - [修改1] 不自动启动"""
        self.task_queue.append(task)
        self.update_list()
        self.log(f"✓ 任务已添加到队列: [{task.id}] {task.get_display_name()}")
        # [修改] 移除自动启动逻辑
        # self.start_next_task()

    def start_next_task(self):
        """启动下一个等待中的任务"""
        if len(self.running_tasks) >= self.max_concurrent:
            return
        waiting_tasks = [t for t in self.task_queue if t.status == TASK_STATUS_WAITING]
        if not waiting_tasks:
            return
        task = waiting_tasks[0]
        self.task_queue.remove(task)
        self.running_tasks[task.id] = task
        threading.Thread(target=lambda: self.run_task(task), daemon=True).start()

    def start_all_tasks(self):
        """[新增] 启动所有等待中的任务"""
        waiting_count = sum(1 for t in self.task_queue if t.status == TASK_STATUS_WAITING)
        if waiting_count == 0:
            self.log("ℹ️ 没有等待中的任务")
            return
        self.log(f"▶️ 开始启动 {waiting_count} 个等待中的任务...")
        # 启动最多 max_concurrent 个任务
        while len(self.running_tasks) < self.max_concurrent:
            if not self.start_next_task():
                break

    def run_task(self, task):
        """运行任务"""
        task.status = TASK_STATUS_RUNNING
        self.app.root.after(0, self.update_list)
        
        if task.type == "m3u8":
            self._run_m3u8_task(task)
        else:
            self._run_ytdlp_task(task)
        
        # [修复] 任务完成后放回task_queue以便在UI中保留显示
        if task.id in self.running_tasks:
            del self.running_tasks[task.id]
            # 将完成的任务放回队列末尾（用于显示）
            self.task_queue.append(task)
        self.app.root.after(0, self.update_list)
        self.app.root.after(100, self.start_next_task)

    def _run_ytdlp_task(self, task):
        """运行 yt-dlp 任务"""
        # --- 预先获取视频标题 ---
        # [修改] 如果设置了自定义文件名,直接使用,跳过网页标题获取
        if task.kwargs.get('custom_filename'):
            task.final_title = task.kwargs.get('custom_filename')
            self.log(f"✓ 使用自定义文件名: {task.final_title}")
        elif not task.final_title and not task.stop_flag:
            self.log(f"◔ 正在获取标题: [{task.id}]")
            try:
                # 先不使用cookies尝试获取标题
                title_cmd = [yt_dlp_path, "--get-title", "--skip-download", "--no-warnings", task.url]
                title_proc = subprocess.run(
                    title_cmd,
                    capture_output=True,
                    text=True,
                    encoding='gbk',
                    timeout=30,
                    startupinfo=startupinfo
                )
                
                # 如果失败且是YouTube,尝试使用cookies重试
                if title_proc.returncode != 0 and task.type == "youtube" and os.path.exists(COOKIES_FILE_PATH):
                    self.log(f"⚠️ 获取标题失败,尝试使用cookies重试...")
                    title_cmd_with_cookies = [yt_dlp_path, "--get-title", "--skip-download", "--no-warnings",
                                             "--cookies", COOKIES_FILE_PATH, task.url]
                    title_proc = subprocess.run(
                        title_cmd_with_cookies,
                        capture_output=True,
                        text=True,
                        encoding='gbk',
                        timeout=30,
                        startupinfo=startupinfo
                    )
                    if title_proc.returncode == 0:
                        task.needs_cookies = True
                        self.log(f"✓ 使用cookies成功获取标题")
                    else:
                        # 检测cookies是否失效
                        error_output = title_proc.stderr if title_proc.stderr else title_proc.stdout
                        if detect_cookies_error(error_output):
                            self.log(f"❌ Cookies可能已失效!", "ERROR")
                            self.log(f"💡 建议: 重新导出cookies文件 (www.youtube.com_cookies.txt)", "ERROR")
                            self.app.root.after(0, self.app.notify_cookies_error)
                
                if title_proc.returncode == 0 and title_proc.stdout:
                    title = title_proc.stdout.strip().split('\n')[0]
                    if title:
                        task.final_title = title
                        self.log(f"✓ 标题获取成功: [{task.id}] {task.final_title[:40]}...")
                    else:
                        task.final_title = task.get_display_name()
                        self.log(f"⚠️ 未获取到标题,使用默认名称: {task.final_title}")
                else:
                    task.final_title = task.get_display_name()
                    error_out = title_proc.stderr if title_proc.stderr else title_proc.stdout
                    self.log(f"❌ 获取标题失败 (码:{title_proc.returncode}),输出: {error_out.strip()[:60]}...")
            except Exception as e:
                task.final_title = task.get_display_name()
                self.log(f"❌ 获取标题异常: {e},使用默认名称: {task.final_title}")
            
            self.app.root.after(0, self.update_list)
        
        self.log(f"▶ 开始下载: [{task.id}] {task.get_display_name()}")
        if task.needs_cookies:
            self.log(f"🍪 此任务使用cookies下载")
        
        cmd = task.build_command()
        max_retries = task.kwargs.get('retries', 3)
        
        for attempt in range(max_retries + 1):
            if task.stop_flag:
                task.status = TASK_STATUS_STOPPED
                self.log(f"⏹ 任务已停止: [{task.id}]")
                return
            
            if attempt > 0:
                self.log(f"🔄 重试: [{task.id}] 第 {attempt}/{max_retries} 次")
                time.sleep(5)
            
            try:
                # 用于收集错误输出
                error_output_buffer = []
                
                task.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    encoding='gbk',
                    bufsize=1,
                    startupinfo=startupinfo
                )
                
                for line in task.process.stdout:
                    if task.stop_flag:
                        task.process.kill()
                        break
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 收集可能的错误信息
                    if any(keyword in line.lower() for keyword in ['error', 'warning', 'failed', 'unavailable']):
                        error_output_buffer.append(line)
                    
                    m = YTDLP_PROGRESS_RE.search(line)
                    if m:
                        pct = m.group(1)
                        speed_val = m.group(2)
                        speed_unit = m.group(3)
                        speed_mbps = convert_to_MBps(speed_val, speed_unit)
                        task.progress = f"{pct}%"
                        task.speed = f"{speed_mbps:.2f} M/s"
                        self.app.root.after(0, self.update_list)
                
                if task.stop_flag:
                    task.status = TASK_STATUS_STOPPED
                    self.log(f"⏹ 任务已停止: [{task.id}]")
                    return
                
                return_code = task.process.wait()
                if return_code == 0:
                    task.status = TASK_STATUS_SUCCESS
                    self.log(f"✅ 任务完成: [{task.id}] {task.get_display_name()}")
                    self._save_to_history(task)
                    self.log("=" * 60)
                    return
                else:
                    if attempt == max_retries:
                        task.status = TASK_STATUS_FAILED
                        self.log(f"❌ 任务失败: [{task.id}] (退出码: {return_code})")
                        # 检测是否为cookies失效问题
                        if task.type == "youtube" and task.needs_cookies and error_output_buffer:
                            error_text = "\n".join(error_output_buffer)
                            if detect_cookies_error(error_text):
                                self.log(f"❌ 检测到Cookies可能已失效!", "ERROR")
                                self.log(f"💡 建议: 重新导出cookies文件 (www.youtube.com_cookies.txt)", "ERROR")
                                self.app.root.after(0, self.app.notify_cookies_error)
                        self.log("=" * 60)
                        return
            except Exception as e:
                self.log(f"❌ 任务异常: [{task.id}] - {e}")
                if attempt == max_retries:
                    task.status = TASK_STATUS_FAILED
                    return

    def _run_m3u8_task(self, task):
        """运行 M3U8 任务"""
        if not os.path.exists(N_M3U8DL_RE_PATH):
            task.status = TASK_STATUS_FAILED
            self.log(f"❌ 任务失败: [{task.id}] - N_M3U8DL-RE.exe 未找到。")
            return
        
        self.log(f"▶ 开始下载: [{task.id}] {task.get_display_name()}")
        command = task.build_command()
        max_attempts = task.kwargs.get('retries', 15) + 1
        filename = task.kwargs.get('filename', 'output')
        possible_extensions = ['.mp4', '.mkv', '.ts', '.flv']
        
        for attempt in range(1, max_attempts + 1):
            if task.stop_flag:
                task.status = TASK_STATUS_STOPPED
                self.log(f"ℹ 任务已停止: [{task.id}]")
                return
            
            if attempt > 1:
                self.log(f"🔄 重试: [{task.id}] 第 {attempt}/{max_attempts} 次")
                time.sleep(5)
            
            try:
                creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                task.process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='gbk',
                    creationflags=creationflags
                )
                
                for line in iter(task.process.stdout.readline, ''):
                    if task.stop_flag:
                        task.process.kill()
                        break
                    
                    if line:
                        line_stripped = line.strip()
                        match_progress = PROGRESS_PATTERN.search(line_stripped)
                        if match_progress:
                            current = match_progress.group(1)
                            total = match_progress.group(2)
                            if int(total) > 0:
                                pct = int(int(current) / int(total) * 100)
                                task.progress = f"{pct}% [{current}/{total}]"
                            else:
                                task.progress = f"0% [{current}/{total}]"
                            self.app.root.after(0, self.update_list)
                        
                        match_speed = SPEED_PATTERN.search(line_stripped)
                        if match_speed:
                            speed_value = match_speed.group(1)
                            speed_unit = match_speed.group(2)
                            task.speed = f"{speed_value}{speed_unit}"
                            self.app.root.after(0, self.update_list)
                
                if task.stop_flag:
                    task.status = TASK_STATUS_STOPPED
                    self.log(f"⏹ 任务已停止: [{task.id}]")
                    return
                
                return_code = task.process.wait()
                
                # 检查输出文件
                output_file_found = False
                output_file_path = None
                for ext in possible_extensions:
                    test_path = os.path.join(task.save_path, filename + ext)
                    if os.path.exists(test_path) and os.path.getsize(test_path) > 0:
                        output_file_found = True
                        output_file_path = test_path
                        break
                
                if output_file_found:
                    task.status = TASK_STATUS_SUCCESS
                    self.log(f"✅ 任务完成: [{task.id}] - 文件: {os.path.basename(output_file_path)}")
                    self._save_to_history(task)
                    self.log("=" * 60)
                    return
                else:
                    if attempt == max_attempts:
                        task.status = TASK_STATUS_FAILED
                        self.log(f"❌ 任务失败: [{task.id}] (退出码: {return_code}, 未找到输出文件)")
                        self.log("=" * 60)
                        return
            except Exception as e:
                self.log(f"❌ 任务异常: [{task.id}] - {e}")
                if attempt == max_attempts:
                    task.status = TASK_STATUS_FAILED
                    self.log("=" * 60)
                    return

    def _save_to_history(self, task):
        """将成功的任务保存到历史记录"""
        try:
            history_file = HISTORY_FILES.get(self.mode)
            if not history_file: return
            
            history_data = []
            if os.path.exists(history_file):
                try:
                    with open(history_file, "r", encoding="utf-8") as f:
                        history_data = json.load(f)
                except:
                    history_data = []
            
            display_title = task.final_title if task.final_title else task.get_display_name()
            history_item = {
                'title': display_title,
                'type': task.type,
                'url': task.url,
                'path': task.save_path,
                'time': time.strftime("%Y-%m-%d %H:%M:%S"),
                'task_id': task.id,
                'kwargs': task.kwargs
            }
            
            history_data.insert(0, history_item)
            if len(history_data) > 100:
                history_data = history_data[:100]
            
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
            
            self.log(f"📝 已保存到历史记录")
        except Exception as e:
            self.log(f"⚠️ 保存历史记录失败: {e}")

    def stop_task(self, task_id):
        """停止指定任务"""
        # 处理正在运行的任务
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.stop_flag = True
            if task.process:
                try:
                    pid = task.process.pid
                    # 使用Windows taskkill强制终止进程树（包括yt-dlp启动的子进程如ffmpeg）
                    # /F = 强制, /T = 包含子进程树
                    subprocess.run(
                        ['taskkill', '/F', '/T', '/PID', str(pid)],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    # 等待进程完全退出
                    try:
                        task.process.wait(timeout=3)
                    except:
                        pass
                except Exception as e:
                    self.log(f"⚠️ 终止进程时出错: {e}")
            self.log(f"正在停止任务: [{task.id}]")
        else:
            # 只处理等待中的任务，将其标记为停止（不移除，保留在队列中显示）
            for task in self.task_queue:
                if task.id == task_id and task.status == TASK_STATUS_WAITING:
                    task.status = TASK_STATUS_STOPPED
                    self.log(f"⏹ 任务已停止: [{task.id}]")
                    self.update_list()
                    break

    def start_task(self, task_id):
        """启动指定的等待任务"""
        for task in self.task_queue:
            if task.id == task_id and task.status == TASK_STATUS_WAITING:
                self.task_queue.remove(task)
                self.task_queue.insert(0, task)
                self.log(f"▶️ 优先启动任务: [{task.id}]")
                self.start_next_task()
                break

    def clear_task(self, task_id):
        """清除指定任务（同时清理临时文件）"""
        if task_id in self.running_tasks:
            self.stop_task(task_id)
            time.sleep(0.5)
        for task in list(self.task_queue):
            if task.id == task_id:
                self.task_queue.remove(task)
                self.log(f"已清除任务: [{task.id}]")
                self.update_list()
                
                # [新增] 延迟清理临时文件（yt-dlp临时文件无法续传，需要删除）
                self.force_cleanup = True
                delay = 2000 if self.mode == 'ytdlp' else 3000  # m3u8需要更长延迟
                self.app.root.after(delay, self._cleanup_temp_files)
                break

    def retry_task(self, task_id):
        """重试失败/已停止的任务"""
        for task in self.task_queue:
            if task.id == task_id and task.status in [TASK_STATUS_FAILED, TASK_STATUS_STOPPED]:
                task.status = TASK_STATUS_WAITING
                task.progress = "0%"
                task.speed = "0 M/s"
                task.stop_flag = False
                task.process = None
                self.log(f"🔄 任务已重置为等待状态: [{task.id}]")
                self.update_list()
                break

    def move_task_to_top(self, task_id):
        """将任务移动到队列顶部"""
        for i, task in enumerate(self.task_queue):
            if task.id == task_id and task.status == TASK_STATUS_WAITING:
                self.task_queue.pop(i)
                self.task_queue.insert(0, task)
                self.log(f"🔝 任务已移到队列顶部: [{task.id}]")
                self.update_list()
                break

    def clear_completed(self):
        """清除已完成任务"""
        self.task_queue = [t for t in self.task_queue 
                          if t.status not in [TASK_STATUS_SUCCESS, TASK_STATUS_FAILED, TASK_STATUS_STOPPED]]
        self.update_list()
        self.log("已清除完成/失败的任务")

    def stop_all(self):
        """停止所有任务并清理临时文件(延迟执行)"""
        for task in list(self.running_tasks.values()):
            task.stop_flag = True
            if task.process:
                try:
                    task.process.kill()  # 使用kill()强制终止
                except Exception:
                    pass
        
        # [Windows] 使用taskkill强制结束所有yt-dlp进程，确保释放文件句柄
        if os.name == "nt" and self.mode == 'ytdlp':
            try:
                subprocess.run(
                    ["taskkill", "/F", "/IM", "yt-dlp.exe"],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                # 也终止可能被yt-dlp调用的ffmpeg
                subprocess.run(
                    ["taskkill", "/F", "/IM", "ffmpeg.exe"],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            except Exception:
                pass
        
        for task in self.task_queue:
            task.status = TASK_STATUS_STOPPED
        
        # 清空任务队列和运行中任务
        self.task_queue = []
        self.running_tasks.clear()
        self.log("已停止所有任务")
        
        self.force_cleanup = True  # 标记为手动停止
        # 延长清理延迟确保进程完全释放文件句柄
        delay = 6000 if self.mode == 'm3u8' else 5000
        self.app.root.after(delay, self._cleanup_temp_files)
        self.update_list()

    def _cleanup_temp_files(self):
        """清理下载目录中的临时文件"""
        try:
            save_dir = self.app.shared_save_dir_var.get()
            if not os.path.exists(save_dir):
                return
            
            is_manual_stop = getattr(self, "force_cleanup", False)
            
            deleted_count = 0
            # 1. 清理单文件临时缓存 - 扩展模式匹配
            # 先收集所有需要删除的文件
            files_to_delete = []
            
            # 遍历目录中的所有文件
            for filename in os.listdir(save_dir):
                file_path = os.path.join(save_dir, filename)
                if not os.path.isfile(file_path):
                    continue
                    
                # 检查是否为临时文件
                lower_name = filename.lower()
                is_temp = False
                
                # yt-dlp 临时文件模式
                if lower_name.endswith('.part'):
                    is_temp = True
                elif lower_name.endswith('.ytdl'):
                    is_temp = True
                elif lower_name.endswith('.temp'):
                    is_temp = True
                elif lower_name.endswith('.tmp'):
                    is_temp = True
                elif lower_name.endswith('.download'):
                    is_temp = True
                elif lower_name.endswith('.aria2'):
                    is_temp = True
                # yt-dlp 特有的格式: xxx.fXXX.mp4.part 或 xxx.fXXX.webm.part
                elif '.f' in lower_name and ('.mp4.part' in lower_name or '.webm.part' in lower_name or '.m4a.part' in lower_name):
                    is_temp = True
                    
                if is_temp:
                    files_to_delete.append(file_path)
            
            # 删除收集到的临时文件
            for file_path in files_to_delete:
                for attempt in range(3):
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                        self.log(f"🗑️ 已删除: {os.path.basename(file_path)}")
                        break
                    except PermissionError:
                        if attempt < 2:
                            time.sleep(1)
                        else:
                            self.log(f"⚠️ 无法删除 {os.path.basename(file_path)}: 文件仍被占用")
                    except Exception as e:
                        self.log(f"⚠️ 无法删除 {os.path.basename(file_path)}: {e}")
                        break
            
            # 2. 清理 .tmp 目录
            tmp_dir = os.path.join(save_dir, '.tmp')
            if os.path.exists(tmp_dir) and os.path.isdir(tmp_dir):
                try:
                    shutil.rmtree(tmp_dir)
                    deleted_count += 1
                    self.log(f"🗑️ 已删除临时目录: .tmp")
                except Exception as e:
                    self.log(f"⚠️ 无法删除临时目录 .tmp: {e}")
            
            # 3. 清理 m3u8 分片目录
            for item in os.listdir(save_dir):
                full_path = os.path.join(save_dir, item)
                if os.path.isdir(full_path):
                    try:
                        files = os.listdir(full_path)
                        video_mp4 = os.path.join(save_dir, item + ".mp4")
                        
                        # 3a. 合成成功
                        if os.path.exists(video_mp4):
                            shutil.rmtree(full_path)
                            deleted_count += 1
                            self.log(f"🗑️ 已删除分片目录: {item}")
                            continue
                        
                        # 3b. 手动停止
                        if is_manual_stop:
                            if (
                                "raw.m3u8" in files or "meta.json" in files or
                                "meta_selected.json" in files or
                                os.path.isdir(os.path.join(full_path, "0___"))
                            ):
                                shutil.rmtree(full_path)
                                deleted_count += 1
                                self.log(f"🗑️(手动停止)已删除分片目录: {item}")
                                continue
                    except Exception as e:
                        self.log(f"⚠️ 无法删除分片目录 {item}: {e}")
            
            if deleted_count > 0:
                self.log(f"✅ 清理完成,共删除 {deleted_count} 个临时文件/目录")
            else:
                self.log("ℹ️ 未发现需要清理的临时文件")
        except Exception as e:
            self.log(f"❌ 清理临时文件时出错: {e}")

    def update_list(self):
        """更新任务列表显示 (Treeview版本)"""
        if not self.treeview: return
        
        all_tasks = list(self.running_tasks.values()) + self.task_queue
        existing_iids = set(self.treeview.get_children())
        current_iids = set(t.id for t in all_tasks)
        
        # 删除已不存在的任务
        for iid in existing_iids - current_iids:
            self.treeview.delete(iid)
        
        # 更新或插入任务
        for task in all_tasks:
            status_text = {
                TASK_STATUS_WAITING: "⏸ 等待中",
                TASK_STATUS_RUNNING: "▶ 下载中",
                TASK_STATUS_SUCCESS: "✅ 完成",
                TASK_STATUS_FAILED: "❌ 失败",
                TASK_STATUS_STOPPED: "⏹ 已停止"
            }.get(task.status, "❓ 未知")
            
            # 获取显示名称 (截断过长的标题)
            display_name = task.get_display_name()
            if len(display_name) > 50:
                display_name = display_name[:50] + "..."
            
            # 类型显示
            type_text = {
                "youtube": "YouTube",
                "bilibili": "Bilibili",
                "tiktok": "TikTok",
                "general": "通用",
                "m3u8": "M3U8"
            }.get(task.type, task.type)
            
            values = (
                task.id,
                status_text,
                task.progress,
                task.speed,
                display_name,
                type_text
            )
            
            if task.id in existing_iids:
                self.treeview.item(task.id, values=values)
            else:
                self.treeview.insert("", tk.END, iid=task.id, values=values)

    def log(self, message, level="INFO"):
        """记录日志,支持 INFO / ERROR(红色)"""
        timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
        line = f"{timestamp} {message}"
        self.log_queue.put((line, level))

    def process_log_queue(self):
        """处理日志队列(支持颜色)"""
        if not self.log_text: return
        
        while True:
            try:
                line, level = self.log_queue.get_nowait()
                self.log_text.config(state='normal')
                tag = "ERROR" if level == "ERROR" else ""
                self.log_text.insert(tk.END, line + '\n', tag)
                self.log_text.see(tk.END)
                self.log_text.config(state='disabled')
            except queue.Empty:
                break
            except ValueError:
                line = line[0] if isinstance(line, tuple) else line
                self.log_text.insert(tk.END, line + '\n')
                self.log_text.see(tk.END)
        
        self.app.root.after(100, self.process_log_queue)

    def clear_log(self):
        """清空日志"""
        if self.log_text:
            self.log_text.config(state='normal')
            self.log_text.delete(1.0, tk.END)
            self.log_text.config(state='disabled')

# ============ UI 样式定义 ============
UI_COLORS = {  # UI色彩配置方案
    "bg_main": "#f0f2f5",           # 主背景色：浅灰白，用于窗口背景
    "bg_secondary": "#ffffff",      # 次级背景色：纯白，用于卡片/内容区背景
    "text_primary": "#333333",      # 主文本颜色：深灰
    "text_secondary": "#666666",    # 副文本颜色：中灰，用于辅助说明
    "primary": "#1890ff",           # 主色调：蓝色，用于主要操作按钮
    "success": "#52c41a",           # 成功/开始色：绿色
    "warning": "#faad14",           # 警告/暂停色：橙色
    "danger": "#ff4d4f",            # 错误/停止色：红色
    "info": "#13c2c2",              # 信息色：青色
    "border": "#d9d9d9",            # 边框色：浅灰
}

def setup_styles():
    """配置ttk样式"""
    style = ttk.Style()
    
    # 使用 'alt' 主题，它支持扁平化且更容易去除边框
    try:
        style.theme_use('alt')
    except:
        pass
    
    # 全局配置
    style.configure(".", 
        background=UI_COLORS["bg_main"], 
        foreground=UI_COLORS["text_primary"], 
        font=(FONT_FAMILY, FONT_SIZE_NORMAL))
    
    # TFrame / TLabel
    style.configure("TFrame", background=UI_COLORS["bg_main"], borderwidth=0)
    style.configure("TLabel", background=UI_COLORS["bg_main"], foreground=UI_COLORS["text_primary"], borderwidth=0)
    
    # TLabelframe (移除边框)
    style.configure("TLabelframe", 
        background=UI_COLORS["bg_main"], 
        foreground=UI_COLORS["text_primary"],
        relief="flat",          # 无边框
        borderwidth=0)          # 边框宽度0
        
    style.configure("TLabelframe.Label", 
        background=UI_COLORS["bg_main"], 
        foreground=UI_COLORS["primary"], 
        font=(FONT_FAMILY, FONT_SIZE_NORMAL + 1, 'bold'))

    # 白色背景的容器 (用于输入框区域)
    style.configure("Card.TFrame", background=UI_COLORS["bg_secondary"], relief="flat", borderwidth=0)
    style.configure("Card.TLabel", background=UI_COLORS["bg_secondary"], borderwidth=0)
    
    # 按钮通用样式
    style.configure("TButton", 
        padding=(15, 8),        # 增加内边距
        relief="flat", 
        borderwidth=0,
        font=(FONT_FAMILY, FONT_SIZE_NORMAL, 'bold'),
        focuscolor=UI_COLORS["bg_main"]) # 去除焦点框颜色
    
    style.map("TButton",
        background=[('active', '#e6f7ff'), ('pressed', '#bae7ff')],
        foreground=[('active', UI_COLORS["primary"])]
    )

    # 主要操作按钮 (蓝)
    style.configure("Primary.TButton", 
        background=UI_COLORS["primary"], 
        foreground="white")
    style.map("Primary.TButton",
        background=[('active', '#40a9ff'), ('pressed', '#096dd9')],
        foreground=[('active', 'white')]
    )

    # 成功/开始按钮 (绿)
    style.configure("Success.TButton", 
        background=UI_COLORS["success"], 
        foreground="white")
    style.map("Success.TButton",
        background=[('active', '#73d13d'), ('pressed', '#389e0d')],
        foreground=[('active', 'white')]
    )
    
    # 危险/停止按钮 (红)
    style.configure("Danger.TButton", 
        padding=(12, 8), 
        font=(FONT_FAMILY, FONT_SIZE_NORMAL, 'bold'), 
        background=UI_COLORS["danger"], 
        foreground="white")
    style.map("Danger.TButton", 
        background=[('active', '#ff7875'), ('pressed', '#cf1322')])
    
    # 小号按钮 (非加粗)
    style.configure("Small.TButton", 
        padding=(8, 6), 
        font=(FONT_FAMILY, FONT_SIZE_NORMAL - 1), 
        background=UI_COLORS["bg_secondary"])
    style.map("Small.TButton", 
        background=[('active', '#e6f7ff'), ('pressed', '#bae7ff')],
        foreground=[('active', UI_COLORS["primary"])]
    )

    # 信息按钮 (青色) - 与主按钮大小一致
    style.configure("Info.Small.TButton", 
        padding=(12, 8), 
        font=(FONT_FAMILY, FONT_SIZE_NORMAL, 'bold'), 
        background="#436EEE", 
        foreground="white")
    style.map("Info.Small.TButton",
        background=[('active', '#1874CD'), ('pressed', '#006d75')],
        foreground=[('active', 'white')]
    )

    # 警告按钮 (橙红色/珊瑚色) - 与主按钮大小一致
    style.configure("Warning.Small.TButton", 
        padding=(12, 8), 
        font=(FONT_FAMILY, FONT_SIZE_NORMAL, 'bold'), 
        background="#ff7a45", 
        foreground="white")
    style.map("Warning.Small.TButton",
        background=[('active', '#ff9c6e'), ('pressed', '#d4380d')],
        foreground=[('active', 'white')]
    )

    # 输入框 (扁平化轻边框)
    style.configure("TEntry", 
        padding=5, 
        relief="solid",         # 实线边框 
        borderwidth=1,          # 1像素宽度
        bordercolor="#e5e5e5",  # 极浅灰色边框
        highlightthickness=0,   # 移除焦点高亮圈
        fieldbackground="white")
    
    #去除聚焦变色和边框变粗，保持极简
    style.map("TEntry",
        bordercolor=[('focus', '#e5e5e5')], 
        lightcolor=[('focus', '#e5e5e5')],
        darkcolor=[('focus', '#e5e5e5')],
        relief=[('focus', 'solid')],
        borderwidth=[('focus', 1)],
    )
    
    # 下拉框 (类似输入框)
    style.configure("TCombobox",
        padding=5,
        relief="solid",
        borderwidth=1,
        bordercolor="#e5e5e5",  # 极浅灰色边框 
        arrowcolor=UI_COLORS["text_secondary"])
        
    style.map("TCombobox",
        bordercolor=[('focus', '#e5e5e5')],
        lightcolor=[('focus', '#e5e5e5')],
        darkcolor=[('focus', '#e5e5e5')],
        fieldbackground=[('readonly', 'white')],
    )
    
    # 数字输入框 (Spinbox)
    style.configure("TSpinbox",
        padding=5,
        relief="solid",
        borderwidth=1,
        bordercolor="#e5e5e5",
        font=(FONT_FAMILY, FONT_SIZE_NORMAL + 3),
        arrowcolor=UI_COLORS["text_secondary"])
        
    style.map("TSpinbox",
        bordercolor=[('focus', '#e5e5e5')],
        lightcolor=[('focus', '#e5e5e5')],
        darkcolor=[('focus', '#e5e5e5')],
        fieldbackground=[('readonly', 'white')],
    )
    
    # 列表框 (Treeview) - 浅色1px细线边框
    style.configure("Treeview", 
        background="white", 
        fieldbackground="white", 
        foreground=UI_COLORS["text_primary"],
        rowheight=28,
        borderwidth=1,
        bordercolor="#d9d9d9",
        lightcolor="#d9d9d9",
        darkcolor="#d9d9d9",
        relief="solid",
        highlightthickness=0)  # 移除焦点高亮环
    
    # [关键] 修改Treeview布局，移除焦点边框元素
    # 这是解决ttk.Treeview焦点边框问题的根本方法
    style.layout("Treeview", [
        ('Treeview.treearea', {'sticky': 'nswe'})
    ])
    
    # 配置Treeview的焦点颜色为透明/浅色，聚焦时边框不变
    style.map("Treeview",
        background=[('selected', '#e3f2fd')],  # 选中时的背景色
        foreground=[('selected', UI_COLORS["text_primary"])])
    
    style.configure("Treeview.Heading", 
        background="#fafafa", 
        foreground=UI_COLORS["text_secondary"],
        font=(FONT_FAMILY, FONT_SIZE_NORMAL, 'bold'),
        relief="flat",
        borderwidth=0)
    
    # 滚动条 (浅色/极简)
    style.configure("TScrollbar",
        background="#f0f0f0",
        troughcolor=UI_COLORS["bg_main"],
        borderwidth=0,
        relief="flat",
        arrowcolor="#cccccc")
        
    style.map("TScrollbar",
        background=[('active', '#e0e0e0'), ('pressed', '#d0d0d0')],
    )
    
    # 笔记本 (Tabs)
    style.configure("TNotebook", 
        background=UI_COLORS["bg_main"], 
        tabmargins=[10, 10, 0, 0], 
        borderwidth=0,
        relief="flat")
        
    style.configure("TNotebook.Tab", 
        padding=[20, 10],        
        font=(FONT_FAMILY, FONT_SIZE_NORMAL, 'bold'),
        background=UI_COLORS["bg_main"], 
        foreground=UI_COLORS["text_secondary"],
        borderwidth=0,
        relief="flat",
        focuscolor=UI_COLORS["bg_main"]) # 去除Tab焦点框
        
    style.map("TNotebook.Tab",
        background=[("selected", "#E9E7EF")], 
        foreground=[("selected", UI_COLORS["primary"])],
        expand=[("selected", [0, 0, 0, 0])]
    )
    
    # 移除 LabelFrame 标题的边框 (如果还有)
    style.configure("TLabelframe.Label", 
        background=UI_COLORS["bg_main"], 
        foreground=UI_COLORS["primary"], 
        font=(FONT_FAMILY, FONT_SIZE_NORMAL - 2, 'bold'),
        borderwidth=0)

# ============ (重构) 主应用程序类 ============
class DownloadApplication:
    """主应用程序 GUI 类"""
    def __init__(self, root):
        self.root = root
        setup_styles()
        self.root.configure(background=UI_COLORS["bg_main"])
        self.root.title("Ry Downloader - 20251230")
        self.root.geometry("1400x750")
        self.root.minsize(1200, 600)  # 设置最小窗口尺寸
        load_window_pos(self.root)
        
        # 加载历史记录时使用
        self.current_history_data = []
        
        # --- 初始化共享状态变量 ---
        self.shared_save_dir_var = tk.StringVar(value=LAST_SAVE_PATH_DEFAULT)
        self.main_status_var = tk.StringVar(value="就绪")  # yt-dlp 状态
        self.m3u8_tool_status_var = tk.StringVar(value="N_M3U8DL-RE: 检测中...")
        self.cookies_error_notified = False  # Cookies失效提示标志
        
        # --- 初始化任务管理器 ---
        self.ytdlp_manager = TaskManager(self, "ytdlp", max_concurrent=2)  # 统一视频下载
        self.m3u8_manager = TaskManager(self, "m3u8", max_concurrent=3)
        
        # --- 初始化Aria2相关 ---
        self.aria2_daemon = None
        self.aria2_rpc = None
        self.aria2_tasks = {}
        self.aria2_tasks_lock = threading.Lock()
        self.aria2_ui_queue = Queue()
        self.aria2_ignored_gids = set()
        
        # --- 构建UI ---
        self._create_top_bar()
        self._create_notebook()
        self._create_bottom_bar()
        
        # --- 启动后台进程 ---
        self.check_m3u8_tool_status()
        self._start_log_processors()
        self._start_aria2_daemon()  # 启动Aria2
        
        # --- 绑定关闭事件 ---
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_top_bar(self):
        """创建顶部工具栏 - 紧凑布局"""
        title_frame = ttk.Frame(self.root)
        title_frame.pack(fill='x', padx=10, pady=(5, 0))  # 减少顶部间距
        
        tool_control_frame = ttk.Frame(title_frame)
        tool_control_frame.pack(side='right')
        
        ttk.Button(tool_control_frame, text="🔄 更新yt-dlp",
                  command=self.update_yt_dlp, style="Small.TButton").pack(side='right', padx=5)
        ttk.Button(tool_control_frame, text="🌐 更新N_M3U8DL-RE",
                  command=self.update_n_m3u8dl_re, style="Small.TButton").pack(side='right', padx=5)
        
        tk.Label(tool_control_frame, textvariable=self.m3u8_tool_status_var,
                font=(FONT_FAMILY, FONT_SIZE_NORMAL - 1)).pack(side='right', padx=10)

    def _create_notebook(self):
        """创建标签页"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(padx=10, expand=True, fill="both")
        
        # 1. 统一视频下载标签页 (yt-dlp)
        self._create_download_tab(self.notebook, '📺 视频下载 (yt-dlp)', self.ytdlp_manager, UnifiedVideoInputFrame)
        
        # 2. M3U8下载标签页
        self._create_download_tab(self.notebook, '🎬 M3U8 下载', self.m3u8_manager, M3U8InputFrame)
        
        # 3. Aria2下载标签页
        self._create_aria2_tab(self.notebook, '🚀 Aria2 下载')

    def _create_bottom_bar(self):
        """创建底部保存路径栏"""
        bottom_control_frame = ttk.Frame(self.root)
        bottom_control_frame.pack(side='bottom', fill='x', padx=15, pady=(5, 15))
        
        # 使用 Grid 布局更能保证布局稳定性
        bottom_control_frame.columnconfigure(1, weight=1) # 中间输入框扩充
        
        # 1. 标签 (col 0)
        ttk.Label(bottom_control_frame, text="📁 保存路径:",
                font=(FONT_FAMILY, FONT_SIZE_NORMAL)).grid(row=0, column=0, padx=(0, 5), sticky="w")
        
        # 2. 路径显示 (col 1 - 自动填充)
        ttk.Entry(bottom_control_frame, textvariable=self.shared_save_dir_var,
                state='readonly').grid(row=0, column=1, padx=5, sticky="ew")
        
        # 3. 按钮 (col 2, 3)
        ttk.Button(bottom_control_frame, text="📂 浏览/设置",
                  command=self.choose_directory).grid(row=0, column=2, padx=5, sticky="e")
                  
        ttk.Button(bottom_control_frame, text="📁 打开目录",
                  command=self.open_save_directory).grid(row=0, column=3, padx=(5, 0), sticky="e")

    def _start_log_processors(self):
        """启动所有管理器的日志队列处理器"""
        self.root.after(100, self.ytdlp_manager.process_log_queue)
        self.root.after(100, self.m3u8_manager.process_log_queue)

    def _start_aria2_daemon(self):
        """启动Aria2守护进程"""
        if not os.path.exists(ARIA2_EXE):
            print(f"警告: 未找到 aria2c.exe，Aria2功能将不可用")
            return
        
        try:
            self.aria2_daemon = Aria2Daemon(base_path)
            self.aria2_daemon.start(
                global_max_concurrent=2,
                global_max_tries=3
            )
            self.aria2_rpc = self.aria2_daemon.client
            print(f"Aria2 daemon started on port {self.aria2_daemon.port}")
            
            # 启动aria2轮询线程
            self._start_aria2_poller()
            # 启动UI队列处理
            self.root.after(120, self._drain_aria2_ui_queue)
        except Exception as e:
            print(f"启动Aria2失败: {e}")
            self.aria2_daemon = None
            self.aria2_rpc = None

    def _start_aria2_poller(self):
        """启动Aria2任务状态轮询线程"""
        def poll_loop():
            keys = ["gid", "status", "totalLength", "completedLength", "downloadSpeed",
                    "errorMessage", "files", "infoHash"]
            while True:
                try:
                    if not self.aria2_rpc:
                        time.sleep(0.5)
                        continue
                    
                    active = self.aria2_rpc.tell_active(keys)
                    waiting = self.aria2_rpc.tell_waiting(0, 1000, keys)
                    stopped = self.aria2_rpc.tell_stopped(0, 1000, keys)
                    
                    merged = []
                    merged.extend(active or [])
                    merged.extend(waiting or [])
                    merged.extend(stopped or [])
                    
                    for item in merged:
                        gid = item.get("gid")
                        if not gid or gid in self.aria2_ignored_gids:
                            continue
                        
                        status = item.get("status", "unknown")
                        total = int(item.get("totalLength") or 0)
                        comp = int(item.get("completedLength") or 0)
                        speed = int(item.get("downloadSpeed") or 0)
                        err = item.get("errorMessage") or ""
                        info_hash = item.get("infoHash") or ""
                        
                        filepaths = []
                        filenames = []
                        files = item.get("files") or []
                        for f in files:
                            p = (f.get("path") or "").strip()
                            if p:
                                filepaths.append(p)
                                filenames.append(Path(p).name)
                        
                        name_show = ""
                        if filenames:
                            name_show = filenames[0] if len(filenames) == 1 else f"{filenames[0]}（+{len(filenames)-1}）"
                        
                        with self.aria2_tasks_lock:
                            if gid not in self.aria2_tasks:
                                self.aria2_tasks[gid] = Aria2TaskMeta(
                                    gid=gid,
                                    url="",
                                    save_dir=self.shared_save_dir_var.get(),
                                    url_type="unknown",
                                    created_time=time.strftime("%Y-%m-%d %H:%M:%S")
                                )
                            t = self.aria2_tasks[gid]
                            t.status = status
                            t.total = total
                            t.completed = comp
                            t.speed = speed
                            t.error = err
                            t.filenames = filenames
                            t.filepaths = filepaths
                            t.info_hash = info_hash
                        
                        if hasattr(self, 'aria2_tree'):
                            self.aria2_ui_queue.put(("update_task", gid, name_show))
                    
                    # 动态调整轮询频率：根据任务状态优化CPU占用
                    active_count = len(active or [])
                    waiting_count = len(waiting or [])
                    if active_count > 0:
                        poll_interval = 0.5   # 有活跃下载：高频轮询
                    elif waiting_count > 0:
                        poll_interval = 1.5   # 只有等待任务：中频轮询
                    else:
                        poll_interval = 3.0   # 无任务或全部完成：低频轮询
                    time.sleep(poll_interval)
                except Exception as e:
                    print(f"Aria2轮询错误: {e}")
                    time.sleep(1.2)
        
        th = threading.Thread(target=poll_loop, daemon=True)
        th.start()

    def _drain_aria2_ui_queue(self):
        """处理Aria2 UI更新队列"""
        try:
            while True:
                msg = self.aria2_ui_queue.get_nowait()
                kind = msg[0]
                if kind == "update_task" and hasattr(self, 'aria2_tree'):
                    _, gid, name_show = msg
                    self._refresh_aria2_tree_row(gid, name_show)
        except Empty:
            pass
        self.root.after(120, self._drain_aria2_ui_queue)

    def _refresh_aria2_tree_row(self, gid, name_show):
        """刷新Aria2任务列表行"""
        if not hasattr(self, 'aria2_tree'):
            return
        
        with self.aria2_tasks_lock:
            t = self.aria2_tasks.get(gid)
        if not t:
            return
        
        total = t.total
        comp = t.completed
        progress = "0%"
        if total > 0:
            progress = f"{(comp / total) * 100:.1f}%"
        
        sp = speed_human(t.speed)
        status = display_aria2_status(t.status)
        url = t.url
        save_dir = t.save_dir
        
        if not self.aria2_tree.exists(gid):
            self.aria2_tree.insert("", tk.END, iid=gid, values=(gid[:8], status, progress, sp, name_show, url, save_dir))
        else:
            self.aria2_tree.item(gid, values=(gid[:8], status, progress, sp, name_show, url, save_dir))


    def launch_aria2c(self):
        """启动aria2c下载器（静默启动，无提示）"""
        aria2_script = os.path.join(base_path, "aria2c_chatgpt.pyw")

        if not os.path.exists(aria2_script):
            messagebox.showerror("错误", "未找到 aria2c_chatgpt.pyw 文件！\n请确保文件在程序同一目录下。")
            return

        try:
            # 使用pythonw.exe启动,避免显示控制台窗口
            if os.name == "nt":  # Windows系统
                # 尝试获取pythonw.exe路径
                python_exe = sys.executable
                if python_exe.endswith('python.exe'):
                    pythonw_exe = python_exe.replace('python.exe', 'pythonw.exe')
                elif python_exe.endswith('pythonw.exe'):
                    pythonw_exe = python_exe
                else:
                    pythonw_exe = 'pythonw.exe'

                subprocess.Popen([pythonw_exe, aria2_script], 
                               creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            else:
                subprocess.Popen([sys.executable, aria2_script])

            # 静默启动，不显示成功提示
        except Exception as e:
            messagebox.showerror("错误", f"启动Aria2下载器失败：\n{str(e)}")

    def _on_close(self):
        """关闭窗口时保存位置并检查运行中的任务"""
        # 检查是否有正在运行的任务
        running_count = 0
        running_count += len(self.ytdlp_manager.running_tasks)
        running_count += len(self.m3u8_manager.running_tasks)

        if running_count > 0:
            # 弹出确认对话框
            result = messagebox.askyesno(
                "确认关闭",
                f"当前有 {running_count} 个下载任务正在运行\n\n是否要停止所有任务并关闭程序？",
                icon='warning'
            )

            # 如果用户选择"否"，则取消关闭
            if not result:
                return

            # 如果用户选择"是"，停止所有任务
            for manager in [self.ytdlp_manager, self.m3u8_manager]:
                for task in list(manager.running_tasks.values()):
                    task.stop_flag = True
                    if task.process:
                        try:
                            task.process.terminate()
                        except:
                            pass

        # 停止Aria2守护进程
        if self.aria2_daemon:
            try:
                self.aria2_daemon.stop()
            except:
                pass
        
        # 保存窗口位置并关闭
        save_window_pos(self.root)
        self.root.destroy()

    def _create_aria2_tab(self, notebook, title):
        """创建Aria2下载标签页"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=title)
        
        # 主布局
        # 输入区域 - 增加顶部间距与其他标签页视觉一致 (LabelFrame比普通Frame有额外间距)
        input_container = ttk.Frame(frame, style="Card.TFrame", padding="12")
        input_container.pack(side='top', fill='x', padx=(10, 10), pady=(20, 10))
        
        # URL输入 (与M3U8页面行距一致)
        ttk.Label(input_container, text="下载链接 (HTTP/FTP/BT/Magnet):", 
                  font=(FONT_FAMILY, FONT_SIZE_TITLE, 'bold'), style="Card.TLabel").grid(row=0, column=0, sticky="w")
        
        self.aria2_url_var = tk.StringVar()
        # 使用tk.Text替代ttk.Entry，采用默认样式
        self.aria2_url_entry = tk.Text(input_container, height=2, width=70, wrap='word', 
                                        font=(FONT_FAMILY, FONT_SIZE_NORMAL),
                                        highlightthickness=0)  # 完全移除高亮环
        self.aria2_url_entry.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(5, 10))
        
        # 绑定Text控件到变量
        def update_aria2_url_var(*args):
            self.aria2_url_var.set(self.aria2_url_entry.get("1.0", "end-1c"))
        self.aria2_url_entry.bind("<KeyRelease>", update_aria2_url_var)
        
        # 添加空白行增加间距
        ttk.Frame(input_container, height=15).grid(row=2, column=0, columnspan=4, sticky="ew")
        
        # [新增] Aria2 全局设置行 (放在URL输入和按钮之间)
        settings_frame = ttk.Frame(input_container, style="Card.TFrame")
        settings_frame.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(0, 10))
        
        # 自动应用设置的回调函数
        def apply_aria2_settings(*args):
            if not self.aria2_rpc:
                return
            try:
                options = {
                    "max-concurrent-downloads": str(self.aria2_concurrent_var.get()),
                    "max-tries": str(self.aria2_retries_var.get()),
                }
                speed = self.aria2_speed_limit_var.get()
                if speed > 0:
                    options["max-overall-download-limit"] = f"{speed}M"
                else:
                    options["max-overall-download-limit"] = "0"
                self.aria2_rpc.change_global_option(options)
            except Exception as e:
                print(f"应用Aria2设置失败: {e}")
        
        # 并发数
        ttk.Label(settings_frame, text="并发数:", style="Card.TLabel").pack(side='left')
        self.aria2_concurrent_var = tk.IntVar(value=3)
        aria2_concurrent_spin = ttk.Spinbox(settings_frame, from_=1, to=20, 
            textvariable=self.aria2_concurrent_var, width=5, 
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), command=apply_aria2_settings)
        aria2_concurrent_spin.pack(side='left', padx=(5, 15))
        self.aria2_concurrent_var.trace_add("write", apply_aria2_settings)
        
        # 重试次数
        ttk.Label(settings_frame, text="重试:", style="Card.TLabel").pack(side='left')
        self.aria2_retries_var = tk.IntVar(value=5)
        aria2_retries_spin = ttk.Spinbox(settings_frame, from_=0, to=100, 
            textvariable=self.aria2_retries_var, width=5, 
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), command=apply_aria2_settings)
        aria2_retries_spin.pack(side='left', padx=(5, 15))
        self.aria2_retries_var.trace_add("write", apply_aria2_settings)
        
        # 限速 (0=不限速, 单位MB/s)
        ttk.Label(settings_frame, text="限速(M):", style="Card.TLabel").pack(side='left')
        self.aria2_speed_limit_var = tk.IntVar(value=4)
        aria2_speed_spin = ttk.Spinbox(settings_frame, from_=0, to=100, 
            textvariable=self.aria2_speed_limit_var, width=5, 
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), command=apply_aria2_settings)
        aria2_speed_spin.pack(side='left', padx=(5, 15))
        self.aria2_speed_limit_var.trace_add("write", apply_aria2_settings)
        
        
        # 添加空白行增加间距 (设置行与按钮行之间)
        ttk.Frame(input_container, height=15).grid(row=4, column=0, columnspan=4, sticky="ew")
        
        # 控制按钮
        btn_frame = ttk.Frame(input_container, style="Card.TFrame")
        btn_frame.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(0, 5))
        
        ttk.Button(btn_frame, text="➕ 添加任务", command=self._aria2_add_task, style="Success.TButton").pack(side='left', padx=(0, 5))
        ttk.Button(btn_frame, text="📁 添加BT种子", command=self._aria2_add_torrent).pack(side='left', padx=5)
        
        ttk.Separator(btn_frame, orient='vertical').pack(side='left', fill='y', padx=10)
        
        ttk.Button(btn_frame, text="⏸ 暂停选中", command=self._aria2_pause_selected).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="▶ 继续选中", command=self._aria2_resume_selected).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="🛑 停止并删除", command=self._aria2_stop_delete_selected, style="Danger.TButton").pack(side='left', padx=5)
        
        input_container.columnconfigure(0, weight=1)

        # 任务列表 (Treeview)
        # 外层Frame去边框
        mid_frame = ttk.Frame(frame) 
        mid_frame.pack(side='top', fill='both', expand=True, padx=10, pady=(0, 10))
        
        cols = ("gid", "status", "progress", "speed", "name", "url", "save_dir")
        self.aria2_tree = ttk.Treeview(mid_frame, columns=cols, show="headings", selectmode="extended")
        
        # 统一居左对齐
        self.aria2_tree.heading("gid", text="    GID", anchor="w")
        self.aria2_tree.heading("status", text="状态", anchor="w")
        self.aria2_tree.heading("progress", text="进度", anchor="w")
        self.aria2_tree.heading("speed", text="速度", anchor="w")
        self.aria2_tree.heading("name", text="文件名", anchor="w")
        self.aria2_tree.heading("url", text="链接", anchor="w")
        self.aria2_tree.heading("save_dir", text="保存目录", anchor="w")
        
        self.aria2_tree.column("gid", width=80, anchor="w")
        self.aria2_tree.column("status", width=80, anchor="w")
        self.aria2_tree.column("progress", width=80, anchor="w")
        self.aria2_tree.column("speed", width=100, anchor="w")
        self.aria2_tree.column("name", width=250, anchor="w")
        self.aria2_tree.column("url", width=300, anchor="w")
        self.aria2_tree.column("save_dir", width=200, anchor="w")
        
        vsb = ttk.Scrollbar(mid_frame, orient="vertical", command=self.aria2_tree.yview)
        hsb = ttk.Scrollbar(mid_frame, orient="horizontal", command=self.aria2_tree.xview)
        self.aria2_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.aria2_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        mid_frame.rowconfigure(0, weight=1)
        mid_frame.columnconfigure(0, weight=1)
        
        # [新增] Aria2右键菜单
        def aria2_context_menu(event):
            # 获取点击位置的item
            item = self.aria2_tree.identify_row(event.y)
            if not item:
                return
            
            # 选中该行
            self.aria2_tree.selection_set(item)
            gid = item  # Treeview的iid就是gid
            
            # 获取任务元数据
            with self.aria2_tasks_lock:
                task_meta = self.aria2_tasks.get(gid)
            
            if not task_meta:
                return
            
            menu = tk.Menu(self.root, tearoff=0, font=(FONT_FAMILY, FONT_SIZE_NORMAL))
            status = task_meta.status
            
            # ========== 根据任务状态显示不同菜单选项 ==========
            
            # 等待中/暂停的任务
            if status in ["waiting", "paused"]:
                def resume_task():
                    try:
                        self.aria2_daemon.client.unpause(gid)
                    except Exception as e:
                        SilentMessagebox.showerror("错误", f"继续任务失败: {e}")
                menu.add_command(label="▶️  继续下载", command=resume_task)
            
            # 下载中的任务
            if status == "active":
                def pause_task():
                    try:
                        self.aria2_daemon.client.pause(gid, force=True)
                    except Exception as e:
                        SilentMessagebox.showerror("错误", f"暂停任务失败: {e}")
                menu.add_command(label="⏸   暂停下载", command=pause_task)
            
            # ========== 通用选项 ==========
            menu.add_separator()
            
            # 复制URL
            def copy_url():
                self.root.clipboard_clear()
                self.root.clipboard_append(task_meta.url)
            menu.add_command(label="📋   复制URL", command=copy_url)
            
            # 打开保存目录
            if task_meta.save_dir and os.path.exists(task_meta.save_dir):
                def open_folder():
                    os.startfile(task_meta.save_dir)
                menu.add_command(label="📂  打开保存目录", command=open_folder)
            
            menu.add_separator()
            
            # 停止并删除 (由于右键菜单已选中该任务，直接调用已有方法)
            menu.add_command(label="🗑   停止并删除", command=self._aria2_stop_delete_selected)
            
            menu.post(event.x_root, event.y_root)
        
        self.aria2_tree.bind('<Button-3>', aria2_context_menu)
        self.aria2_tree.bind('<Button-2>', aria2_context_menu)

    def _aria2_add_task(self):
        """添加Aria2任务（磁力链接支持文件选择）"""
        if not self.aria2_rpc:
            SilentMessagebox.showerror("错误", "Aria2 RPC 未就绪")
            return
        
        url = self.aria2_url_var.get().strip()
        if not url:
            SilentMessagebox.showwarning("提示", "请输入下载链接")
            return
        
        save_dir = self.shared_save_dir_var.get()
        url_type = guess_url_type(url)
        
        # 检查是否是磁力链接
        is_magnet = url.startswith("magnet:")
        
        opts = {
            "dir": save_dir,
            "split": "2",
            "max-connection-per-server": "2",
            "continue": "true",
            "allow-overwrite": "false",
            "auto-file-renaming": "true",
        }
        
        # 如果是磁力链接，先暂停以便获取元数据后选择文件
        if is_magnet:
            opts["pause"] = "true"
            opts["seed-time"] = "0"  # 不做种
        
        try:
            gid = self.aria2_rpc.add_uri([url], opts)
            with self.aria2_tasks_lock:
                self.aria2_tasks[gid] = Aria2TaskMeta(
                    gid=gid,
                    url=url,
                    save_dir=save_dir,
                    url_type=url_type,
                    created_time=time.strftime("%Y-%m-%d %H:%M:%S")
                )
            self.aria2_url_var.set("")
            self.aria2_url_entry.delete("1.0", "end")  # 同时清空Text控件
            
            if is_magnet:
                print(f"已添加磁力任务 gid={gid}，正在获取元数据...")
                # 立即取消暂停以开始获取元数据
                try:
                    self.aria2_rpc.unpause(gid)
                except Exception as e:
                    print(f"取消暂停失败: {e}")
                
                # 启动后台线程等待元数据并显示文件选择
                threading.Thread(
                    target=self._wait_magnet_metadata_and_select,
                    args=(gid, url),
                    daemon=True
                ).start()
            else:
                print(f"已添加Aria2任务 gid={gid} url={url}")
        except Exception as e:
            SilentMessagebox.showerror("添加失败", str(e))

    def _wait_magnet_metadata_and_select(self, gid, url):
        """等待磁力链接元数据获取完成，然后显示文件选择对话框"""
        max_wait_seconds = 120  # 最多等待2分钟
        poll_interval = 2  # 每2秒检查一次
        
        start_time = time.time()
        files = []
        current_gid = gid  # 当前跟踪的GID（可能会因为followedBy而改变）
        
        print(f"开始等待磁力元数据 gid={gid}...")
        
        while time.time() - start_time < max_wait_seconds:
            try:
                status = self.aria2_rpc.tell_status(current_gid, 
                    ["status", "files", "bittorrent", "infoHash", "followedBy", "dir"])
                
                task_status = status.get("status", "")
                print(f"磁力任务状态: gid={current_gid}, status={task_status}")
                
                # 检查任务是否还存在
                if task_status == "removed":
                    print(f"磁力任务 {current_gid} 已被移除")
                    return
                
                # 检查是否有 followedBy（aria2 创建了新的下载任务）
                followed_by = status.get("followedBy", [])
                if followed_by:
                    new_gid = followed_by[0]
                    print(f"磁力任务 {current_gid} -> 跟踪新任务 {new_gid}")
                    
                    # 更新任务记录
                    with self.aria2_tasks_lock:
                        if current_gid in self.aria2_tasks:
                            task_meta = self.aria2_tasks[current_gid]
                            # 复制元数据到新GID
                            self.aria2_tasks[new_gid] = Aria2TaskMeta(
                                gid=new_gid,
                                url=task_meta.url,
                                save_dir=task_meta.save_dir,
                                url_type=task_meta.url_type,
                                created_time=task_meta.created_time
                            )
                    
                    current_gid = new_gid
                    time.sleep(poll_interval)
                    continue
                
                # 检查是否已获取到元数据（files 不为空且有文件名）
                files_info = status.get("files") or []
                print(f"文件数量: {len(files_info)}")
                
                if files_info:
                    # 检查是否有有效的文件路径（不是 [METADATA]）
                    valid_files = []
                    for idx, f in enumerate(files_info):
                        path = f.get("path", "").strip()
                        if path and "[METADATA]" not in path:
                            size = int(f.get("length", 0))
                            filename = os.path.basename(path)
                            valid_files.append((idx + 1, filename, size))
                            print(f"  文件 {idx+1}: {filename} ({size} bytes)")
                    
                    if valid_files:
                        files = valid_files
                        break
                
                time.sleep(poll_interval)
            except Exception as e:
                print(f"检查磁力元数据失败: {e}")
                time.sleep(poll_interval)
        
        if not files:
            # 超时或获取失败，直接开始下载
            print(f"磁力任务 {current_gid} 元数据获取超时或失败，直接开始下载")
            try:
                self.aria2_rpc.unpause(current_gid)
            except:
                pass
            return
        
        print(f"磁力元数据获取成功，共 {len(files)} 个文件，显示选择对话框")
        # 在主线程显示文件选择对话框
        self.root.after(0, lambda: self._show_magnet_file_select_dialog(current_gid, url, files))

    def _show_magnet_file_select_dialog(self, gid, url, files):
        """显示磁力链接文件选择对话框"""
        # 从URL中提取名称用于显示
        magnet_name = "磁力链接"
        if "dn=" in url:
            try:
                import urllib.parse
                dn_match = re.search(r'dn=([^&]+)', url)
                if dn_match:
                    magnet_name = urllib.parse.unquote(dn_match.group(1))
            except:
                pass
        
        # 如果只有一个文件，直接开始下载
        if len(files) == 1:
            try:
                # 只有非活动状态才需要unpause
                status = self.aria2_rpc.tell_status(gid, ["status"])
                if status.get("status") != "active":
                    self.aria2_rpc.unpause(gid)
                    print(f"磁力任务 {gid} 开始下载（单文件）")
                else:
                    print(f"磁力任务 {gid} 已在下载（单文件）")
            except Exception as e:
                print(f"继续磁力任务失败: {e}")
            return
        
        # 显示文件选择对话框
        dialog = TorrentFileSelectDialog(self.root, files, magnet_name)
        
        if dialog.result is None:
            # 用户取消，删除任务
            try:
                self.aria2_rpc.remove(gid, force=True)
                self.aria2_rpc.remove_download_result(gid)
                if self.aria2_tree.exists(gid):
                    self.aria2_tree.delete(gid)
                with self.aria2_tasks_lock:
                    if gid in self.aria2_tasks:
                        del self.aria2_tasks[gid]
                print(f"磁力任务 {gid} 已取消")
            except Exception as e:
                print(f"取消磁力任务失败: {e}")
            return
        
        # 用户选择了文件，设置 select-file 并继续下载
        try:
            if len(dialog.result) < len(files):
                # 只有部分文件被选中
                # 先暂停任务（如果正在运行）
                try:
                    self.aria2_rpc.pause(gid, force=True)
                    time.sleep(0.3)  # 等待暂停完成
                except:
                    pass
                
                # 设置 select-file
                select_file_str = ",".join(str(i) for i in sorted(dialog.result))
                self.aria2_rpc.change_option(gid, {"select-file": select_file_str})
                print(f"磁力任务 {gid} 选择下载文件: {select_file_str}")
            
            # 继续下载
            try:
                status = self.aria2_rpc.tell_status(gid, ["status"])
                if status.get("status") != "active":
                    self.aria2_rpc.unpause(gid)
            except:
                pass
                
            print(f"磁力任务 {gid} 开始下载（已选择 {len(dialog.result)}/{len(files)} 个文件）")
        except Exception as e:
            print(f"设置磁力任务选项失败: {e}")
            SilentMessagebox.showerror("错误", f"设置下载选项失败: {e}")

    def _aria2_pause_selected(self):
        """暂停选中的Aria2任务"""
        if not self.aria2_rpc:
            return
        for gid in self.aria2_tree.selection():
            try:
                self.aria2_rpc.pause(gid, force=True)
            except Exception as e:
                print(f"暂停失败 {gid}: {e}")

    def _aria2_resume_selected(self):
        """继续选中的Aria2任务"""
        if not self.aria2_rpc:
            return
        for gid in self.aria2_tree.selection():
            try:
                self.aria2_rpc.unpause(gid)
            except Exception as e:
                print(f"继续失败 {gid}: {e}")

    def _aria2_stop_delete_selected(self):
        """停止并删除选中的Aria2任务（同时删除临时文件）"""
        if not self.aria2_rpc:
            return
        for gid in self.aria2_tree.selection():
            self.aria2_ignored_gids.add(gid)
            
            # 收集需要删除的所有关联GID（处理磁力链接的followedBy关系）
            gids_to_delete = [gid]
            
            # 尝试获取任务关联信息
            try:
                status_info = self.aria2_rpc.tell_status(gid, ["files", "dir", "followedBy", "belongsTo"])
                
                # 如果有 followedBy，说明这是元数据任务，需要删除实际下载任务
                followed_by = status_info.get("followedBy") or []
                for followed_gid in followed_by:
                    if followed_gid not in gids_to_delete:
                        gids_to_delete.append(followed_gid)
                        self.aria2_ignored_gids.add(followed_gid)
                        print(f"发现关联任务 (followedBy): {followed_gid}")
                
                # 如果有 belongsTo，说明这是实际下载任务，需要删除元数据任务
                belongs_to = status_info.get("belongsTo")
                if belongs_to and belongs_to not in gids_to_delete:
                    gids_to_delete.insert(0, belongs_to)
                    self.aria2_ignored_gids.add(belongs_to)
                    print(f"发现父任务 (belongsTo): {belongs_to}")
                    
            except Exception as e:
                print(f"获取任务关联信息失败 {gid}: {e}")
            
            # 检查内存中的任务记录，查找相关联的任务
            # 处理元数据任务完成后无法从RPC获取的情况
            with self.aria2_tasks_lock:
                # 查找所有与当前任务URL相同的任务（可能是元数据任务和下载任务）
                current_task = self.aria2_tasks.get(gid)
                if current_task and current_task.url:
                    for other_gid, other_task in list(self.aria2_tasks.items()):
                        if other_gid not in gids_to_delete and other_task.url == current_task.url:
                            gids_to_delete.append(other_gid)
                            self.aria2_ignored_gids.add(other_gid)
                            print(f"发现关联任务 (相同URL): {other_gid}")
            
            # 同时检查UI中显示的任务，查找可能相关的任务
            for item in self.aria2_tree.get_children():
                if item not in gids_to_delete:
                    try:
                        values = self.aria2_tree.item(item, 'values')
                        if len(values) >= 6:
                            item_url = values[5]  # URL列
                            current_url = ""
                            with self.aria2_tasks_lock:
                                if gid in self.aria2_tasks:
                                    current_url = self.aria2_tasks[gid].url
                            if current_url and item_url and current_url == item_url:
                                gids_to_delete.append(item)
                                self.aria2_ignored_gids.add(item)
                                print(f"发现UI关联任务: {item}")
                    except:
                        pass
            
            # 直接从Aria2 RPC获取文件路径信息（在删除任务前获取）
            filepaths_to_delete = []
            for target_gid in gids_to_delete:
                try:
                    status_info = self.aria2_rpc.tell_status(target_gid, ["files", "dir"])
                    files = status_info.get("files") or []
                    for f in files:
                        filepath = (f.get("path") or "").strip()
                        if filepath and "[METADATA]" not in filepath and filepath not in filepaths_to_delete:
                            filepaths_to_delete.append(filepath)
                except Exception as e:
                    print(f"获取文件路径失败 {target_gid}: {e}")
            
            if filepaths_to_delete:
                print(f"获取到文件路径: {filepaths_to_delete}")
            
            # 如果RPC获取失败，尝试从缓存获取
            if not filepaths_to_delete:
                with self.aria2_tasks_lock:
                    if gid in self.aria2_tasks:
                        task_meta = self.aria2_tasks[gid]
                        if task_meta.filepaths:
                            filepaths_to_delete = list(task_meta.filepaths)
            
            # 删除所有关联任务
            for target_gid in gids_to_delete:
                try:
                    # 尝试 remove (针对 active/waiting/paused)
                    try:
                        self.aria2_rpc.remove(target_gid, force=True)
                    except:
                        pass
                    
                    # 尝试 removeDownloadResult (针对 complete/error/removed)
                    try:
                        self.aria2_rpc.remove_download_result(target_gid)
                    except:
                        pass
                    
                    # 清理UI和内存
                    if self.aria2_tree.exists(target_gid):
                        self.aria2_tree.delete(target_gid)
                    with self.aria2_tasks_lock:
                        if target_gid in self.aria2_tasks:
                            del self.aria2_tasks[target_gid]
                    print(f"已删除任务: {target_gid}")
                except Exception as e:
                    print(f"清理任务失败 {target_gid}: {e}")
            
            # 删除临时文件（用户主动删除时才删除文件）
            deleted_dirs = set()  # 记录需要清理的目录
            for filepath in filepaths_to_delete:
                try:
                    # 删除主文件（可能是部分下载的文件）
                    if os.path.exists(filepath):
                        os.remove(filepath)
                        print(f"已删除文件: {filepath}")
                        # 记录父目录
                        deleted_dirs.add(os.path.dirname(filepath))
                    # 删除.aria2控制文件
                    aria2_file = filepath + ".aria2"
                    if os.path.exists(aria2_file):
                        os.remove(aria2_file)
                        print(f"已删除控制文件: {aria2_file}")
                except Exception as e:
                    print(f"删除文件失败 {filepath}: {e}")
            
            # 清理空文件夹（从子目录到父目录）
            for dir_path in sorted(deleted_dirs, key=lambda x: x.count('/'), reverse=True):
                try:
                    # 尝试逐级向上删除空目录
                    current_dir = dir_path
                    save_dir = self.shared_save_dir_var.get()
                    while current_dir and current_dir != save_dir and len(current_dir) > len(save_dir):
                        if os.path.exists(current_dir) and os.path.isdir(current_dir):
                            # 检查目录是否为空
                            if not os.listdir(current_dir):
                                os.rmdir(current_dir)
                                print(f"已删除空目录: {current_dir}")
                                # 删除目录级别的.aria2文件
                                dir_aria2 = current_dir + ".aria2"
                                if os.path.exists(dir_aria2):
                                    os.remove(dir_aria2)
                                    print(f"已删除目录控制文件: {dir_aria2}")
                            else:
                                break  # 目录不为空，停止向上
                        current_dir = os.path.dirname(current_dir)
                except Exception as e:
                    print(f"删除目录失败 {dir_path}: {e}")

    def _aria2_add_torrent(self):
        """添加BT种子文件（支持文件选择）"""
        if not self.aria2_rpc:
            SilentMessagebox.showerror("错误", "Aria2 RPC 未就绪")
            return
        
        filepath = filedialog.askopenfilename(
            title="选择BT种子文件",
            filetypes=[("Torrent files", "*.torrent"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        save_dir = self.shared_save_dir_var.get()
        torrent_name = os.path.basename(filepath)
        
        try:
            with open(filepath, 'rb') as f:
                torrent_data = f.read()
            
            # 解析种子文件获取文件列表
            files = parse_torrent_files(torrent_data)
            
            if not files:
                SilentMessagebox.showerror("错误", "无法解析种子文件")
                return
            
            # 如果只有一个文件，直接下载；如果有多个文件，显示选择对话框
            selected_indices = None
            if len(files) > 1:
                dialog = TorrentFileSelectDialog(self.root, files, torrent_name)
                if dialog.result is None:
                    return  # 用户取消
                selected_indices = dialog.result
            
            # 构建下载选项
            opts = {
                "dir": save_dir,
                "seed-time": "0",  # 不做种
            }
            
            # 如果用户选择了特定文件，设置 select-file 选项
            if selected_indices and len(selected_indices) < len(files):
                # aria2 的 select-file 格式: "1,2,5-8"
                opts["select-file"] = ",".join(str(i) for i in sorted(selected_indices))
                print(f"选择下载文件: {opts['select-file']}")
            
            gid = self.aria2_rpc.add_torrent(torrent_data, opts)
            
            with self.aria2_tasks_lock:
                self.aria2_tasks[gid] = Aria2TaskMeta(
                    gid=gid,
                    url=f"[BT] {torrent_name}",
                    save_dir=save_dir,
                    url_type="torrent",
                    created_time=time.strftime("%Y-%m-%d %H:%M:%S")
                )
            
            selected_info = f" (已选择 {len(selected_indices)}/{len(files)} 个文件)" if selected_indices else ""
            print(f"已添加BT种子任务 gid={gid} file={torrent_name}{selected_info}")
        except Exception as e:
            SilentMessagebox.showerror("添加失败", str(e))

    # --- (重构) 核心UI构建函数 ---
    def _create_download_tab(self, notebook, title, manager, InputFrameClass):
        """
        (重构)
        创建一个标准的下载标签页 (左侧: 输入+队列, 右侧: 日志)。
        """
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=title)
        
        # 1. 主布局 - 使用 PanedWindow 支持拖动调整左右比例
        paned = ttk.PanedWindow(frame, orient='horizontal')
        paned.pack(fill='both', expand=True, padx=10, pady=(5, 10))
        
        left_frame = ttk.Frame(paned)
        right_frame = ttk.Frame(paned)
        
        paned.add(left_frame, weight=1)
        paned.add(right_frame, weight=1)
        
        # 设置最小面板宽度，防止拖动时UI元素被隐藏
        self.root.update_idletasks()  # 先更新布局
        paned.sashpos(0, 600)  # 设置初始分割位置
        
        # 2. 左侧 (输入 + 队列)
        input_frame = InputFrameClass(left_frame, manager, self)
        input_frame.pack(fill='x', pady=(0, 5))
        
        queue_frame = ttk.LabelFrame(left_frame, text="   下载队列", padding="5")
        queue_frame.pack(fill='both', expand=True, pady=(5, 0))
        
        # [重构] 将Listbox替换为Treeview表格
        cols = ("id", "status", "progress", "speed", "name", "type")
        task_tree = ttk.Treeview(queue_frame, columns=cols, show="headings", 
                                  selectmode="extended", height=8, takefocus=False)
        
        # 设置列标题 (统一居左对齐)
        task_tree.heading("id", text="    ID", anchor="w")
        task_tree.heading("status", text="状态", anchor="w")
        task_tree.heading("progress", text="进度", anchor="w")
        task_tree.heading("speed", text="速度", anchor="w")
        task_tree.heading("name", text="文件名", anchor="w")
        task_tree.heading("type", text="类型", anchor="w")
        
        # 设置列宽度 (统一居左对齐) - 加宽队列显示
        task_tree.column("id", width=70, minwidth=60, anchor="w")
        task_tree.column("status", width=90, minwidth=80, anchor="w")
        task_tree.column("progress", width=100, minwidth=80, anchor="w")
        task_tree.column("speed", width=110, minwidth=90, anchor="w")
        task_tree.column("name", width=280, minwidth=150, anchor="w")
        task_tree.column("type", width=80, minwidth=60, anchor="w")
        
        # 滚动条
        vsb = ttk.Scrollbar(queue_frame, orient="vertical", command=task_tree.yview)
        hsb = ttk.Scrollbar(queue_frame, orient="horizontal", command=task_tree.xview)
        task_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # 使用grid布局
        task_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        queue_frame.rowconfigure(0, weight=1)
        queue_frame.columnconfigure(0, weight=1)
        
        # (关键) 将 Treeview 实例注入 Manager
        manager.treeview = task_tree
        
        # [重构] 右键菜单 - 完整的单任务管理功能
        def task_control_handler(event):
            # 获取点击位置的item
            item = task_tree.identify_row(event.y)
            if not item:
                return
            
            # 选中该行
            task_tree.selection_set(item)
            task_id = item  # Treeview的iid就是任务ID
            
            # 查找任务对象
            task_obj = None
            for t in manager.running_tasks.values():
                if t.id == task_id:
                    task_obj = t
                    break
            if not task_obj:
                for t in manager.task_queue:
                    if t.id == task_id:
                        task_obj = t
                        break
            
            if task_obj:
                menu = tk.Menu(self.root, tearoff=0, font=(FONT_FAMILY, FONT_SIZE_NORMAL))
                
                # ========== 根据任务状态显示不同菜单选项 ==========
                
                # 等待中的任务
                if task_obj.status == TASK_STATUS_WAITING:
                    menu.add_command(label="▶️  开始此任务", 
                        command=lambda: manager.start_task(task_id))
                    menu.add_command(label="🔝  移到队列顶部", 
                        command=lambda: manager.move_task_to_top(task_id))
                
                # 下载中的任务
                if task_obj.status == TASK_STATUS_RUNNING:
                    menu.add_command(label="🛑  停止下载", 
                        command=lambda: manager.stop_task(task_id))
                
                # 失败/已停止的任务
                if task_obj.status in [TASK_STATUS_FAILED, TASK_STATUS_STOPPED]:
                    menu.add_command(label="🔄  重试下载", 
                        command=lambda: manager.retry_task(task_id))
                
                # ========== 通用选项 ==========
                menu.add_separator()
                
                # 复制URL
                def copy_url():
                    self.root.clipboard_clear()
                    self.root.clipboard_append(task_obj.url)
                    manager.log(f"📋 已复制URL到剪贴板")
                menu.add_command(label="📋   复制URL", command=copy_url)
                
                # 打开保存目录 (只对完成的任务显示)
                if task_obj.status == TASK_STATUS_SUCCESS:
                    def open_folder():
                        save_path = task_obj.save_path
                        if os.path.exists(save_path):
                            os.startfile(save_path)
                        else:
                            messagebox.showwarning("提示", f"目录不存在: {save_path}")
                    menu.add_command(label="📂  打开保存目录", command=open_folder)
                
                menu.add_separator()
                
                # 删除任务 (非下载中状态可删除)
                if task_obj.status != TASK_STATUS_RUNNING:
                    menu.add_command(label="🗑  删除任务", 
                        command=lambda: manager.clear_task(task_id))
                else:
                    # 下载中的任务显示"停止并删除"
                    def stop_and_delete():
                        manager.stop_task(task_id)
                        # 延迟更长时间确保任务完全停止后再清理
                        def delayed_clear():
                            manager.clear_task(task_id)
                            # 额外触发一次临时文件清理（确保清理）
                            manager.force_cleanup = True
                            self.root.after(2000, manager._cleanup_temp_files)
                        self.root.after(2000, delayed_clear)
                    menu.add_command(label="🗑  停止并删除", command=stop_and_delete)
                
                menu.post(event.x_root, event.y_root)
        
        task_tree.bind('<Button-3>', task_control_handler)
        task_tree.bind('<Button-2>', task_control_handler)
        
        # 3. 右侧 (日志) (通用)
        # 创建日志区域的标题栏 (包含标题和按钮)
        log_header = ttk.Frame(right_frame)
        log_header.pack(fill='x', pady=(0, 2))  # 减少标题和边框之间的间距
        
        ttk.Label(log_header, text="   下载日志", font=(FONT_FAMILY, FONT_SIZE_NORMAL, 'bold')).pack(side='left')
        
        # 日志按钮放在标题右边
        ttk.Button(log_header, text="历史记录",
                  command=lambda m=manager.mode: (self.load_history(m), self.show_history())).pack(side='right', padx=2)
        ttk.Button(log_header, text="清空日志",
                  command=manager.clear_log).pack(side='right', padx=2)
        
        # 日志内容区域 (使用浅色边框样式)
        log_frame = ttk.LabelFrame(right_frame, text="", padding="10")
        log_frame.pack(fill='both', expand=True)
        
        log_text = tk.Text(log_frame, height=20, state='disabled', font=('Microsoft YaHei', 9))
        log_text.pack(fill='both', expand=True, side='left')
        
        log_scrollbar = ttk.Scrollbar(log_frame, orient='vertical', command=log_text.yview)
        log_scrollbar.pack(side='right', fill='y')
        log_text.config(yscrollcommand=log_scrollbar.set)
        
        # (关键) 将 Log Text 实例注入 Manager
        manager.log_text = log_text
        
        # M3U8 日志需要红色标签
        if manager.mode == 'm3u8':
            init_log_red_tag(log_text)

    # --- (重构) UI 辅助方法 ---
    def load_history(self, mode):
        """加载指定模式的历史记录到 self.current_history_data"""
        file = HISTORY_FILES.get(mode)
        if not file or not os.path.exists(file):
            self.current_history_data = []
            self.current_history_mode = mode
            return
        try:
            with open(file, "r", encoding="utf-8") as f:
                self.current_history_data = json.load(f)
            self.current_history_mode = mode
        except:
            self.current_history_data = []
            self.current_history_mode = mode

    def show_history(self):
        """(重构) 显示 self.current_history_data"""
        win = tk.Toplevel(self.root)
        win.title("下载历史记录 - 详细信息")
        win.geometry("800x600")
        
        # 文本显示区域
        text_frame = ttk.Frame(win)
        text_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        text = tk.Text(text_frame, wrap="word", yscrollcommand=scrollbar.set)
        text.pack(expand=True, fill="both", side=tk.LEFT)
        scrollbar.config(command=text.yview)
        
        if not self.current_history_data:
            text.insert("end", "暂无历史记录")
        else:
            for item in self.current_history_data:
                title = item.get('title', 'N/A')
                type_str = item.get('type', 'N/A')
                url = item.get('url', 'N/A')
                path = item.get('path', 'N/A')
                time_str = item.get('time', 'N/A')
                kwargs = item.get('kwargs', {})
                
                detail_str = f"任务标题: {title}\n"
                detail_str += f"下载类型: {type_str.capitalize()} \n"
                detail_str += f"URL: {url}\n"
                detail_str += f"保存路径: {path}\n"
                detail_str += f"完成时间: {time_str}\n"
                
                if type_str in ['youtube', 'bilibili']:
                    fmt = kwargs.get('format', 'N/A')
                    sub = kwargs.get('sub_lang', '无')
                    retry = kwargs.get('retries', 3)
                    detail_str += f"下载格式: {fmt}\n"
                    if type_str == 'youtube':
                        detail_str += f"字幕语言: {sub}\n"
                    detail_str += f"重试次数: {retry}\n"
                elif type_str == 'm3u8':
                    filename = kwargs.get('filename', 'output')
                    threads = kwargs.get('threads', 16)
                    headers = kwargs.get('headers', '')
                    detail_str += f"文件名: {filename}\n"
                    detail_str += f"线程数: {threads}\n"
                    if headers:
                        detail_str += f"Headers: [已设置]\n"
                elif type_str == 'tiktok' or type_str == 'general':
                    retry = kwargs.get('retries', 3)
                    custom_filename = kwargs.get('custom_filename', '')
                    detail_str += f"重试次数: {retry}\n"
                    if custom_filename:
                        detail_str += f"自定义文件名: {custom_filename}\n"
                
                detail_str += "=" * 60 + "\n\n"
                text.insert("end", detail_str)
        
        # 底部按钮
        btn_frame = ttk.Frame(win)
        btn_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        # 清空全部历史按钮
        def on_clear_all():
            """清空全部历史记录"""
            if not self.current_history_data:
                return  # 没有历史记录就直接返回
            
            self.clear_all_history(self.current_history_mode)
            win.destroy()  # 关闭窗口
        
        ttk.Button(btn_frame, text="🗑 清空全部历史", command=on_clear_all).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="关闭", command=win.destroy).pack(side='right', padx=5)
    
    def clear_all_history(self, mode):
        """清空指定模式的全部历史记录"""
        try:
            file = HISTORY_FILES.get(mode)
            if not file:
                return
            
            # 清空文件内容
            with open(file, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            
            # 更新当前数据
            self.current_history_data = []
        except Exception:
            pass  # 静默失败

    def choose_directory(self):
        """(重构) 选择保存文件夹"""
        current_path = self.shared_save_dir_var.get()
        folder = filedialog.askdirectory(title="选择保存文件夹", initialdir=current_path)
        if folder:
            self.shared_save_dir_var.set(folder)

    def open_save_directory(self):
        """(重构) 打开当前设置的保存目录"""
        current_path = self.shared_save_dir_var.get()
        try:
            if os.path.exists(current_path):
                if os.name == 'nt':
                    os.startfile(current_path)
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', current_path])
                else:
                    subprocess.Popen(['xdg-open', current_path])
            else:
                SilentMessagebox.showwarning("提示", "保存目录不存在")
        except Exception as e:
            SilentMessagebox.showerror("错误", f"无法打开目录: {e}")

    def update_yt_dlp(self):
        """(重构) 更新 yt-dlp.exe"""
        url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
        self.main_status_var.set("正在更新 yt-dlp...")
        
        def run_update():
            try:
                urllib.request.urlretrieve(url, yt_dlp_path)
                self.root.after(0, lambda: [
                    SilentMessagebox.showinfo("更新完成", "yt-dlp 已更新到最新版!"),
                    self.main_status_var.set("就绪")
                ])
            except Exception as e:
                self.root.after(0, lambda: [
                    SilentMessagebox.showerror("更新失败", f"更新 yt-dlp 失败:{e}"),
                    self.main_status_var.set("更新失败")
                ])
        
        try:
            threading.Thread(target=run_update, daemon=True).start()
        except Exception as e:
            SilentMessagebox.showerror("错误", f"启动更新失败:{e}")
            self.main_status_var.set("就绪")

    def update_n_m3u8dl_re(self):
        """(重构) 更新 N_M3U8DL-RE.exe"""
        API_URL = "https://api.github.com/repos/nilaoda/N_m3u8DL-RE/releases/latest"
        self.m3u8_tool_status_var.set("N_M3U8DL-RE: 正在检查更新...")
        
        def run_update():
            try:
                with urllib.request.urlopen(API_URL) as response:
                    release_info = json.loads(response.read().decode('utf-8'))
                
                download_url = None
                exe_name = "N_m3u8DL-RE.exe"
                for asset in release_info.get('assets', []):
                    if 'win' in asset['name'] and 'x64' in asset['name'] and asset['name'].endswith('.zip') and 'arm64' not in asset['name'] and 'x86' not in asset['name']:
                        download_url = asset['browser_download_url']
                        break
                
                if not download_url:
                    raise RuntimeError("未找到 Windows x64 版本的下载链接。")
                
                self.m3u8_tool_status_var.set("N_M3U8DL-RE: 正在下载...")
                req = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
                
                with urllib.request.urlopen(req) as response:
                    zip_bytes = response.read()
                
                with io.BytesIO(zip_bytes) as zip_buffer:
                    with zipfile.ZipFile(zip_buffer) as zf:
                        if exe_name in zf.namelist():
                            with zf.open(exe_name) as source, open(N_M3U8DL_RE_PATH, "wb") as target:
                                target.write(source.read())
                        else:
                            raise RuntimeError(f"Zip文件中未包含 {exe_name}。")
                
                self.root.after(0, lambda: [
                    SilentMessagebox.showinfo("更新完成", "N_M3U8DL-RE 已更新到最新版!"),
                    self.check_m3u8_tool_status()
                ])
            except Exception as e:
                self.root.after(0, lambda: [
                    SilentMessagebox.showerror("更新失败", f"更新 N_M3U8DL-RE 失败: {e}"),
                    self.check_m3u8_tool_status()
                ])
        
        try:
            threading.Thread(target=run_update, daemon=True).start()
        except Exception as e:
            SilentMessagebox.showerror("错误", f"启动更新失败: {e}")
            self.check_m3u8_tool_status()

    def check_m3u8_tool_status(self):
        """(重构) 检测 N_M3U8DL-RE.exe 是否存在"""
        if os.path.exists(N_M3U8DL_RE_PATH):
            self.m3u8_tool_status_var.set("N_M3U8DL-RE: 就绪")
        else:
            self.m3u8_tool_status_var.set("N_M3U8DL-RE: 未找到")
            self.root.after(1000, lambda: messagebox.showwarning(
                "工具缺失",
                f"未找到 N_M3U8DL-RE.exe ({os.path.basename(N_M3U8DL_RE_PATH)}),M3U8下载功能将不可用。请点击 '更新N_M3U8DL-RE' 按钮下载。"
            ))

    def notify_cookies_error(self):
        """提示Cookies失效（仅提示一次）"""
        if not self.cookies_error_notified:
            self.cookies_error_notified = True
            self.root.after(500, lambda: messagebox.showwarning(
                "⚠️ Cookies可能已失效",
                "检测到YouTube cookies文件可能已失效或过期。\n\n"
                "💡 解决方法：\n"
                "1. 使用浏览器插件重新导出cookies\n"
                "2. 确保导出的是 www.youtube.com_cookies.txt\n"
                "3. 将文件放在程序同一目录下\n\n"
                "推荐插件: Get cookies.txt LOCALLY\n"
                "(Chrome/Edge/Firefox 扩展商店搜索)"
            ))

# ============ (重构) 输入框基类 ============
class BaseInputFrame(ttk.LabelFrame):
    """(重构) 用于构建输入区域的基类"""
    def __init__(self, parent, manager, app):
        super().__init__(parent, text="", padding="12")  #➕ 添加下载任务
        self.manager = manager
        self.app = app  # 引用主 App
        self.shared_save_dir_var = app.shared_save_dir_var
        self._create_widgets()

    def _create_widgets(self):
        """子类必须实现此方法来创建其特定的UI控件"""
        raise NotImplementedError

    def _create_common_buttons(self, add_task_command):
        """创建通用的"添加/开始全部/清除/停止"按钮"""
        button_frame = ttk.Frame(self)
        button_frame.pack(fill='x', pady=(15, 0))
        
        ttk.Button(button_frame, text="✚ 添加到队列",
                  command=add_task_command, style="Primary.TButton").pack(side='left', padx=5)
        
        ttk.Button(button_frame, text="▶ 开始全部",
                  command=self.manager.start_all_tasks, style="Success.TButton").pack(side='left', padx=5)
        
        ttk.Button(button_frame, text="❌ 停止全部",
                  command=self.manager.stop_all, style="Danger.TButton").pack(side='left', padx=5)
                  
        ttk.Button(button_frame, text="🗑 清除完成",
                  command=self.manager.clear_completed).pack(side='right', padx=5)

    def _create_concurrency_spinbox(self, parent, manager, default_val=1, grid_row=1, grid_col_start=2, padx=(0,0)):
        """创建并发设置 Spinbox"""
        ttk.Label(parent, text="并发数:", font=(FONT_FAMILY, FONT_SIZE_NORMAL - 1))\
            .grid(row=grid_row, column=grid_col_start, sticky='w', pady=(5, 0), padx=padx)
        
        var = tk.IntVar(value=default_val)
        
        def on_concurrent_change(*args):
            manager.max_concurrent = var.get()
            manager.start_next_task()
        
        var.trace_add('write', on_concurrent_change)
        
        spinbox = ttk.Spinbox(parent, from_=1, to=10, textvariable=var, width=5,
                             font=(FONT_FAMILY, FONT_SIZE_NORMAL),
                             command=lambda: setattr(manager, 'max_concurrent', var.get()))
        spinbox.grid(row=grid_row, column=grid_col_start + 1, sticky='w', padx=5, pady=(5, 0))
        
        return var

    def _create_speedlimit_spinbox(self, parent, default_val=2):
        """创建限速 Spinbox"""
        ttk.Label(parent, text="限速(MB/s):", font=(FONT_FAMILY, FONT_SIZE_NORMAL - 1))\
            .grid(row=1, column=4, sticky='w', padx=(15, 0), pady=(5, 0))
        
        var = tk.IntVar(value=default_val)
        ttk.Spinbox(parent, from_=0, to=100, textvariable=var, width=5,
                   font=(FONT_FAMILY, FONT_SIZE_NORMAL)).grid(row=1, column=5, sticky='w', padx=5, pady=(5, 0))
        
        ttk.Label(parent, text="(0=不限)", font=(FONT_FAMILY, 8), foreground="gray")\
            .grid(row=1, column=6, sticky='w', pady=(5, 0))
        
        return var

    def _create_retry_spinbox(self, parent, default_val=3):
        """创建重试次数 Spinbox"""
        ttk.Label(parent, text="重    试: ", font=(FONT_FAMILY, FONT_SIZE_NORMAL - 1))\
            .grid(row=1, column=0, sticky='w', pady=(5, 0))
        
        var = tk.IntVar(value=default_val)
        ttk.Spinbox(parent, from_=0, to=10, textvariable=var, width=5,
                   font=(FONT_FAMILY, FONT_SIZE_NORMAL)).grid(row=1, column=1, sticky='w', padx=5, pady=(5, 0))
        
        return var

# ============ 统一视频下载输入框 ============
class UnifiedVideoInputFrame(BaseInputFrame):
    """统一的视频下载输入框（合并YouTube/Bilibili/通用）"""
    def _create_widgets(self):
        # 1. URL Input (Title style)
        url_frame = ttk.Frame(self)
        url_frame.pack(fill='x', pady=(0, 5))
        
        ttk.Label(url_frame, text="视频 URL:", font=(FONT_FAMILY, FONT_SIZE_TITLE, 'bold')).pack(anchor='w')
        # 使用tk.Text替代ttk.Entry，完全模仿m3u8的默认样式
        self.url_var = tk.StringVar()
        self.url_entry = tk.Text(url_frame, height=2, width=65, wrap='word', font=(FONT_FAMILY, FONT_SIZE_NORMAL))
        self.url_entry.pack(fill='x', pady=(5, 0))
        
        # 绑定Text控件更新到内部变量（保持兼容性）
        def update_url_from_text(*args):
            self.url_var.set(self.url_entry.get("1.0", "end-1c"))
        self.url_entry.bind("<KeyRelease>", update_url_from_text)
        
        ttk.Label(url_frame, text="支持平台: YouTube / Bilibili / TikTok / 通用网页", 
                  font=(FONT_FAMILY, 8), foreground="#888888").pack(anchor='w', side='right',pady=(2, 0))
                  
        # 2. Format & Resolution (Card Style)
        format_card = ttk.Frame(self, style="Card.TFrame", padding=5)
        format_card.pack(fill='x', pady=5)
        
        # Row 1: Actions (按钮行放在前面)
        btn_row = ttk.Frame(format_card, style="Card.TFrame")
        btn_row.pack(fill='x', pady=(0, 10))  # 增加按钮与下拉框之间的间距
        
        ttk.Button(btn_row, text="🔍 获取分辨率/格式", 
                   command=lambda: threading.Thread(target=self.fetch_formats, daemon=True).start(),
                   style="Info.Small.TButton"
                  ).pack(side='left', padx=(0, 5))
        
        ttk.Button(btn_row, text="⚡ 直接下载",
                   command=self.add_direct_task,
                   style="Warning.Small.TButton"
                  ).pack(side='left', padx=5)

        # Row 2: Combo (下拉框放在按钮下面)
        res_row = ttk.Frame(format_card, style="Card.TFrame")
        res_row.pack(fill='x')
        ttk.Label(res_row, text="分辨率/格式:", style="Card.TLabel").pack(side='left')
        self.format_var_combo = tk.StringVar()
        self.format_combo = ttk.Combobox(res_row, textvariable=self.format_var_combo, state="readonly", width=45)
        self.format_combo.pack(side='left', padx=10, fill='x', expand=True)

        # 3. Rename & Options (Card Style)
        options_card = ttk.Frame(self, style="Card.TFrame", padding=5)
        options_card.pack(fill='x', pady=5)
        
        # Row 1: Filename
        file_row = ttk.Frame(options_card, style="Card.TFrame")
        file_row.pack(fill='x', pady=(0, 5))
        ttk.Label(file_row, text="重命名:", style="Card.TLabel").pack(side='left')
        self.custom_filename_var = tk.StringVar()
        # 使用tk.Text替代ttk.Entry，采用默认样式
        filename_entry = tk.Text(file_row, height=1, width=30, wrap='word', font=(FONT_FAMILY, FONT_SIZE_NORMAL))
        filename_entry.pack(side='left', padx=10, fill='x', expand=True)
        
        # 绑定Text控件到变量
        def update_filename_var(*args):
            self.custom_filename_var.set(filename_entry.get("1.0", "end-1c"))
        filename_entry.bind("<KeyRelease>", update_filename_var)
        self.filename_entry_widget = filename_entry
        
        ttk.Label(file_row, text="(可选 | 留空则自动从网页获取)", font=(FONT_FAMILY, 8), foreground="#888888", style="Card.TLabel").pack(side='left')

        # Row 2: Spinboxes
        settings_row = ttk.Frame(options_card, style="Card.TFrame")
        settings_row.pack(fill='x')
        
        self.retry_var = self._create_retry_spinbox(settings_row)
        self.concurrent_var = self._create_concurrency_spinbox(settings_row, self.manager, padx=(15, 0))
        self.speedlimit_var = self._create_speedlimit_spinbox(settings_row)
        
        # 4. Main Buttons
        self._create_common_buttons(self.add_task)
        
        # State vars
        self.format_fetch_used_cookies = False
        self.detected_url_type = None

    def fetch_formats(self):
        """获取视频的可用格式 - 自动检测类型"""
        url = self.url_entry.get("1.0", "end-1c").strip()
        if not url:
            self.app.root.after(0, lambda: SilentMessagebox.showwarning("提示", "请输入视频 URL"))
            return
        
        # 检测URL类型
        self.detected_url_type = detect_video_url_type(url)
        type_labels = {'youtube': 'YouTube', 'bilibili': 'Bilibili', 'general': '通用'}
        
        self.manager.log(f"正在获取可用格式... (类型: {type_labels.get(self.detected_url_type, '未知')})")
        self.format_fetch_used_cookies = False  # 重置标记
        
        def run_fetch():
            try:
                # 第一次尝试:不使用cookies
                cmd = [yt_dlp_path, "--dump-single-json", "--no-warnings", url]
                self.manager.log("📡 尝试获取格式...")
                
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60, startupinfo=startupinfo)
                
                # 如果失败,尝试使用cookies重试（仅YouTube）
                if proc.returncode != 0 and self.detected_url_type == 'youtube':
                    if os.path.exists(COOKIES_FILE_PATH):
                        self.manager.log("⚠️ 获取格式失败,尝试使用cookies重试...")
                        cmd_with_cookies = [yt_dlp_path, "--dump-single-json", "--no-warnings",
                                           "--cookies", COOKIES_FILE_PATH, url]
                        proc = subprocess.run(cmd_with_cookies, capture_output=True, text=True, 
                                            timeout=60, startupinfo=startupinfo)
                        if proc.returncode == 0:
                            self.format_fetch_used_cookies = True
                            self.manager.log("✓ 使用cookies成功获取格式")
                        else:
                            # 检测是否为cookies失效
                            if detect_cookies_error(proc.stderr):
                                self.manager.log("❌ Cookies可能已失效!", "ERROR")
                                self.manager.log("💡 建议: 重新导出cookies文件 (www.youtube.com_cookies.txt)", "ERROR")
                                if hasattr(self.app, 'notify_cookies_error'):
                                    self.app.root.after(0, self.app.notify_cookies_error)
                    else:
                        raise RuntimeError(f"获取失败且未找到cookies文件: {proc.stderr[:100]}")
                
                if proc.returncode != 0:
                    error_msg = proc.stderr if proc.stderr else proc.stdout
                    raise RuntimeError(f"获取格式失败: {error_msg[:200]}")
                
                info = json.loads(proc.stdout.strip())
                formats = []
                
                # 解析格式列表
                for f in info.get("formats", []):
                    height = f.get("height") or 0
                    ext = f.get("ext")
                    if f.get("vcodec") == "none" or height < 720: continue
                    if f.get('protocol', '').startswith('m3u8') or f.get('protocol', '').startswith('dash'): continue
                    
                    fps = f.get("fps") or 0
                    raw_vcodec = f.get("vcodec") or "未知"
                    vcodec_match = re.match(r'^(av01|avc1|vp09|vp9|hev1|h264)', raw_vcodec, re.IGNORECASE)
                    vcodec = vcodec_match.group(0) if vcodec_match else "未知"

                    # [修改] 过滤编码为"未知"的格式 (TikTok会员专享等)
                    if vcodec == "未知":
                        continue
                    
                    res_label = f"{height}p ({fps}fps)" if fps and fps >= 50 else f"{height}p"
                    fmt_line = f"{f.get('format_id')} - [{vcodec}] - {res_label} - {ext}"
                    formats.append(fmt_line)
                
                if not formats:
                    raise RuntimeError("未找到符合条件的格式")
                
                unique_formats = sorted(list(set(formats)), 
                                      key=lambda x: int(re.search(r'(\d+)p', x).group(1)), reverse=True)
                
                def update_ui():
                    self.format_combo.configure(values=unique_formats)
                    self.format_var_combo.set(unique_formats[0])
                    self.manager.log(f"✓ 获取到 {len(unique_formats)} 个格式")
                
                self.app.root.after(0, update_ui)
            except Exception as e:
                err_msg = str(e)
                self.app.root.after(0, lambda msg=err_msg: self.manager.log(f"❌ 获取格式失败: {msg}"))
        
        threading.Thread(target=run_fetch, daemon=True).start()

    def add_task(self):
        url = self.url_entry.get("1.0", "end-1c").strip()
        if not url:
            SilentMessagebox.showwarning("提示", "请输入视频 URL")
            return
        
        # 自动检测URL类型
        url_type = detect_video_url_type(url)
        self.manager.log(f"URL: {url} (类型: {url_type})")
        
        # 获取自定义文件名
        custom_filename = self.custom_filename_var.get().strip()
        
        # 检查文件名是否包含非法字符
        if custom_filename:
            invalid_chars = r'\/:*?"<>|'
            if any(char in custom_filename for char in invalid_chars):
                self.manager.log(f"❌ 添加任务失败: 文件名包含非法字符 {invalid_chars}", "ERROR")
                SilentMessagebox.showerror("错误", f"文件名不能包含以下字符:\n{invalid_chars}")
                return
            self.manager.log(f"✓ 将使用自定义文件名: {custom_filename}")
        
        # 获取格式选择
        fmt_choice = self.format_var_combo.get().strip()
        if not fmt_choice:
            SilentMessagebox.showwarning("提示", "请先获取并选择格式")
            return
        
        format_id = fmt_choice.split(' - ')[0]
        fmt_expr = f"{format_id}+bestaudio[ext=m4a]"
        
        speed_limit = self.speedlimit_var.get()
        
        # 创建任务（使用统一的类型标识）
        task = DownloadTask(
            url_type,  # 自动检测的类型
            url,
            self.shared_save_dir_var.get(),
            format=fmt_expr,
            retries=self.retry_var.get(),
            speed_limit=speed_limit,
            custom_filename=custom_filename if custom_filename else None
        )
        
        # 如果获取格式时使用了cookies,设置任务标记
        if self.format_fetch_used_cookies and url_type == 'youtube':
            task.needs_cookies = True
            self.manager.log("🍪 此任务将使用cookies下载")
        
        self.manager.add_task(task)
        
        self.url_entry.delete("1.0", "end")
        self.custom_filename_var.set("")
        self.filename_entry_widget.delete("1.0", "end")  # 清空重命名输入框
        self.format_combo.set('')
        self.format_combo['values'] = []  # 清空下拉列表选项
        self.url_type_label.config(text="")
        # 重置标记
        self.format_fetch_used_cookies = False

    def add_direct_task(self):
        """直接添加下载任务，不获取格式，使用yt-dlp默认参数"""
        url = self.url_entry.get("1.0", "end-1c").strip()
        if not url:
            SilentMessagebox.showwarning("提示", "请输入视频 URL")
            return
        
        # 自动检测URL类型
        url_type = detect_video_url_type(url)
        self.manager.log(f"URL: {url} (类型: {url_type}) [⚡ 直接下载模式]")
        
        # 获取自定义文件名
        custom_filename = self.custom_filename_var.get().strip()
        
        # 检查文件名是否包含非法字符
        if custom_filename:
            invalid_chars = r'\/:*?"<>|'
            if any(char in custom_filename for char in invalid_chars):
                self.manager.log(f"❌ 添加任务失败: 文件名包含非法字符 {invalid_chars}", "ERROR")
                SilentMessagebox.showerror("错误", f"文件名不能包含以下字符:\n{invalid_chars}")
                return
            self.manager.log(f"✓ 将使用自定义文件名: {custom_filename}")
        
        speed_limit = self.speedlimit_var.get()
        
        # 创建任务 - 不指定格式，使用yt-dlp默认best格式
        task = DownloadTask(
            url_type,
            url,
            self.shared_save_dir_var.get(),
            format=None,  # 不指定格式，使用默认
            retries=self.retry_var.get(),
            speed_limit=speed_limit,
            custom_filename=custom_filename if custom_filename else None
        )
        
        self.manager.add_task(task)
        
        self.url_entry.delete("1.0", "end")
        self.custom_filename_var.set("")
        self.filename_entry_widget.delete("1.0", "end")  # 清空重命名输入框

# ============ (重构) YouTube 输入框 ============
class YouTubeInputFrame(BaseInputFrame):
    def _create_widgets(self):
        tk.Label(self, text="YouTube URL:", font=(FONT_FAMILY, FONT_SIZE_TITLE)).pack(anchor='w')
        self.url_entry = tk.Entry(self, width=60)
        self.url_entry.pack(fill='x', pady=5)
        
        tk.Label(self, text="分辨率:", font=(FONT_FAMILY, FONT_SIZE_NORMAL)).pack(anchor='w')
        self.format_var_combo = tk.StringVar()
        self.format_combo = ttk.Combobox(self, textvariable=self.format_var_combo, state="readonly", width=57)
        self.format_combo.pack(fill='x', pady=5)
        
        # [修改3] 移除cookies复选框,只保留获取按钮
        action_frame = ttk.Frame(self)
        action_frame.pack(fill='x', pady=5)
        
        ttk.Button(
            action_frame,
            text="获取可用分辨率 / 格式",
            command=lambda: threading.Thread(target=self.fetch_formats, daemon=True).start()
        ).pack(side='left')
        
        subtitle_frame = ttk.Frame(self)
        subtitle_frame.pack(fill='x', pady=5)
        
        tk.Label(subtitle_frame, text="字幕:", font=(FONT_FAMILY, FONT_SIZE_NORMAL)).pack(side='left', padx=(0, 5))
        self.subtitle_var = tk.StringVar(value="none")
        ttk.Radiobutton(subtitle_frame, text="无", variable=self.subtitle_var, value="none").pack(side='left', padx=5)
        ttk.Radiobutton(subtitle_frame, text="英文", variable=self.subtitle_var, value="en").pack(side='left', padx=5)
        ttk.Radiobutton(subtitle_frame, text="中文", variable=self.subtitle_var, value="zh-CN").pack(side='left', padx=5)
        
        shortcut_frame = ttk.Frame(self)
        shortcut_frame.pack(fill='x', pady=5)
        
        tk.Label(shortcut_frame, text="快捷下载:", font=(FONT_FAMILY, FONT_SIZE_NORMAL)).pack(side='left', padx=(0, 5))        

        ttk.Button(shortcut_frame, text="📺 1080p", width=8,
                  command=lambda: self.add_task(preset_format=P1080_FMT)).pack(side='left', padx=5)
        ttk.Button(shortcut_frame, text="📺 720p", width=8,
                  command=lambda: self.add_task(preset_format=P720_FMT)).pack(side='left', padx=5)
        ttk.Button(shortcut_frame, text="🎵 仅音频",
                  command=lambda: self.add_task(preset_format=AUDIO_FMT)).pack(side='left', padx=5)
                          
        settings_frame = ttk.Frame(self)
        settings_frame.pack(fill='x', pady=5)
        
        self.retry_var = self._create_retry_spinbox(settings_frame)
        self.concurrent_var = self._create_concurrency_spinbox(settings_frame, self.manager)
        self.speedlimit_var = self._create_speedlimit_spinbox(settings_frame)
        
        self._create_common_buttons(self.add_task)
        
        # 用于标记获取格式时是否使用了cookies
        self.format_fetch_used_cookies = False

    def fetch_formats(self):
        """获取 YouTube 视频的可用格式 - 自动尝试cookies"""
        url = self.url_entry.get().strip()
        if not url:
            self.app.root.after(0, lambda: SilentMessagebox.showwarning("提示", "请输入 YouTube URL"))
            return
        
        self.manager.log("正在获取可用格式...")
        self.format_fetch_used_cookies = False  # 重置标记
        
        def run_fetch():
            try:
                # 第一次尝试:不使用cookies
                cmd = [yt_dlp_path, "--dump-single-json", "--no-warnings", url]
                self.manager.log("📡 尝试获取格式 (不使用cookies)...")
                
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60, startupinfo=startupinfo)
                
                # 如果失败,尝试使用cookies重试
                if proc.returncode != 0:
                    if os.path.exists(COOKIES_FILE_PATH):
                        self.manager.log("⚠️ 获取格式失败,尝试使用cookies重试...")
                        cmd_with_cookies = [yt_dlp_path, "--dump-single-json", "--no-warnings",
                                           "--cookies", COOKIES_FILE_PATH, url]
                        proc = subprocess.run(cmd_with_cookies, capture_output=True, text=True, 
                                            timeout=60, startupinfo=startupinfo)
                        if proc.returncode == 0:
                            self.format_fetch_used_cookies = True
                            self.manager.log("✓ 使用cookies成功获取格式")
                        else:
                            # 检测是否为cookies失效
                            if detect_cookies_error(proc.stderr):
                                self.manager.log("❌ Cookies可能已失效!", "ERROR")
                                self.manager.log("💡 建议: 重新导出cookies文件 (www.youtube.com_cookies.txt)", "ERROR")
                                self.app.root.after(0, self.app.notify_cookies_error)
                    else:
                        raise RuntimeError(f"获取失败且未找到cookies文件: {proc.stderr[:100]}")
                
                if proc.returncode != 0:
                    error_msg = proc.stderr if proc.stderr else proc.stdout
                    if detect_cookies_error(error_msg):
                        self.app.root.after(0, self.app.notify_cookies_error)
                        raise RuntimeError(f"获取格式失败 - Cookies可能已失效: {error_msg[:100]}")
                    else:
                        raise RuntimeError(f"获取格式失败 (退出码: {proc.returncode}): {error_msg[:100]}")
                
                info = json.loads(proc.stdout.strip())
                formats = []
                
                for f in info.get("formats", []):
                    height = f.get("height") or 0
                    ext = f.get("ext")
                    if f.get("vcodec") == "none" or height < 720: continue
                    if f.get('protocol', '').startswith('m3u8') or f.get('protocol', '').startswith('dash'): continue
                    
                    fps = f.get("fps") or 0
                    raw_vcodec = f.get("vcodec") or "未知"
                    vcodec_match = re.match(r'^(av01|avc1|vp09|vp9|hev1|h264)', raw_vcodec, re.IGNORECASE)
                    vcodec = vcodec_match.group(0) if vcodec_match else "未知"

                    # [修改] 过滤编码为"未知"的格式 (TikTok会员专享等)
                    if vcodec == "未知":
                        continue
                    
                    res_label = f"{height}p ({fps}fps)" if fps else f"{height}p"
                    fmt_line = f"{f.get('format_id')} - [{vcodec}] - {res_label} - {ext}"
                    formats.append(fmt_line)
                
                if not formats:
                    raise RuntimeError("未找到符合条件的格式")
                
                unique_formats = sorted(list(set(formats)), 
                                      key=lambda x: int(re.search(r'(\d+)p', x).group(1)), reverse=True)
                
                self.app.root.after(0, lambda: [
                    self.format_combo.configure(values=unique_formats),
                    self.format_var_combo.set(unique_formats[0]),
                    self.manager.log(f"✓ 获取到 {len(unique_formats)} 个格式")
                ])
            except Exception as e:
                self.app.root.after(0, lambda: self.manager.log(f"❌ 获取格式失败: {e}"))
        
        threading.Thread(target=run_fetch, daemon=True).start()

    def add_task(self, preset_format=None):
        url = self.url_entry.get().strip()
        if not url:
            SilentMessagebox.showwarning("提示", "请输入 YouTube URL")
            return
        
        self.manager.log(f"URL: {url}")
        
        if preset_format:
            fmt_expr = preset_format
        else:
            fmt_choice = self.format_var_combo.get().strip()
            if not fmt_choice:
                SilentMessagebox.showwarning("提示", "请先获取并选择格式")
                return
            format_id = fmt_choice.split(' - ')[0]
            fmt_expr = f"{format_id}+bestaudio[ext=m4a]"
        
        sub_lang = None if self.subtitle_var.get() == "none" else self.subtitle_var.get()
        speed_limit = self.speedlimit_var.get()
        
        task = DownloadTask(
            "youtube",
            url,
            self.shared_save_dir_var.get(),
            format=fmt_expr,
            sub_lang=sub_lang,
            retries=self.retry_var.get(),
            speed_limit=speed_limit
        )
        
        # 如果获取格式时使用了cookies,设置任务标记
        if self.format_fetch_used_cookies:
            task.needs_cookies = True
            self.manager.log("🍪 此任务将使用cookies下载")
        
        self.manager.add_task(task)
        
        self.url_entry.delete(0, tk.END)
        if not preset_format:
            self.format_combo.set('')
        # 重置标记
        self.format_fetch_used_cookies = False

# ============ (重构) Bilibili 输入框 ============
class BilibiliInputFrame(BaseInputFrame):
    def _create_widgets(self):
        tk.Label(self, text="Bilibili URL:", font=(FONT_FAMILY, FONT_SIZE_TITLE)).pack(anchor='w')
        self.url_entry = tk.Entry(self, width=60)
        self.url_entry.pack(fill='x', pady=5)
        
        tk.Label(self, text="分辨率:", font=(FONT_FAMILY, FONT_SIZE_NORMAL)).pack(anchor='w')
        self.format_var = tk.StringVar()
        self.format_combo = ttk.Combobox(self, textvariable=self.format_var, state="readonly", width=57)
        self.format_combo.pack(fill='x', pady=5)
        
        ttk.Button(self, text="获取可用分辨率 / 格式", command=self.fetch_formats).pack(pady=5)
        
        settings_frame = ttk.Frame(self)
        settings_frame.pack(fill='x', pady=5)
        
        self.retry_var = self._create_retry_spinbox(settings_frame)
        self.concurrent_var = self._create_concurrency_spinbox(settings_frame, self.manager)
        self.speedlimit_var = self._create_speedlimit_spinbox(settings_frame)
        
        self._create_common_buttons(self.add_task)

    def fetch_formats(self):
        url = self.url_entry.get().strip()
        if not url:
            SilentMessagebox.showwarning("提示", "请输入 Bilibili URL")
            return
        
        self.manager.log("正在获取可用格式...")
        
        def run_fetch():
            try:
                cmd = [yt_dlp_path, "--dump-single-json", "--no-warnings", url]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60, startupinfo=startupinfo)
                info = json.loads(proc.stdout.strip())
                
                formats = []
                for f in info.get("formats", []):
                    ext = f.get("ext")
                    if f.get("vcodec") == "none" or ext not in ["mp4", "m4a"]: continue
                    
                    height = f.get("height") or 0
                    if height < 720: continue
                    
                    fps = f.get("fps") or 0
                    raw_vcodec = f.get("vcodec") or "未知"
                    if not any(raw_vcodec.startswith(prefix) for prefix in ['av01', 'avc1', 'hev1', 'h.264']): continue
                    
                    vcodec_match = re.match(r'^(av01|avc1|hev1|h\.264)', raw_vcodec, re.IGNORECASE)
                    vcodec = vcodec_match.group(0) if vcodec_match else "未知"

                    # [修改] 过滤编码为"未知"的格式 (TikTok会员专享等)
                    if vcodec == "未知":
                        continue
                    
                    note = f.get("format_note") or ""
                    res_label = f"{height}p ({fps})" if fps and fps >= 50 else f"{height}p"
                    fmt_line = f"{f.get('format_id')} - [{vcodec}] - {res_label} - {note} - {ext}" if note else f"{f.get('format_id')} - [{vcodec}] - {res_label} - {ext}"
                    formats.append(fmt_line)
                
                unique_formats = sorted(list(set(formats)), 
                                      key=lambda x: int(re.search(r'(\d+)p', x).group(1)), reverse=True)
                
                if not unique_formats:
                    raise RuntimeError("未找到符合条件的格式")
                
                self.app.root.after(0, lambda: [
                    self.format_combo.configure(values=unique_formats),
                    self.format_var.set(unique_formats[0]),
                    self.manager.log(f"✓ 获取到 {len(unique_formats)} 个格式")
                ])
            except Exception as e:
                self.app.root.after(0, lambda: self.manager.log(f"❌ 获取格式失败: {e}"))
        
        threading.Thread(target=run_fetch, daemon=True).start()

    def add_task(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("提示", "请输入 Bilibili URL")
            return
        
        self.manager.log(f"URL: {url}")
        
        fmt = self.format_var.get().strip()
        if not fmt:
            messagebox.showwarning("提示", "请先获取并选择格式")
            return
        
        format_expr = f"{fmt.split(' - ')[0]}+bestaudio[ext=m4a]"
        speed_limit = self.speedlimit_var.get()
        
        task = DownloadTask(
            "bilibili",
            url,
            self.shared_save_dir_var.get(),
            format=format_expr,
            retries=self.retry_var.get(),
            speed_limit=speed_limit
        )
        
        self.manager.add_task(task)
        
        self.url_entry.delete(0, tk.END)
        self.format_combo.set('')

# ============ (重构) TikTok/通用 输入框 ============
class TikTokInputFrame(BaseInputFrame):
    def _create_widgets(self):
        tk.Label(self, text="TikTok/通用 URL:", font=(FONT_FAMILY, FONT_SIZE_TITLE)).pack(anchor='w')
        self.url_entry = tk.Entry(self, width=60)
        self.url_entry.pack(fill='x', pady=5)

        # [新增] 自定义文件名输入框
        filename_frame = ttk.Frame(self)
        filename_frame.pack(fill='x', pady=5)
        tk.Label(filename_frame, text="自定义文件名 (可选):", 
                font=(FONT_FAMILY, FONT_SIZE_NORMAL)).pack(side='left', padx=(0, 5))
        self.filename_var = tk.StringVar()
        filename_entry = tk.Entry(filename_frame, textvariable=self.filename_var, width=40)
        filename_entry.pack(side='left', fill='x', expand=True)
        tk.Label(filename_frame, text="(留空则自动从网页获取)", 
                font=(FONT_FAMILY, 8), foreground="gray").pack(side='left', padx=(5, 0))

        settings_frame = ttk.Frame(self)
        settings_frame.pack(fill='x', pady=5)

        self.retry_var = self._create_retry_spinbox(settings_frame)
        self.concurrent_var = self._create_concurrency_spinbox(settings_frame, self.manager)

        self._create_common_buttons(self.add_task)

    def add_task(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("提示", "请输入 TikTok URL")
            return

        self.manager.log(f"URL: {url}")

        # [新增] 获取自定义文件名(如果有)
        custom_filename = self.filename_var.get().strip()

        # 检查文件名是否包含非法字符
        if custom_filename:
            invalid_chars = r'\/:*?"<>|'
            if any(char in custom_filename for char in invalid_chars):
                self.manager.log(f"❌ 添加任务失败: 文件名包含非法字符 {invalid_chars}", "ERROR")
                messagebox.showerror("错误", f"文件名不能包含以下字符:\n{invalid_chars}")
                return
            self.manager.log(f"✓ 将使用自定义文件名: {custom_filename}")

        # [修改] 传递自定义文件名给任务
        task = DownloadTask(
            "tiktok",
            url,
            self.shared_save_dir_var.get(),
            retries=self.retry_var.get(),
            custom_filename=custom_filename if custom_filename else None
        )

        self.manager.add_task(task)
        self.url_entry.delete(0, tk.END)
        self.filename_var.set("")  # 清空文件名输入框

class M3U8InputFrame(BaseInputFrame):
    def _create_widgets(self):
        # [修改4] URL输入框改为2行高度 - 使用ttk.Label与其他标签页颜色一致
        ttk.Label(self, text="M3U8 URL:", font=(FONT_FAMILY, FONT_SIZE_TITLE, 'bold')).pack(anchor='w')
        self.url_var = tk.StringVar()
        # height=1 m3u8标签页M3U8 URL输入框高度
        url_text = tk.Text(self, height=2, width=60, wrap='word', font=(FONT_FAMILY, FONT_SIZE_NORMAL))
        url_text.pack(fill='x', pady=5)
        
        # 绑定Text控件到变量
        def update_url_var(*args):
            self.url_var.set(url_text.get("1.0", "end-1c"))
        url_text.bind("<KeyRelease>", update_url_var)
        self.url_text_widget = url_text
        
        # [修改4] 文件名输入框改为2行高度
        file_frame = ttk.Frame(self)
        file_frame.pack(fill='x', pady=5)
        
        tk.Label(file_frame, text="文件名 [必填]:", font=(FONT_FAMILY, FONT_SIZE_NORMAL), foreground="red").pack(side='left')
        self.filename_var = tk.StringVar(value="")
        # height=1 m3u8标签页文件名输入框高度
        filename_text = tk.Text(file_frame, height=2, width=50, wrap='word', font=(FONT_FAMILY, FONT_SIZE_NORMAL))
        filename_text.pack(side='left', padx=5, fill='x', expand=True)
        
        def update_filename_var(*args):
            self.filename_var.set(filename_text.get("1.0", "end-1c"))
        filename_text.bind("<KeyRelease>", update_filename_var)
        self.filename_text_widget = filename_text
        
        advanced_frame = ttk.Frame(self)
        advanced_frame.pack(fill='x', pady=5)
        
        tk.Label(advanced_frame, text="线  程  数:", font=(FONT_FAMILY, FONT_SIZE_NORMAL)).grid(row=0, column=0, sticky='w', pady=(5, 0))
        self.threads_var = tk.IntVar(value=10)
        ttk.Spinbox(advanced_frame, from_=1, to=128, textvariable=self.threads_var, width=10,
                   font=(FONT_FAMILY, FONT_SIZE_NORMAL)).grid(row=0, column=1, sticky='w', padx=5, pady=(5, 0))
        
        tk.Label(advanced_frame, text="重试:", font=(FONT_FAMILY, FONT_SIZE_NORMAL)).grid(row=0, column=2, sticky='w', padx=(10, 0), pady=(5, 0))
        self.retries_var = tk.IntVar(value=15)
        ttk.Spinbox(advanced_frame, from_=0, to=100, textvariable=self.retries_var, width=10,
                   font=(FONT_FAMILY, FONT_SIZE_NORMAL)).grid(row=0, column=3, sticky='w', padx=5, pady=(5, 0))
        
        self.concurrent_var = self._create_concurrency_spinbox(
            advanced_frame,
            self.manager,
            default_val=1, # 这里设置了m3u8默认并发数
            grid_row=0,
            grid_col_start=4,
            padx=(10, 0)
        )
        
        # [新增] 限速设置 (单位: MB/s, 0=不限速)
        tk.Label(advanced_frame, text="限速(M):", font=(FONT_FAMILY, FONT_SIZE_NORMAL)).grid(row=0, column=6, sticky='w', padx=(10, 0), pady=(5, 0))
        self.speed_limit_var = tk.IntVar(value=5)  # 0 = 不限速
        ttk.Spinbox(advanced_frame, from_=0, to=100, textvariable=self.speed_limit_var, width=8,
                   font=(FONT_FAMILY, FONT_SIZE_NORMAL)).grid(row=0, column=7, sticky='w', padx=5, pady=(5, 0))
        
        # [修改4] Headers和额外参数放在同一行,保持1行高度
        extra_frame = ttk.Frame(self)
        extra_frame.pack(fill='x', pady=5)
        
        tk.Label(extra_frame, text="Headers:", font=(FONT_FAMILY, FONT_SIZE_NORMAL)).pack(side='left', padx=(0, 5))
        self.headers_var = tk.StringVar()
        tk.Entry(extra_frame, textvariable=self.headers_var, width=30).pack(side='left', padx=5, fill='x', expand=True)
        
        tk.Label(extra_frame, text="额外参数:", font=(FONT_FAMILY, FONT_SIZE_NORMAL)).pack(side='left', padx=(10, 5))
        self.extra_args_var = tk.StringVar()
        tk.Entry(extra_frame, textvariable=self.extra_args_var, width=30).pack(side='left', padx=5, fill='x', expand=True)
        
        self._create_common_buttons(self.add_task)

    def add_task(self):
        url = self.url_var.get().strip()
        filename = self.filename_var.get().strip()
        
        if not url:
            self.manager.log("添加任务失败: 未填写 URL", "ERROR")
            return
        
        if not filename:
            self.manager.log("添加任务失败: 未填写文件名!", "ERROR")
            return
        
        invalid_chars = r'\/:*?"<>|'
        if any(char in filename for char in invalid_chars):
            self.manager.log(f"添加任务失败: 文件名包含非法字符 {invalid_chars}", "ERROR")
            return
        
        self.manager.log(f"URL: {url}")
        
        task = DownloadTask(
            "m3u8",
            url,
            self.shared_save_dir_var.get(),
            filename=filename,
            threads=self.threads_var.get(),
            retries=self.retries_var.get(),
            headers=self.headers_var.get().strip(),
            extra_args=self.extra_args_var.get().strip(),
            speed_limit=self.speed_limit_var.get()  # [新增] 限速
        )
        
        self.manager.add_task(task)
        
        # 清空输入框
        self.url_text_widget.delete("1.0", tk.END)
        self.filename_text_widget.delete("1.0", tk.END)
        self.headers_var.set("")
        self.extra_args_var.set("")

# ============ (重构) 启动器 ============
if __name__ == "__main__":
    root = tk.Tk()
    app = DownloadApplication(root)
    root.mainloop()
