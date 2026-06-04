let API = null;

function updateUserDataBadge(source, offline = false) {
  const badge = document.getElementById("userDataBadge");
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

function aqiLabel(a) {
  if (a <= 50) return "Good";
  if (a <= 100) return "Moderate";
  if (a <= 150) return "Sensitive";
  if (a <= 200) return "Unhealthy";
  if (a <= 300) return "Very Unhealthy";
  return "Hazardous";
}
function aqiColor(a) {
  if (a <= 50) return "#22c55e";
  if (a <= 100) return "#eab308";
  if (a <= 150) return "#f97316";
  if (a <= 200) return "#ef4444";
  if (a <= 300) return "#a855f7";
  return "#800020";
}
function recommendationList(a) {
  if (a <= 50) return ["Safe for jogging", "Windows can remain open", "Minimal respiratory risk"];
  if (a <= 100) return ["Okay for normal outdoor activity", "Sensitive groups limit long exposure", "Hydrate and monitor symptoms"];
  if (a <= 150) return ["Reduce prolonged outdoor exposure", "Children and elderly stay cautious", "Carry a light mask outdoors"];
  if (a <= 200) return ["Avoid strenuous outdoor workouts", "Wear N95 mask in traffic zones", "Keep indoor air circulation filtered"];
  if (a <= 300) return ["Avoid prolonged outdoor exposure", "Wear N95 masks", "Sensitive groups stay indoors"];
  return ["Stay indoors as much as possible", "Use purifier if available", "Avoid all outdoor physical activity"];
}

function drawForecastChart(points) {
  const canvas = document.getElementById("forecastChart");
  const ctx = canvas.getContext("2d");
  const tip = document.getElementById("forecastTooltip");
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  if (!points?.length) {
    ctx.fillStyle = "#9fb0d5";
    ctx.font = "16px Inter";
    ctx.fillText("No forecast points available.", 20, 36);
    return;
  }

  const values = points.map((p) => Number(p.predicted_aqi));
  const max = Math.max(...values) + 15;
  const min = Math.max(0, Math.min(...values) - 15);
  const left = 56;
  const right = w - 20;
  const top = 22;
  const bottom = h - 38;
  const plotW = right - left;
  const plotH = bottom - top;

  ctx.strokeStyle = "rgba(102,127,174,0.22)";
  for (let i = 0; i <= 5; i++) {
    const y = top + (plotH * i) / 5;
    ctx.beginPath();
    ctx.moveTo(left, y);
    ctx.lineTo(right, y);
    ctx.stroke();
    const yVal = (max - ((max - min) * i) / 5).toFixed(0);
    ctx.fillStyle = "#8fa4c7";
    ctx.font = "11px Inter";
    ctx.fillText(yVal, 20, y + 4);
  }

  const mapX = (i) => left + (plotW * i) / Math.max(1, points.length - 1);
  const mapY = (v) => bottom - ((v - min) / Math.max(1, max - min)) * plotH;

  ctx.strokeStyle = "#22d3ee";
  ctx.lineWidth = 3;
  ctx.beginPath();
  values.forEach((v, i) => {
    const x = mapX(i);
    const y = mapY(v);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  values.forEach((v, i) => {
    const x = mapX(i);
    const y = mapY(v);
    ctx.fillStyle = aqiColor(v);
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.fill();
  });

  ctx.fillStyle = "#9fb0d5";
  ctx.font = "12px Inter";
  points.forEach((p, i) => {
    if (i % 2 !== 0 && i !== points.length - 1) return;
    const x = mapX(i);
    ctx.fillText(`+${p.horizon_hour}h`, x - 14, h - 16);
  });

  const chartPoints = points.map((p, i) => ({
    x: mapX(i),
    y: mapY(values[i]),
    value: values[i],
    hour: p.horizon_hour,
    status: p.status,
  }));
  canvas.onmousemove = (e) => {
    const rect = canvas.getBoundingClientRect();
    const mx = ((e.clientX - rect.left) / rect.width) * canvas.width;
    const my = ((e.clientY - rect.top) / rect.height) * canvas.height;
    let found = null;
    for (const pt of chartPoints) {
      const d = Math.hypot(pt.x - mx, pt.y - my);
      if (d < 12) {
        found = pt;
        break;
      }
    }
    if (!found) {
      tip.style.opacity = "0";
      return;
    }
    tip.style.opacity = "1";
    tip.style.left = `${Math.max(8, Math.min(rect.width - 160, e.clientX - rect.left + 10))}px`;
    tip.style.top = `${Math.max(8, e.clientY - rect.top - 36)}px`;
    tip.textContent = `+${found.hour}h: ${found.value.toFixed(2)} (${found.status})`;
  };
  canvas.onmouseleave = () => {
    tip.style.opacity = "0";
  };
}

async function load48HourForecast(city) {
  const base = await resolveApiBase();
  const res = await fetch(`${base}/realtime/forecast?city=${encodeURIComponent(city)}`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Failed to load 48-hour forecast");
  drawForecastChart(data.points || []);
  renderForecastCards(data.points || []);
  document.getElementById("forecastMeta").textContent = `Forecast generated at ${new Date(
    data.generated_at
  ).toLocaleString()} (${data.interval_hours}h interval)`;
}

function renderForecastCards(points) {
  const box = document.getElementById("forecastMiniCards");
  if (!points.length) {
    box.innerHTML = "";
    return;
  }
  box.innerHTML = points
    .slice(0, 8)
    .map(
      (p) => `<article class="forecast-mini">
        <div class="t">+${p.horizon_hour}h</div>
        <div class="v" style="color:${aqiColor(Number(p.predicted_aqi))}">${Number(p.predicted_aqi).toFixed(2)}</div>
      </article>`
    )
    .join("");
}

async function loadCities() {
  const base = await resolveApiBase();
  const sel = document.getElementById("citySelect");
  const res = await fetch(`${base}/realtime/cities`);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Failed to load cities");
  sel.innerHTML = data.cities.map((c) => `<option value="${c}">${c}</option>`).join("");
  if (!data.cities.length) throw new Error("No cities found in dataset");
  sel.value = data.cities[0];
}

function renderRecord(rec) {
  updateUserDataBadge(rec.data_source || "historical_dataset");
  document.getElementById("cityName").textContent = rec.city;
  document.getElementById("aqiVal").textContent = Number(rec.actual_aqi).toFixed(2);
  document.getElementById("aqiStatus").textContent = aqiLabel(rec.actual_aqi);
  document.getElementById("aqiDate").textContent = `Date: ${rec.date}`;
  document.getElementById("healthIcon").textContent = rec.health_indicator || "😷";
  document.getElementById("aqiTrend").textContent = `AQI ${rec.trend?.delta_aqi < 0 ? "↓" : rec.trend?.delta_aqi > 0 ? "↑" : "→"} ${Math.abs(
    Number(rec.trend?.delta_pct || 0)
  ).toFixed(2)}% from yesterday • ${rec.trend?.label || "Stable"}`;

  const angle = Math.min(360, (rec.actual_aqi / 320) * 360);
  const gauge = document.getElementById("aqiGauge");
  gauge.style.background = `conic-gradient(${aqiColor(rec.actual_aqi)} ${angle}deg, #1b2a45 ${angle}deg)`;
  gauge.style.boxShadow = `0 0 45px ${aqiColor(rec.actual_aqi)}55`;

  const p = rec.pollutants;
  document.getElementById("pollutants").innerHTML = Object.entries(p)
    .map(([k, v]) => {
      const value = Number(v);
      const icon = k === "PM2.5" ? "🌫️" : k === "PM10" ? "🏭" : k === "NO2" ? "🚗" : k === "SO2" ? "🔥" : k === "CO" ? "🧪" : "☀️";
      const safe = value < (k === "CO" ? 1.2 : 60);
      const status = safe ? "Safe" : "Watch";
      const pct = Math.max(5, Math.min(100, value));
      return `<article class="pollutant-card compact">
        <div class="label">${icon} ${k}</div>
        <div class="value">${value.toFixed(2)}</div>
        <div class="unit">${k === "CO" ? "ppm" : "ug/m3"}</div>
        <div class="pollutant-badge ${safe ? "ok" : "warn"}">${status}</div>
        <div class="pollutant-meter"><span style="width:${pct}%;background:${aqiColor(value * 2)}"></span></div>
      </article>`;
    })
    .join("");

  const recItems = recommendationList(rec.actual_aqi);
  document.getElementById("recList").innerHTML = recItems.map((x) => `<li>${x}</li>`).join("");

  document.getElementById("predStats").innerHTML = `
    <div class="stat">RF Next AQI: <strong>${rec.predictions.rf_next_aqi != null ? Number(rec.predictions.rf_next_aqi).toFixed(2) : "n/a"}</strong></div>
    <div class="stat">ARIMA Next AQI: <strong>${rec.predictions.arima_next_aqi != null ? Number(rec.predictions.arima_next_aqi).toFixed(2) : "n/a"}</strong></div>
    <div class="stat">Data Source: <strong>${rec.data_source || "historical_dataset"}</strong></div>
  `;

  const w = rec.weather || {};
  document.getElementById("weatherStats").innerHTML = `
    <div class="stat">Temperature: <strong>${w.temperature_c != null ? Number(w.temperature_c).toFixed(2) : "--"}°C</strong></div>
    <div class="stat">Humidity: <strong>${w.humidity_pct != null ? Number(w.humidity_pct).toFixed(2) : "--"}%</strong></div>
    <div class="stat">Wind: <strong>${w.wind_speed_kmh != null ? Number(w.wind_speed_kmh).toFixed(2) : "--"} km/h</strong></div>
  `;
  document.getElementById("liveUpdated").textContent = `Live Updated ${relativeTime(rec.last_updated)}`;
}

function relativeTime(ts) {
  if (!ts) return "--";
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return "--";
  const mins = Math.max(0, Math.round((Date.now() - d.getTime()) / 60000));
  if (mins < 1) return "just now";
  if (mins === 1) return "1 min ago";
  return `${mins} mins ago`;
}

async function loadComparison() {
  const base = await resolveApiBase();
  const res = await fetch(`${base}/realtime/comparison`);
  const data = await res.json();
  if (!res.ok) return;
  const el = document.getElementById("cityComparison");
  el.innerHTML = (data.cities || [])
    .slice(0, 5)
    .map(
      (c) => `<article class="comparison-card">
        <div>${c.city}</div>
        <div class="aqi ${Number(c.aqi) <= 100 ? "aqi-good" : Number(c.aqi) <= 200 ? "aqi-unhealthy" : "aqi-hazard"}">${Number(c.aqi).toFixed(2)}</div>
        <div>${c.status}</div>
      </article>`
    )
    .join("");
}

async function refresh() {
  const base = await resolveApiBase();
  const city = document.getElementById("citySelect").value;
  const res = await fetch(`${base}/realtime/current?city=${encodeURIComponent(city)}`);
  const rec = await res.json();
  if (!res.ok) throw new Error(rec.error || "Failed to load current record");
  renderRecord(rec);
  await load48HourForecast(city);
  await loadComparison();
}

async function init() {
  await loadCities();
  document.getElementById("citySelect").addEventListener("change", refresh);
  await refresh();
  setInterval(refresh, 10000);
}

init().catch((e) => {
  updateUserDataBadge("", true);
  document.body.insertAdjacentHTML("beforeend", `<div class="card">Error: ${e.message}</div>`);
});
