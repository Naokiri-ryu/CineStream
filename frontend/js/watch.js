/**
 * CineStream - Watch Engine Logics
 */

// ── INJEKSI CSS ROTASI AJAIB ──
const fsStyle = document.createElement("style");
fsStyle.innerHTML = `
  .video-wrapper:fullscreen, 
  .video-wrapper:-webkit-full-screen {
      background-color: #000 !important;
      overflow: hidden !important;
      position: fixed !important;
      top: 0 !important;
      left: 0 !important;
      width: 100vw !important;
      height: 100vh !important;
      z-index: 9999 !important;
      margin: 0 !important;
      padding: 0 !important;
  }

  @media screen and (orientation: portrait) {
      .video-wrapper:fullscreen video, 
      .video-wrapper:-webkit-full-screen video {
          position: absolute !important;
          top: 50% !important;
          left: 50% !important;
          width: 100vh !important;
          height: 100vw !important;
          max-width: none !important;
          max-height: none !important;
          transform: translate(-50%, -50%) rotate(90deg) !important;
          transform-origin: center center !important;
          object-fit: contain !important;
          margin: 0 !important;
          padding: 0 !important;
      }
      
      .video-wrapper:fullscreen button,
      .video-wrapper:-webkit-full-screen button {
          transform: rotate(90deg) !important;
          right: auto !important;
          left: 20px !important;
          bottom: 20px !important;
          z-index: 10000 !important;
      }
  }

  @media screen and (orientation: landscape) {
      .video-wrapper:fullscreen video, 
      .video-wrapper:-webkit-full-screen video {
          position: absolute !important;
          top: 0 !important;
          left: 0 !important;
          width: 100vw !important;
          height: 100vh !important;
          max-width: none !important;
          max-height: none !important;
          object-fit: contain !important;
          transform: none !important;
          margin: 0 !important;
          padding: 0 !important;
      }
  }
`;
document.head.appendChild(fsStyle);

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
let socket = typeof io !== "undefined" ? io({ transports: ["polling"] }) : null;
let isIgnoringEvents = false;
let _lastTime = 0;
let hostIsPlaying = false;

// ── KONTROL HOST & AKSES FULLSCREEN GUEST ──
if (!IS_HOST && ROOM_CODE) {
  video.controls = false;
  video.removeAttribute("controls");
  video.setAttribute("playsinline", "");
  video.setAttribute("webkit-playsinline", "");

  video.style.width = "100%";
  video.style.height = "100%";
  video.style.objectFit = "contain";
  video.style.pointerEvents = "none";

  const wrapper = document.querySelector(".video-wrapper");
  if (wrapper) {
    wrapper.style.position = "relative";
    wrapper.style.display = "flex";
    wrapper.style.alignItems = "center";
    wrapper.style.justifyContent = "center";
    wrapper.style.background = "#000";

    const glass = document.createElement("div");
    glass.style.position = "absolute";
    glass.style.top = "0";
    glass.style.left = "0";
    glass.style.width = "100%";
    glass.style.height = "100%";
    glass.style.zIndex = "10";
    wrapper.appendChild(glass);

    const fsBtn = document.createElement("button");
    fsBtn.innerHTML = "⛶";
    fsBtn.title = "Perbesar Layar";
    fsBtn.style.position = "absolute";
    fsBtn.style.bottom = "15px";
    fsBtn.style.right = "15px";
    fsBtn.style.zIndex = "15";
    fsBtn.style.background = "#ff0043";
    fsBtn.style.color = "white";
    fsBtn.style.border = "none";
    fsBtn.style.borderRadius = "6px";
    fsBtn.style.padding = "8px 12px";
    fsBtn.style.fontSize = "18px";
    fsBtn.style.cursor = "pointer";
    fsBtn.style.boxShadow = "0 4px 10px rgba(0,0,0,0.5)";
    fsBtn.style.transition = "transform 0.3s";
    wrapper.appendChild(fsBtn);

    const toggleFullscreen = async () => {
      const isFullscreen =
        document.fullscreenElement || document.webkitFullscreenElement;
      if (!isFullscreen) {
        try {
          if (wrapper.requestFullscreen) await wrapper.requestFullscreen();
          else if (wrapper.webkitRequestFullscreen)
            await wrapper.webkitRequestFullscreen();

          if (screen.orientation && screen.orientation.lock) {
            screen.orientation.lock("landscape").catch(() => {});
          }
        } catch (e) {}
      } else {
        try {
          if (document.exitFullscreen) await document.exitFullscreen();
          else if (document.webkitExitFullscreen)
            await document.webkitExitFullscreen();

          if (screen.orientation && screen.orientation.unlock) {
            screen.orientation.unlock();
          }
        } catch (e) {}
      }
    };

    fsBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleFullscreen();
    });

    glass.addEventListener("dblclick", (e) => {
      e.stopPropagation();
      toggleFullscreen();
    });
  }

  video.addEventListener("play", (e) => {
    if (isIgnoringEvents) return;
    if (!hostIsPlaying) {
      e.preventDefault();
      video.pause();
      showToast("Menunggu Host untuk memulai film.");
    }
  });

  video.addEventListener("pause", (e) => {
    if (isIgnoringEvents) return;
    if (hostIsPlaying) {
      e.preventDefault();
      video.play().catch(() => {});
      showToast("Hanya Host yang dapat menjeda film.");
    }
  });

  video.addEventListener("timeupdate", () => {
    if (isIgnoringEvents) return;
    if (Math.abs(video.currentTime - _lastTime) < 1.5) {
      _lastTime = video.currentTime;
    }
  });

  video.addEventListener("seeking", (e) => {
    if (isIgnoringEvents) return;
    if (Math.abs(video.currentTime - _lastTime) > 2) {
      video.currentTime = _lastTime;
      showToast("Hanya Host yang dapat mempercepat film.");
    }
  });
} else {
  video.controls = true;
}

if (!ROOM_CODE) {
  const syncStatusDiv = document.querySelector(".sync-status");
  if (syncStatusDiv) syncStatusDiv.style.display = "none";
}

// ── FUNGSI PEMUAT VIDEO ──
function loadVideoPlayer(film) {
  const titleEl = document.getElementById("video-title");
  if (titleEl) titleEl.textContent = film.title;

  const metaEl = document.getElementById("film-meta");
  if (metaEl && film.year)
    metaEl.textContent = `${film.year} • ${film.genre} • ${film.format}`;
  const descEl = document.getElementById("film-desc");
  if (descEl && film.description) descEl.textContent = film.description;

  let rawPath = film.hls_path || "";
  let safePath = rawPath.replace(/\\/g, "/");
  let streamUrl = "";

  if (safePath.toLowerCase().includes("/media/hls/")) {
    let parts = safePath.split(new RegExp("/media/hls/", "i"));
    streamUrl = "/media/hls/" + parts[1];
  } else {
    if (safePath.startsWith("/")) safePath = safePath.substring(1);
    streamUrl = `/media/hls/${safePath}`;
  }
  if (!film.hls_path)
    streamUrl = `/media/hls/${film.id || film.film_id}/index.m3u8`;

  // === PERBAIKAN: JANGAN PAKSA SUBTITLE JIKA BISA BIKIN HANG ===
  if (film.has_subtitle) {
    let subtitleUrl = streamUrl.replace("index.m3u8", "subtitle.vtt");
    const track = document.createElement("track");
    track.kind = "subtitles";
    track.label = "Subtitle";
    track.srclang = "id";
    track.src = subtitleUrl;
    // KUNCI: Jangan gunakan `track.default = true;` di sini!
    // Biarkan user mengaktifkannya secara manual dari logo "CC" di player video.
    video.appendChild(track);
  }

  // === PERBAIKAN: TAMBAHKAN PELACAK ERROR HLS ===
  if (Hls.isSupported()) {
    const hls = new Hls();
    hls.loadSource(streamUrl);
    hls.attachMedia(video);

    hls.on(Hls.Events.MANIFEST_PARSED, () => {
      if (!ROOM_CODE) video.play().catch(() => {});
    });

    hls.on(Hls.Events.ERROR, (event, data) => {
      if (data.fatal) {
        console.error("HLS Error:", data);
        if (data.type === Hls.ErrorTypes.NETWORK_ERROR) {
          showToast("Gagal memuat video. Cek jalur HLS!");
        }
      }
    });
  } else {
    video.src = streamUrl;
    video.load();
    video.addEventListener("loadedmetadata", () => {
      if (!ROOM_CODE) video.play();
    });
  }
}

// ── LOGIKA JALUR ──
if (ROOM_CODE) {
  fetch(`/api/rooms/${ROOM_CODE}`)
    .then((res) => {
      if (!res.ok) throw new Error("Room tidak valid atau sudah ditutup.");
      return res.json();
    })
    .then((roomData) => fetch(`/api/films/${roomData.film_id}`))
    .then((res) => res.json())
    .then((filmData) => loadVideoPlayer(filmData))
    .catch((err) => {
      showToast(err.message);
      console.error(err);
    });
} else if (FILM_ID) {
  fetch(`/api/films/${FILM_ID}`)
    .then((res) => res.json())
    .then((filmData) => loadVideoPlayer(filmData))
    .catch((err) => console.error("Gagal memuat API Film:", err));
} else {
  showToast("ID Film atau Kode Room tidak valid!");
}

// ── Logika Watch Party (Socket.IO) ──
if (ROOM_CODE) {
  const displayCode = document.getElementById("display-room-code");
  if (displayCode) displayCode.textContent = ROOM_CODE;

  const displayRole = document.getElementById("display-role");
  if (displayRole)
    displayRole.textContent = IS_HOST
      ? "Host (Pembuat Room)"
      : "Penonton (Guest)";

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
    if (list) {
      list.innerHTML = users
        .map(
          (u) =>
            `<li class="${u.is_host ? "host" : ""}">${u.username === USERNAME ? `<b>${u.username} (Kamu)</b>` : u.username}</li>`,
        )
        .join("");
    }
    const count = document.getElementById("user-count");
    if (count) count.textContent = users.length;

    const hostUser = users.find((u) => u.is_host);
    const hostDisplay = document.getElementById("display-host");
    if (hostDisplay && hostUser) hostDisplay.textContent = hostUser.username;
  });

  socket.on("chat_message", (data) => {
    appendChat(data.username, data.message, false);
  });

  socket.on("system_message", (data) => {
    addSystemMessage(data.message);
  });

  socket.on("room_closed", (data) => {
    showToast(
      data.message ||
        "Host telah mengakhiri Party. Anda dikembalikan ke Beranda.",
    );
    isIgnoringEvents = true;
    video.pause();
    setTimeout(() => {
      window.location.href = "/";
    }, 2000);
  });

  // ── Sync Handler ──
  socket.on("video_play", (data) => {
    isIgnoringEvents = true;
    hostIsPlaying = true;
    const diff = Math.abs(video.currentTime - data.current_time);
    if (diff > 1.5) video.currentTime = data.current_time;
    video.play().catch((e) => {
      showToast("Ketuk tombol layar atau ketuk 2x untuk memutar.");
    });
    setTimeout(() => (isIgnoringEvents = false), 500);
  });

  socket.on("video_pause", (data) => {
    isIgnoringEvents = true;
    hostIsPlaying = false;
    video.currentTime = data.current_time;
    video.pause();
    setTimeout(() => (isIgnoringEvents = false), 500);
  });

  socket.on("video_seek", (data) => {
    isIgnoringEvents = true;
    video.currentTime = data.current_time;
    _lastTime = data.current_time;
    setTimeout(() => (isIgnoringEvents = false), 500);
  });

  if (IS_HOST) {
    video.addEventListener("play", () => {
      if (isIgnoringEvents) return;
      hostIsPlaying = true;
      socket.emit("video_play", {
        room_code: ROOM_CODE,
        current_time: video.currentTime,
      });
    });
    video.addEventListener("pause", () => {
      if (isIgnoringEvents) return;
      hostIsPlaying = false;
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
        "Yakin ingin mengakhiri Watch Party?\nSemua penonton akan dikeluarkan.",
      )
    ) {
      socket.emit("end_party", { room_code: ROOM_CODE });
      setTimeout(() => {
        window.location.href = "/";
      }, 500);
    }
  };
  tabRoom.appendChild(endBtn);
}

window.sendChatMessage = function (e) {
  if (e) e.preventDefault();
  const chatInput = document.getElementById("chat-input");
  if (!chatInput) return;

  const msg = chatInput.value.trim();
  if (msg && socket) {
    socket.emit("chat_message", { room_code: ROOM_CODE, message: msg });
    appendChat(USERNAME, msg, true);
    chatInput.value = "";
  }
};

function appendChat(sender, msg, isMe) {
  const box = document.getElementById("chat-messages");
  if (!box) return;
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
  if (!box) return;
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
    const btn = document.getElementById("btn-tab-room");
    const tab = document.getElementById("tab-room");
    if (btn) btn.classList.add("active");
    if (tab) tab.classList.add("active");
  } else {
    const btn = document.getElementById("btn-tab-chat");
    const tab = document.getElementById("tab-chat");
    if (btn) btn.classList.add("active");
    if (tab) tab.classList.add("active");
  }
}

function setSyncStatus(connected, text) {
  const dot = document.getElementById("sync-dot");
  if (dot) dot.className = `sync-dot ${connected ? "connected" : ""}`;
  const lbl = document.getElementById("sync-label");
  if (lbl) lbl.textContent = text;
}

function copyRoomCode() {
  if (!ROOM_CODE) return;
  navigator.clipboard.writeText(ROOM_CODE);
  showToast("Kode Room disalin: " + ROOM_CODE);
}

function showToast(msg) {
  let toast = document.getElementById("toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "toast";
    toast.className = "toast";
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 3000);
}
