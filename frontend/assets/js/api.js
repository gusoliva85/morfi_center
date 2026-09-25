// Cliente HTTP central: todas las páginas llaman a la API a través de este
// módulo (nunca fetch directo), así hay un solo lugar con manejo de auth y errores.
//
// window.__MC_API__ permite fijar la URL base de la API sin tocar este archivo:
// se define en un <script> inline antes de importar este módulo (dev:
// "http://localhost:8000/api/v1"; prod: la URL pública del backend en el VPS).
// Sin definir, usa "/api/v1" (mismo origen, fallback razonable solo en dev).
const BASE = window.__MC_API__ ?? "/api/v1";

let accessToken = null; // en memoria, nunca localStorage (02_Documento_Tecnico.md §13.1)

export function setToken(token) {
  accessToken = token;
}

export class ApiError extends Error {
  constructor(status, error) {
    super(error?.message ?? `Error HTTP ${status}`);
    this.status = status;
    this.code = error?.code ?? null;
    this.details = error?.details ?? null;
  }
}

async function request(path, { method = "GET", body, form, auth = true, retry = true } = {}) {
  const headers = {};
  if (auth && accessToken) headers.Authorization = `Bearer ${accessToken}`;

  let payload;
  if (form) {
    payload = form; // FormData (comprobantes) — el browser pone su propio Content-Type
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: payload,
    credentials: "include",
    // Sin esto, el navegador puede servir un GET repetido (misma URL) desde su
    // caché en vez de pedirlo de nuevo: el backend no manda `Cache-Control`, y
    // ese es exactamente el patrón de esta app — la misma URL (`/users?...`)
    // se vuelve a pedir todo el tiempo después de crear/editar algo, esperando
    // el dato fresco. Se notó recién con el panel de admin: crear un usuario y
    // refrescar la lista en el momento seguía mostrando la lista vieja.
    cache: "no-store",
  });

  if (res.status === 401 && retry && auth) {
    // access vencido -> refresh -> reintento (una sola vez, retry:false corta el loop)
    const refreshed = await refreshSession();
    if (refreshed) return request(path, { method, body, form, auth, retry: false });
  }

  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, data?.error);
  return data;
}

/** Intenta renovar el access token con la cookie de refresh (httpOnly). */
export async function refreshSession() {
  try {
    const res = await fetch(`${BASE}/auth/refresh`, { method: "POST", credentials: "include" });
    if (!res.ok) return false;
    const data = await res.json();
    setToken(data.access_token);
    return true;
  } catch {
    return false;
  }
}

export const api = {
  get: (path, opts) => request(path, { ...opts, method: "GET" }),
  post: (path, body, opts) => request(path, { ...opts, method: "POST", body }),
  put: (path, body, opts) => request(path, { ...opts, method: "PUT", body }),
  patch: (path, body, opts) => request(path, { ...opts, method: "PATCH", body }),
  del: (path, opts) => request(path, { ...opts, method: "DELETE" }),
  upload: (path, form) => request(path, { method: "POST", form }),
};
