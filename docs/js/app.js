(function () {
  "use strict";

  const API = window.API_BASE || "";
  let map = null;
  let dischargeLayer = null;
  let chartDischarge = null;
  let dischargeData = null;

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
      get("point-meta").textContent = meta !== undefined ? meta : "";
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
        min: "1950-01-01",
        max: "2025-12-31",
      },
      y: {
        ticks: { color: "#8b949e", font: { size: 10 } },
        grid: { color: "#21262d" },
        title: { display: false },
      },
    },
  };

  function drawDischargeChart(dischargeDataArr) {
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
            borderWidth: 1,
          }],
        },
        options: chartOptions,
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

  function updateVtecFigure(stationId) {
    const wrap = get("vtec-figure-wrap");
    const img = get("vtec-figure");
    const noData = get("vtec-no-data");
    if (!wrap || !img || !noData) return;
    const staid8 = formatStationIdDisplay(stationId);
    // GitHub Pages: pathname is e.g. /Hydrological-Modeling/ or /Hydrological-Modeling/index.html
    let base = "";
    if (location.pathname && location.pathname !== "/" && location.pathname !== "/index.html") {
      base = location.pathname.replace(/\/[^/]*$/, "/");
      if (base && !base.endsWith("/")) base += "/";
    }
    const src = base + "images/vtec/vtec_timeline_" + staid8 + ".png";
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

  function loadDischargeStation(stationId, lat, lon, displayName) {
    const meta = (lat != null && lon != null)
      ? "Lat " + Number(lat).toFixed(4) + "°, Lon " + Number(lon).toFixed(4) + "°"
      : "Discharge station";
    const idDisplay = formatStationIdDisplay(stationId);
    const title = displayName ? displayName + " (" + idDisplay + ")" : idDisplay;
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
        drawDischargeChart(series);
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
    var dataUrl = "data/discharge_data.json";
    if (location.pathname && location.pathname !== "/" && location.pathname !== "/index.html") {
      var base = location.pathname.replace(/\/[^/]*$/, "/");
      dataUrl = base + (base.indexOf("data/") === -1 ? "data/discharge_data.json" : "discharge_data.json");
    }
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

  function initMap() {
    const center = [41.75, -71.5];
    map = L.map("map").setView(center, 8);
    L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}", {
      attribution: "Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ",
      maxZoom: 18,
    }).addTo(map);

    dischargeLayer = L.layerGroup().addTo(map);

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
        marker.on("click", async () => {
          loadDischargeStation(sid, s.lat, s.lon, name !== sid ? name : null);
          const series = await fetchStationSeries(sid);
          if (series.length > 0) drawDischargeChart(series);
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
      const v = this.value;
      if (!v) return;
      const opt = this.options[this.selectedIndex];
      const displayName = opt && opt.dataset.displayName ? opt.dataset.displayName : null;
      const s = stations.find((st) => st.id === v);
      loadDischargeStation(v, s ? s.lat : null, s ? s.lon : null, displayName || null);
      const series = await fetchStationSeries(v);
      if (series.length > 0) drawDischargeChart(series);
    });
  }

  async function init() {
    dischargeData = await loadDischargeData();
    if (dischargeData && dischargeData.stations && dischargeData.stations.length > 0) {
      document.getElementById("api-error-banner").classList.add("hidden");
    }
    initMap();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
