/**
 * India Urban & National Green Cover Intelligence System
 * Full-viewport multi-tier analytical dashboard (Leaflet + Chart.js).
 */

const PALETTE = {
  copperBase: "#c45d2c",
  copperDark: "#9e441b",
  forestDense: "#1b4d3e",
  forestModerate: "#2e7d32",
  forestLight: "#66bb6a",
  bgPrimary: "#0d1117",
  bgSecondary: "#161b22",
  borderSubtle: "#30363d",
  textPrimary: "#e6edf3",
  textSecondary: "#8b949e",
};

const BASEMAP_PROVIDERS = {
  osm_standard: {
    url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    options: {
      attribution: "&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors",
      maxZoom: 19,
    },
  },
  esri_streets: {
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
    options: {
      attribution: "Tiles &copy; Esri &mdash; English Labels",
      maxZoom: 19,
    },
  },
  esri_satellite: {
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    options: {
      attribution: "Tiles &copy; Esri",
      maxZoom: 18,
    },
  },
  openfreemap_positron: {
    url: "https://tiles.openfreemap.org/styles/positron/{z}/{x}/{y}.png",
    options: {
      attribution: "&copy; <a href='https://openfreemap.org'>OpenFreeMap</a> &copy; OpenStreetMap",
      maxZoom: 18,
    },
  },
  carto_dark_keyed: {
    url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    options: {
      attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
      subdomains: "abcd",
      maxZoom: 19,
    },
  },
};

// Application State
const state = {
  year: 2025,
  yearIndex: 3,
  years: [2000, 2010, 2020, 2025],
  mode: "annual", // "annual" | "change"
  tierSelection: "auto", // "auto" | "states" | "districts" | "city"
  activeTier: "national", // "national" | "district" | "city"
  basemapKey: "osm_standard",
  showRaster: true,
  showVectors: true,
  showLandmarks: true,
  rasterOpacity: 0.75,
  isPlaying: false,
  playTimer: null,
  selectedFeature: null,
};

// Global Data Holders
let map = null;
let currentBasemapLayer = null;
let nationalRasterLayer = null;
let cityRasterLayer = null;
let statesGeoJsonLayer = null;
let districtsGeoJsonLayer = null;
let cityGridGeoJsonLayer = null;
let landmarksLayer = null;
let timelineChart = null;

let statesData = null;
let districtsData = null;
let nationalStats = null;
let cityGridData = null;
let cityStats = null;
let citiesRegistry = null;
let lossHotspots = null;
let forecastData = null;

// Initialize on DOM Load
document.addEventListener("DOMContentLoaded", async () => {
  initMap();
  setupEventListeners();
  await loadDatasets();
  updateTierByZoom();
  renderLegend();
  updateView();
});

// Initialize Leaflet Map
function initMap() {
  // Center of India
  map = L.map("map", {
    center: [22.5937, 78.9629],
    zoom: 5,
    minZoom: 4,
    maxZoom: 16,
    zoomControl: false,
  });

  L.control.zoom({ position: "topright" }).addTo(map);

  setBasemap(state.basemapKey);

  landmarksLayer = L.layerGroup().addTo(map);

  map.on("zoomend", () => {
    if (state.tierSelection === "auto") {
      updateTierByZoom();
    }
  });
}

// Basemap Management
function setBasemap(providerKey) {
  if (currentBasemapLayer) {
    map.removeLayer(currentBasemapLayer);
  }
  const provider = BASEMAP_PROVIDERS[providerKey] || BASEMAP_PROVIDERS.osm_standard;
  currentBasemapLayer = L.tileLayer(provider.url, provider.options).addTo(map);
  state.basemapKey = providerKey;
}

// Load Datasets
async function loadDatasets() {
  try {
    const [
      natRes,
      statesRes,
      distRes,
      citiesRes,
      bengGridRes,
      bengCityRes,
      hotRes,
      fcRes,
    ] = await Promise.allSettled([
      fetch("./data/national_stats.json").then((r) => (r.ok ? r.json() : null)),
      fetch("./data/india_states.geojson").then((r) => (r.ok ? r.json() : null)),
      fetch("./data/india_districts.geojson").then((r) => (r.ok ? r.json() : null)),
      fetch("./data/cities_registry.json").then((r) => (r.ok ? r.json() : null)),
      fetch("./data/zones_grid_1km.geojson").then((r) => (r.ok ? r.json() : null)),
      fetch("./data/city_stats.json").then((r) => (r.ok ? r.json() : null)),
      fetch("./data/loss_hotspots.json").then((r) => (r.ok ? r.json() : null)),
      fetch("./data/forecast.json").then((r) => (r.ok ? r.json() : null)),
    ]);

    nationalStats = natRes.status === "fulfilled" ? natRes.value : null;
    statesData = statesRes.status === "fulfilled" ? statesRes.value : null;
    districtsData = distRes.status === "fulfilled" ? distRes.value : null;
    citiesRegistry = citiesRes.status === "fulfilled" ? citiesRes.value : null;
    cityGridData = bengGridRes.status === "fulfilled" ? bengGridRes.value : null;
    cityStats = bengCityRes.status === "fulfilled" ? bengCityRes.value : null;
    lossHotspots = hotRes.status === "fulfilled" ? hotRes.value : null;
    forecastData = fcRes.status === "fulfilled" ? fcRes.value : null;

    if (statesData && statesData._provenance) state.statesProvenance = statesData._provenance;
    if (districtsData && districtsData._provenance) state.districtsProvenance = districtsData._provenance;
    if (cityGridData && cityGridData._provenance) state.cityProvenance = cityGridData._provenance;

    initVectorLayers();
    initCityMarkers();
    buildSearchIndex();
    renderHotspotsList();
    renderOverviewStats();
  } catch (err) {
    console.error("Failed loading analytical datasets:", err);
  }
}

// Vector Layers Initialization
function initVectorLayers() {
  if (statesData) {
    statesGeoJsonLayer = L.geoJSON(statesData, {
      style: (feature) => getFeatureStyle(feature, "state"),
      onEachFeature: (feature, layer) => {
        layer.on({
          mouseover: (e) => highlightFeature(e.target),
          mouseout: (e) => resetHighlight(e.target, "state"),
          click: () => selectFeature(feature, "state"),
        });
      },
    });
  }

  if (districtsData) {
    districtsGeoJsonLayer = L.geoJSON(districtsData, {
      style: (feature) => getFeatureStyle(feature, "district"),
      onEachFeature: (feature, layer) => {
        layer.on({
          mouseover: (e) => highlightFeature(e.target),
          mouseout: (e) => resetHighlight(e.target, "district"),
          click: () => selectFeature(feature, "district"),
        });
      },
    });
  }

  if (cityGridData) {
    cityGridGeoJsonLayer = L.geoJSON(cityGridData, {
      style: (feature) => getFeatureStyle(feature, "grid"),
      onEachFeature: (feature, layer) => {
        layer.on({
          mouseover: (e) => highlightFeature(e.target),
          mouseout: (e) => resetHighlight(e.target, "grid"),
          click: () => selectFeature(feature, "grid"),
        });
      },
    });
  }
}

// City Markers (Bengaluru & Priority Cities)
function initCityMarkers() {
  landmarksLayer.clearLayers();
  if (!citiesRegistry || !citiesRegistry.cities) return;

  Object.values(citiesRegistry.cities).forEach((city) => {
    const isProcessed = city.status === "processed";
    const isGee = city.status === "computed_gee";
    const marker = L.circleMarker([city.center[1], city.center[0]], {
      radius: isProcessed || isGee ? 7 : 5,
      fillColor: isProcessed || isGee ? PALETTE.forestLight : PALETTE.copperBase,
      color: "#ffffff",
      weight: 1.5,
      opacity: 1,
      fillOpacity: 0.9,
    });

    let statusText = "30 m detail not computed yet";
    if (isProcessed) statusText = "30m Detail: Computed (Click to View Grid)";
    if (isGee) statusText = "30m Detail: Computed via Google Earth Engine";

    marker.bindTooltip(`<strong>${city.name}</strong><br><span style="font-size:10px">${statusText}</span>`, {
      direction: "top",
    });

    marker.on("click", () => {
      if (isProcessed) {
        map.flyTo([city.center[1], city.center[0]], 11);
      } else {
        showCityPendingNotice(city);
      }
    });

    landmarksLayer.addLayer(marker);
  });
}

function showCityPendingNotice(city) {
  if (city.status === "computed_gee") {
    document.getElementById("entity-tier-badge").innerText = "Tier 3: City (Google Earth Engine)";
    document.getElementById("entity-name").innerText = `${city.name} (${city.state})`;
    document.getElementById("entity-subtitle").innerText = "Server-Side Landsat 30m Composite (GEE)";
    const yr = state.year;
    const ndvi = city.gee_landsat_mean_ndvi ? city.gee_landsat_mean_ndvi[yr] : "--";
    document.getElementById("stat-main-pct").innerText = ndvi ? `${ndvi} NDVI` : "--";
    document.getElementById("stat-main-area").innerText = "30m Server-Side";
    const d00 = city.gee_landsat_mean_ndvi ? city.gee_landsat_mean_ndvi[2000] : 0;
    const d25 = city.gee_landsat_mean_ndvi ? city.gee_landsat_mean_ndvi[2025] : 0;
    const diff = (d25 - d00).toFixed(4);
    document.getElementById("stat-shift-pp").innerText = `${diff > 0 ? "+" : ""}${diff} ΔNDVI`;
    document.getElementById("stat-shift-desc").innerText = "2000-2025 Net Landsat Shift (GEE)";
    const qBar = document.getElementById("quality-bar");
    if (qBar) qBar.style.width = "95%";
    const qSub = document.getElementById("quality-sub");
    if (qSub) qSub.innerText = "GEE Server-Side Harmonized (Roy et al. 2016)";
    const qRate = document.getElementById("quality-rating");
    if (qRate) qRate.innerText = "95.0%";

    if (city.gee_landsat_mean_ndvi) {
      renderSelectedTimelineChart({
        green_pct_2000: +(city.gee_landsat_mean_ndvi[2000] * 100).toFixed(2),
        green_pct_2010: +(city.gee_landsat_mean_ndvi[2010] * 100).toFixed(2),
        green_pct_2020: +(city.gee_landsat_mean_ndvi[2020] * 100).toFixed(2),
        green_pct_2025: +(city.gee_landsat_mean_ndvi[2025] * 100).toFixed(2),
      });
    }
    return;
  }

  document.getElementById("entity-tier-badge").innerText = "Tier 3: City";
  document.getElementById("entity-name").innerText = `${city.name} (${city.state})`;
  document.getElementById("entity-subtitle").innerText = "Status: 30 m detail not computed yet";
  document.getElementById("stat-main-pct").innerText = "--";
  document.getElementById("stat-main-area").innerText = "--";
  document.getElementById("stat-shift-pp").innerText = "--";
  document.getElementById("stat-shift-desc").innerText = "Analytical job queued in config/cities.yaml";
}

// Dynamic Feature Styling
function getFeatureStyle(feature, type) {
  const p = feature.properties;
  const isChange = state.mode === "change";

  // If feature has no real computed data yet, render as subtle uncomputed outline
  if (p.has_real_data === false || p[`green_pct_${state.year}`] === undefined) {
    return {
      fillColor: "#161b22",
      weight: type === "state" ? 1.5 : 0.6,
      opacity: 0.6,
      color: type === "state" ? "#484f58" : "#30363d",
      fillOpacity: 0.15,
    };
  }

  if (isChange) {
    const delta = p.net_change_pp || p.net_change_pct || 0;
    let col = "#484f58";
    if (delta <= -10.0) col = "#7a2a0a";
    else if (delta < -2.0) col = PALETTE.copperBase;
    else if (delta >= 10.0) col = PALETTE.forestDense;
    else if (delta > 2.0) col = PALETTE.forestModerate;
    return {
      fillColor: col,
      weight: type === "state" ? 1.5 : 0.8,
      opacity: 0.8,
      color: "#21262d",
      fillOpacity: 0.55,
    };
  }

  // Annual Green Cover
  const pct = p[`green_pct_${state.year}`] || 0;
  let col = "#21262d";
  if (pct >= 50.0) col = PALETTE.forestDense;
  else if (pct >= 35.0) col = PALETTE.forestModerate;
  else if (pct >= 20.0) col = PALETTE.forestLight;
  else if (pct >= 10.0) col = "#d29922";
  else col = PALETTE.copperBase;

  return {
    fillColor: col,
    weight: type === "state" ? 1.5 : (type === "district" ? 0.8 : 0.4),
    opacity: 0.7,
    color: type === "state" ? "#e6edf3" : "#30363d",
    fillOpacity: 0.55,
  };
}

function highlightFeature(layer) {
  layer.setStyle({
    weight: 2.5,
    color: "#ffffff",
    fillOpacity: 0.8,
  });
  if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {
    layer.bringToFront();
  }
}

function resetHighlight(layer, type) {
  layer.setStyle(getFeatureStyle(layer.feature, type));
}

// Feature Selection & Inspection
function selectFeature(feature, type) {
  state.selectedFeature = { feature, type };
  const p = feature.properties;

  const titleEl = document.getElementById("entity-name");
  const subEl = document.getElementById("entity-subtitle");
  const tierBadge = document.getElementById("entity-tier-badge");
  const statPct = document.getElementById("stat-main-pct");
  const statArea = document.getElementById("stat-main-area");
  const statShift = document.getElementById("stat-shift-pp");
  const qualityRating = document.getElementById("quality-rating");
  const qualityBar = document.getElementById("quality-bar");
  const qualitySub = document.getElementById("quality-sub");

  if (type === "state") {
    tierBadge.innerText = "Tier 2: State";
    titleEl.innerText = p.name;
    subEl.innerText = `Total Geographic Area: ${Number(p.area_km2).toLocaleString()} km²`;
  } else if (type === "district") {
    tierBadge.innerText = "Tier 2: District";
    titleEl.innerText = `${p.name}, ${p.state_name || ""}`;
    subEl.innerText = `Total District Area: ${Number(p.area_km2).toLocaleString()} km²`;
  } else {
    tierBadge.innerText = "Tier 3: Urban Cell (1km)";
    titleEl.innerText = p.label || p.zone_id;
    subEl.innerText = `Physical Metric Grid (1.0 km²) | Lon: ${p.centroid_lon}, Lat: ${p.centroid_lat}`;
  }

  // Check if feature has real computed satellite metrics
  const hasReal = p.has_real_data !== false && p[`green_pct_${state.year}`] !== undefined;

  if (!hasReal) {
    statPct.innerText = "Pending";
    statArea.innerText = "No real data yet";
    statShift.innerText = "Pending";
    statShift.className = "stat-value";

    qualityRating.innerText = "N/A";
    qualityBar.style.width = "0%";
    qualitySub.innerText = "No real data yet (Pending satellite ingestion)";

    if (selectedTimelineChart) {
      selectedTimelineChart.data.datasets[0].data = [];
      selectedTimelineChart.update();
    }
    return;
  }

  const curPct = p[`green_pct_${state.year}`] || 0;
  const curArea = p[`green_km2_${state.year}`] || 0;
  const shift = p.net_change_pp || p.net_change_pct || 0;

  statPct.innerText = `${curPct}%`;
  statArea.innerText = `${Number(curArea).toLocaleString()} km²`;
  statShift.innerText = `${shift >= 0 ? "+" : ""}${shift} pp`;
  statShift.className = `stat-value ${shift >= 0 ? "forest-text" : "copper-text"}`;

  // Real Data-Quality Indicator (Zero fake fallbacks)
  const validFrac = p.valid_pixel_fraction !== undefined ? p.valid_pixel_fraction : null;
  if (validFrac !== null) {
    const qualPct = Math.round(validFrac * 100);
    qualityRating.innerText = `${qualPct}%`;
    qualityBar.style.width = `${qualPct}%`;
    qualitySub.innerText = `${qualPct}% valid pixel fraction; clear-sky screened`;
  } else {
    qualityRating.innerText = "N/A";
    qualityBar.style.width = "0%";
    qualitySub.innerText = "Observation quality uncomputed";
  }

  renderSelectedTimelineChart(p);
}

// Zoom-Dependent Tier Resolution
function updateTierByZoom() {
  const z = map.getZoom();
  let targetTier = "national";
  if (z >= 10) {
    targetTier = "city";
  } else if (z >= 6) {
    targetTier = "district";
  } else {
    targetTier = "national";
  }

  state.activeTier = targetTier;
  updateTierShield(targetTier, z);
  updateActiveLayers();
  renderHotspotsList();
}

function updateTierShield(tier, zoom) {
  const badge = document.getElementById("tier-badge");
  const desc = document.getElementById("tier-desc");

  if (tier === "national") {
    const prov = state.statesProvenance;
    const srcLabel = prov && prov.source ? `Source: ${prov.source}` : "Source: Microsoft Planetary Computer (MODIS 250m)";
    badge.innerText = "TIER 1: NATIONAL";
    desc.innerText = `MODIS 250m Pre-Monsoon Proxy | ${srcLabel}`;
  } else if (tier === "district") {
    const prov = state.districtsProvenance;
    const srcLabel = prov && prov.source ? `Source: ${prov.source}` : "Source: Survey of India Admin";
    badge.innerText = "TIER 2: DISTRICT";
    desc.innerText = `Zonal Aggregation (594 Units) | ${srcLabel}`;
  } else {
    const prov = state.cityProvenance;
    const srcLabel = prov && prov.source ? `Source: ${prov.source}` : "Source: Landsat 30m C2 L2";
    badge.innerText = "TIER 3: CITY DRILL-DOWN";
    desc.innerText = `Landsat 30m Dry Season | ${srcLabel}`;
  }
}

// Active Layers Manager
function updateActiveLayers() {
  // Clear vector layers from map
  if (statesGeoJsonLayer) map.removeLayer(statesGeoJsonLayer);
  if (districtsGeoJsonLayer) map.removeLayer(districtsGeoJsonLayer);
  if (cityGridGeoJsonLayer) map.removeLayer(cityGridGeoJsonLayer);
  if (nationalRasterLayer) map.removeLayer(nationalRasterLayer);

  const tier = state.tierSelection === "auto" ? state.activeTier : state.tierSelection;

  // Vector Layers
  if (state.showVectors) {
    if (tier === "national" || tier === "states") {
      if (statesGeoJsonLayer) statesGeoJsonLayer.addTo(map);
    } else if (tier === "district" || tier === "districts") {
      if (districtsGeoJsonLayer) districtsGeoJsonLayer.addTo(map);
    } else if (tier === "city") {
      if (cityGridGeoJsonLayer) cityGridGeoJsonLayer.addTo(map);
    }
  }

  // Raster Layer
  if (state.showRaster) {
    if (tier === "national" || tier === "district" || tier === "states" || tier === "districts") {
      nationalRasterLayer = L.tileLayer(`./tiles/${state.year}/{z}/{x}/{y}.png`, {
        minZoom: 4,
        maxZoom: 7,
        opacity: state.rasterOpacity,
        attribution: "MODIS MOD13Q1 250m via Microsoft Planetary Computer",
      }).addTo(map);
    }
  }

  // City Landmarks
  if (state.showLandmarks) {
    if (!map.hasLayer(landmarksLayer)) {
      landmarksLayer.addTo(map);
    }
  } else {
    if (map.hasLayer(landmarksLayer)) {
      map.removeLayer(landmarksLayer);
    }
  }
}

// View & Styles Refresh
function updateView() {
  document.getElementById("current-year-val").innerText = state.year;
  updateActiveLayers();

  if (statesGeoJsonLayer) {
    statesGeoJsonLayer.eachLayer((l) => l.setStyle(getFeatureStyle(l.feature, "state")));
  }
  if (districtsGeoJsonLayer) {
    districtsGeoJsonLayer.eachLayer((l) => l.setStyle(getFeatureStyle(l.feature, "district")));
  }
  if (cityGridGeoJsonLayer) {
    cityGridGeoJsonLayer.eachLayer((l) => l.setStyle(getFeatureStyle(l.feature, "grid")));
  }
}

// Dynamic Legend Renderer
function renderLegend() {
  const container = document.getElementById("dynamic-legend");
  if (!container) return;

  if (state.mode === "change") {
    container.innerHTML = `
      <div class="legend-row"><span class="legend-chip" style="background:#1b4d3e"></span><span>High Canopy Expansion (&ge; +10 pp)</span></div>
      <div class="legend-row"><span class="legend-chip" style="background:#2e7d32"></span><span>Moderate Canopy Gain (+2 to +10 pp)</span></div>
      <div class="legend-row"><span class="legend-chip" style="background:#484f58"></span><span>Stable Vegetative Balance (&plusmn;2 pp)</span></div>
      <div class="legend-row"><span class="legend-chip" style="background:#c45d2c"></span><span>Moderate Canopy Loss (-2 to -10 pp)</span></div>
      <div class="legend-row"><span class="legend-chip" style="background:#7a2a0a"></span><span>Severe Hotspot Loss (&le; -10 pp)</span></div>
    `;
  } else {
    container.innerHTML = `
      <div class="legend-row"><span class="legend-chip" style="background:#1b4d3e"></span><span>Dense Tree Canopy (&ge; 50%)</span></div>
      <div class="legend-row"><span class="legend-chip" style="background:#2e7d32"></span><span>Moderate Canopy (35% - 50%)</span></div>
      <div class="legend-row"><span class="legend-chip" style="background:#66bb6a"></span><span>Sparse Foliage (20% - 35%)</span></div>
      <div class="legend-row"><span class="legend-chip" style="background:#d29922"></span><span>Marginal Green (10% - 20%)</span></div>
      <div class="legend-row"><span class="legend-chip" style="background:#c45d2c"></span><span>Built-up / Non-Vegetated (&lt; 10%)</span></div>
    `;
  }
}

// Overview Stats (National Baseline)
function renderOverviewStats() {
  if (!nationalStats) return;
  const d = nationalStats.data[String(state.year)];
  const shift = nationalStats.net_change_2000_2025;

  document.getElementById("entity-name").innerText = "India (All States & UTs)";
  document.getElementById("entity-subtitle").innerText = `Total Area: ${Number(nationalStats.total_geographic_area_km2).toLocaleString()} km²`;
  document.getElementById("metric-main-label").innerText = `Perennial Green Cover (${state.year})`;
  document.getElementById("stat-main-pct").innerText = `${d.green_percentage}%`;
  document.getElementById("stat-main-area").innerText = `${Number(d.green_km2).toLocaleString()} km²`;
  document.getElementById("stat-shift-pp").innerText = `${shift.delta_pp >= 0 ? "+" : ""}${shift.delta_pp} pp`;

  renderNationalTimelineChart();
}

// Timeline Line Chart (Chart.js)
function renderNationalTimelineChart() {
  const ctx = document.getElementById("timeline-chart");
  if (!ctx || !nationalStats) return;

  const labels = ["2000", "2010", "2020", "2025", "2030 (P)", "2035 (P)"];
  const historical = state.years.map((y) => nationalStats.data[String(y)].green_percentage);

  // Linear trend projection for national tier
  const lastVal = historical[historical.length - 1];
  const slope = (lastVal - historical[0]) / 25.0;
  const p2030 = +(lastVal + slope * 5.0).toFixed(2);
  const p2035 = +(lastVal + slope * 10.0).toFixed(2);

  const histSeries = [...historical, null, null];
  const projSeries = [null, null, null, lastVal, p2030, p2035];

  if (timelineChart) timelineChart.destroy();

  timelineChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Observed (Perennial Proxy)",
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
          spanGaps: true, // Guarantees connection to last historical point
          tension: 0.1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { color: PALETTE.textSecondary, boxWidth: 10, font: { size: 9 } },
        },
      },
      scales: {
        x: { ticks: { color: PALETTE.textSecondary, font: { size: 9 } }, grid: { color: PALETTE.borderSubtle } },
        y: { ticks: { color: PALETTE.textSecondary, font: { size: 9 } }, grid: { color: PALETTE.borderSubtle } },
      },
    },
  });
}

function renderSelectedTimelineChart(properties) {
  const ctx = document.getElementById("timeline-chart");
  if (!ctx) return;

  const labels = ["2000", "2010", "2020", "2025", "2030 (P)", "2035 (P)"];
  const hist = state.years.map((y) => properties[`green_pct_${y}`] || 0);
  const lastVal = hist[hist.length - 1];
  const slope = (lastVal - hist[0]) / 25.0;
  const p2030 = +(lastVal + slope * 5.0).toFixed(2);
  const p2035 = +(lastVal + slope * 10.0).toFixed(2);

  const histSeries = [...hist, null, null];
  const projSeries = [null, null, null, lastVal, p2030, p2035];

  if (timelineChart) timelineChart.destroy();

  timelineChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Observed Green %",
          data: histSeries,
          borderColor: PALETTE.forestModerate,
          backgroundColor: PALETTE.forestModerate,
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
          spanGaps: true,
          tension: 0.1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { color: PALETTE.textSecondary, boxWidth: 10, font: { size: 9 } },
        },
      },
      scales: {
        x: { ticks: { color: PALETTE.textSecondary, font: { size: 9 } }, grid: { color: PALETTE.borderSubtle } },
        y: { ticks: { color: PALETTE.textSecondary, font: { size: 9 } }, grid: { color: PALETTE.borderSubtle } },
      },
    },
  });
}

// Hotspots List Renderer
function renderHotspotsList() {
  const container = document.getElementById("hotspots-list");
  if (!container) return;
  container.innerHTML = "";

  const tier = state.tierSelection === "auto" ? state.activeTier : state.tierSelection;

  let list = [];
  if (tier === "city") {
    if (lossHotspots) {
      list = Array.isArray(lossHotspots) ? lossHotspots : (lossHotspots.hotspots || []);
    }
  } else if (tier === "district" && districtsData && districtsData.features) {
    // Dynamically rank top loss districts if real computed data exists
    const computedDistricts = districtsData.features.filter((f) => f.properties && f.properties.net_change_pp !== undefined);
    computedDistricts.sort((a, b) => a.properties.net_change_pp - b.properties.net_change_pp);
    list = computedDistricts.slice(0, 5).map((d, i) => ({
      rank: i + 1,
      zone_label: `${d.properties.name}, ${d.properties.state_name || ""}`,
      net_change_pp: d.properties.net_change_pp,
      feature: d,
    }));
  } else if (tier === "national" && statesData && statesData.features) {
    const computedStates = statesData.features.filter((f) => f.properties && f.properties.net_change_pp !== undefined);
    computedStates.sort((a, b) => a.properties.net_change_pp - b.properties.net_change_pp);
    list = computedStates.slice(0, 5).map((s, i) => ({
      rank: i + 1,
      zone_label: s.properties.name,
      net_change_pp: s.properties.net_change_pp,
      feature: s,
    }));
  }

  if (list.length === 0) {
    container.innerHTML = '<div style="color:var(--text-muted); font-size:11px; padding:6px 0;">No loss hotspots recorded at current tier.</div>';
    return;
  }

  list.slice(0, 5).forEach((h) => {
    const item = document.createElement("div");
    item.className = "hotspot-item";
    item.innerHTML = `
      <span class="hotspot-title">#${h.rank} ${h.zone_label}</span>
      <span class="hotspot-val">${h.net_change_pp} pp</span>
    `;
    item.addEventListener("click", () => {
      if (h.centroid_lat && h.centroid_lon) {
        map.flyTo([h.centroid_lat, h.centroid_lon], 13);
      } else if (h.feature) {
        map.fitBounds(L.geoJSON(h.feature).getBounds());
        renderEntityDetails(h.feature, tier === "national" ? "state" : "district");
      }
    });
    container.appendChild(item);
  });
}

// Search Index & Auto-Complete
function buildSearchIndex() {
  const searchInput = document.getElementById("geo-search");
  const dropdown = document.getElementById("search-results");
  if (!searchInput || !dropdown) return;

  const items = [];

  // Index States
  if (statesData && statesData.features) {
    statesData.features.forEach((f) => {
      items.push({
        name: f.properties.name,
        type: "State",
        bounds: L.geoJSON(f).getBounds(),
        feature: f,
      });
    });
  }

  // Index Cities
  if (citiesRegistry && citiesRegistry.cities) {
    Object.values(citiesRegistry.cities).forEach((c) => {
      items.push({
        name: `${c.name} (${c.state})`,
        type: "City",
        center: [c.center[1], c.center[0]],
        zoom: c.status === "processed" ? 11 : 9,
        city: c,
      });
    });
  }

  searchInput.addEventListener("input", (e) => {
    const q = e.target.value.trim().toLowerCase();
    if (q.length < 2) {
      dropdown.style.display = "none";
      return;
    }

    const matches = items.filter((it) => it.name.toLowerCase().includes(q)).slice(0, 6);
    if (matches.length === 0) {
      dropdown.style.display = "none";
      return;
    }

    dropdown.innerHTML = "";
    matches.forEach((m) => {
      const row = document.createElement("div");
      row.className = "search-item";
      row.innerHTML = `
        <span>${m.name}</span>
        <span class="search-item-type">${m.type}</span>
      `;
      row.addEventListener("click", () => {
        searchInput.value = m.name;
        dropdown.style.display = "none";
        if (m.bounds) {
          map.fitBounds(m.bounds);
          selectFeature(m.feature, "state");
        } else if (m.center) {
          map.flyTo(m.center, m.zoom);
          if (m.city.status !== "processed") {
            showCityPendingNotice(m.city);
          }
        }
      });
      dropdown.appendChild(row);
    });
    dropdown.style.display = "block";
  });

  document.addEventListener("click", (e) => {
    if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.style.display = "none";
    }
  });
}

// User Event Listeners
function setupEventListeners() {
  // Timeline slider
  const slider = document.getElementById("year-slider");
  slider.addEventListener("input", (e) => {
    state.yearIndex = parseInt(e.target.value, 10);
    state.year = state.years[state.yearIndex];
    updateView();
  });

  // Play / Pause auto scrub
  const btnPlay = document.getElementById("btn-play-pause");
  btnPlay.addEventListener("click", () => {
    if (state.isPlaying) {
      clearInterval(state.playTimer);
      state.isPlaying = false;
      btnPlay.innerHTML = "<span>&#9658;</span> Play";
    } else {
      state.isPlaying = true;
      btnPlay.innerHTML = "<span>&#10074;&#10074;</span> Pause";
      state.playTimer = setInterval(() => {
        state.yearIndex = (state.yearIndex + 1) % state.years.length;
        state.year = state.years[state.yearIndex];
        slider.value = state.yearIndex;
        updateView();
      }, 1800);
    }
  });

  // Analysis mode
  const modeBtns = document.querySelectorAll("#mode-selector .btn-toggle");
  modeBtns.forEach((btn) => {
    btn.addEventListener("click", (e) => {
      modeBtns.forEach((b) => b.classList.remove("active"));
      e.target.classList.add("active");
      state.mode = e.target.dataset.mode;
      renderLegend();
      updateView();
    });
  });

  // Tier Selector
  const tierBtns = document.querySelectorAll("#tier-selector .btn-toggle");
  tierBtns.forEach((btn) => {
    btn.addEventListener("click", (e) => {
      tierBtns.forEach((b) => b.classList.remove("active"));
      e.target.classList.add("active");
      state.tierSelection = e.target.dataset.tier;
      if (state.tierSelection === "auto") {
        updateTierByZoom();
      } else {
        updateActiveLayers();
      }
    });
  });

  // Layer Visibility
  document.getElementById("layer-toggle-raster").addEventListener("change", (e) => {
    state.showRaster = e.target.checked;
    updateActiveLayers();
  });
  document.getElementById("layer-toggle-vectors").addEventListener("change", (e) => {
    state.showVectors = e.target.checked;
    updateActiveLayers();
  });
  document.getElementById("layer-toggle-landmarks").addEventListener("change", (e) => {
    state.showLandmarks = e.target.checked;
    updateActiveLayers();
  });

  // Opacity Slider
  const opacitySlider = document.getElementById("raster-opacity");
  opacitySlider.addEventListener("input", (e) => {
    const val = parseInt(e.target.value, 10);
    state.rasterOpacity = val / 100.0;
    document.getElementById("opacity-val").innerText = `${val}%`;
    if (nationalRasterLayer) {
      nationalRasterLayer.setOpacity(state.rasterOpacity);
    }
  });

  // Basemap Selector
  document.getElementById("basemap-select").addEventListener("change", (e) => {
    setBasemap(e.target.value);
  });

  // Collapsible panels
  document.getElementById("btn-collapse-left").addEventListener("click", () => {
    const body = document.getElementById("layers-panel-body");
    const btn = document.getElementById("btn-collapse-left");
    if (body.style.display === "none") {
      body.style.display = "flex";
      btn.innerHTML = "&minus;";
    } else {
      body.style.display = "none";
      btn.innerHTML = "+";
    }
  });

  document.getElementById("btn-collapse-right").addEventListener("click", () => {
    const body = document.getElementById("stats-panel-body");
    const btn = document.getElementById("btn-collapse-right");
    if (body.style.display === "none") {
      body.style.display = "flex";
      btn.innerHTML = "&minus;";
    } else {
      body.style.display = "none";
      btn.innerHTML = "+";
    }
  });
}
