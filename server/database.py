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
            rating      REAL DEFAULT 0.0,
            poster_url  TEXT,
            hls_path    TEXT NOT NULL,
            format      TEXT DEFAULT 'HD · HLS Stream',
            language    TEXT DEFAULT 'Inggris',
            has_subtitle INTEGER DEFAULT 1,
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

    count = conn.execute('SELECT COUNT(*) FROM films').fetchone()[0]
    if count == 0:
        conn.executescript('''
            INSERT INTO films (title, description, genre, year, duration, rating, poster_url, hls_path, format, language, has_subtitle) VALUES
            (
                'Big Buck Bunny',
                'Film animasi pendek tentang seekor kelinci raksasa yang harus menghadapi tiga penggangu kecil yang jahat.',
                'Animasi',
                2008,
                10,
                6.5,
                'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Big_buck_bunny_poster_big.jpg/800px-Big_buck_bunny_poster_big.jpg',
                'big_buck_bunny/index.m3u8',
                'HD · HLS Stream',
                'Inggris',
                1
            );
        ''')
    conn.commit()

    # Migrasi otomatis: tambah kolom baru ke database yang sudah ada tanpa menghapus data lama
    for col, definition in [
        ('format',       "TEXT DEFAULT 'HD · HLS Stream'"),
        ('language',     "TEXT DEFAULT 'Inggris'"),
        ('has_subtitle', 'INTEGER DEFAULT 1'),
        ('rating',       'REAL DEFAULT 0.0'), # Tambahan migrasi kolom rating
    ]:
        try:
            conn.execute(f'ALTER TABLE films ADD COLUMN {col} {definition}')
            conn.commit()
        except Exception:
            pass 

    conn.close()
    return get_films()

def get_film(film_id):
    conn = get_db()
    row = conn.execute('SELECT * FROM films WHERE id = ?', (film_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_films():
    conn = get_db()
    rows = conn.execute('SELECT * FROM films ORDER BY title').fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_film(title, description, genre, year, duration, rating, poster_url, hls_path,
             format='HD · HLS Stream', language='Inggris', has_subtitle=1):
    conn = get_db()
    conn.execute(
        '''INSERT INTO films
           (title, description, genre, year, duration, rating, poster_url, hls_path, format, language, has_subtitle)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
        (title, description, genre, year, duration, rating, poster_url, hls_path, format, language, has_subtitle)
    )
    conn.commit()
    conn.close()

def _generate_code(length=6):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))

def create_room(film_id, host_name):
    conn = get_db()
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

def get_all_films():
    conn = get_db()
    rows = conn.execute('SELECT * FROM films ORDER BY id DESC').fetchall()
    conn.close()
    return rows

def delete_film(film_id):
    conn = get_db()
    film = conn.execute('SELECT hls_path FROM films WHERE id = ?', (film_id,)).fetchone()
    if film:
        conn.execute('DELETE FROM films WHERE id = ?', (film_id,))
        conn.commit()
        conn.close()
        return True, film['hls_path']
    conn.close()
    return False, ""

def delete_room(room_code):
    conn = get_db()
    conn.execute('DELETE FROM rooms WHERE room_code = ?', (room_code,))
    conn.commit()
    conn.close()