import "../config.js"; // primero: api.js lee window.__MC_API__ al cargarse
import { api, ApiError } from "../api.js";
import { requireRole } from "../auth.js";
import { $, $all, toast } from "../ui.js";

// Página exclusiva de ADMIN (sin sesión o con otro rol, requireRole() redirige).
await requireRole("ADMIN");

const LOGIN_URL = "/pages/auth/login.html";
const STATUS_LABEL = {
  SCHEDULED: "Por abrir",
  OPEN: "Abierto",
  CLOSED: "Cerrado",
  IN_PRODUCTION: "En producción",
  DISPATCHING: "En reparto",
  FINISHED: "Finalizado",
};
const STATUS_BADGE = {
  SCHEDULED: "bg-mustard/20 text-bark",
  OPEN: "bg-forest/12 text-forest",
  CLOSED: "bg-brick/12 text-brick",
  IN_PRODUCTION: "bg-forest text-cream",
  DISPATCHING: "bg-forest text-cream",
  FINISHED: "bg-bark/12 text-bark/70",
};
const PAST_CLOSING = ["IN_PRODUCTION", "DISPATCHING", "FINISHED"];

// Lo que el servidor devolvió por última vez. Se actualiza con la respuesta de
// cada PUT/PATCH/POST (no se vuelve a pedir la lista): esas respuestas ya traen
// el dato final, y así lo que se ve es siempre lo que quedó guardado.
const state = { template: null, timezone: null, today: null };

const form = $("[data-config-form]");
const submitButton = $("[data-submit]");
const formError = $("[data-form-error]");
const formSuccess = $("[data-form-success]");
const loadError = $("[data-load-error]");
const applyTodayWrap = $("[data-apply-today-wrap]");
const applyToday = $("[data-apply-today]");
const todayStatus = $("[data-today-status]");
const todaySummary = $("[data-today-summary]");
const todayError = $("[data-today-error]");
const todayActions = $("[data-today-actions]");
const todayHelp = $("[data-today-help]");

// ---------- utilidades ----------

function show(box, message) {
  box.textContent = message;
  box.classList.remove("hidden");
}

function hide(box) {
  box.textContent = "";
  box.classList.add("hidden");
}

function goToLogin() {
  location.href = `${LOGIN_URL}?next=${encodeURIComponent(location.pathname)}`;
}

/** Un error que no es de validación: si la sesión se cayó, a login; si no, el mensaje. */
function plainMessage(err) {
  if (err instanceof ApiError && err.code === "NOT_AUTHENTICATED") {
    goToLogin();
    return "";
  }
  return err instanceof ApiError
    ? err.message
    : "No pudimos conectarnos. Revisá tu internet y probá de nuevo.";
}

function fieldErrorBox(name) {
  return $(`[data-field-error="${name}"]`);
}

function clearErrors() {
  hide(formError);
  hide(formSuccess);
  $all("[data-field-error]").forEach(hide);
}

/**
 * Muestra un 422 del backend debajo de cada campo. `mapField(campoDelServidor)`
 * dice a qué campo del formulario corresponde (o `null` para el mensaje
 * general): los nombres de la API no siempre son los del formulario.
 */
function showValidation(err, mapField, generalPrefix = "") {
  const general = [];
  for (const { field, message } of err.details?.fields ?? []) {
    const target = mapField(field);
    const box = target && fieldErrorBox(target);
    if (box) show(box, message);
    else general.push(message);
  }
  if (general.length > 0 || !(err.details?.fields ?? []).length) {
    show(formError, generalPrefix + (general.join(" ") || err.message));
  }
}

function formatServiceDate(isoDate) {
  const [year, month, day] = isoDate.split("-");
  return `${day}/${month}/${year}`;
}

// ---------- formulario ----------

function fillForm() {
  const t = state.template;
  form.open.value = t.open;
  form.close.value = t.close;
  form.prep_eta.value = t.prep_eta ?? "";
  form.dispatch_eta.value = t.dispatch_eta ?? "";
  form.cancel_window_min.value = t.cancel_window_min;
  form.timezone.value = state.timezone;
  $all('input[name="weekday"]').forEach((box) => {
    box.checked = t.weekdays.includes(Number(box.value));
  });
}

function readTemplate() {
  const cancel = form.cancel_window_min.value.trim();
  return {
    open: form.open.value,
    close: form.close.value,
    prep_eta: form.prep_eta.value || null,
    dispatch_eta: form.dispatch_eta.value || null,
    cancel_window_min: cancel === "" ? null : Number(cancel),
    weekdays: $all('input[name="weekday"]:checked').map((box) => Number(box.value)),
  };
}

/** "Aplicar al turno de hoy" solo tiene sentido si ese turno todavía se puede editar. */
function todayIsEditable() {
  const today = state.today;
  return Boolean(today) && !today.closed_effects_applied_at && !PAST_CLOSING.includes(today.status);
}

// ---------- turno de hoy ----------

function renderToday() {
  const today = state.today;
  hide(todayError);

  if (!today) {
    todayStatus.textContent = "Sin turno";
    todayStatus.className = "rounded-full px-3 py-1 text-[12px] font-semibold bg-bark/8 text-bark/60";
    todaySummary.textContent =
      "Hoy no es un día de operación, así que no hay turno. Los días se eligen en la plantilla.";
    todayActions.classList.add("hidden");
    todayHelp.classList.add("hidden");
  } else {
    todayStatus.textContent = STATUS_LABEL[today.status] ?? today.status;
    todayStatus.className = `rounded-full px-3 py-1 text-[12px] font-semibold ${
      STATUS_BADGE[today.status] ?? "bg-bark/8 text-bark/60"
    }`;
    todaySummary.textContent =
      `${formatServiceDate(today.service_date)} · abre ${today.open_time} · cierra ${today.close_time}` +
      ` · se puede cancelar hasta ${today.cancel_window_min} min antes del cierre`;
    todayActions.classList.remove("hidden");
    todayActions.classList.add("flex");
    todayHelp.classList.remove("hidden");

    $('[data-action="open"]').disabled = today.status !== "SCHEDULED";
    $('[data-action="close"]').disabled = today.status !== "OPEN";
    $('[data-action="to_production"]').disabled = today.status !== "CLOSED";
  }

  const editable = todayIsEditable();
  applyTodayWrap.classList.toggle("hidden", !editable);
  applyTodayWrap.classList.toggle("flex", editable);
}

const CONFIRMATIONS = {
  close: "¿Cerrar los pedidos ahora? Los clientes ya no van a poder pedir hoy.",
  to_production:
    "¿Empezar a cocinar? Después ya no se van a poder cambiar los horarios de este turno.",
};

async function runTransition(action, button) {
  if (CONFIRMATIONS[action] && !window.confirm(CONFIRMATIONS[action])) return;
  hide(todayError);
  $all("[data-action]").forEach((b) => (b.disabled = true));
  try {
    state.today = await api.post(`/shift/${state.today.id}/transition`, { action });
    toast("Listo");
  } catch (err) {
    const message = plainMessage(err);
    if (message) show(todayError, message);
  }
  renderToday();
}

$all("[data-action]").forEach((button) => {
  button.addEventListener("click", () => runTransition(button.dataset.action, button));
});

// ---------- guardar ----------

// Nombres que la API de turnos usa distinto a los del formulario.
const SHIFT_FIELD = { open_time: "open", close_time: "close" };

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearErrors();

  const value = readTemplate();
  const timezone = form.timezone.value.trim();
  const notes = [];

  submitButton.disabled = true;
  submitButton.textContent = "Guardando…";
  try {
    // 1) La plantilla (turnos futuros). Si falla, no se sigue.
    try {
      const saved = await api.put("/settings/shift.default", { value });
      state.template = saved.value;
      notes.push("La plantilla del turno se guardó: rige para los turnos que se creen desde ahora.");
    } catch (err) {
      if (err instanceof ApiError && err.code === "VALIDATION_ERROR") {
        showValidation(err, (f) => (f.startsWith("weekdays") ? "weekdays" : f === "value" ? null : f));
        return;
      }
      throw err;
    }

    // 2) La zona horaria.
    try {
      const saved = await api.put("/settings/timezone", { value: timezone });
      state.timezone = saved.value;
    } catch (err) {
      if (err instanceof ApiError && err.code === "VALIDATION_ERROR") {
        showValidation(err, () => "timezone");
        fillForm();
        show(formSuccess, notes.join(" "));
        return;
      }
      throw err;
    }

    // 3) Opcionalmente, el turno de hoy (si todavía se puede editar).
    if (todayIsEditable() && applyToday.checked) {
      const today = state.today;
      try {
        state.today = await api.patch(`/shift/${today.id}`, {
          open_time: value.open,
          close_time: value.close,
          prep_eta: value.prep_eta,
          dispatch_eta: value.dispatch_eta,
          cancel_window_min: value.cancel_window_min,
        });
        notes.push("El turno de hoy también se actualizó.");
      } catch (err) {
        if (err instanceof ApiError && err.code === "VALIDATION_ERROR") {
          showValidation(err, (f) => SHIFT_FIELD[f] ?? (f === "value" ? null : f), "Turno de hoy: ");
        } else if (err instanceof ApiError) {
          show(formError, `El turno de hoy no se pudo cambiar: ${err.message}`);
        } else {
          throw err;
        }
      }
    }

    fillForm();
    renderToday();
    show(formSuccess, notes.join(" "));
    toast("Configuración guardada");
  } catch (err) {
    const message = plainMessage(err);
    if (message) show(formError, message);
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Guardar cambios";
  }
});

// ---------- carga inicial ----------

async function load() {
  hide(loadError);
  try {
    const [settings, current] = await Promise.all([
      api.get("/settings"),
      api.get("/shift/current", { auth: false }), // también crea el turno de hoy si corresponde
    ]);
    const byKey = Object.fromEntries(settings.items.map((item) => [item.key, item.value]));
    state.template = byKey["shift.default"];
    state.timezone = byKey["timezone"];

    if (current.status !== "NO_SERVICE") {
      const list = await api.get(`/shift?date=${current.service_date}`);
      state.today = list.items[0] ?? null;
    }

    fillForm();
    renderToday();
  } catch (err) {
    const message = plainMessage(err);
    if (message) show(loadError, message);
  }
}

await load();
