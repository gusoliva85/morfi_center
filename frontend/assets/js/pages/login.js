import { API_BASE } from "../config.js"; // primero: api.js lee window.__MC_API__ al cargarse
import { ApiError } from "../api.js";
import { login } from "../auth.js";
import { $ } from "../ui.js";

// A dónde va cada rol después de entrar. DELIVERY todavía no tiene pantalla
// propia (llega en Fase 14) y el dashboard de admin tampoco: por eso ADMIN va
// al listado de usuarios (T-1.11.6) y DELIVERY al home, en vez de a un 404.
const HOME_BY_ROLE = {
  CUSTOMER: "/index.html",
  ADMIN: "/pages/admin/usuarios.html",
  DELIVERY: "/index.html",
};

// Mensajes de los errores que el backend devuelve por la URL al volver de
// Google (T-1.8.2): ahí no puede responder un JSON, porque es una navegación.
const AUTH_ERRORS = {
  google: "No pudimos completar el ingreso con Google. Probá de nuevo.",
  google_email_unverified:
    "Tu email de Google todavía no está verificado. Verificalo o entrá con tu contraseña.",
  account_not_active: "Tu cuenta no está habilitada. Contactate con el local.",
};

const form = $("[data-login-form]");
const errorBox = $("[data-error]");
const submitButton = $("[data-submit]");

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
}

function clearError() {
  errorBox.textContent = "";
  errorBox.classList.add("hidden");
}

/**
 * Destino después de entrar. `next` viene de requireRole() cuando alguien quiso
 * abrir una pantalla protegida: solo se acepta una ruta interna, porque un
 * `next` con URL externa convertiría esta pantalla en un salto a cualquier
 * sitio (un clásico para hacer phishing con un link que parece nuestro).
 */
function destinationFor(user) {
  const next = new URLSearchParams(location.search).get("next");
  if (next && next.startsWith("/") && !next.startsWith("//")) return next;
  return HOME_BY_ROLE[user.role] ?? "/index.html";
}

function messageFor(err) {
  if (!(err instanceof ApiError)) {
    return "No pudimos conectarnos. Revisá tu internet y probá de nuevo.";
  }
  // 422: el detalle viene por campo; se muestra el primero para no abrumar.
  const field = err.details?.fields?.[0];
  if (field) return field.message;
  return err.message;
}

async function onSubmit(event) {
  event.preventDefault();
  clearError();

  const email = form.email.value.trim();
  const password = form.password.value;
  if (!email || !password) {
    showError("Completá tu email y tu contraseña.");
    return;
  }

  submitButton.disabled = true;
  submitButton.textContent = "Entrando…";
  try {
    const user = await login(email, password);
    location.href = destinationFor(user);
  } catch (err) {
    showError(messageFor(err));
    submitButton.disabled = false;
    submitButton.textContent = "Iniciar sesión";
  }
}

/**
 * El endpoint redirige a Google, así que necesita una navegación de primer
 * nivel (no un fetch). Pero si las credenciales no están cargadas responde 503,
 * y navegar mostraría un JSON crudo en pantalla: se consulta antes para avisar
 * dentro de la página.
 */
async function onGoogleClick() {
  const url = `${API_BASE}/auth/google/login`;
  try {
    const res = await fetch(url, { redirect: "manual", credentials: "include" });
    if (res.status === 503) {
      const data = await res.json().catch(() => null);
      showError(data?.error?.message ?? AUTH_ERRORS.google);
      return;
    }
  } catch {
    // Si la consulta previa falla, se intenta la navegación normal igual.
  }
  location.href = url;
}

function showErrorFromUrl() {
  const reason = new URLSearchParams(location.search).get("auth_error");
  if (reason) showError(AUTH_ERRORS[reason] ?? AUTH_ERRORS.google);
}

showErrorFromUrl();
form.addEventListener("submit", onSubmit);
$("[data-google]").addEventListener("click", onGoogleClick);
