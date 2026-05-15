import sqlite3
import os
import random
import string

DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS films (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            description TEXT,
            genre       TEXT,
            year        INTEGER,
            duration    INTEGER,
            poster_url  TEXT,
            hls_path    TEXT NOT NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS rooms (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            room_code   TEXT UNIQUE NOT NULL,
            film_id     INTEGER,
            host_name   TEXT,
            is_active   INTEGER DEFAULT 1,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (film_id) REFERENCES films(id)
        );
    ''')

    # Isi data contoh jika tabel kosong
    count = conn.execute('SELECT COUNT(*) FROM films').fetchone()[0]
    if count == 0:
        conn.executescript('''
            INSERT INTO films (title, description, genre, year, duration, poster_url, hls_path) VALUES
            (
                'Big Buck Bunny',
                'Film animasi pendek tentang seekor kelinci raksasa yang harus menghadapi tiga penggangu kecil yang jahat.',
                'Animasi',
                2008,
                10,
                'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Big_buck_bunny_poster_big.jpg/800px-Big_buck_bunny_poster_big.jpg',
                'big_buck_bunny/index.m3u8'
            ),
            (
                'Elephants Dream',
                'Film animasi open source pertama dari Blender Foundation. Sebuah perjalanan surreal dua karakter.',
                'Animasi',
                2006,
                11,
                'https://upload.wikimedia.org/wikipedia/commons/thumb/7/70/Elephants_Dream_s1_l.jpg/800px-Elephants_Dream_s1_l.jpg',
                'elephants_dream/index.m3u8'
            );
        ''')

    conn.commit()
    conn.close()


def get_films():
    conn = get_db()
    rows = conn.execute('SELECT * FROM films ORDER BY title').fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_film(film_id):
    conn = get_db()
    row = conn.execute('SELECT * FROM films WHERE id = ?', (film_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_film(title, description, genre, year, duration, poster_url, hls_path):
    conn = get_db()
    conn.execute(
        'INSERT INTO films (title, description, genre, year, duration, poster_url, hls_path) VALUES (?,?,?,?,?,?,?)',
        (title, description, genre, year, duration, poster_url, hls_path)
    )
    conn.commit()
    conn.close()


def _generate_code(length=6):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))


def create_room(film_id, host_name):
    conn = get_db()
    # Pastikan kode unik
    while True:
        code = _generate_code()
        exists = conn.execute('SELECT 1 FROM rooms WHERE room_code = ?', (code,)).fetchone()
        if not exists:
            break
    conn.execute(
        'INSERT INTO rooms (room_code, film_id, host_name) VALUES (?, ?, ?)',
        (code, film_id, host_name)
    )
    conn.commit()
    conn.close()
    return code


def get_room(room_code):
    conn = get_db()
    row = conn.execute('''
        SELECT r.*, f.title AS film_title, f.hls_path, f.poster_url
        FROM rooms r
        JOIN films f ON r.film_id = f.id
        WHERE r.room_code = ? AND r.is_active = 1
    ''', (room_code,)).fetchone()
    conn.close()
    return dict(row) if row else None


def deactivate_room(room_code):
    conn = get_db()
    conn.execute('UPDATE rooms SET is_active = 0 WHERE room_code = ?', (room_code,))
    conn.commit()
    conn.close()
