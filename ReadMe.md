# Movia 🎬

Selamat datang di Movia — platform streaming lokal dan Watch Party modern untuk jaringan LAN/WLAN.

Movia memadukan:

- Nginx untuk penyajian konten statis dan HLS
- Flask sebagai API backend
- Socket.IO untuk sinkronisasi tontonan real-time
- PyQt6 untuk kontrol tray dan antarmuka lokal
- FFmpeg untuk konversi video ke HLS

## ✨ Fitur Utama

- **🖥️ Professional GUI Dashboard:** Antarmuka pemantauan server bergaya Grafana yang dibangun dengan **PyQt6**. Memantau penggunaan CPU, RAM, Disk, Jaringan, dan aktivitas Watch Party secara _real-time_.
- **⚙️ Mesin Konversi Cerdas (FFmpeg):** Mengonversi video mentah menjadi segmen `.ts` dan `.m3u8` secara otomatis melalui pemrosesan 2-Tahap (Aman untuk format Subtitle Bluray/PGS).
- **📡 Auto-Fetch Metadata:** Cukup ketik judul film, dan sistem akan menarik Deskripsi, Genre, Tahun, Durasi, Skor Rating, dan Poster secara otomatis dari **MyAnimeList** atau **IMDb**.
- **🍿 Nonton Bareng (Watch Party):** Sinkronisasi pemutaran video (Play, Pause, Seek) secara _real-time_ dengan teknologi **WebSocket** (Flask-SocketIO). Dilengkapi dengan fitur Live Chat.
- **🌐 Web Player Responsif:** Menggunakan `Hls.js` dengan integrasi rotasi layar otomatis (_Auto-Landscape_) untuk pengguna perangkat seluler dan dukungan subtitle WebVTT yang dapat dikustomisasi.

## 🧩 Arsitektur Proyek

- **Frontend UI**: HTML5, CSS3, Vanilla JavaScript, Hls.js
- **Backend API**: Python 3, Flask, SQLite
- **Sinkronisasi**: Flask-SocketIO
- **Server Media**: Nginx
- **Pemroses Video**: FFmpeg
- **Pengontrol Desktop**: PyQt6

## 📂 Struktur Direktori Proyek

Movia memisahkan logika ke dalam 3 lapisan utama: **Dashboard Manager**, **Backend Server**, dan **Frontend Client**. Berikut adalah peta direktori proyek ini:

````text
Movia/
│
├── launcher.py            # 🖥️ CORE: Dashboard GUI (PyQt6) & Mesin FFmpeg 2-Tahap
├── requirements.txt       # Daftar pustaka Python (Flask, PyQt6, dll)
├── ReadMe.md              # Dokumentasi utama proyek
├── SETUP.md               # Panduan teknis instalasi dan server
│
├── media/                 # 📁 PENYIMPANAN MEDIA (Auto-generated)
│   └── hls/               # Folder khusus Nginx untuk menyajikan streaming
│       └── judul_film/    # Berisi file playlist (.m3u8), segmen (.ts), dan subtitle (.vtt)
│
├── nginx/                 # 🌐 KONFIGURASI WEB SERVER
│   └── nginx.conf         # Aturan routing Nginx untuk CORS dan file statis
│
├── server/                # ⚙️ BACKEND (Logika Server & API)
│   ├── app.py             # Server Flask & Socket.IO (Manajemen endpoint API & Watch Party)
│   ├── database.py        # Pengelola SQLite (Skema tabel Film & Room)
│   ├── database.db        # File database lokal
│   └── fetcher.py         # Skrip penarik metadata otomatis dari MyAnimeList & IMDb
│
└── frontend/              # 🎨 FRONTEND (Antarmuka Web Pemirsa)
    ├── index.html         # Halaman Beranda (Katalog Premium)
    ├── movie.html         # Halaman Info Film (Poster, Sinopsis, Rating, Genre)
    ├── watch.html         # Halaman Nonton (Pemutar HLS, Chat UI, Sync Room)
    │
    ├── css/               # Gaya Tampilan (Styling)
    │   ├── style.css      # Tema global (Dark/Light mode)
    │   ├── movie.css      # Layout detail film
    │   └── watch.css      # Layout pemutar video & jendela chat
    │
    └── js/                # Logika Klien (Interaktivitas Web)
        ├── main.js        # Logika muat katalog di beranda
        ├── movie.js       # Logika muat metadata & parsing rating bintang
        └── watch.js       # Mesin inti pemutar HLS.js, kontrol Subtitle (CC), & WebSocket Sync

## 🚀 Mengapa Movia?

- Tanpa cloud: semua konten tetap tersimpan di jaringan lokal
- Streaming cepat dengan HLS
- Sinkronisasi tontonan untuk acara bersama
- Layanan ringan untuk laptop atau PC rumahan

## 🛠️ Rencana Pengembangan

Movia terus berkembang. Berikut fitur yang sedang direncanakan:

- [*] Otomatisasi konversi media lewat GUI
- [ ] Sistem autentikasi dan manajemen pengguna
- [*] Halaman detail film dan pencarian cerdas
- [ ] Dukungan subtitle multi-bahasa
- [*] Penguatan stabilitas chat Watch Party
- [*] Dashboard monitoring sumber daya server
- [ ] Adaptive Bitrate Streaming (ABR)

## 💡 Catatan Singkat

- Simpan file HLS di `media/hls/`
- Pastikan `nginx.conf` mengarah ke `frontend/` dan `media/hls/`
- Jalankan `python launcher.py` untuk memulai aplikasi
- Gunakan browser untuk membuka antarmuka pengguna

---

Nikmati pengalaman bioskop lokal dengan Movia! 🎥```
````
