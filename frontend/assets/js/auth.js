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

/** Pide el link de recuperación. El backend responde siempre lo mismo, exista
 * o no el email — no hay nada que interpretar acá aparte del mensaje. */
export function requestPasswordReset(email) {
  return api.post("/auth/password/forgot", { email }, { auth: false });
}

/** Cambia la contraseña con el token del link. No deja logueado (el backend
 * no emite tokens acá): la persona entra después con su contraseña nueva. */
export function resetPassword(token, password) {
  return api.post("/auth/password/reset", { token, password }, { auth: false });
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
 * Refleja la sesión en el widget del header (nombre + "Cerrar sesión", o
 * "Ingresar"), sin ocultar el resto del header. Las páginas sin ese widget
 * (las de auth, con su propio header minimalista) no hacen nada acá.
 *
 * Llamarlo con el resultado de `bootstrapSession()` en toda página pública;
 * `requireRole()` ya lo hace por su cuenta.
 */
export function renderSessionUI(user) {
  const nameEl = document.querySelector("[data-session-name]");
  const logoutBtn = document.querySelector("[data-session-logout]");
  const loginLink = document.querySelector("[data-session-login]");
  if (!nameEl || !logoutBtn || !loginLink) return;

  nameEl.classList.toggle("hidden", !user);
  logoutBtn.classList.toggle("hidden", !user);
  loginLink.classList.toggle("hidden", Boolean(user));
  if (user) nameEl.textContent = `Hola, ${user.first_name}`;
}

// Delegado (no por página): cualquier página que traiga el partial del header
// ya tiene el botón de logout funcionando, sin tener que conectarlo a mano.
document.addEventListener("click", (event) => {
  if (event.target.closest("[data-session-logout]")) logout();
});

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
  renderSessionUI(me);
  return me;
}
