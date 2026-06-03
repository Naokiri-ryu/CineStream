"""
CineStream Infrastructure Manager — Professional Dashboard
Inspired by Grafana monitoring dashboards.
"""
# ── Imports ──────────────────────────────────────────────────────────────────
import sys, os, re, threading, time, shutil, subprocess, webbrowser
from collections import deque
from datetime import datetime
import socket as _socket

import requests
import psutil
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QMessageBox, QDialog, QProgressBar,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QGridLayout, QFrame, QTextEdit, QCheckBox, QSizePolicy, QAbstractItemView,
    QSpacerItem
)
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QPainterPath, QPen, QLinearGradient
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QPointF

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))
from app import create_app, socketio
from database import DB_PATH, init_db, get_all_films, delete_film, add_film
from fetcher import fetch_from_mal, fetch_from_imdb  

# ── Config ───────────────────────────────────────────────────────────────────
FLASK_PORT = 5000
NGINX_PORT = 8080
START_TIME = time.time()
app_flask  = create_app()

_log_q: deque = deque(maxlen=100)

def _push_log(msg: str, level: str = 'info'):
    _log_q.append((datetime.now().strftime('%H:%M:%S'), level, msg))

def _run_flask():
    socketio.run(app_flask, host='0.0.0.0', port=FLASK_PORT,
                 debug=False, use_reloader=False, allow_unsafe_werkzeug=True)

def _get_local_ip() -> str:
    try:
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        s.settimeout(1); s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]; s.close(); return ip
    except Exception:
        return '127.0.0.1'

# ── Theme ─────────────────────────────────────────────────────────────────────
BG      = '#0d1117'
PANEL   = '#161b22'
PANEL2  = '#1c2128'
BORDER  = '#21262d'
BORDER2 = '#30363d'
ACCENT  = '#e50914'
GREEN   = '#3fb950'
BLUE    = '#58a6ff'
YELLOW  = '#d29922'
PURPLE  = '#bc8cff'
TEXT    = '#e6edf3'
MUTED   = '#8b949e'
DIM     = '#2d333b'

QSS = f"""
QMainWindow, QDialog {{ background: {BG}; }}
QWidget {{ color: {TEXT}; font-family: 'Segoe UI', Arial, sans-serif;
           font-size: 13px; background: transparent; }}
QTabWidget::pane {{ background: {BG}; border: none;
                   border-top: 1px solid {BORDER}; }}
QTabBar {{ background: {BG}; }}
QTabBar::tab {{ background: {PANEL}; color: {MUTED}; border: 1px solid {BORDER};
               padding: 10px 22px; margin-right: 3px;
               border-top-left-radius: 7px; border-top-right-radius: 7px;
               font-weight: 700; }}
QTabBar::tab:selected {{ background: {ACCENT}; color: white;
                         border-color: {ACCENT}; }}
QTabBar::tab:hover:!selected {{ background: {DIM}; color: {TEXT}; }}
QPushButton {{ background: {PANEL}; border: 1px solid {BORDER2};
               border-radius: 6px; padding: 7px 14px;
               font-weight: 600; color: {TEXT}; }}
QPushButton:hover {{ background: {DIM}; border-color: {MUTED}; }}
QPushButton[role="accent"] {{ background: {ACCENT}; color: white; border: none; }}
QPushButton[role="accent"]:hover {{ background: #c80812; }}
QPushButton[role="ghost"] {{ background: transparent; border: 1px solid {BORDER};
                              color: {MUTED}; padding: 6px 12px; font-size: 12px; }}
QPushButton[role="ghost"]:hover {{ border-color: {TEXT}; color: {TEXT}; }}
QPushButton[role="danger"] {{ background: transparent; border: 1px solid {ACCENT};
                               color: {ACCENT}; }}
QPushButton[role="danger"]:hover {{ background: rgba(229,9,20,0.12); }}
QPushButton[role="shutdown"] {{
    background: rgba(229,9,20,0.08); border: 1px solid {ACCENT};
    color: {ACCENT}; font-size: 14px; font-weight: 700;
    padding: 12px; border-radius: 8px; }}
QPushButton[role="shutdown"]:hover {{ background: rgba(229,9,20,0.18); }}
QLineEdit {{ background: {PANEL}; border: 1px solid {BORDER};
             border-radius: 6px; padding: 8px 12px; color: {TEXT}; }}
QLineEdit:focus {{ border-color: {ACCENT}; }}
QTextEdit {{ background: {PANEL}; border: 1px solid {BORDER};
             border-radius: 8px; color: {TEXT};
             font-family: Consolas, 'Courier New', monospace;
             font-size: 12px; padding: 6px; }}
QTableWidget {{ background: {PANEL}; border: 1px solid {BORDER};
                border-radius: 8px; gridline-color: {BORDER}; }}
QTableWidget::item {{ padding: 8px 10px; border-bottom: 1px solid {BORDER}; }}
QTableWidget::item:selected {{ background: rgba(229,9,20,0.15); color: white; }}
QHeaderView::section {{ background: {BG}; color: {ACCENT}; padding: 10px 10px;
                        font-weight: 700; font-size: 11px; border: none;
                        border-bottom: 2px solid {BORDER};
                        letter-spacing: 0.5px; text-transform: uppercase; }}
QTableCornerButton::section {{ background: {BG}; border: none; }}
QScrollBar:vertical {{ background: {PANEL}; width: 5px; border-radius: 2px; }}
QScrollBar::handle:vertical {{ background: {DIM}; border-radius: 2px;
                                min-height: 20px; }}
QScrollBar::handle:vertical:hover {{ background: {MUTED}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: {PANEL}; height: 5px; border-radius: 2px; }}
QScrollBar::handle:horizontal {{ background: {DIM}; border-radius: 2px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QProgressBar {{ background: {DIM}; border: none; border-radius: 2px;
                color: transparent; max-height: 4px; }}
QProgressBar::chunk {{ border-radius: 2px; background: {GREEN}; }}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{ width: 15px; height: 15px; border: 1px solid {BORDER2};
                        border-radius: 3px; background: {PANEL}; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
QMessageBox {{ background: {PANEL}; }}
"""

# ── Custom Widgets ────────────────────────────────────────────────────────────

class SparklineWidget(QWidget):
    def __init__(self, color: str = GREEN, parent=None):
        super().__init__(parent)
        self._data  = deque(maxlen=60)
        self._color = QColor(color)
        self.setMinimumSize(60, 44)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def push(self, value: float):
        self._data.append(float(value))
        self.update()

    def paintEvent(self, event):
        if len(self._data) < 2: return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        pts  = list(self._data)
        n    = len(pts)
        dmax = max(max(pts), 1.0)

        def px(i): return (i / (n - 1)) * w
        def py(v): return h - 2 - (v / dmax) * (h - 6)

        path = QPainterPath()
        path.moveTo(QPointF(px(0), float(h)))
        path.lineTo(QPointF(px(0), py(pts[0])))
        for i in range(1, n):
            path.lineTo(QPointF(px(i), py(pts[i])))
        path.lineTo(QPointF(px(n - 1), float(h)))
        path.closeSubpath()

        c = self._color
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0, QColor(c.red(), c.green(), c.blue(), 55))
        grad.setColorAt(1, QColor(c.red(), c.green(), c.blue(), 0))
        p.fillPath(path, grad)

        pen = QPen(self._color, 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        for i in range(1, n):
            p.drawLine(QPointF(px(i-1), py(pts[i-1])), QPointF(px(i), py(pts[i])))
        p.end()

class MetricCard(QFrame):
    def __init__(self, title: str, accent: str = GREEN, show_bar: bool = False, show_spark: bool = False, parent=None):
        super().__init__(parent)
        self._accent     = accent
        self._show_bar   = show_bar
        self._show_spark = show_spark
        self.setObjectName('MetricCard')
        self.setStyleSheet(f"QFrame#MetricCard {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 10px; }} QFrame#MetricCard:hover {{ border-color: {accent}; }}")
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 13, 16, 13)
        root.setSpacing(5)

        top = QHBoxLayout()
        lbl_t = QLabel(title.upper())
        lbl_t.setStyleSheet(f'color: {MUTED}; font-size: 10px; font-weight: 700; letter-spacing: 0.8px;')
        top.addWidget(lbl_t)
        top.addStretch()
        self._dot = QLabel('●')
        self._dot.setStyleSheet(f'color: {accent}; font-size: 9px;')
        top.addWidget(self._dot)
        root.addLayout(top)

        self.lbl_val = QLabel('—')
        self.lbl_val.setStyleSheet('color: white; font-size: 22px; font-weight: 700;')
        root.addWidget(self.lbl_val)

        self.lbl_sub = QLabel('')
        self.lbl_sub.setStyleSheet(f'color: {MUTED}; font-size: 11px;')
        self.lbl_sub.setVisible(False)
        root.addWidget(self.lbl_sub)

        if show_bar:
            self._bar = QProgressBar()
            self._bar.setMaximum(100)
            self._bar.setValue(0)
            self._bar.setFixedHeight(4)
            self._bar.setStyleSheet(f'QProgressBar {{ background: {DIM}; border: none; border-radius: 2px; color: transparent; }} QProgressBar::chunk {{ background: {accent}; border-radius: 2px; }}')
            root.addWidget(self._bar)

        if show_spark:
            self._spark = SparklineWidget(color=accent)
            root.addWidget(self._spark)

    def update_value(self, text: str, sub: str = '', bar_pct: int = -1):
        self.lbl_val.setText(text)
        self.lbl_sub.setText(sub)
        self.lbl_sub.setVisible(bool(sub))
        if self._show_bar and bar_pct >= 0:
            self._bar.setValue(bar_pct)
            chunk = GREEN if bar_pct < 60 else (YELLOW if bar_pct < 80 else ACCENT)
            self._bar.setStyleSheet(f'QProgressBar {{ background: {DIM}; border: none; border-radius: 2px; color: transparent; }} QProgressBar::chunk {{ background: {chunk}; border-radius: 2px; }}')
            self._dot.setStyleSheet(f'color: {chunk}; font-size: 9px;')
        if self._show_spark and bar_pct >= 0:
            self._spark.push(float(bar_pct))

class SectionHeader(QWidget):
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 6, 0, 2)
        lay.setSpacing(10)
        lbl = QLabel(text.upper())
        lbl.setStyleSheet(f'color: {MUTED}; font-size: 10px; font-weight: 700; letter-spacing: 1px;')
        lay.addWidget(lbl)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f'color: {BORDER}; background: {BORDER}; max-height: 1px;')
        lay.addWidget(line)


# ── FFmpeg Worker (Versi 2 Tahap - Cerdas & Anti-Crash) ──────────────────────

class FFmpegWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str, str)

    def __init__(self, input_file: str, title: str):
        super().__init__()
        self.input_file = input_file
        self.title      = title
        self._cancelled = False
        self.process    = None
        self.output_dir = ''

    def stop(self):
        self._cancelled = True
        if self.process:
            self.process.kill()

    def run(self):
        try:
            safe_title = re.sub(r'[^a-zA-Z0-9]', '_', self.title.lower())
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.output_dir = os.path.join(base_dir, 'media', 'hls', safe_title)
            os.makedirs(self.output_dir, exist_ok=True)
            
            output_m3u8 = os.path.join(self.output_dir, 'index.m3u8')
            output_vtt = os.path.join(self.output_dir, 'subtitle.vtt')
            
            # TAHAP 1: KONVERSI VIDEO & AUDIO SAJA (Menjamin kelancaran video)
            cmd_video = [
                'ffmpeg', '-y', '-i', os.path.normpath(self.input_file),
                '-map', '0:v:0', '-map', '0:a:0',
                '-c:v', 'libx264', '-profile:v', 'high', '-pix_fmt', 'yuv420p',
                '-level', '4.1', '-s', '1280x720',
                '-c:a', 'aac', '-ac', '2', '-b:a', '128k',
                '-start_number', '0', '-hls_time', '10', '-hls_list_size', '0',
                '-f', 'hls', os.path.normpath(output_m3u8)
            ]
            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            
            self.process = subprocess.Popen(
                cmd_video, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                universal_newlines=True, creationflags=flags)
                
            while True:
                if self._cancelled: break
                line = self.process.stdout.readline()
                if not line: break
                if 'frame=' in line:
                    self.progress.emit(50)
                    
            self.process.wait()
            
            if self._cancelled:
                shutil.rmtree(self.output_dir, ignore_errors=True)
                self.finished.emit(False, 'Konversi dibatalkan. File dihapus.', '')
                return

            if self.process.returncode == 0:
                # TAHAP 2: EKSTRAKSI SUBTITLE SILENT (Abaikan error jika formatnya gambar/PGS)
                cmd_sub = [
                    'ffmpeg', '-y', '-i', os.path.normpath(self.input_file),
                    '-map', '0:s:0?', '-c:s', 'webvtt', os.path.normpath(output_vtt)
                ]
                subprocess.run(cmd_sub, creationflags=flags, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                self.progress.emit(100)
                self.finished.emit(True, f'Sukses mengonversi {self.title}!', self.output_dir)
            else:
                self.finished.emit(False, f'FFmpeg error code: {self.process.returncode}', '')
                
        except Exception as e:
            self.finished.emit(False, str(e), '')


# ── Dialogs ───────────────────────────────────────────────────────────────────

class ConvertVideoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Mesin Konversi Video — FFmpeg')
        self.setFixedSize(520, 340)
        self.setStyleSheet(QSS)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        hdr = QLabel('🎬  Konversi Video ke Format HLS')
        hdr.setStyleSheet('font-size: 15px; font-weight: 700; color: white;')
        lay.addWidget(hdr)
        sub = QLabel('File video akan dikonversi ke segmen .ts + playlist .m3u8 untuk streaming.')
        sub.setStyleSheet(f'color: {MUTED}; font-size: 12px;')
        sub.setWordWrap(True)
        lay.addWidget(sub)
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f'background: {BORDER}; max-height: 1px; margin: 4px 0;')
        lay.addWidget(sep)

        lbl = QLabel('JUDUL FILM')
        lbl.setStyleSheet(f'color: {MUTED}; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;')
        lay.addWidget(lbl)
        self.txt_title = QLineEdit(); self.txt_title.setPlaceholderText('Masukkan judul film output...')
        lay.addWidget(self.txt_title)

        lbl2 = QLabel('FILE VIDEO SUMBER')
        lbl2.setStyleSheet(f'color: {MUTED}; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;')
        lay.addWidget(lbl2)
        row = QHBoxLayout()
        self.txt_path = QLineEdit(); self.txt_path.setPlaceholderText('Pilih file .mp4 atau .mkv...')
        btn_br = QPushButton('Browse'); btn_br.setProperty('role', 'ghost'); btn_br.setFixedWidth(80)
        btn_br.clicked.connect(self._browse)
        row.addWidget(self.txt_path); row.addWidget(btn_br)
        lay.addLayout(row)

        self.bar = QProgressBar(); self.bar.setFixedHeight(6)
        self.bar.setStyleSheet(f'QProgressBar {{ background: {DIM}; border: none; border-radius: 3px; color: transparent; }} QProgressBar::chunk {{ background: {ACCENT}; border-radius: 3px; }}')
        lay.addWidget(self.bar)
        self.lbl_status = QLabel('Status: Menunggu input...')
        self.lbl_status.setStyleSheet(f'color: {MUTED}; font-size: 12px;')
        lay.addWidget(self.lbl_status)

        btns = QHBoxLayout()
        self.btn_cancel_conv = QPushButton('✕  Batalkan & Hapus'); self.btn_cancel_conv.setProperty('role', 'danger'); self.btn_cancel_conv.setEnabled(False)
        self.btn_cancel_conv.clicked.connect(self._cancel)
        self.btn_start = QPushButton('▶  Mulai Konversi'); self.btn_start.setProperty('role', 'accent')
        self.btn_start.clicked.connect(self._start)
        btns.addWidget(self.btn_cancel_conv); btns.addWidget(self.btn_start)
        lay.addLayout(btns)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Pilih Video', '', 'Video (*.mp4 *.mkv *.avi)')
        if path:
            self.txt_path.setText(path)
            if not self.txt_title.text(): self.txt_title.setText(os.path.splitext(os.path.basename(path))[0])

    def _start(self):
        if not self.txt_path.text(): QMessageBox.warning(self, 'Input kosong', 'Pilih file video dahulu.'); return
        if not self.txt_title.text(): QMessageBox.warning(self, 'Input kosong', 'Masukkan judul film dahulu.'); return
        self.btn_start.setEnabled(False); self.btn_cancel_conv.setEnabled(True)
        self.lbl_status.setText('Status: Memproses dengan FFmpeg...')
        self.lbl_status.setStyleSheet(f'color: {YELLOW}; font-size: 12px;')
        self.worker = FFmpegWorker(self.txt_path.text(), self.txt_title.text())
        self.worker.progress.connect(self.bar.setValue)
        self.worker.finished.connect(self._done)
        self.worker.start()
        _push_log(f"Konversi dimulai: {self.txt_title.text()}", 'info')

    def _cancel(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.lbl_status.setText('Status: Membatalkan...')
            self.worker.stop(); self.worker.wait(); self.accept()

    def _done(self, ok: bool, msg: str, path: str):
        self.btn_start.setEnabled(True); self.btn_cancel_conv.setEnabled(False)
        if ok:
            self.lbl_status.setText('Status: ✅ Selesai')
            self.lbl_status.setStyleSheet(f'color: {GREEN}; font-size: 12px;')
            _push_log(f"Konversi selesai: {self.txt_title.text()}", 'success')
            QMessageBox.information(self, 'Sukses', f'{msg}\nDisimpan di:\n{path}')
            self.accept()
        else:
            self.lbl_status.setText('Status: ✕ Gagal/Dibatalkan')
            self.lbl_status.setStyleSheet(f'color: {ACCENT}; font-size: 12px;')
            _push_log(f"Konversi gagal: {msg}", 'error')
            QMessageBox.warning(self, 'Berhenti', msg)


class AddFilmDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Tambah Film Baru')
        self.setFixedWidth(480)
        self.setStyleSheet(QSS)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 20)
        lay.setSpacing(8)

        hdr = QLabel('➕  Tambah Film ke Katalog')
        hdr.setStyleSheet('font-size: 15px; font-weight: 700; color: white; margin-bottom: 4px;')
        lay.addWidget(hdr)

        self._inputs = {}
        
        def mk_lbl(text):
            l = QLabel(text); l.setStyleSheet(f'color: {MUTED}; font-size: 10px; font-weight: 700; letter-spacing: 0.5px; margin-top: 4px;')
            return l

        lay.addWidget(mk_lbl('JUDUL FILM *'))
        row_title = QHBoxLayout()
        inp_title = QLineEdit(); inp_title.setPlaceholderText('Masukkan judul film')
        self._inputs['title'] = inp_title
        btn_mal = QPushButton('MAL'); btn_mal.setProperty('role', 'ghost'); btn_mal.clicked.connect(self._fetch_mal)
        btn_imdb = QPushButton('IMDb'); btn_imdb.setProperty('role', 'ghost'); btn_imdb.clicked.connect(self._fetch_imdb)
        row_title.addWidget(inp_title); row_title.addWidget(btn_mal); row_title.addWidget(btn_imdb)
        lay.addLayout(row_title)

        lay.addWidget(mk_lbl('DESKRIPSI'))
        inp_desc = QLineEdit(); inp_desc.setPlaceholderText('Sinopsis singkat...')
        self._inputs['desc'] = inp_desc; lay.addWidget(inp_desc)
        
        lay.addWidget(mk_lbl('GENRE'))
        inp_genre = QLineEdit(); inp_genre.setPlaceholderText('Drama, Action...')
        self._inputs['genre'] = inp_genre; lay.addWidget(inp_genre)

        row_meta = QHBoxLayout()
        v_year = QVBoxLayout(); v_year.setSpacing(2)
        v_year.addWidget(mk_lbl('TAHUN'))
        inp_year = QLineEdit(); inp_year.setPlaceholderText('Contoh: 2026')
        self._inputs['year'] = inp_year; v_year.addWidget(inp_year)
        
        v_dur = QVBoxLayout(); v_dur.setSpacing(2)
        v_dur.addWidget(mk_lbl('DURASI (MNT)'))
        inp_dur = QLineEdit(); inp_dur.setPlaceholderText('Contoh: 120')
        self._inputs['duration'] = inp_dur; v_dur.addWidget(inp_dur)
        
        v_rat = QVBoxLayout(); v_rat.setSpacing(2)
        v_rat.addWidget(mk_lbl('RATING (0-10)'))
        inp_rat = QLineEdit(); inp_rat.setPlaceholderText('Contoh: 8.5')
        self._inputs['rating'] = inp_rat; v_rat.addWidget(inp_rat)
        
        row_meta.addLayout(v_year); row_meta.addLayout(v_dur); row_meta.addLayout(v_rat)
        lay.addLayout(row_meta)

        lay.addWidget(mk_lbl('PATH HLS *'))
        row_hls = QHBoxLayout()
        inp_hls = QLineEdit(); inp_hls.setPlaceholderText('nama_folder/index.m3u8')
        self._inputs['hls_path'] = inp_hls
        btn_br = QPushButton('Browse Folder'); btn_br.setProperty('role', 'ghost'); btn_br.clicked.connect(self._browse_hls_folder)
        row_hls.addWidget(inp_hls); row_hls.addWidget(btn_br)
        lay.addLayout(row_hls)

        lay.addWidget(mk_lbl('URL POSTER'))
        inp_poster = QLineEdit(); inp_poster.setPlaceholderText('https://...')
        self._inputs['poster'] = inp_poster; lay.addWidget(inp_poster)

        row_misc = QHBoxLayout()
        v_lang = QVBoxLayout(); v_lang.addWidget(mk_lbl('BAHASA'))
        inp_lang = QLineEdit(); inp_lang.setText('Inggris')
        self._inputs['language'] = inp_lang; v_lang.addWidget(inp_lang)
        
        v_fmt = QVBoxLayout(); v_fmt.addWidget(mk_lbl('FORMAT'))
        inp_fmt = QLineEdit(); inp_fmt.setText('HD · HLS Stream')
        self._inputs['fmt'] = inp_fmt; v_fmt.addWidget(inp_fmt)
        row_misc.addLayout(v_lang); row_misc.addLayout(v_fmt)
        lay.addLayout(row_misc)

        self.cb_sub = QCheckBox('Subtitle Tersedia'); self.cb_sub.setChecked(True)
        lay.addWidget(self.cb_sub)

        btns = QHBoxLayout()
        btn_c = QPushButton('Batal'); btn_c.clicked.connect(self.reject)
        btn_ok = QPushButton('💾  Simpan Film'); btn_ok.setProperty('role', 'accent'); btn_ok.clicked.connect(self._save)
        btns.addWidget(btn_c); btns.addWidget(btn_ok)
        lay.addLayout(btns)

    def _browse_hls_folder(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        media_hls_base = os.path.join(base_dir, 'media', 'hls')
        os.makedirs(media_hls_base, exist_ok=True)
        
        folder_path = QFileDialog.getExistingDirectory(self, 'Pilih Folder Output HLS', media_hls_base)
        
        if folder_path:
            # Mengambil HANYA nama folder paling ujung
            folder_name = os.path.basename(os.path.normpath(folder_path))
            self._inputs['hls_path'].setText(f"{folder_name}/index.m3u8")

    def _apply_fetched_data(self, data):
        if data:
            if data.get('description'): self._inputs['desc'].setText(data['description'])
            if data.get('genre'): self._inputs['genre'].setText(data['genre'])
            if data.get('poster_url'): self._inputs['poster'].setText(data['poster_url'])
            if data.get('year'): self._inputs['year'].setText(str(data['year']))
            
            dur = data.get('duration', 0)
            if isinstance(dur, str):
                match = re.search(r'\d+', dur)
                self._inputs['duration'].setText(match.group() if match else '0')
            else:
                self._inputs['duration'].setText(str(dur))
                
            if data.get('rating'): self._inputs['rating'].setText(str(data['rating']))
            
            show_toast_msg(self, f"Data ditarik otomatis!\n\nScore: {self._inputs['rating'].text()}\nDurasi: {self._inputs['duration'].text()} mnt\nTahun: {self._inputs['year'].text()}")

    def _fetch_mal(self):
        title = self._inputs['title'].text().strip()
        if not title: return
        self.setWindowTitle('Mencari di MAL...'); QApplication.processEvents()
        data = fetch_from_mal(title)
        self.setWindowTitle('Tambah Film Baru')
        if data: self._apply_fetched_data(data)
        else: QMessageBox.warning(self, 'Gagal', 'Data tidak ditemukan di MyAnimeList')

    def _fetch_imdb(self):
        title = self._inputs['title'].text().strip()
        if not title: return
        self.setWindowTitle('Mencari di IMDb...'); QApplication.processEvents()
        data = fetch_from_imdb(title)
        self.setWindowTitle('Tambah Film Baru')
        if data: self._apply_fetched_data(data)
        else: QMessageBox.warning(self, 'Gagal', 'Data tidak ditemukan di IMDb.')

    def _save(self):
        t = self._inputs['title'].text().strip()
        hls = self._inputs['hls_path'].text().strip()
        if not t: QMessageBox.warning(self, 'Validasi', 'Judul tidak boleh kosong.'); return
        if not hls: QMessageBox.warning(self, 'Validasi', 'Path HLS tidak boleh kosong.'); return
        
        try: y = int(self._inputs['year'].text().strip())
        except: y = 2026
        try: d = int(self._inputs['duration'].text().strip())
        except: d = 0
        try: r = float(self._inputs['rating'].text().strip())
        except: r = 0.0

        try:
            add_film(
                title=t, description=self._inputs['desc'].text() or 'Deskripsi tidak tersedia.',
                genre=self._inputs['genre'].text() or 'Film', year=y, duration=d, rating=r,
                poster_url=self._inputs['poster'].text() or '', hls_path=hls,
                format=self._inputs['fmt'].text() or 'HD', language=self._inputs['language'].text() or 'Inggris',
                has_subtitle=1 if self.cb_sub.isChecked() else 0
            )
            _push_log(f"Film ditambahkan: '{t}'", 'success')
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, 'Error Database', str(e))


class EditFilmDialog(QDialog):
    def __init__(self, film: dict, parent=None):
        super().__init__(parent)
        self.film_id = film['id']
        self.setWindowTitle(f"Edit — {film['title']}")
        self.setFixedWidth(480)
        self.setStyleSheet(QSS)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 20)
        lay.setSpacing(8)

        hdr = QLabel('✏️  Edit Data Film')
        hdr.setStyleSheet('font-size: 15px; font-weight: 700; color: white; margin-bottom: 4px;')
        lay.addWidget(hdr)

        self._inputs = {}
        def mk_lbl(text):
            l = QLabel(text); l.setStyleSheet(f'color: {MUTED}; font-size: 10px; font-weight: 700; letter-spacing: 0.5px; margin-top: 4px;')
            return l

        lay.addWidget(mk_lbl('JUDUL FILM *'))
        row_title = QHBoxLayout()
        inp_title = QLineEdit(); inp_title.setText(film.get('title', ''))
        self._inputs['title'] = inp_title
        btn_mal = QPushButton('MAL'); btn_mal.setProperty('role', 'ghost'); btn_mal.clicked.connect(self._fetch_mal)
        btn_imdb = QPushButton('IMDb'); btn_imdb.setProperty('role', 'ghost'); btn_imdb.clicked.connect(self._fetch_imdb)
        row_title.addWidget(inp_title); row_title.addWidget(btn_mal); row_title.addWidget(btn_imdb)
        lay.addLayout(row_title)

        lay.addWidget(mk_lbl('DESKRIPSI'))
        inp_desc = QLineEdit(); inp_desc.setText(film.get('description', ''))
        self._inputs['desc'] = inp_desc; lay.addWidget(inp_desc)
        
        lay.addWidget(mk_lbl('GENRE'))
        inp_genre = QLineEdit(); inp_genre.setText(film.get('genre', ''))
        self._inputs['genre'] = inp_genre; lay.addWidget(inp_genre)

        row_meta = QHBoxLayout()
        v_year = QVBoxLayout(); v_year.addWidget(mk_lbl('TAHUN'))
        inp_year = QLineEdit(); inp_year.setText(str(film.get('year', '')))
        self._inputs['year'] = inp_year; v_year.addWidget(inp_year)
        
        v_dur = QVBoxLayout(); v_dur.addWidget(mk_lbl('DURASI (MNT)'))
        inp_dur = QLineEdit(); inp_dur.setText(str(film.get('duration', '')))
        self._inputs['duration'] = inp_dur; v_dur.addWidget(inp_dur)
        
        v_rat = QVBoxLayout(); v_rat.addWidget(mk_lbl('RATING (0-10)'))
        inp_rat = QLineEdit(); inp_rat.setText(str(film.get('rating', '')))
        self._inputs['rating'] = inp_rat; v_rat.addWidget(inp_rat)
        row_meta.addLayout(v_year); row_meta.addLayout(v_dur); row_meta.addLayout(v_rat)
        lay.addLayout(row_meta)

        lay.addWidget(mk_lbl('URL POSTER'))
        inp_poster = QLineEdit(); inp_poster.setText(film.get('poster_url', ''))
        self._inputs['poster'] = inp_poster; lay.addWidget(inp_poster)

        row_misc = QHBoxLayout()
        v_lang = QVBoxLayout(); v_lang.addWidget(mk_lbl('BAHASA'))
        inp_lang = QLineEdit(); inp_lang.setText(film.get('language', 'Inggris'))
        self._inputs['language'] = inp_lang; v_lang.addWidget(inp_lang)
        
        v_fmt = QVBoxLayout(); v_fmt.addWidget(mk_lbl('FORMAT'))
        inp_fmt = QLineEdit(); inp_fmt.setText(film.get('format', 'HD'))
        self._inputs['fmt'] = inp_fmt; v_fmt.addWidget(inp_fmt)
        row_misc.addLayout(v_lang); row_misc.addLayout(v_fmt)
        lay.addLayout(row_misc)

        self.cb_sub = QCheckBox('Subtitle Tersedia'); self.cb_sub.setChecked(bool(film.get('has_subtitle', 1)))
        lay.addWidget(self.cb_sub)

        btns = QHBoxLayout()
        btn_c = QPushButton('Batal'); btn_c.clicked.connect(self.reject)
        btn_ok = QPushButton('💾  Simpan Perubahan'); btn_ok.setProperty('role', 'accent'); btn_ok.clicked.connect(self._save)
        btns.addWidget(btn_c); btns.addWidget(btn_ok)
        lay.addLayout(btns)

    def _apply_fetched_data(self, data):
        if data:
            if data.get('description'): self._inputs['desc'].setText(data['description'])
            if data.get('genre'): self._inputs['genre'].setText(data['genre'])
            if data.get('poster_url'): self._inputs['poster'].setText(data['poster_url'])
            if data.get('year'): self._inputs['year'].setText(str(data['year']))
            
            dur = data.get('duration', 0)
            if isinstance(dur, str):
                match = re.search(r'\d+', dur)
                self._inputs['duration'].setText(match.group() if match else '0')
            else:
                self._inputs['duration'].setText(str(dur))
                
            if data.get('rating'): self._inputs['rating'].setText(str(data['rating']))
            show_toast_msg(self, f"Data diperbarui!\n\nScore: {self._inputs['rating'].text()}\nDurasi: {self._inputs['duration'].text()} mnt\nTahun: {self._inputs['year'].text()}")

    def _fetch_mal(self):
        title = self._inputs['title'].text().strip()
        if not title: return
        self.setWindowTitle('Mencari di MAL...'); QApplication.processEvents()
        data = fetch_from_mal(title)
        self.setWindowTitle(f"Edit — {title}")
        if data: self._apply_fetched_data(data)
        else: QMessageBox.warning(self, 'Gagal', 'Data tidak ditemukan di MyAnimeList')

    def _fetch_imdb(self):
        title = self._inputs['title'].text().strip()
        if not title: return
        self.setWindowTitle('Mencari di IMDb...'); QApplication.processEvents()
        data = fetch_from_imdb(title)
        self.setWindowTitle(f"Edit — {title}")
        if data: self._apply_fetched_data(data)
        else: QMessageBox.warning(self, 'Gagal', 'Data tidak ditemukan di IMDb.')

    def _save(self):
        try: y = int(self._inputs['year'].text().strip())
        except: y = 2026
        try: d = int(self._inputs['duration'].text().strip())
        except: d = 0
        try: r = float(self._inputs['rating'].text().strip())
        except: r = 0.0

        try:
            import sqlite3
            conn = sqlite3.connect(DB_PATH)
            conn.execute(
                'UPDATE films SET title=?, description=?, genre=?, language=?, format=?,'
                ' poster_url=?, has_subtitle=?, year=?, duration=?, rating=? WHERE id=?',
                (self._inputs['title'].text(), self._inputs['desc'].text(), self._inputs['genre'].text(),
                 self._inputs['language'].text(), self._inputs['fmt'].text(), self._inputs['poster'].text(),
                 1 if self.cb_sub.isChecked() else 0, y, d, r, self.film_id))
            conn.commit(); conn.close()
            _push_log(f"Film diedit: '{self._inputs['title'].text()}'", 'info')
            self.accept()
        except Exception as e: QMessageBox.critical(self, 'Error', str(e))


# ── Main Dashboard ────────────────────────────────────────────────────────────

class CineStreamDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('CineStream Infrastructure Manager')
        self.resize(1200, 780)
        self.setMinimumSize(900, 600)
        self.setStyleSheet(QSS)

        self._local_ip       = _get_local_ip()
        self._prev_rooms     = 0
        self._prev_users     = 0
        self._net_sent_prev  = psutil.net_io_counters().bytes_sent
        self._net_recv_prev  = psutil.net_io_counters().bytes_recv

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self._build_monitor_tab()
        self._build_database_tab()
        self.tabs.addTab(self._tab_monitor,  '📊  Server Monitoring')
        self.tabs.addTab(self._tab_database, '🗄️  Database Management')

        self._timer = QTimer()
        self._timer.timeout.connect(self._refresh_metrics)
        self._timer.start(2000)

    def _build_monitor_tab(self):
        self._tab_monitor = QWidget()
        root = QVBoxLayout(self._tab_monitor)
        root.setContentsMargins(24, 18, 24, 18)
        root.setSpacing(12)

        hdr = QFrame()
        hdr.setStyleSheet(f'background: {PANEL}; border: 1px solid {BORDER}; border-radius: 8px;')
        hl = QHBoxLayout(hdr); hl.setContentsMargins(16, 10, 16, 10)
        dot = QLabel('●'); dot.setStyleSheet(f'color: {GREEN}; font-size: 14px;')
        name = QLabel('CineStream Server'); name.setStyleSheet('color: white; font-size: 15px; font-weight: 700;')
        badge = QLabel('Running'); badge.setStyleSheet(f'color: {GREEN}; font-size: 11px; font-weight: 600; background: rgba(63,185,80,0.12); border: 1px solid {GREEN}; border-radius: 20px; padding: 2px 10px;')
        hl.addWidget(dot); hl.addWidget(name); hl.addWidget(badge); hl.addStretch()

        btn_open = QPushButton('🌐  Buka Browser'); btn_open.setProperty('role', 'ghost')
        btn_open.clicked.connect(lambda: webbrowser.open(f'http://localhost:{NGINX_PORT}'))
        btn_ip = QPushButton(f'📋  {self._local_ip}:{NGINX_PORT}'); btn_ip.setProperty('role', 'ghost')
        btn_ip.clicked.connect(self._copy_lan_url)
        hl.addWidget(btn_open); hl.addWidget(btn_ip); root.addWidget(hdr)

        root.addWidget(SectionHeader('Informasi Server'))
        g1 = QGridLayout(); g1.setSpacing(10)
        self._c_ip = MetricCard('Alamat IP Jaringan', BLUE)
        self._c_port = MetricCard('Port Server', BLUE)
        self._c_up = MetricCard('Uptime Server', GREEN)
        self._c_films = MetricCard('Total Film', PURPLE)
        self._c_ip.update_value(self._local_ip); self._c_port.update_value(f':{FLASK_PORT}')
        for i, c in enumerate([self._c_ip, self._c_port, self._c_up, self._c_films]): g1.addWidget(c, 0, i)
        root.addLayout(g1)

        root.addWidget(SectionHeader('Sumber Daya Sistem'))
        r2 = QHBoxLayout(); r2.setSpacing(10)
        self._c_cpu = MetricCard('CPU Usage', YELLOW, show_bar=True, show_spark=True)
        self._c_ram = MetricCard('RAM Usage', BLUE, show_bar=True, show_spark=True)
        self._c_disk = MetricCard('Disk Usage', GREEN, show_bar=True, show_spark=True)
        for c in [self._c_cpu, self._c_ram, self._c_disk]: r2.addWidget(c)
        root.addLayout(r2)

        root.addWidget(SectionHeader('Aktivitas Real-Time'))
        r3 = QHBoxLayout(); r3.setSpacing(10)
        self._c_users = MetricCard('Pengguna Online', GREEN)
        self._c_rooms = MetricCard('Watch Party Aktif', PURPLE)
        self._c_net = MetricCard('Network I/O', BLUE)
        for c in [self._c_users, self._c_rooms, self._c_net]: r3.addWidget(c)
        root.addLayout(r3)

        root.addWidget(SectionHeader('Detail Aktivitas'))
        r4 = QHBoxLayout(); r4.setSpacing(10)

        rf = QFrame(); rf.setStyleSheet(f'background: {PANEL}; border: 1px solid {BORDER}; border-radius: 10px;')
        rfl = QVBoxLayout(rf); rfl.setContentsMargins(12, 12, 12, 12); rfl.setSpacing(8)
        rl = QLabel('Watch Party Rooms'); rl.setStyleSheet(f'color: {MUTED}; font-size: 10px; font-weight: 700; letter-spacing: 0.8px;')
        rfl.addWidget(rl)
        self._rooms_tbl = QTableWidget(0, 4); self._rooms_tbl.setHorizontalHeaderLabels(['Kode', 'Film', 'Host', 'User'])
        self._rooms_tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._rooms_tbl.verticalHeader().setVisible(False)
        self._rooms_tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._rooms_tbl.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._rooms_tbl.setMinimumHeight(120)
        rfl.addWidget(self._rooms_tbl)

        lf = QFrame(); lf.setStyleSheet(f'background: {PANEL}; border: 1px solid {BORDER}; border-radius: 10px;')
        lfl = QVBoxLayout(lf); lfl.setContentsMargins(12, 12, 12, 12); lfl.setSpacing(8)
        lt = QHBoxLayout(); ll = QLabel('Activity Log'); ll.setStyleSheet(f'color: {MUTED}; font-size: 10px; font-weight: 700; letter-spacing: 0.8px;')
        lt.addWidget(ll); lt.addStretch()
        bc = QPushButton('Clear'); bc.setFixedHeight(22); bc.setStyleSheet(f'font-size: 10px; padding: 2px 8px; color: {MUTED}; background: transparent; border: 1px solid {BORDER}; border-radius: 4px;')
        bc.clicked.connect(lambda: (_log_q.clear(), self._update_log()))
        lt.addWidget(bc); lfl.addLayout(lt)
        self._log_box = QTextEdit(); self._log_box.setReadOnly(True); self._log_box.setMinimumHeight(120)
        lfl.addWidget(self._log_box)

        r4.addWidget(rf, 55); r4.addWidget(lf, 45); root.addLayout(r4)
        root.addStretch()

        btn_sd = QPushButton('✕   Matikan Keseluruhan Server'); btn_sd.setProperty('role', 'shutdown')
        btn_sd.clicked.connect(self._shutdown); root.addWidget(btn_sd)

    def _build_database_tab(self):
        self._tab_database = QWidget()
        root = QVBoxLayout(self._tab_database)
        root.setContentsMargins(24, 18, 24, 18)
        root.setSpacing(12)

        hl = QHBoxLayout()
        lbl = QLabel('Katalog Data Film'); lbl.setStyleSheet('font-size: 18px; font-weight: 700; color: white;')
        hl.addWidget(lbl); hl.addStretch()

        self._search = QLineEdit(); self._search.setPlaceholderText('🔍  Cari judul, genre...'); self._search.setFixedWidth(220)
        self._search.textChanged.connect(self._filter_table)

        btn_add = QPushButton('➕  Tambah Film'); btn_add.setProperty('role', 'accent'); btn_add.clicked.connect(self._action_add)
        btn_conv = QPushButton('🎬  Konversi Video'); btn_conv.clicked.connect(lambda: ConvertVideoDialog(self).exec())
        btn_ref = QPushButton('↻'); btn_ref.setFixedWidth(34); btn_ref.setProperty('role', 'ghost'); btn_ref.clicked.connect(self._refresh_table)

        hl.addWidget(self._search); hl.addWidget(btn_add); hl.addWidget(btn_conv); hl.addWidget(btn_ref)
        root.addLayout(hl)

        self._lbl_count = QLabel('— film terdaftar'); self._lbl_count.setStyleSheet(f'color: {MUTED}; font-size: 12px;')
        root.addWidget(self._lbl_count)

        self._table = QTableWidget(0, 9)
        self._table.setHorizontalHeaderLabels(['No.', 'ID', 'Judul Film', 'Genre', 'Tahun', 'Durasi', 'Rating', 'Sub', 'Aksi'])
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        self._table.setColumnWidth(0, 44); self._table.setColumnWidth(1, 44); self._table.setColumnWidth(4, 55)
        self._table.setColumnWidth(5, 60); self._table.setColumnWidth(6, 60); self._table.setColumnWidth(7, 44)
        self._table.setColumnWidth(8, 140) 
        root.addWidget(self._table)

        self._all_films = []
        self._refresh_table()

    def _refresh_metrics(self):
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory()
        self._c_cpu.update_value(f'{cpu:.1f}%', bar_pct=int(cpu))
        self._c_ram.update_value(f'{ram.percent:.1f}%', sub=f'{ram.used//(1024**3):.1f} / {ram.total//(1024**3):.1f} GB', bar_pct=int(ram.percent))
        try:
            disk = psutil.disk_usage('/')
            self._c_disk.update_value(f'{disk.percent:.1f}%', sub=f'{disk.free / (1024 ** 3):.1f} GB free', bar_pct=int(disk.percent))
        except: pass
        try:
            net = psutil.net_io_counters()
            sk  = (net.bytes_sent - self._net_sent_prev) / 1024
            rk  = (net.bytes_recv - self._net_recv_prev) / 1024
            self._net_sent_prev, self._net_recv_prev = net.bytes_sent, net.bytes_recv
            self._c_net.update_value(f'↑ {sk:.0f} KB/s', sub=f'↓ {rk:.0f} KB/s recv')
        except: pass
        try:
            r = requests.get(f'http://127.0.0.1:{FLASK_PORT}/api/status', timeout=1)
            if r.ok:
                d = r.json(); sec = d.get('uptime', 0); users = d.get('users', 0); rooms = d.get('rooms', 0)
                h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
                self._c_up.update_value(f'{h:02d}:{m:02d}:{s:02d}')
                self._c_users.update_value(f'{users} Orang', sub='sedang online' if users else 'tidak ada')
                self._c_rooms.update_value(f'{rooms} Room', sub='aktif' if rooms else 'tidak ada')
                self._prev_rooms, self._prev_users = rooms, users
        except: pass
        try:
            r = requests.get(f'http://127.0.0.1:{FLASK_PORT}/api/rooms/active', timeout=1)
            if r.ok: self._update_rooms_table(r.json())
        except: pass
        try:
            count = len(get_all_films())
            self._c_films.update_value(f'{count} Film'); self._lbl_count.setText(f'{count} film terdaftar')
        except: pass
        if cpu > 85: _push_log(f'⚠ CPU tinggi: {cpu:.1f}%', 'warning')
        if ram.percent > 90: _push_log(f'⚠ RAM kritis: {ram.percent:.1f}%', 'warning')
        self._update_log()

    def _update_rooms_table(self, rooms: list):
        self._rooms_tbl.setRowCount(0)
        if not rooms:
            self._rooms_tbl.insertRow(0)
            it = QTableWidgetItem('Belum ada watch party aktif'); it.setForeground(QColor(MUTED)); it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._rooms_tbl.setItem(0, 0, it); self._rooms_tbl.setSpan(0, 0, 1, 4); return
        for i, room in enumerate(rooms):
            self._rooms_tbl.insertRow(i)
            code_it = QTableWidgetItem(room.get('code', '')); code_it.setForeground(QColor(ACCENT)); code_it.setFont(QFont('Consolas', 11, QFont.Weight.Bold))
            self._rooms_tbl.setItem(i, 0, code_it)
            self._rooms_tbl.setItem(i, 1, QTableWidgetItem(room.get('film_title', '—')))
            self._rooms_tbl.setItem(i, 2, QTableWidgetItem(room.get('host', '—')))
            cnt = QTableWidgetItem(f"{room.get('users_count', 0)} user"); cnt.setForeground(QColor(GREEN))
            self._rooms_tbl.setItem(i, 3, cnt)

    def _update_log(self):
        icons = {'info': '○', 'success': '●', 'warning': '△', 'error': '✕'}
        colors = {'info': TEXT, 'success': GREEN, 'warning': YELLOW, 'error': ACCENT}
        lines = []
        for ts, lv, msg in list(_log_q)[-50:]:
            ic = icons.get(lv, '○'); c  = colors.get(lv, TEXT)
            lines.append(f'<span style="color:{MUTED};">[{ts}]</span> <span style="color:{c};">{ic} {msg}</span>')
        self._log_box.setHtml('<br>'.join(lines))
        sb = self._log_box.verticalScrollBar(); sb.setValue(sb.maximum())

    def _refresh_table(self):
        self._all_films = [dict(row) for row in get_all_films()]
        self._lbl_count.setText(f'{len(self._all_films)} film terdaftar')
        self._render_table(self._all_films)

    def _filter_table(self, text: str):
        q = text.lower()
        filtered = [f for f in self._all_films if q in f['title'].lower() or q in (f.get('genre') or '').lower()]
        self._render_table(filtered)

    def _render_table(self, films: list):
        self._table.setRowCount(0)
        for ri, film in enumerate(films):
            self._table.insertRow(ri); self._table.setRowHeight(ri, 42)
            def cell(text, align=Qt.AlignmentFlag.AlignVCenter, color=None):
                it = QTableWidgetItem(str(text)); it.setTextAlignment(align | Qt.AlignmentFlag.AlignLeft)
                if color: it.setForeground(QColor(color))
                return it

            no_it = QTableWidgetItem(str(ri + 1)); no_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter); no_it.setForeground(QColor(MUTED))
            self._table.setItem(ri, 0, no_it)
            id_it = QTableWidgetItem(str(film['id'])); id_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter); id_it.setForeground(QColor(MUTED))
            self._table.setItem(ri, 1, id_it)
            self._table.setItem(ri, 2, cell(film['title']))
            self._table.setItem(ri, 3, cell(film.get('genre') or '—', color=BLUE))
            
            yr = QTableWidgetItem(str(film.get('year') or '—')); yr.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(ri, 4, yr)
            
            dur_str = f"{film.get('duration', 0)}m" if film.get('duration') else '—'
            dur_it = QTableWidgetItem(dur_str); dur_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(ri, 5, dur_it)

            rat_val = film.get('rating')
            rat_str = f"★ {rat_val}" if rat_val else '—'
            rat_it = QTableWidgetItem(rat_str); rat_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter); rat_it.setForeground(QColor(YELLOW))
            self._table.setItem(ri, 6, rat_it)

            has_sub = bool(film.get('has_subtitle', 0))
            sub_it = QTableWidgetItem('✓' if has_sub else '✗'); sub_it.setTextAlignment(Qt.AlignmentFlag.AlignCenter); sub_it.setForeground(QColor(GREEN if has_sub else MUTED))
            self._table.setItem(ri, 7, sub_it)

            aw = QWidget(); al = QHBoxLayout(aw); al.setContentsMargins(4, 4, 4, 4); al.setSpacing(6)
            
            btn_edit = QPushButton('Edit')
            btn_edit.setFixedSize(55, 28)
            btn_edit.setStyleSheet(f'QPushButton {{ background: {PANEL2}; border: 1px solid {BORDER2}; border-radius: 5px; color: {BLUE}; font-size: 12px; font-weight: bold; }} QPushButton:hover {{ border-color: {BLUE}; background: rgba(88,166,255,0.1); }}')
            btn_edit.clicked.connect(lambda _, f=film: self._action_edit(f))
            
            btn_del = QPushButton('Hapus')
            btn_del.setFixedSize(60, 28)
            btn_del.setStyleSheet(f'QPushButton {{ background: {PANEL2}; border: 1px solid {BORDER2}; border-radius: 5px; color: {ACCENT}; font-size: 12px; font-weight: bold; }} QPushButton:hover {{ border-color: {ACCENT}; background: rgba(229,9,20,0.1); }}')
            btn_del.clicked.connect(lambda _, fid=film['id'], ft=film['title']: self._action_delete(fid, ft))
            
            al.addWidget(btn_edit); al.addWidget(btn_del); self._table.setCellWidget(ri, 8, aw)

    def _action_add(self):
        dlg = AddFilmDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted: self._refresh_table()

    def _action_edit(self, film: dict):
        dlg = EditFilmDialog(film, self)
        if dlg.exec() == QDialog.DialogCode.Accepted: self._refresh_table()

    def _action_delete(self, fid: int, title: str):
        reply = QMessageBox.question(self, 'Konfirmasi Hapus', f'Yakin hapus film:\n"{title}"?\n\nAksi ini tidak dapat dibatalkan.', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            delete_film(fid); _push_log(f"Film dihapus: '{title}'", 'warning'); self._refresh_table()

    def _copy_lan_url(self):
        url = f'http://{self._local_ip}:{NGINX_PORT}'
        QApplication.clipboard().setText(url)
        QMessageBox.information(self, 'Tersalin!', f'URL jaringan disalin ke clipboard:\n\n{url}')

    def _shutdown(self):
        reply = QMessageBox.question(self, 'Matikan Server', 'Matikan semua layanan CineStream?\n\nSemua pengguna yang sedang menonton akan terputus.', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes: self._timer.stop(); QApplication.quit(); os._exit(0)

def show_toast_msg(parent, text):
    msg = QMessageBox(parent)
    msg.setWindowTitle("Info Metadata")
    msg.setText(text)
    msg.setStyleSheet(QSS)
    msg.exec()

def main():
    init_db()
    _push_log('Database diinisialisasi.', 'success')
    app = QApplication(sys.argv); app.setStyle('Fusion')
    threading.Thread(target=_run_flask, daemon=True, name='Flask').start()
    _push_log(f'Flask server dimulai di port {FLASK_PORT}.', 'success')
    dashboard = CineStreamDashboard(); dashboard.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()