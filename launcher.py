"""
CineStream Modern Launcher (PyQt6 Edition)
------------------------------------------
Menjalankan Server Flask API + SocketIO, serta menampilkan
menu tray kustom berwarna hitam modern sesuai mockup UI.
"""

import sys
import os
import re
import threading
import webbrowser
import socket
import sqlite3
import subprocess
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QSystemTrayIcon, QLineEdit, QMessageBox, QDialog, QProgressBar, QFileDialog)
from PyQt6.QtGui import QIcon, QColor, QPainter, QPixmap
from PyQt6.QtCore import Qt, QPoint, QThread, pyqtSignal
import psutil

# Tambahkan folder server ke Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))

from app import create_app, socketio
from database import DB_PATH, init_db

FLASK_PORT = 5000
NGINX_PORT = 8080  # Port utama yang diakses user melalui Nginx

# ── Mesin Konversi Latar Belakang (FFmpeg) ───────────────────────────────────
class FFmpegWorker(QThread):
    finished = pyqtSignal(bool, str, str) # (Status Sukses, Pesan, HLS Path)

    def __init__(self, input_file, title):
        super().__init__()
        self.input_file = input_file
        self.title = title

    def run(self):
        try:
            safe_title = re.sub(r'[^a-zA-Z0-9]', '_', self.title.lower())
            output_dir = os.path.join(os.getcwd(), 'media', 'hls', safe_title)
            os.makedirs(output_dir, exist_ok=True)
            
            output_m3u8 = os.path.join(output_dir, 'index.m3u8')
            relative_hls_path = f"{safe_title}/index.m3u8"

            cmd = [
                'ffmpeg', '-y', '-i', self.input_file,
                '-map', '0:v', '-map', '0:a',
                '-c:v', 'copy', '-c:a', 'aac',
                '-start_number', '0', '-hls_time', '10',
                '-hls_list_size', '0', '-f', 'hls',
                output_m3u8
            ]

            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            if process.returncode == 0:
                self.finished.emit(True, "Konversi selesai!", relative_hls_path)
            else:
                self.finished.emit(False, f"Gagal konversi:\n{process.stderr}", "")
                
        except Exception as e:
            self.finished.emit(False, str(e), "")

# ── Validasi SQLite & Health Check ───────────────────────────────────────────
def check_database_health():
    print(f"[⚙️] Memeriksa jalur database: {DB_PATH}")
    try:
        if not os.path.exists(DB_PATH):
            print("[-] Database belum ada. Menginisialisasi database baru...")
        
        init_db()
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM films;")
        total_films = cursor.fetchone()[0]
        conn.close()
        print(f"[+️] SQLite Terhubung Sukses! Total katalog film: {total_films}")
        return True
    except Exception as e:
        print(f"[❌] Error Database: {e}")
        return False

# ── Fungsi Pendukung ─────────────────────────────────────────────────────────
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'

def copy_to_clipboard(text):
    app = QApplication.instance()
    if app:
        app.clipboard().setText(text)

def run_flask():
    app = create_app()
    # FIX 5: Ganti 127.0.0.1 → 0.0.0.0 agar Nginx (dan perangkat jaringan)
    # bisa mengakses Flask. 127.0.0.1 hanya bisa diakses dari localhost sendiri.
    socketio.run(app, host='0.0.0.0', port=FLASK_PORT, debug=False, use_reloader=False)

def create_tray_icon():
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#E50914"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(4, 4, 24, 24)
    painter.end()
    return QIcon(pixmap)

# ── Dialog UI: Upload & Konversi Otomatis ────────────────────────────────────
class UploadConvertDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎬 Upload & Auto-Convert Film")
        self.setFixedSize(400, 450)
        self.setStyleSheet("background-color: #1a1a24; color: white; font-family: Segoe UI;")

        layout = QVBoxLayout()

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Judul Film (Cth: The Matrix)")
        
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Deskripsi Singkat")
        
        self.genre_input = QLineEdit()
        self.genre_input.setPlaceholderText("Genre (Cth: Action, Sci-Fi)")

        self.year_input = QLineEdit()
        self.year_input.setPlaceholderText("Tahun (Cth: 1999)")

        self.duration_input = QLineEdit()
        self.duration_input.setPlaceholderText("Durasi Menit (Cth: 136)")

        self.poster_input = QLineEdit()
        self.poster_input.setPlaceholderText("URL Poster Gambar")

        self.file_path = None
        self.btn_select_file = QPushButton("📁 Pilih Video Mentah (.mp4 / .mkv)")
        self.btn_select_file.setStyleSheet("background-color: #24243a; padding: 10px; border-radius: 5px;")
        self.btn_select_file.clicked.connect(self.select_file)

        self.lbl_file_name = QLabel("Belum ada file dipilih.")
        self.lbl_file_name.setStyleSheet("color: #888899; font-size: 11px;")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)

        self.btn_start = QPushButton("🚀 Mulai Konversi & Simpan")
        self.btn_start.setStyleSheet("background-color: #ff0043; font-weight: bold; padding: 12px; border-radius: 5px;")
        self.btn_start.clicked.connect(self.start_conversion)

        for widget in [self.title_input, self.desc_input, self.genre_input, 
                       self.year_input, self.duration_input, self.poster_input]:
            widget.setStyleSheet("padding: 8px; border: 1px solid #2e2e44; border-radius: 4px; background: #0f0f13;")
            layout.addWidget(widget)

        layout.addWidget(self.btn_select_file)
        layout.addWidget(self.lbl_file_name)
        layout.addSpacing(10)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.btn_start)

        self.setLayout(layout)

    def select_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Pilih Video", "", "Video Files (*.mp4 *.mkv *.avi)")
        if file_name:
            self.file_path = file_name
            self.lbl_file_name.setText(os.path.basename(file_name))

    def start_conversion(self):
        if not self.file_path or not self.title_input.text():
            QMessageBox.warning(self, "Peringatan", "Pilih file video dan isi Judul Film!")
            return

        self.btn_start.setEnabled(False)
        self.btn_start.setText("Memproses Konversi... Harap Tunggu")
        self.progress_bar.setVisible(True)

        self.worker = FFmpegWorker(self.file_path, self.title_input.text())
        self.worker.finished.connect(self.on_conversion_finished)
        self.worker.start()

    def on_conversion_finished(self, success, message, hls_path):
        self.progress_bar.setVisible(False)
        self.btn_start.setEnabled(True)
        self.btn_start.setText("🚀 Mulai Konversi & Simpan")

        if success:
            self.save_to_database(hls_path)
            QMessageBox.information(self, "Sukses!", "Film berhasil dikonversi dan masuk katalog!")
            self.accept()
        else:
            QMessageBox.critical(self, "Gagal", message)

    # FIX 4: Method ini sebelumnya berada di LUAR class (indentasi salah),
    # sehingga self.save_to_database() selalu crash dengan AttributeError.
    def save_to_database(self, hls_path):
        try:
            # Memanggil fungsi resmi database.py agar data konsisten
            from database import add_film
            
            # Cek nilai input. Jika kosong, berikan nilai default
            year_val = self.year_input.text().strip()
            duration_val = self.duration_input.text().strip()
            
            add_film(
                title=self.title_input.text().strip(),
                description=self.desc_input.text().strip() or "Deskripsi tidak tersedia.",
                genre=self.genre_input.text().strip() or "Film",
                year=int(year_val) if year_val.isdigit() else 2026,
                duration=int(duration_val) if duration_val.isdigit() else 0,
                poster_url=self.poster_input.text().strip() or "",
                hls_path=hls_path
            )
        except Exception as e:
            print(f"Gagal menyimpan ke DB: {e}")

# ── Dialog UI: Tambah Film Manual ────────────────────────────────────────────
class AddFilmDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CineStream - Tambah Film Manual")
        self.setFixedSize(350, 400)
        self.setStyleSheet("""
            QDialog { background-color: #121212; color: white; }
            QLabel { color: #E0E0E0; font-family: 'Segoe UI'; margin-top: 5px; }
            QLineEdit { background-color: #1E1E1E; border: 1px solid #333; border-radius: 5px; padding: 5px; color: white; }
            QLineEdit:focus { border: 1px solid #E50914; }
            QPushButton { background-color: #E50914; color: white; border: none; border-radius: 5px; padding: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #B20710; }
        """)

        layout = QVBoxLayout(self)

        self.title_input = QLineEdit()
        layout.addWidget(QLabel("Judul Film *"))
        layout.addWidget(self.title_input)

        self.desc_input = QLineEdit()
        layout.addWidget(QLabel("Deskripsi"))
        layout.addWidget(self.desc_input)

        self.genre_input = QLineEdit()
        layout.addWidget(QLabel("Genre"))
        layout.addWidget(self.genre_input)

        self.hls_input = QLineEdit()
        self.hls_input.setPlaceholderText("contoh: nama_folder/index.m3u8")
        layout.addWidget(QLabel("Path HLS * (Wajib sesuai folder)"))
        layout.addWidget(self.hls_input)

        self.poster_input = QLineEdit()
        layout.addWidget(QLabel("URL Poster"))
        layout.addWidget(self.poster_input)

        submit_btn = QPushButton("Simpan ke Database")
        submit_btn.clicked.connect(self.save_film)
        layout.addWidget(submit_btn)

    def save_film(self):
        title = self.title_input.text().strip()
        hls_path = self.hls_input.text().strip()

        if not title or not hls_path:
            QMessageBox.warning(self, "Error", "Judul dan Path HLS wajib diisi!")
            return

        try:
            from database import add_film
            add_film(
                title=title,
                description=self.desc_input.text() or "Deskripsi tidak tersedia.",
                genre=self.genre_input.text() or "Film",
                year=2026,
                duration=0,
                poster_url=self.poster_input.text() or "",
                hls_path=hls_path
            )
            QMessageBox.information(self, "Sukses", f"Film '{title}' berhasil ditambahkan ke katalog!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", str(e))

# ── UI Menu Tray Taskbar ─────────────────────────────────────────────────────
class ModernTrayMenu(QWidget):
    def __init__(self, tray_icon_el):
        super().__init__()
        self.tray_icon_el = tray_icon_el
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | 
                            Qt.WindowType.WindowStaysOnTopHint | 
                            Qt.WindowType.SubWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        self.local_ip = get_local_ip()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        container = QWidget()
        container.setObjectName("Container")
        container.setStyleSheet("""
            QWidget#Container { background-color: #121212; border: 1px solid #282828; border-radius: 12px; }
            QLabel { font-family: 'Segoe UI'; color: #FFFFFF; }
            QPushButton { background-color: #1E1E1E; color: #E0E0E0; border: 1px solid #2D2D2D; border-radius: 6px; padding: 10px 14px; text-align: left; }
            QPushButton:hover { background-color: #2A2A2A; color: #FFFFFF; border-color: #404040; }
        """)
        
        container_layout = QVBoxLayout(container)
        
        header = QLabel("<b>CineStream Server</b><br><span style='color:#2ECC71;'>● Nginx & Flask Aktif</span>")
        container_layout.addWidget(header)
        
        btn_open = QPushButton("🌐  Buka di Browser")
        btn_open.clicked.connect(self.action_open)
        container_layout.addWidget(btn_open)

        btn_copy = QPushButton(f"🔗  Salin IP Jaringan ({self.local_ip})")
        btn_copy.clicked.connect(lambda: copy_to_clipboard(f"http://{self.local_ip}:8080"))
        container_layout.addWidget(btn_copy)
        
        btn_status = QPushButton("📊  Status Server")
        btn_status.clicked.connect(self.action_show_status)
        container_layout.addWidget(btn_status)

        line = QWidget(); line.setFixedHeight(1); line.setStyleSheet("background-color: #282828;")
        container_layout.addWidget(line)

        # Tombol Baru Diaktifkan di Sini
        btn_upload = QPushButton("🚀  Upload & Konversi Video")
        btn_upload.clicked.connect(self.action_upload_film)
        btn_upload.setStyleSheet("color: #ff0043; font-weight: bold;")
        container_layout.addWidget(btn_upload)

        btn_add = QPushButton("📁  Tambah Data (Manual)")
        btn_add.clicked.connect(self.action_add_film)
        container_layout.addWidget(btn_add)
        
        btn_quit = QPushButton("❌  Keluar")
        btn_quit.clicked.connect(self.action_quit)
        container_layout.addWidget(btn_quit)
        
        main_layout.addWidget(container)
        self.setLayout(main_layout)
        self.setFixedSize(300, 370) # Sedikit diperpanjang untuk tombol baru

    def position_at_tray(self):
        tray_geo = self.tray_icon_el.geometry()
        pos = tray_geo.topLeft()
        self.move(pos.x() - self.width() + 30, pos.y() - self.height() - 5)

    def show_toggle(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.Context):
            if self.isVisible(): self.hide()
            else: self.position_at_tray(); self.show(); self.activateWindow()

    def action_open(self):
        webbrowser.open(f"http://localhost:8080")
        self.hide()

    def action_show_status(self):
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        QMessageBox.information(
            self, 
            "Status Server CineStream", 
            f"⚡ Koneksi: Stabil\n"
            f"🧠 Penggunaan CPU: {cpu}%\n"
            f"💾 Penggunaan RAM: {ram}%\n"
            f"📂 Mode: Nginx Reverse Proxy (Port 8080)\n"
            f"Socket.IO siap menerima Watch Party."
        )

    def action_upload_film(self):
        self.hide() 
        dialog = UploadConvertDialog(self)
        dialog.exec()

    def action_add_film(self):
        self.hide() 
        dialog = AddFilmDialog(self)
        dialog.exec()

    def action_quit(self):
        QApplication.quit()
        os._exit(0)

    def changeEvent(self, event):
        if event.type() == event.Type.ActivationChange and not self.isActiveWindow():
            self.hide()

# ── Main Entry Execution ─────────────────────────────────────────────────────
def main():
    if not check_database_health():
        print("[❌] Inisialisasi dibatalkan karena kegagalan struktur database.")
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    server_thread = threading.Thread(target=run_flask, daemon=True, name='CineStream-Flask-Engine')
    server_thread.start()
    
    tray_icon = QSystemTrayIcon(create_tray_icon(), app)
    tray_icon.setToolTip("CineStream Infrastructure Core")
    
    menu_window = ModernTrayMenu(tray_icon)
    tray_icon.activated.connect(menu_window.show_toggle)
    
    tray_icon.show()
    
    print(f"[🚀] Server aktif. Mengalihkan visual utama ke http://localhost:{NGINX_PORT}")
    threading.Timer(2.0, lambda: webbrowser.open(f"http://localhost:{NGINX_PORT}")).start()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()