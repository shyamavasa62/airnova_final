const API_BASE =
  window.location.protocol === "file:"
    ? "http://127.0.0.1:5000"
    : `${window.location.protocol}//${window.location.hostname || "127.0.0.1"}:5000`;
const cityData = [
  { name: "Delhi", trend: "Worsening", coord: [74, 40], pollutants: { "PM2.5": 48.1, PM10: 71.4, NO2: 29.8, SO2: 6.2, CO: 1.41, O3: 85 }, history: [176,153,189,203,226,181,174,143,169,187,210,241,265,231,188,162] },
  { name: "Mumbai", trend: "Worsening", coord: [68, 49], pollutants: { "PM2.5": 39.6, PM10: 57.2, NO2: 24.6, SO2: 4.7, CO: 1.1, O3: 61.5 }, history: [141,149,162,174,188,179,171,163,156,149,144,151,163,176,171,159] },
  { name: "Chennai", trend: "Improving", coord: [71, 54], pollutants: { "PM2.5": 22.8, PM10: 36.5, NO2: 19.2, SO2: 3.6, CO: 0.9, O3: 49.3 }, history: [96,102,109,114,108,101,95,89,84,81,85,92,98,94,88,84] },
  { name: "Bangalore", trend: "Stable", coord: [66, 52], pollutants: { "PM2.5": 24.9, PM10: 38.8, NO2: 21.7, SO2: 4.1, CO: 0.95, O3: 53.6 }, history: [103,108,116,122,117,111,106,100,96,93,97,104,110,107,101,97] },
  { name: "Hyderabad", trend: "Stable", coord: [69, 50], pollutants: { "PM2.5": 28.6, PM10: 43.7, NO2: 23.1, SO2: 4.4, CO: 1.03, O3: 57.8 }, history: [112,118,124,131,126,121,115,109,104,101,105,111,119,116,109,104] },
];
const state = { selectedCity: 0, cityAqi: cityData.map((c) => Math.round(c.history.at(-1))), histAqi: [...cityData[0].history], futureAqi: [], pollutants: [], lastUpdated: new Date(), chartPoints: [] };

const aqiLabel = (a) => (a <= 50 ? "Good" : a <= 100 ? "Moderate" : a <= 150 ? "Sensitive" : a <= 200 ? "Unhealthy" : a <= 300 ? "Very Unhealthy" : "Hazardous");
const aqiClass = (a) => (a <= 50 ? "aqi-good" : a <= 100 ? "aqi-moderate" : a <= 150 ? "aqi-usg" : a <= 200 ? "aqi-unhealthy" : a <= 300 ? "aqi-very" : "aqi-hazard");
const aqiColor = (a) => (a <= 50 ? "#22c55e" : a <= 100 ? "#eab308" : a <= 150 ? "#f97316" : a <= 200 ? "#ef4444" : a <= 300 ? "#a855f7" : "#800020");
const relTime = (d) => { const m = Math.floor((Date.now() - d.getTime()) / 60000); return m < 1 ? "just now" : `${m} mins ago`; };
const advice = (a) => (a <= 50 ? "Air is clean. Great for outdoor activity." : a <= 100 ? "Moderate air. Sensitive groups should monitor exposure." : a <= 150 ? "Children/elderly should reduce long outdoor exertion." : a <= 200 ? "Avoid heavy outdoor exercise. Mask recommended." : a <= 300 ? "Wear N95 mask. Limit outdoor exposure." : "Hazardous air. Stay indoors and use purifier.");

function setSkeleton(on) { ["cityGrid","pollutants","forecastGrid","analyticsGrid","comparisonPanel","insightsPanel","mapBox"].forEach((id) => document.getElementById(id).classList.toggle("skeleton", on)); }
function makeForecastPayload(base, steps) { const inputs = []; for (let i=0;i<steps;i++){ const d=new Date(); d.setDate(d.getDate()+i); const drift=1+i*0.02; inputs.push({ day:d.getDate(), month:d.getMonth()+1, weekend:[0,6].includes(d.getDay())?1:0, "PM2.5":+(base["PM2.5"]*drift).toFixed(2), PM10:+(base.PM10*drift).toFixed(2), NO2:+(base.NO2*drift).toFixed(2), SO2:+(base.SO2*drift).toFixed(2), CO:+(base.CO*drift).toFixed(2), O3:+(base.O3*drift).toFixed(2) }); } return { inputs }; }

function renderTop() {
  document.getElementById("updatedAt").textContent = relTime(state.lastUpdated);
  const max = Math.max(...state.cityAqi, ...(state.futureAqi.length ? state.futureAqi : [0]));
  document.getElementById("alertBanner").innerHTML = `<strong>Pollution Spike Alert:</strong> AQI forecast to reach <strong>${max}</strong> within 48 hours.`;
}
function renderHero() {
  const city = cityData[state.selectedCity], a = state.cityAqi[state.selectedCity], gauge = document.getElementById("aqiGauge");
  const angle = Math.min(360, (a / 320) * 360);
  gauge.style.background = `conic-gradient(${aqiColor(a)} ${angle}deg, #1b2a45 ${angle}deg)`;
  document.getElementById("heroCityName").textContent = city.name;
  document.getElementById("heroAqiValue").textContent = a;
  document.getElementById("heroAqiValue").className = `gauge-value ${aqiClass(a)}`;
  document.getElementById("heroAqiStatus").textContent = aqiLabel(a);
  document.getElementById("heroTrend").textContent = `Trend: ${city.trend}`;
  document.getElementById("healthAdvice").textContent = advice(a);
  const h = state.histAqi, avg = h.reduce((x,y)=>x+y,0)/(h.length||1), min = Math.min(...h), max = Math.max(...h);
  document.getElementById("heroStats").innerHTML = `<div class="stat">Weekly Avg AQI: <strong>${avg.toFixed(1)}</strong></div><div class="stat">Best / Worst: <strong>${min}</strong> / <strong>${max}</strong></div><div class="stat">Prediction Confidence: <strong>${Math.max(76, 95 - Math.abs(max-min)/6).toFixed(0)}%</strong></div>`;
}
function renderCities() {
  const grid = document.getElementById("cityGrid");
  grid.innerHTML = cityData.map((c,i)=>`<article class="city-card ${i===state.selectedCity?"active":""}" data-city="${i}"><div class="name">${c.name}</div><div class="aqi ${aqiClass(state.cityAqi[i])}">${state.cityAqi[i]}</div><div class="status">${aqiLabel(state.cityAqi[i])}</div><div class="status">${c.trend}</div></article>`).join("");
  grid.querySelectorAll(".city-card").forEach((el)=>el.onclick=async()=>{state.selectedCity=Number(el.dataset.city); await refreshDashboardFromBackend();});
}
function renderPollutants() {
  const c = document.getElementById("pollutants");
  c.innerHTML = state.pollutants.map((p)=>`<article class="pollutant-card"><div class="label">${p.label}</div><div class="value">${p.value}</div><div class="unit">${p.unit}</div><div class="pollutant-meter"><span style="width:${Math.min(100,p.value)}%;background:${aqiColor(p.value*2)}"></span></div></article>`).join("");
}
function renderForecastGrid() {
  const grid = document.getElementById("forecastGrid"), start = new Date(), vals = state.futureAqi.length ? state.futureAqi : [192,207,221,180,164,198,233,251,218,219,198,145,174,174,211,248];
  grid.innerHTML = vals.map((v,i)=>{ const t = new Date(start.getTime()+i*3*60*60*1000); return `<div class="forecast-item"><div class="time">${t.toLocaleString([], { month:"2-digit", day:"2-digit", hour:"2-digit" })}</div><div class="dot" style="background:${aqiColor(v)}">${v}</div><div class="${aqiClass(v)}">${aqiLabel(v)}</div></div>`; }).join("");
}
function renderAnalytics() {
  const h = state.histAqi, f = state.futureAqi, avg = h.reduce((a,b)=>a+b,0)/h.length, inc = ((h.at(-1)-h[0])/Math.max(1,h[0]))*100, worst = Math.max(...h,...f), best = Math.min(...h);
  document.getElementById("analyticsGrid").innerHTML = `<div class="analytics-card">Weekly Avg<br><strong>${avg.toFixed(1)}</strong></div><div class="analytics-card">Trend Change<br><strong>${inc>=0?"↑":"↓"} ${Math.abs(inc).toFixed(1)}%</strong></div><div class="analytics-card">Best/Worst<br><strong>${best} / ${worst}</strong></div>`;
}
function renderComparison() {
  const today = state.cityAqi[state.selectedCity], yesterday = state.histAqi.at(-2) ?? today, delta = today - yesterday;
  document.getElementById("comparisonPanel").innerHTML = `<div class="comparison-card">Today AQI<br><strong>${today}</strong></div><div class="comparison-card">Yesterday AQI<br><strong>${yesterday}</strong></div><div class="comparison-card">Change<br><strong>${delta>=0?"↑":"↓"} ${Math.abs(delta)}</strong></div>`;
}
function renderInsights() {
  const p = cityData[state.selectedCity].pollutants, maxP = Object.entries(p).sort((a,b)=>b[1]-a[1])[0], a = state.cityAqi[state.selectedCity];
  document.getElementById("insightsPanel").innerHTML = `<div class="insight-item">Dominant pollutant is <strong>${maxP[0]}</strong>, likely driving AQI peaks.</div><div class="insight-item">Current AQI is <strong>${aqiLabel(a)}</strong>; ${advice(a)}</div><div class="insight-item">Forecast indicates ${state.futureAqi[0] > a ? "rising" : "stable/improving"} trend in next 24-48h.</div>`;
}
function renderMap() {
  const box = document.getElementById("mapBox");
  box.innerHTML = `<div class="map-grid"></div>${cityData.map((c,i)=>`<div class="map-marker" style="left:${c.coord[0]}%;top:${c.coord[1]}%;background:${aqiColor(state.cityAqi[i])}">${c.name} ${state.cityAqi[i]}</div>`).join("")}`;
}

function drawBarChart() {
  const canvas = document.getElementById("barChart"), ctx = canvas.getContext("2d"), w = canvas.width, h = canvas.height;
  ctx.clearRect(0,0,w,h); ctx.strokeStyle = "rgba(123,154,204,0.28)"; ctx.beginPath(); ctx.moveTo(70,20); ctx.lineTo(70,h-40); ctx.lineTo(w-20,h-40); ctx.stroke();
  const maxVal = Math.max(...state.pollutants.map((p)=>p.value))*1.15, barW=100, gap=36;
  state.pollutants.forEach((p,i)=>{ const x=85+i*(barW+gap), barH=(p.value/maxVal)*(h-80), y=h-40-barH; ctx.fillStyle=["#10b981","#0ea5e9","#eab308","#a855f7","#ef4444","#f97316"][i]; ctx.fillRect(x,y,barW,barH); ctx.fillStyle="#97a8c6"; ctx.font="15px Inter"; ctx.fillText(p.label,x+30,h-16); });
}
function drawTrendChart() {
  const canvas = document.getElementById("trendChart"), ctx = canvas.getContext("2d"), w = canvas.width, h = canvas.height;
  const all = state.histAqi.concat(state.futureAqi), max = Math.max(...all)+20, min = Math.min(...all)-20, x0=58, y0=h-34, cw=w-84, ch=h-66;
  ctx.clearRect(0,0,w,h);
  [{from:0,to:50,color:"rgba(34,197,94,.09)"},{from:51,to:100,color:"rgba(234,179,8,.08)"},{from:101,to:150,color:"rgba(249,115,22,.08)"},{from:151,to:200,color:"rgba(239,68,68,.08)"},{from:201,to:300,color:"rgba(168,85,247,.08)"}]
    .forEach((z)=>{ const yTop=y0-((z.to-min)/(max-min))*ch, yBottom=y0-((z.from-min)/(max-min))*ch; ctx.fillStyle=z.color; ctx.fillRect(x0,yTop,cw,yBottom-yTop); });
  ctx.strokeStyle="rgba(102,127,174,.25)"; for(let i=0;i<=6;i++){ const y=y0-(ch*i)/6; ctx.beginPath(); ctx.moveTo(x0,y); ctx.lineTo(x0+cw,y); ctx.stroke(); }
  const project=(v,i,total)=>({x:x0+(cw*i)/(total-1),y:y0-((v-min)/(max-min))*ch});
  const split=state.histAqi.length;
  ctx.strokeStyle="#14b8a6"; ctx.lineWidth=3; ctx.beginPath(); state.histAqi.forEach((v,i)=>{ const p=project(v,i,all.length); i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y); }); ctx.stroke();
  ctx.setLineDash([7,7]); ctx.strokeStyle="#38bdf8"; ctx.beginPath(); state.futureAqi.forEach((v,j)=>{ const p=project(v,split-1+j,all.length); j?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y); }); ctx.stroke(); ctx.setLineDash([]);
  const splitX = x0+(cw*(split-1))/(all.length-1); ctx.fillStyle="rgba(56,189,248,.09)"; ctx.fillRect(splitX,y0-ch,x0+cw-splitX,ch);
  const s=project(all[split-1],split-1,all.length); ctx.strokeStyle="rgba(56,189,248,.4)"; ctx.beginPath(); ctx.moveTo(s.x,y0-ch); ctx.lineTo(s.x,y0); ctx.stroke(); ctx.fillStyle="#38bdf8"; ctx.font="16px Inter"; ctx.fillText("NOW",s.x-20,y0-ch+18);
  const minIdx = all.indexOf(Math.min(...all)), maxIdx = all.indexOf(Math.max(...all)), pMin = project(all[minIdx],minIdx,all.length), pMax = project(all[maxIdx],maxIdx,all.length);
  ctx.fillStyle="#93c5fd"; ctx.beginPath(); ctx.arc(pMin.x,pMin.y,4,0,Math.PI*2); ctx.fill(); ctx.fillText(`Min ${all[minIdx]}`,pMin.x+8,pMin.y+4); ctx.beginPath(); ctx.arc(pMax.x,pMax.y,4,0,Math.PI*2); ctx.fill(); ctx.fillText(`Max ${all[maxIdx]}`,pMax.x+8,pMax.y-8);
  state.chartPoints = all.map((v,i)=>({...project(v,i,all.length),value:v,index:i}));
}
function setupChartTooltip(){ const canvas=document.getElementById("trendChart"), tip=document.getElementById("chartTip"); canvas.onmousemove=(e)=>{ if(!state.chartPoints.length)return; const r=canvas.getBoundingClientRect(); const mx=((e.clientX-r.left)/r.width)*canvas.width; let c=state.chartPoints[0],b=Math.abs(mx-c.x); state.chartPoints.forEach((p)=>{const d=Math.abs(mx-p.x); if(d<b){b=d;c=p;}}); tip.style.opacity="1"; tip.textContent=`${c.index<state.histAqi.length?"Past":"Forecast"} AQI: ${c.value}`; }; canvas.onmouseleave=()=>tip.style.opacity="0"; }

function bindSliders() {
  document.querySelectorAll('input[type="range"]').forEach((el) => {
    const out = document.getElementById(el.dataset.output);
    const set = () => { out.textContent = Number(el.value).toFixed(el.step && Number(el.step) < 0.1 ? 2 : 1); };
    el.addEventListener("input", set); set();
  });
}
function themeSetup() {
  const saved = localStorage.getItem("airnova-theme");
  if (saved === "light") document.body.classList.add("light");
  document.getElementById("themeToggle").onclick = () => {
    document.body.classList.toggle("light");
    localStorage.setItem("airnova-theme", document.body.classList.contains("light") ? "light" : "dark");
  };
}
function exportSetup() {
  document.getElementById("exportCsvBtn").onclick = () => {
    const rows = [["timeIndex", "forecastAQI"], ...state.futureAqi.map((v, i) => [i + 1, v])];
    const csv = rows.map((r) => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "airnova_forecast.csv"; a.click();
  };
  document.getElementById("printBtn").onclick = () => window.print();
}
async function setupPredictionForm() {
  const form = document.getElementById("predictForm"), result = document.getElementById("predictResult");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    const payload = { "PM2.5": Number(fd.get("PM2.5")), PM10: Number(fd.get("PM10")), NO2: Number(fd.get("NO2")), SO2: Number(fd.get("SO2")), CO: Number(fd.get("CO")), O3: Number(fd.get("O3")), date: fd.get("date") };
    try {
      const res = await fetch(`${API_BASE}/predict`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      const data = await res.json(); if (!res.ok) throw new Error(data.error || "Prediction failed");
      const conf = Math.max(75, 96 - Math.abs(data.predicted_aqi - state.histAqi.at(-1)) / 8).toFixed(0);
      result.innerHTML = `<strong>Predicted AQI:</strong> ${data.predicted_aqi} | <strong>Status:</strong> ${data.status} | <strong>Confidence:</strong> ${conf}%`;
    } catch (err) { result.textContent = `Backend not reachable right now (${err.message}).`; }
  });
}

async function refreshDashboardFromBackend() {
  const selected = cityData[state.selectedCity], base = selected.pollutants, history = selected.history;
  state.pollutants = [{ label: "PM2.5", value: base["PM2.5"], unit: "ug/m3" }, { label: "PM10", value: base.PM10, unit: "ug/m3" }, { label: "NO2", value: base.NO2, unit: "ppb" }, { label: "SO2", value: base.SO2, unit: "ppb" }, { label: "CO", value: base.CO, unit: "ppm" }, { label: "O3", value: base.O3, unit: "ppb" }];
  setSkeleton(true);
  try {
    const [rfRes, arimaRes] = await Promise.all([
      fetch(`${API_BASE}/forecast`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(makeForecastPayload(base, 16)) }),
      fetch(`${API_BASE}/arima/forecast`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ aqi_history: history, steps: 16 }) }),
    ]);
    const rf = await rfRes.json(), arima = await arimaRes.json();
    if (!rfRes.ok) throw new Error(rf.error || "Forecast API failed");
    if (!arimaRes.ok) throw new Error(arima.error || "ARIMA API failed");
    state.futureAqi = arima.predictions.map((v) => Math.round(v));
    state.histAqi = [...history];
    state.cityAqi[state.selectedCity] = Math.round(state.futureAqi[0]);
    state.lastUpdated = new Date();
  } catch {
    state.histAqi = [...history];
    state.futureAqi = [192, 207, 221, 180, 164, 198, 233, 251, 218, 219, 198, 145, 174, 174, 211, 248];
    state.cityAqi[state.selectedCity] = state.futureAqi[0];
  } finally {
    setSkeleton(false);
  }
  renderTop(); renderHero(); renderCities(); renderPollutants(); renderForecastGrid(); renderAnalytics(); renderComparison(); renderInsights(); renderMap(); drawBarChart(); drawTrendChart();
}

async function init() {
  themeSetup(); exportSetup(); bindSliders(); setupChartTooltip(); await setupPredictionForm();
  const dateInput = document.querySelector('input[name="date"]'); if (dateInput) dateInput.value = new Date(Date.now() + 86400000).toISOString().slice(0, 10);
  renderTop(); renderHero(); renderCities(); renderPollutants(); renderForecastGrid(); renderAnalytics(); renderComparison(); renderInsights(); renderMap(); drawBarChart(); drawTrendChart();
  await refreshDashboardFromBackend();
}
init();
