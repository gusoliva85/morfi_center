import { api, ApiError, refreshSession, setToken } from "./api.js";

const LOGIN_URL = "/pages/auth/login.html";
let currentUser = null;

export function getUser() {
  return currentUser;
}

/**
 * Se llama al cargar cualquier página, sin redirigir nunca (eso lo deciden
 * requireRole()/la página). Todavía no hay backend de auth (llega en Fase 1):
 * hasta entonces esto siempre devuelve null de forma segura, sin romper nada.
 */
export async function bootstrapSession() {
  try {
    if (!(await refreshSession())) return null;
    currentUser = await api.get("/auth/me");
    return currentUser;
  } catch (err) {
    if (err instanceof ApiError) {
      currentUser = null;
      return null;
    }
    throw err;
  }
}

export async function login(email, password) {
  const data = await api.post("/auth/login", { email, password }, { auth: false });
  setToken(data.access_token);
  currentUser = data.user;
  return currentUser;
}

/**
 * Alta de cliente con login automático (el backend ya devuelve tokens en el
 * 201, igual que `/auth/login`): `payload` es {first_name, last_name, email,
 * password, phone?}.
 */
export async function register(payload) {
  const data = await api.post("/auth/register", payload, { auth: false });
  setToken(data.access_token);
  currentUser = data.user;
  return currentUser;
}

export async function logout() {
  try {
    await api.post("/auth/logout");
  } catch {
    // el logout local sigue igual aunque falle la llamada al backend
  }
  setToken(null);
  currentUser = null;
  location.href = "/";
}

/**
 * roles === undefined -> "cualquier usuario logueado" (páginas de cliente,
 * sin atarlas a un rol puntual). roles: string | string[] -> rol específico
 * (ADMIN/DELIVERY). Sin sesión o sin el rol que corresponde, redirige a
 * login con `next` para volver a esta misma pantalla después de loguear.
 */
export async function requireRole(roles) {
  const me = await bootstrapSession();
  const allowed = roles == null || [].concat(roles).includes(me?.role);
  if (!me || !allowed) {
    location.href = `${LOGIN_URL}?next=${encodeURIComponent(location.pathname)}`;
    throw new Error("no autorizado");
  }
  return me;
}
