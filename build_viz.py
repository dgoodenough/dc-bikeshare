"""
Build the bikeshare map visualization.
Reads map_data.json and produces bikeshare_map.html with the data embedded.

Usage (in notebook or terminal):
    %run build_viz.py
    # or: python build_viz.py
"""

import json
from pathlib import Path

DATA_PATH = "map_data.json"
OUT_PATH = "bikeshare_map.html"

print("Reading map data...")
with open(DATA_PATH) as f:
    json_data = f.read().strip()

# Validate it parses
d = json.loads(json_data)
print(f"  Stations: {len(d['stations'])}, Dockless cells: {len(d['dockless'])}, Months: {len(d['months'])}")

HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Capital Bikeshare — Station Usage Map</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; background: #1a1a2e; color: #e0e0e0; }
  #map { width: 100%; height: calc(100vh - 120px); }
  .controls {
    height: 120px; background: #16213e; padding: 12px 24px;
    display: flex; flex-direction: column; justify-content: center; gap: 8px;
    border-top: 1px solid #0f3460;
  }
  .controls-top {
    display: flex; align-items: center; justify-content: space-between; gap: 16px;
  }
  .month-label {
    font-size: 28px; font-weight: 700; color: #e94560;
    min-width: 140px; text-align: center; font-variant-numeric: tabular-nums;
  }
  .stats {
    display: flex; gap: 24px; font-size: 13px; color: #a0a0b8;
  }
  .stats span { font-weight: 600; }
  .stat-electric { color: #00d4aa; }
  .stat-classic { color: #4a9eff; }
  .stat-dockless { color: #ff9f43; }
  .stat-total { color: #e0e0e0; }
  .slider-row {
    display: flex; align-items: center; gap: 12px;
  }
  input[type=range] {
    flex: 1; height: 6px; -webkit-appearance: none; appearance: none;
    background: #0f3460; border-radius: 3px; outline: none;
  }
  input[type=range]::-webkit-slider-thumb {
    -webkit-appearance: none; width: 18px; height: 18px;
    background: #e94560; border-radius: 50%; cursor: pointer;
    border: 2px solid #fff;
  }
  input[type=range]::-moz-range-thumb {
    width: 18px; height: 18px; background: #e94560;
    border-radius: 50%; cursor: pointer; border: 2px solid #fff;
  }
  .btn {
    background: #0f3460; border: 1px solid #1a4080; color: #e0e0e0;
    padding: 6px 14px; border-radius: 4px; cursor: pointer; font-size: 13px;
    white-space: nowrap;
  }
  .btn:hover { background: #1a4080; }
  .btn.active { background: #e94560; border-color: #e94560; }

  .legend {
    background: rgba(22, 33, 62, 0.92); padding: 10px 14px; border-radius: 8px;
    font-size: 12px; line-height: 1.8; border: 1px solid #0f3460;
    box-shadow: 0 2px 8px rgba(0,0,0,0.4);
  }
  .legend-item { display: flex; align-items: center; gap: 8px; }
  .legend-swatch {
    width: 14px; height: 14px; border-radius: 50%; flex-shrink: 0;
  }

  .station-tooltip {
    background: rgba(22, 33, 62, 0.95) !important;
    border: 1px solid #0f3460 !important;
    color: #e0e0e0 !important;
    border-radius: 6px !important;
    padding: 8px 12px !important;
    font-size: 13px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.5) !important;
  }
  .station-tooltip .tip-name { font-weight: 700; margin-bottom: 4px; font-size: 14px; }
  .station-tooltip .tip-row { display: flex; justify-content: space-between; gap: 16px; }
  .station-tooltip .tip-electric { color: #00d4aa; }
  .station-tooltip .tip-classic { color: #4a9eff; }
  .leaflet-popup-tip { display: none !important; }

  .chart-panel {
    position: fixed; left: 16px; bottom: 136px; z-index: 1000;
    width: min(560px, calc(100vw - 32px));
    background: rgba(22, 33, 62, 0.97); border: 1px solid #0f3460; border-radius: 8px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.5); padding: 12px 14px 10px;
    display: none;
  }
  .chart-panel.open { display: block; }
  .chart-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
  .chart-title { font-size: 15px; font-weight: 700; }
  .chart-sub { font-size: 12px; color: #a0a0b8; margin-top: 2px; }
  .chart-close {
    background: none; border: none; color: #a0a0b8; font-size: 20px; line-height: 1;
    cursor: pointer; padding: 0 4px;
  }
  .chart-close:hover { color: #e0e0e0; }
  .chart-legend { display: flex; gap: 14px; font-size: 12px; color: #a0a0b8; margin: 8px 0 4px; }
  .chart-legend span { display: inline-flex; align-items: center; gap: 6px; }
  .chart-legend i { width: 10px; height: 10px; border-radius: 2px; display: inline-block; }
  .chart-wrap { position: relative; }
  .chart-wrap svg { display: block; width: 100%; height: auto; }
  .chart-wrap .axis { fill: #8a8aa3; font-size: 10px; font-variant-numeric: tabular-nums; }
  .chart-wrap .grid { stroke: #2a3558; stroke-width: 1; }
  .chart-wrap .hit { fill: transparent; cursor: pointer; }
  .chart-wrap .hit:hover, .chart-wrap .hit.hover { fill: rgba(255,255,255,0.06); }
  .chart-wrap .current { fill: none; stroke: #e94560; stroke-width: 1.5; }
  .chart-tip {
    position: absolute; pointer-events: none; display: none; white-space: nowrap;
    background: #0f1830; border: 1px solid #1a4080; border-radius: 6px;
    padding: 6px 10px; font-size: 12px; line-height: 1.5; color: #e0e0e0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.5); transform: translate(-50%, calc(-100% - 8px));
  }
  .chart-tip b { font-weight: 700; }
  .chart-tip .row { display: flex; justify-content: space-between; gap: 14px; }
  .chart-tip .sw { display: inline-block; width: 8px; height: 8px; border-radius: 2px; margin-right: 6px; }
  .chart-hint { font-size: 11px; color: #8a8aa3; margin-top: 4px; }
</style>
</head>
<body>

<div id="map"></div>

<div class="chart-panel" id="chartPanel" role="dialog" aria-labelledby="chartTitle">
  <div class="chart-head">
    <div>
      <div class="chart-title" id="chartTitle"></div>
      <div class="chart-sub" id="chartSub"></div>
    </div>
    <button class="chart-close" id="chartClose" aria-label="Close chart">&times;</button>
  </div>
  <div class="chart-legend" id="chartLegend"></div>
  <div class="chart-wrap" id="chartWrap"><div class="chart-tip" id="chartTip"></div></div>
  <div class="chart-hint">Click a bar to jump the map to that month.</div>
</div>

<div class="controls">
  <div class="controls-top">
    <div class="month-label" id="monthLabel">2020-05</div>
    <div class="stats">
      <div>Stations: <span class="stat-total" id="statStations">0</span></div>
      <div>Rides: <span class="stat-total" id="statTotal">0</span></div>
      <div>Electric: <span class="stat-electric" id="statElectric">0</span></div>
      <div>Classic: <span class="stat-classic" id="statClassic">0</span></div>
      <div>Dockless: <span class="stat-dockless" id="statDockless">0</span></div>
    </div>
    <div style="display:flex;gap:8px;">
      <button class="btn" id="btnPlay">&#9654; Play</button>
      <button class="btn" id="btnSpeed">1x</button>
    </div>
  </div>
  <div class="slider-row">
    <input type="range" id="slider" min="0" max="70" value="0">
  </div>
</div>

<script>
const DATA = __JSON_DATA__;

const MONTHS = DATA.months;
const STATIONS = DATA.stations;
const DOCKLESS = DATA.dockless;

// Compute bounds from station data
let minLat = 90, maxLat = -90, minLng = 180, maxLng = -180;
for (const info of Object.values(STATIONS)) {
  if (info.lat < minLat) minLat = info.lat;
  if (info.lat > maxLat) maxLat = info.lat;
  if (info.lng < minLng) minLng = info.lng;
  if (info.lng > maxLng) maxLng = info.lng;
}

const map = L.map('map', { zoomControl: true });
map.fitBounds([[minLat - 0.01, minLng - 0.01], [maxLat + 0.01, maxLng + 0.01]]);

L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  maxZoom: 19
}).addTo(map);

// Legend
const legend = L.control({ position: 'topright' });
legend.onAdd = function() {
  const div = L.DomUtil.create('div', 'legend');
  div.innerHTML = `
    <div class="legend-item"><div class="legend-swatch" style="background:#00d4aa"></div> Electric</div>
    <div class="legend-item"><div class="legend-swatch" style="background:#4a9eff"></div> Classic</div>
    <div class="legend-item"><div class="legend-swatch" style="background:#ff9f43;opacity:0.6"></div> Dockless e-bike</div>
    <div style="margin-top:6px;font-size:11px;color:#888">Circle size = ride volume</div>
  `;
  return div;
};
legend.addTo(map);

// Flat lists for fast iteration
const stationList = Object.entries(STATIONS).map(([name, info]) => ({
  name, lat: info.lat, lng: info.lng, months: info.months
}));
const docklessList = Object.entries(DOCKLESS).map(([key, info]) => ({
  key, lat: info.lat, lng: info.lng, months: info.months
}));

// Global max for sizing
let globalMax = 0;
for (const s of stationList) {
  for (const vals of Object.values(s.months)) {
    const total = vals.e + vals.c;
    if (total > globalMax) globalMax = total;
  }
}

let stationMarkers = [];
let docklessMarkers = [];

function pieRadius(total) {
  if (total === 0) return 0;
  return 5 + 30 * Math.sqrt(total / globalMax);
}

function createPieSVG(electric, classic, radius) {
  const total = electric + classic;
  if (total === 0) return '';
  const size = radius * 2;
  const cx = radius, cy = radius, r = radius - 1;

  if (electric === 0)
    return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}"><circle cx="${cx}" cy="${cy}" r="${r}" fill="#4a9eff" stroke="#16213e" stroke-width="1.5"/></svg>`;
  if (classic === 0)
    return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}"><circle cx="${cx}" cy="${cy}" r="${r}" fill="#00d4aa" stroke="#16213e" stroke-width="1.5"/></svg>`;

  const eAngle = (electric / total) * 2 * Math.PI;
  const start = -Math.PI / 2;
  const x1 = cx + r * Math.cos(start), y1 = cy + r * Math.sin(start);
  const end = start + eAngle;
  const x2 = cx + r * Math.cos(end), y2 = cy + r * Math.sin(end);
  const la1 = eAngle > Math.PI ? 1 : 0;
  const la2 = (2 * Math.PI - eAngle) > Math.PI ? 1 : 0;

  return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
    <path d="M${cx},${cy} L${x1},${y1} A${r},${r} 0 ${la1},1 ${x2},${y2} Z" fill="#00d4aa" stroke="#16213e" stroke-width="0.5"/>
    <path d="M${cx},${cy} L${x2},${y2} A${r},${r} 0 ${la2},1 ${x1},${y1} Z" fill="#4a9eff" stroke="#16213e" stroke-width="0.5"/>
    <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="#16213e" stroke-width="1.5"/>
  </svg>`;
}

function tooltipContent(name, electric, classic) {
  const total = electric + classic;
  const ePct = total > 0 ? Math.round(100 * electric / total) : 0;
  return `<div class="tip-name">${name}</div>
    <div class="tip-row"><span>Total:</span> <span>${total}</span></div>
    <div class="tip-row"><span class="tip-electric">Electric:</span> <span class="tip-electric">${electric} (${ePct}%)</span></div>
    <div class="tip-row"><span class="tip-classic">Classic:</span> <span class="tip-classic">${classic} (${100-ePct}%)</span></div>`;
}

function renderMonth(monthIdx) {
  const ym = MONTHS[monthIdx];

  for (const m of stationMarkers) map.removeLayer(m);
  for (const m of docklessMarkers) map.removeLayer(m);
  stationMarkers = [];
  docklessMarkers = [];

  let totalRides = 0, totalElectric = 0, totalClassic = 0, totalDockless = 0, activeStations = 0;

  for (const s of stationList) {
    const d = s.months[ym];
    if (!d) continue;
    const e = d.e, c = d.c, total = e + c;
    if (total === 0) continue;

    activeStations++;
    totalRides += total;
    totalElectric += e;
    totalClassic += c;

    const r = pieRadius(total);
    const icon = L.divIcon({
      html: createPieSVG(e, c, r),
      className: '',
      iconSize: [r * 2, r * 2],
      iconAnchor: [r, r]
    });

    const marker = L.marker([s.lat, s.lng], { icon })
      .bindTooltip(tooltipContent(s.name, e, c), {
        className: 'station-tooltip', direction: 'top', offset: [0, -r]
      })
      .on('click', () => openChart(s));
    marker.addTo(map);
    stationMarkers.push(marker);
  }

  for (const dk of docklessList) {
    const cnt = dk.months[ym];
    if (!cnt) continue;
    totalDockless += cnt;

    const r = pieRadius(cnt);
    const circle = L.circleMarker([dk.lat, dk.lng], {
      radius: r, color: '#ff9f43', weight: 1, opacity: 0.7,
      fillColor: '#ff9f43', fillOpacity: 0.35
    }).bindTooltip(`<div class="tip-name">Dockless e-bikes</div><div>Rides: ${cnt}</div>`, {
      className: 'station-tooltip', direction: 'top'
    }).on('click', () => openChart(dk));
    circle.addTo(map);
    docklessMarkers.push(circle);
  }

  document.getElementById('monthLabel').textContent = ym;
  document.getElementById('statStations').textContent = activeStations.toLocaleString();
  document.getElementById('statTotal').textContent = totalRides.toLocaleString();
  document.getElementById('statElectric').textContent = totalElectric.toLocaleString();
  document.getElementById('statClassic').textContent = totalClassic.toLocaleString();
  document.getElementById('statDockless').textContent = totalDockless.toLocaleString();
  markChartMonth(monthIdx);
}

// Station chart: stacked monthly electric/classic bars for the clicked station
const SVG_NS = 'http://www.w3.org/2000/svg';
const chartPanel = document.getElementById('chartPanel');
const chartWrap = document.getElementById('chartWrap');
const chartTip = document.getElementById('chartTip');
const CW = 540, CH = 190, CL = 44, CR = 6, CT = 8, CB = 20;
let chartStation = null, chartCurrent = null;

function svgEl(tag, attrs) {
  const el = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
}

// Axis top as 4 whole-number gridline steps (rides are counts, so no 12.5)
function niceMax(v) {
  const raw = Math.max(v / 4, 1);
  const pow = Math.pow(10, Math.floor(Math.log10(raw)));
  for (const m of [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]) {
    const step = m * pow;
    if (step >= raw && Number.isInteger(step)) return step * 4;
  }
  return 40 * pow;
}

// Opens for a station ({name, months: {ym: {e, c}}}) or a dockless cell ({key, months: {ym: count}})
function openChart(s) {
  chartStation = s;
  const dockless = s.key !== undefined;
  const vals = MONTHS.map(ym => dockless
    ? { e: 0, c: 0, d: s.months[ym] || 0 }
    : { e: 0, c: 0, d: 0, ...s.months[ym] });
  const active = MONTHS.filter((ym, i) => vals[i].e + vals[i].c + vals[i].d > 0);
  const totE = vals.reduce((a, v) => a + v.e, 0), totC = vals.reduce((a, v) => a + v.c, 0);
  const totD = vals.reduce((a, v) => a + v.d, 0);
  const tot = totE + totC + totD;
  const name = dockless ? 'Dockless e-bikes' : s.name;
  const range = active.length ? `active ${active[0]} to ${active[active.length - 1]}` : '';

  document.getElementById('chartTitle').textContent = name;
  document.getElementById('chartSub').textContent = !active.length ? 'No rides'
    : dockless
      ? `~200 m area at ${s.lat.toFixed(3)}, ${s.lng.toFixed(3)} · ${tot.toLocaleString()} rides · ${range}`
      : `${tot.toLocaleString()} rides · ${Math.round(100 * totE / tot)}% electric · ${range}`;
  // A single series needs no legend; the title names it
  document.getElementById('chartLegend').innerHTML = dockless ? '' :
    '<span><i style="background:#00d4aa"></i>Electric</span><span><i style="background:#4a9eff"></i>Classic</span>';

  const yMax = niceMax(Math.max(...vals.map(v => v.e + v.c + v.d)));
  const plotW = CW - CL - CR, plotH = CH - CT - CB;
  const step = plotW / MONTHS.length;
  const barW = Math.max(1, step - Math.min(2, step * 0.25));
  const y = v => CT + plotH - (v / yMax) * plotH;

  const svg = svgEl('svg', { viewBox: `0 0 ${CW} ${CH}`, role: 'img',
    'aria-label': dockless
      ? `Monthly dockless e-bike rides near ${s.lat.toFixed(3)}, ${s.lng.toFixed(3)}, ${MONTHS[0]} to ${MONTHS[MONTHS.length - 1]}`
      : `Monthly rides at ${s.name}, electric and classic, ${MONTHS[0]} to ${MONTHS[MONTHS.length - 1]}` });

  for (let i = 0; i <= 4; i++) {
    const v = yMax * i / 4, gy = y(v);
    svg.appendChild(svgEl('line', { class: 'grid', x1: CL, x2: CW - CR, y1: gy, y2: gy }));
    const t = svgEl('text', { class: 'axis', x: CL - 6, y: gy + 3, 'text-anchor': 'end' });
    t.textContent = v >= 1000 ? (v / 1000).toLocaleString() + 'k' : v.toLocaleString();
    svg.appendChild(t);
  }

  MONTHS.forEach((ym, i) => {
    const x = CL + i * step + (step - barW) / 2;
    const { e, c, d } = vals[i];
    if (d > 0) svg.appendChild(svgEl('rect', { x, y: y(d), width: barW, height: Math.max(0.5, y(0) - y(d)),
      fill: '#ff9f43', rx: Math.min(1.5, barW / 3) }));
    // Classic on the baseline, electric stacked on top, 1px surface gap between them
    if (c > 0) svg.appendChild(svgEl('rect', { x, y: y(c), width: barW, height: Math.max(0.5, y(0) - y(c)),
      fill: '#4a9eff', rx: Math.min(1.5, barW / 3) }));
    if (e > 0) {
      const top = y(c + e), bottom = y(c) - (c > 0 ? 1 : 0);
      svg.appendChild(svgEl('rect', { x, y: top, width: barW, height: Math.max(0.5, bottom - top),
        fill: '#00d4aa', rx: Math.min(1.5, barW / 3) }));
    }
    if (ym.endsWith('-01') || i === 0) {
      const t = svgEl('text', { class: 'axis', x: CL + i * step + step / 2, y: CH - 6, 'text-anchor': i === 0 ? 'start' : 'middle' });
      t.textContent = ym.slice(0, 4);
      svg.appendChild(t);
    }
  });

  chartCurrent = svgEl('rect', { class: 'current', y: CT - 2, width: step, height: plotH + 4, rx: 2 });
  svg.appendChild(chartCurrent);

  // Full-height hit targets, wider than the bars, for hover and click
  MONTHS.forEach((ym, i) => {
    const hit = svgEl('rect', { class: 'hit', x: CL + i * step, y: CT, width: step, height: plotH });
    hit.addEventListener('mouseenter', () => showChartTip(i, vals[i]));
    hit.addEventListener('mouseleave', () => { chartTip.style.display = 'none'; });
    hit.addEventListener('click', () => { slider.value = i; renderMonth(i); });
    svg.appendChild(hit);
  });

  chartWrap.querySelector('svg')?.remove();
  chartWrap.insertBefore(svg, chartTip);
  chartPanel.classList.add('open');
  markChartMonth(parseInt(slider.value));
}

function showChartTip(i, v) {
  const t = v.e + v.c;
  const pct = t ? Math.round(100 * v.e / t) : 0;
  if (chartStation.key !== undefined) chartTip.innerHTML = `<b>${MONTHS[i]}</b>
    <div class="row"><span><i class="sw" style="background:#ff9f43"></i>Dockless rides</span><span>${v.d.toLocaleString()}</span></div>`;
  else chartTip.innerHTML = `<b>${MONTHS[i]}</b>
    <div class="row"><span>Total</span><span>${t.toLocaleString()}</span></div>
    <div class="row"><span><i class="sw" style="background:#00d4aa"></i>Electric</span><span>${v.e.toLocaleString()}${t ? ` (${pct}%)` : ''}</span></div>
    <div class="row"><span><i class="sw" style="background:#4a9eff"></i>Classic</span><span>${v.c.toLocaleString()}${t ? ` (${100 - pct}%)` : ''}</span></div>`;
  const svg = chartWrap.querySelector('svg');
  const scale = svg.getBoundingClientRect().width / CW;
  const step = (CW - CL - CR) / MONTHS.length;
  const cx = (CL + i * step + step / 2) * scale;
  chartTip.style.display = 'block';
  const half = chartTip.offsetWidth / 2, maxX = chartWrap.clientWidth;
  chartTip.style.left = Math.min(Math.max(cx, half), maxX - half) + 'px';
  chartTip.style.top = (CT * scale) + 'px';
}

function markChartMonth(i) {
  if (!chartCurrent) return;
  const step = (CW - CL - CR) / MONTHS.length;
  chartCurrent.setAttribute('x', CL + i * step);
}

function closeChart() {
  chartPanel.classList.remove('open');
  chartStation = null; chartCurrent = null;
}
document.getElementById('chartClose').addEventListener('click', closeChart);

// Controls
const slider = document.getElementById('slider');
const btnPlay = document.getElementById('btnPlay');
const btnSpeed = document.getElementById('btnSpeed');
slider.max = MONTHS.length - 1;

slider.addEventListener('input', () => renderMonth(parseInt(slider.value)));

document.addEventListener('keydown', (e) => {
  if (e.key === 'ArrowLeft' && slider.value > 0) {
    slider.value = parseInt(slider.value) - 1;
    renderMonth(parseInt(slider.value));
  } else if (e.key === 'ArrowRight' && slider.value < MONTHS.length - 1) {
    slider.value = parseInt(slider.value) + 1;
    renderMonth(parseInt(slider.value));
  } else if (e.key === 'Escape') {
    closeChart();
  } else if (e.key === ' ') {
    e.preventDefault();
    togglePlay();
  }
});

let playing = false, playInterval = null, speedMs = 800;
const speeds = [{ label: '1x', ms: 800 }, { label: '2x', ms: 400 }, { label: '4x', ms: 200 }];
let speedIdx = 0;

function togglePlay() {
  playing = !playing;
  btnPlay.innerHTML = playing ? '&#9646;&#9646; Pause' : '&#9654; Play';
  btnPlay.classList.toggle('active', playing);
  if (playing) {
    playInterval = setInterval(() => {
      let next = parseInt(slider.value) + 1;
      if (next >= MONTHS.length) next = 0;
      slider.value = next;
      renderMonth(next);
    }, speedMs);
  } else clearInterval(playInterval);
}

btnPlay.addEventListener('click', togglePlay);
btnSpeed.addEventListener('click', () => {
  speedIdx = (speedIdx + 1) % speeds.length;
  speedMs = speeds[speedIdx].ms;
  btnSpeed.textContent = speeds[speedIdx].label;
  if (playing) {
    clearInterval(playInterval);
    playInterval = setInterval(() => {
      let next = parseInt(slider.value) + 1;
      if (next >= MONTHS.length) next = 0;
      slider.value = next;
      renderMonth(next);
    }, speedMs);
  }
});

renderMonth(0);
</script>
</body>
</html>
'''

html = HTML_TEMPLATE.replace('__JSON_DATA__', json_data)

with open(OUT_PATH, "w") as f:
    f.write(html)

import os
size_kb = os.path.getsize(OUT_PATH) / 1024
print(f"\nWrote {OUT_PATH} ({size_kb:.0f} KB)")
print("Open it in your browser!")
