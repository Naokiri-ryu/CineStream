# CineStream — Panduan Setup & Instalasi

Selamat datang di CineStream! 🎬
Dokumen ini akan membantu Anda menyiapkan server, mengonversi video ke HLS, dan menjalankan watch party di jaringan lokal dengan cepat.

---

## 🚀 1. Siapkan Lingkungan

1. Pastikan Python sudah terpasang. Rekomendasi: **Python 3.11** atau **3.12**.
2. Buka terminal di folder proyek `CineStream`.
3. Jalankan perintah berikut untuk instalasi dependensi:

```bash
pip install -r requirements.txt
```

> Jika menggunakan virtualenv, aktifkan terlebih dahulu sebelum instalasi.

---

## ⚙️ 2. Konfigurasi Nginx

CineStream menggunakan Nginx untuk:

- menyajikan konten frontend
- melayani file HLS
- meneruskan koneksi Socket.IO untuk Watch Party

### Langkah singkat:

1. Instal Nginx (disarankan versi stabil atau Nginx-RTMP).
2. Salin `nginx/nginx.conf` dari repositori ke folder konfigurasi Nginx.
3. Buka file `nginx.conf` dan sesuaikan path berikut:
   - `root` untuk folder `frontend`
   - `alias` untuk folder `media/hls`
4. Jalankan Nginx atau reload konfigurasi:

```bash
start nginx
```

Jika Nginx sudah berjalan:

```bash
nginx -s reload
```

---

## 🎞️ 3. Konversi Video ke HLS (FFmpeg)

Agar video dapat diputar di browser, Anda perlu mengonversinya ke format HLS.

### Persyaratan:

- FFmpeg sudah terpasang
- FFmpeg tersedia di PATH Windows

### Contoh struktur folder:

```text
media/hls/nama_folder_film/index.m3u8
media/hls/nama_folder_film/index0.ts
media/hls/nama_folder_film/index1.ts
```

### Perintah FFmpeg:

```bash
mkdir media\hls\nama_folder_film
ffmpeg -i "path\ke\video_asli.mkv" -map 0:v -map 0:a -c:v copy -c:a aac -start_number 0 -hls_time 10 -hls_list_size 0 -f hls "media\hls\nama_folder_film\index.m3u8"
```

> Gunakan nama folder unik untuk setiap film agar katalog tidak bercampur.

---

## 🎬 4. Jalankan CineStream

Di terminal proyek `CineStream`, jalankan:

```bash
python launcher.py
```

Aplikasi akan:

- mengecek database SQLite
- menjalankan server Flask
- menampilkan ikon CineStream di system tray

### Menambahkan film baru:

1. Klik ikon tray CineStream.
2. Pilih **Tambah Film Baru**.
3. Isi metadata film:
   - Judul
   - Deskripsi
   - Genre
   - URL poster
   - Path HLS (contoh: `nama_folder_film/index.m3u8`)
4. Simpan ke database.

> Setelah disimpan, katalog di browser akan diperbarui otomatis.

---

## 🌐 5. Buka Watch Party di Jaringan Lokal

Pastikan semua perangkat terhubung ke jaringan WiFi atau LAN yang sama.

1. Klik ikon tray CineStream.
2. Salin URL jaringan lokal (contoh: `http://192.168.1.50:8080`).
3. Bagikan URL tersebut kepada teman-teman.

Mereka dapat membuka katalog film dan bergabung ke watch party dalam satu jaringan.

---

## ✅ Tips Cepat

- Gunakan nama folder HLS yang mudah dibaca.
- Jangan lupa reload Nginx setiap kali mengubah `nginx.conf`.
- Simpan file HLS di dalam `media/hls/` agar konfigurasi default berfungsi.
- Jika video tidak muncul, cek kembali path di `index.m3u8` dan `nginx.conf`.
