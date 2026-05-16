# CineStream 🎬

Selamat datang di CineStream — platform streaming lokal dan Watch Party modern untuk jaringan LAN/WLAN.

CineStream memadukan:

- Nginx untuk penyajian konten statis dan HLS
- Flask sebagai API backend
- Socket.IO untuk sinkronisasi tontonan real-time
- PyQt6 untuk kontrol tray dan antarmuka lokal
- FFmpeg untuk konversi video ke HLS

## ✨ Fitur Utama

- Streaming lokal melalui protokol HLS
- Watch Party dengan sinkronisasi pemutaran real-time
- Interface browser untuk katalog film dan pemutar video
- Kontrol sistem tray untuk manajemen cepat
- Dukungan media lokal tanpa bergantung pada layanan cloud

## 🧩 Arsitektur Proyek

- **Frontend UI**: HTML5, CSS3, Vanilla JavaScript, Hls.js
- **Backend API**: Python 3, Flask, SQLite
- **Sinkronisasi**: Flask-SocketIO
- **Server Media**: Nginx
- **Pemroses Video**: FFmpeg
- **Pengontrol Desktop**: PyQt6

## 📁 Struktur Proyek

```text
CineStream/
├── launcher.py           # Entry point aplikasi tray + server
├── requirements.txt      # Daftar dependensi Python
├── server/
│   ├── app.py            # Backend API dan Socket.IO
│   ├── database.py       # Skema SQLite dan fungsi CRUD
│   └── database.db       # Database konten film
├── frontend/
│   ├── index.html        # Halaman katalog film
│   └── watch.html        # Halaman pemutar Watch Party
├── media/
│   └── hls/              # Folder HLS (.m3u8 + .ts)
└── nginx/
    └── nginx.conf        # Konfigurasi Nginx
```

## 🚀 Mengapa CineStream?

- Tanpa cloud: semua konten tetap tersimpan di jaringan lokal
- Streaming cepat dengan HLS
- Sinkronisasi tontonan untuk acara bersama
- Layanan ringan untuk laptop atau PC rumahan

## 🛠️ Rencana Pengembangan

CineStream terus berkembang. Berikut fitur yang sedang direncanakan:

- [ ] Otomatisasi konversi media lewat GUI
- [ ] Sistem autentikasi dan manajemen pengguna
- [ ] Halaman detail film dan pencarian cerdas
- [ ] Dukungan subtitle multi-bahasa
- [ ] Penguatan stabilitas chat Watch Party
- [ ] Dashboard monitoring sumber daya server
- [ ] Adaptive Bitrate Streaming (ABR)
- [ ] Mode auto-start / daemon untuk Windows dan Linux

## 💡 Catatan Singkat

- Simpan file HLS di `media/hls/`
- Pastikan `nginx.conf` mengarah ke `frontend/` dan `media/hls/`
- Jalankan `python launcher.py` untuk memulai aplikasi
- Gunakan browser untuk membuka antarmuka pengguna

---

Nikmati pengalaman bioskop lokal dengan CineStream! 🎥```
