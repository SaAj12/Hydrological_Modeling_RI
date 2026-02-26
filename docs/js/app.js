(function () {
  "use strict";

  const API = window.API_BASE || "";
  let map = null;
  let dischargeLayer = null;
  let noaaLayer = null;
  let chartDischarge = null;
  let chartWaterLevel = null;
  let chartPrecipitation = null;
  let chartMeteorological = null;
  let chartVtec = null;
  let dischargeData = null;
  let waterLevelData = { series: {} };
  let precipitationData = { series: {} };
  let meteorologicalData = { series: {} };
  let vtecData = { series: {}, warning_order: [] };
  let noaaStations = [];
  let stormsData = { storms: [] };

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
    [chartDischarge, chartWaterLevel, chartPrecipitation, chartMeteorological, chartVtec].forEach(function (c) {
      if (c) { c.destroy(); }
    });
    chartDischarge = chartWaterLevel = chartPrecipitation = chartMeteorological = chartVtec = null;
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

  function buildStormAnnotations(storms, yBarTop, yBarBottom) {
    const annotations = {};
    (storms || []).forEach(function (s, i) {
      const id = "storm_" + (s.id || i);
      annotations[id] = {
        type: "box",
        xMin: s.startDate,
        xMax: s.endDate,
        yMin: yBarBottom,
        yMax: yBarTop,
        backgroundColor: "rgba(0, 0, 0, 0.12)",
        borderColor: "rgba(0, 0, 0, 0.25)",
        borderWidth: 1,
      };
    });
    return annotations;
  }

  function drawDischargeChart(dischargeDataArr, stationIdDisplay) {
    var selectedStormId = (get("storm-select") && get("storm-select").value) || "";
    destroyCharts();
    var arr = dischargeDataArr || [];
    if (arr.length === 0) return;
    var canvas = get("chart-discharge");
    if (!canvas) return;
    var ctx = canvas.getContext("2d");
    if (!ctx) return;

    var storms = stormsData.storms || [];
    var selectedStorm = selectedStormId
      ? storms.find(function (s) { return s.id === selectedStormId; })
      : null;

    if (selectedStorm) {
      var startD = selectedStorm.startDate;
      var endD = selectedStorm.endDate;
      arr = arr.filter(function (d) {
        var dStr = (d.date || "").substring(0, 10);
        return dStr >= startD && dStr <= endD;
      });
      if (arr.length === 0) arr = dischargeDataArr || [];
    }

    var dataPoints = arr.map(function (d) {
      return { x: d.date, y: d.value != null ? d.value : null };
    });
    var yMaxVal = 0;
    dataPoints.forEach(function (p) {
      if (p.y != null && p.y > yMaxVal) yMaxVal = p.y;
    });
    if (yMaxVal <= 0) yMaxVal = 100;
    var yBarTop = yMaxVal * 1.05;
    var yBarBottom = yMaxVal * 0.88;

    var titleText = stationIdDisplay
      ? "Discharge (cfs) — Station " + stationIdDisplay
      : "Discharge (cfs)";
    if (selectedStorm) {
      titleText += " — " + selectedStorm.displayLabel;
    }

    var xScaleOpts = { min: "2010-01-01", max: "2025-12-31" };
    if (selectedStorm) {
      xScaleOpts.min = selectedStorm.startDate;
      xScaleOpts.max = selectedStorm.endDate;
    }

    var annotations = buildStormAnnotations(storms, yBarTop, yBarBottom);

    var opts = Object.assign({}, chartOptions, {
      plugins: Object.assign({}, chartOptions.plugins, {
        annotation: {
          annotations: annotations,
        },
      }),
      scales: Object.assign({}, chartOptions.scales, {
        x: Object.assign({}, chartOptions.scales.x, xScaleOpts),
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
    const name = (s.name && String(s.name).trim()) ? String(s.name).trim() : "";
    if (name && name !== id) {
      return name + " (" + idDisplay + ")";
    }
    return idDisplay || "—";
  }

  /** VTEC image uses raw id for NOAA (7-digit, e.g. 8444069) and padded for USGS (8-digit, e.g. 01108000) */
  function vtecImageId(stationId) {
    const s = String(stationId).trim();
    if (/^\d{7}$/.test(s) && parseInt(s, 10) >= 8000000) return s;  // NOAA tide station ids
    return formatStationIdDisplay(stationId);
  }

  function updateVtecFigure(stationId) {
    const wrap = get("vtec-figure-wrap");
    const canvas = get("chart-vtec");
    const noData = get("vtec-no-data");
    if (!wrap || !canvas || !noData) return;
    wrap.classList.remove("hidden");
    const idForVtec = vtecImageId(stationId);
    const events = (vtecData.series && (vtecData.series[idForVtec] || vtecData.series[stationId])) || [];
    if (events.length === 0) {
      if (chartVtec) { chartVtec.destroy(); chartVtec = null; }
      noData.classList.remove("hidden");
      return;
    }
    noData.classList.add("hidden");
    var vtecTitleEl = get("vtec-title");
    if (vtecTitleEl) vtecTitleEl.textContent = "VTEC — Station " + idForVtec;
    const order = vtecData.warning_order || [];
    const nameToY = {};
    order.forEach(function (n, i) { nameToY[n] = i; });
    const datasets = [{
      label: "VTEC",
      data: events.map(function (e) {
        return { x: [e.issued, e.expired], y: nameToY[e.warning_name] != null ? nameToY[e.warning_name] : 0 };
      }),
      type: "bar",
      indexAxis: "y",
      backgroundColor: "rgba(70, 130, 180, 0.8)",
      borderColor: "navy",
      barThickness: 12,
    }];
    const yLabels = order.length ? order : ["Warning"];
    var opts = Object.assign({}, chartOptions, {
      indexAxis: "y",
      plugins: Object.assign({}, chartOptions.plugins, {
        legend: { display: false },
        annotation: { annotations: buildStormAnnotations(stormsData.storms || [], yLabels.length - 0.5, -0.5) },
      }),
      scales: {
        x: {
          type: "time",
          min: "2010-01-01",
          max: "2025-12-31",
          grid: { color: "#e0e0e0" },
          ticks: { color: "#333", maxTicksLimit: 10 },
          time: { unit: "year", stepSize: 2, displayFormats: { year: "yyyy" } },
        },
        y: { min: -0.5, max: yLabels.length - 0.5, minWidth: 48, grid: { color: "#e0e0e0" }, ticks: { callback: function (_, i) { return yLabels[i] || ""; }, color: "#333", maxRotation: 0 } },
      },
    });
    if (chartVtec) chartVtec.destroy();
    chartVtec = new Chart(canvas.getContext("2d"), {
      type: "bar",
      data: { datasets: datasets },
      options: opts,
    });
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
    var canvas = get("chart-water-level");
    var noData = get("water-level-no-data");
    if (!wrap || !canvas || !noData) return;
    wrap.classList.remove("hidden");
    if (!noaaId) {
      if (chartWaterLevel) { chartWaterLevel.destroy(); chartWaterLevel = null; }
      noData.classList.remove("hidden");
      return;
    }
    var sta = waterLevelData.series[String(noaaId)];
    if (!sta || (!sta.verified.length && !sta.preliminary.length && !sta.predictions.length && !sta.residual.length)) {
      if (chartWaterLevel) { chartWaterLevel.destroy(); chartWaterLevel = null; }
      noData.classList.remove("hidden");
      return;
    }
    noData.classList.add("hidden");
    var datasets = [];
    if (sta.verified && sta.verified.length) {
      datasets.push({ label: "Verified", data: sta.verified.map(function (d) { return { x: d.date, y: d.value }; }), borderColor: "#4682b4", backgroundColor: "transparent", fill: false, tension: 0.1 });
    }
    if (sta.preliminary && sta.preliminary.length) {
      datasets.push({ label: "Preliminary", data: sta.preliminary.map(function (d) { return { x: d.date, y: d.value }; }), borderColor: "orange", backgroundColor: "transparent", fill: false, tension: 0.1 });
    }
    if (sta.predictions && sta.predictions.length) {
      datasets.push({ label: "Predictions", data: sta.predictions.map(function (d) { return { x: d.date, y: d.value }; }), borderColor: "green", backgroundColor: "transparent", fill: false, tension: 0.1 });
    }
    if (sta.residual && sta.residual.length) {
      datasets.push({ label: "Obs − Pred", data: sta.residual.map(function (d) { return { x: d.date, y: d.value }; }), borderColor: "crimson", backgroundColor: "transparent", fill: false, tension: 0.1 });
    }
    var yMax = 0;
    datasets.forEach(function (ds) { ds.data.forEach(function (p) { if (p.y > yMax) yMax = p.y; }); });
    if (yMax <= 0) yMax = 1;
    var titleEl = get("water-level-title");
    if (titleEl) titleEl.textContent = "Water level (m MLLW) — Station " + noaaId;
    var opts = Object.assign({}, chartOptions, {
      plugins: Object.assign({}, chartOptions.plugins, {
        legend: { display: true, position: "top", labels: { color: "#333", boxWidth: 12 } },
        annotation: { annotations: buildStormAnnotations(stormsData.storms || [], yMax * 1.05, yMax * 0.88) },
      }),
    });
    if (chartWaterLevel) chartWaterLevel.destroy();
    chartWaterLevel = new Chart(canvas.getContext("2d"), {
      type: "line",
      data: { datasets: datasets },
      options: opts,
    });
  }

  function updateMeteorologicalFigureForStation(noaaId) {
    var wrap = get("meteorological-wrap");
    var canvas = get("chart-meteorological");
    var noData = get("meteorological-no-data");
    if (!wrap || !canvas || !noData) return;
    wrap.classList.remove("hidden");
    if (!noaaId) {
      if (chartMeteorological) { chartMeteorological.destroy(); chartMeteorological = null; }
      noData.classList.remove("hidden");
      return;
    }
    var sta = meteorologicalData.series[String(noaaId)];
    if (!sta) {
      if (chartMeteorological) { chartMeteorological.destroy(); chartMeteorological = null; }
      noData.classList.remove("hidden");
      return;
    }
    var datasets = [];
    var labels = { air_temperature: "Air temp °C", wind: "Wind m/s", air_pressure: "Pressure hPa", water_temperature: "Water temp °C", humidity: "Humidity %", visibility: "Visibility km", water_level: "Water level" };
    if (sta.water_level && (sta.water_level.verified || []).length) {
      datasets.push({ label: "Water level", data: sta.water_level.verified.map(function (d) { return { x: d.date, y: d.value }; }), borderColor: "#4682b4", fill: false, tension: 0.1 });
    }
    ["air_temperature", "wind", "air_pressure", "water_temperature"].forEach(function (k) {
      if (sta[k] && sta[k].length) {
        datasets.push({ label: labels[k] || k, data: sta[k].map(function (d) { return { x: d.date, y: d.value }; }), borderColor: "#58a6ff", fill: false, tension: 0.1 });
      }
    });
    if (datasets.length === 0) {
      if (chartMeteorological) { chartMeteorological.destroy(); chartMeteorological = null; }
      noData.classList.remove("hidden");
      return;
    }
    noData.classList.add("hidden");
    var yMax = 0;
    datasets.forEach(function (ds) { ds.data.forEach(function (p) { if (p.y > yMax) yMax = p.y; }); });
    if (yMax <= 0) yMax = 1;
    var titleEl = get("meteorological-title");
    if (titleEl) titleEl.textContent = "Water level & meteorological — Station " + noaaId;
    var opts = Object.assign({}, chartOptions, {
      plugins: Object.assign({}, chartOptions.plugins, {
        legend: { display: true, position: "top", labels: { color: "#333", boxWidth: 12 } },
        annotation: { annotations: buildStormAnnotations(stormsData.storms || [], yMax * 1.05, yMax * 0.88) },
      }),
    });
    if (chartMeteorological) chartMeteorological.destroy();
    chartMeteorological = new Chart(canvas.getContext("2d"), {
      type: "line",
      data: { datasets: datasets },
      options: opts,
    });
  }

  function updatePrecipitationFigure(noaaId) {
    var wrap = get("precipitation-wrap");
    var canvas = get("chart-precipitation");
    var noData = get("precipitation-no-data");
    if (!wrap || !canvas || !noData) return;
    wrap.classList.remove("hidden");
    if (!noaaId) {
      if (chartPrecipitation) { chartPrecipitation.destroy(); chartPrecipitation = null; }
      noData.classList.remove("hidden");
      return;
    }
    var arr = (precipitationData.series && precipitationData.series[String(noaaId)]) || [];
    if (!arr.length) {
      if (chartPrecipitation) { chartPrecipitation.destroy(); chartPrecipitation = null; }
      noData.classList.remove("hidden");
      return;
    }
    noData.classList.add("hidden");
    var dataPoints = arr.map(function (d) { return { x: d.date, y: d.value }; });
    var yMax = 0;
    dataPoints.forEach(function (p) { if (p.y > yMax) yMax = p.y; });
    if (yMax <= 0) yMax = 1;
    var titleEl = get("precipitation-title");
    if (titleEl) titleEl.textContent = "Precipitation (mm/day) — Station " + noaaId;
    var opts = Object.assign({}, chartOptions, {
      plugins: Object.assign({}, chartOptions.plugins, {
        annotation: { annotations: buildStormAnnotations(stormsData.storms || [], yMax * 1.05, yMax * 0.88) },
      }),
    });
    if (chartPrecipitation) chartPrecipitation.destroy();
    chartPrecipitation = new Chart(canvas.getContext("2d"), {
      type: "line",
      data: {
        datasets: [{ label: "Precipitation", data: dataPoints, borderColor: "#58a6ff", backgroundColor: "rgba(88, 166, 255, 0.2)", fill: true, tension: 0.1 }],
      },
      options: opts,
    });
  }

  function loadNoaaStation(s) {
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
    get("meteorological-wrap").classList.remove("hidden");
    get("precipitation-wrap").classList.remove("hidden");
    destroyCharts();
    updateVtecFigure(s && s.id ? s.id : null);
    updateWaterLevelFigureForStation(s && s.id ? s.id : null);
    updateMeteorologicalFigureForStation(s && s.id ? s.id : null);
    updatePrecipitationFigure(s && s.id ? s.id : null);
  }

  function loadDischargeStation(stationId, lat, lon, displayName) {
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
    var metWrap = get("meteorological-wrap");
    if (metWrap) {
      metWrap.classList.add("hidden");
      var metImg = get("meteorological-figure");
      if (metImg) metImg.src = "";
    }
    get("precipitation-wrap").classList.add("hidden");
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

  async function loadStormsData() {
    if (stormsData.storms && stormsData.storms.length > 0) return stormsData;
    var base = "";
    var path = location.pathname || "";
    if (path && path !== "/" && path !== "/index.html") {
      var segs = path.split("/").filter(Boolean);
      if (segs.length > 0) base = "/" + segs[0] + "/";
    }
    var dataUrl = base + "data/storms_data.json";
    try {
      var res = await fetch(dataUrl);
      if (!res.ok) return stormsData;
      stormsData = await res.json();
      return stormsData;
    } catch (e) {
      console.warn("Failed to load storms data:", e);
      return stormsData;
    }
  }

  async function loadNoaaStations() {
    if (noaaStations.length > 0) return noaaStations;
    var base = "";
    var path = location.pathname || "";
    if (path && path !== "/" && path !== "/index.html") {
      var segments = path.split("/").filter(Boolean);
      if (segments.length > 0) base = "/" + segments[0] + "/";
    }
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

  async function initMap() {
    const center = [41.75, -71.5];
    map = L.map("map").setView(center, 8);
    L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}", {
      attribution: "Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ",
      maxZoom: 18,
    }).addTo(map);

    dischargeLayer = L.layerGroup().addTo(map);
    noaaLayer = L.layerGroup().addTo(map);

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
      marker.bindTooltip("NOAA: " + label, { permanent: false });
      marker.on("click", function () {
        get("discharge-select").value = "";
        get("noaa-select").value = s ? s.id : "";
        loadNoaaStation(s);
      });
      noaaLayer.addLayer(marker);
    });

    var legend = L.control({ position: "bottomright" });
    legend.onAdd = function () {
      var div = L.DomUtil.create("div", "map-legend");
      div.innerHTML =
        "<strong>Legend</strong><br>" +
        "<span class='legend-item'><span class='legend-swatch' style='background:#3fb950;border-color:#2ea043'></span> USGS discharge</span><br>" +
        "<span class='legend-item'><span class='legend-swatch' style='background:#58a6ff;border-color:#388bfd'></span> NOAA tide/water level</span>";
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
        marker.bindTooltip("Discharge: " + label, { permanent: false });
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
        var s = noaaList.find(function (st) { return String(st.id) === String(v); });
        if (s) loadNoaaStation(s);
      });
    }
  }

  async function init() {
    dischargeData = await loadDischargeData();
    stormsData = await loadStormsData();
    var wl = await loadJsonData("water_level_data");
    if (wl && wl.series) waterLevelData = wl;
    var pr = await loadJsonData("precipitation_data");
    if (pr && pr.series) precipitationData = pr;
    var met = await loadJsonData("meteorological_data");
    if (met && met.series) meteorologicalData = met;
    var vtec = await loadJsonData("vtec_data");
    if (vtec) { vtecData.series = vtec.series || {}; vtecData.warning_order = vtec.warning_order || []; }
    if (dischargeData && dischargeData.stations && dischargeData.stations.length > 0) {
      document.getElementById("api-error-banner").classList.add("hidden");
    }
    var stormSelect = get("storm-select");
    if (stormSelect && stormsData.storms && stormsData.storms.length > 0) {
      stormsData.storms.forEach(function (s) {
        var opt = document.createElement("option");
        opt.value = s.id;
        opt.textContent = s.displayLabel;
        stormSelect.appendChild(opt);
      });
      stormSelect.addEventListener("change", function () {
        var dischargeWrap = get("discharge-chart-wrap");
        if (dischargeWrap && !dischargeWrap.classList.contains("hidden")) {
          var v = get("discharge-select").value;
          if (v) {
            var sid = formatStationIdDisplay(v);
            fetchStationSeries(v).then(function (series) {
              if (series.length > 0) drawDischargeChart(series, sid);
            });
          }
        }
        var noaaId = get("noaa-select") && get("noaa-select").value;
        if (noaaId) {
          updateWaterLevelFigureForStation(noaaId);
          updatePrecipitationFigure(noaaId);
          updateMeteorologicalFigureForStation(noaaId);
          updateVtecFigure(noaaId);
        }
      });
    }
    await initMap();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
