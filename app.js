(function () {
  "use strict";

  const API = window.API_BASE || "";
  let map = null;
  let dischargeLayer = null;
  let watershedLayer = null;
  let demLayer = null;
  let chartDischarge = null;
  let dischargeData = null;

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
    maintainAspectRatio: true,
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
    const labels = arr.map((d) => d.date);
    const values = arr.map((d) => (d.value != null ? d.value : null));
    const ctx = get("chart-discharge").getContext("2d");
    chartDischarge = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [{
          label: "Discharge",
          data: values,
          borderColor: "#3fb950",
          backgroundColor: "rgba(63, 185, 80, 0.1)",
          fill: true,
          tension: 0.1,
        }],
      },
      options: chartOptions,
    });
  }

  function stationDisplayLabel(s) {
    const id = String(s.id || "");
    const name = (s.name && String(s.name).trim()) ? String(s.name).trim() : "";
    if (name && name !== id) {
      return name + " (" + id + ")";
    }
    return id || "—";
  }

  function loadDischargeStation(stationId, lat, lon, displayName) {
    const meta = (lat != null && lon != null)
      ? "Lat " + Number(lat).toFixed(4) + "°, Lon " + Number(lon).toFixed(4) + "°"
      : "Discharge station";
    const title = displayName ? displayName + " (" + stationId + ")" : stationId;
    showPanel({ name: title }, { meta: meta });

    if (!dischargeData || !dischargeData.series) {
      get("point-meta").textContent = "No discharge data available.";
      destroyCharts();
      return;
    }
    const series = dischargeData.series[stationId] || dischargeData.series[String(stationId)];
    if (!series || series.length === 0) {
      get("point-meta").textContent = meta + " — No time series data.";
      destroyCharts();
      return;
    }
    drawDischargeChart(series);
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
    try {
      const res = await fetch("data/discharge_data.json");
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

    watershedLayer = L.layerGroup().addTo(map);
    demLayer = null;
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

  function toggleWatershedLayer(checked) {
    if (!watershedLayer || !map) return;
    watershedLayer.clearLayers();
    const cb = get("layer-watershed");
    if (!checked) return;
    const url = (API || "http://127.0.0.1:8000") + "/api/watershed";
    fetch(url)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(r.status + " " + r.statusText))))
      .then((geojson) => {
        if (geojson && geojson.features && geojson.features.length > 0) {
          const layer = L.geoJSON(geojson, {
            style: { color: "#1a5fb4", weight: 2, fillColor: "#1a5fb4", fillOpacity: 0.25 },
          });
          layer.addTo(watershedLayer);
          const b = layer.getBounds();
          if (b && b.isValid()) map.fitBounds(b, { maxZoom: 12, padding: [20, 20] });
        } else {
          if (cb) cb.checked = false;
        }
      })
      .catch((err) => {
        console.warn("Watershed load failed:", err);
        if (cb) cb.checked = false;
      });
  }

  function toggleDEMLayer(checked) {
    if (!map) return;
    if (demLayer) {
      map.removeLayer(demLayer);
      demLayer = null;
    }
    const cb = get("layer-dem");
    if (!checked) return;
    const base = API || "http://127.0.0.1:8000";
    fetch(base + "/api/dem/bounds")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(r.statusText))))
      .then((bounds) => {
        if (bounds && bounds.south != null) {
          const b = [[bounds.south, bounds.west], [bounds.north, bounds.east]];
          demLayer = L.imageOverlay(base + "/api/dem/image", b, { opacity: 0.5, crossOrigin: "anonymous" }).addTo(map);
          map.fitBounds(b, { maxZoom: 12, padding: [20, 20] });
        } else {
          if (cb) cb.checked = false;
        }
      })
      .catch((err) => {
        console.warn("DEM load failed:", err);
        if (cb) cb.checked = false;
      });
  }

  async function init() {
    get("layer-watershed").addEventListener("change", function () {
      toggleWatershedLayer(this.checked);
    });
    get("layer-dem").addEventListener("change", function () {
      toggleDEMLayer(this.checked);
    });

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
