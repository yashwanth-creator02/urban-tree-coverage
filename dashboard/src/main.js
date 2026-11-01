import L from "leaflet";
import {
  Chart,
  LineController,
  LineElement,
  PointElement,
  LinearScale,
  Title,
  CategoryScale,
  BarController,
  BarElement,
  Tooltip,
  Legend,
} from "chart.js";

// Register Chart.js components
Chart.register(
  LineController,
  LineElement,
  PointElement,
  LinearScale,
  Title,
  CategoryScale,
  BarController,
  BarElement,
  Tooltip,
  Legend
);

// Global State
const state = {
  mode: "annual", // "annual" | "change"
  zoneType: "grid_1km", // "grid_1km" | "wards"
  selectedYearIndex: 3, // 0: 2000, 1: 2010, 2: 2020, 3: 2025
  years: [2000, 2010, 2020, 2025],
  showRaster: false,
  rasterOpacity: 0.75,
  showLandmarks: true,
  selectedFeature: null,
};

// Data Store
let cityStats = null;
let changeStats = null;
let lossHotspots = null;
let validationReport = null;
let forecastData = null;
let zonesData = {
  grid_1km: null,
  wards: null,
};

// Map & Layer References
let map = null;
let geojsonLayer = null;
let rasterOverlay = null;
let landmarkLayerGroup = null;
let timelineChart = null;
let tiersChart = null;

// Palette definitions matching brand tokens
const PALETTE = {
  obsidianCanvas: "#161b22",
  obsidianSurface: "#21262d",
  borderSubtle: "#30363d",
  copperBase: "#d97736",
  copperDark: "#a85420",
  lossCopper: "#c45d2c",
  forestDense: "#2e7d32",
  emeraldModerate: "#388e3c",
  mintSparse: "#81c784",
  textPrimary: "#f0f6fc",
  textSecondary: "#8b949e",
};

// Bengaluru geographic bounds for raster overlays
const BENGALURU_BBOX = [
  [12.83, 77.46],
  [13.14, 77.75],
];

// Initialize Application
async function initApp() {
  initMap();
  await loadDatasets();
  setupEventListeners();
  updateKPIs();
  renderTimelineChart();
  renderTiersChart();
  renderHotspots();
  renderValidationSummary();
  updateMapLayers();
}

// Map Initialization
function initMap() {
  map = L.map("map", {
    center: [12.9716, 77.5946],
    zoom: 11,
    zoomControl: false,
  });

  L.control.zoom({ position: "topright" }).addTo(map);

  // CartoDB Dark Matter Base Tiles
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
    subdomains: "abcd",
    maxZoom: 19,
  }).addTo(map);

  landmarkLayerGroup = L.layerGroup().addTo(map);
}

// Data Fetching
async function loadDatasets() {
  try {
    const [cityRes, chgRes, gridRes, wardsRes, hotRes, valRes, fcRes] = await Promise.all([
      fetch("./data/city_stats.json"),
      fetch("./data/change_stats.json"),
      fetch("./data/zones_grid_1km.geojson"),
      fetch("./data/zones_wards.geojson"),
      fetch("./data/loss_hotspots.json"),
      fetch("./data/validation_report.json"),
      fetch("./data/forecast.json"),
    ]);

    cityStats = await cityRes.json();
    changeStats = await chgRes.json();
    zonesData.grid_1km = await gridRes.json();
    if (wardsRes.ok) {
      zonesData.wards = await wardsRes.json();
    }
    lossHotspots = await hotRes.json();
    validationReport = await valRes.json();
    forecastData = await fcRes.json();
  } catch (err) {
    console.error("Failed loading analytical datasets:", err);
  }
}

// Setup UI Listeners
function setupEventListeners() {
  // Mode Selector
  const modeButtons = document.querySelectorAll("#mode-selector button");
  modeButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      modeButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.mode = btn.dataset.mode;

      const yearGroup = document.getElementById("year-control-group");
      if (state.mode === "change") {
        yearGroup.style.display = "none";
      } else {
        yearGroup.style.display = "flex";
      }

      updateMapLayers();
      updateLegend();
    });
  });

  // Zone Partitioning Selector
  const zoneButtons = document.querySelectorAll("#zone-selector button");
  zoneButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      zoneButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.zoneType = btn.dataset.zone;
      updateMapLayers();
    });
  });

  // Year Slider
  const yearSlider = document.getElementById("year-slider");
  const yearDisplay = document.getElementById("current-year-val");
  yearSlider.addEventListener("input", (e) => {
    state.selectedYearIndex = parseInt(e.target.value, 10);
    const yr = state.years[state.selectedYearIndex];
    yearDisplay.textContent = yr;
    updateMapLayers();
    renderTiersChart();
    if (state.selectedFeature) {
      updateZoneDetails(state.selectedFeature.properties);
    }
  });

  // Raster Overlay Toggles
  const btnRasterOff = document.getElementById("btn-raster-off");
  const btnRasterOn = document.getElementById("btn-raster-on");
  const opacityControl = document.getElementById("opacity-control-group");
  const opacitySlider = document.getElementById("raster-opacity");

  btnRasterOff.addEventListener("click", () => {
    btnRasterOff.classList.add("active");
    btnRasterOn.classList.remove("active");
    state.showRaster = false;
    opacityControl.style.display = "none";
    updateRasterOverlay();
  });

  btnRasterOn.addEventListener("click", () => {
    btnRasterOn.classList.add("active");
    btnRasterOff.classList.remove("active");
    state.showRaster = true;
    opacityControl.style.display = "flex";
    updateRasterOverlay();
  });

  opacitySlider.addEventListener("input", (e) => {
    state.rasterOpacity = parseFloat(e.target.value) / 100.0;
    if (rasterOverlay) {
      rasterOverlay.setOpacity(state.rasterOpacity);
    }
  });

  // Landmark Pins Toggle
  const btnLandmarksOn = document.getElementById("btn-landmarks-on");
  const btnLandmarksOff = document.getElementById("btn-landmarks-off");

  btnLandmarksOn.addEventListener("click", () => {
    btnLandmarksOn.classList.add("active");
    btnLandmarksOff.classList.remove("active");
    state.showLandmarks = true;
    updateLandmarkMarkers();
  });

  btnLandmarksOff.addEventListener("click", () => {
    btnLandmarksOff.classList.add("active");
    btnLandmarksOn.classList.remove("active");
    state.showLandmarks = false;
    updateLandmarkMarkers();
  });
}

// Styling Functions for Vector Polygons
function getAnnualColor(pct) {
  if (pct >= 40) return "#2e7d32"; // Dense Forest
  if (pct >= 25) return "#388e3c"; // Moderate Canopy
  if (pct >= 15) return "#81c784"; // Sparse Vegetation
  if (pct >= 5) return "#48525e";  // Low Cover
  return "#21262d";                // Urban / Built
}

function getChangeColor(netPct) {
  if (netPct <= -15) return "#a85420"; // Severe Loss
  if (netPct <= -5) return "#c45d2c";  // Moderate Loss
  if (netPct < 5) return "#30363d";   // Stable
  if (netPct < 15) return "#388e3c";  // Moderate Gain
  return "#2e7d32";                  // High Gain
}

// Update Map Vector Layers
function updateMapLayers() {
  if (geojsonLayer) {
    map.removeLayer(geojsonLayer);
  }

  const activeGeojson = zonesData[state.zoneType] || zonesData.grid_1km;
  if (!activeGeojson) return;

  const currentYear = state.years[state.selectedYearIndex];

  geojsonLayer = L.geoJSON(activeGeojson, {
    style: (feature) => {
      const props = feature.properties;
      let fillColor = "#21262d";
      let fillOpacity = 0.65;

      if (state.mode === "annual") {
        const pct = props[`green_pct_${currentYear}`] || 0.0;
        fillColor = getAnnualColor(pct);
      } else {
        const netPct = props.net_change_pct || 0.0;
        fillColor = getChangeColor(netPct);
      }

      return {
        fillColor: fillColor,
        fillOpacity: fillOpacity,
        weight: 1,
        color: "#30363d",
        opacity: 0.6,
      };
    },
    onEachFeature: (feature, layer) => {
      layer.on({
        mouseover: (e) => {
          const l = e.target;
          l.setStyle({ weight: 2, color: "#d97736", fillOpacity: 0.85 });
          updateZoneDetails(feature.properties);
        },
        mouseout: (e) => {
          geojsonLayer.resetStyle(e.target);
        },
        click: (e) => {
          state.selectedFeature = feature;
          updateZoneDetails(feature.properties);
        },
      });
    },
  }).addTo(map);

  updateLegend();
  updateRasterOverlay();
  updateLandmarkMarkers();
}

// Raster Imagery Overlay
function updateRasterOverlay() {
  if (rasterOverlay) {
    map.removeLayer(rasterOverlay);
    rasterOverlay = null;
  }

  if (!state.showRaster) return;

  const yr = state.years[state.selectedYearIndex];
  const url =
    state.mode === "annual"
      ? `./data/previews/ndvi_${yr}.png`
      : "./data/previews/change_2000_2025.png";

  rasterOverlay = L.imageOverlay(url, BENGALURU_BBOX, {
    opacity: state.rasterOpacity,
    interactive: false,
  }).addTo(map);
}

// Landmark Pins Layer
function updateLandmarkMarkers() {
  landmarkLayerGroup.clearLayers();
  if (!state.showLandmarks || !validationReport) return;

  const landmarks = validationReport.landmark_consistency || {};
  Object.entries(landmarks).forEach(([key, item]) => {
    const [lon, lat] = item.coordinates;
    const isConsistent = item.verified_consistent;
    const markerColor = isConsistent ? PALETTE.forestDense : PALETTE.lossCopper;

    const icon = L.divIcon({
      className: "custom-pin",
      html: `<div style="background-color: ${markerColor}; width: 10px; height: 10px; border: 1px solid #f0f6fc; border-radius: 2px;"></div>`,
      iconSize: [10, 10],
    });

    const marker = L.marker([lat, lon], { icon }).addTo(landmarkLayerGroup);
    marker.bindPopup(`
      <div style="font-family: ui-monospace, SFMono-Regular, monospace; font-size: 11px;">
        <strong style="text-transform: uppercase;">${key.replace(/_/g, " ")}</strong><br/>
        Expected Canopy: ${item.expected_canopy ? "Yes" : "No"}<br/>
        Status: ${isConsistent ? "Consistent" : "Discrepancy"}<br/>
        2025 NDVI: ${item.observations["2025"].ndvi}
      </div>
    `);
  });
}

// Dynamic Legend
function updateLegend() {
  const legendEl = document.getElementById("map-legend");
  if (!legendEl) return;

  if (state.mode === "annual") {
    legendEl.innerHTML = `
      <div class="legend-title">Canopy Density (${state.years[state.selectedYearIndex]})</div>
      <div class="legend-scale">
        <div class="legend-row"><span class="color-box" style="background: #2e7d32;"></span> >= 40% (Dense Canopy)</div>
        <div class="legend-row"><span class="color-box" style="background: #388e3c;"></span> 25% - 40% (Moderate)</div>
        <div class="legend-row"><span class="color-box" style="background: #81c784;"></span> 15% - 25% (Sparse)</div>
        <div class="legend-row"><span class="color-box" style="background: #48525e;"></span> 5% - 15% (Low Cover)</div>
        <div class="legend-row"><span class="color-box" style="background: #21262d;"></span> &lt; 5% (Built / Urban)</div>
      </div>
    `;
  } else {
    legendEl.innerHTML = `
      <div class="legend-title">Net Change (2000 - 2025)</div>
      <div class="legend-scale">
        <div class="legend-row"><span class="color-box" style="background: #2e7d32;"></span> >= +15% (High Gain)</div>
        <div class="legend-row"><span class="color-box" style="background: #388e3c;"></span> +5% to +15% (Gain)</div>
        <div class="legend-row"><span class="color-box" style="background: #30363d;"></span> -5% to +5% (Stable)</div>
        <div class="legend-row"><span class="color-box" style="background: #c45d2c;"></span> -5% to -15% (Loss)</div>
        <div class="legend-row"><span class="color-box" style="background: #a85420;"></span> &lt; -15% (Severe Loss)</div>
      </div>
    `;
  }
}

// Update Top KPI Cards
function updateKPIs() {
  if (!cityStats) return;
  const d2025 = cityStats.data["2025"];
  const d2000 = cityStats.data["2000"];

  document.getElementById("kpi-canopy-area").textContent = `${d2025.green_area_km2} km²`;
  document.getElementById("kpi-canopy-pct").textContent = `${d2025.green_percentage}%`;

  const netKm2 = (d2025.green_area_km2 - d2000.green_area_km2).toFixed(2);
  const netEl = document.getElementById("kpi-net-shift");
  netEl.textContent = `${netKm2 > 0 ? "+" : ""}${netKm2} km²`;
  netEl.className = `kpi-value ${netKm2 >= 0 ? "gain" : "loss"}`;

  document.getElementById("kpi-patch-count").textContent = d2025.fragmentation.patch_count.toLocaleString();
}

// Update Selected Zone Details
function updateZoneDetails(props) {
  const container = document.getElementById("zone-details-body");
  if (!container || !props) return;

  const currentYr = state.years[state.selectedYearIndex];
  const currentPct = props[`green_pct_${currentYr}`] !== undefined ? props[`green_pct_${currentYr}`] : "--";
  const currentKm2 = props[`green_km2_${currentYr}`] !== undefined ? props[`green_km2_${currentYr}`] : "--";
  const netPct = props.net_change_pct !== undefined ? props.net_change_pct : "--";
  const lossKm2 = props.loss_km2 !== undefined ? props.loss_km2 : "--";
  const gainKm2 = props.gain_km2 !== undefined ? props.gain_km2 : "--";

  container.innerHTML = `
    <div style="margin-bottom: 8px;">
      <strong style="color: var(--color-text-primary); font-size: 13px;">${props.label || props.zone_id}</strong>
      <div style="font-size: 11px; color: var(--color-text-muted); font-family: ui-monospace, SFMono-Regular, monospace;">
        ID: ${props.zone_id} | Centroid: [${props.centroid_lon}, ${props.centroid_lat}]
      </div>
    </div>
    <div class="zone-detail-row">
      <span>${currentYr} Green Coverage:</span>
      <span>${currentPct}% (${currentKm2} km²)</span>
    </div>
    <div class="zone-detail-row">
      <span>2000 Baseline:</span>
      <span>${props.green_pct_2000 || "--"}%</span>
    </div>
    <div class="zone-detail-row">
      <span>Net Shift (2000-25):</span>
      <span style="color: ${netPct < 0 ? "var(--color-change-loss)" : "var(--color-change-gain)"}">${netPct > 0 ? "+" : ""}${netPct}%</span>
    </div>
    <div class="zone-detail-row">
      <span>Decadal Canopy Loss:</span>
      <span style="color: var(--color-change-loss);">${lossKm2} km²</span>
    </div>
    <div class="zone-detail-row">
      <span>Decadal Canopy Gain:</span>
      <span style="color: var(--color-change-gain);">${gainKm2} km²</span>
    </div>
  `;
}

// Render Trajectory Line Chart
function renderTimelineChart() {
  const ctx = document.getElementById("timeline-chart");
  if (!ctx || !cityStats) return;

  const labels = ["2000", "2010", "2020", "2025", "2030 (P)", "2035 (P)"];
  const historical = state.years.map((y) => cityStats.data[String(y)].green_percentage);
  const projected2030 = forecastData ? forecastData.projections["2030"] : null;
  const projected2035 = forecastData ? forecastData.projections["2035"] : null;

  const histSeries = [...historical, null, null];
  const projSeries = [null, null, null, historical[historical.length - 1], projected2030, projected2035];

  timelineChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Observed Green %",
          data: histSeries,
          borderColor: PALETTE.forestDense,
          backgroundColor: PALETTE.forestDense,
          borderWidth: 2,
          pointRadius: 4,
          tension: 0.1,
        },
        {
          label: "Projected Trend",
          data: projSeries,
          borderColor: PALETTE.copperBase,
          backgroundColor: PALETTE.copperBase,
          borderDash: [4, 4],
          borderWidth: 2,
          pointRadius: 4,
          tension: 0.1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { color: PALETTE.textSecondary, boxWidth: 12, font: { size: 10 } },
        },
      },
      scales: {
        x: {
          ticks: { color: PALETTE.textSecondary, font: { size: 10 } },
          grid: { color: PALETTE.borderSubtle },
        },
        y: {
          ticks: { color: PALETTE.textSecondary, font: { size: 10 } },
          grid: { color: PALETTE.borderSubtle },
          min: 10,
          max: 35,
        },
      },
    },
  });
}

// Render Vegetation Tier Breakdown Chart
function renderTiersChart() {
  const ctx = document.getElementById("tiers-chart");
  if (!ctx || !cityStats) return;

  const yr = state.years[state.selectedYearIndex];
  const yearData = cityStats.data[String(yr)];
  const tiers = yearData.tier_breakdown;

  const labels = ["Non-Veg", "Sparse", "Moderate", "Dense"];
  const values = [
    tiers.non_vegetated.area_km2,
    tiers.sparse_vegetation.area_km2,
    tiers.moderate_canopy.area_km2,
    tiers.dense_tree_canopy.area_km2,
  ];

  if (tiersChart) {
    tiersChart.data.datasets[0].data = values;
    tiersChart.options.plugins.title.text = `Land Cover Tiers - ${yr} (km²)`;
    tiersChart.update();
    return;
  }

  tiersChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          data: values,
          backgroundColor: [
            "#48525e", // Non-vegetated
            "#81c784", // Sparse
            "#388e3c", // Moderate
            "#2e7d32", // Dense
          ],
          borderWidth: 1,
          borderColor: PALETTE.borderSubtle,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        title: {
          display: true,
          text: `Land Cover Tiers - ${yr} (km²)`,
          color: PALETTE.textSecondary,
          font: { size: 11 },
        },
      },
      scales: {
        x: {
          ticks: { color: PALETTE.textSecondary, font: { size: 10 } },
          grid: { display: false },
        },
        y: {
          ticks: { color: PALETTE.textSecondary, font: { size: 10 } },
          grid: { color: PALETTE.borderSubtle },
        },
      },
    },
  });
}

// Render Top Loss Hotspots List
function renderHotspots() {
  const container = document.getElementById("hotspots-container");
  if (!container || !lossHotspots) return;

  container.innerHTML = "";
  lossHotspots.slice(0, 10).forEach((item) => {
    const row = document.createElement("div");
    row.className = "hotspot-row";
    row.innerHTML = `
      <div>
        <div class="hotspot-label">${item.label}</div>
        <div style="font-size: 10px; color: var(--color-text-muted);">
          2000: ${item.green_pct_2000}% → 2025: ${item.green_pct_2025}%
        </div>
      </div>
      <div class="hotspot-delta">${item.net_change_pct}%</div>
    `;

    row.addEventListener("click", () => {
      map.flyTo([item.centroid_lat, item.centroid_lon], 13, { duration: 1.2 });
      if (zonesData.grid_1km) {
        const feature = zonesData.grid_1km.features.find(
          (f) => f.properties.zone_id === item.zone_id
        );
        if (feature) {
          updateZoneDetails(feature.properties);
        }
      }
    });

    container.appendChild(row);
  });
}

// Render Ground Truth Consistency Summary
function renderValidationSummary() {
  const container = document.getElementById("landmark-verification-body");
  if (!container || !validationReport) return;

  const landmarks = validationReport.landmark_consistency || {};
  let html = "";
  Object.entries(landmarks).forEach(([key, val]) => {
    const isPass = val.verified_consistent;
    const color = isPass ? "var(--color-change-gain)" : "var(--color-change-loss)";
    html += `
      <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--color-border-subtle); padding: 4px 0;">
        <span>${key.replace(/_/g, " ").toUpperCase()}:</span>
        <span style="font-family: ui-monospace, SFMono-Regular, monospace; color: ${color}; font-weight: 600;">
          ${isPass ? "CONSISTENT" : "CHECK"}
        </span>
      </div>
    `;
  });

  html += `
    <div style="font-size: 10px; color: var(--color-text-muted); margin-top: 6px;">
      50 Systematic Sample Points Verified (${validationReport.sample_points_count} points).
    </div>
  `;
  container.innerHTML = html;
}

// Start Application
window.addEventListener("DOMContentLoaded", initApp);
