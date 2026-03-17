(function () {
  "use strict";

  function get(id) { return document.getElementById(id); }

  function formatStationIdDisplay(id) {
    if (id == null || id === "") return "";
    const s = String(id).trim();
    if (!s) return "";
    return s.padStart(8, "0");
  }

  function stationDisplayLabel(s) {
    const id = String(s.id || "");
    const idDisplay = formatStationIdDisplay(id);
    const name = (s.name && String(s.name).trim()) ? String(s.name).trim() : "";
    if (name && name !== id) return name + " (" + idDisplay + ")";
    return idDisplay || "—";
  }

  function getBasePath() {
    var path = location.pathname || "";
    if (path && path !== "/" && path !== "/index.html") {
      var segs = path.split("/").filter(Boolean);
      if (segs.length > 0) return "/" + segs[0] + "/";
    }
    return "";
  }

  async function loadDischargeData() {
    const base = getBasePath();
    const res = await fetch(base + "data/discharge_data.json");
    if (!res.ok) throw new Error("Failed to load discharge_data.json");
    return await res.json();
  }

  function wireFigure(imgId, noDataId, src) {
    const img = get(imgId);
    const noData = get(noDataId);
    if (!img || !noData) return;

    img.onload = function () {
      img.classList.remove("hidden");
      noData.classList.add("hidden");
    };
    img.onerror = function () {
      img.removeAttribute("src");
      img.classList.add("hidden");
      noData.classList.remove("hidden");
    };
    img.classList.add("hidden");
    img.src = src;
  }

  function setStation(station, id8) {
    get("panel-placeholder").classList.add("hidden");
    get("panel-content").classList.remove("hidden");

    const title = station ? stationDisplayLabel(station) : ("Station " + id8);
    get("point-title").textContent = title;
    get("point-meta").innerHTML = 'USGS station: <a href="https://waterdata.usgs.gov/monitoring-location/USGS-' + id8 + '/" target="_blank" rel="noopener">USGS-' + id8 + "</a>";

    const base = getBasePath();
    wireFigure("usgs-fdc-figure", "usgs-fdc-no-data", base + "images/usgs_analysis/fdc_" + id8 + ".png");
    wireFigure("usgs-pot-annual-figure", "usgs-pot-annual-no-data", base + "images/usgs_analysis/pot_counts_annual_" + id8 + ".png");
    wireFigure("usgs-pot-seasonal-figure", "usgs-pot-seasonal-no-data", base + "images/usgs_analysis/pot_counts_seasonal_" + id8 + ".png");
    wireFigure("usgs-seasonality-figure", "usgs-seasonality-no-data", base + "images/usgs_analysis/seasonality_monthly_" + id8 + ".png");
    wireFigure("usgs-extremes-figure", "usgs-extremes-no-data", base + "images/usgs_analysis/extremes_topN_" + id8 + ".png");

    const setTitle = function (elId, text) { const el = get(elId); if (el) el.textContent = text; };
    setTitle("usgs-fdc-title", "Flow duration curve (FDC) — Station " + id8);
    setTitle("usgs-pot-annual-title", "POT counts (annual) — Station " + id8);
    setTitle("usgs-pot-seasonal-title", "POT counts (seasonal) — Station " + id8);
    setTitle("usgs-seasonality-title", "Flood seasonality (monthly) — Station " + id8);
    setTitle("usgs-extremes-title", "Large floods (top-N) — Station " + id8);
  }

  async function init() {
    const select = get("discharge-select");
    if (!select) return;

    let data;
    try {
      data = await loadDischargeData();
    } catch (e) {
      console.error(e);
      return;
    }

    const stations = (data && data.stations) ? data.stations : [];
    stations.forEach(function (s) {
      const sid = s && s.id ? String(s.id) : "";
      if (!sid) return;
      const opt = document.createElement("option");
      opt.value = sid;
      opt.textContent = stationDisplayLabel(s);
      select.appendChild(opt);
    });

    select.addEventListener("change", function () {
      const sid = this.value;
      if (!sid) return;
      const id8 = formatStationIdDisplay(sid);
      const st = stations.find(function (x) { return String(x.id) === String(sid); }) || null;
      setStation(st, id8);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

