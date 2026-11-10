/**
 * India Urban & National Green Cover Intelligence System
 * Full-viewport multi-tier analytical dashboard (Leaflet + Chart.js).
 */

// Chart colours are read from the design tokens so the light and dark themes both work.
const token = (name, fallback) => {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
};

const PALETTE = {
  copperBase: token("--copper-base", "#c45d2c"),
  forestDense: token("--veg-5", "#1b4d3e"),
  forestModerate: token("--veg-3", "#2e7d32"),
  forestLight: token("--veg-1", "#66bb6a"),
  borderSubtle: token("--border-subtle", "#2d343f"),
  textPrimary: token("--text-primary", "#f0f6fc"),
  textSecondary: token("--text-secondary", "#9aa5b1"),
  textMuted: token("--text-muted", "#6e7681"),
};

const BASEMAP_PROVIDERS = {
  esri_dark: {
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
    options: {
      attribution: "Tiles &copy; Esri, HERE, Garmin, &copy; OpenStreetMap contributors",
      maxZoom: 16,
      noWrap: true,
    },
    labels: {
      url: "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}",
      options: { maxZoom: 16, noWrap: true, pane: "shadowPane" },
    },
  },
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
    getUrl: () => {
      const key = getCartoKey();
      return key
        ? `https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}.png?key=${encodeURIComponent(key)}`
        : "";
    },
    options: {
      attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
      subdomains: "abcd",
      maxZoom: 19,
    },
  },
  carto_voyager_keyed: {
    getUrl: () => {
      const key = getCartoKey();
      return key
        ? `https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png?key=${encodeURIComponent(key)}`
        : "";
    },
    options: {
      attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
      subdomains: "abcd",
      maxZoom: 19,
    },
  },
};

function getCartoKey() {
  if (typeof __CARTO_KEY__ !== "undefined" && __CARTO_KEY__) {
    return __CARTO_KEY__;
  }
  try {
    return localStorage.getItem("carto_api_key") || "";
  } catch (e) {
    return "";
  }
}

// Application State
const state = {
  year: 2025,
  yearIndex: 3,
  years: [2000, 2010, 2020, 2025],
  mode: "annual", // "annual" | "change"
  tierSelection: "auto", // "auto" | "states" | "districts" | "city"
  activeTier: "national", // "national" | "district" | "city"
  basemapKey: "esri_dark",
  showRaster: false,
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
  initTooltips();
  await loadDatasets();
  updateTierByZoom();
  renderLegend();
  updateView();
});

// Initialize Leaflet Map
function initMap() {
  // Frame India, not the whole subcontinent
  map = L.map("map", {
    center: [22.5937, 78.9629],
    zoom: 5,
    minZoom: 4,
    maxZoom: 16,
    zoomControl: false,
    noWrap: true,
    worldCopyJump: false,
    maxBounds: [[2.5, 64.0], [40.5, 101.5]],
    maxBoundsViscosity: 0.85,
  });

  L.control.zoom({ position: "topright" }).addTo(map);

  setBasemap(state.basemapKey);

  landmarksLayer = L.layerGroup().addTo(map);

  map.fitBounds([[6.6, 68.0], [37.2, 97.4]], { padding: [0, 0], animate: false });

  map.on("zoomend", () => {
    if (state.tierSelection === "auto") {
      updateTierByZoom();
    }
  });
}

// Basemap Management
let currentBasemapLabels = null;

function setBasemap(providerKey) {
  if (currentBasemapLayer) {
    map.removeLayer(currentBasemapLayer);
    currentBasemapLayer = null;
  }
  if (currentBasemapLabels) {
    map.removeLayer(currentBasemapLabels);
    currentBasemapLabels = null;
  }
  let provider = BASEMAP_PROVIDERS[providerKey] || BASEMAP_PROVIDERS.osm_standard;
  let url = typeof provider.getUrl === "function" ? provider.getUrl() : provider.url;

  if (!url && providerKey && providerKey.startsWith("carto_")) {
    const inputKey = prompt(
      "CARTO Basemaps API key required.\nEnter your CARTO API key to unlock official licensed tiles (or cancel to fall back):",
      ""
    );
    if (inputKey && inputKey.trim()) {
      try {
        localStorage.setItem("carto_api_key", inputKey.trim());
      } catch (e) {}
      url = provider.getUrl();
    }
  }

  if (!url) {
    console.warn(`Basemap ${providerKey} requires an API key. Falling back to the keyless dark canvas.`);
    provider = BASEMAP_PROVIDERS.esri_dark;
    url = provider.url;
    const select = document.getElementById("basemap-select");
    if (select) select.value = "esri_dark";
    state.basemapKey = "esri_dark";
  } else {
    state.basemapKey = providerKey;
  }

  currentBasemapLayer = L.tileLayer(url, provider.options).addTo(map);

  // Place labels ride above the base canvas but below the choropleth
  if (provider.labels) {
    currentBasemapLabels = L.tileLayer(provider.labels.url, provider.labels.options);
    currentBasemapLabels.addTo(map);
    if (currentBasemapLabels.bringToFront) currentBasemapLabels.bringToFront();
  }
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
    applyNationalMetricCopy();
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
  state.activeCityPending = city;
  state.selectedFeature = null;

  const panelTitle = document.getElementById("stats-panel-title");
  if (panelTitle) {
    panelTitle.innerText = `City: ${city.name}`;
  }

  if (city.status === "computed_gee") {
    document.getElementById("entity-tier-badge").innerText = "Tier 3: City (Google Earth Engine)";
    document.getElementById("entity-name").innerText = `${city.name} (${city.state})`;
    document.getElementById("entity-subtitle").innerText = "Server-Side Landsat 30m Composite (GEE)";

    const metricMainEl = document.getElementById("metric-main-label");
    if (metricMainEl) {
      metricMainEl.innerText = `Landsat 30m NDVI (${state.year})`;
    }

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
    const qSub = document.getElementById("quality-sub");
    const qRate = document.getElementById("quality-rating");
    qRate.innerText = "n/a";
    qBar.style.width = "0%";
    qSub.innerText = "Data-quality indicator: n/a for GEE city aggregate";

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

  const metricMainEl = document.getElementById("metric-main-label");
  if (metricMainEl) {
    metricMainEl.innerText = "30 m detail not computed yet";
  }

  document.getElementById("stat-main-pct").innerText = "--";
  document.getElementById("stat-main-area").innerText = "--";
  document.getElementById("stat-shift-pp").innerText = "--";
  document.getElementById("stat-shift-desc").innerText = "Analytical job queued in config/cities.yaml";

  const qBar = document.getElementById("quality-bar");
  const qSub = document.getElementById("quality-sub");
  const qRate = document.getElementById("quality-rating");
  qRate.innerText = "n/a";
  qBar.style.width = "0%";
  qSub.innerText = "Data-quality indicator: n/a";
}

// Dynamic Feature Styling
const VEG_RAMP = [0, 1, 2, 3, 4, 5].map((i) => token(`--veg-${i}`, "#2f4a38"));
const CHANGE_RAMP = {
  lossStrong: token("--chg-loss-2", "#c25a24"),
  loss: token("--chg-loss-1", "#8f3d19"),
  neutral: token("--chg-0", "#2b323b"),
  gain: token("--chg-gain-1", "#2f7d52"),
  gainStrong: token("--chg-gain-2", "#46a874"),
};

function getFeatureStyle(feature, type) {
  const p = feature.properties;
  const isChange = state.mode === "change";
  const isState = type === "state";

  // If feature has no real computed data yet, render as subtle uncomputed outline
  if (p.has_real_data === false || p[`green_pct_${state.year}`] === undefined) {
    return {
      fillColor: "#161b22",
      weight: isState ? 0.9 : 0.4,
      opacity: 0.5,
      color: "#39414d",
      fillOpacity: 0.25,
    };
  }

  if (isChange) {
    const delta = p.net_change_pp || p.net_change_pct || 0;
    let col = CHANGE_RAMP.neutral;
    if (delta <= -10.0) col = CHANGE_RAMP.lossStrong;
    else if (delta < -2.0) col = CHANGE_RAMP.loss;
    else if (delta >= 10.0) col = CHANGE_RAMP.gainStrong;
    else if (delta > 2.0) col = CHANGE_RAMP.gain;
    return {
      fillColor: col,
      weight: isState ? 0.9 : 0.45,
      opacity: 0.85,
      color: "#0f1319",
      fillOpacity: 0.78,
    };
  }

  // Annual green cover
  const pct = p[`green_pct_${state.year}`] || 0;
  let idx = 0;
  if (pct >= 50.0) idx = 5;
  else if (pct >= 35.0) idx = 4;
  else if (pct >= 20.0) idx = 3;
  else if (pct >= 10.0) idx = 2;
  else if (pct >= 5.0) idx = 1;

  return {
    fillColor: VEG_RAMP[idx],
    weight: isState ? 0.9 : 0.45,
    opacity: 0.85,
    color: "#0f1319",
    fillOpacity: 0.82,
  };
}

function highlightFeature(layer) {
  layer.setStyle({
    weight: 1.8,
    color: "#e88d5d",
    fillOpacity: 0.95,
  });
  if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {
    layer.bringToFront();
  }
}

function resetHighlight(layer, type) {
  layer.setStyle(getFeatureStyle(layer.feature, type));
}

// Feature Selection & Inspection
function selectFeature(feature, type, updateChart = true) {
  state.selectedFeature = { feature, type };
  state.activeCityPending = null;
  const p = feature.properties;

  const panelTitle = document.getElementById("stats-panel-title");
  const titleEl = document.getElementById("entity-name");
  const subEl = document.getElementById("entity-subtitle");
  const tierBadge = document.getElementById("entity-tier-badge");
  const metricLabelEl = document.getElementById("metric-main-label");
  const statPct = document.getElementById("stat-main-pct");
  const statArea = document.getElementById("stat-main-area");
  const statShift = document.getElementById("stat-shift-pp");
  const qualityRating = document.getElementById("quality-rating");
  const qualityBar = document.getElementById("quality-bar");
  const qualitySub = document.getElementById("quality-sub");

  const isCity = type === "grid" || type === "city";
  const metricName = isCity
    ? ((state.cityProvenance && state.cityProvenance.metric_definition) || "Green cover (Landsat 30 m, Jan-Mar NDVI)")
    : ((state.statesProvenance && state.statesProvenance.metric_definition) || "Pre-monsoon vegetation greenness (MODIS 250 m)");

  if (panelTitle) {
    if (type === "state") {
      panelTitle.innerText = `State: ${p.name}`;
    } else if (type === "district") {
      panelTitle.innerText = `District: ${p.name}`;
    } else {
      panelTitle.innerText = `City cell ${p.label || p.zone_id}`;
    }
  }

  if (metricLabelEl) {
    metricLabelEl.innerText = `${metricName} (${state.year})`;
  }

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

    qualityRating.innerText = "n/a";
    qualityBar.style.width = "0%";
    qualitySub.innerText = "No real data yet (Pending satellite ingestion)";

    if (selectedTimelineChart && updateChart) {
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

  // Real Data-Quality Indicator (Zero fake fallbacks, never 100% when uncomputed)
  const validFrac = (p.valid_pixel_fraction !== undefined && p.valid_pixel_fraction !== null) ? p.valid_pixel_fraction : null;
  if (validFrac !== null && validFrac > 0) {
    const qualPct = Math.round(validFrac * 100);
    qualityRating.innerText = `${qualPct}%`;
    qualityBar.style.width = `${qualPct}%`;
    qualitySub.innerText = `${qualPct}% valid pixel fraction; clear-sky screened`;
  } else {
    qualityRating.innerText = "n/a";
    qualityBar.style.width = "0%";
    qualitySub.innerText = "Observation quality n/a for this selection";
  }

  if (updateChart) {
    renderSelectedTimelineChart(p);
  }

  renderAnalysisReport(p, type);
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
  const timelineMetric = document.getElementById("timeline-metric-name");

  if (tier === "national") {
    const prov = state.statesProvenance;
    const srcLabel = prov && prov.source ? `Source: ${prov.source}` : "Source: Microsoft Planetary Computer (MODIS 250m)";
    badge.innerText = "TIER 1: NATIONAL";
    desc.innerText = `MODIS 250 m, pre-monsoon greenness | ${srcLabel}`;
    if (timelineMetric) {
      const metricDef = (prov && prov.metric_definition) || "Pre-monsoon vegetation greenness (MODIS 250 m)";
      timelineMetric.innerText = `National Metric: ${metricDef}`;
    }
  } else if (tier === "district") {
    const prov = state.districtsProvenance;
    const srcLabel = prov && prov.source ? `Source: ${prov.source}` : "Source: Survey of India Admin";
    badge.innerText = "TIER 2: DISTRICT";
    desc.innerText = `Zonal Aggregation (594 Units) | ${srcLabel}`;
    if (timelineMetric) {
      const metricDef = (prov && prov.metric_definition) || "Pre-monsoon vegetation greenness (MODIS 250 m)";
      timelineMetric.innerText = `District Metric: ${metricDef}`;
    }
  } else {
    const prov = state.cityProvenance;
    const srcLabel = prov && prov.source ? `Source: ${prov.source}` : "Source: Landsat 30m C2 L2";
    badge.innerText = "TIER 3: CITY DRILL-DOWN";
    desc.innerText = `Landsat 30m Dry Season | ${srcLabel}`;
    if (timelineMetric) {
      const metricDef = (prov && prov.metric_definition) || "Green cover (Landsat 30 m, Jan-Mar NDVI)";
      timelineMetric.innerText = `City Metric: ${metricDef}`;
    }
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

  // Update right stats panel according to current year and selection
  if (state.selectedFeature) {
    selectFeature(state.selectedFeature.feature, state.selectedFeature.type, false);
  } else if (state.activeCityPending) {
    showCityPendingNotice(state.activeCityPending);
  } else {
    renderOverviewStats();
  }

  renderLegend();
  renderHotspotsList();
}

// Dynamic Legend Renderer
function renderLegend() {
  const container = document.getElementById("dynamic-legend");
  if (!container) return;

  const tier = state.tierSelection === "auto" ? state.activeTier : state.tierSelection;
  const isCity = tier === "city";

  const row = (color, text) =>
    `<div class="legend-row"><span class="legend-chip" style="background:${color}"></span><span>${text}</span></div>`;

  if (state.mode === "change") {
    const noun = isCity ? "canopy" : "greenness";
    container.innerHTML = `
      <div class="legend-ramp is-change" aria-hidden="true"></div>
      ${row("var(--chg-gain-2)", `Gain of ${noun}, 10 pp or more`)}
      ${row("var(--chg-gain-1)", "Gain, 2 to 10 pp")}
      ${row("var(--chg-0)", "Broadly unchanged, within 2 pp")}
      ${row("var(--chg-loss-1)", "Loss, 2 to 10 pp")}
      ${row("var(--chg-loss-2)", "Loss of 10 pp or more")}
      <div class="legend-note">Net shift 2000 to 2025, in percentage points of the affected area.</div>
    `;
  } else {
    const metricTitle = isCity
      ? "Green cover, Landsat 30 m, Jan to Mar NDVI"
      : "Pre-monsoon vegetation greenness, MODIS 250 m";
    const labels = isCity
      ? ["Dense canopy", "Moderate canopy", "Sparse foliage", "Marginal green", "Scattered green", "Built-up or bare"]
      : ["Very high greenness", "High greenness", "Moderate greenness", "Low greenness", "Sparse greenness", "Bare or built-up"];
    const ranges = ["50% and above", "35 to 50%", "20 to 35%", "10 to 20%", "5 to 10%", "below 5%"];
    const colors = ["var(--veg-5)", "var(--veg-4)", "var(--veg-3)", "var(--veg-2)", "var(--veg-1)", "var(--veg-0)"];

    container.innerHTML = `
      <div class="legend-ramp" aria-hidden="true"></div>
      <div class="legend-note" style="margin: 0 0 var(--space-2);">${metricTitle}</div>
      ${labels.map((l, i) => row(colors[i], `${l}, ${ranges[i]}`)).join("")}
    `;
  }
}

// Metric copy comes from the provenance manifest, never from hardcoded strings.
function applyNationalMetricCopy() {
  const label = (nationalStats && nationalStats.metric_label) || "Pre-monsoon vegetation greenness (MODIS 250 m)";
  const caveat = (nationalStats && nationalStats.metric_caveat) || "";

  const tag = document.getElementById("national-metric-tag");
  if (tag) tag.innerText = `National metric: ${label}`;

  const note = document.getElementById("national-metric-note");
  if (note) {
    note.setAttribute(
      "data-tooltip",
      caveat
        ? `${label}. ${caveat}`
        : `${label}. Measured in the pre-monsoon window so winter crops in the north do not read as tree cover.`
    );
  }
}

// Overview Stats (National Baseline)
function renderOverviewStats() {
  if (!nationalStats) return;
  const d = nationalStats.data[String(state.year)];
  const shift = nationalStats.net_change_2000_2025;

  const panelTitle = document.getElementById("stats-panel-title");
  const tier = state.tierSelection === "auto" ? state.activeTier : state.tierSelection;
  if (panelTitle) {
    if (tier === "city") panelTitle.innerText = "City Overview: Bengaluru";
    else if (tier === "district") panelTitle.innerText = "District Level Overview";
    else panelTitle.innerText = "India National Overview";
  }

  const cityLabel = (state.cityProvenance && (state.cityProvenance.metric_label || state.cityProvenance.metric_definition))
    || "Green cover (Landsat 30 m, Jan to Mar NDVI)";
  const natLabel = (state.statesProvenance && (state.statesProvenance.metric_label || state.statesProvenance.metric_definition))
    || "Pre-monsoon vegetation greenness (MODIS 250 m)";
  const metricName = tier === "city" ? cityLabel : natLabel;

  const tierBadgeMap = {
    city: "Tier 3: City (Landsat 30 m)",
    district: "Tier 2: District (MODIS 250 m)",
    national: "Tier 1: National (MODIS 250 m)",
    states: "Tier 1: National (MODIS 250 m)",
  };
  document.getElementById("entity-tier-badge").innerText = tierBadgeMap[tier] || tierBadgeMap.national;
  document.getElementById("entity-name").innerText = tier === "city" ? "Bengaluru Urban Region" : "India (All States & UTs)";
  document.getElementById("entity-subtitle").innerText = tier === "city"
    ? "Total Grid Area: 1,078 km² | 1,120 Metric Cells"
    : `Total Area: ${Number(nationalStats.total_geographic_area_km2).toLocaleString()} km²`;

  const metricMainEl = document.getElementById("metric-main-label");
  if (metricMainEl) {
    metricMainEl.innerText = `${metricName} (${state.year})`;
  }

  document.getElementById("stat-main-pct").innerText = `${d.green_percentage}%`;
  document.getElementById("stat-main-area").innerText = `${Number(d.green_km2).toLocaleString()} km²`;
  document.getElementById("stat-shift-pp").innerText = `${shift.delta_pp >= 0 ? "+" : ""}${shift.delta_pp} pp`;

  // Quality indicator for overview
  const qualityRating = document.getElementById("quality-rating");
  const qualityBar = document.getElementById("quality-bar");
  const qualitySub = document.getElementById("quality-sub");
  if (nationalStats && nationalStats.valid_pixel_fraction !== undefined) {
    const qualPct = Math.round(nationalStats.valid_pixel_fraction * 100);
    qualityRating.innerText = `${qualPct}%`;
    qualityBar.style.width = `${qualPct}%`;
    qualitySub.innerText = `${qualPct}% valid pixel fraction; clear-sky screened`;
  } else {
    qualityRating.innerText = "n/a";
    qualityBar.style.width = "0%";
    qualitySub.innerText = "Data-quality indicator: n/a for national aggregation";
  }

  renderNationalTimelineChart();
}

// Timeline Line Chart (Chart.js)
function renderNationalTimelineChart() {
  const ctx = document.getElementById("timeline-chart");
  if (!ctx || !nationalStats) return;

  const tier = state.tierSelection === "auto" ? state.activeTier : state.tierSelection;
  const isCity = tier === "city";

  const labels = ["2000", "2010", "2020", "2025", "2030 (P)", "2035 (P)"];
  const historical = state.years.map((y) => nationalStats.data[String(y)].green_percentage);

  // Linear trend projection for national tier
  const lastVal = historical[historical.length - 1];
  const slope = (lastVal - historical[0]) / 25.0;
  const p2030 = +(lastVal + slope * 5.0).toFixed(2);
  const p2035 = +(lastVal + slope * 10.0).toFixed(2);

  const histSeries = [...historical, null, null];
  const projSeries = [null, null, null, lastVal, p2030, p2035];

  // Threshold-free cross-check. Green share depends on a hard NDVI cut, so the
  // median NDVI is plotted beside it: if the two disagree, the share move is partly a cut artifact.
  const ndvi = isCity
    ? null
    : state.years.map((y) => {
        const v = nationalStats.data[String(y)];
        return v && typeof v.median_ndvi === "number" ? v.median_ndvi : null;
      });
  const hasNdvi = !!ndvi && ndvi.every((v) => v !== null);

  const datasets = [
    {
      label: isCity ? "Observed canopy share" : "Observed greenness share (%)",
      data: histSeries,
      borderColor: PALETTE.forestDense,
      backgroundColor: PALETTE.forestDense,
      borderWidth: 2,
      pointRadius: 4,
      tension: 0.1,
    },
    {
      label: "Projected trend",
      data: projSeries,
      borderColor: PALETTE.copperBase,
      backgroundColor: PALETTE.copperBase,
      borderDash: [4, 4],
      borderWidth: 2,
      pointRadius: 4,
      spanGaps: true, // Guarantees connection to last historical point
      tension: 0.1,
    },
  ];

  if (hasNdvi) {
    datasets.push({
      label: "Median NDVI (right axis)",
      data: [...ndvi, null, null],
      borderColor: PALETTE.textMuted,
      backgroundColor: PALETTE.textMuted,
      borderWidth: 1.5,
      borderDash: [2, 3],
      pointRadius: 3,
      tension: 0.1,
      yAxisID: "y1",
    });
  }

  if (timelineChart) timelineChart.destroy();

  timelineChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: datasets,
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
        y1: hasNdvi
          ? {
              position: "right",
              display: true,
              ticks: { color: PALETTE.textMuted, font: { size: 9 } },
              grid: { display: false },
            }
          : undefined,
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
// Ranked by absolute green area lost (km2), which is threshold-stable, rather than
// by percentage points, which explode on small units near the NDVI cut.
const HOTSPOT_MIN_AREA_KM2 = 500;

function _districtHotspots() {
  if (!districtsData || !districtsData.features) return [];
  return districtsData.features
    .filter((f) => {
      const p = f.properties || {};
      return p.has_real_data !== false
        && typeof p.net_change_km2 === "number"
        && p.net_change_km2 < 0
        && (p.area_km2 || 0) >= HOTSPOT_MIN_AREA_KM2;
    })
    .sort((a, b) => a.properties.net_change_km2 - b.properties.net_change_km2)
    .slice(0, 5)
    .map((f, i) => ({
      rank: i + 1,
      label: `${f.properties.name}, ${f.properties.state_name || ""}`.replace(/, $/, ""),
      value: `${Math.abs(f.properties.net_change_km2).toFixed(0)} km2`,
      detail: `${Number(f.properties.net_change_pp).toFixed(1)} pp`,
      feature: f,
    }));
}

function _cityHotspots() {
  if (!lossHotspots) return [];
  const raw = Array.isArray(lossHotspots) ? lossHotspots : (lossHotspots.hotspots || []);
  return raw
    .filter((h) => {
      const v = h.net_change_pp !== undefined ? h.net_change_pp : h.net_change_pct;
      return typeof v === "number" && v < 0;
    })
    .sort((a, b) => {
      const va = a.net_change_pp !== undefined ? a.net_change_pp : a.net_change_pct;
      const vb = b.net_change_pp !== undefined ? b.net_change_pp : b.net_change_pct;
      return va - vb;
    })
    .slice(0, 5)
    .map((h, i) => ({
      rank: i + 1,
      label: h.zone_label || h.label || h.zone_id || `Cell ${i + 1}`,
      value: `${Number(h.net_change_pp !== undefined ? h.net_change_pp : h.net_change_pct).toFixed(1)} pp`,
      detail: "",
      zone_id: h.zone_id,
      centroid_lat: h.centroid_lat,
      centroid_lon: h.centroid_lon,
    }));
}

// Analysis Report Generator
function renderAnalysisReport(properties, type) {
  const section = document.getElementById("analysis-report-section");
  const body = document.getElementById("analysis-report-body");
  const recList = document.getElementById("recommendations-list");
  if (!section || !body || !recList) return;

  const isCity = type === "grid" || type === "city";
  const hasReal = properties.has_real_data !== false && properties[`green_pct_${state.year}`] !== undefined;

  // Show analysis report only for city grid cells with real data
  if (!isCity || !hasReal) {
    section.style.display = "none";
    return;
  }

  section.style.display = "block";

  const curPct = properties[`green_pct_${state.year}`] || 0;
  const curArea = properties[`green_km2_${state.year}`] || 0;
  const shift = properties.net_change_pp || properties.net_change_pct || 0;
  const med2000 = properties.green_pct_2000 || 0;
  const med2025 = properties.green_pct_2025 || 0;

  const currentPctEl = document.getElementById("ar-current-pct");
  const gapEl = document.getElementById("ar-gap");
  const trendEl = document.getElementById("ar-trend");

  if (currentPctEl) currentPctEl.innerText = `${curPct}%`;
  if (gapEl) {
    const gap = Math.max(0, 40.0 - curPct).toFixed(1);
    gapEl.innerText = `${gap} pp`;
  }
  if (trendEl) {
    const dir = shift >= 0 ? "Increasing" : "Decreasing";
    trendEl.innerText = `${dir} (${shift >= 0 ? "+" : ""}${shift} pp)`;
  }

  // Generate recommendations
  const recs = generateRecommendations(properties, curPct, shift, med2000, med2025);
  recList.innerHTML = "";
  recs.forEach((rec) => {
    const item = document.createElement("div");
    item.className = "recommendation-item";
    item.innerHTML = `<div class="rec-title">${rec.title}</div><span class="rec-priority ${rec.priority}">${rec.priority}</span>${rec.text}`;
    recList.appendChild(item);
  });
}

function generateRecommendations(properties, curPct, shift, med2000, med2025) {
  const recs = [];

  if (curPct < 10) {
    recs.push({
      title: "Critical: Low canopy cover",
      priority: "high",
      text: "This cell has very low vegetation. Priority intervention: plant native shade trees along roads and in vacant lots. Target 15-20% cover within 3 years.",
    });
  } else if (curPct < 25) {
    recs.push({
      title: "Moderate: Room for growth",
      priority: "medium",
      text: "Canopy is present but below the 40% dense threshold. Infill planting in gaps and roadside verges can raise cover. Consider Miyawaki-style dense planting.",
    });
  } else if (curPct < 40) {
    recs.push({
      title: "Good: Approaching dense canopy",
      priority: "low",
      text: "Near the 40% dense threshold. Focus on protecting existing canopy and replacing invasive species with native trees.",
    });
  } else {
    recs.push({
      title: "Excellent: Dense canopy maintained",
      priority: "low",
      text: "This cell exceeds the 40% dense canopy threshold. Priority: protect existing green cover from conversion and monitor for fragmentation.",
    });
  }

  if (shift < -10) {
    recs.push({
      title: "Severe loss detected",
      priority: "high",
      text: "Green cover dropped more than 10 percentage points since 2000. Investigate causes: construction, road widening, or land conversion. Enforce tree protection ordinances.",
    });
  } else if (shift < -2) {
    recs.push({
      title: "Moderate decline",
      priority: "medium",
      text: "Gradual canopy loss detected. Review development permits and ensure compensatory planting requirements are met.",
    });
  } else if (shift > 10) {
    recs.push({
      title: "Strong recovery",
      priority: "low",
      text: "Significant green cover gain. Document successful interventions (afforestation, park development) for replication in other cells.",
    });
  }

  const ndvi2025 = properties.green_pct_2025 || 0;
  const ndvi2000 = properties.green_pct_2000 || 0;
  if (ndvi2025 > ndvi2000 + 5) {
    recs.push({
      title: "Positive trajectory",
      priority: "low",
      text: "Cover has increased since 2000. Continue current management practices and monitor for fragmentation.",
    });
  }

  // Data quality note
  const validFrac = properties.valid_pixel_fraction;
  if (validFrac && validFrac < 0.8) {
    recs.push({
      title: "Data quality note",
      priority: "medium",
      text: "Observation quality is below 80%. Recommendations are based on limited clear-sky observations; verify with ground survey.",
    });
  }

  if (recs.length === 0) {
    recs.push({
      title: "No specific recommendations",
      priority: "low",
      text: "Cell metrics are within normal ranges. Continue routine monitoring.",
    });
  }

  return recs;
}

function renderHotspotsList() {
  const container = document.getElementById("hotspots-list");
  if (!container) return;
  container.innerHTML = "";

  const tier = state.tierSelection === "auto" ? state.activeTier : state.tierSelection;
  const isCity = tier === "city";
  const list = isCity ? _cityHotspots() : _districtHotspots();

  const title = document.getElementById("hotspots-title");
  if (title) title.innerText = isCity ? "Largest 1 km cell losses" : "Largest district losses";

  const note = document.getElementById("hotspots-note");
  if (note) {
    note.innerText = isCity
      ? "Ranked by percentage-point decline, Bengaluru 30 m Landsat, 2000 to 2025."
      : `Ranked by square kilometres lost, 2000 to 2025. Units under ${HOTSPOT_MIN_AREA_KM2} km2 excluded.`;
  }

  if (list.length === 0) {
    container.innerHTML = '<div class="hotspots-empty">No real loss data at this level yet.</div>';
    return;
  }

  list.forEach((h) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "hotspot-item";
    item.setAttribute("role", "listitem");
    item.innerHTML = `
      <span class="hotspot-title">#${h.rank} ${h.label}</span>
      <span class="hotspot-val">${h.value}${h.detail ? `<em>${h.detail}</em>` : ""}</span>
    `;
    item.addEventListener("click", () => {
      if (h.zone_id && h.centroid_lat && h.centroid_lon) {
        map.flyTo([h.centroid_lat, h.centroid_lon], 13);
        if (cityGridData && cityGridData.features) {
          const match = cityGridData.features.find((f) => f.properties && f.properties.zone_id === h.zone_id);
          if (match) selectFeature(match, "grid");
        }
      } else if (h.feature) {
        map.fitBounds(L.geoJSON(h.feature).getBounds(), { padding: [40, 40] });
        selectFeature(h.feature, isCity ? "grid" : "district");
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

// Accessible Tooltip Positioning & Event Handler
function initTooltips() {
  const tooltipEl = document.getElementById("app-tooltip");
  if (!tooltipEl) return;

  let activeTrigger = null;

  function showTooltip(target, text) {
    if (!text) return;
    activeTrigger = target;
    tooltipEl.textContent = text;
    tooltipEl.classList.add("visible");
    tooltipEl.setAttribute("aria-hidden", "false");

    const rect = target.getBoundingClientRect();
    const tooltipRect = tooltipEl.getBoundingClientRect();
    const padding = 12;

    // Prefer positioning below or above depending on viewport space
    let top = rect.bottom + 6;
    let left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);

    // If bottom overflow, show above
    if (top + tooltipRect.height > window.innerHeight - padding) {
      top = rect.top - tooltipRect.height - 6;
    }

    // Clamp horizontal position within viewport
    left = Math.max(padding, Math.min(left, window.innerWidth - tooltipRect.width - padding));

    tooltipEl.style.top = `${Math.round(top)}px`;
    tooltipEl.style.left = `${Math.round(left)}px`;
  }

  function hideTooltip() {
    activeTrigger = null;
    tooltipEl.classList.remove("visible");
    tooltipEl.setAttribute("aria-hidden", "true");
  }

  document.addEventListener("mouseover", (e) => {
    const trigger = e.target.closest("[data-tooltip]");
    if (trigger) {
      showTooltip(trigger, trigger.getAttribute("data-tooltip"));
    }
  });

  document.addEventListener("mouseout", (e) => {
    const trigger = e.target.closest("[data-tooltip]");
    if (trigger && trigger === activeTrigger) {
      hideTooltip();
    }
  });

  document.addEventListener("focusin", (e) => {
    const trigger = e.target.closest("[data-tooltip]");
    if (trigger) {
      showTooltip(trigger, trigger.getAttribute("data-tooltip"));
    }
  });

  document.addEventListener("focusout", (e) => {
    const trigger = e.target.closest("[data-tooltip]");
    if (trigger && trigger === activeTrigger) {
      hideTooltip();
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      hideTooltip();
    }
  });
}
