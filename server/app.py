import os
import time
from flask import Flask, jsonify, request, send_from_directory
from flask_socketio import SocketIO, join_room, leave_room, emit

from database import init_db, get_films, get_film, create_room, get_room, deactivate_room

# Inisialisasi SocketIO dengan izin lintas perangkat (CORS) agar bisa diakses HP
socketio = SocketIO(cors_allowed_origins='*', async_mode='threading')

# Simpan state room di memory (siapa host, posisi video, playing/pause)
room_states = {}
room_users = {}

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

        # Buat state awal room
        room_states[code] = {
            'is_playing': False,
            'current_time': 0.0,
            'host_sid': None,
            'updated_at': time.time(),
        }

        return jsonify({'room_code': code})

    @app.route('/api/rooms/<room_code>')
    def api_get_room(room_code):
        room = get_room(room_code)
        return jsonify(room) if room else (jsonify({'error': 'Room tidak ditemukan'}), 404)
    
    @app.route('/api/rooms/active')
    def api_active_rooms():
        active = []
        for code, state in room_states.items():
            room_db = get_room(code)
            if room_db:
                film = get_film(room_db['film_id'])
                users = room_users.get(code, [])
                active.append({
                    'code': code,
                    'host': room_db['host_name'],
                    'film_title': film['title'] if film else 'Tidak diketahui',
                    'users_count': len(users)
                })
        return jsonify(active)

    # Serve file HLS (.m3u8 + .ts)
    @app.route('/media/hls/<path:filename>')
    def serve_hls(filename):
        return send_from_directory(media_dir, filename)

#── SocketIO Events ───────────────────────────────────────────────────────

    room_users = {} # Format: { 'CODE': [ {'sid': '...', 'username': '...', 'is_host': True} ] }

    @socketio.on('join_room')
    def on_join(data):
        code     = data.get('room_code', '').upper()
        username = data.get('username', 'Penonton')
        is_host  = data.get('is_host', False)

        join_room(code)

        # Simpan identitas user di server
        if code not in room_users:
            room_users[code] = []
        
        # Cegah duplikasi SID
        user_data = {'sid': request.sid, 'username': username, 'is_host': is_host}
        if user_data not in room_users[code]:
            room_users[code].append(user_data)

        if is_host and code in room_states:
            room_states[code]['host_sid'] = request.sid

        emit('system_message', {'message': f'{username} bergabung ke room', 'timestamp': time.time()}, to=code)
        
        # Siarkan daftar penonton terbaru ke semua orang di room
        emit('user_list_update', room_users[code], to=code)

        # Jika yang masuk adalah penonton, paksa videonya sinkron dengan Host saat ini
        if not is_host and code in room_states:
            state = room_states[code]
            emit('sync_state', {
                'is_playing': state['is_playing'],
                'current_time': state['current_time'],
            })

    @socketio.on('disconnect')
    def on_disconnect():
        # Cari dan hapus user yang tiba-tiba keluar / tutup browser
        for code, users in room_users.items():
            for u in users:
                if u['sid'] == request.sid:
                    users.remove(u)
                    leave_room(code)
                    emit('user_list_update', users, to=code)
                    emit('system_message', {'message': f"{u['username']} telah terputus.", 'timestamp': time.time()}, to=code)
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
        code = data.get('room_code', '').upper()
        current = data.get('current_time', 0.0)
        if code in room_states:
            room_states[code]['is_playing'] = True
            room_states[code]['current_time'] = current
        emit('video_play', {'current_time': current}, to=code, include_self=False)

    @socketio.on('video_pause')
    def on_pause(data):
        code = data.get('room_code', '').upper()
        current = data.get('current_time', 0.0)
        if code in room_states:
            room_states[code]['is_playing'] = False
            room_states[code]['current_time'] = current
        emit('video_pause', {'current_time': current}, to=code, include_self=False)

    @socketio.on('video_seek')
    def on_seek(data):
        code = data.get('room_code', '').upper()
        current = data.get('current_time', 0.0)
        if code in room_states:
            room_states[code]['current_time'] = current
        emit('video_seek', {'current_time': current}, to=code, include_self=False)
        
    return app