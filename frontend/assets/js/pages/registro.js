import "../config.js"; // primero: api.js lee window.__MC_API__ al cargarse
import { ApiError } from "../api.js";
import { register } from "../auth.js";
import { $ } from "../ui.js";

// Mismas reglas que el backend (app/services/user_service.py y
// app/schemas/auth.py), para que el error aparezca al tipear y no recién
// después de un viaje al servidor. La validación real sigue siendo la del
// backend: esto es solo para que la experiencia no se sienta a destiempo.
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

function isValidName(value) {
  return Boolean(value && value.trim());
}

function isValidEmail(value) {
  return EMAIL_RE.test(value.trim());
}

function isValidPassword(value) {
  if (value.length < 8 || value.length > 72) return false;
  return /[a-zA-Z]/.test(value) && /[0-9]/.test(value);
}

const form = $("[data-register-form]");
const generalError = $("[data-error]");
const submitButton = $("[data-submit]");

const fields = {
  first_name: {
    input: form.first_name,
    validate: (v) => (isValidName(v) ? null : "Requerido."),
  },
  last_name: {
    input: form.last_name,
    validate: (v) => (isValidName(v) ? null : "Requerido."),
  },
  email: {
    input: form.email,
    validate: (v) => {
      if (!v.trim()) return "Requerido.";
      return isValidEmail(v) ? null : "El email no tiene un formato válido.";
    },
  },
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

function showFieldError(name, message) {
  const box = $(`[data-field-error="${name}"]`);
  if (!box) return;
  box.textContent = message;
  box.classList.remove("hidden");
  fields[name]?.input.classList.add("border-brick/60");
}

function clearFieldError(name) {
  const box = $(`[data-field-error="${name}"]`);
  if (!box) return;
  box.textContent = "";
  box.classList.add("hidden");
  fields[name]?.input.classList.remove("border-brick/60");
}

function runValidator(name) {
  const { input, validate } = fields[name];
  const message = validate(input.value);
  if (message) showFieldError(name, message);
  else clearFieldError(name);
  return !message;
}

function validateAll() {
  // password_confirm depende de password: si password cambió después de
  // haber tipeado la repetición, hay que revalidarla también.
  return Object.keys(fields)
    .map(runValidator)
    .every(Boolean);
}

function wireLiveValidation(name) {
  const { input } = fields[name];
  let touched = false;
  input.addEventListener("blur", () => {
    touched = true;
    runValidator(name);
  });
  input.addEventListener("input", () => {
    if (touched) runValidator(name);
    // Si ya se tocó la repetición, que reaccione a los cambios en la
    // contraseña principal (si no, "coincide" quedaría mal hasta el submit).
    if (name === "password" && form.password_confirm.dataset.touched === "1") {
      runValidator("password_confirm");
    }
  });
  if (name === "password_confirm") {
    input.addEventListener("blur", () => {
      input.dataset.touched = "1";
    });
  }
}

function showGeneralError(message) {
  generalError.textContent = message;
  generalError.classList.remove("hidden");
}

function clearGeneralError() {
  generalError.textContent = "";
  generalError.classList.add("hidden");
}

/** Aplica los errores 422/409 del backend sobre los campos correspondientes. */
function applyServerError(err) {
  if (err.code === "CONFLICT") {
    showFieldError("email", err.message);
    return;
  }
  const serverFields = err.details?.fields;
  if (Array.isArray(serverFields) && serverFields.length > 0) {
    for (const { field, message } of serverFields) {
      if (fields[field]) showFieldError(field, message);
      else showGeneralError(message);
    }
    return;
  }
  showGeneralError(err.message);
}

async function onSubmit(event) {
  event.preventDefault();
  clearGeneralError();

  if (!validateAll()) return;

  submitButton.disabled = true;
  submitButton.textContent = "Creando cuenta…";
  try {
    await register({
      first_name: form.first_name.value.trim(),
      last_name: form.last_name.value.trim(),
      email: form.email.value.trim(),
      password: form.password.value,
      phone: form.phone.value.trim() || undefined,
    });
    location.href = "/index.html";
  } catch (err) {
    if (err instanceof ApiError) applyServerError(err);
    else showGeneralError("No pudimos conectarnos. Revisá tu internet y probá de nuevo.");
    submitButton.disabled = false;
    submitButton.textContent = "Crear cuenta";
  }
}

Object.keys(fields).forEach(wireLiveValidation);
form.addEventListener("submit", onSubmit);
