# -*- coding: utf-8 -*-
"""
订单管理系统启动器 v3.0（PySide6 重写版）
提供可视化交互界面和实时日志显示。

为什么重写（修复「点最大化出现双份界面堆叠」）：
  旧版用 Tkinter 的 overrideredirect(无边框) + state('zoomed')，这是 Tk/Windows
  合成器的经典坑——最大化时旧画布缓冲不擦除，新旧帧叠加成双份界面。此前用
  Win32 ShowWindow 等 6 种方案均未能彻底消除。
  本版改用 PySide6(Qt)：最大化走 Qt 原生的 showMaximized()/showNormal()，窗口状态
  由系统合成器正确管理，该 bug 从根上消失。无边框窗口也由 Qt 自己绘制，拖拽/
  缩放/任务栏图标均为原生行为，稳定可靠。

功能模块：
  1. 无边框窗口框架（自定义标题栏/拖拽/边缘缩放/最大化/系统托盘）
  2. 左侧侧边栏（logo + 状态/备份/初始 三导航 + 版本号）
  3. 运行监控视图（服务磁贴 + 四通道实时日志 + 启停/打开/刷新按钮）
  4. 备份设置视图（立即备份/自动备份计划/还原/操作日志）
  5. 核心服务管理（依赖检查/启动/停止/自愈看门狗/健康检查）
线程安全：子线程一律通过 Qt 信号槽(emit→slot)更新 UI，绝不跨线程碰控件。
"""

import os
import sys
import socket
import subprocess
import threading
import json
import shutil
import sqlite3
import calendar
import html
import time
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from PySide6.QtCore import (
    Qt, QObject, Signal, QTimer, QSize, QByteArray, QUrl, QPoint, QEvent,
    QPointF, QRectF,
)
from PySide6.QtGui import (
    QIcon, QPixmap, QPainter, QPen, QBrush, QColor, QFont, QAction, QDesktopServices,
    QImage, QMouseEvent, QPaintEvent, QResizeEvent, QTextCursor, QIntValidator,
    QPainterPath, QLinearGradient, QRadialGradient, QFontMetrics,
)
from PySide6.QtWidgets import (
    QApplication, QWidget, QFrame, QLabel, QPushButton, QLineEdit, QComboBox,
    QListWidget, QTextEdit, QCheckBox, QStackedWidget, QSystemTrayIcon, QMenu,
    QMessageBox, QFileDialog, QHBoxLayout, QVBoxLayout, QGridLayout, QSizePolicy,
    QSpacerItem, QDialog, QAbstractItemView,
)
from PySide6.QtSvg import QSvgRenderer

try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

if sys.platform == 'win32':
    CREATE_NO_WINDOW = 0x08000000
else:
    CREATE_NO_WINDOW = 0

# ─────────────────────────────────────────
# 主题色板（苹果浅色风格）
# ─────────────────────────────────────────
BG = '#f5f5f7'
SIDEBAR = '#ececf1'
CARD = '#ffffff'
CARD_BORDER = '#e6e6eb'
DIVIDER = '#e6e6eb'
TEXT = '#1d1d1f'
TEXT2 = '#6e6e73'
TEXT3 = '#a1a1a6'
BLUE = '#007aff'
BLUE_L = '#3399ff'
BLUE_D = '#0062cc'
GREEN = '#34c759'
GREEN_L = '#4cd964'
FONT = "'Microsoft YaHei', 'PingFang SC', 'Helvetica Neue', Arial, sans-serif"
GREEN_D = '#28cd41'
RED = '#ff3b30'
RED_L = '#ff5e52'
RED_D = '#e02e24'
ORANGE = '#ff9500'
PURPLE = '#af52de'
PURPLE_L = '#bf6fd6'

LOG_COLORS = {
    'system': TEXT3, 'backend': '#60a5fa', 'frontend': '#4ade80',
    'error': '#f87171', 'success': '#4ade80', 'warning': '#f59e0b',
    'info': '#60a5fa',
}

BTN_SPEC = {
    'start':   {'color': GREEN, 'hover': GREEN_L, 'press': GREEN_D, 'off': '#d1d1d6'},
    'stop':    {'color': RED,   'hover': RED_L,   'press': RED_D,   'off': '#d1d1d6'},
    'open':    {'color': BLUE,  'hover': BLUE_L,  'press': BLUE_D,  'off': '#d1d1d6'},
    'refresh': {'color': PURPLE,'hover': PURPLE_L,'press': '#9e44cc','off': '#d1d1d6'},
}


# ─────────────────────────────────────────
# 模块级工具函数（与框架无关，原样保留）
# ─────────────────────────────────────────

# ── 系统备份本地接口（供后台「系统备份」页面读取/控制）──
BACKUP_API_PORT = 25998
BACKUP_LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'backend', 'data', 'backup_logs.jsonl')


class BackupHttpHandler(BaseHTTPRequestHandler):
    """仅监听 127.0.0.1 的极简 JSON 接口：/backup/state /backup/run /backup/config。"""
    app_ref = None  # 由 LauncherApp 注入实例引用

    def log_message(self, *args):
        pass

    def _send(self, code, payload):
        data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        app = self.app_ref
        if app is not None and self.path.split('?')[0] == '/backup/state':
            self._send(200, {
                'ok': True,
                'backup_dir': app.backup_config.get('backup_dir', ''),
                'auto_backup': app.backup_config.get('auto_backup', {}),
                'next_backup': app._next_backup_text(),
                'logs': app._load_backup_logs(200),
            })
        else:
            self._send(404, {'ok': False, 'message': 'not found'})

    def do_POST(self):
        app = self.app_ref
        if app is None:
            self._send(503, {'ok': False, 'message': '启动器未就绪'})
            return
        length = int(self.headers.get('Content-Length') or 0)
        raw = self.rfile.read(length) if length else b'{}'
        try:
            data = json.loads(raw or b'{}')
        except Exception:
            data = {}
        path = self.path.split('?')[0]
        if path == '/backup/run':
            app._do_backup_now()
            self._send(200, {'ok': True, 'message': '已开始备份'})
        elif path == '/backup/config':
            ac = data.get('auto_backup')
            if not isinstance(ac, dict):
                self._send(400, {'ok': False, 'message': 'auto_backup 参数缺失'})
                return
            try:
                app._apply_auto_backup_config(ac)
                self._send(200, {'ok': True, 'message': '自动备份设置已保存',
                                 'auto_backup': app.backup_config.get('auto_backup', {})})
            except Exception as e:
                self._send(400, {'ok': False, 'message': f'设置保存失败: {e}'})
        else:
            self._send(404, {'ok': False, 'message': 'not found'})


def is_port_open(port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            return s.connect_ex(('localhost', port)) == 0
    except Exception:
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
    """Windows: kill ALL processes listening on the given port."""
    if sys.platform == 'win32':
        try:
            cmd = (f'for /f "tokens=5" %a in (\'netstat -ano ^| findstr /R '
                   f'":{port}.*LISTENING"\') do @taskkill /F /T /PID %a >nul 2>&1')
            subprocess.run(cmd, shell=True, capture_output=True)
            return True
        except Exception:
            pass
    else:
        try:
            cmd = f"lsof -ti:{port} | xargs kill -9 2>/dev/null"
            subprocess.run(cmd, shell=True, capture_output=True)
            return True
        except Exception:
            pass
    return False


def acquire_single_instance_lock(port=25999):
    """绑定专用本地端口作为单实例进程锁；返回 socket 或 None(已有实例)。"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('127.0.0.1', port))
        sock.listen(1)
        return sock
    except Exception:
        return None


# ─────────────────────────────────────────
# SVG 线性图标（渲染成 QPixmap）
# ─────────────────────────────────────────
_ICON_PATHS = {
    'home': '<path d="M5 11l7-7 7 7" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><path d="M7 10v9h10v-9" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
    'folder': '<path d="M4 7h4l2 2h10v9H4z" fill="none" stroke="{c}" stroke-width="1.8" stroke-linejoin="round"/>',
    'restore': '<circle cx="12" cy="12" r="8" fill="none" stroke="{c}" stroke-width="1.8"/><path d="M12 8v4l3 2" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
    'play': '<path d="M9 7l8 5-8 5z" fill="{c}"/>',
    'stop': '<rect x="8" y="8" width="8" height="8" rx="1.6" fill="{c}"/>',
    'browser': '<rect x="4" y="5" width="16" height="14" rx="2.5" fill="none" stroke="{c}" stroke-width="1.8"/><path d="M4 9h16" stroke="{c}" stroke-width="1.8"/>',
    'refresh': '<path d="M20 11a8 8 0 1 0-2.3 5.6" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round"/><path d="M20 5v6h-6" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
    'server': '<rect x="4" y="5" width="16" height="6" rx="1.5" fill="none" stroke="{c}" stroke-width="1.8"/><rect x="4" y="13" width="16" height="6" rx="1.5" fill="none" stroke="{c}" stroke-width="1.8"/>',
    'window': '<rect x="4" y="5" width="16" height="14" rx="2" fill="none" stroke="{c}" stroke-width="1.8"/>',
    'save': '<path d="M6 4h9l3 3v13H6z" fill="none" stroke="{c}" stroke-width="1.8" stroke-linejoin="round"/><path d="M9 4v5h6V4" fill="none" stroke="{c}" stroke-width="1.8"/>',
    'save_settings': '<path d="M6 4h9l3 3v13H6z" fill="none" stroke="{c}" stroke-width="1.8" stroke-linejoin="round"/><path d="M9 14l2 2 4-4" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
    'import': '<path d="M12 4v9" stroke="{c}" stroke-width="1.8" stroke-linecap="round"/><path d="M9 10l3 3 3-3" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><path d="M5 19h14" stroke="{c}" stroke-width="1.8" stroke-linecap="round"/>',
    'search': '<circle cx="11" cy="11" r="6" fill="none" stroke="{c}" stroke-width="1.8"/><path d="M15.5 15.5L20 20" stroke="{c}" stroke-width="1.8" stroke-linecap="round"/>',
    'grid': '<rect x="5" y="5" width="14" height="14" rx="2" fill="none" stroke="{c}" stroke-width="1.8"/><path d="M12 5v14M5 12h14" stroke="{c}" stroke-width="1.8"/>',
    'settings': '<circle cx="12" cy="12" r="3" fill="none" stroke="{c}" stroke-width="1.8"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1" stroke="{c}" stroke-width="1.6" stroke-linecap="round"/>',
    'minimize': '<rect x="6" y="11" width="12" height="2" rx="1" fill="{c}"/>',
    'maximize': '<rect x="6" y="6" width="12" height="12" rx="1.5" fill="none" stroke="{c}" stroke-width="1.8"/>',
    'restore': '<rect x="6" y="8" width="10" height="10" rx="1.5" fill="none" stroke="{c}" stroke-width="1.8"/><rect x="8" y="6" width="10" height="10" rx="1.5" fill="{c}"/>',
    'close': '<path d="M7 7l10 10M17 7L7 17" stroke="{c}" stroke-width="1.8" stroke-linecap="round"/>',
}


def svg_icon(name, color, size=22):
    inner = _ICON_PATHS.get(name, '<circle cx="12" cy="12" r="6" fill="none" stroke="{c}" stroke-width="1.8"/>').format(c=color)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
           f'viewBox="0 0 24 24">{inner}</svg>')
    renderer = QSvgRenderer(QByteArray(svg.encode('utf-8')))
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    renderer.render(painter)
    painter.end()
    return pix


# ─────────────────────────────────────────
# 信号桥：子线程 → 主线程 UI 更新（线程安全核心）
# ─────────────────────────────────────────
class Bridge(QObject):
    log = Signal(str, str, str)          # text, source, channel
    service = Signal(str, str, str)       # which, word, fg
    progress = Signal(str, int, str)      # which, width(0-180), color
    button = Signal(str, str)             # name(start/stop/open), state(enabled/disabled)
    settingslog = Signal(str, str)        # text, level
    backuplist = Signal()
    uicall = Signal(object)               # callable


# ─────────────────────────────────────────
# 服务磁贴内的仪表（波形 + 进度条，QPainter 绘制）
# ─────────────────────────────────────────
class GaugeWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 0
        self._state = 'off'
        self._color = TEXT3
        self.setMinimumWidth(110)

    def set_progress(self, width, state, color):
        self._progress = max(0, min(180, width))
        self._state = state
        self._color = color
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        bar_c = {'running': GREEN, 'error': ORANGE, 'starting': BLUE, 'off': '#c7c7cc'}.get(self._state, '#c7c7cc')
        # 顶部均衡器波形
        heights = [5, 9, 6, 11, 7, 13, 7, 11, 6, 10, 7, 14, 9, 11, 6, 7, 10, 6, 11, 6, 9, 5]
        bw, gap = 3, 4
        n = min(len(heights), w // (bw + gap))
        x0 = max(0, (w - n * (bw + gap)) // 2)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(bar_c)))
        for i in range(n):
            x = x0 + i * (bw + gap)
            hh = heights[i % len(heights)]
            p.drawRoundedRect(x, (15 - hh) // 2, bw, hh, 1.5, 1.5)
        # 进度轨道
        p.setBrush(QBrush(QColor('#e5e5ea')))
        p.drawRoundedRect(0, 16, w, 6, 3, 3)
        if self._state in ('running', 'error', 'starting') and self._progress > 0:
            fw = int(self._progress / 180 * w)
            p.setBrush(QBrush(QColor(self._color)))
            p.drawRoundedRect(0, 16, fw, 6, 3, 3)
            kx = max(2, min(fw, w - 2))
            p.setBrush(QBrush(QColor('#ffffff')))
            p.drawEllipse(kx - 5, 16, 10, 10)
        p.end()


class ServiceTile(QFrame):
    def __init__(self, name, srv_tag, glyph, accent, parent=None):
        super().__init__(parent)
        self.setObjectName('tile')
        self.glyph = glyph
        self.accent = accent
        self._color = accent
        self._state = 'off'
        root = QHBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(12)

        # 左侧图标
        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(48, 48)
        self._draw_icon()
        root.addWidget(self.icon_lbl, alignment=Qt.AlignVCenter)

        # 中间信息列
        info = QVBoxLayout()
        info.setSpacing(1)
        info.setAlignment(Qt.AlignVCenter)
        if srv_tag:
            self.tag_lbl = QLabel(srv_tag)
            self.tag_lbl.setStyleSheet(f"color:{BLUE}; font: bold 10px {FONT};")
            info.addWidget(self.tag_lbl)
        self.name_lbl = QLabel(name)
        self.name_lbl.setStyleSheet(f"font: bold 14px {FONT}; color:{TEXT};")
        info.addWidget(self.name_lbl)
        self.status_lbl = QLabel("未启动")
        self.status_lbl.setStyleSheet(f"color:{TEXT3}; font: 11px {FONT};")
        info.addWidget(self.status_lbl)
        root.addLayout(info, 1)

    def _draw_icon(self):
        pix = QPixmap(48, 48)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QBrush(QColor('#f2f2f7')))
        p.setPen(QPen(QColor(CARD_BORDER)))
        p.drawRoundedRect(1, 1, 46, 46, 12, 12)
        p.drawPixmap((48 - 26) // 2, (48 - 26) // 2, svg_icon(self.glyph, self._color, 26))
        p.end()
        self.icon_lbl.setPixmap(pix)

    def set_state(self, word, fg):
        self.status_lbl.setText(word)
        self.status_lbl.setStyleSheet(f"color:{fg}; font: 11px {FONT};")

    def set_progress(self, width, state, color):
        # 进度/均衡控件已移除，保留方法以兼容 on_progress 信号连接
        self._color = color


# ─────────────────────────────────────────
# 波浪进度条（绿色流体渐变 + 内部波浪循环 + 左侧圆形滑块 + 右端"运行中"标签）
# ─────────────────────────────────────────
class WaveBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 0        # 0-100
        self._color = GREEN
        self._phase = 0.0
        self._label = ''
        self.setMinimumHeight(22)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # 新增

    def set_progress(self, p, color):
        self._progress = max(0, min(100, p))
        self._color = color
        self.update()

    def set_phase(self, phase):
        self._phase = phase

    def set_label(self, text):
        self._label = text
        self.update()

    def paintEvent(self, e):
        import math
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        r = h / 2

        # 1) 背景轨道（白色胶囊 + 浅灰描边，未运行时显示白色）
        p.setPen(QPen(QColor('#e5e5ea'), 1.2))
        p.setBrush(QBrush(QColor('#ffffff')))
        p.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), r, r)

        # 2) 进度填充（绿色渐变胶囊，直接 drawRoundedRect 画完整圆角矩形，避免手画弧方向错）
        if self._progress > 0:
            base = QColor(self._color)
            fw = int(w * self._progress / 100)
            # 渐变（亮→暗）
            grad = QLinearGradient(0, 0, max(fw, 1), 0)
            grad.setColorAt(0, base.lighter(115))
            grad.setColorAt(1, base.darker(108))
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(grad))
            p.drawRoundedRect(QRectF(0, 0, fw, h), r, r)
            # 3) 波浪（3 条白色半透明 sin 曲线；error 模式按 _phase 闪烁脉动）
            is_alert = self._color in (ORANGE, RED)
            pulse = 0.5 + 0.5 * math.sin(self._phase * 2.0)   # 0~1
            wave_paths = []
            for k, (amp_k, alpha, phase_off, wl_k) in enumerate([
                (h * 0.20, 90, 0.0, 0.55),
                (h * 0.14, 60, 2.2, 0.35),
                (h * 0.10, 40, 4.2, 0.75),
            ]):
                wp = QPainterPath()
                wavelength = max(fw * wl_k, 1)
                step = 3
                first = True
                for x in range(0, fw + 2, step):
                    y = h/2 + amp_k * math.sin(2 * math.pi * x / wavelength + self._phase + phase_off)
                    if first:
                        wp.moveTo(QPointF(x, y))
                        first = False
                    else:
                        wp.lineTo(QPointF(x, y))
                if is_alert:
                    alpha = int(alpha * (0.35 + 0.65 * pulse))
                wave_paths.append((wp, alpha))
            for wp, alpha in wave_paths:
                p.setPen(QPen(QColor(255, 255, 255, alpha), 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                p.setBrush(Qt.NoBrush)
                p.drawPath(wp)

        # 4) 左侧装饰滑块（固定在最左，浅绿白带柔光）
        slide_r = h * 0.36
        sx = slide_r + 4
        sy = h / 2
        # 外圈柔光
        glow = QRadialGradient(sx, sy, slide_r * 1.6)
        glow.setColorAt(0, QColor(255, 255, 255, 200))
        glow.setColorAt(1, QColor(255, 255, 255, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(glow))
        p.drawEllipse(QPointF(sx, sy), slide_r * 1.5, slide_r * 1.5)
        # 滑块本体（浅绿白 #f2ffe9 + 浅绿边框 #e0f8dc）
        p.setBrush(QBrush(QColor('#f2ffe9')))
        p.setPen(QPen(QColor('#e0f8dc'), 1.5))
        p.drawEllipse(QPointF(sx, sy), slide_r, slide_r)
        # 高光（左上）
        hl = QRadialGradient(sx - slide_r * 0.25, sy - slide_r * 0.3, slide_r * 0.9)
        hl.setColorAt(0, QColor(255, 255, 255, 240))
        hl.setColorAt(1, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(hl))
        p.drawEllipse(QPointF(sx, sy), slide_r, slide_r)

        # 5) 右侧嵌入"运行中"标签（半透明白底 + 白色文字，参考 Tkinter stipple 效果）
        if self._label:
            font = QFont()
            font.setFamilies(['Microsoft YaHei', 'PingFang SC', 'Helvetica Neue', 'Arial', 'sans-serif'])
            font.setPointSizeF(8.5)
            font.setBold(True)
            fm = QFontMetrics(font)
            tw = fm.horizontalAdvance(self._label) + 18
            th = h - 10
            tx = w - tw - 6
            ty = (h - th) / 2
            tr = th / 2
            p.setBrush(QBrush(QColor(255, 255, 255, 150)))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(tx, ty, tw, th), tr, tr)
            p.setPen(QPen(QColor('#ffffff')))
            p.setFont(font)
            p.drawText(QRectF(tx, ty, tw, th), Qt.AlignCenter, self._label)

        p.end()


# ─────────────────────────────────────────
# 服务状态卡片（标题 + WaveBar + 底部状态文本）
# ─────────────────────────────────────────
class ServiceStatusCard(QFrame):
    STATE_MAP = {
        GREEN: ('running', 100),
        GREEN_L: ('running', 100),   # 脉冲亮绿 → 仍属正常运行
        BLUE: ('running', 100),      # 启动中合并到"正常运行"
        BLUE_L: ('running', 100),
        ORANGE: ('error', 25),
        RED: ('error', 25),
        TEXT3: ('off', 0),
    }
    LABEL_MAP = {
        'running': '运行中',
        'error':   '异常告警',
        'off':     '已停止',
    }

    def __init__(self, side, parent=None):
        super().__init__(parent)
        self.side = side
        self._state = 'off'
        self._color = TEXT3
        self._progress = 0
        self._phase = 0.0
        self.setObjectName('status_card')
        self.setStyleSheet(
            f"QFrame#status_card{{background:{CARD}; border:1px solid {CARD_BORDER}; border-radius:10px;}}")
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 10, 14, 12)
        v.setSpacing(8)

        # 标题（限宽 2/3，居中）
        title_row = QHBoxLayout()
        title_row.setSpacing(0)
        title_row.setContentsMargins(0, 0, 0, 0)
        title = QLabel("服务状态")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"font: bold 13px {FONT}; color:{TEXT}; background:transparent; border:none;")
        title_row.addWidget(title, 2)
        title_row.addStretch(1)
        v.addLayout(title_row)

        # 进度条：自适应拉伸铺满全宽
        bar_row = QHBoxLayout()
        bar_row.setSpacing(0)
        bar_row.setContentsMargins(0, 0, 0, 0)
        self.bar = WaveBar()
        self.bar.setFixedHeight(30)
        bar_row.addWidget(self.bar)
        v.addLayout(bar_row)

        # 动画定时器（按状态切换频率）
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

    def _on_tick(self):
        if self._state == 'running':
            self._phase = (self._phase + 0.04) % (2 * 3.14159)   # 缓慢波浪
        elif self._state == 'error':
            self._phase = (self._phase + 0.18) % (2 * 3.14159)   # 高频闪烁
        self.bar.set_phase(self._phase)
        self.bar.update()

    def start_anim(self):
        if self._timer.isActive():
            self._timer.stop()
        if self._state == 'running':
            self._timer.start(40)   # 缓慢
        elif self._state == 'error':
            self._timer.start(20)   # 高频

    def stop_anim(self):
        if self._timer.isActive():
            self._timer.stop()

    def set_state(self, word, fg):
        if fg in self.STATE_MAP:
            self._state, self._progress = self.STATE_MAP[fg]
        else:
            self._state, self._progress = 'off', 0
        self._color = fg
        # 标签按规格表固定显示
        self._label_text = self.LABEL_MAP.get(self._state, '已停止')
        self.bar.set_progress(self._progress, self._color)
        self.bar.set_label(self._label_text)
        self.bar.set_phase(self._phase)
        self.bar.update()
        if self._state in ('running', 'error'):
            self.start_anim()
        else:
            self.stop_anim()


# ─────────────────────────────────────────
# 底部动作按钮（图标在上、文字在下）
# ─────────────────────────────────────────
class ActionButton(QWidget):
    def __init__(self, text, icon_name, spec, cmd, parent=None):
        super().__init__(parent)
        self.spec = spec
        self.icon_name = icon_name
        self.cmd = cmd
        self._enabled = False
        self._hover = False
        self._press = False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        lay.setAlignment(Qt.AlignCenter)
        self.icon_lbl = QLabel()
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        self.text_lbl = QLabel(text)
        self.text_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.icon_lbl)
        lay.addWidget(self.text_lbl)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(64)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._render()

    def _bg(self):
        if not self._enabled:
            return self.spec['off']
        if self._press:
            return self.spec['press']
        if self._hover:
            return self.spec['hover']
        return self.spec['color']

    def _fg(self):
        return TEXT

    def _render(self):
        bg = self._bg()
        fg = self._fg()
        self.setStyleSheet(f"background:{bg}; border-radius:11px; border:none;")
        self.icon_lbl.setPixmap(svg_icon(self.icon_name, fg, 26))
        self.text_lbl.setStyleSheet(f"color:{fg}; font: bold 13px {FONT}; background:transparent;")

    def set_enabled(self, e):
        self._enabled = e
        self._render()

    def enterEvent(self, e):
        self._hover = True
        self._render()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self._press = False
        self._render()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self._enabled:
            self._press = True
            self._render()
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        if self._press and self._enabled and e.button() == Qt.LeftButton:
            self._press = False
            self._render()
            self.cmd()
        else:
            self._press = False
            self._render()
        super().mouseReleaseEvent(e)


# ─────────────────────────────────────────
# 侧边栏导航项
# ─────────────────────────────────────────
# 侧边栏导航项
# ─────────────────────────────────────────
class NavItem(QWidget):
    def __init__(self, text, icon_name, cmd, parent=None):
        super().__init__(parent)
        self.text = text
        self.icon_name = icon_name
        self.cmd = cmd
        self._active = False
        self._hover = False
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 12, 0)
        lay.setSpacing(10)
        self.indicator = QFrame()
        self.indicator.setFixedWidth(4)
        self.icon_lbl = QLabel()
        self.text_lbl = QLabel(text)
        self.text_lbl.setStyleSheet(f"font: bold 13px {FONT};")
        lay.addWidget(self.indicator, alignment=Qt.AlignVCenter)
        lay.addWidget(self.icon_lbl)
        lay.addWidget(self.text_lbl)
        lay.addStretch()
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(42)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._render()

    def _render(self):
        if self._active:
            bg, fg, ind = '#e3f2ff', BLUE, BLUE
        elif self._hover:
            bg, fg, ind = '#f2f2f7', TEXT, 'transparent'
        else:
            bg, fg, ind = 'transparent', '#3f4248', 'transparent'
        self.setStyleSheet(f"background:{bg}; border-radius:9px;")
        self.indicator.setStyleSheet(f"background:{ind}; border-radius:1px; border:none;")
        self.indicator.setFixedHeight(18 if self._active else 0)
        self.icon_lbl.setPixmap(svg_icon(self.icon_name, fg, 18))
        self.text_lbl.setStyleSheet(f"color:{fg}; font: bold 13px {FONT}; background:transparent;")

    def set_active(self, a):
        self._active = a
        self._render()

    def set_hover(self, h):
        self._hover = h
        self._render()

    def enterEvent(self, e):
        self.set_hover(True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.set_hover(False)
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.cmd()
        super().mousePressEvent(e)


# ─────────────────────────────────────────
# 自定义标题栏（拖拽 + 最小化/最大化/关闭）
# ─────────────────────────────────────────
class TitleBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent = parent
        self._drag_pos = None
        self.setFixedHeight(40)
        self.setStyleSheet(f"background:{BG}; border: none;")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        title = QLabel("ERP_GO 订单管理系统")
        title.setStyleSheet(f"font: bold 13px {FONT}; color:{TEXT}; padding-left:14px;")
        title.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        lay.addWidget(title, alignment=Qt.AlignVCenter)
        lay.addStretch()
        self._add_btn('minimize', parent._on_minimize)
        self._max_btn = self._add_btn('maximize', parent._on_zoom)
        self._add_btn('close', parent._on_close, close=True)

    def _add_btn(self, icon_name, cmd, close=False):
        btn = QPushButton()
        btn.setFixedSize(44, 36)
        btn.setCursor(Qt.PointingHandCursor)
        hover = RED if close else '#e8e8ed'
        btn.setStyleSheet(
            f"QPushButton{{background:{BG}; border:none;}}"
            f"QPushButton:hover{{background:{hover};}}"
        )
        btn.setIcon(svg_icon(icon_name, TEXT if not close else TEXT, 15))
        btn.clicked.connect(cmd)
        self.layout().addWidget(btn)
        return btn

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            if self._parent.isMaximized():
                self._parent.showNormal()
            self._drag_pos = e.globalPosition().toPoint() - self._parent.pos()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._drag_pos is not None and (e.buttons() & Qt.LeftButton):
            self._parent.move(e.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None
        super().mouseReleaseEvent(e)


# ═══════════════════════════════════════
# 主应用
# ═══════════════════════════════════════
class LauncherApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setMinimumSize(880, 620)
        self.resize(880, 620)
        self.setStyleSheet(f"LauncherApp{{background:{BG}; border:1px solid #c9c9cf;}}")

        self.bridge = Bridge()
        self.bridge.log.connect(self.on_log)
        self.bridge.service.connect(self.on_service)
        self.bridge.progress.connect(self.on_progress)
        self.bridge.button.connect(self.on_button)
        self.bridge.settingslog.connect(self.on_settingslog)
        self.bridge.backuplist.connect(self._refresh_backup_list)
        self.bridge.uicall.connect(lambda fn: fn() if callable(fn) else None)

        # 服务进程与状态
        self.backend_process = None
        self.frontend_process = None
        self.backend_status = "未启动"
        self.frontend_status = "未启动"
        self._start_enabled = True
        self._stop_enabled = False
        self._open_enabled = False
        self._stop_requested = False
        self._starting = False
        self._watchdog_started = False
        self._last_watchdog_restart = 0.0
        self._stop_in_progress = False
        self._zoomed = False

        # 日志存储与渲染状态
        self.log_entries = []  # (ts, tag, text, source, channel)
        self.active_log_tab = 0
        self.log_filter = ""

        # 备份配置
        self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        'backend', 'data', 'launcher_config.json')
        self.backup_config = self._load_backup_config()
        self.backup_scheduler_event = threading.Event()
        self.backup_scheduler_thread = None

        self._current_view = 'home'
        self._settings_built = False
        self._settings_view_open = False

        self._build_ui()
        self.detect_service_status()
        self._start_pulse()
        self._start_backup_scheduler()
        self._start_backup_http_service()
        self._center_window()

    # ── UI 构建 ──
    def _build_ui(self):
        self.setMouseTracking(True)
        main_v = QVBoxLayout(self)
        main_v.setContentsMargins(0, 0, 0, 0)
        main_v.setSpacing(0)

        self.title_bar = TitleBar(self)
        main_v.addWidget(self.title_bar)

        mid = QHBoxLayout()
        mid.setContentsMargins(0, 0, 0, 0)
        mid.setSpacing(0)
        self._build_sidebar()
        mid.addWidget(self.sidebar, 0)
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet(f"background:{BG}; border:none;")
        self._build_home()
        self.settings_page = QWidget()
        self.content_stack.addWidget(self.home_page)
        self.content_stack.addWidget(self.settings_page)
        mid.addWidget(self.content_stack, 1)
        main_v.addLayout(mid, 1)

        self._build_bottom_row()
        main_v.addWidget(self.bottom_row)

    def _build_sidebar(self):
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(170)
        self.sidebar.setStyleSheet(f"background:{SIDEBAR}; border:none;")
        v = QVBoxLayout(self.sidebar)
        v.setContentsMargins(12, 14, 12, 10)
        v.setSpacing(6)

        # Logo 区
        logo_frame = QHBoxLayout()
        logo_frame.setSpacing(6)
        logo_lbl = QLabel()
        logo_lbl.setFixedSize(34, 34)
        pm = QPixmap(34, 34)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        logo_path = Path(__file__).resolve().parent / "frontend" / "src" / "assets" / "img" / "logo.png"
        if logo_path.exists():
            p.drawPixmap(0, 0, QPixmap(str(logo_path)).scaled(34, 34, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            p.setBrush(QBrush(QColor(GREEN)))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(1, 1, 32, 32, 8, 8)
            p.drawText(pm.rect(), Qt.AlignCenter, "ERP")
        p.end()
        logo_lbl.setPixmap(pm)
        logo_frame.addWidget(logo_lbl)
        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        t1 = QLabel("牛蛙产销协同")
        t1.setStyleSheet(f"font: bold 14px {FONT}; color:{TEXT};")
        t2 = QLabel("启动器")
        t2.setStyleSheet(f"font: 10px {FONT}; color:{TEXT3};")
        title_col.addWidget(t1)
        title_col.addWidget(t2)
        logo_frame.addLayout(title_col)
        logo_frame.addStretch()
        v.addLayout(logo_frame)
        v.addSpacing(14)

        def section(text):
            lbl = QLabel(text)
            lbl.setStyleSheet(f"font: bold 10px {FONT}; color:{TEXT3}; padding-left:3px;")
            return lbl

        v.addWidget(section("运行监控"))
        v.addSpacing(2)
        self.nav_home = NavItem('状态', 'home', self._show_home_view, self.sidebar)
        v.addWidget(self.nav_home)
        v.addStretch()

        self.nav_settings = NavItem('备份', 'folder', self.open_settings, self.sidebar)
        v.addWidget(self.nav_settings)

        v.addSpacing(8)
        ver = QLabel('v3.0')
        ver.setStyleSheet(f"font: 10px 'Segoe UI'; color:#5c6068; padding-left:3px;")
        v.addWidget(ver, alignment=Qt.AlignLeft)
        self._refresh_nav()

    def _build_home(self):
        self.home_page = QWidget()
        self.home_page.setStyleSheet(f"background:{BG};")
        root = QVBoxLayout(self.home_page)
        root.setContentsMargins(18, 14, 18, 12)
        root.setSpacing(0)

        # 顶栏品牌 + 系统状态
        header = QHBoxLayout()
        brand = QHBoxLayout()
        brand.setSpacing(9)
        bicon = QLabel()
        bicon.setFixedSize(26, 26)
        bp = QPixmap(26, 26)
        bp.fill(Qt.transparent)
        pp = QPainter(bp)
        pp.setRenderHint(QPainter.Antialiasing)
        pp.setBrush(QBrush(QColor(BLUE)))
        pp.setPen(Qt.NoPen)
        pp.drawRoundedRect(1, 1, 24, 24, 8, 8)
        pp.drawText(bp.rect(), Qt.AlignCenter, "G")
        pp.end()
        bicon.setPixmap(bp)
        brand.addWidget(bicon)
        b1 = QLabel("ERP_GO 订单管理系统")
        b1.setStyleSheet(f"font: bold 14px {FONT}; color:{TEXT};")
        b2 = QLabel("控制台")
        b2.setStyleSheet(f"font: 11px {FONT}; color:{TEXT2};")
        brand.addWidget(b1)
        brand.addWidget(b2)
        header.addLayout(brand)
        header.addStretch()
        self.hdr_backend_lbl = QLabel("后端 8000")
        self.hdr_backend_lbl.setStyleSheet(f"font: 11px {FONT}; color:{TEXT3};")
        self.hdr_frontend_lbl = QLabel("前端 5173")
        self.hdr_frontend_lbl.setStyleSheet(f"font: 11px {FONT}; color:{TEXT3};")
        header.addWidget(self.hdr_backend_lbl)
        header.addSpacing(8)
        header.addWidget(self.hdr_frontend_lbl)
        root.addLayout(header)

        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background:{DIVIDER}; border:none;")
        root.addSpacing(10)
        root.addWidget(line)
        root.addSpacing(10)

        content = QHBoxLayout()
        content.setSpacing(12)
        content.setContentsMargins(0, 0, 0, 0)
        left_card, left_body = self._make_card("服务概览")
        right_card, right_body = self._make_card("实时日志")
        content.addWidget(left_card, 1)
        content.addWidget(right_card, 2)
        root.addLayout(content, 1)

        # 服务磁贴
        self.backend_tile = ServiceTile("后端接口服务", "SRV-01 · API", "server", GREEN)
        self.frontend_tile = ServiceTile("前端网页客户端", "SRV-02 · WEB", "window", BLUE)
        self.backend_status_card = ServiceStatusCard('backend')
        self.frontend_status_card = ServiceStatusCard('frontend')
        left_body.addWidget(self.backend_tile)
        left_body.addSpacing(8)
        left_body.addWidget(self.backend_status_card)
        left_body.addSpacing(12)
        left_body.addWidget(self.frontend_tile)
        left_body.addSpacing(8)
        left_body.addWidget(self.frontend_status_card)
        left_body.addStretch()

        # 实时日志：页签 + 搜索 + 4 通道
        tab_row = QHBoxLayout()
        tab_row.setSpacing(6)
        self.tab_buttons = []
        tab_specs = [("综合", "grid"), ("前端", "window"), ("后端", "server"), ("备份", "save")]
        for i, (t, ic) in enumerate(tab_specs):
            btn = QPushButton(t)
            btn.setMinimumSize(50, 28)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=i: self._switch_tab(idx))
            self.tab_buttons.append(btn)
            tab_row.addWidget(btn, 1)
        self._style_tab(0)
        right_body.addLayout(tab_row)

        search_row = QHBoxLayout()
        search_row.setSpacing(7)
        self.log_search = QLineEdit()
        self.log_search.setPlaceholderText("检索日志")
        self.log_search.setStyleSheet(
            f"QLineEdit{{background:{CARD}; border:1px solid {CARD_BORDER}; border-radius:6px; "
            f"padding:3px 9px; font:11px {FONT}; color:{TEXT2};}}")
        self.log_search.textChanged.connect(self._on_filter_changed)
        search_btn = QPushButton()
        search_btn.setFixedSize(48, 26)
        search_btn.setCursor(Qt.PointingHandCursor)
        search_btn.setIcon(svg_icon('search', TEXT2, 14))
        search_btn.setStyleSheet(f"QPushButton{{background:{CARD}; border:1px solid {CARD_BORDER}; border-radius:6px;}}")
        search_btn.clicked.connect(lambda: self._apply_filter(self.log_search.text()))
        search_row.addWidget(self.log_search, 1)
        search_row.addWidget(search_btn)
        right_body.addLayout(search_row)

        log_area = QHBoxLayout()
        log_area.setContentsMargins(0, 0, 0, 0)
        self.log_stack = QStackedWidget()
        self.all_log = QTextEdit()
        self.frontend_log = QTextEdit()
        self.backend_log = QTextEdit()
        self.backup_log = QTextEdit()
        for w in (self.all_log, self.frontend_log, self.backend_log, self.backup_log):
            w.setReadOnly(True)
            w.setStyleSheet(
                f"QTextEdit{{background:{CARD}; border:1px solid {CARD_BORDER}; border-radius:7px; "
                f"font:9pt Consolas; color:{TEXT}; padding:6px;}}")
            self.log_stack.addWidget(w)
        log_area.addWidget(self.log_stack, 1)
        right_body.addLayout(log_area, 1)

    def _make_card(self, title):
        card = QFrame()
        card.setObjectName('card')
        v = QVBoxLayout(card)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        t = QLabel(title)
        t.setStyleSheet(f"font: bold 12px {FONT}; color:{TEXT}; padding:10px 11px 4px 11px;")
        v.addWidget(t)
        body = QWidget()
        bv = QVBoxLayout(body)
        bv.setContentsMargins(11, 0, 11, 10)
        bv.setSpacing(7)
        v.addWidget(body, 1)
        return card, bv

    def _build_bottom_row(self):
        self.bottom_row = QWidget()
        self.bottom_row.setStyleSheet(f"background:{BG};")
        self.bottom_row.setFixedHeight(86)
        v = QVBoxLayout(self.bottom_row)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background:{DIVIDER}; border:none;")
        v.addWidget(line)
        lay = QHBoxLayout()
        lay.setContentsMargins(16, 10, 16, 12)
        lay.setSpacing(10)
        self.start_btn = ActionButton("启动系统", "play", BTN_SPEC['start'], self.start_services)
        self.stop_btn = ActionButton("停止系统", "stop", BTN_SPEC['stop'], self.stop_services)
        self.open_btn = ActionButton("打开页面", "browser", BTN_SPEC['open'], self.open_browser)
        self.refresh_btn = ActionButton("刷新状态", "refresh", BTN_SPEC['refresh'], self.refresh_status)
        for b in (self.start_btn, self.stop_btn, self.open_btn, self.refresh_btn):
            lay.addWidget(b, 1)
        v.addLayout(lay)
        self._set_button_state(start='enabled', stop='disabled', open='disabled')

    # ── 日志渲染 ──
    def _log_predicate(self, idx, entry):
        ts, tag, text, source, channel = entry
        if idx == 0:
            return True
        if idx == 1:
            return source == 'frontend'
        if idx == 2:
            return source == 'backend'
        if idx == 3:
            return channel == 'backup'
        return False

    def _append_log_line(self, qte, ts, tag, text, color):
        qte.moveCursor(QTextCursor.End)
        qte.insertHtml(
            f'<span style="color:{color}">[{html.escape(ts)}] [{html.escape(tag.upper())}] '
            f'{html.escape(text)}</span><br>')

    def on_log(self, text, source='system', channel=None):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        tag = source if source in LOG_COLORS else 'info'
        entry = (timestamp, tag, text, source, channel)
        self.log_entries.append(entry)
        if len(self.log_entries) > 1500:
            self.log_entries.pop(0)
        qtes = [self.all_log, self.frontend_log, self.backend_log, self.backup_log]
        flt = self.log_filter.lower()
        for idx, qte in enumerate(qtes):
            if self._log_predicate(idx, entry) and (not flt or flt in text.lower()):
                self._append_log_line(qte, timestamp, tag, text, LOG_COLORS.get(tag, TEXT))

    def _rebuild_logs(self):
        qtes = [self.all_log, self.frontend_log, self.backend_log, self.backup_log]
        for qte in qtes:
            qte.clear()
        flt = self.log_filter.lower()
        for entry in self.log_entries:
            ts, tag, text, source, channel = entry
            for idx, qte in enumerate(qtes):
                if self._log_predicate(idx, entry) and (not flt or flt in text.lower()):
                    self._append_log_line(qte, ts, tag, text, LOG_COLORS.get(tag, TEXT))

    def _switch_tab(self, index):
        if index == self.active_log_tab:
            return
        self.active_log_tab = index
        self._style_tab(index)
        self.log_stack.setCurrentIndex(index)

    def _style_tab(self, active):
        for i, btn in enumerate(self.tab_buttons):
            if i == active:
                bg, fg = CARD, TEXT
            else:
                bg, fg = '#f0f0f3', '#8e8e93'
            btn.setStyleSheet(
                f"QPushButton{{background:{bg}; color:{fg}; border:none; border-radius:7px; "
                f"font: bold 11px {FONT};}}")

    def _on_filter_changed(self, text):
        self.log_filter = text.strip()
        self._rebuild_logs()

    def _apply_filter(self, text):
        self.log_filter = text.strip()
        self._rebuild_logs()

    # ── 服务状态 / 进度（信号槽）──
    def on_service(self, which, word, fg):
        tile = self.backend_tile if which == 'backend' else self.frontend_tile
        card = self.backend_status_card if which == 'backend' else self.frontend_status_card
        tile.set_state(word, fg)
        card.set_state(word, fg)
        hdr = self.hdr_backend_lbl if which == 'backend' else self.hdr_frontend_lbl
        hdr.setStyleSheet(f"font: 12px {FONT}; color:{fg};")
        if which == 'backend':
            self.backend_status = word
        else:
            self.frontend_status = word

    def on_progress(self, which, width, color):
        tile = self.backend_tile if which == 'backend' else self.frontend_tile
        if color == GREEN:
            state = 'running'
        elif color == ORANGE:
            state = 'error'
        elif color == BLUE:
            state = 'starting'
        else:
            state = 'off'
        tile.set_progress(width, state, color)

    def on_button(self, name, state):
        btn = {'start': self.start_btn, 'stop': self.stop_btn, 'open': self.open_btn}.get(name)
        if btn:
            btn.set_enabled(state == 'enabled')

    def _ui_set_service(self, which, word, fg):
        self.bridge.service.emit(which, word, fg)

    def _update_progress(self, which, width, color):
        self.bridge.progress.emit(which, width, color)

    def _set_button_state(self, start='enabled', stop='disabled', open='disabled'):
        self.start_btn.set_enabled(start == 'enabled')
        self.stop_btn.set_enabled(stop == 'enabled')
        self.open_btn.set_enabled(open == 'enabled')
        # 刷新状态按钮始终可用（修复：原代码从未启用它，导致点击无任何反馈）
        self.refresh_btn.set_enabled(True)
        self.bridge.button.emit('start', start)
        self.bridge.button.emit('stop', stop)
        self.bridge.button.emit('open', open)

    def add_log(self, text, source='system', level='info', channel=None):
        self.bridge.log.emit(text, source, channel)

    def _log_backup(self, text, level='info'):
        self.add_log(text, level, channel='backup')
        self.bridge.settingslog.emit(text, level)
        self._append_backup_log_file(text, level)

    # ── 脉冲动画（状态点闪烁）──
    def _start_pulse(self):
        self._pulse_on = False
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse_tick)
        self._pulse_timer.start(800)

    def _pulse_tick(self):
        self._pulse_on = not self._pulse_on
        for which in ('backend', 'frontend'):
            tile = self.backend_tile if which == 'backend' else self.frontend_tile
            card = self.backend_status_card if which == 'backend' else self.frontend_status_card
            word = self.backend_status if which == 'backend' else self.frontend_status
            if word == '运行中':
                color = GREEN_L if self._pulse_on else GREEN
                tile.set_state(word, color)
                card.set_state(word, color)
            elif word == '启动中...':
                color = BLUE_L if self._pulse_on else BLUE
                tile.set_state(word, color)
                card.set_state(word, color)

    # ── 服务状态检测 ──
    def detect_service_status(self):
        self.add_log("正在检测服务状态...", 'system')
        backend_open = is_port_open(8000)
        frontend_open = is_port_open(5173)
        if backend_open:
            if is_service_healthy('http://localhost:8000/health'):
                self._ui_set_service('backend', "运行中", GREEN)
                self._update_progress('backend', 180, GREEN)
                self.add_log("检测到后端服务健康运行中", 'success')
            else:
                self._ui_set_service('backend', "异常-端口占用", ORANGE)
                self._update_progress('backend', 100, ORANGE)
                self.add_log("警告: 8000端口已占用但后端无响应，建议重启", 'warning')
        else:
            self._ui_set_service('backend', "未启动", TEXT3)
            self._update_progress('backend', 0, TEXT3)
        if frontend_open:
            if is_service_healthy('http://localhost:5173'):
                self._ui_set_service('frontend', "运行中", GREEN)
                self._update_progress('frontend', 180, GREEN)
                self.add_log("检测到前端服务健康运行中", 'success')
            else:
                self._ui_set_service('frontend', "异常-端口占用", ORANGE)
                self._update_progress('frontend', 100, ORANGE)
                self.add_log("警告: 5173端口已占用但前端无响应，建议重启", 'warning')
        else:
            self._ui_set_service('frontend', "未启动", TEXT3)
            self._update_progress('frontend', 0, TEXT3)
        if backend_open or frontend_open:
            self._set_button_state(start='enabled', stop='enabled', open='enabled')
        else:
            self._set_button_state(start='enabled', stop='disabled', open='disabled')
        self.add_log("检测完成", 'system')

    def refresh_status(self):
        self.add_log("正在刷新服务状态...", 'system')
        backend_open = is_port_open(8000)
        if backend_open:
            if is_service_healthy('http://localhost:8000/health'):
                self._ui_set_service('backend', "运行中", GREEN)
                self._update_progress('backend', 180, GREEN)
                self.backend_status = "运行中"
                self.add_log("后端服务: 健康运行 (端口 8000)", 'success')
            else:
                self._ui_set_service('backend', "异常", ORANGE)
                self._update_progress('backend', 100, ORANGE)
                self.backend_status = "异常"
                self.add_log("后端服务: 端口已占用但无响应，可能存在进程残留，请重启", 'warning')
        else:
            self._ui_set_service('backend', "未启动", TEXT3)
            self._update_progress('backend', 0, TEXT3)
            self.backend_status = "未启动"
            self.add_log("后端服务: 未启动 (端口 8000)", 'warning')
        frontend_open = is_port_open(5173)
        if frontend_open:
            if is_service_healthy('http://localhost:5173'):
                self._ui_set_service('frontend', "运行中", GREEN)
                self._update_progress('frontend', 180, GREEN)
                self.frontend_status = "运行中"
                self.add_log("前端服务: 健康运行 (端口 5173)", 'success')
            else:
                self._ui_set_service('frontend', "异常", ORANGE)
                self._update_progress('frontend', 100, ORANGE)
                self.frontend_status = "异常"
                self.add_log("前端服务: 端口已占用但无响应，可能存在进程残留，请重启", 'warning')
        else:
            self._ui_set_service('frontend', "未启动", TEXT3)
            self._update_progress('frontend', 0, TEXT3)
            self.frontend_status = "未启动"
            self.add_log("前端服务: 未启动 (端口 5173)", 'warning')
        if backend_open or frontend_open:
            self._set_button_state(start='enabled', stop='enabled', open='enabled')
        else:
            self._set_button_state(start='enabled', stop='disabled', open='disabled')
        # 汇总一行显示到「综合」页签，并自动切换过去，便于一眼看到全部服务状态
        summary = f"▍后端={self.backend_status} ｜ 前端={self.frontend_status}"
        self.add_log(summary, 'system')
        self._switch_tab(0)
        self.add_log("状态刷新完成", 'system')

    # ── 服务进程管理（与旧版逻辑一致）──
    def check_python_version(self):
        v = sys.version_info
        if v.major < 3 or (v.major == 3 and v.minor < 10):
            self.add_log(f"Python版本要求3.10+，当前版本{v.major}.{v.minor}", 'error')
            return False
        self.add_log(f"Python版本: {v.major}.{v.minor}.{v.micro}", 'success')
        return True

    def install_backend_deps(self):
        backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
        req = os.path.join(backend_dir, 'requirements.txt')
        if not os.path.exists(req):
            self.add_log("requirements.txt 不存在", 'error')
            return False
        REQUIRED = [('fastapi', 'FastAPI 框架'), ('uvicorn', 'ASGI 服务器'),
                    ('sqlalchemy', 'ORM 数据库'), ('aiosqlite', '异步 SQLite 驱动'),
                    ('jose', 'JWT 令牌处理'), ('passlib', '密码哈希库'),
                    ('multipart', '多部分表单解析 (OAuth2 登录必需)'), ('pydantic', '数据验证')]
        missing = []
        for module, desc in REQUIRED:
            try:
                __import__(module)
            except ImportError:
                missing.append(f'{desc} ({module})')
        if not missing:
            self.add_log(f"后端依赖已安装 (全部 {len(REQUIRED)} 项检查通过)", 'success')
            return True
        self.add_log(f"检测到 {len(missing)} 项依赖缺失:", 'warning')
        for m in missing:
            self.add_log(f"  - {m}", 'warning')
        self.add_log("正在安装后端依赖...", 'system')
        self.add_log("pip install -r requirements.txt (使用清华镜像加速)", 'system')
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt',
                 '-i', 'https://pypi.tuna.tsinghua.edu.cn/simple'],
                cwd=backend_dir, capture_output=True, text=True, timeout=300)
        except Exception as e:
            self.add_log(f"后端依赖安装异常: {e}", 'error')
            return False
        if result.returncode != 0:
            self.add_log("后端依赖安装失败", 'error')
            self.add_log(result.stderr[-500:], 'error')
            return False
        self.add_log("后端依赖安装完成", 'success')
        return True

    def install_frontend_deps(self):
        frontend_dir = os.path.join(os.path.dirname(__file__), 'frontend')
        node_modules = os.path.join(frontend_dir, 'node_modules')
        if os.path.exists(node_modules):
            self.add_log("前端依赖已安装", 'success')
            return True
        self.add_log("正在安装前端依赖...")
        result = subprocess.run(['cmd', '/c', 'npm', 'install'], capture_output=True,
                                text=True, cwd=frontend_dir)
        if result.returncode != 0:
            self.add_log("前端依赖安装失败", 'error')
            self.add_log(result.stderr, 'error')
            return False
        self.add_log("前端依赖安装完成", 'success')
        return True

    def ensure_directories(self):
        backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
        data_dir = os.path.join(backend_dir, 'data')
        dirs = [('db', '数据库目录'), ('images', '图片存储目录'),
                ('images/temp', '临时图片目录'), ('images/official', '正式图片目录'),
                ('logs', '日志目录'), ('backup', '备份目录'), ('qr_codes', '二维码缓存目录')]
        created = 0
        for sub, name in dirs:
            p = os.path.join(data_dir, sub)
            if not os.path.exists(p):
                try:
                    os.makedirs(p, exist_ok=True)
                    self.add_log(f"创建目录: {name}", 'success')
                    created += 1
                except Exception as e:
                    self.add_log(f"创建目录失败 {name}: {e}", 'error')
                    return False
        if created == 0:
            self.add_log("所有目录已存在", 'success')
        return True

    def check_database(self):
        db_path = os.path.join(os.path.dirname(__file__), 'backend', 'data', 'db', 'order_system.db')
        if os.path.exists(db_path):
            self.add_log(f"数据库已存在 ({os.path.getsize(db_path)/1024:.1f} KB)", 'success')
        else:
            self.add_log("警告: 数据库文件不存在!", 'warning')
            self.add_log("请先运行 '数据库初始化.py' 创建数据库", 'warning')

    def wait_for_port(self, port, timeout=60):
        start = time.time()
        while time.time() - start < timeout:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    if s.connect_ex(('localhost', port)) == 0:
                        return True
            except Exception:
                pass
            elapsed = time.time() - start
            prog = min(180, int(elapsed / timeout * 180))
            if port == 8000:
                self._update_progress('backend', prog, BLUE)
            else:
                self._update_progress('frontend', prog, BLUE)
            time.sleep(0.5)
        return False

    def _is_alive(self, proc):
        if not proc:
            return False
        try:
            return proc.poll() is None
        except Exception:
            return False

    def kill_own_process(self, proc):
        if not proc:
            return
        try:
            pid = proc.pid
            if sys.platform == 'win32':
                subprocess.run(f'taskkill /F /T /PID {pid} >nul 2>&1', shell=True, capture_output=True)
            else:
                try:
                    os.kill(pid, signal.SIGTERM)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            proc.wait(timeout=3)
        except Exception:
            pass

    def _start_backend(self):
        backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
        proc = subprocess.Popen(
            [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000'],
            cwd=backend_dir, creationflags=CREATE_NO_WINDOW,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.read_process_output(proc, 'backend')
        return proc

    def _health_watchdog(self):
        import time as _time
        fail_count = 0
        DEADLOCK_THRESHOLD = 12
        self._last_watchdog_restart = 0.0
        while True:
            _time.sleep(15)
            if getattr(self, '_stop_requested', False):
                fail_count = 0
                continue
            if getattr(self, '_starting', False):
                fail_count = 0
                continue
            try:
                if not is_port_open(8000):
                    now = _time.time()
                    if now - getattr(self, '_last_watchdog_restart', 0.0) < 30:
                        continue
                    self._last_watchdog_restart = now
                    self.bridge.log.emit("看门狗：8000 端口未监听，正在自动重启后端", 'backend')
                    self.backend_process = self._start_backend()
                    fail_count = 0
                    continue
                if is_service_healthy('http://localhost:8000/health', timeout=8):
                    fail_count = 0
                else:
                    fail_count += 1
                    self.bridge.log.emit(
                        f"看门狗：/health 超时（后端繁忙？{fail_count}/{DEADLOCK_THRESHOLD}），仅观察不重启", 'backend')
                    if fail_count >= DEADLOCK_THRESHOLD:
                        if self._is_alive(self.backend_process):
                            self.bridge.log.emit("看门狗：后端疑似死锁（连续超时约 3 分钟），正在重启", 'backend_err')
                            self.kill_own_process(self.backend_process)
                            _time.sleep(2)
                            self.backend_process = self._start_backend()
                        else:
                            self.bridge.log.emit("看门狗：8000 端口进程非本启动器管理，跳过自动重启", 'backend_err')
                        fail_count = 0
            except Exception as e:
                self.bridge.log.emit(f"看门狗异常: {e}", 'backend_err')

    def start_services(self):
        self._set_button_state(start='disabled')
        self._update_progress('backend', 0, TEXT3)
        self._update_progress('frontend', 0, TEXT3)
        self.add_log("开始启动系统...", 'system')

        def run_start():
            self._starting = True
            try:
                if not self.check_python_version():
                    self._set_button_state(start='enabled')
                    return
                if not self.install_backend_deps():
                    self._set_button_state(start='enabled')
                    return
                if not self.install_frontend_deps():
                    self._set_button_state(start='enabled')
                    return
                if not self.ensure_directories():
                    self._set_button_state(start='enabled')
                    return
                self.check_database()
                self.kill_own_process(getattr(self, 'backend_process', None))
                self.backend_process = None
                self.kill_own_process(getattr(self, 'frontend_process', None))
                self.frontend_process = None
                time.sleep(1)
                self._stop_requested = False
                if not getattr(self, '_watchdog_started', False):
                    threading.Thread(target=self._health_watchdog, daemon=True).start()
                    self._watchdog_started = True

                external_backend = is_port_open(8000) and is_service_healthy('http://localhost:8000/health', timeout=3)
                if external_backend:
                    self.add_log("复用外部已运行的后端服务 (端口:8000)，本启动器不再重复启动", 'success')
                    self._ui_set_service('backend', "运行中", GREEN)
                    self._update_progress('backend', 180, GREEN)
                else:
                    if is_port_open(8000):
                        self.add_log("8000 端口被占用但无 HTTP 响应，可能是外部异常进程，请手动停止后重试", 'warning')
                    self.add_log("正在启动后端服务...", 'system')
                    self._ui_set_service('backend', "启动中...", BLUE)
                    self._update_progress('backend', 0, TEXT3)
                    self.backend_process = self._start_backend()
                    if self.wait_for_port(8000):
                        self._update_progress('backend', 180, GREEN)
                        if is_service_healthy('http://localhost:8000/health', timeout=3):
                            self.add_log("后端服务启动成功并健康就绪 (端口:8000)", 'success')
                            self._ui_set_service('backend', "运行中", GREEN)
                        else:
                            self.add_log("后端端口已开放但 HTTP 服务未就绪，继续等待...", 'warning')
                            time.sleep(2)
                            if is_service_healthy('http://localhost:8000/health', timeout=5):
                                self.add_log("后端服务最终就绪 (端口:8000)", 'success')
                                self._ui_set_service('backend', "运行中", GREEN)
                            else:
                                self.add_log("后端服务可能异常，请检查后端控制台日志", 'error')
                                self._ui_set_service('backend', "异常", ORANGE)
                    else:
                        self._update_progress('backend', 180, ORANGE)
                        self.add_log("后端服务启动超时，可能仍在启动中...", 'warning')
                        self._ui_set_service('backend', "运行中", GREEN)

                external_frontend = is_port_open(5173) and is_service_healthy('http://localhost:5173', timeout=3)
                if external_frontend:
                    self.add_log("复用外部已运行的前端服务 (端口:5173)，本启动器不再重复启动", 'success')
                    self._ui_set_service('frontend', "运行中", GREEN)
                    self._update_progress('frontend', 180, GREEN)
                else:
                    if is_port_open(5173):
                        self.add_log("5173 端口被占用但无 HTTP 响应，可能是外部异常进程，请手动停止后重试", 'warning')
                    self.add_log("正在启动前端服务...", 'system')
                    self._ui_set_service('frontend', "启动中...", BLUE)
                    self._update_progress('frontend', 0, TEXT3)
                    frontend_dir = os.path.join(os.path.dirname(__file__), 'frontend')
                    self.frontend_process = subprocess.Popen(
                        ['cmd', '/c', 'npm', 'run', 'dev'], cwd=frontend_dir,
                        creationflags=CREATE_NO_WINDOW, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    self.read_process_output(self.frontend_process, 'frontend')
                    if self.wait_for_port(5173):
                        self._update_progress('frontend', 180, GREEN)
                        if is_service_healthy('http://localhost:5173', timeout=3):
                            self.add_log("前端服务启动成功并健康就绪 (端口:5173)", 'success')
                            self._ui_set_service('frontend', "运行中", GREEN)
                        else:
                            self.add_log("前端端口已开放但 HTTP 服务未就绪，继续等待...", 'warning')
                            time.sleep(2)
                            if is_service_healthy('http://localhost:5173', timeout=5):
                                self.add_log("前端服务最终就绪 (端口:5173)", 'success')
                                self._ui_set_service('frontend', "运行中", GREEN)
                            else:
                                self.add_log("前端服务可能异常，请检查前端控制台日志", 'error')
                                self._ui_set_service('frontend', "异常", ORANGE)
                    else:
                        self._update_progress('frontend', 180, ORANGE)
                        self.add_log("前端服务启动超时，可能仍在启动中...", 'warning')
                        self._ui_set_service('frontend', "运行中", GREEN)

                self.add_log("所有服务启动完成", 'success')
                self._set_button_state(start='enabled', stop='enabled', open='enabled')
                time.sleep(2)
                self.bridge.uicall.emit(self.open_browser)
            finally:
                self._starting = False

        threading.Thread(target=run_start, daemon=True).start()

    def stop_services(self):
        if getattr(self, '_stop_in_progress', False):
            return
        self._stop_in_progress = True
        threading.Thread(target=self._stop_services_impl, daemon=True).start()

    def _stop_services_impl(self):
        self.add_log("正在停止服务...", 'system')
        self._stop_requested = True
        self.kill_own_process(getattr(self, 'backend_process', None))
        self.kill_own_process(getattr(self, 'frontend_process', None))
        time.sleep(1.2)
        kill_process_on_port(8000)
        kill_process_on_port(5173)
        time.sleep(1.5)
        if is_port_open(8000):
            self.add_log("后端端口 8000 仍被占用（可能有进程拒绝终止），请手动检查", 'warning')
        else:
            self.add_log("后端服务已停止", 'success')
            self._ui_set_service('backend', "未启动", TEXT3)
            self._update_progress('backend', 0, TEXT3)
        if is_port_open(5173):
            self.add_log("前端端口 5173 仍被占用（可能有进程拒绝终止），请手动检查", 'warning')
        else:
            self.add_log("前端服务已停止", 'success')
            self._ui_set_service('frontend', "未启动", TEXT3)
            self._update_progress('frontend', 0, TEXT3)
        self.backend_process = None
        self.frontend_process = None
        self._set_button_state(start='enabled', stop='disabled', open='disabled')
        self._stop_in_progress = False

    def open_browser(self):
        self.add_log("正在打开浏览器...", 'system')
        webbrowser.open('http://localhost:5173')

    # ── 日志线程（Qt 信号直接驱动 UI，无需手动队列）──
    def read_process_output(self, process, source):
        threading.Thread(target=self._read_single_pipe, args=(process, source, 'stdout'), daemon=True).start()
        threading.Thread(target=self._read_single_pipe, args=(process, source, 'stderr'), daemon=True).start()

    def _read_single_pipe(self, process, source, pipe):
        stream = process.stdout if pipe == 'stdout' else process.stderr
        tag = source if pipe == 'stdout' else source + '_err'
        try:
            while True:
                line = stream.readline()
                if not line:
                    break
                decoded = line.decode('utf-8', errors='ignore').strip()
                if decoded:
                    self.bridge.log.emit(decoded, tag)
        except Exception:
            pass

    # ── 系统备份本地接口（供后台「系统备份」页面联动）──
    def _start_backup_http_service(self):
        try:
            handler = BackupHttpHandler
            handler.app_ref = self
            self._backup_http_server = ThreadingHTTPServer(('127.0.0.1', BACKUP_API_PORT), handler)
            threading.Thread(target=self._backup_http_server.serve_forever, daemon=True).start()
            self.add_log(f"系统备份本地接口已启动 (127.0.0.1:{BACKUP_API_PORT})", 'system')
        except OSError as e:
            self._backup_http_server = None
            self.add_log(f"备份本地接口启动失败（端口 {BACKUP_API_PORT} 可能被占用）: {e}", 'warning')

    def _append_backup_log_file(self, text, level='info'):
        """备份日志落盘（backup_logs.jsonl，保留最近 500 条），供后台页面读取。"""
        try:
            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(BACKUP_LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps({'ts': ts, 'level': level, 'text': text}, ensure_ascii=False) + '\n')
            # 截断：仅保留最近 500 行
            try:
                with open(BACKUP_LOG_FILE, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                if len(lines) > 500:
                    with open(BACKUP_LOG_FILE, 'w', encoding='utf-8') as f:
                        f.writelines(lines[-500:])
            except Exception:
                pass
        except Exception:
            pass

    def _load_backup_logs(self, limit=200):
        try:
            with open(BACKUP_LOG_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            out = []
            for ln in lines[-limit:]:
                try:
                    out.append(json.loads(ln))
                except Exception:
                    pass
            return out
        except Exception:
            return []

    def _next_backup_text(self):
        cfg = self.backup_config.get('auto_backup', {})
        if not cfg.get('enabled'):
            return ''
        try:
            nxt = self._compute_next_backup_time(cfg)
            return nxt.strftime('%Y-%m-%d %H:%M')
        except Exception:
            return ''

    def _apply_auto_backup_config(self, cfg):
        """从「系统备份」页面下发自动备份设置（校验后应用并持久化）。"""
        period = cfg.get('period', 'daily')
        if period not in ('daily', 'weekly', 'monthly', 'interval'):
            raise ValueError('备份模式非法')
        time_str = cfg.get('time', '02:00')
        datetime.strptime(time_str, '%H:%M')
        weekday = int(cfg.get('weekday', 0))
        if not (0 <= weekday <= 6):
            raise ValueError('星期取值非法')
        day = int(cfg.get('day', 1))
        if not (1 <= day <= 31):
            raise ValueError('日期取值非法')
        interval = int(cfg.get('interval', 4))
        if not (1 <= interval <= 24):
            raise ValueError('间隔小时必须在 1-24 之间')
        new_cfg = {'enabled': bool(cfg.get('enabled', False)), 'period': period,
                   'time': time_str, 'weekday': weekday, 'day': day, 'interval': interval}
        self.backup_config['auto_backup'] = new_cfg
        self._save_backup_config()
        self._start_backup_scheduler()
        self._log_backup("自动备份设置已保存（系统备份页面）", 'success')
        # 若启动器备份设置界面已打开，同步 UI 显示
        if getattr(self, '_settings_view_open', False) and hasattr(self, 'settings_auto_enabled'):
            try:
                pmap_rev = {'daily': '每日', 'weekly': '每周', 'monthly': '每月', 'interval': '每隔几小时'}
                self.settings_auto_enabled.setChecked(new_cfg['enabled'])
                self.period_combo.setCurrentText(pmap_rev[period])
                self.time_combo.setCurrentText(time_str)
                self.weekday_combo.setCurrentIndex(weekday)
                self.day_combo.setCurrentText(str(day))
                self.interval_edit.setText(str(interval))
                self._update_settings_ui()
            except Exception:
                pass

    # ── 备份 / 还原配置 ──
    def _load_backup_config(self):
        base = os.path.dirname(os.path.abspath(__file__))
        default_dir = os.path.join(base, 'backend', 'data', 'backup')
        default = {'backup_dir': default_dir, 'auto_backup': {'enabled': False, 'period': 'daily',
                                                             'time': '02:00', 'weekday': 0, 'day': 1,
                                                             'interval': 4}}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                for k, v in default.items():
                    if k not in cfg:
                        cfg[k] = v
                for k, v in default['auto_backup'].items():
                    if k not in cfg.get('auto_backup', {}):
                        cfg['auto_backup'][k] = v
                return cfg
            except Exception:
                pass
        return default

    def _save_backup_config(self):
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.backup_config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self._log_backup(f"保存备份配置失败: {e}", 'error')

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
        last = None
        while not self.backup_scheduler_event.is_set():
            cfg = self.backup_config.get('auto_backup', {})
            if not cfg.get('enabled'):
                break
            nxt = self._compute_next_backup_time(cfg)
            now = datetime.now()
            wait = max(60, int((nxt - now).total_seconds()))
            if nxt.strftime('%Y-%m-%d %H:%M') != last:
                self._log_backup(f"下次自动备份时间: {nxt.strftime('%Y-%m-%d %H:%M')}", 'system')
                last = nxt.strftime('%Y-%m-%d %H:%M')
            slept = 0
            while slept < wait and not self.backup_scheduler_event.is_set():
                chunk = min(60, wait - slept)
                time.sleep(chunk)
                slept += chunk
            if self.backup_scheduler_event.is_set() or not self.backup_config.get('auto_backup', {}).get('enabled'):
                break
            self._log_backup("执行定时自动备份...", 'system')
            self._run_backup_task()

    def _compute_next_backup_time(self, cfg):
        period = cfg.get('period', 'daily')
        hour, minute = map(int, cfg.get('time', '02:00').split(':'))
        now = datetime.now()
        if period == 'interval':
            # 每隔几小时：以当前整点对齐，每 N 小时执行一次（N 限制 1-24）
            try:
                interval = max(1, min(24, int(cfg.get('interval', 4))))
            except (ValueError, TypeError):
                interval = 4
            return now + timedelta(hours=interval)
        if period == 'daily':
            c = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if c <= now:
                c += timedelta(days=1)
            return c
        if period == 'weekly':
            wd = int(cfg.get('weekday', 0))
            c = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            c += timedelta(days=(wd - c.weekday()) % 7)
            if c <= now:
                c += timedelta(days=7)
            return c
        if period == 'monthly':
            day = int(cfg.get('day', 1))
            last_day = calendar.monthrange(now.year, now.month)[1]
            safe = min(day, last_day)
            c = now.replace(day=safe, hour=hour, minute=minute, second=0, microsecond=0)
            if c <= now:
                if now.month == 12:
                    y, m = now.year + 1, 1
                else:
                    y, m = now.year, now.month + 1
                last_day = calendar.monthrange(y, m)[1]
                safe = min(day, last_day)
                c = now.replace(year=y, month=m, day=safe, hour=hour, minute=minute, second=0, microsecond=0)
            return c
        return now + timedelta(days=1)

    def _run_backup_task(self):
        try:
            backup_dir = self.backup_config.get('backup_dir')
            if not backup_dir:
                self._log_backup("备份失败: 未配置备份目录", 'error')
                return
            os.makedirs(backup_dir, exist_ok=True)
            base = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(base, 'backend', 'data', 'db', 'order_system.db')
            if not os.path.exists(db_path):
                self._log_backup(f"备份失败: 数据库文件不存在 {db_path}", 'error')
                return
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = os.path.join(backup_dir, f"order_system_backup_{ts}.db")
            conn = sqlite3.connect(db_path)
            conn.execute(f"VACUUM INTO '{backup_path}'")
            conn.close()
            size = os.path.getsize(backup_path)
            size_str = f"{size/1024/1024:.2f} MB" if size > 1024*1024 else f"{size/1024:.1f} KB"
            self._log_backup(f"数据库备份成功: {backup_path} ({size_str})", 'success')
        except Exception as e:
            self._log_backup(f"数据库备份失败: {e}", 'error')

    # ── 视图切换 ──
    def _refresh_nav(self):
        self.nav_home.set_active(self._current_view == 'home')
        self.nav_settings.set_active(self._current_view == 'settings')

    def _show_home_view(self):
        self.content_stack.setCurrentWidget(self.home_page)
        self._current_view = 'home'
        self._settings_view_open = False
        self._refresh_nav()

    def open_settings(self):
        if not self._settings_built:
            self._build_settings_view()
            self._settings_built = True
        self.content_stack.setCurrentWidget(self.settings_page)
        self._current_view = 'settings'
        self._settings_view_open = True
        self._refresh_nav()

    # ── 备份设置视图 ──
    def _build_settings_view(self):
        page = self.settings_page
        root = QVBoxLayout(page)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(7)
        h = QVBoxLayout()
        h.setSpacing(0)
        t1 = QLabel("数据库备份与还原")
        t1.setStyleSheet(f"font: bold 14px {FONT}; color:{TEXT};")
        t2 = QLabel("管理备份目录、自动备份计划与还原操作")
        t2.setStyleSheet(f"font: 10px 'Segoe UI'; color:{TEXT2};")
        h.addWidget(t1)
        h.addWidget(t2)
        root.addLayout(h)

        cols = QHBoxLayout()
        cols.setSpacing(10)
        left = QVBoxLayout()
        left.setSpacing(8)
        right = QVBoxLayout()
        right.setSpacing(8)
        cols.addLayout(left, 1)
        cols.addLayout(right, 1)
        root.addLayout(cols, 1)

        # 备份设置卡
        c1, b1 = self._make_card_settings("备份设置")
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("备份目录:"))
        row1.itemAt(0).widget().setStyleSheet(f"font:11px {FONT}; color:{TEXT};")
        self.settings_backup_dir_var = QLabel(self.backup_config.get('backup_dir', ''))
        self.settings_backup_dir_var.setStyleSheet(f"font:9pt 'Segoe UI'; color:{TEXT2};")
        self.settings_backup_dir_var.setWordWrap(True)
        row1.addWidget(self.settings_backup_dir_var, 1)
        b1.addLayout(row1)
        row1b = QHBoxLayout()
        row1b.addStretch()
        self._settings_btn(row1b, "选择目录", BLUE, self._choose_backup_dir)
        self._settings_btn(row1b, "立即备份", GREEN, self._do_backup_now)
        b1.addLayout(row1b)
        left.addWidget(c1)

        # 自动备份配置卡
        c2, b2 = self._make_card_settings("自动备份配置")
        auto = self.backup_config.get('auto_backup', {})
        plabels = {'daily': '每日', 'weekly': '每周', 'monthly': '每月', 'interval': '每隔几小时'}
        wlabels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        self.settings_auto_enabled = QCheckBox("启用自动备份")
        self.settings_auto_enabled.setChecked(auto.get('enabled', False))
        self.settings_auto_enabled.setStyleSheet(f"font:11px {FONT}; color:{TEXT};")
        b2.addWidget(self.settings_auto_enabled)
        b2.addSpacing(4)

        lbl_style = f"font:11px {FONT}; color:{TEXT2};"
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(1, 1)

        l_period = QLabel("备份模式:")
        l_period.setStyleSheet(lbl_style)
        self.period_combo = QComboBox()
        self.period_combo.addItems(list(plabels.values()))
        self.period_combo.setCurrentText(plabels.get(auto.get('period', 'daily'), '每日'))
        self.period_combo.currentTextChanged.connect(self._update_settings_ui)
        self._style_combo(self.period_combo)
        grid.addWidget(l_period, 0, 0)
        grid.addWidget(self.period_combo, 0, 1)

        # 每日/每周/每月 共用时间选择器
        self.time_label = QLabel("执行时间:")
        self.time_label.setStyleSheet(lbl_style)
        self.time_combo = QComboBox()
        self.time_combo.addItems([f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)])
        self.time_combo.setCurrentText(auto.get('time', '02:00'))
        self._style_combo(self.time_combo)
        grid.addWidget(self.time_label, 1, 0)
        grid.addWidget(self.time_combo, 1, 1)

        # 每周：星期选择
        self.weekday_container = QWidget()
        wcv = QHBoxLayout(self.weekday_container)
        wcv.setContentsMargins(0, 0, 0, 0)
        wcv.setSpacing(8)
        l_week = QLabel("星期:")
        l_week.setStyleSheet(lbl_style)
        self.weekday_combo = QComboBox()
        self.weekday_combo.addItems(wlabels)
        self.weekday_combo.setCurrentIndex(auto.get('weekday', 0))
        self._style_combo(self.weekday_combo)
        wcv.addWidget(l_week)
        wcv.addWidget(self.weekday_combo)
        wcv.addStretch()
        grid.addWidget(self.weekday_container, 2, 0, 1, 2)

        # 每月：日期选择
        self.day_container = QWidget()
        dcv = QHBoxLayout(self.day_container)
        dcv.setContentsMargins(0, 0, 0, 0)
        dcv.setSpacing(8)
        l_day = QLabel("日期:")
        l_day.setStyleSheet(lbl_style)
        self.day_combo = QComboBox()
        self.day_combo.addItems([str(d) for d in range(1, 32)])
        self.day_combo.setCurrentText(str(auto.get('day', 1)))
        self._style_combo(self.day_combo)
        dcv.addWidget(l_day)
        dcv.addWidget(self.day_combo)
        dcv.addStretch()
        grid.addWidget(self.day_container, 2, 0, 1, 2)

        # 每隔几小时：间隔输入（仅允许 1-24 整数）
        self.interval_container = QWidget()
        ivc = QHBoxLayout(self.interval_container)
        ivc.setContentsMargins(0, 0, 0, 0)
        ivc.setSpacing(8)
        l_interval = QLabel("间隔小时:")
        l_interval.setStyleSheet(lbl_style)
        self.interval_edit = QLineEdit()
        self.interval_edit.setText(str(auto.get('interval', 4)))
        self.interval_edit.setFixedWidth(72)
        self.interval_edit.setValidator(QIntValidator(1, 24, self.interval_edit))
        self.interval_edit.setStyleSheet(
            f"QLineEdit{{background:{CARD}; border:1px solid {CARD_BORDER}; border-radius:7px; "
            f"padding:3px 8px; font:11px {FONT}; color:{TEXT};}}")
        ivc.addWidget(l_interval)
        ivc.addWidget(self.interval_edit)
        ivc.addWidget(QLabel("小时"), alignment=Qt.AlignLeft)
        ivc.addStretch()
        grid.addWidget(self.interval_container, 2, 0, 1, 2)

        b2.addLayout(grid)
        b2.addSpacing(4)
        row2c = QHBoxLayout()
        self.settings_next_backup = QLabel("")
        self.settings_next_backup.setStyleSheet(f"font:10px 'Segoe UI'; color:{TEXT2};")
        row2c.addWidget(self.settings_next_backup, 1)
        row2c.addStretch()
        self._settings_btn(row2c, "保存设置", PURPLE, self._save_auto_backup_settings)
        b2.addLayout(row2c)
        left.addWidget(c2, 1)

        # 还原操作卡
        c3, b3 = self._make_card_settings("还原操作")
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("备份文件列表:"))
        row3.itemAt(0).widget().setStyleSheet(f"font:11px {FONT}; color:{TEXT};")
        row3.addStretch()
        self._settings_btn(row3, "刷新列表", BLUE, self._refresh_backup_list)
        b3.addLayout(row3)
        self.settings_backup_listbox = QListWidget()
        self.settings_backup_listbox.setStyleSheet(
            f"QListWidget{{background:{CARD}; border:1px solid {CARD_BORDER}; border-radius:7px; "
            f"font:9pt Consolas; color:{TEXT};}}")
        b3.addWidget(self.settings_backup_listbox, 1)
        row3c = QHBoxLayout()
        row3c.addStretch()
        self._settings_btn(row3c, "从文件还原", ORANGE, self._do_restore_from_file)
        self._settings_btn(row3c, "还原选中备份", PURPLE, self._do_restore)
        b3.addLayout(row3c)
        right.addWidget(c3, 1)

        # 操作日志卡
        c4, b4 = self._make_card_settings("操作日志")
        self.settings_log_text = QTextEdit()
        self.settings_log_text.setReadOnly(True)
        self.settings_log_text.setStyleSheet(
            f"QTextEdit{{background:{CARD}; border:1px solid {CARD_BORDER}; border-radius:7px; "
            f"font:9pt Consolas; color:{TEXT}; padding:6px;}}")
        b4.addWidget(self.settings_log_text, 1)
        right.addWidget(c4, 1)

        self._update_settings_ui()
        self._refresh_backup_list()

    def _make_card_settings(self, title):
        card = QFrame()
        card.setObjectName('card')
        v = QVBoxLayout(card)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        t = QLabel(title)
        t.setStyleSheet(f"font: bold 12px {FONT}; color:{TEXT}; padding:10px 11px 4px 11px;")
        v.addWidget(t)
        body = QWidget()
        bv = QVBoxLayout(body)
        bv.setContentsMargins(11, 0, 11, 10)
        bv.setSpacing(7)
        v.addWidget(body, 1)
        return card, bv

    def _style_combo(self, combo):
        combo.setFixedWidth(90)
        combo.setCursor(Qt.PointingHandCursor)
        combo.setStyleSheet(
            f"QComboBox{{background:{CARD}; border:1px solid {CARD_BORDER}; border-radius:6px; "
            f"padding:3px 8px; font:11px {FONT}; color:{TEXT};}}"
            f"QComboBox::drop-down{{border:none;}}"
            f"QComboBox QAbstractItemView{{background:{CARD}; selection-background-color:{BLUE}; "
            f"color:{TEXT}; font:11px {FONT};}}")

    def _settings_btn(self, layout, text, color, cmd):
        btn = QPushButton(text)
        btn.setFixedHeight(22)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(cmd)
        btn.setStyleSheet(
            f"QPushButton{{background:{color}; color:#ffffff; border:none; border-radius:7px; "
            f"font: bold 11px {FONT}; padding:0 12px;}}"
            f"QPushButton:hover{{background:{color};}}")
        layout.addWidget(btn)
        return btn

    def _update_settings_ui(self, *args):
        pmap = {'每日': 'daily', '每周': 'weekly', '每月': 'monthly', '每隔几小时': 'interval'}
        wlabels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        period = pmap.get(self.period_combo.currentText(), 'daily')
        self.weekday_container.setVisible(period == 'weekly')
        self.day_container.setVisible(period == 'monthly')
        self.interval_container.setVisible(period == 'interval')
        # 每日/每周/每月显示时间选择器；每隔几小时不显示
        self.time_label.setVisible(period != 'interval')
        self.time_combo.setVisible(period != 'interval')
        try:
            interval_val = 4
            try:
                interval_val = int(self.interval_edit.text().strip())
            except (ValueError, AttributeError):
                pass
            cfg = {'enabled': self.settings_auto_enabled.isChecked(), 'period': period,
                   'time': self.time_combo.currentText(),
                   'weekday': wlabels.index(self.weekday_combo.currentText()),
                   'day': int(self.day_combo.currentText()),
                   'interval': interval_val}
            if cfg['enabled']:
                nxt = self._compute_next_backup_time(cfg)
                if period == 'interval':
                    self.settings_next_backup.setText(f"下次备份: {nxt.strftime('%Y-%m-%d %H:%M')}（每 {interval_val} 小时）")
                else:
                    self.settings_next_backup.setText(f"下次备份: {nxt.strftime('%Y-%m-%d %H:%M')}")
            else:
                self.settings_next_backup.setText("自动备份未启用")
        except Exception:
            self.settings_next_backup.setText("请检查自动备份设置")

    def on_settingslog(self, text, level='info'):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        color = LOG_COLORS.get(level, TEXT)
        if getattr(self, 'settings_log_text', None):
            self.settings_log_text.moveCursor(QTextCursor.End)
            self.settings_log_text.insertHtml(
                f'<span style="color:{color}">[{html.escape(timestamp)}] '
                f'[{html.escape(level.upper())}] {html.escape(text)}</span><br>')

    def _choose_backup_dir(self):
        initial = self.backup_config.get('backup_dir') or os.path.dirname(os.path.abspath(__file__))
        d = QFileDialog.getExistingDirectory(self, "选择备份目录", initial)
        if d:
            self.backup_config['backup_dir'] = d
            self.settings_backup_dir_var.setText(d)
            self._save_backup_config()
            self._log_backup(f"备份目录已设置为: {d}", 'success')

    def _do_backup_now(self):
        def run():
            self._log_backup("开始手动备份...", 'system')
            self._run_backup_task()
            self.bridge.backuplist.emit()
        threading.Thread(target=run, daemon=True).start()

    def _refresh_backup_list(self):
        if not getattr(self, '_settings_view_open', False) or not hasattr(self, 'settings_backup_listbox'):
            return
        self.settings_backup_listbox.clear()
        backup_dir = self.backup_config.get('backup_dir', '')
        if not backup_dir or not os.path.exists(backup_dir):
            return
        files = sorted([f for f in os.listdir(backup_dir) if f.endswith('.db')], reverse=True)
        for f in files:
            fp = os.path.join(backup_dir, f)
            size = os.path.getsize(fp)
            mtime = time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(fp)))
            size_str = f"{size/1024/1024:.2f} MB" if size > 1024*1024 else f"{size/1024:.1f} KB"
            self.settings_backup_listbox.addItem(f"{f}  |  {size_str}  |  {mtime}")

    def _do_restore(self):
        item = self.settings_backup_listbox.currentItem()
        if not item:
            QMessageBox.warning(self, "提示", "请先选择一个备份文件")
            return
        backup_name = item.text().split('  |  ')[0].strip()
        backup_dir = self.backup_config.get('backup_dir', '')
        backup_path = os.path.join(backup_dir, backup_name)
        if QMessageBox.question(self, "确认还原",
                f"确定要用备份 {backup_name} 还原数据库吗？\n还原将停止后端服务、替换当前数据库，并自动重新启动。",
                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        threading.Thread(target=lambda: self._run_restore_task(backup_path, backup_name), daemon=True).start()

    def _do_restore_from_file(self):
        fp = QFileDialog.getOpenFileName(self, "选择要还原的数据库备份文件", "",
                                         "SQLite 数据库 (*.db);;所有文件 (*.*)")[0]
        if not fp:
            return
        backup_name = os.path.basename(fp)
        if QMessageBox.question(self, "确认还原",
                f"确定要用备份 {backup_name} 还原数据库吗？\n还原将停止后端服务、替换当前数据库，并自动重新启动。",
                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        threading.Thread(target=lambda: self._run_restore_task(fp, backup_name), daemon=True).start()

    def _run_restore_task(self, backup_path, backup_name):
        self._log_backup(f"开始还原数据库: {backup_name}", 'system')
        try:
            self._log_backup("正在停止后端服务...", 'system')
            self.stop_services()
            time.sleep(2)
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend', 'data', 'db', 'order_system.db')
            if not os.path.exists(backup_path):
                raise FileNotFoundError(f"备份文件不存在: {backup_path}")
            backup_dir = self.backup_config.get('backup_dir', '')
            emergency = os.path.join(backup_dir, f"order_system_emergency_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
            if os.path.exists(db_path):
                shutil.copy2(db_path, emergency)
                self._log_backup(f"当前数据库已紧急备份到: {emergency}", 'system')
            shutil.copy2(backup_path, db_path)
            self._log_backup("数据库文件已替换", 'success')
            self._log_backup("正在重新启动服务...", 'system')
            self.start_services()
            self._log_backup("数据库还原完成，服务已重新启动", 'success')
        except Exception as e:
            self._log_backup(f"还原失败: {e}", 'error')

    def _save_auto_backup_settings(self):
        pmap = {'每日': 'daily', '每周': 'weekly', '每月': 'monthly', '每隔几小时': 'interval'}
        wlabels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        try:
            period = pmap.get(self.period_combo.currentText(), 'daily')
            # 每隔几小时模式：间隔必须是 1-24 整数，否则拦截弹窗
            interval = 4
            if period == 'interval':
                raw = self.interval_edit.text().strip()
                try:
                    interval = int(raw)
                except ValueError:
                    QMessageBox.warning(self, "输入无效", "间隔小时数必须是 1-24 之间的整数")
                    return
                if not (1 <= interval <= 24):
                    QMessageBox.warning(self, "输入无效", "间隔小时数必须在 1-24 之间")
                    return
            time_str = self.time_combo.currentText()
            datetime.strptime(time_str, '%H:%M')
            cfg = {'enabled': self.settings_auto_enabled.isChecked(), 'period': period,
                   'time': time_str, 'weekday': wlabels.index(self.weekday_combo.currentText()),
                   'day': int(self.day_combo.currentText()), 'interval': interval}
            self.backup_config['auto_backup'] = cfg
            self._save_backup_config()
            self._start_backup_scheduler()
            self._update_settings_ui()
            self._log_backup("自动备份设置已保存", 'success')
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"设置保存失败: {e}")

    # ── 窗口控制（最大化走 Qt 原生，彻底规避合成器 bug）──
    def _on_minimize(self):
        self.showMinimized()

    def _on_zoom(self):
        if self.isMaximized():
            self.showNormal()
            self._zoomed = False
        else:
            self.showMaximized()
            self._zoomed = True

    def _on_close(self):
        self._stop_backup_scheduler()
        self._stop_tray_icon()
        if is_port_open(8000) or is_port_open(5173) or self.backend_process or self.frontend_process:
            if QMessageBox.question(self, "退出确认",
                    "服务正在运行中，确定要退出吗？\n退出时将自动停止所有相关进程。",
                    QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                self._stop_services_impl()
                self.close()
        else:
            self.close()

    def closeEvent(self, e):
        self._stop_backup_scheduler()
        self._stop_tray_icon()
        super().closeEvent(e)

    # ── 拖拽 / 缩放（无边框窗口）──
    def _center_window(self):
        fg = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        fg.moveCenter(cp)
        self.move(fg.topLeft())

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            w, h = self.width(), self.height()
            edge = 6
            x, y = e.position().x(), e.position().y()
            if y < 40:
                return
            left = x <= edge
            right = x >= w - edge
            bottom = y >= h - edge
            child = self.childAt(e.position().toPoint())
            interactive = (QPushButton, QComboBox, QLineEdit, QListWidget, QTextEdit, QCheckBox)
            if child is not None and isinstance(child, interactive):
                return
            if left and bottom:
                self._resize_edge = 'sw'
            elif right and bottom:
                self._resize_edge = 'se'
            elif left:
                self._resize_edge = 'w'
            elif right:
                self._resize_edge = 'e'
            elif bottom:
                self._resize_edge = 's'
            else:
                self._resize_edge = None
            if self._resize_edge:
                self._rx = e.globalPosition().x()
                self._ry = e.globalPosition().y()
                self._rw = w
                self._rh = h
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if getattr(self, '_resize_edge', None):
            dx = e.globalPosition().x() - self._rx
            dy = e.globalPosition().y() - self._ry
            nw, nh = self._rw, self._rh
            nx, ny = self.x(), self.y()
            if 'e' in self._resize_edge:
                nw = max(980, self._rw + dx)
            if 's' in self._resize_edge:
                nh = max(680, self._rh + dy)
            if 'w' in self._resize_edge:
                nw = max(980, self._rw - dx)
                nx = self.x() + (self._rw - nw)
            self.setGeometry(nx, ny, nw, nh)
        else:
            if e.position().y() < 40:
                self.setCursor(Qt.ArrowCursor)
            else:
                w, h = self.width(), self.height()
                edge = 6
                left = e.position().x() <= edge
                right = e.position().x() >= w - edge
                bottom = e.position().y() >= h - edge
                if (left and bottom) or (right and bottom):
                    self.setCursor(Qt.SizeFDiagCursor if (left ^ right) else Qt.SizeFDiagCursor)
                elif left or right:
                    self.setCursor(Qt.SizeHorCursor)
                elif bottom:
                    self.setCursor(Qt.SizeVerCursor)
                else:
                    self.setCursor(Qt.ArrowCursor)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._resize_edge = None
        super().mouseReleaseEvent(e)

    # ── 系统托盘（Qt 原生）──
    def _create_tray_icon(self):
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 'frontend', 'src', 'assets', 'img', 'logo.png')
        if os.path.exists(logo_path):
            return QIcon(str(logo_path))
        pm = QPixmap(64, 64)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QBrush(QColor(BLUE)))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(4, 4, 56, 56, 12, 12)
        p.drawText(pm.rect(), Qt.AlignCenter, "ERP")
        p.end()
        return QIcon(pm)

    def _show_tray_icon(self):
        if getattr(self, '_tray_icon', None):
            self._tray_icon.show()
            return
        self._tray_icon = QSystemTrayIcon(self)
        self._tray_icon.setIcon(self._create_tray_icon())
        self._tray_icon.setToolTip('ERP_GO 订单管理系统 启动器')
        menu = QMenu()
        show_act = QAction("恢复启动器", self)
        show_act.triggered.connect(self._restore_from_tray)
        quit_act = QAction("退出启动器", self)
        quit_act.triggered.connect(self._on_close)
        menu.addAction(show_act)
        menu.addAction(quit_act)
        self._tray_icon.setContextMenu(menu)
        self._tray_icon.activated.connect(
            lambda reason: self._restore_from_tray() if reason == QSystemTrayIcon.DoubleClick else None)
        self._tray_icon.show()
        self.add_log("已最小化到系统托盘（双击托盘图标可恢复窗口）", 'system')

    def _restore_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _stop_tray_icon(self):
        ti = getattr(self, '_tray_icon', None)
        if ti:
            try:
                ti.hide()
            except Exception:
                pass
            self._tray_icon = None


# ═══════════════════════════════════════
# 启动入口
# ═══════════════════════════════════════
def main():
    # 单实例保护
    lock_sock = acquire_single_instance_lock()
    if lock_sock is None:
        app = QApplication.instance() or QApplication([])
        QMessageBox.warning(None, "提示", "启动器已在运行，请勿重复打开。\n若窗口不可见，请在任务栏或系统托盘查找。")
        sys.exit(0)

    app = QApplication([])
    app.setStyle('Fusion')
    app.setStyleSheet(f"""
        QFrame#card{{background:{CARD}; border:1px solid {CARD_BORDER}; border-radius:16px;}}
        QLabel{{background:transparent;}}
    """)

    window = LauncherApp()
    window.show()
    window._show_tray_icon()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
