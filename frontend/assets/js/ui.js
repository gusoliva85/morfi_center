// Helpers de UI compartidos: selección de DOM, inyección de parciales y toasts.

export function $(selector, root = document) {
  return root.querySelector(selector);
}

export function $all(selector, root = document) {
  return Array.from(root.querySelectorAll(selector));
}

// Resuelto contra la URL de este módulo (no de la página que lo importa),
// así funciona igual desde index.html que desde pages/cliente/menu.html.
const PARTIALS_BASE = new URL("../../partials/", import.meta.url);

/**
 * Busca elementos con [data-partial="nombre"], reemplaza su innerHTML por el
 * contenido de partials/nombre.html, y repite hasta que no queden pendientes
 * (soporta parciales anidados, p. ej. header.html incluye top-nav.html).
 */
export async function injectPartials(root = document) {
  let pending = $all("[data-partial]:not([data-partial-loaded])", root);
  while (pending.length > 0) {
    await Promise.all(pending.map(loadPartial));
    pending = $all("[data-partial]:not([data-partial-loaded])", root);
  }
}

async function loadPartial(node) {
  const name = node.dataset.partial;
  try {
    const response = await fetch(new URL(`${name}.html`, PARTIALS_BASE));
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    node.innerHTML = await response.text();
  } catch (err) {
    console.error(`No se pudo cargar el parcial "${name}":`, err);
  } finally {
    node.setAttribute("data-partial-loaded", "");
  }
}

let toastTimer = null;

export function toast(message, { duration = 3000 } = {}) {
  let el = $("#mc-toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "mc-toast";
    el.className =
      "fixed bottom-24 left-1/2 z-50 -translate-x-1/2 whitespace-nowrap rounded-full bg-bark px-5 py-2.5 text-sm font-medium text-cream shadow-lg transition-opacity duration-300 lg:bottom-8";
    document.body.appendChild(el);
  }
  el.textContent = message;
  el.style.opacity = "1";
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    el.style.opacity = "0";
  }, duration);
}
