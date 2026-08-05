# -*- coding: utf-8 -*-
"""
订单管理系统启动器 - Windows Dark Tech Style
提供可视化交互界面和实时日志显示
"""

import os
import sys
import subprocess
import time
import webbrowser
import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import shutil
import sqlite3
import calendar
from datetime import datetime, timedelta

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
        # 记录创建本 App 的线程为主线程，用于把子线程里的 Tk 操作调度回主线程，
        # 避免跨线程访问 Tcl 解释器导致程序直接崩溃闪退（无任何 traceback）。
        self._main_thread = threading.current_thread()
        self.root.title("订单管理系统")
        self.root.geometry("1240x880")
        self.root.minsize(980, 680)
        self.root.resizable(True, True)
        self.root.configure(bg='#2c3138')

        self.colors = {
            'bg':              '#2c3138',   # 主背景（深灰蓝，磨砂玻璃风）
            'bg_light':        '#323841',   # 浅色背景
            'card':            '#374151',   # 卡片背景
            'card_border':     '#46505e',   # 卡片边框（淡亮边）
            'card_border_glow': '#4ade80',  # 卡片霓虹边框
            'text_primary':    '#e5e7eb',   # 主文字
            'text_secondary':  '#9ca3af',   # 辅助文字
            'text_tertiary':   '#6b7280',   # 三级文字
            'blue':            '#3b82f6',   # 科技蓝
            'blue_light':      '#60a5fa',   # 蓝色悬停
            'blue_dark':       '#2563eb',   # 蓝色按下
            'green':           '#4ade80',   # 成功绿
            'green_light':     '#6ee7a0',   # 绿色悬停
            'green_dark':      '#22c55e',   # 绿色按下
            'red':             '#f87171',   # 危险红
            'red_light':       '#fca5a5',   # 红色悬停
            'red_dark':        '#ef4444',   # 红色按下
            'orange':          '#f59e0b',   # 警告橙
            'yellow':          '#eab308',   # 黄色
            'cyan':            '#22d3ee',   # 青色
            'purple':          '#a78bfa',   # 紫色
            'progress_track':  '#4b5563',   # 进度条轨道
            'progress_fill':   '#4ade80',   # 进度条填充
            'log_bg':          '#1e2228',   # 终端日志背景
            'log_text':        '#cbd5e1',   # 终端日志文字
            'log_border':      '#374151',   # 终端边框
            'divider':         '#4b5563',   # 分割线
            'tab_active_bg':   '#4ade80',   # 标签页激活背景（绿）
            'tab_active_border': '#4ade80', # 标签页激活边框
            'tab_inactive_bg': '#374151',   # 标签页非激活背景
            'tab_inactive_text': '#9ca3af', # 标签页非激活文字
            'title_bar_bg':    '#1e2227',   # 标题栏背景
            'title_bar_btn':   '#374151',   # 标题栏按钮背景
            'title_bar_btn_hover': '#46505e', # 标题栏按钮悬停
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

        # 备份还原配置（与数据库、备份同域，放在 backend/data/ 下）
        self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend', 'data', 'launcher_config.json')
        self.backup_config = self._load_backup_config()
        self.backup_scheduler_event = threading.Event()
        self.backup_scheduler_thread = None
        self._settings_view_open = False

        self.create_widgets()
        self.apply_styles()
        self.detect_service_status()
        self.start_animations()
        self._start_backup_scheduler()

    def detect_service_status(self):
        # 先用端口检测快速判断，再用 HTTP 健康检查精准验证
        backend_port_open = is_port_open(8000)
        frontend_port_open = is_port_open(5173)

        if backend_port_open:
            if is_service_healthy('http://localhost:8000/health'):
                self._ui_set_service('backend', "运行中", self.colors['green'])
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
            self._update_progress(self.backend_progress_canvas, 0, self.colors['text_tertiary'])

        if frontend_port_open:
            if is_service_healthy('http://localhost:5173'):
                self._ui_set_service('frontend', "运行中", self.colors['green'])
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
            self._update_progress(self.frontend_progress_canvas, 0, self.colors['text_tertiary'])

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
                self._ui_set_service('backend', "运行中", self.colors['green'])
                self._update_progress(self.backend_progress_canvas, 180, self.colors['green'])
                self.add_log("后端服务: 健康运行 (端口 8000)", 'success')
            else:
                self._ui_set_service('backend', "异常", self.colors['orange'])
                self._update_progress(self.backend_progress_canvas, 100, self.colors['orange'])
                self.add_log("后端服务: 端口已占用但无响应，可能存在进程残留，请重启", 'warning')
        else:
            self.backend_status.set("未启动")
            self.backend_indicator.config(text='○', foreground=self.colors['text_tertiary'])
            self._update_progress(self.backend_progress_canvas, 0, self.colors['text_tertiary'])
            self.add_log("后端服务: 未启动 (端口 8000)", 'warning')

        # ── 更新前端状态 ──
        frontend_port_open = is_port_open(5173)
        if frontend_port_open:
            if is_service_healthy('http://localhost:5173'):
                self._ui_set_service('frontend', "运行中", self.colors['green'])
                self._update_progress(self.frontend_progress_canvas, 180, self.colors['green'])
                self.add_log("前端服务: 健康运行 (端口 5173)", 'success')
            else:
                self._ui_set_service('frontend', "异常", self.colors['orange'])
                self._update_progress(self.frontend_progress_canvas, 100, self.colors['orange'])
                self.add_log("前端服务: 端口已占用但无响应，可能存在进程残留，请重启", 'warning')
        else:
            self.frontend_status.set("未启动")
            self.frontend_indicator.config(text='○', foreground=self.colors['text_tertiary'])
            self._update_progress(self.frontend_progress_canvas, 0, self.colors['text_tertiary'])
            self.add_log("前端服务: 未启动 (端口 5173)", 'warning')

        # ── 更新按钮状态 ──
        if backend_port_open or frontend_port_open:
            self._set_button_state(start='normal', stop='normal', open='normal')
        else:
            self._set_button_state(start='normal', stop='disabled', open='disabled')

        self.add_log("状态刷新完成", 'system')

    def create_widgets(self):
        root_bg = self.colors['bg']

        # ═══════════════════════════════════════
        # Sidebar (72px)
        # ═══════════════════════════════════════
        sidebar = tk.Frame(self.root, bg='#1e2227', width=72)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        sidebar_top = tk.Frame(sidebar, bg='#1e2227')
        sidebar_top.pack(side=tk.TOP, fill=tk.X, pady=(22, 0))

        # 侧边栏仅保留首页与设置两个有效入口（矢量线性图标）
        def make_nav_icon(parent, name, cmd, active_view, pad_bottom=0):
            cv = tk.Canvas(parent, width=40, height=40, bg='#1e2227',
                           highlightthickness=0, cursor='hand2')
            cv.pack(pady=(0, pad_bottom))
            cv._name = name
            cv._active_view = active_view

            def redraw(hover=False):
                cv.delete('all')
                active = getattr(self, '_current_view', 'home') == active_view
                if active:
                    bg, icon_color = '#22c55e', '#ffffff'
                elif hover:
                    bg, icon_color = '#2a2f37', '#cbd5e1'
                else:
                    bg, icon_color = '#1e2227', '#9ca3af'
                cv.configure(bg=bg)
                self._draw_icon(cv, name, 20, 20, 22, icon_color)

            cv._redraw = redraw
            cv.bind('<Button-1>', lambda e: cmd())
            cv.bind('<Enter>', lambda e: redraw(hover=True))
            cv.bind('<Leave>', lambda e: redraw(hover=False))
            redraw()
            return cv

        self.nav_home = make_nav_icon(sidebar_top, 'home', self._show_home_view, 'home', pad_bottom=18)
        sidebar_bottom = tk.Frame(sidebar, bg='#1e2227')
        sidebar_bottom.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 22))
        self.nav_settings = make_nav_icon(sidebar_bottom, 'settings', self.open_settings_window, 'settings')

        self._current_view = 'home'
        self._settings_built = False
        self._settings_view_open = False
        self._refresh_nav()

        # ═══════════════════════════════════════
        # Main content
        # ═══════════════════════════════════════
        main = tk.Frame(self.root, bg=root_bg)
        main.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        header = tk.Frame(main, bg=root_bg)
        header.pack(fill=tk.X, padx=24, pady=(26, 0))
        tk.Label(header, text="订单管理系统", font=('微软雅黑', 22, 'bold'),
                 bg=root_bg, fg='#e5e7eb', anchor=tk.CENTER).pack(fill=tk.X)

        content = tk.Frame(main, bg=root_bg)
        content.pack(fill=tk.BOTH, expand=True, padx=24, pady=(18, 0))

        # 首页视图：服务概览 + 实时日志
        self.home_view = tk.Frame(content, bg=root_bg)
        self.home_view.pack(fill=tk.BOTH, expand=True)
        # 设置视图：数据库备份与还原（默认隐藏，点击 ⚙ 切换，不弹新窗口）
        self.settings_view = tk.Frame(content, bg=root_bg)

        left_card = self._create_card(self.home_view, "服务概览", side=tk.LEFT, expand=True, padx=(0, 10))
        right_card = self._create_card(self.home_view, "实时日志", side=tk.LEFT, expand=True, padx=(10, 0))

        # ── Left: service overview ──
        left_body = tk.Frame(left_card, bg=self.colors['card'])
        left_body.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 12))

        self._create_service_tile(left_body, 'backend', "后端接口服务", "后端在线服务", "后端在线服务", "server",
                                  self.colors['green'], side=tk.TOP)
        self._create_service_tile(left_body, 'frontend', "前端网页客户端", "前端页面服务", "前端页面服务", "window",
                                  self.colors['blue'], side=tk.TOP)

        # ── Right: realtime log ──
        right_body = tk.Frame(right_card, bg=self.colors['card'])
        right_body.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 12))

        tab_frame = tk.Frame(right_body, bg=self.colors['card'])
        tab_frame.pack(fill=tk.X, padx=12, pady=(8, 6))

        self.tab_buttons = []
        tab_specs = [("综合", "grid", "all"), ("前端", "window", "frontend"),
                     ("后端", "server", "backend"), ("备份", "save", "backup")]
        for i, (t, ic, key) in enumerate(tab_specs):
            cv = tk.Canvas(tab_frame, width=86, height=30, bg='#2f3742',
                           highlightthickness=0, cursor='hand2')
            cv.pack(side=tk.LEFT, padx=(0, 6))
            cv._text = t
            cv._icon = ic
            cv._active = (i == 0)

            def tab_redraw(cv=cv):
                cv.delete('all')
                if cv._active:
                    bg, fg = self.colors['green'], '#111827'
                else:
                    bg, fg = '#2f3742', self.colors['text_secondary']
                cv.configure(bg=bg)
                cv.create_text(43, 15, text=cv._text, font=('微软雅黑', 11), fill=fg, tags='t')

            cv._redraw = tab_redraw
            tab_redraw()
            cv.bind('<Button-1>', lambda e, idx=i: self._switch_tab(idx))
            self.tab_buttons.append(cv)

        search_row = tk.Frame(right_body, bg=self.colors['card'])
        search_row.pack(fill=tk.X, padx=12, pady=(0, 8))

        search = tk.Entry(search_row, bg='#1e2228', fg=self.colors['text_secondary'],
                          insertbackground=self.colors['text_secondary'], relief=tk.FLAT,
                          font=('微软雅黑', 10))
        search.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search.insert(0, "检索日志")
        search.bind('<FocusIn>', lambda e: search.delete(0, tk.END) if search.get() == "检索日志" else None)
        search.bind('<KeyRelease>', lambda e: self._filter_log(search.get()))
        self.log_search_entry = search

        search_btn = tk.Canvas(search_row, width=74, height=26, bg=self.colors['card'],
                                highlightthickness=0, cursor='hand2')
        search_btn.pack(side=tk.RIGHT)

        def search_redraw(hot=False):
            search_btn.delete('all')
            col = self.colors['text_primary'] if hot else self.colors['text_secondary']
            self._draw_icon(search_btn, 'search', 14, 13, 15, col)
            search_btn.create_text(34, 13, text="搜索", font=('微软雅黑', 10), fill=col, tags='s')

        search_btn.bind('<Enter>', lambda e: search_redraw(hot=True))
        search_btn.bind('<Leave>', lambda e: search_redraw(hot=False))
        search_btn.bind('<Button-1>', lambda e: self._filter_log(search.get()))
        search_redraw()

        log_area = tk.Frame(right_body, bg='#1e2228')
        log_area.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        log_font = ('Consolas', 9) if sys.platform == 'win32' else ('Menlo', 10)
        self.all_log_text = tk.Text(log_area, state=tk.DISABLED, font=log_font, wrap=tk.WORD,
                                    bg='#1e2228', fg=self.colors['log_text'], relief=tk.FLAT,
                                    padx=10, pady=8, spacing1=2, highlightthickness=0,
                                    insertbackground=self.colors['blue'])
        self.all_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.backend_log_text = tk.Text(log_area, state=tk.DISABLED, font=log_font, wrap=tk.WORD,
                                         bg='#1e2228', fg=self.colors['log_text'], relief=tk.FLAT,
                                         padx=10, pady=8, spacing1=2, highlightthickness=0)
        self.frontend_log_text = tk.Text(log_area, state=tk.DISABLED, font=log_font, wrap=tk.WORD,
                                          bg='#1e2228', fg=self.colors['log_text'], relief=tk.FLAT,
                                          padx=10, pady=8, spacing1=2, highlightthickness=0)
        self.backup_log_text = tk.Text(log_area, state=tk.DISABLED, font=log_font, wrap=tk.WORD,
                                        bg='#1e2228', fg=self.colors['log_text'], relief=tk.FLAT,
                                        padx=10, pady=8, spacing1=2, highlightthickness=0)

        scrollbar_frame = tk.Frame(log_area, bg='#1e2228', width=12)
        scrollbar_frame.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_frame.pack_propagate(False)
        self.log_scrollbar = ttk.Scrollbar(scrollbar_frame, orient=tk.VERTICAL,
                                           command=self.all_log_text.yview,
                                           style='DarkScrollbar.Vertical.TScrollbar')
        self.log_scrollbar.pack(fill=tk.Y, expand=True)
        self.all_log_text.configure(yscrollcommand=self.log_scrollbar.set)

        self.active_tab = 0
        self.tab_text_widgets = [self.all_log_text, self.frontend_log_text, self.backend_log_text, self.backup_log_text]

        log_tags = {
            'system':  self.colors['text_tertiary'],
            'backend': '#60a5fa',
            'frontend': '#4ade80',
            'error':   '#f87171',
            'success': '#4ade80',
            'warning': '#f59e0b',
            'info':    '#60a5fa',
        }
        for tw in self.tab_text_widgets:
            for tag, color in log_tags.items():
                tw.tag_config(tag, foreground=color)

        # ═══════════════════════════════════════
        # Bottom function buttons
        # ═══════════════════════════════════════
        # 每个按钮由左右两部分组成：左侧放图标+文字，右侧为纯色色块
        self._btn_spec = {
            'start':   {'color': '#22c55e', 'hover': '#4ade80', 'press': '#16a34a', 'off': '#374151'},
            'stop':    {'color': '#ef4444', 'hover': '#f87171', 'press': '#dc2626', 'off': '#374151'},
            'open':    {'color': '#3b82f6', 'hover': '#60a5fa', 'press': '#2563eb', 'off': '#374151'},
            'refresh': {'color': '#06b6d4', 'hover': '#22d3ee', 'press': '#0891b2', 'off': '#374151'},
        }

        btn_row = tk.Frame(main, bg=root_bg)
        btn_row.pack(fill=tk.X, padx=24, pady=(16, 24))
        for _i in range(4):
            btn_row.grid_columnconfigure(_i, weight=1)
        btn_row.grid_rowconfigure(0, weight=1)

        self.start_btn = self._make_func_btn(btn_row, "启动系统", "play",
                                             self._btn_spec['start'], self.start_services, '_start_enabled', col=0)
        self.stop_btn = self._make_func_btn(btn_row, "停止系统", "stop",
                                            self._btn_spec['stop'], self.stop_services, '_stop_enabled', col=1)
        self.open_btn = self._make_func_btn(btn_row, "打开页面", "browser",
                                            self._btn_spec['open'], self.open_browser, '_open_enabled', col=2)
        self.refresh_btn = self._make_func_btn(btn_row, "刷新状态", "refresh",
                                               self._btn_spec['refresh'], self.refresh_status, None, col=3)

    # ─────────────────────────────────────────
    # Service tile / toggle / wave helpers
    # ─────────────────────────────────────────
    def _create_service_tile(self, parent, key, name, tag_on, tag_off, glyph, accent=None, side=tk.LEFT):
        tile = tk.Frame(parent, bg='#2b323b', highlightbackground=self.colors['card_border'], highlightthickness=1)
        if side == tk.TOP:
            tile.pack(side=tk.TOP, fill=tk.X, expand=False, padx=8, pady=6)
        else:
            tile.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)

        icon = tk.Canvas(tile, width=64, height=64, bg='#2b323b', highlightthickness=0)
        icon.pack(pady=(20, 4))
        accent = accent or self.colors['green']
        self._hex(icon, 32, 32, 30, fill='#1e2228', outline=accent, width=1)
        self._draw_icon(icon, glyph, 32, 32, 36, accent)

        tk.Label(tile, text=name, font=('微软雅黑', 13, 'bold'), bg='#2b323b',
                 fg=self.colors['text_primary']).pack(pady=(2, 10))

        wave = tk.Canvas(tile, width=180, height=14, bg='#2b323b', highlightthickness=0)
        wave.pack()
        self._draw_wave(wave, accent)
        setattr(self, f'{key}_wave_canvas', wave)

        slider = tk.Canvas(tile, width=180, height=14, bg='#2b323b', highlightthickness=0)
        slider.pack(pady=(8, 4))
        self._draw_progress_track(slider, 180, 6)
        setattr(self, f'{key}_progress_canvas', slider)

        row = tk.Frame(tile, bg='#2b323b')
        row.pack(fill=tk.X, pady=(2, 12), padx=14)
        indicator = tk.Label(row, text="未启动", font=('微软雅黑', 11), bg='#2b323b',
                             fg=self.colors['text_tertiary'])
        indicator.pack(side=tk.LEFT)
        setattr(self, f'{key}_indicator', indicator)
        toggle = tk.Canvas(row, width=44, height=22, bg='#2b323b', highlightthickness=0)
        toggle.pack(side=tk.RIGHT)
        setattr(self, f'{key}_toggle_canvas', toggle)
        self._draw_toggle(toggle, False)

        slider._indicator = indicator
        slider._toggle = toggle
        slider._tag = None
        slider._tag_on = tag_on
        slider._tag_off = tag_off
        slider._wave = wave
        slider._icon = icon
        slider._glyph = glyph
        slider._accent = accent
        self._update_progress(slider, 0, self.colors['text_tertiary'])

    def _draw_toggle(self, canvas, on):
        canvas.delete('all')
        w, h = 44, 22
        r = h // 2
        bg = self.colors['green'] if on else '#4b5563'
        self._draw_rounded_rect(canvas, 0, 0, w, h, r, fill=bg, outline='', tags='tg')
        knob_r = 8
        padding = 1.5
        cx = w - r - padding if on else r + padding
        cy = h / 2
        canvas.create_oval(cx - knob_r, cy - knob_r, cx + knob_r, cy + knob_r, fill='#ffffff', outline='')

    def _draw_wave(self, canvas, color):
        canvas.delete('all')
        w, h = 180, 14
        bar_w = 3
        gap = 4
        n = w // (bar_w + gap)
        # 固定高度的竖条均衡器样式，与截图一致
        heights = [5, 9, 6, 11, 7, 13, 8, 12, 6, 10, 7, 14, 9, 11, 6, 8, 10, 7, 12, 6, 9, 5]
        for i in range(n):
            x = i * (bar_w + gap) + gap
            hh = min(heights[i % len(heights)], h - 2)
            y1 = (h - hh) / 2
            y2 = y1 + hh
            self._draw_rounded_rect(canvas, x, y1, x + bar_w, y2, 1.5, fill=color, outline='', tags='wave')

    def _draw_slider_knob(self, canvas, x):
        r = 6
        max_w = 180
        x = max(r, min(x, max_w - r))
        cy = 3
        canvas.create_oval(x - r, cy - r, x + r, cy + r, fill='#ffffff', outline='', tags='knob')

    def _hex(self, canvas, cx, cy, r, **kw):
        import math
        pts = []
        for i in range(6):
            ang = math.radians(60 * i - 30)
            pts.append(cx + r * math.cos(ang))
            pts.append(cy + r * math.sin(ang))
        canvas.create_polygon(pts, **kw)

    # ─────────────────────────────────────────
    # 统一线性图标库（24x24 网格，中心对齐，圆角线帽）
    # ─────────────────────────────────────────
    def _draw_icon(self, canvas, name, cx, cy, size, color, width=None):
        """绘制统一风格的线性图标。name 决定图标种类；size 为外接边长(px)。"""
        import math
        u = size / 24.0
        lw = width if width is not None else max(1.6, size * 0.09)

        def P(x, y):
            return (cx + (x - 12) * u, cy + (y - 12) * u)

        def line(*pts, w=lw):
            canvas.create_line(*pts, fill=color, width=w, joinstyle=tk.ROUND,
                               capstyle=tk.ROUND, tags='icon')

        def rect(x1, y1, x2, y2, w=lw):
            canvas.create_rectangle(*P(x1, y1), *P(x2, y2), outline=color, fill='',
                                    width=w, tags='icon')

        def oval(x1, y1, x2, y2, w=lw):
            canvas.create_oval(*P(x1, y1), *P(x2, y2), outline=color, fill='',
                               width=w, tags='icon')

        def poly(*pts, w=lw):
            canvas.create_polygon(*pts, outline=color, fill='', width=w,
                                  joinstyle=tk.ROUND, tags='icon')

        if name == 'home':
            line(*P(12, 3), *P(5, 11), *P(19, 11))
            line(*P(7, 10), *P(7, 21), *P(17, 21), *P(17, 10))
            line(*P(11, 21), *P(11, 15), *P(13, 15), *P(13, 21))
        elif name == 'settings':
            oval(8, 8, 16, 16)
            canvas.create_oval(*P(10.5, 10.5), *P(13.5, 13.5), outline=color, fill='',
                               width=lw * 0.7, tags='icon')
            for k in range(8):
                a = math.radians(45 * k)
                line(cx + (7.6 * math.cos(a)) * u, cy + (7.6 * math.sin(a)) * u,
                     cx + (10 * math.cos(a)) * u, cy + (10 * math.sin(a)) * u, w=lw * 0.8)
        elif name == 'play':
            poly(*P(8, 6), *P(8, 18), *P(18, 12))
        elif name == 'stop':
            rect(7, 7, 17, 17)
        elif name == 'browser':
            rect(4, 5, 20, 19)
            line(*P(4, 9), *P(20, 9))
            oval(6.3, 7, 8, 8.7, lw * 0.7)
            oval(9.3, 7, 11, 8.7, lw * 0.7)
            oval(12.3, 7, 14, 8.7, lw * 0.7)
        elif name == 'refresh' or name == 'refresh_list':
            oval(6, 6, 18, 18)
            poly(*P(12, 3.5), *P(9, 7), *P(15, 7))
        elif name == 'server':
            oval(5, 6, 19, 10)
            line(*P(5, 6), *P(5, 18))
            line(*P(19, 6), *P(19, 18))
            canvas.create_arc(*P(5, 14), *P(19, 18), start=0, extent=180,
                              style=tk.ARC, outline=color, width=lw, tags='icon')
            line(*P(5, 12), *P(19, 12))
        elif name == 'window':
            rect(5, 5, 19, 15)
            line(*P(12, 15), *P(12, 18))
            line(*P(8, 18), *P(16, 18))
        elif name == 'folder':
            rect(4, 7, 20, 18)
            line(*P(4, 7), *P(8, 7), *P(10, 4), *P(20, 4))
        elif name == 'save':
            rect(5, 5, 19, 19)
            rect(9, 5, 15, 11)
            rect(8, 13, 16, 17)
        elif name == 'save_settings':
            rect(5, 5, 19, 19)
            line(*P(9, 12), *P(12, 15), *P(16, 9))
        elif name == 'import':
            rect(7, 4, 17, 20)
            line(*P(12, 17), *P(12, 9))
            poly(*P(9, 12), *P(12, 9), *P(15, 12))
        elif name == 'restore':
            oval(6, 6, 18, 18)
            line(*P(12, 12), *P(12, 7))
            line(*P(12, 12), *P(16, 13))
        elif name == 'search':
            oval(6, 6, 15, 15)
            line(*P(13.5, 13.5), *P(18, 18))
        elif name == 'grid':
            rect(5, 5, 19, 19)
            line(*P(12, 5), *P(12, 19))
            line(*P(5, 12), *P(19, 12))
        else:
            oval(9, 9, 15, 15)

    def _darken(self, hex_color, factor=0.8):
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join(c * 2 for c in hex_color)
        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
        except ValueError:
            return hex_color
        r = max(0, min(255, int(r * factor)))
        g = max(0, min(255, int(g * factor)))
        b = max(0, min(255, int(b * factor)))
        return f'#{r:02x}{g:02x}{b:02x}'

    def _make_func_btn(self, parent, text, icon, spec, cmd, enabled_attr, col=None):
        c = tk.Canvas(parent, height=120, bg=parent.cget('bg'), highlightthickness=0, cursor='hand2')
        if col is not None:
            c.grid(row=0, column=col, sticky='nsew', padx=8)
        else:
            c.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
        c._spec = spec
        c._text = text
        c._icon = icon
        c._enabled_attr = enabled_attr
        c._cmd = cmd
        c._hover = False
        c._press = False

        def redraw(event=None):
            w = c.winfo_width()
            h = c.winfo_height()
            if w < 20 or h < 20:
                w, h = 200, 120
            enabled = (enabled_attr is None) or getattr(self, enabled_attr, True)
            if not enabled:
                color = spec['off']
            elif c._press:
                color = spec['press']
            elif c._hover:
                color = spec['hover']
            else:
                color = spec['color']
            c.delete('all')
            self._draw_rounded_rect(c, 0, 0, w, h, 12, fill=color, outline='', tags='btn_bg')
            icon_color = '#ffffff' if enabled else '#9aa3af'
            icon_size = min(34, w * 0.28)
            self._draw_icon(c, icon, w / 2, h * 0.38, icon_size, icon_color)
            c.create_text(w / 2, h * 0.72, text=text, font=('微软雅黑', 13, 'bold'),
                          fill=icon_color, tags='tx')

        c._redraw = redraw

        def on_enter(e):
            c._hover = True
            redraw()

        def on_leave(e):
            c._hover = False
            c._press = False
            redraw()

        def on_press(e):
            if (enabled_attr is None) or getattr(self, enabled_attr, True):
                c._press = True
                redraw()

        def on_release(e):
            c._press = False
            redraw()
            if (enabled_attr is None) or getattr(self, enabled_attr, True):
                cmd()

        c.bind('<Enter>', on_enter)
        c.bind('<Leave>', on_leave)
        c.bind('<ButtonPress-1>', on_press)
        c.bind('<ButtonRelease-1>', on_release)
        c.bind('<Configure>', redraw)
        c.update_idletasks()
        redraw()
        c.after(100, redraw)
        return c

    def _style_func_btn(self, c, spec, enabled):
        c._spec = spec
        c._redraw()

    def _filter_log(self, query):
        widget = self.tab_text_widgets[self.active_tab]
        try:
            widget.config(state=tk.NORMAL)
            widget.tag_remove('hidden', '1.0', tk.END)
            q = (query or '').strip().lower()
            if q and q != "检索日志":
                lines = widget.get('1.0', tk.END).split('\n')
                for i, line in enumerate(lines):
                    if q not in line.lower():
                        widget.tag_add('hidden', f'{i+1}.0', f'{i+1}.end')
                widget.tag_config('hidden', elide=True)
            widget.config(state=tk.DISABLED)
        except Exception:
            pass

    def _create_card(self, parent, title, expand=False, side=None, padx=0, pady=10):
        outer = tk.Frame(parent, bg=self.colors['bg'])
        if side is not None:
            outer.pack(side=side, fill=tk.BOTH if expand else tk.X, expand=expand, padx=padx, pady=(0, pady))
        elif expand:
            outer.pack(fill=tk.BOTH, expand=True, pady=(0, pady))
        else:
            outer.pack(fill=tk.X, pady=(0, pady))

        card = tk.Canvas(outer, bg=self.colors['card'], highlightthickness=0)
        if expand:
            card.pack(fill=tk.BOTH, expand=True)
        else:
            card.pack(fill=tk.X)

        def _on_card_configure(event):
            card.delete('bg')
            r = 10
            w, h = event.width, event.height
            self._draw_rounded_rect(card, 0, 0, w, h, r, fill=self.colors['card'], outline=self.colors['card_border'], width=1, tags='bg')

        card.bind('<Configure>', _on_card_configure)

        if title:
            title_label = tk.Label(
                card, text=title,
                font=('微软雅黑', 13, 'bold'),
                bg=self.colors['card'], fg=self.colors['text_primary'],
                anchor=tk.W
            )
            title_label.pack(fill=tk.X, padx=16, pady=(14, 6))

        return card
    def _draw_rounded_rect(self, canvas, x1, y1, x2, y2, r, **kwargs):
        """四角均为圆角的矩形。改用密集线段（smooth=False）绘制真实圆弧，
        避免 Tkinter 对直角顶点使用 smooth 贝塞尔曲线时在拐角处产生抗锯齿杂色边。"""
        return self._draw_partial_rounded_rect(
            canvas, x1, y1, x2, y2, r, (True, True, True, True), **kwargs)

    def _draw_rounded_btn(self, canvas, w, h, color, r=20):
        canvas.delete('btn_bg')
        self._draw_rounded_rect(canvas, 0, 0, w, h, r, fill=color, outline='', tags='btn_bg')
        canvas.tag_lower('btn_bg')

    def _draw_partial_rounded_rect(self, canvas, x1, y1, x2, y2, r, rounded, **kwargs):
        """绘制可指定哪些角圆角的矩形。rounded 为 (tl, tr, br, bl) 布尔元组。
        使用密集线段近似圆弧，smooth=False，避免 Tkinter 把直边也弯成曲线。"""
        import math
        pts = []
        # top-left corner: 圆心 (x1+r, y1+r), 角度 180 -> 270
        if rounded[0]:
            for i in range(180, 271, 5):
                ang = math.radians(i)
                pts.extend([x1 + r + r * math.cos(ang), y1 + r + r * math.sin(ang)])
        else:
            pts.extend([x1, y1])
        # top edge -> top-right start
        pts.extend([x2 - (r if rounded[1] else 0), y1])
        # top-right corner: 圆心 (x2-r, y1+r), 角度 270 -> 360
        if rounded[1]:
            for i in range(270, 361, 5):
                ang = math.radians(i)
                pts.extend([x2 - r + r * math.cos(ang), y1 + r + r * math.sin(ang)])
        else:
            pts.extend([x2, y1])
        # right edge -> bottom-right start
        pts.extend([x2, y2 - (r if rounded[2] else 0)])
        # bottom-right corner: 圆心 (x2-r, y2-r), 角度 0 -> 90
        if rounded[2]:
            for i in range(0, 91, 5):
                ang = math.radians(i)
                pts.extend([x2 - r + r * math.cos(ang), y2 - r + r * math.sin(ang)])
        else:
            pts.extend([x2, y2])
        # bottom edge -> bottom-left start
        pts.extend([x1 + (r if rounded[3] else 0), y2])
        # bottom-left corner: 圆心 (x1+r, y2-r), 角度 90 -> 180
        if rounded[3]:
            for i in range(90, 181, 5):
                ang = math.radians(i)
                pts.extend([x1 + r + r * math.cos(ang), y2 - r + r * math.sin(ang)])
        else:
            pts.extend([x1, y2])
        return canvas.create_polygon(pts, smooth=False, **kwargs)

    def _draw_two_part_btn(self, canvas, w, h, left_color, right_color, split=0.72, r=12):
        """绘制左右两部分组成的按钮：左侧放图标文字，右侧为纯色色块。
        先以 right_color 画完整圆角矩形作为外框底色（确保四个圆角处都不透出窗口背景），
        再用只有左侧两个圆角的 left_color 块覆盖左半部分，并向右多覆盖 2px 以避免中间接缝出现缝隙。"""
        canvas.delete('btn_bg')
        s = w * split
        overlap = 2
        # 完整右侧色块外框：所有圆角/接缝处均由 right_color 兜底
        self._draw_rounded_rect(canvas, 0, 0, w, h, r, fill=right_color, outline='', tags='btn_bg')
        # 左侧色块覆盖左半部分，仅保留左上、左下圆角
        self._draw_partial_rounded_rect(canvas, 0, 0, s + overlap, h, r,
                                        (True, False, False, True),
                                        fill=left_color, outline='', tags='btn_bg')
        canvas.tag_lower('btn_bg')

    def _draw_progress_track(self, canvas, w, h, r=3):
        self._draw_rounded_rect(canvas, 0, 0, w, h, r, fill=self.colors['progress_track'], outline='')

    def _update_progress(self, canvas, width, color):
        # 子线程调用时切回主线程执行，避免跨线程访问 Tk 导致闪退
        if threading.current_thread() is not self._main_thread:
            self.root.after(0, self._update_progress, canvas, width, color)
            return
        max_w = 180
        width = max(0, min(width, max_w))
        canvas.delete('progress_fill')
        canvas.delete('knob')

        # 根据传入 color 判断状态：green=运行中 orange=异常 blue=启动中 其它=未启动
        if color == self.colors['green']:
            state, accent = 'running', self.colors['green']
        elif color == self.colors['orange']:
            state, accent = 'error', self.colors['orange']
        elif color == self.colors['blue']:
            state, accent = 'starting', self.colors['blue']
        else:
            state, accent = 'off', getattr(canvas, '_accent', self.colors['text_tertiary'])

        # 已启动/异常/启动中时绘制填充条；未启动时仅显示灰色轨道
        if state in ('running', 'error', 'starting') and width > 0:
            self._draw_rounded_rect(canvas, 0, 0, width, 6, 3, fill=accent, outline='', tags='progress_fill')

        # 白色圆形滑块，位于填充条末端（未启动时在左侧）
        self._draw_slider_knob(canvas, width)

        indicator = getattr(canvas, '_indicator', None)
        toggle = getattr(canvas, '_toggle', None)
        tag = getattr(canvas, '_tag', None)
        wave = getattr(canvas, '_wave', None)
        icon = getattr(canvas, '_icon', None)
        glyph = getattr(canvas, '_glyph', '')

        if state == 'running':
            word, fg, on, hex_fill = "运行中", self.colors['green'], True, '#16351f'
        elif state == 'error':
            word, fg, on, hex_fill = "异常", self.colors['orange'], True, '#3f2c1e'
        elif state == 'starting':
            word, fg, on, hex_fill = "启动中...", self.colors['blue'], True, '#1e293b'
        else:
            word, fg, on, hex_fill = "未启动", self.colors['text_tertiary'], False, '#1e2228'

        if indicator:
            indicator.config(text=word, fg=fg)
        if toggle:
            self._draw_toggle(toggle, on)
        if wave:
            self._draw_wave(wave, accent)
        if icon:
            icon.delete('all')
            self._hex(icon, 32, 32, 30, fill=hex_fill, outline=accent, width=1)
            self._draw_icon(icon, glyph, 32, 32, 36, accent)

    def _hover_btn(self, canvas, w, h, color):
        self._draw_rounded_btn(canvas, w, h, color)

    def _set_button_state(self, start='normal', stop='disabled', open='disabled'):
        # 子线程调用时切回主线程执行，避免跨线程访问 Tk 导致闪退
        if threading.current_thread() is not self._main_thread:
            self.root.after(0, self._set_button_state, start, stop, open)
            return
        """Update button visual state WITHOUT using tk.DISABLED (which applies gray stipple mask)."""
        # ── Start button ──
        self._style_func_btn(self.start_btn, self._btn_spec['start'], start != 'disabled')
        self._start_enabled = (start != 'disabled')
        self.start_btn.config(cursor='hand2' if self._start_enabled else 'arrow')

        # ── Stop button ──
        self._style_func_btn(self.stop_btn, self._btn_spec['stop'], stop != 'disabled')
        self._stop_enabled = (stop != 'disabled')
        self.stop_btn.config(cursor='hand2' if self._stop_enabled else 'arrow')

        # ── Open button ──
        self._style_func_btn(self.open_btn, self._btn_spec['open'], open != 'disabled')
        self._open_enabled = (open != 'disabled')
        self.open_btn.config(cursor='hand2' if self._open_enabled else 'arrow')

    def _to_ui(self, fn, *args):
        """线程安全地执行 Tk 操作：非主线程时通过 after 切回主线程，
        避免跨线程访问 Tcl 导致解释器崩溃/闪退。"""
        if threading.current_thread() is self._main_thread:
            fn(*args)
        else:
            self.root.after(0, fn, *args)

    def _ui_set_service(self, which, word, fg):
        """线程安全地设置某服务的状态文字与指示灯（供子线程调用）。"""
        status_var = self.backend_status if which == 'backend' else self.frontend_status
        ind = self.backend_indicator if which == 'backend' else self.frontend_indicator
        self._to_ui(lambda: (status_var.set(word), ind.config(text='●', foreground=fg)))

    def _switch_tab(self, index):
        if index == self.active_tab:
            return

        for i, btn in enumerate(self.tab_buttons):
            btn._active = (i == index)
            btn._redraw()

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

    def add_log(self, text, source='system', level='info', channel=None):
        # 子线程调用时切回主线程执行，避免跨线程访问 Text 控件导致闪退
        if threading.current_thread() is not self._main_thread:
            self.root.after(0, self.add_log, text, source, level, channel)
            return
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

        # 备份/还原相关日志额外写入“备份”标签页
        if channel == 'backup' and getattr(self, 'backup_log_text', None):
            bt = self.backup_log_text
            bt.config(state=tk.NORMAL)
            bt.insert(tk.END, log_line, tag)
            bt.config(state=tk.DISABLED)
            bt.see(tk.END)

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
        self._update_progress(self.backend_progress_canvas, 0, self.colors['text_tertiary'])
        self._update_progress(self.frontend_progress_canvas, 0, self.colors['text_tertiary'])
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
                self._ui_set_service('backend', "运行中", self.colors['green'])
                self._update_progress(self.backend_progress_canvas, 180, self.colors['green'])
            else:
                if is_port_open(8000):
                    self.add_log("8000 端口被占用但无 HTTP 响应，可能是外部异常进程，请手动停止后重试", 'warning')
                self.add_log("正在启动后端服务...", 'system')
                self._ui_set_service('backend', "启动中...", self.colors['blue'])
                self._update_progress(self.backend_progress_canvas, 0, self.colors['text_tertiary'])

                self.backend_process = self._start_backend()

                if self.wait_for_port(8000):
                    self._update_progress(self.backend_progress_canvas, 180, self.colors['green'])
                    # 端口通了后再做 HTTP 健康检查确保服务真正可用
                    if is_service_healthy('http://localhost:8000/health', timeout=3):
                        self.add_log("后端服务启动成功并健康就绪 (端口:8000)", 'success')
                        self._ui_set_service('backend', "运行中", self.colors['green'])
                    else:
                        self.add_log("后端端口已开放但 HTTP 服务未就绪，继续等待...", 'warning')
                        time.sleep(2)
                        if is_service_healthy('http://localhost:8000/health', timeout=5):
                            self.add_log("后端服务最终就绪 (端口:8000)", 'success')
                            self._ui_set_service('backend', "运行中", self.colors['green'])
                        else:
                            self.add_log("后端服务可能异常，请检查后端控制台日志", 'error')
                            self._ui_set_service('backend', "异常", self.colors['orange'])
                else:
                    self._update_progress(self.backend_progress_canvas, 180, self.colors['orange'])
                    self.add_log("后端服务启动超时，可能仍在启动中...", 'warning')
                    self._ui_set_service('backend', "运行中", self.colors['green'])

            # 若 5173 已被外部健康进程占用，则复用而非重复启动（避免端口冲突与误杀）
            external_frontend_healthy = is_port_open(5173) and is_service_healthy('http://localhost:5173', timeout=3)
            if external_frontend_healthy:
                self.add_log("复用外部已运行的前端服务 (端口:5173)，本启动器不再重复启动", 'success')
                self._ui_set_service('frontend', "运行中", self.colors['green'])
                self._update_progress(self.frontend_progress_canvas, 180, self.colors['green'])
            else:
                if is_port_open(5173):
                    self.add_log("5173 端口被占用但无 HTTP 响应，可能是外部异常进程，请手动停止后重试", 'warning')
                self.add_log("正在启动前端服务...", 'system')
                self._ui_set_service('frontend', "启动中...", self.colors['blue'])
                self._update_progress(self.frontend_progress_canvas, 0, self.colors['text_tertiary'])

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
                        self._ui_set_service('frontend', "运行中", self.colors['green'])
                    else:
                        self.add_log("前端端口已开放但 HTTP 服务未就绪，继续等待...", 'warning')
                        time.sleep(2)
                        if is_service_healthy('http://localhost:5173', timeout=5):
                            self.add_log("前端服务最终就绪 (端口:5173)", 'success')
                            self._ui_set_service('frontend', "运行中", self.colors['green'])
                        else:
                            self.add_log("前端服务可能异常，请检查前端控制台日志", 'error')
                            self._ui_set_service('frontend', "异常", self.colors['orange'])
                else:
                    self._update_progress(self.frontend_progress_canvas, 180, self.colors['orange'])
                    self.add_log("前端服务启动超时，可能仍在启动中...", 'warning')
                    self._ui_set_service('frontend', "运行中", self.colors['green'])

            self.add_log("所有服务启动完成", 'success')

            self._set_button_state(start='normal', stop='normal', open='normal')

            time.sleep(2)
            self._to_ui(self.open_browser)

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
            self._update_progress(self.backend_progress_canvas, 0, self.colors['text_tertiary'])
        if not is_port_open(5173):
            self.frontend_status.set("未启动")
            self.frontend_indicator.config(text='○', foreground=self.colors['text_tertiary'])
            self._update_progress(self.frontend_progress_canvas, 0, self.colors['text_tertiary'])

        self.backend_process = None
        self.frontend_process = None
        self._set_button_state(start='normal', stop='disabled', open='disabled')

    def open_browser(self):
        self.add_log("正在打开浏览器...", 'system')
        webbrowser.open('http://localhost:5173')

    # ═══════════════════════════════════════
    # Settings / Backup & Restore
    # ═══════════════════════════════════════

    def _load_backup_config(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        default_dir = os.path.join(base_dir, 'backend', 'data', 'backup')
        default = {
            'backup_dir': default_dir,
            'auto_backup': {
                'enabled': False,
                'period': 'daily',
                'time': '02:00',
                'weekday': 0,
                'day': 1
            }
        }
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                for k, v in default.items():
                    if k not in cfg:
                        cfg[k] = v
                if 'auto_backup' in cfg:
                    for k, v in default['auto_backup'].items():
                        if k not in cfg['auto_backup']:
                            cfg['auto_backup'][k] = v
                else:
                    cfg['auto_backup'] = default['auto_backup']
                return cfg
            except Exception:
                pass
        return default

    def _save_backup_config(self):
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.backup_config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.add_log(f"保存备份配置失败: {e}", 'error', channel='backup')

    def _start_backup_scheduler(self):
        self._stop_backup_scheduler()
        cfg = self.backup_config.get('auto_backup', {})
        if not cfg.get('enabled'):
            return
        self.backup_scheduler_event.clear()
        self.backup_scheduler_thread = threading.Thread(target=self._backup_scheduler_loop, daemon=True)
        self.backup_scheduler_thread.start()

    def _stop_backup_scheduler(self):
        self.backup_scheduler_event.set()
        if self.backup_scheduler_thread and self.backup_scheduler_thread.is_alive():
            self.backup_scheduler_thread.join(timeout=2)
        self.backup_scheduler_thread = None

    def _backup_scheduler_loop(self):
        while not self.backup_scheduler_event.is_set():
            cfg = self.backup_config.get('auto_backup', {})
            if not cfg.get('enabled'):
                break
            next_time = self._compute_next_backup_time(cfg)
            now = datetime.now()
            wait_seconds = max(60, int((next_time - now).total_seconds()))
            self.add_log(f"下次自动备份时间: {next_time.strftime('%Y-%m-%d %H:%M')}", 'system', channel='backup')
            slept = 0
            while slept < wait_seconds and not self.backup_scheduler_event.is_set():
                chunk = min(60, wait_seconds - slept)
                time.sleep(chunk)
                slept += chunk
            if self.backup_scheduler_event.is_set():
                break
            if not self.backup_config.get('auto_backup', {}).get('enabled'):
                break
            self.add_log("执行定时自动备份...", 'system', channel='backup')
            self._run_backup_task()

    def _compute_next_backup_time(self, cfg):
        period = cfg.get('period', 'daily')
        time_str = cfg.get('time', '02:00')
        hour, minute = map(int, time_str.split(':'))
        now = datetime.now()

        if period == 'daily':
            candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if candidate <= now:
                candidate += timedelta(days=1)
            return candidate

        if period == 'weekly':
            weekday = int(cfg.get('weekday', 0))
            candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            days_ahead = (weekday - candidate.weekday()) % 7
            candidate += timedelta(days=days_ahead)
            if candidate <= now:
                candidate += timedelta(days=7)
            return candidate

        if period == 'monthly':
            day = int(cfg.get('day', 1))
            last_day = calendar.monthrange(now.year, now.month)[1]
            safe_day = min(day, last_day)
            candidate = now.replace(day=safe_day, hour=hour, minute=minute, second=0, microsecond=0)
            if candidate <= now:
                if now.month == 12:
                    y, m = now.year + 1, 1
                else:
                    y, m = now.year, now.month + 1
                last_day = calendar.monthrange(y, m)[1]
                safe_day = min(day, last_day)
                candidate = now.replace(year=y, month=m, day=safe_day, hour=hour, minute=minute, second=0, microsecond=0)
            return candidate

        return now + timedelta(days=1)

    def _run_backup_task(self):
        try:
            backup_dir = self.backup_config.get('backup_dir')
            if not backup_dir:
                self._log_to_settings("备份失败: 未配置备份目录", 'error')
                return
            os.makedirs(backup_dir, exist_ok=True)

            base_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(base_dir, 'backend', 'data', 'db', 'order_system.db')
            if not os.path.exists(db_path):
                self._log_to_settings(f"备份失败: 数据库文件不存在 {db_path}", 'error')
                return

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = os.path.join(backup_dir, f"order_system_backup_{timestamp}.db")

            conn = sqlite3.connect(db_path)
            conn.execute(f"VACUUM INTO '{backup_path}'")
            conn.close()

            size = os.path.getsize(backup_path)
            size_str = f"{size/1024/1024:.2f} MB" if size > 1024*1024 else f"{size/1024:.1f} KB"
            msg = f"数据库备份成功: {backup_path} ({size_str})"
            self._log_to_settings(msg, 'success')
        except Exception as e:
            msg = f"数据库备份失败: {e}"
            self._log_to_settings(msg, 'error')

    def open_settings_window(self):
        """点击设置：在主窗口内切换到「数据库备份与还原」视图，不弹出独立窗口。"""
        if not getattr(self, '_settings_built', False):
            self._build_settings_view(self.settings_view)
            self._settings_built = True
            self._settings_view_open = True
        self.home_view.pack_forget()
        self.settings_view.pack(fill=tk.BOTH, expand=True)
        self._current_view = 'settings'
        self._refresh_nav()

    def _show_home_view(self):
        if getattr(self, '_settings_built', False):
            self.settings_view.pack_forget()
        self.home_view.pack(fill=tk.BOTH, expand=True)
        self._current_view = 'home'
        self._settings_view_open = False
        self._refresh_nav()

    def _refresh_nav(self):
        if getattr(self, 'nav_home', None):
            self.nav_home._redraw(hover=False)
        if getattr(self, 'nav_settings', None):
            self.nav_settings._redraw(hover=False)

    def _build_settings_view(self, parent):
        parent.configure(bg=self.colors['bg'])

        header = tk.Frame(parent, bg=self.colors['bg'])
        header.pack(fill=tk.X, padx=20, pady=(16, 8))
        tk.Label(header, text="数据库备份与还原", font=('微软雅黑', 16, 'bold'),
                 bg=self.colors['bg'], fg=self.colors['text_primary']).pack(anchor=tk.W)
        tk.Label(header, text="管理数据库备份目录、自动备份计划与还原操作",
                 font=('Segoe UI', 9), bg=self.colors['bg'], fg=self.colors['text_secondary']).pack(anchor=tk.W)

        # 内容区：双列网格布局，无右侧滚动条，确保整体在一屏内显示
        content = tk.Frame(parent, bg=self.colors['bg'])
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=8)
        cols = tk.Frame(content, bg=self.colors['bg'])
        cols.pack(fill=tk.BOTH, expand=True)
        left_col = tk.Frame(cols, bg=self.colors['bg'])
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        right_col = tk.Frame(cols, bg=self.colors['bg'])
        right_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))

        # 1. Backup settings
        backup_card = self._create_card(left_col, "备份设置")
        row1 = tk.Frame(backup_card, bg=self.colors['card'])
        row1.pack(fill=tk.X, padx=16, pady=(8, 8))
        tk.Label(row1, text="备份目录:", font=('微软雅黑', 10),
                 bg=self.colors['card'], fg=self.colors['text_primary']).pack(side=tk.LEFT)
        self.settings_backup_dir_var = tk.StringVar(value=self.backup_config.get('backup_dir', ''))
        tk.Label(row1, textvariable=self.settings_backup_dir_var, font=('Segoe UI', 9),
                 bg=self.colors['card'], fg=self.colors['text_secondary'],
                 wraplength=420, justify=tk.LEFT).pack(side=tk.LEFT, padx=(12, 0), fill=tk.X, expand=True)
        self._create_settings_button(row1, "选择目录", self.colors['blue'], self.colors['blue_light'],
                                     self._choose_backup_dir, width=130, height=32, icon='folder')

        row1b = tk.Frame(backup_card, bg=self.colors['card'])
        row1b.pack(fill=tk.X, padx=16, pady=(0, 12))
        self._create_settings_button(row1b, "立即备份", self.colors['green'], self.colors['green_light'],
                                     self._do_backup_now, width=130, height=34, icon='save')

        # 2. Auto backup config
        auto_card = self._create_card(left_col, "自动备份配置", expand=True)
        auto_cfg = self.backup_config.get('auto_backup', {})
        period_labels = {'daily': '每日', 'weekly': '每周', 'monthly': '每月'}
        weekday_labels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

        self.settings_auto_enabled_var = tk.BooleanVar(value=auto_cfg.get('enabled', False))
        self.settings_period_var = tk.StringVar(value=period_labels.get(auto_cfg.get('period', 'daily'), '每日'))
        self.settings_time_var = tk.StringVar(value=auto_cfg.get('time', '02:00'))
        self.settings_weekday_var = tk.StringVar(value=weekday_labels[auto_cfg.get('weekday', 0)])
        self.settings_day_var = tk.IntVar(value=auto_cfg.get('day', 1))

        row2 = tk.Frame(auto_card, bg=self.colors['card'])
        row2.pack(fill=tk.X, padx=16, pady=(8, 8))
        tk.Checkbutton(row2, text="启用自动备份", variable=self.settings_auto_enabled_var,
                       bg=self.colors['card'], fg=self.colors['text_primary'],
                       selectcolor=self.colors['card'], activebackground=self.colors['card'],
                       activeforeground=self.colors['text_primary'], font=('微软雅黑', 10)).pack(side=tk.LEFT)

        row2b = tk.Frame(auto_card, bg=self.colors['card'])
        row2b.pack(fill=tk.X, padx=16, pady=(0, 8))
        tk.Label(row2b, text="周期:", font=('微软雅黑', 10),
                 bg=self.colors['card'], fg=self.colors['text_secondary']).pack(side=tk.LEFT)
        period_combo = ttk.Combobox(row2b, textvariable=self.settings_period_var,
                                    values=list(period_labels.values()), width=10, state='readonly')
        period_combo.pack(side=tk.LEFT, padx=(8, 16))
        period_combo.bind('<<ComboboxSelected>>', lambda e: self._update_settings_ui())
        tk.Label(row2b, text="时间:", font=('微软雅黑', 10),
                 bg=self.colors['card'], fg=self.colors['text_secondary']).pack(side=tk.LEFT)
        time_values = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]
        ttk.Combobox(row2b, textvariable=self.settings_time_var, values=time_values,
                     width=8, state='readonly').pack(side=tk.LEFT, padx=(8, 0))

        self.settings_weekday_row = tk.Frame(auto_card, bg=self.colors['card'])
        tk.Label(self.settings_weekday_row, text="星期:", font=('微软雅黑', 10),
                 bg=self.colors['card'], fg=self.colors['text_secondary']).pack(side=tk.LEFT)
        ttk.Combobox(self.settings_weekday_row, textvariable=self.settings_weekday_var,
                     values=weekday_labels, width=10, state='readonly').pack(side=tk.LEFT, padx=(8, 0))

        self.settings_day_row = tk.Frame(auto_card, bg=self.colors['card'])
        tk.Label(self.settings_day_row, text="日期:", font=('微软雅黑', 10),
                 bg=self.colors['card'], fg=self.colors['text_secondary']).pack(side=tk.LEFT)
        ttk.Combobox(self.settings_day_row, textvariable=self.settings_day_var,
                     values=list(range(1, 32)), width=10, state='readonly').pack(side=tk.LEFT, padx=(8, 0))

        row2c = tk.Frame(auto_card, bg=self.colors['card'])
        row2c.pack(fill=tk.X, padx=16, pady=(0, 12))
        self.settings_next_backup_var = tk.StringVar(value="")
        tk.Label(row2c, textvariable=self.settings_next_backup_var, font=('Segoe UI', 9),
                 bg=self.colors['card'], fg=self.colors['text_secondary']).pack(side=tk.LEFT)
        self._create_settings_button(row2c, "保存设置", self.colors['purple'], '#bc8cff',
                                     self._save_auto_backup_settings, width=130, height=34, icon='save_settings')

        # 3. Restore
        restore_card = self._create_card(right_col, "还原操作")
        row3 = tk.Frame(restore_card, bg=self.colors['card'])
        row3.pack(fill=tk.X, padx=16, pady=(8, 8))
        tk.Label(row3, text="备份文件列表:", font=('微软雅黑', 10),
                 bg=self.colors['card'], fg=self.colors['text_primary']).pack(side=tk.LEFT)
        self._create_settings_button(row3, "刷新列表", self.colors['blue'], self.colors['blue_light'],
                                     self._refresh_backup_list, width=120, height=32, icon='refresh_list')

        row3b = tk.Frame(restore_card, bg=self.colors['card'])
        row3b.pack(fill=tk.BOTH, padx=16, pady=(0, 8), expand=True)
        list_frame = tk.Frame(row3b, bg=self.colors['card'])
        list_frame.pack(fill=tk.BOTH, expand=True)
        self.settings_backup_listbox = tk.Listbox(list_frame, bg=self.colors['log_bg'], fg=self.colors['log_text'],
                                                  selectbackground=self.colors['blue'], font=('Consolas', 10),
                                                  highlightthickness=0, relief=tk.FLAT, height=6)
        self.settings_backup_listbox.pack(fill=tk.BOTH, expand=True)

        row3c = tk.Frame(restore_card, bg=self.colors['card'])
        row3c.pack(fill=tk.X, padx=16, pady=(0, 12))
        self._create_settings_button(row3c, "从文件还原", self.colors['orange'], '#e3b341',
                                     self._do_restore_from_file, width=130, height=34, icon='import')
        self._create_settings_button(row3c, "还原选中备份", self.colors['purple'], '#bc8cff',
                                     self._do_restore, width=130, height=34, icon='restore')

        # 4. Log
        log_card = self._create_card(right_col, "操作日志", expand=True)
        log_frame = tk.Frame(log_card, bg=self.colors['card'])
        log_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(8, 12))
        self.settings_log_text = tk.Text(log_frame, height=6, wrap=tk.WORD, bg=self.colors['log_bg'],
                                         fg=self.colors['log_text'], insertbackground=self.colors['blue'],
                                         font=('Consolas', 9), highlightthickness=0, relief=tk.FLAT)
        self.settings_log_text.pack(fill=tk.BOTH, expand=True)
        self.settings_log_text.tag_config('success', foreground=self.colors['green'])
        self.settings_log_text.tag_config('warning', foreground=self.colors['orange'])
        self.settings_log_text.tag_config('error', foreground=self.colors['red'])
        self.settings_log_text.tag_config('info', foreground=self.colors['log_text'])
        self.settings_log_text.tag_config('system', foreground=self.colors['text_tertiary'])

        self._update_settings_ui()
        self._refresh_backup_list()

    def _create_settings_button(self, parent, text, color, hover_color, command, width=140, height=34, icon=None):
        canvas = tk.Canvas(parent, width=width, height=height, bg=color, highlightthickness=0, cursor='hand2')
        canvas.pack(side=tk.RIGHT, padx=(8, 0))
        canvas._color = color
        canvas._hl = hover_color
        canvas._icon = icon
        canvas._pressed = False
        canvas._hot = False

        def redraw():
            if canvas._pressed:
                bg = self._darken(canvas._color, 0.85)
            elif canvas._hot:
                bg = canvas._hl
            else:
                bg = canvas._color
            canvas.delete('all')
            self._draw_rounded_btn(canvas, width, height, bg, r=8)
            if canvas._icon:
                self._draw_icon(canvas, canvas._icon, 20, height / 2, 16, '#ffffff')
                canvas.create_text(width / 2 + 12, height / 2, text=text,
                                   font=('微软雅黑', 9, 'bold'), fill='white', tags='btn_text')
            else:
                canvas.create_text(width / 2, height / 2, text=text,
                                   font=('微软雅黑', 9, 'bold'), fill='white', tags='btn_text')

        canvas._redraw = redraw
        canvas.bind('<Enter>', lambda e: (setattr(canvas, '_hot', True), redraw()))
        canvas.bind('<Leave>', lambda e: (setattr(canvas, '_hot', False),
                                          setattr(canvas, '_pressed', False), redraw()))
        canvas.bind('<ButtonPress-1>', lambda e: (setattr(canvas, '_pressed', True), redraw()))
        canvas.bind('<ButtonRelease-1>', lambda e: (setattr(canvas, '_pressed', False), redraw(), command()))
        redraw()
        return canvas

    def _update_settings_ui(self, *args):
        if not getattr(self, '_settings_view_open', False):
            return
        period_map = {'每日': 'daily', '每周': 'weekly', '每月': 'monthly'}
        weekday_labels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        period_label = self.settings_period_var.get()
        period = period_map.get(period_label, 'daily')

        if period == 'weekly':
            self.settings_weekday_row.pack(fill=tk.X, padx=16, pady=(0, 8))
            self.settings_day_row.pack_forget()
        elif period == 'monthly':
            self.settings_weekday_row.pack_forget()
            self.settings_day_row.pack(fill=tk.X, padx=16, pady=(0, 8))
        else:
            self.settings_weekday_row.pack_forget()
            self.settings_day_row.pack_forget()

        try:
            cfg_preview = {
                'enabled': self.settings_auto_enabled_var.get(),
                'period': period,
                'time': self.settings_time_var.get(),
                'weekday': weekday_labels.index(self.settings_weekday_var.get()),
                'day': self.settings_day_var.get()
            }
            if cfg_preview['enabled']:
                next_time = self._compute_next_backup_time(cfg_preview)
                self.settings_next_backup_var.set(f"下次备份: {next_time.strftime('%Y-%m-%d %H:%M')}")
            else:
                self.settings_next_backup_var.set("自动备份未启用")
        except Exception:
            self.settings_next_backup_var.set("请检查自动备份设置")

    def _log_to_settings(self, text, level='info'):
        # 子线程调用时切回主线程，避免跨线程操作 Text 控件导致闪退
        if threading.current_thread() is not self._main_thread:
            self.root.after(0, self._log_to_settings, text, level)
            return
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        tag = level if level in ('info', 'success', 'warning', 'error', 'system') else 'info'
        line = f"[{timestamp}] [{tag.upper()}] {text}\n"
        # 同步写入首页「实时日志 - 综合」标签页与「备份」标签页（聚合前端/后端/备份）
        for tw in (getattr(self, 'all_log_text', None), getattr(self, 'backup_log_text', None)):
            if not tw:
                continue
            try:
                tw.config(state=tk.NORMAL)
                tw.insert(tk.END, line, tag)
                tw.config(state=tk.DISABLED)
                tw.see(tk.END)
            except Exception:
                pass
        # 仅当设置界面打开时，额外写入其本地「操作日志」卡片
        if getattr(self, '_settings_view_open', False) and getattr(self, 'settings_log_text', None):
            self.settings_log_text.config(state=tk.NORMAL)
            self.settings_log_text.insert(tk.END, line, tag)
            self.settings_log_text.config(state=tk.DISABLED)
            self.settings_log_text.see(tk.END)

    def _choose_backup_dir(self):
        initial = self.backup_config.get('backup_dir') or os.path.dirname(os.path.abspath(__file__))
        dir_path = filedialog.askdirectory(initialdir=initial, parent=self.root)
        if dir_path:
            self.backup_config['backup_dir'] = dir_path
            self.settings_backup_dir_var.set(dir_path)
            self._save_backup_config()
            self._log_to_settings(f"备份目录已设置为: {dir_path}", 'success')

    def _do_backup_now(self):
        def run():
            self._log_to_settings("开始手动备份...", 'system')
            self._run_backup_task()
            self.root.after(0, self._refresh_backup_list)
        threading.Thread(target=run, daemon=True).start()

    def _refresh_backup_list(self):
        if not getattr(self, '_settings_view_open', False):
            return
        self.settings_backup_listbox.delete(0, tk.END)
        backup_dir = self.backup_config.get('backup_dir', '')
        if not backup_dir or not os.path.exists(backup_dir):
            return
        files = [f for f in os.listdir(backup_dir) if f.endswith('.db')]
        files.sort(reverse=True)
        for f in files:
            fp = os.path.join(backup_dir, f)
            size = os.path.getsize(fp)
            mtime = time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(fp)))
            size_str = f"{size/1024/1024:.2f} MB" if size > 1024*1024 else f"{size/1024:.1f} KB"
            self.settings_backup_listbox.insert(tk.END, f"{f}  |  {size_str}  |  {mtime}")

    def _do_restore(self):
        """从备份列表中选中的文件还原。"""
        selection = self.settings_backup_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个备份文件", parent=self.root)
            return
        item = self.settings_backup_listbox.get(selection[0])
        backup_name = item.split('  |  ')[0].strip()
        backup_dir = self.backup_config.get('backup_dir', '')
        backup_path = os.path.join(backup_dir, backup_name)
        if not messagebox.askyesno("确认还原",
                f"确定要用备份 {backup_name} 还原数据库吗？\n还原将停止后端服务、替换当前数据库，并自动重新启动。",
                parent=self.root):
            return
        threading.Thread(target=lambda: self._run_restore_task(backup_path, backup_name), daemon=True).start()

    def _do_restore_from_file(self):
        """从电脑上任意位置选择 .db 备份文件进行还原。"""
        file_path = filedialog.askopenfilename(
            title="选择要还原的数据库备份文件",
            filetypes=[("SQLite 数据库", "*.db"), ("所有文件", "*.*")],
            parent=self.root)
        if not file_path:
            return
        backup_name = os.path.basename(file_path)
        if not messagebox.askyesno("确认还原",
                f"确定要用备份 {backup_name} 还原数据库吗？\n还原将停止后端服务、替换当前数据库，并自动重新启动。",
                parent=self.root):
            return
        threading.Thread(target=lambda: self._run_restore_task(file_path, backup_name), daemon=True).start()

    def _run_restore_task(self, backup_path, backup_name):
        """还原核心逻辑：停止服务 → 紧急备份当前库 → 替换 → 重启服务。"""
        self._log_to_settings(f"开始还原数据库: {backup_name}", 'system')
        try:
            self._log_to_settings("正在停止后端服务...", 'system')
            self.stop_services()
            time.sleep(2)

            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend', 'data', 'db', 'order_system.db')
            if not os.path.exists(backup_path):
                raise FileNotFoundError(f"备份文件不存在: {backup_path}")

            backup_dir = self.backup_config.get('backup_dir', '')
            emergency = os.path.join(backup_dir, f"order_system_emergency_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
            if os.path.exists(db_path):
                shutil.copy2(db_path, emergency)
                self._log_to_settings(f"当前数据库已紧急备份到: {emergency}", 'system')

            shutil.copy2(backup_path, db_path)
            self._log_to_settings("数据库文件已替换", 'success')

            self._log_to_settings("正在重新启动服务...", 'system')
            self.start_services()
            self._log_to_settings("数据库还原完成，服务已重新启动", 'success')
        except Exception as e:
            self._log_to_settings(f"还原失败: {e}", 'error')

    def _save_auto_backup_settings(self):
        period_map = {'每日': 'daily', '每周': 'weekly', '每月': 'monthly'}
        weekday_labels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        try:
            period_label = self.settings_period_var.get()
            period = period_map.get(period_label, 'daily')
            time_str = self.settings_time_var.get()
            datetime.strptime(time_str, '%H:%M')
            cfg = {
                'enabled': self.settings_auto_enabled_var.get(),
                'period': period,
                'time': time_str,
                'weekday': weekday_labels.index(self.settings_weekday_var.get()),
                'day': int(self.settings_day_var.get())
            }
            self.backup_config['auto_backup'] = cfg
            self._save_backup_config()
            self._start_backup_scheduler()
            self._update_settings_ui()
            self._log_to_settings("自动备份设置已保存", 'success')
        except Exception as e:
            messagebox.showerror("保存失败", f"设置保存失败: {e}", parent=self.root)

    def _on_close(self):
        self.animation_running = False
        self.pulse_running = False
        self._stop_backup_scheduler()
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

    root.configure(bg='#2c3138')

    app = WindowsLauncherApp(root)

    def on_closing():
        app._on_close()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == '__main__':
    main()