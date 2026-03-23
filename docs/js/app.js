(function () {
  "use strict";

  const API = window.API_BASE || "";
  let map = null;
  let dischargeLayer = null;
  let noaaLayer = null;
  let sensorsLayer = null;
  let chartDischarge = null;
  let dischargeData = null;
  let noaaStations = [];

  /** Format station ID as 8-digit text (e.g. 1108000 -> "01108000") */
  function formatStationIdDisplay(id) {
    if (id == null || id === "") return "";
    const s = String(id).trim();
    if (!s) return "";
    return s.padStart(8, "0");
  }

  function get(id) {
    return document.getElementById(id);
  }

  function showPanel(content, options) {
    options = options || {};
    get("panel-placeholder").classList.add("hidden");
    get("panel-content").classList.remove("hidden");
    if (content) {
      get("point-title").textContent = content.name || "Station";
      const meta = options.meta;
      const metaEl = get("point-meta");
      if (meta !== undefined) {
        metaEl.innerHTML = meta;
      } else {
        metaEl.textContent = "";
      }
    }
  }

  function hidePanel() {
    get("panel-placeholder").classList.remove("hidden");
    get("panel-content").classList.add("hidden");
  }

  function destroyCharts() {
    if (chartDischarge) { chartDischarge.destroy(); chartDischarge = null; }
  }

  /* Chart rules: white bg, x 2010–2025, year labels 2yr, station ID in title, same size, y-axis aligned */
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    layout: { padding: { top: 4, right: 8, bottom: 16, left: 8 } },
    plugins: { legend: { display: false } },
    scales: {
      x: {
        ticks: { maxTicksLimit: 10, color: "#333", font: { size: 10 } },
        grid: { color: "#e0e0e0" },
        type: "time",
        time: { unit: "year", stepSize: 2, displayFormats: { year: "yyyy", month: "yyyy" } },
        min: "2010-01-01",
        max: "2025-12-31",
      },
      y: {
        ticks: { color: "#333", font: { size: 10 } },
        grid: { color: "#e0e0e0" },
        title: { display: false },
        minWidth: 48,
      },
    },
  };

  function drawDischargeChart(dischargeDataArr, stationIdDisplay) {
    destroyCharts();
    var arr = dischargeDataArr || [];
    if (arr.length === 0) return;
    var canvas = get("chart-discharge");
    if (!canvas) return;
    var ctx = canvas.getContext("2d");
    if (!ctx) return;

    var dataPoints = arr.map(function (d) {
      return { x: d.date, y: d.value != null ? d.value : null };
    });
    var titleText = stationIdDisplay
      ? "Discharge (cfs) — Station " + stationIdDisplay
      : "Discharge (cfs)";

    var opts = Object.assign({}, chartOptions, {
      scales: Object.assign({}, chartOptions.scales, {
        x: Object.assign({}, chartOptions.scales.x, { min: "2010-01-01", max: "2025-12-31" }),
        y: Object.assign({}, chartOptions.scales.y, { min: 0 }),
      }),
    });

    try {
      chartDischarge = new Chart(ctx, {
        type: "line",
        data: {
          datasets: [{
            label: "Discharge",
            data: dataPoints,
            borderColor: "#3fb950",
            backgroundColor: "rgba(63, 185, 80, 0.1)",
            fill: true,
            tension: 0.1,
            borderWidth: 2.5,
          }],
        },
        options: opts,
      });
      requestAnimationFrame(function () {
        if (chartDischarge) chartDischarge.resize();
      });
    } catch (err) {
      console.error("Chart error:", err);
      var meta = get("point-meta");
      if (meta) meta.textContent = (meta.textContent || "") + " Chart failed to draw.";
    }
  }

  function stationDisplayLabel(s) {
    const id = String(s.id || "");
    const idDisplay = formatStationIdDisplay(id);
    const rawName = (s.name && String(s.name).trim()) ? String(s.name).trim() : "";
    const name = rawName
      ? rawName.toLowerCase().replace(/\b([a-z])/g, function (_, c) { return c.toUpperCase(); })
      : "";
    if (name && name !== id) {
      return name + " (" + idDisplay + ")";
    }
    return idDisplay || "—";
  }

  /** VTEC PNG uses raw id for NOAA (7-digit) and padded for USGS (8-digit) */
  function vtecImageId(stationId) {
    const s = String(stationId).trim();
    if (/^\d{7}$/.test(s) && parseInt(s, 10) >= 8000000) return s;
    return formatStationIdDisplay(stationId);
  }

  function updateVtecFigure(stationId) {
    const wrap = get("vtec-figure-wrap");
    const img = get("vtec-figure");
    const noData = get("vtec-no-data");
    if (!wrap || !img || !noData) return;
    wrap.classList.remove("hidden");
    if (!stationId) {
      img.removeAttribute("src");
      img.classList.add("hidden");
      noData.classList.remove("hidden");
      return;
    }
    const idForVtec = vtecImageId(stationId);
    const base = getBasePath();
    img.onload = function () { img.classList.remove("hidden"); noData.classList.add("hidden"); };
    img.onerror = function () {
      img.removeAttribute("src");
      img.classList.add("hidden");
      noData.classList.remove("hidden");
    };
    img.classList.add("hidden");
    img.src = base + "images/vtec/vtec_timeline_" + idForVtec + ".png";
    var vtecTitleEl = get("vtec-title");
    if (vtecTitleEl) vtecTitleEl.textContent = "VTEC — Station " + idForVtec;
  }

  function usgsStationUrl(stationId) {
    var id8 = formatStationIdDisplay(stationId);
    if (!id8) return null;
    return "https://waterdata.usgs.gov/monitoring-location/USGS-" + id8 + "/#dataTypeId=continuous-00060-0&period=P7D&showFieldMeasurements=true";
  }

  function getBasePath() {
    var path = location.pathname || "";
    if (path && path !== "/" && path !== "/index.html") {
      var segs = path.split("/").filter(Boolean);
      if (segs.length > 0) return "/" + segs[0] + "/";
    }
    return "";
  }

  function updateWaterLevelFigureForStation(noaaId) {
    var wrap = get("water-level-wrap");
    var img = get("water-level-figure");
    var noData = get("water-level-no-data");
    if (!wrap || !img || !noData) return;
    wrap.classList.remove("hidden");
    if (!noaaId) {
      img.removeAttribute("src");
      img.classList.add("hidden");
      noData.classList.remove("hidden");
      return;
    }
    var base = getBasePath();
    img.onload = function () { img.classList.remove("hidden"); noData.classList.add("hidden"); };
    img.onerror = function () {
      img.removeAttribute("src");
      img.classList.add("hidden");
      noData.classList.remove("hidden");
    };
    img.classList.add("hidden");
    img.src = base + "images/noaa/" + noaaId + "_water_level_with_predictions.png";
    var titleEl = get("water-level-title");
    if (titleEl) titleEl.textContent = "Water level (m MLLW) — Station " + noaaId;
  }

  // Only include products we want to show on the GitHub Pages UI
  var MET_PRODUCTS = ["air_pressure", "air_temperature", "water_temperature"];
  var MET_TITLES = { air_pressure: "Air pressure", air_temperature: "Air temperature", water_temperature: "Water temperature" };

  function updateMetProductFigure(noaaId, product) {
    var wrap = get(product + "-wrap");
    var img = get(product + "-figure");
    var noData = get(product + "-no-data");
    var titleEl = get(product + "-title");
    if (!wrap || !img || !noData) return;
    wrap.classList.remove("hidden");
    if (!noaaId) {
      img.removeAttribute("src");
      img.classList.add("hidden");
      noData.classList.remove("hidden");
      return;
    }
    var base = getBasePath();
    img.onload = function () { img.classList.remove("hidden"); noData.classList.add("hidden"); };
    img.onerror = function () {
      img.removeAttribute("src");
      img.classList.add("hidden");
      noData.classList.remove("hidden");
    };
    img.classList.add("hidden");
    img.src = base + "images/noaa/" + noaaId + "_" + product + ".png";
    if (titleEl) titleEl.textContent = (MET_TITLES[product] || product) + " — Station " + noaaId;
  }

  function updatePrecipitationFigure(noaaId) {
    var wrap = get("precipitation-wrap");
    var img = get("precipitation-figure");
    var noData = get("precipitation-no-data");
    if (!wrap || !img || !noData) return;
    wrap.classList.remove("hidden");
    if (!noaaId) {
      img.removeAttribute("src");
      img.classList.add("hidden");
      noData.classList.remove("hidden");
      return;
    }
    var base = getBasePath();
    img.onload = function () { img.classList.remove("hidden"); noData.classList.add("hidden"); };
    img.onerror = function () {
      img.removeAttribute("src");
      img.classList.add("hidden");
      noData.classList.remove("hidden");
    };
    img.classList.add("hidden");
    img.src = base + "images/noaa/precipitation_" + noaaId + ".png";
    var titleEl = get("precipitation-title");
    if (titleEl) titleEl.textContent = "Precipitation (mm/day) — Station " + noaaId;
  }

  function updatePrecipitationFigureForUsgs(stationId) {
    var wrap = get("precipitation-wrap");
    var img = get("precipitation-figure");
    var noData = get("precipitation-no-data");
    if (!wrap || !img || !noData) return;
    wrap.classList.remove("hidden");
    if (!stationId) {
      img.removeAttribute("src");
      img.classList.add("hidden");
      noData.classList.remove("hidden");
      return;
    }
    var id8 = formatStationIdDisplay(stationId);
    var base = getBasePath();
    img.onload = function () { img.classList.remove("hidden"); noData.classList.add("hidden"); };
    img.onerror = function () {
      img.removeAttribute("src");
      img.classList.add("hidden");
      noData.classList.remove("hidden");
    };
    img.classList.add("hidden");
    img.src = base + "images/pr/precipitation_" + id8 + ".png";
    var titleEl = get("precipitation-title");
    if (titleEl) titleEl.textContent = "Precipitation (mm/day) — Station " + id8;
  }

  function sensorImageSlug(name) {
    var n = name == null ? "" : String(name).trim();
    if (!n) return "sensor";
    var parts = n.split(/\s+/).filter(function (x) { return x; });
    var cleaned = [];
    for (var i = 0; i < parts.length && cleaned.length < 3; i++) {
      var tok = parts[i].replace(/[^A-Za-z0-9]+/g, "");
      if (tok) cleaned.push(tok.toLowerCase());
    }
    return cleaned.length > 0 ? cleaned.join("_") : "sensor";
  }

  function updatePrecipitationFigureForSensor(sensor, sensorIndex) {
    var wrap = get("precipitation-wrap");
    var img = get("precipitation-figure");
    var noData = get("precipitation-no-data");
    if (!wrap || !img || !noData) return;
    wrap.classList.remove("hidden");
    if (sensorIndex == null || sensorIndex < 0) {
      img.removeAttribute("src");
      img.classList.add("hidden");
      noData.classList.remove("hidden");
      return;
    }
    var base = getBasePath();
    img.onload = function () { img.classList.remove("hidden"); noData.classList.add("hidden"); };
    img.onerror = function () {
      img.removeAttribute("src");
      img.classList.add("hidden");
      noData.classList.remove("hidden");
    };
    img.classList.add("hidden");
    var slug = sensorImageSlug(sensor && sensor.name ? sensor.name : null);
    img.src = base + "images/sensors/precipitation_sensor_" + slug + "_" + String(sensorIndex) + ".png";
    var titleEl = get("precipitation-title");
    var sensorName = (sensor && sensor.name) ? String(sensor.name) : ("Sensor " + (sensorIndex + 1));
    if (titleEl) titleEl.textContent = "Precipitation (mm/day) — " + sensorName;
  }

  function loadNoaaStation(s) {
    var sensorsSelect = get("sensors-select");
    if (sensorsSelect) sensorsSelect.value = "";
    get("discharge-select").value = "";
    var meta = (s && s.lat != null && s.lon != null)
      ? "Lat " + Number(s.lat).toFixed(4) + "°, Lon " + Number(s.lon).toFixed(4) + "° — NOAA tide/water level"
      : "NOAA tide/water level station";
    if (s && s.url) meta += ' <a href="' + s.url + '" target="_blank" rel="noopener">View on NOAA Tides & Currents</a>';
    var label = (s && s.name && s.name.trim()) ? s.name + " (" + (s.id || "") + ")" : (s ? s.id : "NOAA station");
    showPanel({ name: label }, { meta: meta });
    get("discharge-chart-wrap").classList.add("hidden");
    get("vtec-figure-wrap").classList.remove("hidden");
    get("water-level-wrap").classList.remove("hidden");
    MET_PRODUCTS.forEach(function (p) { get(p + "-wrap") && get(p + "-wrap").classList.remove("hidden"); });
    get("precipitation-wrap").classList.remove("hidden");
    destroyCharts();
    updateVtecFigure(s && s.id ? s.id : null);
    updateWaterLevelFigureForStation(s && s.id ? s.id : null);
    MET_PRODUCTS.forEach(function (p) { updateMetProductFigure(s && s.id ? s.id : null, p); });
    updatePrecipitationFigure(s && s.id ? s.id : null);
  }

  function loadSensorStation(sensor, sensorIndex) {
    var sensorsSelect = get("sensors-select");
    if (sensorsSelect) sensorsSelect.value = sensorIndex != null ? String(sensorIndex) : "";
    get("discharge-select").value = "";
    get("noaa-select").value = "";

    var name = (sensor && sensor.name) ? String(sensor.name) : "Sensor";
    var meta = "";
    if (sensor && sensor.lat != null && sensor.lon != null) {
      meta = "Lat " + Number(sensor.lat).toFixed(4) + "°, Lon " + Number(sensor.lon).toFixed(4) + "°";
    }
    if (sensor && sensor.sensorType) {
      meta = (meta ? (meta + " — ") : "") + "Type: " + String(sensor.sensorType);
    }
    showPanel({ name: name }, { meta: meta });

    // Hide all chart/image sections for sensors (no plots wired yet)
    var dischargeWrap = get("discharge-chart-wrap");
    if (dischargeWrap) dischargeWrap.classList.add("hidden");
    var vtecWrap = get("vtec-figure-wrap");
    if (vtecWrap) vtecWrap.classList.add("hidden");
    var waterWrap = get("water-level-wrap");
    if (waterWrap) waterWrap.classList.add("hidden");
    MET_PRODUCTS.forEach(function (p) {
      var w = get(p + "-wrap");
      if (w) w.classList.add("hidden");
    });
    var prWrap = get("precipitation-wrap");
    if (prWrap) prWrap.classList.remove("hidden");
    updatePrecipitationFigureForSensor(sensor, sensorIndex);
    destroyCharts();
  }

  function loadDischargeStation(stationId, lat, lon, displayName) {
    var sensorsSelect = get("sensors-select");
    if (sensorsSelect) sensorsSelect.value = "";
    get("noaa-select").value = "";
    get("discharge-select").value = stationId || "";
    get("discharge-chart-wrap").classList.remove("hidden");
    get("vtec-figure-wrap").classList.remove("hidden");
    var waterWrap = get("water-level-wrap");
    if (waterWrap) {
      waterWrap.classList.add("hidden");
      var waterImg = get("water-level-figure");
      if (waterImg) waterImg.src = "";
    }
    MET_PRODUCTS.forEach(function (p) {
      var w = get(p + "-wrap");
      if (w) { w.classList.add("hidden"); var img = get(p + "-figure"); if (img) img.removeAttribute("src"); }
    });
    get("precipitation-wrap").classList.remove("hidden");
    updatePrecipitationFigureForUsgs(stationId);
    var meta = (lat != null && lon != null)
      ? "Lat " + Number(lat).toFixed(4) + "°, Lon " + Number(lon).toFixed(4) + "°"
      : "Discharge station";
    var usgsUrl = usgsStationUrl(stationId);
    if (usgsUrl) meta += ' <a href="' + usgsUrl + '" target="_blank" rel="noopener">View on USGS Water Data</a>';
    var idDisplay = formatStationIdDisplay(stationId);
    var title = displayName ? displayName + " (" + idDisplay + ")" : idDisplay;
    showPanel({ name: title }, { meta: meta });
    var chartTitleEl = get("discharge-chart-title");
    if (chartTitleEl) chartTitleEl.textContent = "Discharge (cfs, Cubic feet per second) — Station " + idDisplay;
    updateVtecFigure(stationId);

    if (!dischargeData || !dischargeData.series) {
      get("point-meta").textContent = "No discharge data available.";
      destroyCharts();
      return;
    }
    var series = dischargeData.series[stationId] || dischargeData.series[String(stationId)];
    if (!series) {
      var keys = Object.keys(dischargeData.series || {});
      for (var i = 0; i < keys.length; i++) {
        if (String(keys[i]) === String(stationId)) {
          series = dischargeData.series[keys[i]];
          break;
        }
      }
    }
    if (!series || series.length === 0) {
      get("point-meta").textContent = meta + " — No time series data.";
      destroyCharts();
      return;
    }
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        drawDischargeChart(series, idDisplay);
      });
    });
  }

  async function loadDischargeData() {
    if (dischargeData) return dischargeData;
    if (API) {
      try {
        const res = await fetch(API + "/api/discharge/stations?_=" + Date.now());
        if (res.ok) {
          const geojson = await res.json();
          const stations = [];
          (geojson.features || []).forEach((f) => {
            const sid = f.id || f.properties?.id;
            const name = f.properties?.name || f.properties?.staname || sid;
            const coords = f.geometry && f.geometry.coordinates;
            stations.push({
              id: String(sid || ""),
              name: name ? String(name) : sid,
              lat: coords ? coords[1] : null,
              lon: coords ? coords[0] : null,
            });
          });
          dischargeData = { stations, series: {} };
          return dischargeData;
        }
      } catch (e) {
        console.warn("Backend not available, loading static data:", e.message);
      }
    }
    var base = "";
    var path = location.pathname || "";
    if (path && path !== "/" && path !== "/index.html") {
      var segs = path.split("/").filter(Boolean);
      if (segs.length > 0) base = "/" + segs[0] + "/";
    }
    var dataUrl = base + "data/discharge_data.json";
    try {
      var res = await fetch(dataUrl);
      if (!res.ok) throw new Error(res.statusText);
      dischargeData = await res.json();
      return dischargeData;
    } catch (e) {
      console.error("Failed to load discharge data:", e);
      document.getElementById("api-error-banner").classList.remove("hidden");
      return { stations: [], series: {} };
    }
  }

  async function loadJsonData(name) {
    var base = "";
    var path = location.pathname || "";
    if (path && path !== "/" && path !== "/index.html") {
      var segs = path.split("/").filter(Boolean);
      if (segs.length > 0) base = "/" + segs[0] + "/";
    }
    try {
      var res = await fetch(base + "data/" + name + ".json");
      if (!res.ok) return null;
      return await res.json();
    } catch (e) {
      return null;
    }
  }

  async function loadNoaaStations() {
    if (noaaStations.length > 0) return noaaStations;
    var base = getBasePath();
    var dataUrl = base + "data/noaa_stations.json";
    try {
      var res = await fetch(dataUrl);
      if (!res.ok) return [];
      var data = await res.json();
      noaaStations = data.stations || [];
      return noaaStations;
    } catch (e) {
      console.warn("Failed to load NOAA stations:", e);
      return [];
    }
  }

  async function fetchStationSeries(stationId) {
    if (dischargeData && dischargeData.series) {
      const s = dischargeData.series[stationId] || dischargeData.series[String(stationId)];
      if (s && s.length > 0) return s;
    }
    if (API) {
      try {
        const res = await fetch(API + "/api/discharge/station/" + encodeURIComponent(stationId) + "?limit=50000");
        if (res.ok) {
          const d = await res.json();
          return d.discharge || [];
        }
      } catch (e) {
        console.warn("API station fetch failed:", e.message);
      }
    }
    return [];
  }

  async function loadSensors() {
    var base = getBasePath();
    var dataUrl = base + "data/sensors_data.json";
    try {
      var res = await fetch(dataUrl);
      if (!res.ok) return [];
      var data = await res.json();
      return data.sensors || [];
    } catch (e) {
      console.warn("Failed to load sensors:", e);
      return [];
    }
  }

  function sleep(ms) {
    return new Promise(function (resolve) { setTimeout(resolve, ms); });
  }

  async function flashMarker(marker, opts) {
    if (!marker) return;
    var flashTimes = (opts && opts.times != null) ? opts.times : 3;
    var flashRadius = (opts && opts.flashRadius != null) ? opts.flashRadius : 14;
    var onDurationMs = (opts && opts.onDurationMs != null) ? opts.onDurationMs : 140;
    var offDurationMs = (opts && opts.offDurationMs != null) ? opts.offDurationMs : 120;

    // Leaflet circleMarker: keep the original look and temporarily "pulse" it.
    var originalRadius = marker.options && marker.options.radius != null ? marker.options.radius : 6;
    var originalFillOpacity = marker.options && marker.options.fillOpacity != null ? marker.options.fillOpacity : 0.9;
    var originalWeight = marker.options && marker.options.weight != null ? marker.options.weight : 1;

    marker.bringToFront && marker.bringToFront();
    for (var i = 0; i < flashTimes; i++) {
      marker.setRadius(flashRadius);
      marker.setStyle({ fillOpacity: 1, weight: originalWeight });
      await sleep(onDurationMs);
      marker.setRadius(originalRadius);
      marker.setStyle({ fillOpacity: originalFillOpacity, weight: originalWeight });
      await sleep(offDurationMs);
    }
  }

  async function initMap() {
    const center = [41.75, -71.5];
    map = L.map("map").setView(center, 8);
    L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}", {
      attribution: "Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ",
      maxZoom: 18,
    }).addTo(map);

    // Scale bar (metric only). Leaflet will automatically switch units as zoom changes.
    L.control.scale({
      position: "bottomleft",
      metric: true,
      imperial: false,
      maxWidth: 200,
    }).addTo(map);

    dischargeLayer = L.layerGroup().addTo(map);
    noaaLayer = L.layerGroup().addTo(map);
    sensorsLayer = L.layerGroup().addTo(map);

    var noaaMarkersById = new Map();
    var sensorMarkersByIndex = new Map();
    var usgsMarkersById = new Map();

    const noaaList = await loadNoaaStations();
    noaaList.forEach(function (s) {
      if (s.lat == null || s.lon == null) return;
      const label = (s.name && s.name.trim()) ? s.name + " (" + (s.id || "") + ")" : (s.id || "NOAA");
      const marker = L.circleMarker([s.lat, s.lon], {
        radius: 6,
        fillColor: "#58a6ff",
        color: "#388bfd",
        weight: 1,
        fillOpacity: 0.9,
      });
      var latText = Number(s.lat).toFixed(4);
      var lonText = Number(s.lon).toFixed(4);
      var nameText = (s.name && s.name.trim()) ? s.name.trim() : String(s.id || "NOAA");
      var idText = s.id != null ? String(s.id) : "";
      marker.bindTooltip(
        "NOAA station<br>" + nameText + " — Lat " + latText + ", Lon " + lonText + " (ID: " + idText + ")",
        { permanent: false }
      );
      if (s.id != null) noaaMarkersById.set(String(s.id), marker);
      marker.on("click", function () {
        get("discharge-select").value = "";
        get("noaa-select").value = s ? s.id : "";
        loadNoaaStation(s);
      });
      noaaLayer.addLayer(marker);
    });

    var sensorsList = await loadSensors();
    var sensorsSelect = get("sensors-select");
    if (sensorsSelect) {
      sensorsList.forEach(function (s, idx) {
        var opt = document.createElement("option");
        opt.value = String(idx);
        var name = (s && s.name) ? String(s.name) : ("Sensor " + (idx + 1));
        var st = (s && s.sensorType) ? String(s.sensorType) : "";
        opt.textContent = st ? (name + " — " + st) : name;
        sensorsSelect.appendChild(opt);
      });
      sensorsSelect.addEventListener("change", function () {
        var v = this.value;
        if (v === "") return;
        var idx = parseInt(v, 10);
        if (!Number.isFinite(idx) || idx < 0 || idx >= sensorsList.length) return;
        loadSensorStation(sensorsList[idx], idx);
        flashMarker(sensorMarkersByIndex.get(idx));
      });
    }
    sensorsList.forEach(function (s, idx) {
      if (s.lat == null || s.lon == null) return;
      var marker = L.circleMarker([s.lat, s.lon], {
        radius: 6,
        fillColor: "#f0883e",
        color: "#c76b22",
        weight: 1,
        fillOpacity: 0.9,
      });
      var latText = Number(s.lat).toFixed(4);
      var lonText = Number(s.lon).toFixed(4);
      var nameText = (s.name && s.name.trim()) ? s.name.trim() : "Sensor";
      marker.bindTooltip(
        "Sensor<br>" + nameText + " — Lat " + latText + ", Lon " + lonText + " (ID: " + String(idx) + ")",
        { permanent: false }
      );
      marker.on("click", function () {
        loadSensorStation(s, idx);
        if (sensorsSelect) sensorsSelect.value = String(idx);
      });
      sensorsLayer.addLayer(marker);
      sensorMarkersByIndex.set(idx, marker);
    });

    var legend = L.control({ position: "bottomright" });
    legend.onAdd = function () {
      var div = L.DomUtil.create("div", "map-legend");
      div.innerHTML =
        "<strong>Legend</strong><br>" +
        "<span class='legend-item'><span class='legend-swatch' style='background:#3fb950;border-color:#2ea043'></span> USGS stations</span><br>" +
        "<span class='legend-item'><span class='legend-swatch' style='background:#58a6ff;border-color:#388bfd'></span> NOAA stations</span><br>" +
        "<span class='legend-item'><span class='legend-swatch' style='background:#f0883e;border-color:#c76b22'></span> Sensors</span>";
      return div;
    };
    legend.addTo(map);

    const dischargeSelect = get("discharge-select");
    const stations = dischargeData ? dischargeData.stations : [];
    const allStationIds = new Set();

    stations.forEach((s) => {
      const sid = s.id;
      const name = s.name || sid;
      const label = stationDisplayLabel(s);
      if (s.lat != null && s.lon != null) {
        const marker = L.circleMarker([s.lat, s.lon], {
          radius: 6,
          fillColor: "#3fb950",
          color: "#2ea043",
          weight: 1,
          fillOpacity: 0.9,
        });
        // Green markers represent USGS discharge stations; show USGS identity on hover.
        var idDisplay = formatStationIdDisplay(String(sid));
        var latText = Number(s.lat).toFixed(4);
        var lonText = Number(s.lon).toFixed(4);
        var nameText = (s.name && String(s.name).trim()) ? String(s.name).trim() : String(sid);
        marker.bindTooltip(
          "USGS station<br>" + nameText + " — Lat " + latText + ", Lon " + lonText + " (ID: " + idDisplay + ")",
          { permanent: false }
        );
        usgsMarkersById.set(String(sid), marker);
        marker.on("click", async function () {
          get("discharge-select").value = sid;
          get("noaa-select").value = "";
          loadDischargeStation(sid, s.lat, s.lon, name !== sid ? name : null);
          var series = await fetchStationSeries(sid);
          if (series.length > 0) drawDischargeChart(series, formatStationIdDisplay(sid));
        });
        dischargeLayer.addLayer(marker);
      }
      if (sid && !allStationIds.has(sid)) {
        allStationIds.add(sid);
        const opt = document.createElement("option");
        opt.value = sid;
        opt.textContent = label;
        opt.dataset.displayName = name !== sid ? name : "";
        dischargeSelect.appendChild(opt);
      }
    });

    dischargeSelect.addEventListener("change", async function () {
      var v = this.value;
      if (!v) return;
      get("noaa-select").value = "";
      flashMarker(usgsMarkersById.get(String(v)));
      var opt = this.options[this.selectedIndex];
      var displayName = opt && opt.dataset.displayName ? opt.dataset.displayName : null;
      var s = stations.find(function (st) { return st.id === v; });
      loadDischargeStation(v, s ? s.lat : null, s ? s.lon : null, displayName || null);
      var series = await fetchStationSeries(v);
      if (series.length > 0) drawDischargeChart(series, formatStationIdDisplay(v));
    });

    var noaaSelect = get("noaa-select");
    if (noaaSelect) {
      noaaList.forEach(function (s) {
        var label = (s.name && s.name.trim()) ? s.name + " (" + (s.id || "") + ")" : (s.id || "NOAA");
        var opt = document.createElement("option");
        opt.value = s.id || "";
        opt.textContent = label;
        noaaSelect.appendChild(opt);
      });
      noaaSelect.addEventListener("change", function () {
        var v = this.value;
        if (!v) return;
        get("discharge-select").value = "";
        flashMarker(noaaMarkersById.get(String(v)));
        var s = noaaList.find(function (st) { return String(st.id) === String(v); });
        if (s) loadNoaaStation(s);
      });
    }
  }

  async function init() {
    dischargeData = await loadDischargeData();
    if (dischargeData && dischargeData.stations && dischargeData.stations.length > 0) {
      document.getElementById("api-error-banner").classList.add("hidden");
    }
    await initMap();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
