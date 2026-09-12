/**
 * config.js · configuración de runtime del frontend.
 *
 * `window.__MC_API__` = URL base de la API.
 *   - Producción: el front lo sirve el mismo backend → `/api/v1` (relativo).
 *   - Desarrollo: el front corre en otro puerto (5500) y la API en :8000.
 *
 * Se puede forzar desde una página con un <script> (NO módulo) antes de los
 * módulos:  <script>window.__MC_API__ = "http://mi-host:9000/api/v1"</script>
 */

if (!window.__MC_API__) {
  const { protocol, hostname, port } = window.location;
  // Si el front NO corre en el puerto del backend, asumimos dev y apuntamos a :8000.
  window.__MC_API__ =
    port && port !== "8000" ? `${protocol}//${hostname}:8000/api/v1` : "/api/v1";
}

export const API_BASE = window.__MC_API__;
