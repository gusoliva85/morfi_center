/**
 * admin-usuarios.js · pages/admin/usuarios.html (`03_Roadmap.md` T-1.11.6).
 *
 * Gateada con `requireRole("ADMIN")`. Tabla de usuarios (filtro por rol +
 * paginación), alta de ADMIN/DELIVERY (`POST /users`) y, por fila, cambiar
 * rol o suspender/activar (`PATCH /users/{id}`).
 */

import { ApiError, api } from "../api.js";
import { paintSessionSlot, requireRole } from "../auth.js";
import { $, $$ } from "../ui.js";

const ROLE_LABEL = { CUSTOMER: "Cliente", ADMIN: "Admin", DELIVERY: "Delivery" };
const ROLES = ["CUSTOMER", "ADMIN", "DELIVERY"];

const user = await requireRole("ADMIN");
paintSessionSlot(user);

const state = { role: "", page: 1, pageSize: 20, total: 0 };

// ── Filtro por rol ─────────────────────────────────────
$$("[data-filter]").forEach((btn) => {
  btn.addEventListener("click", () => {
    $$("[data-filter]").forEach((b) => {
      const active = b === btn;
      b.setAttribute("aria-pressed", String(active));
      b.classList.toggle("bg-bark", active);
      b.classList.toggle("text-cream", active);
      b.classList.toggle("border-2", !active);
      b.classList.toggle("border-bark/15", !active);
      b.classList.toggle("text-bark/60", !active);
    });
    state.role = btn.dataset.filter;
    state.page = 1;
    loadUsers();
  });
});

// ── Paginación ──────────────────────────────────────────
$("[data-prev-page]").addEventListener("click", () => {
  if (state.page > 1) {
    state.page -= 1;
    loadUsers();
  }
});
$("[data-next-page]").addEventListener("click", () => {
  if (state.page * state.pageSize < state.total) {
    state.page += 1;
    loadUsers();
  }
});

function statusClasses(status) {
  return status === "ACTIVE"
    ? "rounded-full bg-forest/12 px-2.5 py-1 text-[11px] font-semibold text-forest"
    : "rounded-full bg-brick/12 px-2.5 py-1 text-[11px] font-semibold text-brick";
}

function statusLabel(status) {
  return status === "ACTIVE" ? "Activo" : status === "SUSPENDED" ? "Suspendido" : "Inactivo";
}

async function updateUser(id, patch) {
  try {
    await api.patch(`/users/${id}`, patch);
    await loadUsers();
  } catch (err) {
    window.alert(err instanceof ApiError ? err.message : "Algo salió mal. Probá de nuevo.");
  }
}

function buildRow(u) {
  const tr = document.createElement("tr");
  tr.className = "border-b border-bark/8 last:border-0";

  const tdName = document.createElement("td");
  tdName.className = "px-4 py-3 font-medium";
  tdName.textContent = `${u.first_name} ${u.last_name}`;

  const tdEmail = document.createElement("td");
  tdEmail.className = "px-4 py-3 text-bark/60";
  tdEmail.textContent = u.email;

  const tdRole = document.createElement("td");
  tdRole.className = "px-4 py-3";
  const roleSelect = document.createElement("select");
  roleSelect.className =
    "rounded-lg border-2 border-bark/15 bg-cream px-2 py-1 text-[12px] focus:border-forest focus:outline-none";
  roleSelect.setAttribute("aria-label", `Rol de ${u.first_name} ${u.last_name}`);
  ROLES.forEach((value) => {
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = ROLE_LABEL[value];
    opt.selected = value === u.role;
    roleSelect.appendChild(opt);
  });
  roleSelect.addEventListener("change", () => updateUser(u.id, { role: roleSelect.value }));
  tdRole.appendChild(roleSelect);

  const tdStatus = document.createElement("td");
  tdStatus.className = "px-4 py-3";
  const badge = document.createElement("span");
  badge.className = statusClasses(u.status);
  badge.textContent = statusLabel(u.status);
  tdStatus.appendChild(badge);

  const tdActions = document.createElement("td");
  tdActions.className = "px-4 py-3";
  const toggleBtn = document.createElement("button");
  toggleBtn.type = "button";
  const nextStatus = u.status === "ACTIVE" ? "SUSPENDED" : "ACTIVE";
  toggleBtn.textContent = u.status === "ACTIVE" ? "Suspender" : "Activar";
  toggleBtn.className =
    "blob border-2 border-bark/20 px-3 py-1 text-[12px] transition hover:bg-bark hover:text-cream";
  toggleBtn.addEventListener("click", () => updateUser(u.id, { status: nextStatus }));
  tdActions.appendChild(toggleBtn);

  tr.append(tdName, tdEmail, tdRole, tdStatus, tdActions);
  return tr;
}

async function loadUsers() {
  const body = $("[data-users-body]");
  body.replaceChildren();
  const loadingRow = document.createElement("tr");
  const loadingCell = document.createElement("td");
  loadingCell.colSpan = 5;
  loadingCell.className = "px-4 py-6 text-center text-bark/45";
  loadingCell.textContent = "Cargando…";
  loadingRow.appendChild(loadingCell);
  body.appendChild(loadingRow);

  try {
    const page = await api.get("/users", {
      params: { role: state.role || undefined, page: state.page, page_size: state.pageSize },
    });
    state.total = page.total;

    body.replaceChildren();
    if (page.items.length === 0) {
      const emptyRow = document.createElement("tr");
      const emptyCell = document.createElement("td");
      emptyCell.colSpan = 5;
      emptyCell.className = "px-4 py-6 text-center text-bark/45";
      emptyCell.textContent = "No hay usuarios con ese filtro.";
      emptyRow.appendChild(emptyCell);
      body.appendChild(emptyRow);
    } else {
      page.items.forEach((u) => body.appendChild(buildRow(u)));
    }

    const from = page.total === 0 ? 0 : (state.page - 1) * state.pageSize + 1;
    const to = Math.min(state.page * state.pageSize, page.total);
    $("[data-page-info]").textContent = `${from}–${to} de ${page.total}`;
    $("[data-prev-page]").disabled = state.page <= 1;
    $("[data-next-page]").disabled = state.page * state.pageSize >= page.total;
  } catch (err) {
    body.replaceChildren();
    const errorRow = document.createElement("tr");
    const errorCell = document.createElement("td");
    errorCell.colSpan = 5;
    errorCell.className = "px-4 py-6 text-center text-brick";
    errorCell.textContent =
      err instanceof ApiError ? err.message : "No pudimos cargar los usuarios.";
    errorRow.appendChild(errorCell);
    body.appendChild(errorRow);
  }
}

// ── Panel de alta ───────────────────────────────────────
const createPanel = $("[data-create-panel]");
const createForm = $("#create-form");
const createError = $('[data-error="create-form"]');
const createSuccess = $('[data-success="create-form"]');
const createSubmit = $("[data-submit-create]");
const deliveryFields = $("[data-delivery-fields]");

$("[data-toggle-create]").addEventListener("click", () => {
  createPanel.hidden = !createPanel.hidden;
});
$("[data-cancel-create]").addEventListener("click", () => {
  createPanel.hidden = true;
  createForm.reset();
  createError.classList.add("hidden");
  createSuccess.classList.add("hidden");
});
$("#c_role").addEventListener("change", (event) => {
  deliveryFields.hidden = event.target.value !== "DELIVERY";
});

createForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  createError.classList.add("hidden");
  createSuccess.classList.add("hidden");

  const role = $("#c_role").value;
  const payload = {
    first_name: $("#c_first_name").value.trim(),
    last_name: $("#c_last_name").value.trim(),
    email: $("#c_email").value.trim(),
    phone: $("#c_phone").value.trim() || undefined,
    role,
    password: $("#c_password").value.trim() || undefined,
  };
  if (role === "DELIVERY") {
    payload.vehicle_type = $("#c_vehicle").value;
    payload.capacity = Number($("#c_capacity").value) || undefined;
  }

  createSubmit.disabled = true;
  createSubmit.textContent = "Creando…";

  try {
    const created = await api.post("/users", payload);
    createSuccess.textContent = created.temporary_password
      ? `Usuario creado. Contraseña temporal (copiala, no se vuelve a mostrar): ${created.temporary_password}`
      : "Usuario creado.";
    createSuccess.classList.remove("hidden");
    createForm.reset();
    deliveryFields.hidden = true;
    await loadUsers();
  } catch (err) {
    createError.textContent =
      err instanceof ApiError ? err.message : "Algo salió mal. Probá de nuevo.";
    createError.classList.remove("hidden");
  } finally {
    createSubmit.disabled = false;
    createSubmit.textContent = "Crear usuario";
  }
});

await loadUsers();
