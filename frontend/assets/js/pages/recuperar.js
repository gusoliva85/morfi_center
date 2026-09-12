/**
 * recuperar.js · pages/auth/recuperar.html (`03_Roadmap.md` T-1.11.3).
 *
 * Dos pasos en la misma página, elegidos por la presencia de `?token=`:
 *   1. Sin token: pide el email (`POST /auth/password/forgot`). Mensaje
 *      siempre neutro — el backend nunca revela si el email existe.
 *   2. Con token (el que en dev queda logueado en la consola del backend,
 *      todavía no hay envío de mail): nueva contraseña + repetir
 *      (`POST /auth/password/reset`).
 */

import { api, ApiError } from "../api.js";
import { $ } from "../ui.js";

const token = new URLSearchParams(window.location.search).get("token");

const requestStep = $('[data-step="request"]');
const resetStep = $('[data-step="reset"]');

if (token) {
  requestStep.hidden = true;
  resetStep.hidden = false;
} else {
  requestStep.hidden = false;
  resetStep.hidden = true;
}

// ── Paso 1 · pedir el link ─────────────────────────────
const forgotForm = $("#forgot-form");
const forgotError = $('[data-error="forgot-form"]');
const forgotSubmit = $("[data-submit-forgot]");
const forgotDone = $("[data-forgot-done]");

forgotForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  forgotError.classList.add("hidden");

  forgotSubmit.disabled = true;
  forgotSubmit.textContent = "Enviando…";

  try {
    const email = $("#email").value.trim();
    // Siempre 200: el backend nunca revela si el email existe.
    await api.post("/auth/password/forgot", { email }, { auth: false });
    forgotForm.hidden = true;
    forgotDone.hidden = false;
  } catch (err) {
    forgotError.textContent =
      err instanceof ApiError ? err.message : "Algo salió mal. Probá de nuevo.";
    forgotError.classList.remove("hidden");
    forgotSubmit.disabled = false;
    forgotSubmit.textContent = "Enviar instrucciones";
  }
});

// ── Paso 2 · nueva contraseña ──────────────────────────
const resetForm = $("#reset-form");
const resetFormError = $('[data-error="reset-form"]');
const resetSubmit = $("[data-submit-reset]");
const resetDone = $("[data-reset-done]");
const passwordField = $("#password");
const confirmField = $("#password_confirm");

function setFieldError(field, message) {
  const el = $(`[data-error="${field}"]`);
  if (!el) return;
  if (message) {
    el.textContent = message;
    el.classList.remove("hidden");
  } else {
    el.textContent = "";
    el.classList.add("hidden");
  }
}

resetForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  resetFormError.classList.add("hidden");
  setFieldError("password", null);
  setFieldError("password_confirm", null);

  const password = passwordField.value;
  const confirm = confirmField.value;
  if (password !== confirm) {
    setFieldError("password_confirm", "No coincide con la contraseña.");
    return;
  }

  resetSubmit.disabled = true;
  resetSubmit.textContent = "Cambiando…";

  try {
    await api.post("/auth/password/reset", { token, password }, { auth: false });
    resetForm.hidden = true;
    resetDone.hidden = false;
  } catch (err) {
    if (err instanceof ApiError && err.details?.field === "password") {
      setFieldError("password", err.message);
    } else if (err instanceof ApiError) {
      // token ausente/inválido/vencido/ya usado: no hay campo de token en
      // pantalla (viaja en la URL), así que el mensaje va en el banner.
      resetFormError.textContent = err.message;
      resetFormError.classList.remove("hidden");
    } else {
      resetFormError.textContent = "Algo salió mal. Probá de nuevo.";
      resetFormError.classList.remove("hidden");
    }
    resetSubmit.disabled = false;
    resetSubmit.textContent = "Cambiar contraseña";
  }
});
