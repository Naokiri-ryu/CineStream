# CineStream — Panduan Setup

## 1. Install dependensi Python

```
pip install -r requirements.txt (lakukan di terminal yang terbuka pada folder cinestream)
```

## 2. Siapkan video (lakukan sekali saja)

Install FFmpeg dari https://ffmpeg.org/download.html, lalu:

```
mkdir media\hls\big_buck_bunny
ffmpeg -i "film.mp4" -codec: copy -start_number 0 -hls_time 10 -hls_list_size 0 -f hls "media/hls/big_buck_bunny/index.m3u8"
```

Ulangi untuk setiap film. Nama folder harus sesuai dengan kolom `hls_path` di database.

## 3. Jalankan aplikasi

```
python launcher.py
```

Ikon akan muncul di system tray (pojok kanan bawah Windows).
Browser otomatis terbuka ke http://localhost:5000

## 4. Akses dari perangkat lain

Klik kanan ikon tray → **Salin URL Jaringan**
Buka URL tersebut di HP atau laptop lain yang tersambung WiFi yang sama.

---

## Menambah Film Baru

Edit `server/database.py` bagian INSERT, atau tambahkan langsung lewat SQLite:

```sql
INSERT INTO films (title, description, genre, year, duration, poster_url, hls_path)
VALUES ('Judul Film', 'Deskripsi', 'Genre', 2024, 120, 'https://...poster.jpg', 'nama_folder/index.m3u8');
```

## Struktur Folder

```
cinestream/
├── launcher.py          ← Jalankan ini
├── requirements.txt
├── server/
│   ├── app.py           ← Flask + SocketIO
│   └── database.py      ← SQLite helper
├── frontend/
│   ├── index.html       ← Katalog film
│   └── watch.html       ← Player + Watch Party
├── media/
│   └── hls/
│       └── nama_film/
│           ├── index.m3u8
│           └── segment*.ts
└── nginx/
    └── nginx.conf       ← Opsional, untuk performa lebih baik
```
