# -*- coding: utf-8 -*-
"""
订单管理系统启动器 - Windows Dark Tech Style
提供可视化交互界面和实时日志显示
设计风格：深色科技美学 - 深色背景、渐变卡片、霓虹边框、科技感配色
"""

import os
import sys
import subprocess
import time
import webbrowser
import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox

if sys.platform == 'win32':
    CREATE_NO_WINDOW = 0x08000000
else:
    CREATE_NO_WINDOW = 0


def is_port_open(port):
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            return s.connect_ex(('localhost', port)) == 0
    except:
        return False


def is_service_healthy(url, timeout=2):
    """真正的 HTTP 健康检查，确保服务不仅端口通，而且能正常响应 HTTP 请求。"""
    import urllib.request
    import urllib.error
    try:
        req = urllib.request.Request(url, method='GET')
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.status == 200
    except Exception:
        return False


def kill_process_on_port(port):
    """Windows: kill ALL processes listening on the given port.
    Uses a single shell command string so the pipe is handled by cmd.exe."""
    if sys.platform == 'win32':
        try:
            cmd = f'for /f "tokens=5" %a in (\'netstat -ano ^| findstr /R ":{port}.*LISTENING"\') do @taskkill /F /T /PID %a >nul 2>&1'
            subprocess.run(cmd, shell=True, capture_output=True)
            return True
        except:
            pass
    else:
        try:
            cmd = f"lsof -ti:{port} | xargs kill -9 2>/dev/null"
            subprocess.run(cmd, shell=True, capture_output=True)
            return True
        except:
            pass
    return False


class WindowsLauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("订单管理系统")
        self.root.geometry("820x700")
        self.root.resizable(True, True)
        self.root.configure(bg='#0d1117')

        self.colors = {
            'bg':              '#0d1117',   # 主背景（深色）
            'bg_light':        '#161b22',   # 浅色背景
            'card':            '#1c2128',   # 卡片背景
            'card_border':     '#30363d',   # 卡片边框
            'card_border_glow': '#00d4ff',  # 卡片霓虹边框
            'text_primary':    '#e6edf3',   # 主文字
            'text_secondary':  '#8b949e',   # 辅助文字
            'text_tertiary':   '#484f58',   # 三级文字
            'blue':            '#58a6ff',   # 科技蓝
            'blue_light':      '#79c0ff',   # 蓝色悬停
            'blue_dark':       '#1f6feb',   # 蓝色按下
            'green':           '#3fb950',   # 成功绿
            'green_light':     '#56d364',   # 绿色悬停
            'green_dark':      '#238636',   # 绿色按下
            'red':             '#f85149',   # 危险红
            'red_light':       '#ff7b72',   # 红色悬停
            'red_dark':        '#da3633',   # 红色按下
            'orange':          '#d29922',   # 警告橙
            'yellow':          '#e3b341',   # 黄色
            'cyan':            '#56d4dd',   # 青色
            'purple':          '#a371f7',   # 紫色
            'progress_track':  '#30363d',   # 进度条轨道
            'progress_fill':   '#58a6ff',   # 进度条填充
            'log_bg':          '#010409',   # 终端日志背景
            'log_text':        '#c9d1d9',   # 终端日志文字
            'log_border':      '#21262d',   # 终端边框
            'divider':         '#30363d',   # 分割线
            'tab_active_bg':   '#21262d',   # 标签页激活背景
            'tab_active_border': '#58a6ff', # 标签页激活边框
            'tab_inactive_bg': '#161b22',   # 标签页非激活背景
            'tab_inactive_text': '#8b949e', # 标签页非激活文字
            'title_bar_bg':    '#161b22',   # 标题栏背景
            'title_bar_btn':   '#1c2128',   # 标题栏按钮背景
            'title_bar_btn_hover': '#30363d', # 标题栏按钮悬停
        }

        self.style = ttk.Style()
        self.style.theme_use('clam')

        self.backend_process = None
        self.frontend_process = None
        self.backend_log_thread = None
        self.frontend_log_thread = None

        # 日志队列：子线程只 queue.put，主线程轮询消费，彻底避免子线程触碰 Tkinter/Tcl 死锁
        self.log_queue = queue.Queue()
        self.root.after(300, self._poll_log_queue)

        self.backend_status = tk.StringVar(value="未启动")
        self.frontend_status = tk.StringVar(value="未启动")

        self.animation_running = True
        self.pulse_running = True

        self._progress_anim_id = None

        self._start_enabled = True
        self._stop_enabled = False
        self._open_enabled = False

        self.create_widgets()
        self.apply_styles()
        self.detect_service_status()
        self.start_animations()

    def detect_service_status(self):
        # 先用端口检测快速判断，再用 HTTP 健康检查精准验证
        backend_port_open = is_port_open(8000)
        frontend_port_open = is_port_open(5173)

        if backend_port_open:
            if is_service_healthy('http://localhost:8000/health'):
                self.backend_status.set("运行中")
                self.backend_indicator.config(text='●', foreground=self.colors['green'])
                self._update_progress(self.backend_progress_canvas, 180, self.colors['green'])
                self.add_log("检测到后端服务健康运行中", 'success')
            else:
                self.backend_status.set("异常-端口占用")
                self.backend_indicator.config(text='●', foreground=self.colors['orange'])
                self._update_progress(self.backend_progress_canvas, 100, self.colors['orange'])
                self.add_log("警告: 8000端口已占用但后端无响应，建议重启", 'warning')
        else:
            self.backend_status.set("未启动")
            self.backend_indicator.config(text='○', foreground=self.colors['text_tertiary'])
            self._update_progress(self.backend_progress_canvas, 0, self.colors['blue'])

        if frontend_port_open:
            if is_service_healthy('http://localhost:5173'):
                self.frontend_status.set("运行中")
                self.frontend_indicator.config(text='●', foreground=self.colors['green'])
                self._update_progress(self.frontend_progress_canvas, 180, self.colors['green'])
                self.add_log("检测到前端服务健康运行中", 'success')
            else:
                self.frontend_status.set("异常-端口占用")
                self.frontend_indicator.config(text='●', foreground=self.colors['orange'])
                self._update_progress(self.frontend_progress_canvas, 100, self.colors['orange'])
                self.add_log("警告: 5173端口已占用但前端无响应，建议重启", 'warning')
        else:
            self.frontend_status.set("未启动")
            self.frontend_indicator.config(text='○', foreground=self.colors['text_tertiary'])
            self._update_progress(self.frontend_progress_canvas, 0, self.colors['blue'])

        if backend_port_open or frontend_port_open:
            self._set_button_state(start='normal', stop='normal', open='normal')
        else:
            self._set_button_state(start='normal', stop='disabled', open='disabled')
        self.add_log("检测完成", 'system')

    def refresh_status(self):
        """手动刷新前后端运行状态 — 使用 HTTP 健康检查，精准判断服务是否可用"""
        self.add_log("正在刷新服务状态...", 'system')

        # ── 更新后端状态 ──
        backend_port_open = is_port_open(8000)
        if backend_port_open:
            if is_service_healthy('http://localhost:8000/health'):
                self.backend_status.set("运行中")
                self.backend_indicator.config(text='●', foreground=self.colors['green'])
                self._update_progress(self.backend_progress_canvas, 180, self.colors['green'])
                self.add_log("后端服务: 健康运行 (端口 8000)", 'success')
            else:
                self.backend_status.set("异常")
                self.backend_indicator.config(text='●', foreground=self.colors['orange'])
                self._update_progress(self.backend_progress_canvas, 100, self.colors['orange'])
                self.add_log("后端服务: 端口已占用但无响应，可能存在进程残留，请重启", 'warning')
        else:
            self.backend_status.set("未启动")
            self.backend_indicator.config(text='○', foreground=self.colors['text_tertiary'])
            self._update_progress(self.backend_progress_canvas, 0, self.colors['blue'])
            self.add_log("后端服务: 未启动 (端口 8000)", 'warning')

        # ── 更新前端状态 ──
        frontend_port_open = is_port_open(5173)
        if frontend_port_open:
            if is_service_healthy('http://localhost:5173'):
                self.frontend_status.set("运行中")
                self.frontend_indicator.config(text='●', foreground=self.colors['green'])
                self._update_progress(self.frontend_progress_canvas, 180, self.colors['green'])
                self.add_log("前端服务: 健康运行 (端口 5173)", 'success')
            else:
                self.frontend_status.set("异常")
                self.frontend_indicator.config(text='●', foreground=self.colors['orange'])
                self._update_progress(self.frontend_progress_canvas, 100, self.colors['orange'])
                self.add_log("前端服务: 端口已占用但无响应，可能存在进程残留，请重启", 'warning')
        else:
            self.frontend_status.set("未启动")
            self.frontend_indicator.config(text='○', foreground=self.colors['text_tertiary'])
            self._update_progress(self.frontend_progress_canvas, 0, self.colors['blue'])
            self.add_log("前端服务: 未启动 (端口 5173)", 'warning')

        # ── 更新按钮状态 ──
        if backend_port_open or frontend_port_open:
            self._set_button_state(start='normal', stop='normal', open='normal')
        else:
            self._set_button_state(start='normal', stop='disabled', open='disabled')

        self.add_log("状态刷新完成", 'system')

    def create_widgets(self):
        # ── Main Content ──
        main_frame = tk.Frame(self.root, bg=self.colors['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)

        # ═══════════════════════════════════════
        # Header Section
        # ═══════════════════════════════════════
        header_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        header_frame.pack(fill=tk.X, pady=(0, 16))

        header_left = tk.Frame(header_frame, bg=self.colors['bg'])
        header_left.pack(side=tk.LEFT)

        icon_canvas = tk.Canvas(
            header_left, width=48, height=48,
            bg=self.colors['bg'], highlightthickness=0
        )
        icon_canvas.pack(side=tk.LEFT, padx=(0, 12))
        icon_canvas.create_oval(2, 2, 46, 46, fill=self.colors['card'], outline=self.colors['cyan'], width=2)
        icon_canvas.create_text(24, 24, text="⚡", font=('Segoe UI Emoji', 22), fill=self.colors['cyan'])

        title_text_frame = tk.Frame(header_left, bg=self.colors['bg'])
        title_text_frame.pack(side=tk.LEFT)

        tk.Label(
            title_text_frame, text="订单管理系统",
            font=('微软雅黑', 22, 'bold'),
            bg=self.colors['bg'], fg=self.colors['text_primary'],
            anchor=tk.W
        ).pack(anchor=tk.W)

        tk.Label(
            title_text_frame, text="Order Management System Launcher",
            font=('Segoe UI', 10),
            bg=self.colors['bg'], fg=self.colors['text_tertiary'],
            anchor=tk.W
        ).pack(anchor=tk.W)

        # ═══════════════════════════════════════
        # Status Cards
        # ═══════════════════════════════════════
        status_card = self._create_card(main_frame, "系统状态")

        status_container = tk.Frame(status_card, bg=self.colors['card'])
        status_container.pack(fill=tk.X, padx=16, pady=(0, 5))

        # ── Backend Row ──
        backend_row = tk.Frame(status_container, bg=self.colors['card'])
        backend_row.pack(fill=tk.X, pady=(10, 6))

        backend_icon_canvas = tk.Canvas(
            backend_row, width=36, height=36,
            bg=self.colors['card'], highlightthickness=0
        )
        backend_icon_canvas.pack(side=tk.LEFT, padx=(0, 12))
        backend_icon_canvas.create_oval(2, 2, 34, 34, fill='#1a2744', outline='#58a6ff', width=1)
        backend_icon_canvas.create_text(18, 18, text="⚙", font=('Segoe UI Emoji', 14), fill=self.colors['blue'])

        backend_info = tk.Frame(backend_row, bg=self.colors['card'])
        backend_info.pack(side=tk.LEFT)

        tk.Label(
            backend_info, text="后端服务",
            font=('微软雅黑', 12, 'bold'),
            bg=self.colors['card'], fg=self.colors['text_primary']
        ).pack(anchor=tk.W)

        backend_status_label = tk.Label(
            backend_info, textvariable=self.backend_status,
            font=('Segoe UI', 10),
            bg=self.colors['card'], fg=self.colors['text_secondary']
        )
        backend_status_label.pack(anchor=tk.W)

        backend_right = tk.Frame(backend_row, bg=self.colors['card'])
        backend_right.pack(side=tk.RIGHT)

        self.backend_progress_canvas = tk.Canvas(
            backend_right, width=180, height=6,
            bg=self.colors['card'], highlightthickness=0
        )
        self.backend_progress_canvas.pack(side=tk.RIGHT, padx=(10, 0))
        self._draw_progress_track(self.backend_progress_canvas, 180, 6)
        self._update_progress(self.backend_progress_canvas, 0, self.colors['blue'])

        self.backend_indicator = tk.Label(
            backend_right, text='○',
            font=('Segoe UI', 12),
            bg=self.colors['card'], fg=self.colors['text_tertiary']
        )
        self.backend_indicator.pack(side=tk.RIGHT)

        divider = tk.Frame(status_container, bg=self.colors['divider'], height=1)
        divider.pack(fill=tk.X, pady=4)

        # ── Frontend Row ──
        frontend_row = tk.Frame(status_container, bg=self.colors['card'])
        frontend_row.pack(fill=tk.X, pady=(6, 10))

        frontend_icon_canvas = tk.Canvas(
            frontend_row, width=36, height=36,
            bg=self.colors['card'], highlightthickness=0
        )
        frontend_icon_canvas.pack(side=tk.LEFT, padx=(0, 12))
        frontend_icon_canvas.create_oval(2, 2, 34, 34, fill='#1a272e', outline='#3fb950', width=1)
        frontend_icon_canvas.create_text(18, 18, text="◈", font=('Segoe UI', 12, 'bold'), fill=self.colors['green'])

        frontend_info = tk.Frame(frontend_row, bg=self.colors['card'])
        frontend_info.pack(side=tk.LEFT)

        tk.Label(
            frontend_info, text="前端服务",
            font=('微软雅黑', 12, 'bold'),
            bg=self.colors['card'], fg=self.colors['text_primary']
        ).pack(anchor=tk.W)

        frontend_status_label = tk.Label(
            frontend_info, textvariable=self.frontend_status,
            font=('Segoe UI', 10),
            bg=self.colors['card'], fg=self.colors['text_secondary']
        )
        frontend_status_label.pack(anchor=tk.W)

        frontend_right = tk.Frame(frontend_row, bg=self.colors['card'])
        frontend_right.pack(side=tk.RIGHT)

        self.frontend_progress_canvas = tk.Canvas(
            frontend_right, width=180, height=6,
            bg=self.colors['card'], highlightthickness=0
        )
        self.frontend_progress_canvas.pack(side=tk.RIGHT, padx=(10, 0))
        self._draw_progress_track(self.frontend_progress_canvas, 180, 6)
        self._update_progress(self.frontend_progress_canvas, 0, self.colors['blue'])

        self.frontend_indicator = tk.Label(
            frontend_right, text='○',
            font=('Segoe UI', 12),
            bg=self.colors['card'], fg=self.colors['text_tertiary']
        )
        self.frontend_indicator.pack(side=tk.RIGHT)

        # ═══════════════════════════════════════
        # Action Buttons
        # ═══════════════════════════════════════
        button_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        button_frame.pack(fill=tk.X, pady=14)

        button_container = tk.Frame(button_frame, bg=self.colors['bg'])
        button_container.pack(anchor=tk.CENTER)

        self.start_btn = tk.Canvas(
            button_container, width=150, height=40,
            bg=self.colors['green'], highlightthickness=0, cursor='hand2'
        )
        self.start_btn.pack(side=tk.LEFT, padx=8)
        self._draw_rounded_btn(self.start_btn, 150, 40, self.colors['green'])
        self.start_btn.create_text(
            75, 20, text="启动系统",
            font=('微软雅黑', 11, 'bold'), fill='white'
        )
        self.start_btn.bind('<Button-1>', lambda e: self.start_services() if self._start_enabled else None)
        self.start_btn.bind('<Enter>', lambda e: self._hover_btn(self.start_btn, 150, 40, self.colors['green_light']) if self._start_enabled else None)
        self.start_btn.bind('<Leave>', lambda e: self._hover_btn(self.start_btn, 150, 40, self.colors['green']) if self._start_enabled else None)

        self.stop_btn = tk.Canvas(
            button_container, width=150, height=40,
            bg='#30363d', highlightthickness=0, cursor='hand2'
        )
        self.stop_btn.pack(side=tk.LEFT, padx=8)
        self._draw_rounded_btn(self.stop_btn, 150, 40, '#30363d')
        self.stop_btn.create_text(
            75, 20, text="停止系统",
            font=('微软雅黑', 11, 'bold'), fill='#484f58', tags='btn_text'
        )
        self.stop_btn.bind('<Button-1>', lambda e: self.stop_services() if self._stop_enabled else None)
        self.stop_btn.bind('<Enter>', lambda e: self._hover_btn(self.stop_btn, 150, 40, self.colors['red_light']) if self._stop_enabled else None)
        self.stop_btn.bind('<Leave>', lambda e: self._hover_btn(self.stop_btn, 150, 40, self.colors['red']) if self._stop_enabled else None)

        self.open_btn = tk.Canvas(
            button_container, width=150, height=40,
            bg='#30363d', highlightthickness=0, cursor='hand2'
        )
        self.open_btn.pack(side=tk.LEFT, padx=8)
        self._draw_rounded_btn(self.open_btn, 150, 40, '#30363d')
        self.open_btn.create_text(
            75, 20, text="打开页面",
            font=('微软雅黑', 11, 'bold'), fill='#484f58', tags='btn_text'
        )
        self.open_btn.bind('<Button-1>', lambda e: self.open_browser() if self._open_enabled else None)
        self.open_btn.bind('<Enter>', lambda e: self._hover_btn(self.open_btn, 150, 40, self.colors['blue_light']) if self._open_enabled else None)
        self.open_btn.bind('<Leave>', lambda e: self._hover_btn(self.open_btn, 150, 40, self.colors['blue']) if self._open_enabled else None)

        # ── Refresh Button ──
        self.refresh_btn = tk.Canvas(
            button_container, width=150, height=40,
            bg=self.colors['purple'], highlightthickness=0, cursor='hand2'
        )
        self.refresh_btn.pack(side=tk.LEFT, padx=8)
        self._draw_rounded_btn(self.refresh_btn, 150, 40, self.colors['purple'])
        self.refresh_btn.create_text(
            75, 20, text="刷新状态",
            font=('微软雅黑', 11, 'bold'), fill='white'
        )
        self.refresh_btn.bind('<Button-1>', lambda e: self.refresh_status())
        self.refresh_btn.bind('<Enter>', lambda e: self._hover_btn(self.refresh_btn, 150, 40, '#bc8cff'))
        self.refresh_btn.bind('<Leave>', lambda e: self._hover_btn(self.refresh_btn, 150, 40, self.colors['purple']))

        # ═══════════════════════════════════════
        # Log Panel
        # ═══════════════════════════════════════
        self.log_card = self._create_card(main_frame, "实时日志", expand=True)

        tab_frame = tk.Frame(self.log_card, bg=self.colors['card'])
        tab_frame.pack(fill=tk.X, padx=16, pady=(10, 6))

        self.tabs = []
        tab_configs = [
            ('综合日志', 'all'),
            ('后端日志', 'backend'),
            ('前端日志', 'frontend'),
        ]

        self.tab_buttons = []
        for i, (tab_text, tab_id) in enumerate(tab_configs):
            btn = tk.Label(
                tab_frame, text=tab_text,
                font=('微软雅黑', 10),
                bg=self.colors['tab_active_bg'] if i == 0 else self.colors['tab_inactive_bg'],
                fg=self.colors['text_primary'] if i == 0 else self.colors['tab_inactive_text'],
                padx=16, pady=5, cursor='hand2'
            )
            btn.pack(side=tk.LEFT, padx=(0, 6))
            btn.bind('<Button-1>', lambda e, idx=i: self._switch_tab(idx))
            self.tab_buttons.append(btn)

        log_container = tk.Frame(self.log_card, bg=self.colors['log_bg'], highlightthickness=0)
        log_container.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))

        self.log_text_container = tk.Frame(log_container, bg=self.colors['log_bg'])
        self.log_text_container.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        self.all_log_text = tk.Text(
            self.log_text_container, height=16, state=tk.DISABLED,
            font=('Cascadia Code', 9) if sys.platform == 'win32' else ('Menlo', 10),
            wrap=tk.WORD, bg=self.colors['log_bg'], fg=self.colors['log_text'],
            insertbackground=self.colors['blue'],
            selectbackground='#264f78', selectforeground='white',
            highlightthickness=0, relief=tk.FLAT,
            padx=10, pady=8, spacing1=2
        )
        self.all_log_text.pack(fill=tk.BOTH, expand=True)

        self.backend_log_text = tk.Text(
            self.log_text_container, height=16, state=tk.DISABLED,
            font=('Cascadia Code', 9) if sys.platform == 'win32' else ('Menlo', 10),
            wrap=tk.WORD, bg=self.colors['log_bg'], fg=self.colors['log_text'],
            highlightthickness=0, relief=tk.FLAT,
            padx=10, pady=8, spacing1=2
        )

        self.frontend_log_text = tk.Text(
            self.log_text_container, height=16, state=tk.DISABLED,
            font=('Cascadia Code', 9) if sys.platform == 'win32' else ('Menlo', 10),
            wrap=tk.WORD, bg=self.colors['log_bg'], fg=self.colors['log_text'],
            highlightthickness=0, relief=tk.FLAT,
            padx=10, pady=8, spacing1=2
        )

        scrollbar_frame = tk.Frame(log_container, bg=self.colors['log_bg'], width=12)
        scrollbar_frame.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_frame.pack_propagate(False)

        self.log_scrollbar = ttk.Scrollbar(
            scrollbar_frame, orient=tk.VERTICAL,
            command=self.all_log_text.yview,
            style='DarkScrollbar.Vertical.TScrollbar'
        )
        self.log_scrollbar.pack(fill=tk.Y, expand=True)
        self.all_log_text.configure(yscrollcommand=self.log_scrollbar.set)

        self.active_tab = 0
        self.tab_text_widgets = [self.all_log_text, self.backend_log_text, self.frontend_log_text]

        log_tags = {
            'system':  self.colors['text_tertiary'],
            'backend': '#58a6ff',
            'frontend': '#3fb950',
            'error':   '#f85149',
            'success': '#3fb950',
            'warning': '#d29922',
            'info':    '#58a6ff',
        }
        for tw in self.tab_text_widgets:
            for tag, color in log_tags.items():
                tw.tag_config(tag, foreground=color)

        # ═══════════════════════════════════════
        # Info Bar
        # ═══════════════════════════════════════
        info_card = self._create_card(main_frame, None)

        info_grid = tk.Frame(info_card, bg=self.colors['card'])
        info_grid.pack(fill=tk.X, padx=16, pady=10)

        info_items = [
            ('前端地址', 'http://localhost:5173'),
            ('后端 API', 'http://localhost:8000'),
            ('默认账号', '1001'),
            ('默认密码', '1001'),
        ]

        for label, value in info_items:
            row = tk.Frame(info_grid, bg=self.colors['card'])
            row.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 20))

            tk.Label(
                row, text=label,
                font=('微软雅黑', 9),
                bg=self.colors['card'], fg=self.colors['text_tertiary']
            ).pack(side=tk.LEFT, padx=(0, 6))

            tk.Label(
                row, text=value,
                font=('Cascadia Code', 9) if sys.platform == 'win32' else ('Menlo', 9),
                bg=self.colors['card'], fg=self.colors['text_primary']
            ).pack(side=tk.LEFT)

    def _create_card(self, parent, title=None, expand=False):
        outer = tk.Frame(parent, bg=self.colors['bg'])
        if expand:
            outer.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        else:
            outer.pack(fill=tk.X, pady=(0, 10))

        card = tk.Canvas(
            outer, bg=self.colors['card'], highlightthickness=0
        )
        if expand:
            card.pack(fill=tk.BOTH, expand=True)
        else:
            card.pack(fill=tk.X)

        def _on_card_configure(event):
            card.delete('bg')
            r = 8
            w, h = event.width, event.height
            self._draw_rounded_rect(card, 0, 0, w, h, r, fill=self.colors['card'], outline=self.colors['card_border'], width=1, tags='bg')

        card.bind('<Configure>', _on_card_configure)

        if title:
            title_label = tk.Label(
                card, text=title,
                font=('微软雅黑', 11, 'bold'),
                bg=self.colors['card'], fg=self.colors['text_primary'],
                anchor=tk.W
            )
            title_label.pack(fill=tk.X, padx=16, pady=(12, 0))

        return card

    def _draw_rounded_rect(self, canvas, x1, y1, x2, y2, r, **kwargs):
        points = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1,
        ]
        return canvas.create_polygon(points, smooth=True, **kwargs)

    def _draw_rounded_btn(self, canvas, w, h, color, r=20):
        canvas.delete('btn_bg')
        self._draw_rounded_rect(canvas, 0, 0, w, h, r, fill=color, outline='', tags='btn_bg')
        canvas.tag_lower('btn_bg')

    def _draw_progress_track(self, canvas, w, h, r=3):
        self._draw_rounded_rect(canvas, 0, 0, w, h, r, fill=self.colors['progress_track'], outline='')

    def _update_progress(self, canvas, width, color):
        max_w = 180
        width = max(0, min(width, max_w))
        canvas.delete('progress_fill')
        if width > 0:
            self._draw_rounded_rect(canvas, 0, 0, width, 6, 3, fill=color, outline='', tags='progress_fill')

    def _hover_btn(self, canvas, w, h, color):
        self._draw_rounded_btn(canvas, w, h, color)

    def _set_button_state(self, start='normal', stop='disabled', open='disabled'):
        """Update button visual state WITHOUT using tk.DISABLED (which applies gray stipple mask)."""
        # ── Start button ──
        if start == 'disabled':
            self._draw_rounded_btn(self.start_btn, 150, 40, '#30363d')
            self.start_btn.delete('btn_text')
            self.start_btn.create_text(75, 20, text="启动系统", font=('微软雅黑', 11, 'bold'), fill='#484f58', tags='btn_text')
            self._start_enabled = False
            self.start_btn.config(cursor='arrow')
        else:
            self._draw_rounded_btn(self.start_btn, 150, 40, self.colors['green'])
            self.start_btn.delete('btn_text')
            self.start_btn.create_text(75, 20, text="启动系统", font=('微软雅黑', 11, 'bold'), fill='white', tags='btn_text')
            self._start_enabled = True
            self.start_btn.config(cursor='hand2')

        # ── Stop button ──
        if stop == 'disabled':
            self._draw_rounded_btn(self.stop_btn, 150, 40, '#30363d')
            self.stop_btn.delete('btn_text')
            self.stop_btn.create_text(75, 20, text="停止系统", font=('微软雅黑', 11, 'bold'), fill='#484f58', tags='btn_text')
            self._stop_enabled = False
            self.stop_btn.config(cursor='arrow')
        else:
            self._draw_rounded_btn(self.stop_btn, 150, 40, self.colors['red'])
            self.stop_btn.delete('btn_text')
            self.stop_btn.create_text(75, 20, text="停止系统", font=('微软雅黑', 11, 'bold'), fill='white', tags='btn_text')
            self._stop_enabled = True
            self.stop_btn.config(cursor='hand2')

        # ── Open button ──
        if open == 'disabled':
            self._draw_rounded_btn(self.open_btn, 150, 40, '#30363d')
            self.open_btn.delete('btn_text')
            self.open_btn.create_text(75, 20, text="打开页面", font=('微软雅黑', 11, 'bold'), fill='#484f58', tags='btn_text')
            self._open_enabled = False
            self.open_btn.config(cursor='arrow')
        else:
            self._draw_rounded_btn(self.open_btn, 150, 40, self.colors['blue'])
            self.open_btn.delete('btn_text')
            self.open_btn.create_text(75, 20, text="打开页面", font=('微软雅黑', 11, 'bold'), fill='white', tags='btn_text')
            self._open_enabled = True
            self.open_btn.config(cursor='hand2')

    def _switch_tab(self, index):
        if index == self.active_tab:
            return

        for i, btn in enumerate(self.tab_buttons):
            if i == index:
                btn.config(bg=self.colors['tab_active_bg'], fg=self.colors['text_primary'])
            else:
                btn.config(bg=self.colors['tab_inactive_bg'], fg=self.colors['tab_inactive_text'])

        for i, tw in enumerate(self.tab_text_widgets):
            if i == index:
                tw.pack(fill=tk.BOTH, expand=True)
                self.log_scrollbar.config(command=tw.yview)
                tw.configure(yscrollcommand=self.log_scrollbar.set)
            else:
                tw.pack_forget()

        self.active_tab = index

    def start_animations(self):
        self.pulse_animation()

    def pulse_animation(self):
        if not self.pulse_running:
            return

        try:
            for state_var, indicator in [
                (self.backend_status, self.backend_indicator),
                (self.frontend_status, self.frontend_indicator)
            ]:
                if state_var.get() == "运行中":
                    current_fg = indicator.cget('foreground')
                    if current_fg == self.colors['green']:
                        indicator.config(foreground=self.colors['green_light'])
                    else:
                        indicator.config(foreground=self.colors['green'])
                elif state_var.get() == "启动中...":
                    current_fg = indicator.cget('foreground')
                    if current_fg == self.colors['blue']:
                        indicator.config(foreground=self.colors['blue_light'])
                    else:
                        indicator.config(foreground=self.colors['blue'])
        except:
            pass

        self.root.after(800, self.pulse_animation)

    def apply_styles(self):
        c = self.colors

        self.style.element_create('Dark.Scrollbar.trough', 'from', 'clam')
        self.style.element_create('Dark.Scrollbar.thumb', 'from', 'clam')
        self.style.layout('DarkScrollbar.Vertical.TScrollbar',
            [('Dark.Scrollbar.trough', {'sticky': 'ns', 'children':
                [('Dark.Scrollbar.thumb', {'expand': '1', 'sticky': 'nswe'})]})])
        self.style.configure('DarkScrollbar.Vertical.TScrollbar',
            background=c['log_border'], troughcolor=c['log_bg'],
            bordercolor=c['log_bg'], darkcolor=c['log_border'],
            lightcolor=c['log_border'], borderwidth=0, arrowsize=0)
        self.style.map('DarkScrollbar.Vertical.TScrollbar',
            background=[('active', '#30363d')],
            darkcolor=[('active', '#30363d')],
            lightcolor=[('active', '#30363d')])

    def add_log(self, text, source='system', level='info'):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

        tag = source if source in ('system', 'backend', 'frontend', 'error', 'success', 'warning') else 'info'

        log_line = f"[{timestamp}] [{tag.upper()}] {text}\n"

        self.all_log_text.config(state=tk.NORMAL)
        self.all_log_text.insert(tk.END, log_line, tag)
        self.all_log_text.config(state=tk.DISABLED)
        self.all_log_text.see(tk.END)

        if source == 'backend':
            tw = self.backend_log_text
        elif source == 'frontend':
            tw = self.frontend_log_text
        else:
            tw = None

        if tw:
            tw.config(state=tk.NORMAL)
            tw.insert(tk.END, log_line, tag)
            tw.config(state=tk.DISABLED)
            tw.see(tk.END)

    def add_backend_log(self, text, level='info'):
        self.add_log(text, 'backend')

    def add_frontend_log(self, text, level='info'):
        self.add_log(text, 'frontend')

    def read_process_output(self, process, source):
        """线程安全地读取子进程管道。

        ⚠️ 关键：子线程**绝不能直接调用任何 Tkinter 方法**（包括 self.root.after）。
        Tkinter/Tcl 解释器不是线程安全的，子线程调用 after() 会与主线程竞争 Tcl 锁，
        导致读线程死锁、停止 drain 管道，进而后端写 stdout 被阻塞、整个事件循环挂起
        （表现为“后端端口在监听但所有请求超时”）。

        本方法只负责把日志放入线程安全的 queue，所有 Tkinter 更新交由主线程的
        _poll_log_queue 完成。
        """
        try:
            while process.poll() is None:
                line = process.stdout.readline()
                if line:
                    decoded = line.decode('utf-8', errors='ignore').strip()
                    if decoded:
                        self.log_queue.put((source, decoded))

                line = process.stderr.readline()
                if line:
                    decoded = line.decode('utf-8', errors='ignore').strip()
                    if decoded:
                        self.log_queue.put((source + '_err', decoded))
        except Exception:
            pass

    def _poll_log_queue(self):
        """主线程定时轮询日志队列，消费并写入对应日志区。

        仅主线程操作 Tkinter，绝对安全。每 300ms 递归调度一次。
        """
        try:
            while True:
                source, text = self.log_queue.get_nowait()
                if source == 'backend':
                    self.add_backend_log(text)
                elif source == 'backend_err':
                    self.add_backend_log(text, 'error')
                elif source == 'frontend':
                    self.add_frontend_log(text)
                elif source == 'frontend_err':
                    self.add_frontend_log(text, 'error')
                else:
                    self.add_backend_log(text)
        except queue.Empty:
            pass
        finally:
            self.root.after(300, self._poll_log_queue)

    def check_python_version(self):
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 10):
            self.add_log(f"Python版本要求3.10+，当前版本{version.major}.{version.minor}", 'error')
            return False
        self.add_log(f"Python版本: {version.major}.{version.minor}.{version.micro}", 'success')
        return True

    def install_backend_deps(self):
        backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
        requirements_file = os.path.join(backend_dir, 'requirements.txt')

        if not os.path.exists(requirements_file):
            self.add_log("requirements.txt 不存在", 'error')
            return False

        # 检查所有关键运行时依赖，而不仅仅是 fastapi
        REQUIRED_DEPS = [
            ('fastapi', 'FastAPI 框架'),
            ('uvicorn', 'ASGI 服务器'),
            ('sqlalchemy', 'ORM 数据库'),
            ('aiosqlite', '异步 SQLite 驱动'),
            ('jose', 'JWT 令牌处理'),
            ('passlib', '密码哈希库'),
            ('multipart', '多部分表单解析 (OAuth2 登录必需)'),
            ('pydantic', '数据验证'),
        ]

        missing = []
        for module, desc in REQUIRED_DEPS:
            try:
                __import__(module)
            except ImportError:
                missing.append(f'{desc} ({module})')

        if not missing:
            self.add_log(f"后端依赖已安装 (全部 {len(REQUIRED_DEPS)} 项检查通过)", 'success')
            return True

        self.add_log(f"检测到 {len(missing)} 项依赖缺失:", 'warning')
        for m in missing:
            self.add_log(f"  - {m}", 'warning')

        self.add_log("正在安装后端依赖...", 'system')
        self.add_log(f"pip install -r requirements.txt (使用清华镜像加速)", 'system')
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt', '-i', 'https://pypi.tuna.tsinghua.edu.cn/simple'],
            cwd=backend_dir,
            capture_output=True, text=True,
            timeout=300  # 5 分钟超时
        )
        if result.returncode != 0:
            self.add_log("后端依赖安装失败", 'error')
            self.add_log(result.stderr[-500:] if len(result.stderr) > 500 else result.stderr, 'error')
            return False
        self.add_log("后端依赖安装完成", 'success')
        return True

    def install_frontend_deps(self):
        frontend_dir = os.path.join(os.path.dirname(__file__), 'frontend')
        node_modules_dir = os.path.join(frontend_dir, 'node_modules')

        if os.path.exists(node_modules_dir):
            self.add_log("前端依赖已安装", 'success')
            return True

        self.add_log("正在安装前端依赖...")
        result = subprocess.run(['cmd', '/c', 'npm', 'install'], capture_output=True, text=True, cwd=frontend_dir)
        if result.returncode != 0:
            self.add_log("前端依赖安装失败", 'error')
            self.add_log(result.stderr, 'error')
            return False
        self.add_log("前端依赖安装完成", 'success')
        return True

    def ensure_directories(self):
        backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
        data_dir = os.path.join(backend_dir, 'data')
        
        dirs_to_create = [
            (os.path.join(data_dir, 'db'), '数据库目录'),
            (os.path.join(data_dir, 'images'), '图片存储目录'),
            (os.path.join(data_dir, 'images', 'temp'), '临时图片目录'),
            (os.path.join(data_dir, 'images', 'official'), '正式图片目录'),
            (os.path.join(data_dir, 'logs'), '日志目录'),
            (os.path.join(data_dir, 'backup'), '备份目录'),
            (os.path.join(data_dir, 'qr_codes'), '二维码缓存目录'),
        ]
        
        created_count = 0
        for dir_path, dir_name in dirs_to_create:
            if not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path, exist_ok=True)
                    self.add_log(f"创建目录: {dir_name}", 'success')
                    created_count += 1
                except Exception as e:
                    self.add_log(f"创建目录失败 {dir_name}: {str(e)}", 'error')
                    return False
        
        if created_count == 0:
            self.add_log("所有目录已存在", 'success')
        
        return True

    def check_database(self):
        backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
        db_dir = os.path.join(backend_dir, 'data', 'db')
        db_path = os.path.join(db_dir, 'order_system.db')

        if os.path.exists(db_path):
            db_size = os.path.getsize(db_path) / 1024
            self.add_log(f"数据库已存在 ({db_size:.1f} KB)", 'success')
        else:
            self.add_log("警告: 数据库文件不存在!", 'warning')
            self.add_log("请先运行 '数据库初始化.py' 创建数据库", 'warning')
            self.add_log("运行方式: python 数据库初始化.py --force", 'warning')

    def wait_for_port(self, port, timeout=60):
        import socket
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    if s.connect_ex(('localhost', port)) == 0:
                        return True
            except:
                pass
            elapsed = time.time() - start_time
            progress = min(180, int(elapsed / timeout * 180))
            if port == 8000:
                self._update_progress(self.backend_progress_canvas, progress, self.colors['blue'])
            else:
                self._update_progress(self.frontend_progress_canvas, progress, self.colors['blue'])
            time.sleep(0.5)
        return False

    def _is_alive(self, proc):
        """判断本启动器 Popen 子进程是否仍在运行。"""
        if not proc:
            return False
        try:
            return proc.poll() is None
        except Exception:
            return False

    def kill_own_process(self, proc):
        """只终止本启动器自己 Popen 拉起的子进程及其子树，绝不误伤外部进程。"""
        if not proc:
            return
        try:
            pid = proc.pid
            if sys.platform == 'win32':
                subprocess.run(f'taskkill /F /T /PID {pid} >nul 2>&1', shell=True, capture_output=True)
            else:
                import os as _os, signal as _sig
                try:
                    _os.kill(pid, _sig.SIGTERM)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            proc.wait(timeout=3)
        except Exception:
            pass

    def _start_backend(self):
        """启动后端 uvicorn 进程并启动其日志读取线程（线程安全，读线程只负责 drain 管道）。"""
        backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
        proc = subprocess.Popen(
            [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000'],
            cwd=backend_dir,
            creationflags=CREATE_NO_WINDOW,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        t = threading.Thread(
            target=self.read_process_output,
            args=(proc, 'backend'),
            daemon=True
        )
        t.start()
        return proc

    def _health_watchdog(self):
        """自愈看门狗：周期性检查后端存活。

        关键原则（避免“刷新即误杀”）：
        - 仅当 8000 端口【彻底不通（连接被拒绝）】时才判定后端已死并重启——
          这是“进程真的挂了”的明确信号。
        - 若端口仍在监听，但 /health 偶发超时（如用户狂刷页面导致后端短暂繁忙），
          只记录告警、绝不重启。后端只是“忙”，并非“死”。
        - 仅当端口在监听、且 /health 连续失败约 3 分钟（12 次 × 15s，且每次 8s 超时）
          才视为真死锁，此时才重启本启动器管理的后端。
        """
        import time as _time
        fail_count = 0
        # 连续多少次 /health 超时（端口仍监听）才判定为真死锁
        DEADLOCK_THRESHOLD = 12
        while True:
            _time.sleep(15)
            try:
                if not is_port_open(8000):
                    # 端口彻底不通 = 后端进程已退出 → 明确需要重启
                    self.log_queue.put(('backend', "看门狗：8000 端口未监听，正在自动重启后端"))
                    self.backend_process = self._start_backend()
                    fail_count = 0
                    continue
                # 端口在监听：给足超时，区分“忙”与“死”
                if is_service_healthy('http://localhost:8000/health', timeout=8):
                    fail_count = 0
                else:
                    fail_count += 1
                    self.log_queue.put(('backend', f"看门狗：/health 超时（后端繁忙？{fail_count}/{DEADLOCK_THRESHOLD}），仅观察不重启"))
                    if fail_count >= DEADLOCK_THRESHOLD:
                        # 连续长时间无响应 + 端口仍在监听 = 真死锁，才重启本启动器管理的进程
                        if self._is_alive(self.backend_process):
                            self.log_queue.put(('backend_err', "看门狗：后端疑似死锁（连续超时约 3 分钟），正在重启"))
                            self.kill_own_process(self.backend_process)
                            _time.sleep(2)
                            self.backend_process = self._start_backend()
                        else:
                            self.log_queue.put(('backend_err', "看门狗：8000 端口进程非本启动器管理，跳过自动重启（请手动处理）"))
                        fail_count = 0
            except Exception as e:
                self.log_queue.put(('backend_err', f"看门狗异常: {e}"))

    def start_services(self):
        self._set_button_state(start='disabled')
        self._update_progress(self.backend_progress_canvas, 0, self.colors['blue'])
        self._update_progress(self.frontend_progress_canvas, 0, self.colors['blue'])
        self.add_log("开始启动系统...", 'system')

        def run_start():
            if not self.check_python_version():
                self._set_button_state(start='normal')
                return

            if not self.install_backend_deps():
                self._set_button_state(start='normal')
                return

            if not self.install_frontend_deps():
                self._set_button_state(start='normal')
                return

            if not self.ensure_directories():
                self._set_button_state(start='normal')
                return

            self.check_database()

            # 先清理本启动器自己可能残留的子进程（绝不无差别 kill 端口，避免误杀外部进程）
            self.kill_own_process(getattr(self, 'backend_process', None))
            self.backend_process = None
            self.kill_own_process(getattr(self, 'frontend_process', None))
            self.frontend_process = None
            time.sleep(1)

            # 启动自愈看门狗（仅一次）：仅重启本启动器自己管理的后端，绝不误杀外部进程
            if not getattr(self, '_watchdog_started', False):
                threading.Thread(target=self._health_watchdog, daemon=True).start()
                self._watchdog_started = True

            # 若 8000 已被外部健康进程占用，则复用而非重复启动（避免端口冲突与误杀）
            external_backend_healthy = is_port_open(8000) and is_service_healthy('http://localhost:8000/health', timeout=3)
            if external_backend_healthy:
                self.add_log("复用外部已运行的后端服务 (端口:8000)，本启动器不再重复启动", 'success')
                self.backend_status.set("运行中")
                self.backend_indicator.config(text='●', foreground=self.colors['green'])
                self._update_progress(self.backend_progress_canvas, 180, self.colors['green'])
            else:
                if is_port_open(8000):
                    self.add_log("8000 端口被占用但无 HTTP 响应，可能是外部异常进程，请手动停止后重试", 'warning')
                self.add_log("正在启动后端服务...", 'system')
                self.backend_status.set("启动中...")
                self.backend_indicator.config(text='●', foreground=self.colors['blue'])
                self._update_progress(self.backend_progress_canvas, 0, self.colors['blue'])

                self.backend_process = self._start_backend()

                if self.wait_for_port(8000):
                    self._update_progress(self.backend_progress_canvas, 180, self.colors['green'])
                    # 端口通了后再做 HTTP 健康检查确保服务真正可用
                    if is_service_healthy('http://localhost:8000/health', timeout=3):
                        self.add_log("后端服务启动成功并健康就绪 (端口:8000)", 'success')
                        self.backend_status.set("运行中")
                        self.backend_indicator.config(text='●', foreground=self.colors['green'])
                    else:
                        self.add_log("后端端口已开放但 HTTP 服务未就绪，继续等待...", 'warning')
                        time.sleep(2)
                        if is_service_healthy('http://localhost:8000/health', timeout=5):
                            self.add_log("后端服务最终就绪 (端口:8000)", 'success')
                            self.backend_status.set("运行中")
                            self.backend_indicator.config(text='●', foreground=self.colors['green'])
                        else:
                            self.add_log("后端服务可能异常，请检查后端控制台日志", 'error')
                            self.backend_status.set("异常")
                            self.backend_indicator.config(text='●', foreground=self.colors['orange'])
                else:
                    self._update_progress(self.backend_progress_canvas, 180, self.colors['orange'])
                    self.add_log("后端服务启动超时，可能仍在启动中...", 'warning')
                    self.backend_status.set("运行中")
                    self.backend_indicator.config(text='●', foreground=self.colors['green'])

            # 若 5173 已被外部健康进程占用，则复用而非重复启动（避免端口冲突与误杀）
            external_frontend_healthy = is_port_open(5173) and is_service_healthy('http://localhost:5173', timeout=3)
            if external_frontend_healthy:
                self.add_log("复用外部已运行的前端服务 (端口:5173)，本启动器不再重复启动", 'success')
                self.frontend_status.set("运行中")
                self.frontend_indicator.config(text='●', foreground=self.colors['green'])
                self._update_progress(self.frontend_progress_canvas, 180, self.colors['green'])
            else:
                if is_port_open(5173):
                    self.add_log("5173 端口被占用但无 HTTP 响应，可能是外部异常进程，请手动停止后重试", 'warning')
                self.add_log("正在启动前端服务...", 'system')
                self.frontend_status.set("启动中...")
                self.frontend_indicator.config(text='●', foreground=self.colors['blue'])
                self._update_progress(self.frontend_progress_canvas, 0, self.colors['blue'])

                frontend_dir = os.path.join(os.path.dirname(__file__), 'frontend')
                self.frontend_process = subprocess.Popen(
                    ['cmd', '/c', 'npm', 'run', 'dev'],
                    cwd=frontend_dir,
                    creationflags=CREATE_NO_WINDOW,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=False
                )

                self.frontend_log_thread = threading.Thread(
                    target=self.read_process_output,
                    args=(self.frontend_process, 'frontend'),
                    daemon=True
                )
                self.frontend_log_thread.start()

                if self.wait_for_port(5173):
                    self._update_progress(self.frontend_progress_canvas, 180, self.colors['green'])
                    if is_service_healthy('http://localhost:5173', timeout=3):
                        self.add_log("前端服务启动成功并健康就绪 (端口:5173)", 'success')
                        self.frontend_status.set("运行中")
                        self.frontend_indicator.config(text='●', foreground=self.colors['green'])
                    else:
                        self.add_log("前端端口已开放但 HTTP 服务未就绪，继续等待...", 'warning')
                        time.sleep(2)
                        if is_service_healthy('http://localhost:5173', timeout=5):
                            self.add_log("前端服务最终就绪 (端口:5173)", 'success')
                            self.frontend_status.set("运行中")
                            self.frontend_indicator.config(text='●', foreground=self.colors['green'])
                        else:
                            self.add_log("前端服务可能异常，请检查前端控制台日志", 'error')
                            self.frontend_status.set("异常")
                            self.frontend_indicator.config(text='●', foreground=self.colors['orange'])
                else:
                    self._update_progress(self.frontend_progress_canvas, 180, self.colors['orange'])
                    self.add_log("前端服务启动超时，可能仍在启动中...", 'warning')
                    self.frontend_status.set("运行中")
                    self.frontend_indicator.config(text='●', foreground=self.colors['green'])

            self.add_log("所有服务启动完成", 'success')

            self._set_button_state(start='normal', stop='normal', open='normal')

            time.sleep(2)
            self.open_browser()

        threading.Thread(target=run_start, daemon=True).start()

    def stop_services(self):
        self.add_log("正在停止服务...", 'system')

        # 统一通过端口杀进程，覆盖本启动器启动的及外部残留的
        if is_port_open(8000):
            self.add_log("停止后端服务 (端口 8000)...", 'warning')
            kill_process_on_port(8000)
            time.sleep(1.5)
            if not is_port_open(8000):
                self.add_log("后端服务已停止", 'success')
            else:
                self.add_log("后端端口 8000 释放失败，请手动检查", 'error')

        if is_port_open(5173):
            self.add_log("停止前端服务 (端口 5173)...", 'warning')
            kill_process_on_port(5173)
            time.sleep(1.5)
            if not is_port_open(5173):
                self.add_log("前端服务已停止", 'success')
            else:
                self.add_log("前端端口 5173 释放失败，请手动检查", 'error')

        # 更新状态显示
        if not is_port_open(8000):
            self.backend_status.set("未启动")
            self.backend_indicator.config(text='○', foreground=self.colors['text_tertiary'])
            self._update_progress(self.backend_progress_canvas, 0, self.colors['blue'])
        if not is_port_open(5173):
            self.frontend_status.set("未启动")
            self.frontend_indicator.config(text='○', foreground=self.colors['text_tertiary'])
            self._update_progress(self.frontend_progress_canvas, 0, self.colors['blue'])

        self.backend_process = None
        self.frontend_process = None
        self._set_button_state(start='normal', stop='disabled', open='disabled')

    def open_browser(self):
        self.add_log("正在打开浏览器...", 'system')
        webbrowser.open('http://localhost:5173')

    def _on_close(self):
        self.animation_running = False
        self.pulse_running = False
        # 检测端口占用而不仅是进程对象，覆盖非本启动器启动的服务
        if is_port_open(8000) or is_port_open(5173) or self.backend_process or self.frontend_process:
            if messagebox.askokcancel("退出确认", "服务正在运行中，确定要退出吗？\n退出时将自动停止所有相关进程。"):
                self.stop_services()
                self.root.destroy()
        else:
            self.root.destroy()


def main():
    root = tk.Tk()

    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

    root.configure(bg='#0d1117')

    app = WindowsLauncherApp(root)

    def on_closing():
        app._on_close()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == '__main__':
    main()