/**
 * login.js · pages/auth/login.html (`03_Roadmap.md` T-1.11.1).
 *
 * - Login local (`auth.login()`), errores del backend en el banner del form.
 * - Botón "Continuar con Google": apunta a `${API_BASE}/auth/google/login`
 *   (URL absoluta porque en dev la API vive en otro puerto).
 * - Vuelta del flujo de Google: el callback del backend redirige acá con
 *   `#access_token=...&expires_in=...` (éxito) o `?error=google_auth_failed`.
 * - `?next=/ruta` (dejado por `requireRole()` al pedir sesión) se respeta al
 *   redirigir tras un login exitoso, sea local o con Google.
 */

import { api, ApiError, setToken } from "../api.js";
import { login, homeForRole } from "../auth.js";
import { API_BASE } from "../config.js";
import { $ } from "../ui.js";

const form = $("#login-form");
const formError = $('[data-error="form"]');
const submitBtn = $("[data-submit]");
const googleLink = $("[data-google-login]");

if (googleLink) {
  googleLink.href = `${API_BASE}/auth/google/login`;
}

function safeNext() {
  const raw = new URLSearchParams(window.location.search).get("next");
  return raw && raw.startsWith("/") && !raw.startsWith("//") ? raw : null;
}

function showFormError(message) {
  formError.textContent = message;
  formError.classList.remove("hidden");
}

function hideFormError() {
  formError.classList.add("hidden");
  formError.textContent = "";
}

function redirectAfterLogin(user) {
  window.location.href = safeNext() || homeForRole(user.role);
}

/** Si venimos de `/auth/google/callback`, completa la sesión y redirige. */
async function handleGoogleRedirect() {
  if (!window.location.hash.startsWith("#access_token=")) return false;

  const params = new URLSearchParams(window.location.hash.slice(1));
  const accessToken = params.get("access_token");
  history.replaceState(null, "", window.location.pathname + window.location.search);
  if (!accessToken) return false;

  try {
    setToken(accessToken);
    const user = await api.get("/auth/me");
    redirectAfterLogin(user);
  } catch {
    setToken(null);
    showFormError("No pudimos completar el inicio con Google. Probá de nuevo.");
  }
  return true;
}

if (!(await handleGoogleRedirect())) {
  if (new URLSearchParams(window.location.search).get("error") === "google_auth_failed") {
    showFormError("No pudimos completar el inicio con Google. Probá de nuevo.");
  }
}

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideFormError();
  submitBtn.disabled = true;
  submitBtn.textContent = "Entrando…";

  try {
    const email = $("#email").value.trim();
    const password = $("#password").value;
    const user = await login(email, password);
    redirectAfterLogin(user);
  } catch (err) {
    showFormError(err instanceof ApiError ? err.message : "Algo salió mal. Probá de nuevo.");
    submitBtn.disabled = false;
    submitBtn.textContent = "Iniciar sesión";
  }
});
