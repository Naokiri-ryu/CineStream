"""
CineStream Launcher
-------------------
Jalankan file ini untuk memulai server.
Server berjalan di background, ikon muncul di system tray.
"""

import sys
import os
import threading
import webbrowser
import socket
import time

# Tambahkan folder server ke Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))

from PIL import Image, ImageDraw, ImageFont
import pystray

from app import create_app, socketio

PORT = 5000
_icon = None


# ── Utilitas ──────────────────────────────────────────────────────────────────

def get_local_ip():
    """Dapatkan IP lokal di jaringan WiFi/LAN."""
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
    """Salin teks ke clipboard (Windows & Linux)."""
    try:
        if sys.platform == 'win32':
            import subprocess
            subprocess.run('clip', input=text.encode('utf-8'), check=True, shell=True)
        else:
            import subprocess
            subprocess.run(['xclip', '-selection', 'clipboard'],
                           input=text.encode('utf-8'), check=True)
    except Exception:
        pass


# ── Ikon Tray ─────────────────────────────────────────────────────────────────

def make_icon_image(size=64):
    """Buat gambar ikon secara programatik dengan Pillow."""
    img  = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Lingkaran latar (ungu)
    draw.ellipse([2, 2, size - 2, size - 2], fill='#534AB7')

    # Segitiga play (putih)
    m = size // 2
    play = [
        (m - 10, m - 14),
        (m - 10, m + 14),
        (m + 14, m),
    ]
    draw.polygon(play, fill='white')

    # Titik hijau (status aktif) — pojok kanan bawah
    r = size // 9
    cx, cy = size - r - 3, size - r - 3
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill='#1D9E75')

    return img


# ── Thread Server ─────────────────────────────────────────────────────────────

def run_server():
    app = create_app()
    socketio.run(
        app,
        host='0.0.0.0',
        port=PORT,
        use_reloader=False,
        log_output=False,
        allow_unsafe_werkzeug=True,
    )


# ── Aksi Menu Tray ────────────────────────────────────────────────────────────

def action_open_browser(icon, item):
    webbrowser.open(f'http://localhost:{PORT}')


def action_copy_local(icon, item):
    copy_to_clipboard(f'http://localhost:{PORT}')


def action_copy_lan(icon, item):
    ip = get_local_ip()
    copy_to_clipboard(f'http://{ip}:{PORT}')


def action_quit(icon, item):
    icon.stop()
    os._exit(0)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    global _icon

    # 1. Jalankan server Flask+SocketIO di thread background
    server_thread = threading.Thread(target=run_server, daemon=True, name='CineStream-Server')
    server_thread.start()

    # 2. Tunggu server siap
    time.sleep(2)

    # 3. Buka browser otomatis
    webbrowser.open(f'http://localhost:{PORT}')

    # 4. Dapatkan IP lokal untuk label menu
    local_ip = get_local_ip()

    # 5. Buat menu tray
    menu = pystray.Menu(
        pystray.MenuItem('🎬  CineStream', None, enabled=False),
        pystray.Menu.SEPARATOR,

        pystray.MenuItem('Buka di Browser', action_open_browser),
        pystray.MenuItem(f'Salin URL Lokal  (localhost:{PORT})', action_copy_local),
        pystray.MenuItem(f'Salin URL Jaringan  ({local_ip}:{PORT})', action_copy_lan),

        pystray.Menu.SEPARATOR,
        pystray.MenuItem('Keluar', action_quit),
    )

    # 6. Tampilkan ikon di system tray
    _icon = pystray.Icon(
        name='CineStream',
        icon=make_icon_image(),
        title=f'CineStream  •  localhost:{PORT}',
        menu=menu,
    )

    _icon.run()


if __name__ == '__main__':
    main()
