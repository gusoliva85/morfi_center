/**
 * ui.js · helpers de UI compartidos.
 *
 *   - $ / $$        : selección de elementos
 *   - injectPartials: carga los parciales de /partials en los <… data-partial="x">
 *   - toast         : notificación efímera
 *
 * Sin dependencias. Se usa como módulo ES:  import { $, injectPartials, toast } from '/assets/js/ui.js'
 */

const PARTIALS_BASE = "/partials";
const MAX_PARTIAL_PASSES = 5; // evita loops si un parcial se referencia a sí mismo

/** querySelector abreviado. */
export const $ = (selector, root = document) => root.querySelector(selector);

/** querySelectorAll -> Array. */
export const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

/**
 * Reemplaza el contenido de cada `[data-partial="nombre"]` por `partials/nombre.html`.
 * Resuelve parciales anidados (p. ej. top-nav dentro de header). Idempotente.
 * @returns {Promise<void>}
 */
export async function injectPartials(root = document) {
  for (let pass = 0; pass < MAX_PARTIAL_PASSES; pass += 1) {
    const slots = $$("[data-partial]", root).filter((el) => !el.dataset.partialState);
    if (slots.length === 0) break;

    await Promise.all(
      slots.map(async (el) => {
        const name = el.dataset.partial;
        try {
          const res = await fetch(`${PARTIALS_BASE}/${name}.html`, { cache: "no-cache" });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          el.innerHTML = await res.text();
          el.dataset.partialState = "loaded";
        } catch (err) {
          el.dataset.partialState = "error";
          console.error(`No se pudo cargar el parcial "${name}":`, err);
        }
      }),
    );
  }
  markActiveNav(root);
}

/**
 * Marca el enlace de navegación que corresponde a la página actual
 * (en top-nav y bottom-nav) con el color de acento + `aria-current`.
 */
export function markActiveNav(root = document) {
  const strip = (path) => path.replace(/index\.html$/, "") || "/";
  const here = strip(window.location.pathname);
  $$('[data-partial="top-nav"] a, [data-partial="bottom-nav"] a', root).forEach((a) => {
    const target = strip(new URL(a.getAttribute("href"), window.location.origin).pathname);
    const active = target === here;
    const inBottomNav = a.closest('[data-partial="bottom-nav"]') !== null;
    a.classList.toggle(inBottomNav ? "text-forest" : "text-bark", active);
    if (active) {
      a.classList.toggle("font-semibold", !inBottomNav);
      a.setAttribute("aria-current", "page");
    } else {
      a.removeAttribute("aria-current");
    }
  });
}

let toastHost = null;

/**
 * Muestra una notificación efímera.
 * @param {string} message
 * @param {{variant?: 'default'|'success'|'error', duration?: number}} [opts]
 */
export function toast(message, { variant = "default", duration = 3400 } = {}) {
  if (!toastHost) {
    toastHost = document.createElement("div");
    toastHost.className =
      "pointer-events-none fixed inset-x-0 bottom-4 z-50 flex flex-col items-center gap-2 px-4 " +
      "lg:inset-x-auto lg:right-6 lg:items-end";
    document.body.appendChild(toastHost);
  }

  const tone =
    variant === "error"
      ? "bg-brick text-cream"
      : variant === "success"
        ? "bg-forest text-cream"
        : "bg-bark text-cream";

  const el = document.createElement("div");
  el.setAttribute("role", "status");
  el.className =
    `blob pointer-events-auto max-w-sm translate-y-2 px-4 py-3 text-sm opacity-0 ${tone} ` +
    "shadow-[0_16px_36px_-12px_rgba(59,46,34,0.5)] transition duration-300";
  el.textContent = message;
  toastHost.appendChild(el);

  requestAnimationFrame(() => el.classList.remove("opacity-0", "translate-y-2"));
  window.setTimeout(() => {
    el.classList.add("opacity-0", "translate-y-2");
    window.setTimeout(() => el.remove(), 320);
  }, duration);
}
