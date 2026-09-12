/**
 * perfil.js · pages/cliente/perfil.html (`03_Roadmap.md` T-1.11.5).
 *
 * Primera pantalla realmente gateada del front: `requireRole()` sin
 * argumentos (cualquier usuario logueado, no solo CUSTOMER — así la
 * pueden abrir ADMIN/DELIVERY también). Sin sesión, redirige a
 * `login.html?next=/pages/cliente/perfil.html` y vuelve acá al loguear.
 */

import { ApiError, api } from "../api.js";
import { paintSessionSlot, requireRole } from "../auth.js";
import { formatMoney } from "../format.js";
import { $, injectPartials } from "../ui.js";

const ROLE_LABEL = {
  CUSTOMER: "Cliente",
  ADMIN: "Administrador",
  DELIVERY: "Repartidor",
};

await injectPartials();
const user = await requireRole();
paintSessionSlot(user);

const form = $("#perfil-form");
const submitBtn = $("[data-submit]");
const formError = $('[data-error="form"]');
const formSuccess = $('[data-success="form"]');

function fillForm(u) {
  $("#first_name").value = u.first_name;
  $("#last_name").value = u.last_name;
  $("#email").value = u.email;
  $("#phone").value = u.phone || "";
  $("[data-role]").textContent = ROLE_LABEL[u.role] || u.role;
}

fillForm(user);
$("[data-balance]").textContent = formatMoney(user.balance ?? 0);

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

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  formError.classList.add("hidden");
  formSuccess.classList.add("hidden");
  ["first_name", "last_name", "phone"].forEach((f) => setFieldError(f, null));

  submitBtn.disabled = true;
  submitBtn.textContent = "Guardando…";

  try {
    const updated = await api.patch("/users/me/profile", {
      first_name: $("#first_name").value.trim(),
      last_name: $("#last_name").value.trim(),
      phone: $("#phone").value.trim() || null,
    });
    fillForm(updated);
    formSuccess.textContent = "Guardado.";
    formSuccess.classList.remove("hidden");
  } catch (err) {
    if (err instanceof ApiError && err.details?.field && $(`[data-error="${err.details.field}"]`)) {
      setFieldError(err.details.field, err.message);
    } else if (err instanceof ApiError) {
      formError.textContent = err.message;
      formError.classList.remove("hidden");
    } else {
      formError.textContent = "Algo salió mal. Probá de nuevo.";
      formError.classList.remove("hidden");
    }
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Guardar cambios";
  }
});
