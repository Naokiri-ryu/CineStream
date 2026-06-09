import os
import time
from flask import Flask, jsonify, request, send_from_directory
from flask_socketio import SocketIO, join_room, leave_room, emit

from database import init_db, get_films, get_film, create_room, get_room, deactivate_room, delete_room

socketio = SocketIO(cors_allowed_origins='*', async_mode='threading')

SERVER_START_TIME = time.time()
active_users = set()

room_states = {}
room_users  = {} 

def create_app():
    base_dir  = os.path.dirname(os.path.dirname(__file__))
    frontend  = os.path.join(base_dir, 'frontend')
    media_dir = os.path.join(base_dir, 'media', 'hls')

    app = Flask(__name__, static_folder=frontend, static_url_path='')
    app.config['SECRET_KEY'] = 'movia-dev-secret-2025'

    with app.app_context():
        init_db()

    socketio.init_app(app)

    @app.route('/')
    def index(): return send_from_directory(frontend, 'index.html')

    @app.route('/watch')
    def watch(): return send_from_directory(frontend, 'watch.html')

    @app.route('/movie')
    def movie(): return send_from_directory(frontend, 'movie.html')

    @app.route('/api/films')
    def api_films(): return jsonify(get_films())

    @app.route('/api/films/<int:film_id>')
    def api_film(film_id):
        film = get_film(film_id)
        return jsonify(film) if film else (jsonify({'error': 'Tidak ditemukan'}), 404)

    @app.route('/api/rooms', methods=['POST'])
    def api_create_room():
        data = request.get_json(force=True)
        film_id = data.get('film_id')
        host_name = data.get('host_name', 'Host')

        if not film_id: return jsonify({'error': 'film_id diperlukan'}), 400

        code = create_room(film_id, host_name)
        room_states[code] = {
            'is_playing': False, 'current_time': 0.0,
            'host_sid': None, 'updated_at': time.time(),
        }
        return jsonify({'room_code': code})
    
    @app.route('/api/status')
    def api_status():
        return jsonify({
            'uptime': int(time.time() - SERVER_START_TIME),
            'users': len(active_users),
            'rooms': len(room_states)
        })

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
                    'users_count': len(users),
                })
        return jsonify(active)

    @app.route('/api/rooms/<room_code>')
    def api_get_room(room_code):
        room = get_room(room_code)
        return jsonify(room) if room else (jsonify({'error': 'Room tidak ditemukan'}), 404)

    @app.route('/media/hls/<path:filename>')
    def serve_hls(filename):
        return send_from_directory(media_dir, filename)

    # ── SocketIO Events ───────────────────────────────────────────────────────
    
    @socketio.on('connect')
    def handle_connect():
        active_users.add(request.sid)

    @socketio.on('join_room')
    def handle_join_room(data):
        room = data['room_code']
        username = data['username']
        is_host = data.get('is_host', False)
        
        join_room(room)
        if room not in room_users:
            room_users[room] = []
            
        room_users[room] = [u for u in room_users[room] if u['username'] != username]
            
        room_users[room].append({
            'sid': request.sid,
            'username': username,
            'is_host': is_host
        })
        
        emit('user_list', room_users[room], to=room)
        
        # PERBAIKAN: Mengirim format waktu yang benar kepada user yang baru masuk
        if room in room_states:
            state = room_states[room]
            emit('video_seek', {'current_time': state['current_time']}, to=request.sid)
            if state['is_playing']:
                emit('video_play', {'current_time': state['current_time']}, to=request.sid)
        
        emit('user_list', room_users[room], to=room)
        if room in room_states:
            emit('video_seek', {'current_time': room_states[room]}, to=request.sid)
            
    @socketio.on('disconnect')
    def handle_disconnect():
        sid = request.sid
        active_users.discard(sid)
        
        for code, users in list(room_users.items()):
            for user in users:
                if user['sid'] == sid:
                    if user.get('is_host'):
                        emit('room_closed', {'message': 'Host telah keluar. Watch Party dihentikan.'}, to=code)
                        delete_room(code)
                        room_states.pop(code, None)
                        room_users.pop(code, None)
                        return
                    else:
                        room_users[code] = [u for u in users if u['sid'] != sid]
                        emit('user_list', room_users[code], to=code)
                        return

    @socketio.on('end_party')
    def handle_end_party(data):
        room = data.get('room_code')
        emit('room_closed', {'message': 'Host telah mengakhiri Watch Party secara manual.'}, to=room)
        delete_room(room)
        room_states.pop(room, None)
        room_users.pop(room, None)

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
        emit('video_play', {'current_time': current, 'server_time': time.time()}, to=code, include_self=False)

    @socketio.on('video_pause')
    def on_pause(data):
        code = data.get('room_code', '').upper()
        current = data.get('current_time', 0.0)
        if code in room_states:
            room_states[code]['is_playing'] = False
            room_states[code]['current_time'] = current
        emit('video_pause', {'current_time': current, 'server_time': time.time()}, to=code, include_self=False)

    @socketio.on('video_seek')
    def on_seek(data):
        code = data.get('room_code', '').upper()
        current = data.get('current_time', 0.0)
        if code in room_states:
            room_states[code]['current_time'] = current
        emit('video_seek', {'current_time': current, 'server_time': time.time()}, to=code, include_self=False)

    return app