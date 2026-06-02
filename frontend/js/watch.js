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

// KUNCI PERBAIKAN 1: BYPASS NGINX, LANGSUNG TEMBAK KE FLASK (PORT 5000)
let socket =
  typeof io !== "undefined"
    ? io(`http://${window.location.hostname}:5000`)
    : null;
let isIgnoringEvents = false;

// ── PERBAIKAN: KONTROL HOST & AKSES FULLSCREEN GUEST (MOBILE FRIENDLY) ──
if (!IS_HOST && ROOM_CODE) {
  video.controls = false;
  video.addEventListener("click", () => {
    const isFullscreen =
      document.fullscreenElement ||
      document.webkitFullscreenElement ||
      document.mozFullScreenElement ||
      document.msFullscreenElement;
    if (!isFullscreen) {
      if (video.requestFullscreen) video.requestFullscreen();
      else if (video.webkitRequestFullscreen) video.webkitRequestFullscreen();
      else if (video.webkitEnterFullscreen) video.webkitEnterFullscreen();
      else if (video.msRequestFullscreen) video.msRequestFullscreen();
    } else {
      if (document.exitFullscreen) document.exitFullscreen();
      else if (document.webkitExitFullscreen) document.webkitExitFullscreen();
    }
  });

  video.addEventListener("play", (e) => {
    if (isIgnoringEvents) return;
    e.preventDefault();
    video.pause();
    showToast("Hanya Host yang dapat memulai film.");
  });

  video.addEventListener("pause", (e) => {
    if (isIgnoringEvents) return;
    e.preventDefault();
    video.play().catch(() => {});
    showToast("Hanya Host yang dapat menjeda film.");
  });
} else {
  video.controls = true;
}

// ── Logika Fetch Data Film ──
if (FILM_ID) {
  fetch(`/api/films/${FILM_ID}`)
    .then((res) => res.json())
    .then((film) => {
      document.getElementById("film-title").textContent = film.title;
      document.getElementById("film-meta").textContent =
        `${film.year} • ${film.genre} • ${film.format}`;
      document.getElementById("film-desc").textContent = film.description;

      // KUNCI PERBAIKAN 2: CASE-INSENSITIVE PATH SPLITTING
      let rawPath = film.hls_path || "";
      let safePath = rawPath.replace(/\\/g, "/");
      let lowerPath = safePath.toLowerCase();

      let streamUrl = "";
      if (lowerPath.includes("/media/hls/")) {
        let idx = lowerPath.indexOf("/media/hls/") + 11;
        streamUrl = "/media/hls/" + safePath.substring(idx);
      } else {
        if (safePath.startsWith("/")) safePath = safePath.substring(1);
        streamUrl = `/media/hls/${safePath}`;
      }
      if (!film.hls_path) streamUrl = `/media/hls/${film.id}/index.m3u8`;

      let subtitleUrl = streamUrl.replace("index.m3u8", "subtitle.vtt");

      const track = document.createElement("track");
      track.kind = "subtitles";
      track.label = "Subtitle";
      track.srclang = "id";
      track.src = subtitleUrl;
      track.default = true;
      video.appendChild(track);

      if (Hls.isSupported()) {
        const hls = new Hls();
        hls.loadSource(streamUrl);
        hls.attachMedia(video);
        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          if (!ROOM_CODE)
            video.play().catch((e) => console.log("Autoplay dicegah"));
        });
      } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
        video.src = streamUrl;
        video.addEventListener("loadedmetadata", () => {
          if (!ROOM_CODE) video.play();
        });
      }
    });
} else {
  showToast("ID Film tidak valid!");
}

// ── Logika Watch Party (Socket.IO) ──
if (ROOM_CODE) {
  document.getElementById("party-panel").style.display = "flex";
  document.getElementById("party-code").textContent = ROOM_CODE;

  socket.on("connect", () => {
    setSyncStatus(true, "Terhubung ke Party");
    socket.emit("join_room", {
      room_code: ROOM_CODE,
      username: USERNAME,
      is_host: IS_HOST,
    });
  });

  socket.on("disconnect", () => {
    setSyncStatus(false, "Terputus. Menghubungkan ulang...");
  });

  socket.on("user_list", (users) => {
    const list = document.getElementById("user-list");
    list.innerHTML = users
      .map(
        (u) =>
          `<li class="${u.is_host ? "host" : ""}">${u.username === USERNAME ? `<b>${u.username} (Kamu)</b>` : u.username}</li>`,
      )
      .join("");
    document.getElementById("user-count").textContent = users.length;
  });

  socket.on("chat_message", (data) => {
    appendChat(data.username, data.message, data.username === USERNAME);
  });

  socket.on("system_message", (data) => {
    addSystemMessage(data.message);
  });

  socket.on("room_closed", (data) => {
    showToast(data.message || "Host telah keluar. Room Watch Party ditutup.");
    isIgnoringEvents = true;
    video.pause();
    setTimeout(() => {
      window.location.href = "/";
    }, 2500);
  });

  // ── Sync Handler ──
  socket.on("video_play", (data) => {
    isIgnoringEvents = true;
    const diff = Math.abs(video.currentTime - data.current_time);
    if (diff > 1.5) video.currentTime = data.current_time;
    video.play().catch((e) => console.log(e));
    setTimeout(() => (isIgnoringEvents = false), 500);
  });

  socket.on("video_pause", (data) => {
    isIgnoringEvents = true;
    video.currentTime = data.current_time;
    video.pause();
    setTimeout(() => (isIgnoringEvents = false), 500);
  });

  socket.on("video_seek", (data) => {
    isIgnoringEvents = true;
    video.currentTime = data.current_time;
    setTimeout(() => (isIgnoringEvents = false), 500);
  });

  // ── Host Broadcaster ──
  if (IS_HOST) {
    video.addEventListener("play", () => {
      if (isIgnoringEvents) return;
      socket.emit("video_play", {
        room_code: ROOM_CODE,
        current_time: video.currentTime,
      });
    });

    video.addEventListener("pause", () => {
      if (isIgnoringEvents) return;
      socket.emit("video_pause", {
        room_code: ROOM_CODE,
        current_time: video.currentTime,
      });
    });

    video.addEventListener("seeked", () => {
      if (isIgnoringEvents) return;
      socket.emit("video_seek", {
        room_code: ROOM_CODE,
        current_time: video.currentTime,
      });
    });
  }
}

const tabRoom = document.getElementById("tab-room");
if (tabRoom && IS_HOST) {
  const endBtn = document.createElement("button");
  endBtn.className = "btn";
  endBtn.style.backgroundColor = "#ff0043";
  endBtn.style.color = "white";
  endBtn.style.marginTop = "20px";
  endBtn.style.width = "100%";
  endBtn.style.fontWeight = "bold";
  endBtn.innerHTML = "❌ Akhiri Watch Party";

  endBtn.onclick = () => {
    if (
      confirm(
        "Yakin ingin mengakhiri Watch Party untuk semua orang?\nRoom ini akan dihapus secara permanen.",
      )
    ) {
      socket.emit("end_party", { room_code: ROOM_CODE });
    }
  };
  tabRoom.appendChild(endBtn);
}

// ── Chat & UI ──
const chatInput = document.getElementById("chat-input");
chatInput.addEventListener("keypress", (e) => {
  if (e.key === "Enter") sendChat();
});

function sendChat() {
  const msg = chatInput.value.trim();
  if (msg && socket) {
    socket.emit("chat_message", { room_code: ROOM_CODE, message: msg });
    chatInput.value = "";
  }
}

function appendChat(sender, msg, isMe) {
  const box = document.getElementById("chat-messages");
  const el = document.createElement("div");
  el.className = `chat-msg ${isMe ? "me" : ""}`;
  const safeMsg = msg.replace(/</g, "&lt;").replace(/>/g, "&gt;");
  el.innerHTML = `<div class="sender">${sender}</div><div>${safeMsg}</div>`;
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
  if (dot) dot.className = `sync-dot ${connected ? "connected" : ""}`;
  const lbl = document.getElementById("sync-label");
  if (lbl) lbl.textContent = text;
}

function showToast(msg) {
  const toast = document.getElementById("toast");
  toast.textContent = msg;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 3000);
}
