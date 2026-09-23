// URL base de la API, en un solo lugar: si viviera en un <script> inline de
// cada página, cambiar el backend obligaría a editar todas.
//
// Se importa **antes** que api.js (que lee window.__MC_API__ al cargarse):
// los módulos se evalúan en el orden de sus imports.
window.__MC_API__ =
  location.hostname === "localhost" || location.hostname === "127.0.0.1"
    ? "http://localhost:8000/api/v1"
    : "https://13-140-36-93.sslip.io/api/v1";

export const API_BASE = window.__MC_API__;
