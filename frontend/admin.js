let API = null;

function updateAdminDataBadge(source, offline = false) {
  const badge = document.getElementById("adminDataBadge");
  if (!badge) return;
  if (offline) {
    badge.className = "status-badge offline";
    badge.textContent = "Backend Offline";
    return;
  }
  if (source === "live_api") {
    badge.className = "status-badge live";
    badge.textContent = "Live Feed Active";
    return;
  }
  badge.className = "status-badge fallback";
  badge.textContent = "Fallback Data";
}

async function resolveApiBase() {
  if (API) return API;
  const proto = window.location.protocol === "file:" ? "http:" : window.location.protocol;
  const host = window.location.hostname || "127.0.0.1";
  const candidates = [
    `${proto}//${host}:5000`,
    `${proto}//${host}:5001`,
    "http://127.0.0.1:5000",
    "http://127.0.0.1:5001",
    "http://localhost:5000",
    "http://localhost:5001",
  ];
  for (const base of candidates) {
    try {
      const res = await fetch(`${base}/health`);
      if (!res.ok) continue;
      const data = await res.json();
      if (data?.status === "ok") {
        API = base;
        return API;
      }
    } catch (_) {}
  }
  throw new Error("AIRNOVA backend not reachable. Start backend and retry.");
}

async function fetchCities() {
  const base = await resolveApiBase();
  const res = await fetch(`${base}/realtime/cities`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Failed to load cities");
  const sel = document.getElementById("adminCity");
  sel.innerHTML = data.cities.map((c) => `<option value="${c}">${c}</option>`).join("");
  if (!data.cities.length) throw new Error("No cities found in dataset");
  sel.value = data.cities[0];
}

function setStatus(msg) {
  document.getElementById("adminStatus").textContent = msg;
  appendAdminLog(msg);
}

function appendAdminLog(msg) {
  const box = document.getElementById("adminLogs");
  if (!box) return;
  const line = `[${new Date().toLocaleTimeString()}] ${msg}`;
  const prev = box.textContent === "No admin actions yet." ? "" : box.textContent;
  box.textContent = [line, prev].filter(Boolean).join("\n");
}

function renderModelMetrics(statusObj) {
  const cards = document.getElementById("modelMetricsCards");
  const updated = document.getElementById("modelMetricsUpdated");
  if (!cards || !updated) return;

  const last = statusObj?.last_result;
  const err = statusObj?.last_error;
  const running = Boolean(statusObj?.running);

  if (running) {
    updated.textContent = "Retrain running…";
    return;
  }

  if (err) {
    updated.textContent = `Last retrain failed: ${err}`;
    return;
  }

  if (!last) {
    updated.textContent = "No retrain run yet.";
    return;
  }

  const rf = last.random_forest || {};
  const rfM = rf.metrics || {};
  const ar = last.arima || {};

  const fmt = (v, digits = 3) => (typeof v === "number" && Number.isFinite(v) ? v.toFixed(digits) : "--");
  const fmtInt = (v) => (typeof v === "number" && Number.isFinite(v) ? String(Math.round(v)) : "--");

  const arOrder = ar.order ? JSON.stringify(ar.order) : "--";
  const arMae = typeof ar.valid_mae === "number" ? fmt(ar.valid_mae, 3) : "--";

  cards.innerHTML = `
    <div class="analytics-card">RandomForest MAE<br /><strong>${fmt(rfM.mae, 3)}</strong></div>
    <div class="analytics-card">RandomForest RMSE<br /><strong>${fmt(rfM.rmse, 3)}</strong></div>
    <div class="analytics-card">RandomForest R²<br /><strong>${fmt(rfM.r2, 3)}</strong></div>
    <div class="analytics-card">ARIMA Order<br /><strong>${arOrder}</strong></div>
    <div class="analytics-card">ARIMA Valid MAE<br /><strong>${arMae}</strong></div>
    <div class="analytics-card">Trained On Rows<br /><strong>${fmtInt(rf.n_rows)}</strong></div>
  `;
  updated.textContent = `Last updated: ${new Date().toLocaleString()}`;
}

function renderRecord(obj) {
  updateAdminDataBadge(obj.data_source || "historical_dataset");
  const cards = document.getElementById("adminSnapshotCards");
  cards.innerHTML = `
    <div class="analytics-card">AQI<br /><strong>${Number(obj.actual_aqi).toFixed(2)}</strong></div>
    <div class="analytics-card">Status<br /><strong>${aqiLabel(obj.actual_aqi)}</strong></div>
    <div class="analytics-card">Source<br /><strong>${obj.data_source || "historical_dataset"}</strong></div>
  `;
}

function aqiLabel(a) {
  if (a <= 50) return "Good";
  if (a <= 100) return "Moderate";
  if (a <= 150) return "Sensitive";
  if (a <= 200) return "Unhealthy";
  if (a <= 300) return "Very Unhealthy";
  return "Hazardous";
}

function renderForecast(points) {
  const rows = document.getElementById("forecastRows");
  if (!points?.length) {
    rows.innerHTML = `<tr><td colspan="4" style="padding: 8px;">No forecast points available.</td></tr>`;
    return;
  }

  rows.innerHTML = points
    .map(
      (p) => `
      <tr style="border-top: 1px solid rgba(138,149,173,0.25);">
        <td style="padding: 8px;">+${p.horizon_hour}h</td>
        <td style="padding: 8px;">${new Date(p.timestamp).toLocaleString()}</td>
        <td style="padding: 8px;">${Number(p.predicted_aqi).toFixed(2)}</td>
        <td style="padding: 8px;">${p.status}</td>
      </tr>
    `
    )
    .join("");
}

async function loadForecast() {
  const base = await resolveApiBase();
  const city = document.getElementById("adminCity").value;
  const res = await fetch(`${base}/realtime/forecast?city=${encodeURIComponent(city)}`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Failed to load forecast");
  renderForecast(data.points || []);
}

async function loadCurrent() {
  const base = await resolveApiBase();
  const city = document.getElementById("adminCity").value;
  const res = await fetch(`${base}/realtime/current?city=${encodeURIComponent(city)}`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Failed");
  renderRecord(data);
  await loadForecast();
  setStatus(`Current loaded for ${city}`);
}

async function nextStep() {
  const base = await resolveApiBase();
  const city = document.getElementById("adminCity").value;
  const res = await fetch(`${base}/realtime/next`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ city }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Failed");
  renderRecord(data);
  await loadForecast();
  setStatus(`Stepped to next record for ${city}`);
}

async function loadModelMetrics() {
  const base = await resolveApiBase();
  try {
    const sres = await fetch(`${base}/admin/retrain/status`);
    const sdata = await sres.json();
    if (sres.ok) renderModelMetrics(sdata);
  } catch (_) {
    // Leave metrics placeholders as-is if backend isn't reachable.
  }
}

async function init() {
  await fetchCities();
  document.getElementById("btnCurrent").onclick = () => loadCurrent().catch((e) => setStatus(e.message));
  document.getElementById("btnNext").onclick = () => nextStep().catch((e) => setStatus(e.message));
  document.getElementById("adminCity").addEventListener("change", () => {
    loadCurrent().catch((e) => setStatus(e.message));
  });
  const csvInput = document.getElementById("csvInput");
  if (csvInput) {
    csvInput.addEventListener("change", (e) => {
      const file = e.target.files?.[0];
      if (file) appendAdminLog(`CSV selected: ${file.name} (${file.size} bytes)`);
    });
  }
  const btnSimTrain = document.getElementById("btnSimTrain");
  if (btnSimTrain) {
    btnSimTrain.onclick = () => {
      runRetrain().catch((e) => setStatus(e.message));
    };
  }
  await loadModelMetrics();
  await loadCurrent();
}

async function uploadCsv(mode = "replace") {
  const base = await resolveApiBase();
  const csvInput = document.getElementById("csvInput");
  const file = csvInput?.files?.[0];
  if (!file) throw new Error("Please choose a CSV file first.");

  setStatus("Uploading dataset...");
  const form = new FormData();
  form.append("file", file);
  form.append("mode", mode);

  const res = await fetch(`${base}/admin/ingest`, { method: "POST", body: form });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Upload failed");

  appendAdminLog(`Ingested: inserted=${data.inserted} db_rows=${data.db_rows} mode=${data.mode}`);
  setStatus("Dataset uploaded. Reloading cities...");
  await fetchCities();
  await loadCurrent();
  setStatus("Dataset active.");
}

async function runRetrain() {
  const base = await resolveApiBase();
  appendAdminLog("Retrain requested...");
  setStatus("Starting retrain...");

  const res = await fetch(`${base}/admin/retrain`, { method: "POST" });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Failed to start retrain");

  appendAdminLog(`Retrain status: ${data.status}`);
  if (data.status === "running") {
    setStatus("Retrain already running.");
    return;
  }

  // Poll status for a short time.
  for (let i = 0; i < 30; i++) {
    await new Promise((r) => setTimeout(r, 1000));
    const sres = await fetch(`${base}/admin/retrain/status`);
    const sdata = await sres.json();
    if (!sres.ok) throw new Error(sdata.error || "Failed to fetch retrain status");
    if (!sdata.running) {
      if (sdata.last_error) {
        appendAdminLog(`Retrain failed: ${sdata.last_error}`);
        renderModelMetrics(sdata);
        setStatus("Retrain failed.");
      } else {
        appendAdminLog(`Retrain complete: ${JSON.stringify(sdata.last_result, null, 2)}`);
        renderModelMetrics(sdata);
        setStatus("Retrain completed.");
      }
      return;
    }
  }

  setStatus("Retrain still running. Check logs or try again later.");
}

init().catch((e) => {
  updateAdminDataBadge("", true);
  setStatus(e.message);
});
