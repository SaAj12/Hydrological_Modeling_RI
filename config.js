// API base URL: use backend when running locally (watershed/DEM), empty for static deployment
// When opened from file:// or on GitHub Pages, uses static data/discharge_data.json
window.API_BASE = window.API_BASE || (
  (location.hostname === "localhost" || location.hostname === "127.0.0.1") && location.protocol !== "file:"
    ? "http://127.0.0.1:8000"
    : ""
);
