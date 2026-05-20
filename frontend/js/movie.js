// ── movie.js — Halaman Detail Film ──

let currentFilm = null;
let allFilms = [];
let selectedFilmId = null;

// ── Tema ──
const themeToggle = document.getElementById('theme-toggle');
const currentTheme = localStorage.getItem('theme') || 'dark';
document.documentElement.setAttribute('data-theme', currentTheme);
themeToggle.textContent = currentTheme === 'dark' ? '☀️' : '🌙';

themeToggle.addEventListener('click', () => {
  let theme = document.documentElement.getAttribute('data-theme');
  if (theme === 'dark') {
    document.documentElement.setAttribute('data-theme', 'light');
    localStorage.setItem('theme', 'light');
    themeToggle.textContent = '🌙';
  } else {
    document.documentElement.setAttribute('data-theme', 'dark');
    localStorage.setItem('theme', 'dark');
    themeToggle.textContent = '☀️';
  }
});

// ── Navbar Mobile ──
const mobileToggle = document.getElementById('mobile-toggle');
const navLinks = document.getElementById('nav-links');
if (mobileToggle) {
  mobileToggle.addEventListener('click', () => navLinks.classList.toggle('show'));
}

window.addEventListener('scroll', () => {
  const nav = document.getElementById('navbar');
  if (window.scrollY > 50) nav.classList.add('scrolled');
  else nav.classList.remove('scrolled');
});

// ── Ambil film_id dari URL ──
function getFilmIdFromURL() {
  const params = new URLSearchParams(window.location.search);
  return parseInt(params.get('film'));
}

// ── Load Detail Film ──
async function loadFilmDetail() {
  const filmId = getFilmIdFromURL();
  if (!filmId) {
    window.location.href = '/';
    return;
  }

  try {
    const res = await fetch(`/api/films/${filmId}`);
    if (!res.ok) throw new Error('Film tidak ditemukan');
    const film = await res.json();
    currentFilm = film;
    renderDetail(film);

    // Load semua film untuk seksi "Film Lainnya"
    const allRes = await fetch('/api/films');
    allFilms = await allRes.json();
    renderMoreFilms(allFilms.filter(f => f.id !== film.id));
  } catch (e) {
    document.getElementById('detail-loading').innerHTML = `
      <div style="text-align:center; color: var(--muted);">
        <p style="font-size:2rem; margin-bottom: 10px;">😕</p>
        <p>Film tidak ditemukan.</p>
        <a href="/" class="btn btn-accent" style="margin-top:15px; display:inline-flex;">← Kembali ke Home</a>
      </div>`;
  }
}

function renderDetail(film) {
  // Backdrop
  const backdrop = document.getElementById('detail-backdrop');
  backdrop.style.backgroundImage = `url('${film.poster_url}')`;

  // Poster & Glow
  const poster = document.getElementById('detail-poster');
  poster.src = film.poster_url;
  poster.alt = film.title;
  poster.onerror = () => {
    poster.src = 'https://via.placeholder.com/280x420/222534/888899?text=No+Poster';
  };

  // Breadcrumb
  document.getElementById('breadcrumb-title').textContent = film.title;
  document.title = `${film.title} - CineStream`;

  // Info teks
  document.getElementById('detail-title').textContent = film.title;
  document.getElementById('detail-year').textContent = film.year || '—';
  document.getElementById('detail-duration').textContent = film.duration ? `${film.duration} mnt` : '—';
  document.getElementById('detail-genre-text').textContent = film.genre || 'Film';
  document.getElementById('detail-genre-badge').textContent = film.genre || 'Film';
  document.getElementById('detail-synopsis').textContent = film.description || 'Tidak ada sinopsis tersedia.';

  // Tags dari genre
  const tagsEl = document.getElementById('detail-tags');
  const tags = generateTags(film);
  tagsEl.innerHTML = tags.map(t => `<span class="tag">${t}</span>`).join('');

  // Tombol aksi
  document.getElementById('btn-watch').onclick = () => {
    window.location.href = `/watch?film=${film.id}`;
  };
  document.getElementById('btn-party').onclick = () => {
    openModal(film.id, film.title);
  };

  // Tampilkan konten
  document.getElementById('detail-loading').style.display = 'none';
  document.getElementById('detail-content').style.display = 'block';
}

function generateTags(film) {
  const tags = [];
  if (film.genre) tags.push(film.genre);
  if (film.year) tags.push(film.year.toString());
  if (film.duration) {
    if (film.duration < 30) tags.push('Short Film');
    else if (film.duration < 90) tags.push('Medium Length');
    else tags.push('Feature Film');
  }
  tags.push('HD', 'Stream Gratis');
  return tags;
}

function renderMoreFilms(films) {
  const grid = document.getElementById('more-films-grid');
  if (films.length === 0) {
    grid.innerHTML = '<p style="color:var(--muted); font-size:13px;">Tidak ada film lain tersedia.</p>';
    return;
  }
  grid.innerHTML = films.map(f => `
    <div class="film-card" onclick="goToDetail(${f.id})" style="cursor:pointer;">
      <img class="film-poster" src="${f.poster_url}" alt="${f.title}"
           onerror="this.src='https://via.placeholder.com/200x300/222534/888899?text=Poster'">
      <div class="film-info">
        <div class="film-title" title="${f.title}">${f.title}</div>
        <div class="film-genre-text">${f.genre || 'Film'} • ${f.year || '—'}</div>
      </div>
      <div class="film-overlay">
        <button class="btn btn-accent" onclick="event.stopPropagation(); window.location.href='/watch?film=${f.id}'">▶ Tonton</button>
        <button class="btn btn-outline" onclick="event.stopPropagation(); openModal(${f.id}, '${f.title.replace(/'/g, "\\'")}')">👥 Party</button>
      </div>
    </div>
  `).join('');
}

function goToDetail(filmId) {
  window.location.href = `/movie?film=${filmId}`;
}

// ── Modal Room ──
function showJoinModal() {
  document.getElementById('modal').classList.add('open');
  switchModalTab('join');
  document.getElementById('tab-btn-create').style.display = 'none';
}

function openModal(filmId, title) {
  selectedFilmId = filmId;
  document.getElementById('modal-film-title').textContent = 'Terpilih: ' + title;
  document.getElementById('modal').classList.add('open');
  document.getElementById('tab-btn-create').style.display = 'block';
  switchModalTab('create');
}

function closeModal() {
  document.getElementById('modal').classList.remove('open');
  selectedFilmId = null;
}

function switchModalTab(tab) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.modal-form').forEach(f => f.classList.remove('active'));
  if (tab === 'create') {
    document.querySelectorAll('.tab-btn')[0].classList.add('active');
    document.getElementById('modal-create').classList.add('active');
  } else {
    document.querySelectorAll('.tab-btn')[1].classList.add('active');
    document.getElementById('modal-join').classList.add('active');
  }
}

async function createRoom() {
  const hostName = document.getElementById('host-name').value.trim() || 'Host';
  if (!selectedFilmId) { showToast('Pilih film dari katalog terlebih dahulu!'); return; }
  try {
    const res = await fetch('/api/rooms', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ film_id: selectedFilmId, host_name: hostName }),
    });
    const data = await res.json();
    window.location.href = `/watch?room=${data.room_code}&host=1&name=${encodeURIComponent(hostName)}`;
  } catch (e) { showToast('Gagal membuat room.'); }
}

async function joinRoom() {
  const code = document.getElementById('join-code').value.trim().toUpperCase();
  const name = document.getElementById('join-name').value.trim() || 'Penonton';
  if (!code || code.length !== 6) { showToast('Kode harus 6 karakter!'); return; }
  const res = await fetch(`/api/rooms/${code}`);
  if (!res.ok) { showToast('Room tidak ditemukan.'); return; }
  window.location.href = `/watch?room=${code}&name=${encodeURIComponent(name)}`;
}

function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3000);
}

// ── Inisiasi ──
loadFilmDetail();
