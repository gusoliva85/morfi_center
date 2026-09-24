import "../config.js"; // primero: api.js lee window.__MC_API__ al cargarse
import { api, ApiError } from "../api.js";
import { logout, renderSessionUI, requireRole } from "../auth.js";
import { formatMoney } from "../format.js";
import { $, injectPartials } from "../ui.js";
import { isValidName } from "../validators.js";

const ROLE_LABELS = { CUSTOMER: "Cliente", ADMIN: "Administrador/a", DELIVERY: "Repartidor/a" };

await injectPartials();
// Página exclusiva de sesión (cualquier rol logueado, RN-33 / T-1.11.4): sin
// sesión, requireRole() ya redirige a login con `next` de vuelta acá.
const me = await requireRole();

const form = $("[data-profile-form]");
const errorBox = $("[data-error]");
const successBox = $("[data-success]");
const submitButton = $("[data-submit]");

function fillForm(user) {
  form.first_name.value = user.first_name;
  form.last_name.value = user.last_name;
  form.phone.value = user.phone ?? "";
  $("[data-email]").textContent = user.email;
  $("[data-role]").textContent = ROLE_LABELS[user.role] ?? user.role;
  $("[data-balance]").textContent = formatMoney(user.balance);
}

fillForm(me);

const fields = {
  first_name: {
    input: form.first_name,
    validate: (v) => (isValidName(v) ? null : "Requerido."),
  },
  last_name: {
    input: form.last_name,
    validate: (v) => (isValidName(v) ? null : "Requerido."),
  },
};

function showFieldError(name, message) {
  const box = $(`[data-field-error="${name}"]`);
  box.textContent = message;
  box.classList.remove("hidden");
}

function clearFieldError(name) {
  const box = $(`[data-field-error="${name}"]`);
  box.textContent = "";
  box.classList.add("hidden");
}

function runValidator(name) {
  const { input, validate } = fields[name];
  const message = validate(input.value);
  if (message) showFieldError(name, message);
  else clearFieldError(name);
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
  });
});

function hideMessages() {
  errorBox.classList.add("hidden");
  successBox.classList.add("hidden");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideMessages();
  const valid = Object.keys(fields)
    .map(runValidator)
    .every(Boolean);
  if (!valid) return;

  submitButton.disabled = true;
  submitButton.textContent = "Guardando…";
  try {
    const updated = await api.patch("/users/me/profile", {
      first_name: form.first_name.value.trim(),
      last_name: form.last_name.value.trim(),
      phone: form.phone.value.trim() || null,
    });
    fillForm(updated);
    renderSessionUI(updated); // el nombre del header puede haber cambiado
    successBox.textContent = "Tus datos se guardaron.";
    successBox.classList.remove("hidden");
  } catch (err) {
    if (err instanceof ApiError && err.code === "VALIDATION_ERROR") {
      const nameField = err.details?.fields?.find((f) => f.field in fields);
      if (nameField) showFieldError(nameField.field, nameField.message);
      else {
        errorBox.textContent = err.message;
        errorBox.classList.remove("hidden");
      }
    } else if (err instanceof ApiError && err.code === "FORBIDDEN") {
      // La cuenta se deshabilitó mientras navegaba: no tiene sentido dejarla
      // seguir en una pantalla que ya no puede usar.
      await logout();
    } else if (err instanceof ApiError && err.code === "NOT_AUTHENTICATED") {
      location.href = `/pages/auth/login.html?next=${encodeURIComponent(location.pathname)}`;
    } else {
      errorBox.textContent =
        err instanceof ApiError
          ? err.message
          : "No pudimos conectarnos. Revisá tu internet y probá de nuevo.";
      errorBox.classList.remove("hidden");
    }
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Guardar cambios";
  }
});
