"""
CineStream Modern Launcher (PyQt6 Edition)
------------------------------------------
Menjalankan Server Flask API + SocketIO, serta menampilkan
menu tray kustom berwarna hitam modern sesuai mockup UI.
"""

import sys
import os
import threading
import webbrowser
import socket
import sqlite3
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QSystemTrayIcon, QLineEdit, QMessageBox, QDialog)
from PyQt6.QtGui import QIcon, QColor, QPainter, QPixmap
from PyQt6.QtCore import Qt, QPoint
import psutil

# Tambahkan folder server ke Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))

from app import create_app, socketio
from database import DB_PATH, init_db

FLASK_PORT = 5000
NGINX_PORT = 8080  # Port utama yang diakses user melalui Nginx

# ── Validasi SQLite & Health Check ───────────────────────────────────────────
def check_database_health():
    print(f"[⚙️] Memeriksa jalur database: {DB_PATH}")
    try:
        if not os.path.exists(DB_PATH):
            print("[-] Database belum ada. Menginisialisasi database baru...")
        
        # Jalankan init_db untuk memastikan skema tabel lengkap
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

# ── Fungsi Pendukung Jaringan ────────────────────────────────────────────────
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
    # Flask berjalan di port internal 5000, Nginx akan mem-proxy ke sini
    socketio.run(app, host='127.0.0.1', port=FLASK_PORT, debug=False, use_reloader=False)

# ── Pembuat Ikon Flat untuk System Tray ──────────────────────────────────────
def create_tray_icon():
    """Membuat logo lingkaran merah minimalis sebagai ikon di taskbar"""
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#E50914")) # Merah Sinema
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(4, 4, 24, 24)
    painter.end()
    return QIcon(pixmap)

# ── Dialog Tambah Film Baru (GUI Berbasis SQLite) ───────────────────────────
class AddFilmDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CineStream - Tambah Film")
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
            # Panggil fungsi add_film dari database.py yang sudah ada
            from database import add_film
            # Gunakan nilai default jika kosong
            add_film(
                title=title,
                description=self.desc_input.text() or "Deskripsi tidak tersedia.",
                genre=self.genre_input.text() or "Film",
                year=2026, # Default
                duration=0, # Default
                poster_url=self.poster_input.text() or "",
                hls_path=hls_path
            )
            QMessageBox.information(self, "Sukses", f"Film '{title}' berhasil ditambahkan ke katalog!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", str(e))

# ── UI Jendela Menu Tray Kustom (Warna Hitam) ────────────────────────────────
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
            /* ... (Gunakan CSS styling hitam yang sama seperti kode sebelumnya) ... */
            QWidget#Container { background-color: #121212; border: 1px solid #282828; border-radius: 12px; }
            QLabel { font-family: 'Segoe UI'; color: #FFFFFF; }
            QPushButton { background-color: #1E1E1E; color: #E0E0E0; border: 1px solid #2D2D2D; border-radius: 6px; padding: 10px 14px; text-align: left; }
            QPushButton:hover { background-color: #2A2A2A; color: #FFFFFF; border-color: #404040; }
        """)
        
        container_layout = QVBoxLayout(container)
        
        # Header Status
        header = QLabel("<b>CineStream Server</b><br><span style='color:#2ECC71;'>● Nginx & Flask Aktif</span>")
        container_layout.addWidget(header)
        
        # Tombol Aksi Standard
        btn_open = QPushButton("🌐  Buka di Browser")
        btn_open.clicked.connect(self.action_open)
        container_layout.addWidget(btn_open)

        btn_copy = QPushButton(f"🔗  Salin IP Jaringan ({self.local_ip})")
        btn_copy.clicked.connect(lambda: copy_to_clipboard(f"http://{self.local_ip}:8080"))
        container_layout.addWidget(btn_copy)
        
        # --- Fitur Baru: Status Server ---
        btn_status = QPushButton("📊  Status Server")
        btn_status.clicked.connect(self.action_show_status)
        container_layout.addWidget(btn_status)

        # Garis Pembatas
        line = QWidget(); line.setFixedHeight(1); line.setStyleSheet("background-color: #282828;")
        container_layout.addWidget(line)

        # --- Fitur Baru: Tambah Film ---
        btn_add = QPushButton("📁  Tambah Film Baru")
        btn_add.clicked.connect(self.action_add_film)
        container_layout.addWidget(btn_add)
        
        btn_quit = QPushButton("❌  Keluar")
        btn_quit.clicked.connect(self.action_quit)
        container_layout.addWidget(btn_quit)
        
        main_layout.addWidget(container)
        self.setLayout(main_layout)
        self.setFixedSize(290, 320)

    def position_at_tray(self):
        # ... (Gunakan logika penempatan koordinat dari kode sebelumnya) ...
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
        # Mengambil penggunaan resource sistem
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

    def action_add_film(self):
        self.hide() # Sembunyikan menu tray saat dialog muncul
        dialog = AddFilmDialog(self)
        dialog.exec()

    def action_quit(self):
        QApplication.quit()
        os._exit(0)

    def changeEvent(self, event):
        # Otomatis sembunyikan menu jika pengguna mengklik aplikasi lain diluar tray
        if event.type() == event.Type.ActivationChange and not self.isActiveWindow():
            self.hide()

# ── Main Entry Execution ─────────────────────────────────────────────────────
def main():
    # 1. Jalankan Health Check Database SQLite terlebih dahulu
    if not check_database_health():
        print("[❌] Inisialisasi dibatalkan karena kegagalan struktur database.")
        sys.exit(1)

    # 2. Setup Qt Application Context
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # 3. Jalankan Engine Flask API di Core Thread terpisah
    server_thread = threading.Thread(target=run_flask, daemon=True, name='CineStream-Flask-Engine')
    server_thread.start()
    
    # 4. Bangun Komponen Tray Utama
    tray_icon = QSystemTrayIcon(create_tray_icon(), app)
    tray_icon.setToolTip("CineStream Infrastructure Core")
    
    # 5. Pasang Jendela Hitam Kustom ke Interaksi Klik Tray
    menu_window = ModernTrayMenu(tray_icon)
    tray_icon.activated.connect(menu_window.show_toggle)
    
    tray_icon.show()
    
    # 6. Otomatis buka browser ke arah port Nginx (8080) setelah inisialisasi selesai
    print(f"[🚀] Server aktif. Mengalihkan visual utama ke http://localhost:{NGINX_PORT}")
    threading.Timer(2.0, lambda: webbrowser.open(f"http://localhost:{NGINX_PORT}")).start()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()