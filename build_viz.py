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
</style>
</head>
<body>

<div id="map"></div>

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

L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
  attribution: '&copy; OpenStreetMap &copy; CARTO',
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
      });
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
    });
    circle.addTo(map);
    docklessMarkers.push(circle);
  }

  document.getElementById('monthLabel').textContent = ym;
  document.getElementById('statStations').textContent = activeStations.toLocaleString();
  document.getElementById('statTotal').textContent = totalRides.toLocaleString();
  document.getElementById('statElectric').textContent = totalElectric.toLocaleString();
  document.getElementById('statClassic').textContent = totalClassic.toLocaleString();
  document.getElementById('statDockless').textContent = totalDockless.toLocaleString();
}

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
