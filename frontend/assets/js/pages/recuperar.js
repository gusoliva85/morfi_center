import "../config.js"; // primero: api.js lee window.__MC_API__ al cargarse
import { ApiError } from "../api.js";
import { requestPasswordReset, resetPassword } from "../auth.js";
import { $ } from "../ui.js";
import { isValidEmail, isValidPassword } from "../validators.js";

const token = new URLSearchParams(location.search).get("token");

if (token) {
  setupResetStep(token);
} else {
  setupRequestStep();
}

// ===== Paso 1: pedir el link =====

function setupRequestStep() {
  $('[data-step="request"]').classList.remove("hidden");

  const form = $("[data-request-form]");
  const errorBox = $("[data-request-error]");
  const fieldError = $('[data-field-error="email"]');
  const submitButton = $("[data-request-submit]");

  function validateEmail() {
    const value = form.email.value.trim();
    const message = !value
      ? "Requerido."
      : isValidEmail(value)
        ? null
        : "El email no tiene un formato válido.";
    fieldError.textContent = message ?? "";
    fieldError.classList.toggle("hidden", !message);
    return !message;
  }

  form.email.addEventListener("blur", validateEmail);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.classList.add("hidden");
    if (!validateEmail()) return;

    submitButton.disabled = true;
    submitButton.textContent = "Enviando…";
    try {
      await requestPasswordReset(form.email.value.trim());
      form.classList.add("hidden");
      $("[data-request-sent]").classList.remove("hidden");
    } catch (err) {
      // El backend responde 200 siempre que la petición sea válida (§ T-1.9.1);
      // lo único que puede fallar acá es la red o el límite de intentos.
      errorBox.textContent =
        err instanceof ApiError
          ? err.message
          : "No pudimos conectarnos. Revisá tu internet y probá de nuevo.";
      errorBox.classList.remove("hidden");
      submitButton.disabled = false;
      submitButton.textContent = "Enviar link";
    }
  });
}

// ===== Paso 2: elegir la contraseña nueva =====

function setupResetStep(resetToken) {
  $('[data-step="reset"]').classList.remove("hidden");

  const form = $("[data-reset-form]");
  const errorBox = $("[data-reset-error]");
  const submitButton = $("[data-reset-submit]");

  const fields = {
    password: {
      input: form.password,
      validate: (v) =>
        isValidPassword(v) ? null : "Debe tener al menos 8 caracteres, con una letra y un número.",
    },
    password_confirm: {
      input: form.password_confirm,
      validate: (v) => (v === form.password.value ? null : "Las contraseñas no coinciden."),
    },
  };

  function runValidator(name) {
    const { input, validate } = fields[name];
    const message = validate(input.value);
    const box = $(`[data-field-error="${name}"]`);
    box.textContent = message ?? "";
    box.classList.toggle("hidden", !message);
    return !message;
  }

  Object.keys(fields).forEach((name) => {
    const { input } = fields[name];
    let touched = false;
    input.addEventListener("blur", () => {
      touched = true;
      runValidator(name);
    });
    input.addEventListener("input", () => {
      if (touched) runValidator(name);
      if (name === "password" && form.password_confirm.dataset.touched === "1") {
        runValidator("password_confirm");
      }
    });
    if (name === "password_confirm") {
      input.addEventListener("blur", () => {
        input.dataset.touched = "1";
      });
    }
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.classList.add("hidden");
    const valid = Object.keys(fields)
      .map(runValidator)
      .every(Boolean);
    if (!valid) return;

    submitButton.disabled = true;
    submitButton.textContent = "Cambiando…";
    try {
      await resetPassword(resetToken, form.password.value);
      form.classList.add("hidden");
      $("[data-reset-done]").classList.remove("hidden");
    } catch (err) {
      if (err instanceof ApiError && err.code === "VALIDATION_ERROR") {
        const passwordField = err.details?.fields?.find((f) => f.field === "password");
        if (passwordField) {
          const box = $('[data-field-error="password"]');
          box.textContent = passwordField.message;
          box.classList.remove("hidden");
        } else {
          errorBox.textContent = err.message;
          errorBox.classList.remove("hidden");
        }
      } else if (err instanceof ApiError && err.code === "NOT_AUTHENTICATED") {
        // Link vencido, ya usado, o inválido: no hay forma de "arreglarlo" acá,
        // solo pedir uno nuevo desde el paso 1.
        errorBox.innerHTML =
          'Este link no es válido o ya venció. <a class="font-semibold underline" href="recuperar.html">Pedí uno nuevo</a>.';
        errorBox.classList.remove("hidden");
      } else {
        errorBox.textContent =
          err instanceof ApiError
            ? err.message
            : "No pudimos conectarnos. Revisá tu internet y probá de nuevo.";
        errorBox.classList.remove("hidden");
      }
      submitButton.disabled = false;
      submitButton.textContent = "Cambiar contraseña";
    }
  });
}
