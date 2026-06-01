import os
import time
from flask import Flask, jsonify, request, send_from_directory
from flask_socketio import SocketIO, join_room, leave_room, emit

from database import init_db, get_films, get_film, create_room, get_room, deactivate_room

socketio = SocketIO(cors_allowed_origins='*', async_mode='threading')

# State room disimpan di memory (di luar create_app agar persisten)
room_states = {}
room_users  = {}  # Format: { 'CODE': [{'sid': '...', 'username': '...', 'is_host': True}] }


def create_app():
    base_dir  = os.path.dirname(os.path.dirname(__file__))
    frontend  = os.path.join(base_dir, 'frontend')
    media_dir = os.path.join(base_dir, 'media', 'hls')

    app = Flask(__name__, static_folder=frontend, static_url_path='')
    app.config['SECRET_KEY'] = 'cinestream-dev-secret-2025'

    with app.app_context():
        init_db()

    socketio.init_app(app)

    # ── Halaman Web ───────────────────────────────────────────────────────────

    @app.route('/')
    def index():
        return send_from_directory(frontend, 'index.html')

    @app.route('/watch')
    def watch():
        return send_from_directory(frontend, 'watch.html')

    # FIX 1: Route /movie yang hilang — penyebab 404 saat klik tombol Detail
    @app.route('/movie')
    def movie():
        return send_from_directory(frontend, 'movie.html')

    # ── REST API ──────────────────────────────────────────────────────────────

    @app.route('/api/films')
    def api_films():
        return jsonify(get_films())

    @app.route('/api/films/<int:film_id>')
    def api_film(film_id):
        film = get_film(film_id)
        return jsonify(film) if film else (jsonify({'error': 'Tidak ditemukan'}), 404)

    @app.route('/api/rooms', methods=['POST'])
    def api_create_room():
        data      = request.get_json(force=True)
        film_id   = data.get('film_id')
        host_name = data.get('host_name', 'Host')

        if not film_id:
            return jsonify({'error': 'film_id diperlukan'}), 400

        code = create_room(film_id, host_name)
        room_states[code] = {
            'is_playing':   False,
            'current_time': 0.0,
            'host_sid':     None,
            'updated_at':   time.time(),
        }
        return jsonify({'room_code': code})

    # FIX 2: Route statis /active harus didaftarkan SEBELUM route dinamis /<room_code>
    # agar Flask tidak salah mencocokkan "active" sebagai nilai room_code
    @app.route('/api/rooms/active')
    def api_active_rooms():
        active = []
        for code, state in room_states.items():
            room_db = get_room(code)
            if room_db:
                film  = get_film(room_db['film_id'])
                users = room_users.get(code, [])
                active.append({
                    'code':        code,
                    'host':        room_db['host_name'],
                    'film_title':  film['title'] if film else 'Tidak diketahui',
                    'users_count': len(users),
                })
        return jsonify(active)

    @app.route('/api/rooms/<room_code>')
    def api_get_room(room_code):
        room = get_room(room_code)
        return jsonify(room) if room else (jsonify({'error': 'Room tidak ditemukan'}), 404)

    # Serve file HLS (.m3u8 + .ts)
    @app.route('/media/hls/<path:filename>')
    def serve_hls(filename):
        return send_from_directory(media_dir, filename)

    # ── SocketIO Events ───────────────────────────────────────────────────────
    # FIX 3: Hapus duplikasi "room_users = {}" yang ada di sini sebelumnya.
    # room_users sudah didefinisikan di level modul di atas, cukup satu kali.

    @socketio.on('join_room')
    def on_join(data):
        code     = data.get('room_code', '').upper()
        username = data.get('username', 'Penonton')
        is_host  = data.get('is_host', False)

        join_room(code)

        if code not in room_users:
            room_users[code] = []

        # Cegah entri SID yang sama masuk dua kali
        sids = [u['sid'] for u in room_users[code]]
        if request.sid not in sids:
            room_users[code].append({
                'sid':      request.sid,
                'username': username,
                'is_host':  is_host,
            })

        if is_host and code in room_states:
            room_states[code]['host_sid'] = request.sid

        emit('system_message', {
            'message':   f'{username} bergabung ke room',
            'timestamp': time.time(),
        }, to=code)

        emit('user_list_update', room_users[code], to=code)

        # Sinkronkan state video ke viewer baru (bukan host)
        if not is_host and code in room_states:
            state = room_states[code]
            emit('sync_state', {
                'is_playing':   state['is_playing'],
                'current_time': state['current_time'],
            })

    @socketio.on('disconnect')
    def on_disconnect():
        for code, users in room_users.items():
            for u in list(users):
                if u['sid'] == request.sid:
                    users.remove(u)
                    leave_room(code)
                    emit('user_list_update', users, to=code)
                    emit('system_message', {
                        'message':   f"{u['username']} telah terputus.",
                        'timestamp': time.time(),
                    }, to=code)
                    break

    @socketio.on('chat_message')
    def on_chat(data):
        code = data.get('room_code', '').upper()
        emit('chat_message', {
            'username':  data.get('username', 'Anonim'),
            'message':   data.get('message', ''),
            'timestamp': time.time(),
        }, to=code, include_self=False)

    @socketio.on('video_play')
    def on_play(data):
        code    = data.get('room_code', '').upper()
        current = data.get('current_time', 0.0)
        if code in room_states:
            room_states[code]['is_playing']  = True
            room_states[code]['current_time'] = current
            room_states[code]['updated_at']   = time.time()
        emit('video_play', {'current_time': current, 'server_time': time.time()},
             to=code, include_self=False)

    @socketio.on('video_pause')
    def on_pause(data):
        code    = data.get('room_code', '').upper()
        current = data.get('current_time', 0.0)
        if code in room_states:
            room_states[code]['is_playing']  = False
            room_states[code]['current_time'] = current
            room_states[code]['updated_at']   = time.time()
        emit('video_pause', {'current_time': current, 'server_time': time.time()},
             to=code, include_self=False)

    @socketio.on('video_seek')
    def on_seek(data):
        code    = data.get('room_code', '').upper()
        current = data.get('current_time', 0.0)
        if code in room_states:
            room_states[code]['current_time'] = current
            room_states[code]['updated_at']   = time.time()
        emit('video_seek', {'current_time': current, 'server_time': time.time()},
             to=code, include_self=False)

    return app
