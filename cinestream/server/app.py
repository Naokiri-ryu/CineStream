import os
import time
from flask import Flask, jsonify, request, send_from_directory
from flask_socketio import SocketIO, join_room, leave_room, emit

from database import init_db, get_films, get_film, create_room, get_room, deactivate_room

# SocketIO instance (diinisialisasi di create_app)
socketio = SocketIO(cors_allowed_origins='*', async_mode='threading')

# Simpan state room di memory (siapa host, posisi video, playing/pause)
room_states = {}


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

    # Serve file HLS (.m3u8 + .ts)
    @app.route('/media/hls/<path:filename>')
    def serve_hls(filename):
        return send_from_directory(media_dir, filename)

    # ── SocketIO Events ───────────────────────────────────────────────────────

    @socketio.on('join_room')
    def on_join(data):
        code     = data.get('room_code', '').upper()
        username = data.get('username', 'Penonton')
        is_host  = data.get('is_host', False)

        join_room(code)

        # Simpan SID host agar hanya host yang bisa kontrol
        if is_host and code in room_states:
            room_states[code]['host_sid'] = request.sid

        emit('system_message', {
            'message': f'{username} bergabung ke room',
            'timestamp': time.time(),
        }, to=code)

        # Kirim state video saat ini ke user baru (bukan host)
        if not is_host and code in room_states:
            state = room_states[code]
            emit('sync_state', {
                'is_playing': state['is_playing'],
                'current_time': state['current_time'],
            })

    @socketio.on('leave_room')
    def on_leave(data):
        code     = data.get('room_code', '').upper()
        username = data.get('username', 'Penonton')

        leave_room(code)

        emit('system_message', {
            'message': f'{username} meninggalkan room',
            'timestamp': time.time(),
        }, to=code)

    @socketio.on('chat_message')
    def on_chat(data):
        code = data.get('room_code', '').upper()
        emit('chat_message', {
            'username':  data.get('username', 'Anonim'),
            'message':   data.get('message', ''),
            'timestamp': time.time(),
        }, to=code)

    @socketio.on('video_play')
    def on_play(data):
        code = data.get('room_code', '').upper()
        current = data.get('current_time', 0.0)

        if code in room_states:
            room_states[code]['is_playing']  = True
            room_states[code]['current_time'] = current
            room_states[code]['updated_at']   = time.time()

        # Broadcast ke semua kecuali pengirim (host)
        emit('video_play', {
            'current_time': current,
            'server_time':  time.time(),
        }, to=code, include_self=False)

    @socketio.on('video_pause')
    def on_pause(data):
        code    = data.get('room_code', '').upper()
        current = data.get('current_time', 0.0)

        if code in room_states:
            room_states[code]['is_playing']  = False
            room_states[code]['current_time'] = current
            room_states[code]['updated_at']   = time.time()

        emit('video_pause', {
            'current_time': current,
            'server_time':  time.time(),
        }, to=code, include_self=False)

    @socketio.on('video_seek')
    def on_seek(data):
        code    = data.get('room_code', '').upper()
        current = data.get('current_time', 0.0)

        if code in room_states:
            room_states[code]['current_time'] = current
            room_states[code]['updated_at']   = time.time()

        emit('video_seek', {
            'current_time': current,
            'server_time':  time.time(),
        }, to=code, include_self=False)

    return app
