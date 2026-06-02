# launcher.py
import sys, os, re, threading, time, shutil, sqlite3, subprocess, webbrowser
import requests # Pastikan pip install requests
import psutil   # Pastikan pip install psutil
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QLineEdit, QMessageBox, QDialog, 
                             QProgressBar, QFileDialog, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QTextEdit, QTabWidget, QGridLayout)
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))

from app import create_app, socketio
from database import DB_PATH, init_db, get_all_films, delete_film, add_film

FLASK_PORT = 5000
NGINX_PORT = 8080
app_flask = create_app()

def run_flask():
    socketio.run(app_flask, host='0.0.0.0', port=FLASK_PORT, debug=False, use_reloader=False)

# ── FFmpeg Worker (Dengan Fitur Pembatalan) ──
class FFmpegWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str, str)

    def __init__(self, input_file, title):
        super().__init__()
        self.input_file = input_file
        self.title = title
        self._is_cancelled = False
        self.process = None
        self.output_dir = ""

    def stop(self):
        """Memicu penghentian paksa proses FFmpeg"""
        self._is_cancelled = True
        if self.process:
            self.process.kill()

    def run(self):
        try:
            safe_title = re.sub(r'[^a-zA-Z0-9]', '_', self.title.lower())
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.output_dir = os.path.join(base_dir, 'media', 'hls', safe_title)
            os.makedirs(self.output_dir, exist_ok=True)
            output_m3u8 = os.path.join(self.output_dir, 'index.m3u8')
            
            cmd = [
                'ffmpeg', '-y', '-i', os.path.normpath(self.input_file),
                '-c:v', 'libx264', '-profile:v', 'high', '-pix_fmt', 'yuv420p',
                '-level', '4.1', '-s', '1280x720',
                '-start_number', '0', '-hls_time', '10', '-hls_list_size', '0',
                '-f', 'hls', os.path.normpath(output_m3u8)
            ]
            
            self.process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                universal_newlines=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            while True:
                if self._is_cancelled:
                    break
                line = self.process.stdout.readline()
                if not line: break
                if "frame=" in line: self.progress.emit(50)
                    
            self.process.wait()
            
            if self._is_cancelled:
                shutil.rmtree(self.output_dir, ignore_errors=True) # Bersihkan file sampah
                self.finished.emit(False, "Konversi dibatalkan. File sementara dihapus.", "")
            elif self.process.returncode == 0:
                self.progress.emit(100)
                self.finished.emit(True, f"Sukses mengonversi {self.title}!", self.output_dir)
            else:
                self.finished.emit(False, f"Error Code: {self.process.returncode}", "")
        except Exception as e:
            self.finished.emit(False, str(e), "")

# ── DIALOG KONVERSI ──
class ConvertVideoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mesin Konversi Video")
        self.resize(500, 300)
        self.setStyleSheet(parent.styleSheet())
        layout = QVBoxLayout(self)
        
        self.txt_title = QLineEdit()
        self.txt_title.setPlaceholderText("Judul Output...")
        layout.addWidget(self.txt_title)
        
        file_layout = QHBoxLayout()
        self.txt_file_path = QLineEdit()
        self.txt_file_path.setPlaceholderText("Pilih video sumber...")
        btn_browse = QPushButton("Browse")
        btn_browse.clicked.connect(self.browse_video)
        file_layout.addWidget(self.txt_file_path)
        file_layout.addWidget(btn_browse)
        layout.addLayout(file_layout)
        
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        self.lbl_status = QLabel("Status: Menunggu...")
        layout.addWidget(self.lbl_status)
        
        # Tombol Aksi
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("Mulai Konversi")
        self.btn_start.setObjectName("btn-accent")
        self.btn_start.clicked.connect(self.start_conversion)
        
        self.btn_cancel = QPushButton("Batalkan & Hapus")
        self.btn_cancel.setObjectName("btn-danger")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_conversion)
        
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def browse_video(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Pilih Video", "", "Video (*.mp4 *.mkv)")
        if file_path:
            self.txt_file_path.setText(file_path)
            if not self.txt_title.text():
                self.txt_title.setText(os.path.splitext(os.path.basename(file_path))[0])

    def start_conversion(self):
        if not self.txt_file_path.text(): return
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.lbl_status.setText("Memproses...")
        self.worker = FFmpegWorker(self.txt_file_path.text(), self.txt_title.text())
        self.worker.progress.connect(lambda val: self.progress_bar.setValue(val))
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def cancel_conversion(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.lbl_status.setText("Membatalkan proses dan membersihkan folder...")
            self.worker.stop()
            self.worker.wait()
            self.accept()

    def on_finished(self, success, msg, path):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        if success:
            QMessageBox.information(self, "Sukses", f"{msg}\nDisimpan di: {path}")
            self.accept()
        else:
            QMessageBox.warning(self, "Berhenti", msg)

# ── DASHBOARD UTAMA (SPLIT TABS) ──
class CineStreamDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CineStream Infrastructure Manager")
        self.resize(1150, 720)
        self.local_ip = self.get_local_ip()
        
        self.setStyleSheet("""
            QMainWindow, QTabWidget::pane { background-color: #0a0b10; border: none; }
            QWidget { color: #e8e8f0; font-family: 'Segoe UI'; }
            QTabBar::tab { background: #161823; border: 1px solid #2a2d3e; padding: 10px 25px; margin-right: 2px; font-weight: bold; border-top-left-radius: 6px; border-top-right-radius: 6px; }
            QTabBar::tab:selected { background: #ff0043; color: white; border-color: #ff0043; }
            QPushButton { background-color: #161823; border: 1px solid #2a2d3e; border-radius: 6px; padding: 10px; font-weight: bold; }
            QPushButton:hover { background-color: #222534; border-color: #ff0043; }
            QPushButton#btn-accent { background-color: #ff0043; color: white; border: none; }
            QPushButton#btn-danger { background-color: #3a121a; color: #ff3366; }
            QTableWidget { background-color: #161823; border: 1px solid #2a2d3e; border-radius: 8px; }
            QHeaderView::section { background-color: #1c1e2e; color: #ff0043; padding: 8px; font-weight: bold; }
            /* Stat Card */
            .StatCard { background-color: #141520; border: 1px solid #222435; border-radius: 10px; padding: 15px; }
        """)

        # Main Tab Layout
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # TAB 1: SERVER MONITORING
        self.tab_monitor = QWidget()
        self.setup_monitor_tab()
        self.tabs.addTab(self.tab_monitor, "📊 Server Monitoring")
        
        # TAB 2: DATABASE MANAGEMENT
        self.tab_database = QWidget()
        self.setup_database_tab()
        self.tabs.addTab(self.tab_database, "🗄️ Database Management")

        # Timer Fetch Realtime Data (Tiap 2 Detik)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_live_metrics)
        self.timer.start(2000)

    def setup_monitor_tab(self):
        layout = QVBoxLayout(self.tab_monitor)
        layout.setContentsMargins(30, 30, 30, 30)
        
        lbl_title = QLabel("Server Real-time Status")
        lbl_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        layout.addWidget(lbl_title)
        
        # Grid Statistik
        grid = QGridLayout()
        grid.setSpacing(20)
        
        # Cards
        self.lbl_ip = self.create_stat_card("Alamat IP Jaringan", self.local_ip, grid, 0, 0)
        self.lbl_uptime = self.create_stat_card("Server Uptime", "00:00:00", grid, 0, 1)
        self.lbl_users = self.create_stat_card("User Online Saat Ini", "0 Orang", grid, 1, 0)
        self.lbl_rooms = self.create_stat_card("Watch Party Aktif", "0 Room", grid, 1, 1)
        self.lbl_cpu = self.create_stat_card("Penggunaan CPU", "0%", grid, 2, 0)
        self.lbl_ram = self.create_stat_card("Penggunaan RAM", "0%", grid, 2, 1)
        
        layout.addLayout(grid)
        layout.addStretch()

        btn_quit = QPushButton("❌ Matikan Keseluruhan Server")
        btn_quit.setObjectName("btn-danger")
        btn_quit.clicked.connect(self.shutdown)
        layout.addWidget(btn_quit)

    def create_stat_card(self, title, default_val, grid, row, col):
        card = QWidget()
        card.setProperty("class", "StatCard")
        cl = QVBoxLayout(card)
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("color: #888899; font-weight: bold; font-size: 11px;")
        lbl_v = QLabel(default_val)
        lbl_v.setStyleSheet("color: white; font-size: 20px; font-weight: bold;")
        cl.addWidget(lbl_t)
        cl.addWidget(lbl_v)
        grid.addWidget(card, row, col)
        return lbl_v

    def setup_database_tab(self):
        layout = QVBoxLayout(self.tab_database)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Navbar Database
        nav = QHBoxLayout()
        lbl_title = QLabel("Katalog Data Film")
        lbl_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        nav.addWidget(lbl_title)
        
        btn_add = QPushButton("➕ Tambah Film")
        btn_add.setObjectName("btn-accent")
        btn_add.clicked.connect(self.action_add_film) # Anggap dialog AddFilmAutoDialog sdh ada
        nav.addWidget(btn_add)
        
        btn_conv = QPushButton("🎬 Konversi Video (FFmpeg)")
        btn_conv.clicked.connect(lambda: ConvertVideoDialog(self).exec())
        nav.addWidget(btn_conv)
        layout.addLayout(nav)
        
        # Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Judul Film", "Genre", "Tahun", "Aksi"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        self.refresh_table()

    def get_local_ip(self):
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except: return "127.0.0.1"

    def update_live_metrics(self):
        # Update Hardware
        try:
            self.lbl_cpu.setText(f"{psutil.cpu_percent()}%")
            self.lbl_ram.setText(f"{psutil.virtual_memory().percent}%")
        except: pass
        
        # Update API Flask (Uptime, Users, Rooms)
        try:
            res = requests.get(f"http://127.0.0.1:{FLASK_PORT}/api/status", timeout=1)
            if res.status_code == 200:
                data = res.json()
                sec = data['uptime']
                self.lbl_uptime.setText(f"{sec//3600:02}:{(sec%3600)//60:02}:{sec%60:02}")
                self.lbl_users.setText(f"{data['users']} Orang")
                self.lbl_rooms.setText(f"{data['rooms']} Room")
        except: pass

    def refresh_table(self):
        self.table.setRowCount(0)
        for i, f in enumerate(get_all_films()):
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(str(f['id'])))
            self.table.setItem(i, 1, QTableWidgetItem(f['title']))
            self.table.setItem(i, 2, QTableWidgetItem(f['genre'] or "-"))
            self.table.setItem(i, 3, QTableWidgetItem(str(f['year'] or "-")))
            
            btn_del = QPushButton("Hapus")
            btn_del.setObjectName("btn-danger")
            btn_del.clicked.connect(lambda checked, fid=f['id']: self.delete_film_action(fid))
            self.table.setCellWidget(i, 4, btn_del)

    def action_add_film(self):
        # Panggil class AddFilmAutoDialog Anda dari kode sebelumnya di sini
        pass

    def delete_film_action(self, fid):
        if QMessageBox.question(self, "Hapus", "Yakin hapus film?") == QMessageBox.StandardButton.Yes:
            delete_film(fid)
            self.refresh_table()

    def shutdown(self):
        if QMessageBox.question(self, "Shutdown", "Matikan semua layanan?") == QMessageBox.StandardButton.Yes:
            QApplication.quit()
            os._exit(0)

def main():
    init_db()
    app = QApplication(sys.argv)
    threading.Thread(target=run_flask, daemon=True).start()
    dashboard = CineStreamDashboard()
    dashboard.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()