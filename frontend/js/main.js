let allFilms = [];
let heroIndex = 0;
let heroInterval;
let selectedFilmId = null;

// Melacak pengunjung aktif secara global di background
if (typeof io !== "undefined" && !window.location.pathname.includes("/watch")) {
  const globalSocket = io({ transports: ["polling"] });
}

const mobileToggle = document.getElementById("mobile-toggle");
const navLinks = document.getElementById("nav-links");
if (mobileToggle) {
  mobileToggle.addEventListener("click", () => {
    navLinks.classList.toggle("show");
  });
}

// ── Logika Tema (Light/Dark Mode) ──
const themeToggle = document.getElementById("theme-toggle");
const currentTheme = localStorage.getItem("theme") || "dark";

// Set tema awal saat halaman dimuat
document.documentElement.setAttribute("data-theme", currentTheme);
themeToggle.textContent = currentTheme === "dark" ? "☀️" : "🌙";

themeToggle.addEventListener("click", () => {
  let theme = document.documentElement.getAttribute("data-theme");
  if (theme === "dark") {
    document.documentElement.setAttribute("data-theme", "light");
    localStorage.setItem("theme", "light");
    themeToggle.textContent = "🌙";
  } else {
    document.documentElement.setAttribute("data-theme", "dark");
    localStorage.setItem("theme", "dark");
    themeToggle.textContent = "☀️";
  }
});

// Mengubah background navbar saat di-scroll
window.addEventListener("scroll", () => {
  const nav = document.getElementById("navbar");
  if (window.scrollY > 50) nav.classList.add("scrolled");
  else nav.classList.remove("scrolled");
});

// Mengambil data film dari API
async function loadFilms() {
  try {
    const res = await fetch("/api/films");
    allFilms = await res.json();
    document.getElementById("film-count").textContent = allFilms.length;
    if (allFilms.length > 0) {
      initHeroCarousel();
      renderFilms(allFilms);
    }
    // Muat room aktif setelah film dimuat
    loadActiveRooms();
    // Refresh daftar room tiap 10 detik
    setInterval(loadActiveRooms, 10000);
  } catch (e) {
    document.getElementById("film-grid").innerHTML =
      '<div class="loading">Gagal terhubung ke server.</div>';
  }
}

async function loadActiveRooms() {
  try {
    const res = await fetch("/api/rooms/active");
    const rooms = await res.json();
    const grid = document.getElementById("active-rooms-grid");

    if (rooms.length === 0) {
      grid.innerHTML =
        '<div style="color: var(--muted); font-size: 13px; grid-column: 1 / -1;">Saat ini belum ada Watch Party yang sedang berlangsung.</div>';
      return;
    }

    grid.innerHTML = rooms
      .map(
        (r) => `
      <div class="room-card">
        <div class="room-card-title">🎬 ${r.film_title}</div>
        <div class="room-card-meta">
          Host: <b>${r.host}</b><br>
          Penonton: ${r.users_count} orang
        </div>
        <button class="btn btn-accent" style="width:100%; font-size: 12px;" onclick="joinActiveRoom('${r.code}')">Gabung (Code: ${r.code})</button>
      </div>
    `,
      )
      .join("");
  } catch (e) {
    console.log("Gagal memuat room aktif.");
  }
}

function joinActiveRoom(code) {
  document.getElementById("join-code").value = code;
  showJoinModal();
}

// ── Logika Hero Carousel ──
function initHeroCarousel() {
  updateHeroUI();
  // Ganti slide setiap 5 detik
  heroInterval = setInterval(nextSlide, 5000);
}

function updateHeroUI() {
  if (!allFilms[heroIndex]) return;
  const film = allFilms[heroIndex];
  const heroSec = document.getElementById("hero-section");
  const heroContent = document.getElementById("hero-content");

  // Set Background
  heroSec.style.backgroundImage = `url('${film.poster_url}')`;

  // Set Teks
  heroContent.innerHTML = `
    <span class="hero-badge">PREMIUM</span>
    <h1 class="hero-title">${film.title}</h1>
    <div class="hero-meta">
      <span>Tahun: ${film.year || "—"}</span>
      <span>Genre: ${film.genre || "Film"}</span>
      <span>Durasi: ${film.duration ? film.duration + " mnt" : "—"}</span>
      <span style="color: #d29922;">★ ${film.rating ? film.rating.toFixed(1) : "N/A"}</span>
    </div>
    <div style="display: flex; gap: 10px;">
      <button class="btn btn-accent" onclick="watchFilm(${film.id})">▶ TONTON SEKARANG</button>
      <button class="btn btn-outline" onclick="openModal(${film.id}, '${film.title.replace(/'/g, "\\'")}')">👥 WATCH PARTY</button>
      <button class="btn btn-outline" onclick="goToDetail(${film.id})" style="font-size:13px;">ℹ INFO</button>
    </div>
  `;
}

function nextSlide() {
  heroIndex = (heroIndex + 1) % allFilms.length;
  updateHeroUI();
}

function prevSlide() {
  heroIndex = (heroIndex - 1 + allFilms.length) % allFilms.length;
  updateHeroUI();
}

// ── Logika Katalog Scroll ──
function renderFilms(films) {
  const grid = document.getElementById("film-grid");
  if (!grid) return;

  if (films.length === 0) {
    grid.innerHTML =
      '<p style="grid-column: 1/-1; text-align:center; color:var(--muted); padding: 40px 0;">Tidak ada film yang ditemukan.</p>';
    return;
  }

  grid.innerHTML = films
    .map(
      (f) => `
    <div class="film-card" onclick="goToDetail(${f.id})" style="cursor:pointer;">
      <img class="film-poster" src="${f.poster_url}" alt="${f.title}"
           onerror="this.src='https://via.placeholder.com/200x300/222534/888899?text=Poster'">
      <div class="film-info">
        <div class="film-title" title="${f.title}">${f.title}</div>
        <div class="film-genre-text">${f.genre || "Film"} • ${f.year || "—"}</div>
      </div>
      <div class="film-overlay">
        <button class="btn btn-accent" onclick="event.stopPropagation(); window.location.href='/watch?film=${f.id}'">▶ Tonton</button>
        <button class="btn btn-outline" onclick="event.stopPropagation(); openModal(${f.id}, '${f.title.replace(/'/g, "\\'")}')">👥 Party</button>
        <button class="btn btn-outline" onclick="event.stopPropagation(); goToDetail(${f.id})" style="font-size:11px;">ℹ Detail Film</button>
      </div>
    </div>
  `,
    )
    .join("");
}

// Tambahkan fungsi ini di bawahnya jika belum ada di main.js
function goToDetail(id) {
  window.location.href = `/movie?id=${id}`;
}

function filterFilms() {
  const q = document.getElementById("search").value.toLowerCase();
  renderFilms(
    allFilms.filter(
      (f) =>
        f.title.toLowerCase().includes(q) ||
        (f.genre || "").toLowerCase().includes(q),
    ),
  );
}

function watchFilm(filmId) {
  window.location.href = `/watch?film=${filmId}`;
}

function goToDetail(filmId) {
  window.location.href = `/movie?film=${filmId}`;
}

// ── Logika Modal & Room ──
function showJoinModal() {
  document.getElementById("modal").classList.add("open");
  switchModalTab("join");
  // Sembunyikan tab Buat Room jika dipanggil dari navbar
  document.getElementById("tab-btn-create").style.display = "none";
}

function openModal(filmId) {
  // Cari data film di katalog berdasarkan ID
  const film = allFilms.find((f) => f.id === filmId);
  if (!film) return; // Jika gagal, hentikan

  selectedFilmId = film.id;
  document.getElementById("modal-film-title").textContent =
    "Terpilih: " + film.title;
  document.getElementById("modal").classList.add("open");
  document.getElementById("tab-btn-create").style.display = "block";
  switchModalTab("create");
}

function closeModal() {
  document.getElementById("modal").classList.remove("open");
  selectedFilmId = null;
}

function switchModalTab(tab) {
  document
    .querySelectorAll(".tab-btn")
    .forEach((b) => b.classList.remove("active"));
  document
    .querySelectorAll(".modal-form")
    .forEach((f) => f.classList.remove("active"));

  if (tab === "create") {
    document.querySelectorAll(".tab-btn")[0].classList.add("active");
    document.getElementById("modal-create").classList.add("active");
  } else {
    document.querySelectorAll(".tab-btn")[1].classList.add("active");
    document.getElementById("modal-join").classList.add("active");
  }
}

async function createRoom() {
  const hostName = document.getElementById("host-name").value.trim() || "Host";
  if (!selectedFilmId) {
    showToast("Pilih film dari katalog terlebih dahulu!");
    return;
  }

  try {
    const res = await fetch("/api/rooms", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ film_id: selectedFilmId, host_name: hostName }),
    });
    const data = await res.json();
    window.location.href = `/watch?room=${data.room_code}&host=1&name=${encodeURIComponent(hostName)}`;
  } catch (e) {
    showToast("Gagal membuat room.");
  }
}

async function joinRoom() {
  const code = document.getElementById("join-code").value.trim().toUpperCase();
  const name = document.getElementById("join-name").value.trim() || "Penonton";
  if (!code || code.length !== 6) {
    showToast("Kode harus 6 karakter!");
    return;
  }

  const res = await fetch(`/api/rooms/${code}`);
  if (!res.ok) {
    showToast("Room tidak ditemukan.");
    return;
  }
  window.location.href = `/watch?room=${code}&name=${encodeURIComponent(name)}`;
}

function showToast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 3000);
}

// Menjalankan inisiasi awal
loadFilms();
