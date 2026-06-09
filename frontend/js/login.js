import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
import { getAuth, GoogleAuthProvider, signInWithPopup } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-auth.js";

// ── 1. KONFIGURASI FIREBASE ──
const firebaseConfig = {
  apiKey: "AIzaSyDZ8jBvFk5GmpL4L-KgJjg-QD6ngPrf7A4",
  authDomain: "cinestream-d7a3a.firebaseapp.com",
  projectId: "cinestream-d7a3a",
  storageBucket: "cinestream-d7a3a.firebasestorage.app",
  messagingSenderId: "40567378181",
  appId: "1:40567378181:web:2383250301d3e54ca6676c"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const provider = new GoogleAuthProvider();

// ── 2. LOGIKA UI (TABS & PASSWORD VISIBILITY) ──
window.switchTab = function(tab) {
  document.querySelectorAll('.auth-tab').forEach((t, i) => { 
    t.classList.toggle('active', (i === 0 && tab === 'login') || (i === 1 && tab === 'register')); 
  });
  document.querySelectorAll('.auth-panel').forEach(p => { 
    p.classList.toggle('active', p.id === 'panel-' + tab); 
  });
};

window.togglePass = function(inputId, btn) {
  const input = document.getElementById(inputId);
  input.type = input.type === 'password' ? 'text' : 'password';
  btn.textContent = input.type === 'password' ? '👁' : '🙈';
};

function showMsg(id, text, type) {
  const el = document.getElementById(id);
  el.className = 'msg ' + type; el.style.display = 'flex';
  el.textContent = (type === 'error' ? '⚠ ' : '✓ ') + text;
}

function hideMsg(id) { 
  document.getElementById(id).style.display = 'none'; 
}

// ── 3. LOGIKA AUTENTIKASI (EMAIL & GOOGLE) ──
window.doLogin = async function() {
  const email = document.getElementById('login-email').value.trim();
  const pass  = document.getElementById('login-pass').value;
  hideMsg('msg-login');
  
  if (!email || !pass) return showMsg('msg-login', 'Email dan password wajib diisi.', 'error');
  
  const btn = document.getElementById('btn-login'); 
  btn.classList.add('loading');
  
  try {
    const res = await fetch('/api/auth/login', { 
      method: 'POST', 
      headers: { 'Content-Type': 'application/json' }, 
      body: JSON.stringify({ email, password: pass }) 
    });
    const data = await res.json();
    if (!res.ok) showMsg('msg-login', data.message || 'Email atau password salah.', 'error');
    else {
      localStorage.setItem('token', data.token); 
      localStorage.setItem('user', JSON.stringify(data.user));
      window.location.href = '/';
    }
  } catch (e) { 
    showMsg('msg-login', 'Gagal terhubung ke server.', 'error'); 
  } finally { 
    btn.classList.remove('loading'); 
  }
};

window.doRegister = async function() {
  const username = document.getElementById('reg-username').value.trim();
  const email    = document.getElementById('reg-email').value.trim();
  const pass     = document.getElementById('reg-pass').value;
  hideMsg('msg-register');
  
  if (!username || !email || !pass) return showMsg('msg-register', 'Semua field wajib diisi.', 'error');
  
  const btn = document.getElementById('btn-register'); 
  btn.classList.add('loading');
  
  try {
    const res = await fetch('/api/auth/register', { 
      method: 'POST', 
      headers: { 'Content-Type': 'application/json' }, 
      body: JSON.stringify({ username, email, password: pass }) 
    });
    const data = await res.json();
    if (!res.ok) showMsg('msg-register', data.message || 'Gagal mendaftar.', 'error');
    else {
      localStorage.setItem('token', data.token); 
      localStorage.setItem('user', JSON.stringify(data.user));
      window.location.href = '/';
    }
  } catch (e) { 
    showMsg('msg-register', 'Gagal terhubung ke server.', 'error'); 
  } finally { 
    btn.classList.remove('loading'); 
  }
};

window.loginGoogleFirebase = async function() {
  try {
    const result = await signInWithPopup(auth, provider);
    const res = await fetch('/api/auth/google-sync', {
      method: 'POST', 
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: result.user.email, username: result.user.displayName })
    });
    if(res.ok) {
      const data = await res.json();
      localStorage.setItem('token', data.token); 
      localStorage.setItem('user', JSON.stringify(data.user));
      window.location.href = '/'; 
    }
  } catch (error) { 
    alert("Gagal login dengan Google: " + error.message); 
  }
};

// ── 4. LOGIKA LUPA PASSWORD ──
window.showResetModal = function() {
  document.getElementById('reset-modal').style.display = 'flex';
  hideMsg('msg-reset'); 
  document.getElementById('reset-email').value = '';
};

window.hideResetModal = function() { 
  document.getElementById('reset-modal').style.display = 'none'; 
};

window.doResetPassword = async function() {
  const email = document.getElementById('reset-email').value.trim();
  hideMsg('msg-reset');
  if (!email) return showMsg('msg-reset', 'Masukkan email kamu.', 'error'); 

  const btn = document.getElementById('btn-reset'); 
  btn.textContent = 'Memproses...';
  
  try {
    const res = await fetch('/api/auth/reset-password', {
      method: 'POST', 
      headers: { 'Content-Type': 'application/json' }, 
      body: JSON.stringify({ email })
    });
    const data = await res.json();
    if (!res.ok) showMsg('msg-reset', data.message || 'Gagal memproses.', 'error'); 
    else { showMsg('msg-reset', data.message, 'success'); }
  } catch (e) { 
    showMsg('msg-reset', 'Gagal terhubung ke server.', 'error'); 
  } finally { 
    btn.textContent = 'Dapatkan'; 
  }
};

// ── 5. LOGIKA ANIMASI BACKGROUND POSTER ──
async function loadBackgroundPosters() {
  try {
    const grid = document.getElementById('dynamic-poster-grid');
    if (!grid) return;

    let posters = [];

    // Coba ambil dari database
    try {
      const res = await fetch('/api/films');
      const films = await res.json();
      if (films && films.length > 0) {
        posters = films.map(f => f.poster_url).filter(url => url);
      }
    } catch (err) {
      console.log("Database belum siap, memakai poster cadangan.");
    }

    // JIKA DATABASE KOSONG / GAGAL, GUNAKAN POSTER CADANGAN INI:
    if (posters.length === 0) {
      posters = [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Big_buck_bunny_poster_big.jpg/800px-Big_buck_bunny_poster_big.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/7/70/Elephants_Dream_s1_l.jpg/800px-Elephants_Dream_s1_l.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Sintel_poster.jpg/800px-Sintel_poster.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/1/18/Tears_of_Steel_poster.jpg/800px-Tears_of_Steel_poster.jpg",
        "https://via.placeholder.com/200x300/ff0043/ffffff?text=CineStream",
        "https://via.placeholder.com/200x300/222534/888899?text=Watch+Party"
      ];
    }

    let html = '';
    // Buat 5 kolom
    for (let i = 0; i < 5; i++) {
      html += `<div class="poster-column">`;
      // Acak urutan agar estetik
      const shuffled = [...posters].sort(() => 0.5 - Math.random());
      // Gandakan jumlahnya berkali-kali lipat agar animasinya panjang
      const repeatedPosters = [...shuffled, ...shuffled, ...shuffled, ...shuffled, ...shuffled, ...shuffled];
      
      repeatedPosters.forEach(url => {
        html += `<img src="${url}" class="poster-img" onerror="this.style.display='none'">`;
      });
      html += `</div>`;
    }
    
    grid.innerHTML = html;
  } catch (e) {
    console.error("Gagal menjalankan animasi poster:", e);
  }
}

// Jalankan animasi poster saat halaman dimuat
loadBackgroundPosters();