/**
 * CineStream - Watch Engine Logics
 */

// ── Logika Tema ──
const themeToggle = document.getElementById("theme-toggle");
const currentTheme = localStorage.getItem("theme") || "dark";
document.documentElement.setAttribute("data-theme", currentTheme);
if (themeToggle) {
  themeToggle.textContent = currentTheme === "dark" ? "☀️" : "🌙";
  themeToggle.addEventListener("click", () => {
    let theme = document.documentElement.getAttribute("data-theme");
    let newTheme = theme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", newTheme);
    localStorage.setItem("theme", newTheme);
    themeToggle.textContent = newTheme === "dark" ? "☀️" : "🌙";
  });
}

const urlParams = new URLSearchParams(window.location.search);
const FILM_ID = urlParams.get("film");
const ROOM_CODE = urlParams.get("room")
  ? urlParams.get("room").toUpperCase()
  : null;
const IS_HOST = urlParams.get("host") === "1";
const USERNAME = urlParams.get("name") || (IS_HOST ? "Host" : "Penonton");

const video = document.getElementById("video");
let socket = null;
let isIgnoringEvents = false;

// ENFORCE HOST ONLY CONTROLS
if (!IS_HOST && ROOM_CODE) {
  // Hilangkan menu pemutar (play/pause/timeline) agar penonton tidak bisa mengatur video
  video.removeAttribute("controls");
  video.style.pointerEvents = "none"; // Cegah klik ganda di layar
}

async function initWatchPage() {
  if (ROOM_CODE) {
    await loadFilmDetailsByRoom(ROOM_CODE);
    initSocketConnection();
  } else if (FILM_ID) {
    await loadDirectFilmDetails(FILM_ID);
    setSyncStatus(true, "Mode Tonton Mandiri (Offline Chat)");
    document.getElementById("user-list").innerHTML =
      "<li>👤 Anda (Mandiri)</li>";
  } else {
    window.location.href = "/";
  }
}

async function loadDirectFilmDetails(id) {
  const res = await fetch(`/api/films/${id}`);
  if (!res.ok) window.location.href = "/";
  setupVideoPlayer(await res.json());
}

async function loadFilmDetailsByRoom(code) {
  const res = await fetch(`/api/rooms/${code}`);
  if (!res.ok) {
    alert("Room tidak ditemukan!");
    window.location.href = "/";
    return;
  }
  const roomData = await res.json();

  document.getElementById("display-room-code").textContent = roomData.room_code;
  document.getElementById("display-host").textContent = roomData.host_name;
  document.getElementById("display-role").textContent = IS_HOST
    ? "Pembuat Room (Host)"
    : "Peserta Tontonan";

  setupVideoPlayer(roomData);
}

function setupVideoPlayer(mediaSource) {
  document.getElementById("video-title").textContent = mediaSource.title;
  const hlsUrl = `/media/hls/${mediaSource.hls_path}`;

  if (Hls.isSupported()) {
    const hls = new Hls();
    hls.loadSource(hlsUrl);
    hls.attachMedia(video);
  } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
    video.src = hlsUrl;
  }
  setupLocalVideoEvents();
}

function initSocketConnection() {
  socket = io(window.location.origin, { transports: ["websocket"] });

  socket.on("connect", () => {
    setSyncStatus(true, "Terhubung ke Watch Party");
    socket.emit("join_room", {
      room_code: ROOM_CODE,
      username: USERNAME,
      is_host: IS_HOST,
    });
  });

  socket.on("disconnect", () => {
    setSyncStatus(false, "Koneksi terputus!");
  });

  // Menerima data daftar penonton real-time
  socket.on("user_list_update", (users) => {
    document.getElementById("user-count").textContent = users.length;
    const list = document.getElementById("user-list");
    list.innerHTML = users
      .map(
        (u) => `<li class="${u.is_host ? "host" : ""}">👤 ${u.username}</li>`,
      )
      .join("");
  });

  socket.on("system_message", (data) => addSystemMessage(data.message));
  socket.on("chat_message", (data) =>
    renderIncomingChat(data.username, data.message),
  );

  // Menerima sinkronisasi awal saat baru masuk
  socket.on("sync_state", (data) => {
    if (IS_HOST) return;
    ignoreLocalVideoEvents(() => {
      video.currentTime = data.current_time;
      if (data.is_playing) video.play().catch(() => {});
      else video.pause();
    });
  });

  // Menerima perintah dari Host
  socket.on("video_play", (data) => {
    if (IS_HOST) return;
    ignoreLocalVideoEvents(() => {
      video.currentTime = data.current_time;
      video.play().catch(() => {});
    });
  });

  socket.on("video_pause", (data) => {
    if (IS_HOST) return;
    ignoreLocalVideoEvents(() => {
      video.currentTime = data.current_time;
      video.pause();
    });
  });

  socket.on("video_seek", (data) => {
    if (IS_HOST) return;
    ignoreLocalVideoEvents(() => {
      video.currentTime = data.current_time;
    });
  });
}

function setupLocalVideoEvents() {
  video.addEventListener("play", () => {
    if (!ROOM_CODE || isIgnoringEvents || !IS_HOST) return;
    socket.emit("video_play", {
      room_code: ROOM_CODE,
      current_time: video.currentTime,
    });
  });
  video.addEventListener("pause", () => {
    if (!ROOM_CODE || isIgnoringEvents || !IS_HOST) return;
    socket.emit("video_pause", {
      room_code: ROOM_CODE,
      current_time: video.currentTime,
    });
  });
  video.addEventListener("seeked", () => {
    if (!ROOM_CODE || isIgnoringEvents || !IS_HOST) return;
    socket.emit("video_seek", {
      room_code: ROOM_CODE,
      current_time: video.currentTime,
    });
  });
}

function ignoreLocalVideoEvents(callback) {
  isIgnoringEvents = true;
  callback();
  setTimeout(() => {
    isIgnoringEvents = false;
  }, 400);
}

// PERBAIKAN BUG CHAT DI SINI
function sendChatMessage(event) {
  event.preventDefault();
  const input = document.getElementById("chat-input");
  const msg = input.value.trim(); // Menggunakan .value, bukan .text()
  if (!msg) return;

  if (ROOM_CODE && socket) {
    socket.emit("chat_message", {
      room_code: ROOM_CODE,
      username: USERNAME,
      message: msg,
    });
    renderIncomingChat("Anda", msg, true);
  } else {
    renderIncomingChat("Anda", msg, true);
  }
  input.value = "";
}

function renderIncomingChat(sender, message, isMe = false) {
  const box = document.getElementById("chat-messages");
  const el = document.createElement("div");
  el.className = `chat-msg ${isMe ? "me" : ""}`;
  const safeMsg = message.replace(/</g, "&lt;").replace(/>/g, "&gt;");
  el.innerHTML = `<div class="user">${sender}</div><div>${safeMsg}</div>`;
  box.appendChild(el);
  box.scrollTop = box.scrollHeight;
  if (!isMe) switchTab("chat");
}

function addSystemMessage(text) {
  const box = document.getElementById("chat-messages");
  const el = document.createElement("div");
  el.className = "chat-msg system";
  el.textContent = text;
  box.appendChild(el);
  box.scrollTop = box.scrollHeight;
}

function switchTab(targetTab) {
  document
    .querySelectorAll(".tab")
    .forEach((t) => t.classList.remove("active"));
  document
    .querySelectorAll(".tab-panel")
    .forEach((p) => p.classList.remove("active"));
  if (targetTab === "room") {
    document.getElementById("btn-tab-room").classList.add("active");
    document.getElementById("tab-room").classList.add("active");
  } else {
    document.getElementById("btn-tab-chat").classList.add("active");
    document.getElementById("tab-chat").classList.add("active");
  }
}

function setSyncStatus(connected, text) {
  const dot = document.getElementById("sync-dot");
  dot.className = `sync-dot ${connected ? "connected" : ""}`;
  document.getElementById("sync-label").textContent = text;
}

function copyRoomCode() {
  if (!ROOM_CODE) return;
  navigator.clipboard.writeText(ROOM_CODE).then(() => {
    const btn = document.getElementById("btn-copy-code");
    btn.textContent = "✅ Tersalin!";
    setTimeout(() => {
      btn.textContent = "📋 Salin Kode";
    }, 2000);
  });
}

initWatchPage();
