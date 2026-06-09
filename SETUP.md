# 🎬 Movia — Panduan Setup & Instalasi

Selamat datang di Movia! Platform _Self-Hosted Video Streaming_ dan _Watch Party_ lokal.
Dokumen ini akan membantu Anda menyiapkan server, mengonversi video secara otomatis, dan menjalankan _Watch Party_ di jaringan lokal (WiFi/LAN) Anda.

---

## 🚀 1. Persiapan Lingkungan Sistem

Sebelum memulai, pastikan 3 program utama ini sudah terpasang di PC/Laptop Server Anda:

1. **Python (Rekomendasi 3.10 - 3.12):** [Download di sini](https://www.python.org/downloads/). (Wajib centang _Add Python to PATH_ saat instalasi).
2. **FFmpeg:** Mesin inti untuk konversi video HLS. [Download di sini](https://ffmpeg.org/download.html) dan pastikan folder `bin` FFmpeg telah dimasukkan ke dalam _Environment Variables PATH_ Windows Anda.
3. **Nginx:** Web server untuk mengalirkan pecahan video dengan cepat. [Download Nginx Windows](http://nginx.org/en/download.html).

### Instalasi Dependensi Python

Buka terminal/Command Prompt di dalam folder proyek ini, lalu jalankan:

````bash
pip install -r requirements.txt

### ⚙️ 2. Konfigurasi Nginx

Movia menggunakan Nginx untuk:

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
````

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

## 🎬 4. Jalankan Movia

Di terminal proyek `Movia`, jalankan:

```bash
python launcher.py
```

Aplikasi akan:

- mengecek database SQLite
- menjalankan server Flask
- menampilkan ikon Movia di system tray

### Menambahkan film baru:

1. Klik ikon tray Movia.
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

1. Klik ikon tray Movia.
2. Salin URL jaringan lokal (contoh: `http://192.168.1.50:8080`).
3. Bagikan URL tersebut kepada teman-teman.

Mereka dapat membuka katalog film dan bergabung ke watch party dalam satu jaringan.

---

## ✅ Tips Cepat

- Gunakan nama folder HLS yang mudah dibaca.
- Jangan lupa reload Nginx setiap kali mengubah `nginx.conf`.
- Simpan file HLS di dalam `media/hls/` agar konfigurasi default berfungsi.
- Jika video tidak muncul, cek kembali path di `index.m3u8` dan `nginx.conf`.
