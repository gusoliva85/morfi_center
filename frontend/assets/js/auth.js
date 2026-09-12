/**
 * auth.js · sesión y guardas por rol.
 *
 *   import { bootstrapSession, login, register, requireRole, mountSessionUI } from "/assets/js/auth.js";
 *
 * - `bootstrapSession()`: intenta recuperar la sesión (cookie de refresh + `/auth/me`).
 * - `login()` / `register()`: dejan al usuario logueado (mismo `AuthOut` del backend).
 * - `requireRole()`: guarda de página **exclusiva de rol** — sin sesión (o rol) redirige
 *   a login con `?next=` y no pinta nada de la pantalla.
 * - `mountSessionUI()`: para páginas **públicas** — resuelve la sesión sin redirigir y
 *   pinta el `[data-session-slot]` del header ("Hola, {nombre}" / "Ingresar").
 * - `paintSessionSlot(user)`: mismo pintado, para páginas **gateadas** que ya tienen
 *   el usuario de `requireRole()` (evita pedir la sesión dos veces).
 */

import { api, ApiError, refreshSession, setToken } from "./api.js";

const LOGIN_URL = "/pages/auth/login.html";

// Home por rol tras iniciar sesión.
const HOME_BY_ROLE = {
  CUSTOMER: "/index.html",
  ADMIN: "/pages/admin/dashboard.html",
  DELIVERY: "/pages/delivery/inicio.html",
};

let currentUser = null;

/** Usuario en memoria de la sesión actual (o `null`). */
export function getUser() {
  return currentUser;
}

/**
 * Intenta recuperar la sesión: refresca el token con la cookie y pide `/auth/me`.
 * @returns {Promise<object|null>} el usuario, o `null` si no hay sesión.
 */
export async function bootstrapSession() {
  try {
    const refreshed = await refreshSession();
    if (!refreshed) return null;
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

/**
 * Inicia sesión con email + contraseña.
 * @returns {Promise<object>} el usuario.
 */
export async function login(email, password) {
  const data = await api.post("/auth/login", { email, password }, { auth: false });
  setToken(data.access_token);
  currentUser = data.user;
  return currentUser;
}

/**
 * Alta de cuenta propia (rol CUSTOMER). Deja logueado, igual que `login()`.
 * @param {{first_name: string, last_name: string, email: string, phone?: string, password: string}} payload
 * @returns {Promise<object>} el usuario.
 */
export async function register(payload) {
  const data = await api.post("/auth/register", payload, { auth: false });
  setToken(data.access_token);
  currentUser = data.user;
  return currentUser;
}

/** Cierra sesión (invalida el refresh) y vuelve al inicio. */
export async function logout() {
  try {
    await api.post("/auth/logout");
  } catch {
    /* da igual si falla: igual limpiamos local */
  }
  setToken(null);
  currentUser = null;
  window.location.href = "/";
}

/** URL de home según el rol del usuario. */
export function homeForRole(role) {
  return HOME_BY_ROLE[role] || "/index.html";
}

/**
 * Guarda de página: exige sesión (y opcionalmente un rol). Si no cumple,
 * redirige al login y lanza para cortar la ejecución de la página.
 * @param {string|string[]} [roles]  rol o roles permitidos
 * @returns {Promise<object>} el usuario
 */
export async function requireRole(roles) {
  const me = await bootstrapSession();
  const allowed = roles == null || [].concat(roles).includes(me?.role);
  if (!me || !allowed) {
    const next = encodeURIComponent(window.location.pathname);
    window.location.href = `${LOGIN_URL}?next=${next}`;
    throw new Error("no autorizado");
  }
  return me;
}

/**
 * Página pública (T-1.11.4, RF-USR-11/12): resuelve la sesión sin redirigir
 * — solo para saludar al usuario si ya está logueado — y pinta el
 * `[data-session-slot]` del header con "Hola, {nombre} · Cerrar sesión" o
 * "Ingresar" según corresponda. No bloquea el acceso a la pantalla.
 * @param {ParentNode} [root]
 * @returns {Promise<object|null>} el usuario, o `null` si no hay sesión.
 */
export async function mountSessionUI(root = document) {
  const user = await bootstrapSession();
  paintSessionSlot(user, root);
  return user;
}

/**
 * Pinta el `[data-session-slot]` del header a partir de un usuario ya
 * resuelto (p. ej. el que devuelve `requireRole()`) — para páginas
 * **gateadas**, que ya hicieron su propio `bootstrapSession()` y no
 * necesitan pedirlo de nuevo solo para el header.
 * @param {object|null} user
 * @param {ParentNode} [root]
 */
export function paintSessionSlot(user, root = document) {
  const slot = root.querySelector("[data-session-slot]");
  if (slot) renderSessionSlot(slot, user);
}

function renderSessionSlot(slot, user) {
  slot.replaceChildren();

  if (user) {
    const greeting = document.createElement("span");
    greeting.className = "text-bark/60";
    greeting.textContent = `Hola, ${user.first_name}`;

    const dot = document.createElement("span");
    dot.className = "text-bark/25";
    dot.setAttribute("aria-hidden", "true");
    dot.textContent = "·";

    const logoutBtn = document.createElement("button");
    logoutBtn.type = "button";
    logoutBtn.className = "text-brick transition hover:underline";
    logoutBtn.textContent = "Cerrar sesión";
    logoutBtn.addEventListener("click", () => {
      logout();
    });

    slot.append(greeting, dot, logoutBtn);
  } else {
    const link = document.createElement("a");
    const next = encodeURIComponent(window.location.pathname);
    link.href = `${LOGIN_URL}?next=${next}`;
    link.className = "font-hand text-[15px] text-brick";
    link.textContent = "Ingresar";
    slot.append(link);
  }
}
