// API base URL: use backend when running locally, empty for static deployment
window.API_BASE = window.API_BASE || (
  (location.hostname === "localhost" || location.hostname === "127.0.0.1") && location.protocol !== "file:"
    ? "http://127.0.0.1:8000"
    : ""
);
