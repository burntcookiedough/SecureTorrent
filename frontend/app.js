const API_URL = window.location.origin;
const socket = io(API_URL);

// --- UI State ---
let currentTorrentId = null;
let totalPieces = 0;
let isScanning = false;
let maxRisk = 0;

// --- Visualizer Setup ---
const gridPlane = document.getElementById("gridPlane");
const hexDump = document.getElementById("hexDump");
const logFeed = document.getElementById("logFeed");

// --- Canvas Noise Effect (Fake Waveform) ---
const canvas = document.getElementById("noiseCanvas");
const ctx = canvas.getContext("2d");
let noiseData = new Array(50).fill(0);

function resizeCanvas() {
  canvas.width = canvas.parentElement.offsetWidth;
  canvas.height = canvas.parentElement.offsetHeight;
}

window.addEventListener("resize", resizeCanvas);
resizeCanvas();

// --- FPS & Uptime ---
let lastFrameTime = performance.now();
let frameCount = 0;
const fpsEl = document.getElementById("fpsCounter");

function drawNoise() {
  // FPS Calculation
  const now = performance.now();
  frameCount++;
  if (now - lastFrameTime >= 1000) {
    if (fpsEl) fpsEl.innerText = frameCount;
    frameCount = 0;
    lastFrameTime = now;
  }

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#00f0ff";

  // Shift data
  noiseData.shift();
  // If scanning, high noise, else low noise
  const volatility = isScanning ? 50 : 5;
  noiseData.push(Math.random() * volatility);

  const barWidth = canvas.width / noiseData.length;

  noiseData.forEach((val, i) => {
    const height = val;
    ctx.fillRect(i * barWidth, canvas.height - height, barWidth - 1, height);
  });
  requestAnimationFrame(drawNoise);
}

drawNoise();

// Uptime Counter
const startTime = Date.now();
const uptimeEl = document.getElementById("uptime");

setInterval(() => {
  if (!uptimeEl) return;
  const diff = Date.now() - startTime;
  const h = Math.floor(diff / 3600000)
    .toString()
    .padStart(2, "0");
  const m = Math.floor((diff % 3600000) / 60000)
    .toString()
    .padStart(2, "0");
  const s = Math.floor((diff % 60000) / 1000)
    .toString()
    .padStart(2, "0");
  uptimeEl.innerText = `${h}:${m}:${s}`;
}, 1000);

// --- Hex Dump Simulation ---
function updateHex(riskLevel) {
  let hex = "";

  for (let i = 0; i < 4; i++) {
    for (let j = 0; j < 8; j++) {
      let val = Math.floor(Math.random() * 255)
        .toString(16)
        .toUpperCase()
        .padStart(2, "0");

      if (isScanning && Math.random() > 0.8) {
        if (riskLevel > 50) hex += `<span class="hex-danger">${val}</span>`;
        else hex += `<span class="hex-highlight">${val}</span>`;
      } else {
        hex += `${val} `;
      }
    }
    hex += "<br>";
  }

  hexDump.innerHTML = hex;
}

setInterval(() => {
  if (isScanning) updateHex(0);
}, 100);

// --- Logging System ---
function log(msg, type = "info") {
  const el = document.createElement("div");
  el.className = `log-item ${type}`;
  const ts = new Date().toLocaleTimeString("en-GB");
  el.innerHTML = `<span class="ts">${ts}</span><span>${msg}</span>`;
  logFeed.prepend(el); // Newest top
  if (logFeed.children.length > 20) logFeed.lastChild.remove();
}

// --- Helper: Format Bytes ---
function formatBytes(bytes) {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

// --- Save Log Function ---
function saveLog() {
  const logs = Array.from(document.querySelectorAll(".log-item"))
    .map((el) => {
      const ts = el.querySelector(".ts")?.innerText || "";
      const msg = el.innerText.replace(ts, "").trim();
      return `[${ts}] ${msg}`;
    })
    .join("\n");

  const blob = new Blob([logs], { type: "text/plain" });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `torrentguard_log_${new Date().toISOString().replace(/[:.]/g, "-")}.txt`;
  a.click();
  window.URL.revokeObjectURL(url);
}

// --- Socket Logic ---
socket.on("connect", () => {
  document.getElementById("netStat").classList.add("on");
  document.getElementById("netStat").style.background = "var(--c-accent-main)";
  log("UPLINK_ESTABLISHED", "info");
});

socket.on("disconnect", () => {
  document.getElementById("netStat").classList.remove("on");
  document.getElementById("netStat").style.background = "var(--c-accent-crit)";
  log("CARRIER_LOST", "err");
});

socket.on("download_started", (data) => {
  log("DOWNLOAD_STARTED", "info");
  document.getElementById("engineText").innerText = "ENGINE_ACTIVE";
  document.getElementById("engineLight").style.boxShadow =
    "0 0 8px var(--c-accent-warn)";
  document.getElementById("engineLight").style.background =
    "var(--c-accent-warn)";
});

// --- Upload Handling ---
const fileInput = document.getElementById("fileInput");

fileInput.addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;

  log(`PARSING_OBJECT: ${file.name}`, "info");
  document.getElementById("dropZone").innerHTML =
    `<div style="color:var(--c-accent-main)">UPLOADING...</div>`;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch(`${API_URL}/api/upload-torrent`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();

    if (data.success) {
      currentTorrentId = data.torrent.torrent_id;
      totalPieces = data.torrent.total_pieces;

      document.getElementById("metaName").innerText = data.torrent.name;
      document.getElementById("metaSize").innerText = formatBytes(
        data.torrent.total_size,
      );
      document.getElementById("metaHash").innerText = currentTorrentId;
      document.getElementById("btnScan").disabled = false;
      document.getElementById("dropZone").innerHTML =
        `<div style="font-size:32px; color:var(--c-accent-main)">✔</div> <div>READY</div>`;

      log("METADATA_LOCKED", "info");
    } else {
      log("UPLOAD_FAIL: " + data.error, "err");
    }
  } catch (err) {
    log("TRANSMISSION_ERROR", "err");
  }
});

// --- Scan Logic ---
async function startScan() {
  if (!currentTorrentId) return;
  isScanning = true;
  maxRisk = 0;
  document.getElementById("btnScan").innerText = "SCAN_IN_PROGRESS...";

  // Build Grid
  gridPlane.innerHTML = "";
  // Cap visual pieces to 400 for DOM performance in this demo
  const displayPieces = Math.min(totalPieces, 400);

  for (let i = 0; i < displayPieces; i++) {
    const d = document.createElement("div");
    d.className = "sector";
    d.id = `sector-${i}`;
    gridPlane.appendChild(d);
  }

  try {
    await fetch(`${API_URL}/api/start-download`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        torrent_id: currentTorrentId,
        num_pieces: 25,
      }),
    });
    log("SCAN_SEQUENCE_INITIATED", "info");
  } catch (e) {
    isScanning = false;
    log("EXECUTION_FAIL", "err");
  }
}

socket.on("piece_downloaded", (data) => {
  // Map actual piece index to our visual grid (modulo if larger)
  const visualIndex = data.piece_index % 400;

  const el = document.getElementById(`sector-${visualIndex}`);

  if (el) {
    if (data.scan_result.verdict === "MALICIOUS") {
      el.className = "sector crit";
      log(`THREAT_DETECT [IDX:${data.piece_index}]`, "err");
    } else if (data.scan_result.verdict === "SUSPICIOUS") {
      el.className = "sector warn";
    } else {
      el.className = "sector clean";
    }
  }

  // Update Gauge & Progress
  const risk = data.scan_result.risk_score;
  maxRisk = Math.max(maxRisk, risk);

  document.getElementById("riskNum").innerText = maxRisk.toFixed(1) + "%";
  document.getElementById("riskFill").style.width = maxRisk + "%";

  // Update MEM (Progress)
  if (data.progress !== undefined) {
    document.getElementById("memVal").innerText = Math.floor(data.progress)
      .toString()
      .padStart(2, "0");
  }

  if (maxRisk > 80) {
    document.getElementById("riskFill").style.backgroundColor =
      "var(--c-accent-crit)";
    document.getElementById("riskFill").style.boxShadow =
      "0 0 15px var(--c-accent-crit)";
  } else if (maxRisk > 40) {
    document.getElementById("riskFill").style.backgroundColor =
      "var(--c-accent-warn)";
    document.getElementById("riskFill").style.boxShadow =
      "0 0 15px var(--c-accent-warn)";
  }
});

socket.on("download_progress", (data) => {
  if (data.progress !== undefined) {
    document.getElementById("memVal").innerText = Math.floor(data.progress)
      .toString()
      .padStart(2, "0");
  }
});

socket.on("download_complete", (data) => {
  isScanning = false;
  document.getElementById("btnScan").innerText = "SCAN_COMPLETE";

  // Reset Engine Status
  document.getElementById("engineText").innerText = "ENGINE_IDLE";
  document.getElementById("engineLight").style.background =
    "var(--c-accent-main)";
  document.getElementById("engineLight").style.boxShadow =
    "0 0 8px var(--c-accent-main)";

  const overlay = document.getElementById("resultOverlay");
  const title = document.getElementById("reportTitle");
  const sub = document.getElementById("reportSub");

  if (data.quarantined) {
    title.innerText = "CONTAINMENT_ACTIVE";
    title.style.color = "var(--c-accent-crit)";

    sub.innerHTML = `Subject contains high-confidence viral signatures.<br>Automated quarantine protocols enforced.<br><br>RISK_FACTOR: <span style="color:var(--c-accent-crit)">${data.max_risk_score.toFixed(1)}%</span>`;
  } else if (data.verdict === "MALICIOUS") {
    title.innerText = "THREAT_IDENTIFIED";
    title.style.color = "var(--c-accent-crit)";
    sub.innerHTML = `Malicious patterns detected. Manual intervention recommended.`;
  } else {
    title.innerText = "SPECIMEN_CLEAN";
    title.style.color = "var(--c-accent-main)";
    sub.innerHTML = `No pathogenic code structures detected.<br>File release authorized.`;
  }

  overlay.classList.add("visible");
});
