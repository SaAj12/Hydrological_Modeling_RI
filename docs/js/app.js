(function () {
  "use strict";

  const API = window.API_BASE || "";
  let map = null;
  let dischargeLayer = null;
  let noaaLayer = null;
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
    if (chartDischarge) {
      chartDischarge.destroy();
      chartDischarge = null;
    }
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: {
        ticks: { maxTicksLimit: 8, color: "#8b949e", font: { size: 10 } },
        grid: { color: "#21262d" },
        type: "time",
        time: { unit: "year", displayFormats: { year: "yyyy", month: "MMM yyyy" } },
        min: "2010-01-01",
        max: "2025-12-31",
      },
      y: {
        ticks: { color: "#8b949e", font: { size: 10 } },
        grid: { color: "#21262d" },
        title: { display: false },
      },
    },
  };

  function drawDischargeChart(dischargeDataArr, stationIdDisplay) {
    destroyCharts();
    const arr = dischargeDataArr || [];
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
      plugins: Object.assign({}, chartOptions.plugins, {
        title: {
          display: true,
          text: titleText,
          font: { size: 14 },
          color: "#8b949e",
        },
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
    const img = get("vtec-figure");
    const noData = get("vtec-no-data");
    if (!wrap || !img || !noData) return;
    const idForImage = vtecImageId(stationId);
    const base = getBasePath();
    const src = base + "images/vtec/vtec_timeline_" + idForImage + ".png";
    img.classList.add("hidden");
    noData.classList.add("hidden");
    wrap.classList.remove("hidden");
    img.onerror = function () {
      img.classList.add("hidden");
      noData.classList.remove("hidden");
    };
    img.onload = function () {
      img.classList.remove("hidden");
      noData.classList.add("hidden");
    };
    img.src = src;
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
    var base = getBasePath();
    var id = noaaId || "8454000";
    var src = base + "images/noaa/" + id + "_water_level_with_predictions.png";
    img.classList.add("hidden");
    noData.classList.add("hidden");
    img.onerror = function () {
      img.src = base + "images/noaa/8454000_water_level_with_predictions.png";
    };
    img.onload = function () {
      img.classList.remove("hidden");
      noData.classList.add("hidden");
    };
    img.src = src;
  }

  function updatePrecipitationFigure(noaaId) {
    var wrap = get("precipitation-wrap");
    var img = get("precipitation-figure");
    var noData = get("precipitation-no-data");
    if (!wrap || !img || !noData) return;
    wrap.classList.remove("hidden");
    var base = getBasePath();
    var src = base + "images/noaa/precipitation_" + (noaaId || "") + ".png";
    img.classList.add("hidden");
    noData.classList.add("hidden");
    img.onerror = function () {
      img.classList.add("hidden");
      noData.classList.remove("hidden");
      noData.textContent = "No precipitation data available.";
    };
    img.onload = function () {
      img.classList.remove("hidden");
      noData.classList.add("hidden");
    };
    img.src = src;
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
    get("precipitation-wrap").classList.remove("hidden");
    destroyCharts();
    updateVtecFigure(s && s.id ? s.id : null);
    updateWaterLevelFigureForStation(s && s.id ? s.id : null);
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
    get("precipitation-wrap").classList.add("hidden");
    var meta = (lat != null && lon != null)
      ? "Lat " + Number(lat).toFixed(4) + "°, Lon " + Number(lon).toFixed(4) + "°"
      : "Discharge station";
    var usgsUrl = usgsStationUrl(stationId);
    if (usgsUrl) meta += ' <a href="' + usgsUrl + '" target="_blank" rel="noopener">View on USGS Water Data</a>';
    var idDisplay = formatStationIdDisplay(stationId);
    var title = displayName ? displayName + " (" + idDisplay + ")" : idDisplay;
    showPanel({ name: title }, { meta: meta });
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
