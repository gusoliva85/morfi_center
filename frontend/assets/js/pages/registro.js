/**
 * registro.js · pages/auth/registro.html (`03_Roadmap.md` T-1.11.2).
 *
 * Validación en vivo (espejo liviano de `user_service` en el backend, para
 * feedback inmediato) + `auth.register()` que da de alta y loguea en el
 * mismo paso. El backend sigue siendo la fuente de verdad: cualquier error
 * que devuelva (p. ej. email repetido) se muestra en el campo que
 * corresponda vía `details.field`, o en el banner del form si no aplica a
 * un campo puntual.
 */

import { ApiError } from "../api.js";
import { homeForRole, register } from "../auth.js";
import { $ } from "../ui.js";

const form = $("#registro-form");
const submitBtn = $("[data-submit]");
const formError = $('[data-error="form"]');

const NAME_RE = /^[\p{L} '.-]{2,80}$/u;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_RE = /^[+(]?\d[\d\s()-]{5,19}$/;

const fields = {
  first_name: $("#first_name"),
  last_name: $("#last_name"),
  email: $("#email"),
  phone: $("#phone"),
  password: $("#password"),
  password_confirm: $("#password_confirm"),
};

function errorEl(field) {
  return $(`[data-error="${field}"]`);
}

function setFieldError(field, message) {
  const el = errorEl(field);
  if (!el) return;
  if (message) {
    el.textContent = message;
    el.classList.remove("hidden");
    fields[field]?.classList.add("border-brick");
  } else {
    el.textContent = "";
    el.classList.add("hidden");
    fields[field]?.classList.remove("border-brick");
  }
}

function hideFormError() {
  formError.classList.add("hidden");
  formError.textContent = "";
}

function showFormError(message) {
  formError.textContent = message;
  formError.classList.remove("hidden");
}

/** @returns {string|null} mensaje de error, o `null` si es válido. */
function validateName(value, label) {
  const trimmed = value.trim();
  if (!trimmed) return `Ingresá tu ${label}.`;
  if (/\d/.test(trimmed) || !NAME_RE.test(trimmed)) {
    return `El ${label} no puede tener números.`;
  }
  return null;
}

function validateEmail(value) {
  if (!value.trim()) return "Ingresá tu email.";
  if (!EMAIL_RE.test(value.trim())) return "Ese email no parece válido.";
  return null;
}

function validatePhone(value) {
  if (!value.trim()) return null; // opcional
  if (!PHONE_RE.test(value.trim())) return "Ese teléfono no parece válido.";
  return null;
}

function validatePassword(value) {
  if (value.length < 8) return "Mínimo 8 caracteres.";
  if (!/[a-zA-Z]/.test(value) || !/\d/.test(value)) {
    return "Tiene que tener al menos una letra y un número.";
  }
  return null;
}

function validateConfirm(value, password) {
  if (!value) return "Repetí la contraseña.";
  if (value !== password) return "No coincide con la contraseña.";
  return null;
}

const VALIDATORS = {
  first_name: () => validateName(fields.first_name.value, "nombre"),
  last_name: () => validateName(fields.last_name.value, "apellido"),
  email: () => validateEmail(fields.email.value),
  phone: () => validatePhone(fields.phone.value),
  password: () => validatePassword(fields.password.value),
  password_confirm: () => validateConfirm(fields.password_confirm.value, fields.password.value),
};

function validateField(name) {
  const message = VALIDATORS[name]();
  setFieldError(name, message);
  return message === null;
}

function validateAll() {
  return Object.keys(VALIDATORS).reduce((ok, name) => validateField(name) && ok, true);
}

// Validación en vivo: al salir del campo, y mientras se corrige un error visible.
Object.entries(fields).forEach(([name, el]) => {
  el?.addEventListener("blur", () => validateField(name));
  el?.addEventListener("input", () => {
    if (!errorEl(name)?.classList.contains("hidden")) validateField(name);
  });
});

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideFormError();

  if (!validateAll()) return;

  submitBtn.disabled = true;
  submitBtn.textContent = "Creando cuenta…";

  try {
    const user = await register({
      first_name: fields.first_name.value.trim(),
      last_name: fields.last_name.value.trim(),
      email: fields.email.value.trim(),
      phone: fields.phone.value.trim() || undefined,
      password: fields.password.value,
    });
    window.location.href = homeForRole(user.role);
  } catch (err) {
    if (err instanceof ApiError && err.details?.field && fields[err.details.field]) {
      setFieldError(err.details.field, err.message);
    } else if (err instanceof ApiError) {
      showFormError(err.message);
    } else {
      showFormError("Algo salió mal. Probá de nuevo.");
    }
    submitBtn.disabled = false;
    submitBtn.textContent = "Crear cuenta";
  }
});
