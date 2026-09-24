import "../config.js"; // primero: api.js lee window.__MC_API__ al cargarse
import { api, ApiError } from "../api.js";
import { requireRole } from "../auth.js";
import { roleLabel } from "../format.js";
import { $, $all, toast } from "../ui.js";
import { isValidEmail, isValidName, isValidPassword } from "../validators.js";

const PAGE_SIZE = 20;

const STATUS_LABELS = { ACTIVE: "Activo", SUSPENDED: "Suspendido", INACTIVE: "Inactivo" };

// Página exclusiva de ADMIN: sin sesión o con otro rol, requireRole()
// redirige a login (o a donde le corresponda) antes de que se ejecute nada más.
const me = await requireRole("ADMIN");

const rowsBody = $("[data-user-rows]");
const listError = $("[data-list-error]");
const pageSummary = $("[data-page-summary]");
const prevButton = $("[data-prev-page]");
const nextButton = $("[data-next-page]");

// `items` vive acá (no solo en el DOM) para poder actualizar una fila sin
// pedirle la lista de nuevo al servidor: crear/editar ya devuelven el usuario
// actualizado en la propia respuesta, así que no hace falta "creer" que un
// segundo pedido va a traer lo recién escrito — a veces esa segunda lectura
// llega antes de que el propio servidor la vea (ya documentado en T-1.4.2 /
// T-1.9.1, exclusivo de este entorno de desarrollo), y sin esto la tabla se
// quedaría mostrando el dato viejo hasta que el usuario recargue a mano.
let state = { role: "", page: 1, total: 0, items: [] };

function roleBadgeClass(role) {
  if (role === "ADMIN") return "bg-brick/12 text-brick";
  if (role === "DELIVERY") return "bg-mustard/20 text-bark/80";
  return "bg-forest/12 text-forest"; // CUSTOMER
}

function statusBadgeClass(status) {
  return status === "ACTIVE" ? "bg-forest/12 text-forest" : "bg-brick/12 text-brick";
}

function renderRows() {
  if (state.items.length === 0) {
    rowsBody.innerHTML = `<tr><td class="px-4 py-6 text-bark/40" colspan="5">No hay usuarios con ese filtro.</td></tr>`;
    return;
  }

  rowsBody.innerHTML = state.items
    .map((user) => {
      const isSelf = user.id === me.id;
      const nextStatus = user.status === "ACTIVE" ? "SUSPENDED" : "ACTIVE";
      const statusButtonLabel = user.status === "ACTIVE" ? "Suspender" : "Reactivar";

      return `
        <tr class="border-b border-bark/8 last:border-0" data-row="${user.id}">
          <td class="px-4 py-3">
            <div class="font-semibold">${escapeHtml(user.first_name)} ${escapeHtml(user.last_name)}</div>
            ${isSelf ? '<div class="text-[11px] text-bark/40">(vos)</div>' : ""}
          </td>
          <td class="px-4 py-3 text-bark/70">${escapeHtml(user.email)}</td>
          <td class="px-4 py-3">
            ${
              isSelf
                ? `<span class="rounded-full px-2.5 py-1 text-[11px] font-semibold ${roleBadgeClass(user.role)}">${roleLabel(user.role)}</span>`
                : `<select
                     class="rounded-full border-2 border-bark/15 bg-cream px-2.5 py-1 text-[12px]"
                     data-role-select
                     data-user-id="${user.id}"
                     data-current-role="${user.role}"
                   >
                     <option value="CUSTOMER" ${user.role === "CUSTOMER" ? "selected" : ""}>Cliente</option>
                     <option value="ADMIN" ${user.role === "ADMIN" ? "selected" : ""}>Admin</option>
                     <option value="DELIVERY" ${user.role === "DELIVERY" ? "selected" : ""}>Repartidor/a</option>
                   </select>`
            }
          </td>
          <td class="px-4 py-3">
            <span class="rounded-full px-2.5 py-1 text-[11px] font-semibold ${statusBadgeClass(user.status)}">
              ${STATUS_LABELS[user.status] ?? user.status}
            </span>
          </td>
          <td class="px-4 py-3">
            ${
              isSelf
                ? '<span class="text-[12px] text-bark/35">—</span>'
                : `<button
                     class="rounded-full border-2 border-bark/20 px-3 py-1 text-[12px] font-semibold hover:bg-bark hover:text-cream"
                     type="button"
                     data-status-toggle
                     data-user-id="${user.id}"
                     data-next-status="${nextStatus}"
                   >${statusButtonLabel}</button>`
            }
          </td>
        </tr>
      `;
    })
    .join("");
}

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value ?? "";
  return div.innerHTML;
}

async function loadUsers() {
  listError.classList.add("hidden");
  try {
    const query = new URLSearchParams({ page: state.page, page_size: PAGE_SIZE });
    if (state.role) query.set("role", state.role);
    const data = await api.get(`/users?${query}`);
    state.total = data.total;
    state.items = data.items;
    renderRows();
    updatePagination();
  } catch (err) {
    listError.textContent =
      err instanceof ApiError ? err.message : "No pudimos cargar la lista. Probá de nuevo.";
    listError.classList.remove("hidden");
  }
}

function updatePagination() {
  const lastPage = Math.max(1, Math.ceil(state.total / PAGE_SIZE));
  pageSummary.textContent = `Página ${state.page} de ${lastPage} · ${state.total} usuarios`;
  prevButton.disabled = state.page <= 1;
  nextButton.disabled = state.page >= lastPage;
}

prevButton.addEventListener("click", () => {
  if (state.page > 1) {
    state.page -= 1;
    loadUsers();
  }
});
nextButton.addEventListener("click", () => {
  state.page += 1;
  loadUsers();
});

// ---------- filtro por rol ----------

$all("[data-role-value]").forEach((button) => {
  button.addEventListener("click", () => {
    state.role = button.dataset.roleValue;
    state.page = 1;
    $all("[data-role-value]").forEach((b) => {
      const active = b === button;
      b.classList.toggle("bg-bark", active);
      b.classList.toggle("text-cream", active);
      b.classList.toggle("border-2", !active);
      b.classList.toggle("border-bark/15", !active);
      b.classList.toggle("text-bark/60", !active);
    });
    loadUsers();
  });
});

// ---------- acciones por fila ----------

/**
 * Reemplaza en memoria el usuario que cambió y vuelve a pintar la tabla con
 * la respuesta que ya devolvió el PATCH — no hace falta volver a pedirle la
 * lista al servidor (ni esperar a que esa lectura "vea" lo recién escrito).
 */
function applyUpdatedUser(updatedUser) {
  state.items = state.items.map((u) => (u.id === updatedUser.id ? updatedUser : u));
  renderRows();
}

rowsBody.addEventListener("change", async (event) => {
  const select = event.target.closest("[data-role-select]");
  if (!select) return;

  const userId = select.dataset.userId;
  const previousValue = select.dataset.currentRole; // el valor ANTES de este cambio
  try {
    const updated = await api.patch(`/users/${userId}`, { role: select.value });
    toast("Rol actualizado.");
    applyUpdatedUser(updated);
  } catch (err) {
    select.value = previousValue; // revertir: el cambio no se guardó
    toast(err instanceof ApiError ? err.message : "No pudimos cambiar el rol.");
  }
});

rowsBody.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-status-toggle]");
  if (!button) return;

  button.disabled = true;
  try {
    const updated = await api.patch(`/users/${button.dataset.userId}`, {
      status: button.dataset.nextStatus,
    });
    toast(button.dataset.nextStatus === "ACTIVE" ? "Usuario reactivado." : "Usuario suspendido.");
    applyUpdatedUser(updated);
  } catch (err) {
    toast(err instanceof ApiError ? err.message : "No pudimos actualizar el estado.");
    button.disabled = false;
  }
});

// ---------- alta de ADMIN/DELIVERY ----------

const createPanel = $("[data-create-panel]");
const createForm = $("[data-create-form]");
const createError = $("[data-create-error]");
const createSubmit = $("[data-create-submit]");
const deliveryFields = $("[data-delivery-fields]");

$("[data-toggle-create]").addEventListener("click", () => {
  createPanel.classList.toggle("hidden");
});
$("[data-cancel-create]").addEventListener("click", () => {
  createForm.reset();
  clearAllFieldErrors();
  createPanel.classList.add("hidden");
});

createForm.role.addEventListener("change", updateDeliveryFieldsVisibility);
function updateDeliveryFieldsVisibility() {
  deliveryFields.classList.toggle("hidden", createForm.role.value !== "DELIVERY");
}
updateDeliveryFieldsVisibility();

const createFieldValidators = {
  first_name: (v) => (isValidName(v) ? null : "Requerido."),
  last_name: (v) => (isValidName(v) ? null : "Requerido."),
  email: (v) => (isValidEmail(v.trim()) ? null : "El email no tiene un formato válido."),
  password: (v) =>
    isValidPassword(v) ? null : "Debe tener al menos 8 caracteres, con una letra y un número.",
};

function showFieldError(name, message) {
  const box = $(`[data-field-error="${name}"]`, createForm);
  if (box) {
    box.textContent = message;
    box.classList.remove("hidden");
  }
}
function clearFieldError(name) {
  const box = $(`[data-field-error="${name}"]`, createForm);
  if (box) {
    box.textContent = "";
    box.classList.add("hidden");
  }
}
function clearAllFieldErrors() {
  Object.keys(createFieldValidators).forEach(clearFieldError);
  clearFieldError("vehicle_type");
}

function validateCreateForm() {
  let valid = true;
  for (const [name, validate] of Object.entries(createFieldValidators)) {
    const message = validate(createForm[name].value);
    if (message) {
      showFieldError(name, message);
      valid = false;
    } else {
      clearFieldError(name);
    }
  }
  return valid;
}

createForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  createError.classList.add("hidden");
  if (!validateCreateForm()) return;

  const payload = {
    role: createForm.role.value,
    first_name: createForm.first_name.value.trim(),
    last_name: createForm.last_name.value.trim(),
    email: createForm.email.value.trim(),
    password: createForm.password.value,
    phone: createForm.phone.value.trim() || undefined,
  };
  if (createForm.role.value === "DELIVERY") {
    payload.vehicle_type = createForm.vehicle_type.value;
    payload.capacity = createForm.capacity.value ? Number(createForm.capacity.value) : undefined;
  }

  createSubmit.disabled = true;
  createSubmit.textContent = "Creando…";
  try {
    const created = await api.post("/users", payload);
    toast(`Usuario creado: ${created.email}`);
    createForm.reset();
    updateDeliveryFieldsVisibility();
    clearAllFieldErrors();
    createPanel.classList.add("hidden");

    // Se agrega directo con lo que ya devolvió el POST, en vez de volver a
    // pedirle la lista al servidor (mismo motivo que `applyUpdatedUser`). Solo
    // si entra en el filtro actual — si estás viendo "Clientes" y creaste un
    // repartidor, no correspondería que aparezca ahí. Se suma al final de la
    // página actual: con la escala de usuarios de staff de este proyecto no
    // amerita la lógica de intercalarlo en la página real que le tocaría por
    // paginación (siempre la última, por orden ascendente de id).
    if (!state.role || state.role === created.role) {
      state.items = [...state.items, created];
      state.total += 1;
      renderRows();
      updatePagination();
    }
  } catch (err) {
    if (err instanceof ApiError && err.code === "VALIDATION_ERROR") {
      for (const field of err.details?.fields ?? []) {
        showFieldError(field.field, field.message);
      }
    } else if (err instanceof ApiError && err.code === "CONFLICT") {
      showFieldError("email", err.message);
    } else {
      createError.textContent =
        err instanceof ApiError ? err.message : "No pudimos crear el usuario. Probá de nuevo.";
      createError.classList.remove("hidden");
    }
  } finally {
    createSubmit.disabled = false;
    createSubmit.textContent = "Crear usuario";
  }
});

await loadUsers();
