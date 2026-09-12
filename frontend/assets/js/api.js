/**
 * api.js · cliente HTTP de la API de Morfi Center.
 *
 *   import { api, ApiError, setToken } from "/assets/js/api.js";
 *   const shift = await api.get("/shift/current");
 *
 * - Base URL: `window.__MC_API__` (ver config.js).
 * - Access token en memoria (nunca en localStorage). El refresh token viaja en
 *   una cookie httpOnly; por eso todas las requests usan `credentials: "include"`.
 * - Ante un 401, intenta `POST /auth/refresh` una vez y reintenta la request.
 * - Los errores del backend (`{ "error": { code, message, details } }`) se
 *   propagan como `ApiError`.
 */

import { API_BASE } from "./config.js";

const DEFAULT_TIMEOUT_MS = 20000;
const NO_RETRY_PATHS = ["/auth/login", "/auth/register", "/auth/refresh", "/auth/logout"];

// ── Token en memoria ───────────────────────────────────
let accessToken = null;

/** Guarda (o limpia con `null`) el access token en memoria. */
export function setToken(token) {
  accessToken = token || null;
}

/** Devuelve el access token actual (o `null`). */
export function getToken() {
  return accessToken;
}

// ── Error ──────────────────────────────────────────────
export class ApiError extends Error {
  /**
   * @param {number} status  código HTTP
   * @param {{code?: string, message?: string, details?: object}} [errorBody]
   */
  constructor(status, errorBody = {}) {
    super(errorBody.message || `Error ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.code = errorBody.code || (status === 0 ? "NETWORK_ERROR" : `HTTP_${status}`);
    this.details = errorBody.details || {};
  }

  /** true si es un problema de red / timeout (no una respuesta del servidor). */
  get isNetwork() {
    return this.status === 0;
  }
}

// ── Refresh de sesión (con guarda de concurrencia) ─────
let refreshInFlight = null;

/**
 * Intenta renovar el access token con la cookie de refresh.
 * @returns {Promise<boolean>} true si se obtuvo un token nuevo.
 */
export function refreshSession() {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const res = await fetch(`${API_BASE}/auth/refresh`, {
          method: "POST",
          credentials: "include",
        });
        if (!res.ok) return false;
        const data = await res.json().catch(() => null);
        if (!data?.access_token) return false;
        setToken(data.access_token);
        return true;
      } catch {
        return false;
      }
    })();
    refreshInFlight.finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

// ── Request ────────────────────────────────────────────
function buildUrl(path, params) {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, value);
      }
    }
  }
  return url.toString();
}

async function request(path, options = {}) {
  const {
    method = "GET",
    body,
    form,
    params,
    auth = true,
    retry = true,
    timeout = DEFAULT_TIMEOUT_MS,
  } = options;

  const headers = {};
  if (auth && accessToken) headers.Authorization = `Bearer ${accessToken}`;

  let payload;
  if (form) {
    payload = form; // FormData: el browser pone el Content-Type con boundary
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeout);

  let res;
  try {
    res = await fetch(buildUrl(path, params), {
      method,
      headers,
      body: payload,
      credentials: "include",
      signal: controller.signal,
    });
  } catch (err) {
    throw new ApiError(0, {
      code: err.name === "AbortError" ? "TIMEOUT" : "NETWORK_ERROR",
      message:
        err.name === "AbortError"
          ? "La solicitud tardó demasiado. Probá de nuevo."
          : "No pudimos conectarnos. Revisá tu conexión.",
    });
  } finally {
    window.clearTimeout(timer);
  }

  // 401 → intentar refresh una sola vez y reintentar
  const canRetry = retry && auth && !NO_RETRY_PATHS.some((p) => path.startsWith(p));
  if (res.status === 401 && canRetry) {
    const ok = await refreshSession();
    if (ok) return request(path, { ...options, retry: false });
  }

  const data = res.status === 204 ? null : await res.json().catch(() => null);

  if (!res.ok) {
    throw new ApiError(res.status, data?.error ?? { message: `Error ${res.status}` });
  }
  return data;
}

// ── API pública ────────────────────────────────────────
export const api = {
  get: (path, opts) => request(path, { ...opts, method: "GET" }),
  post: (path, body, opts) => request(path, { ...opts, method: "POST", body }),
  patch: (path, body, opts) => request(path, { ...opts, method: "PATCH", body }),
  put: (path, body, opts) => request(path, { ...opts, method: "PUT", body }),
  del: (path, opts) => request(path, { ...opts, method: "DELETE" }),
  /** Sube un FormData (multipart), p. ej. un comprobante. */
  upload: (path, formData, opts) => request(path, { ...opts, method: "POST", form: formData }),
  request,
};
