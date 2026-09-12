/**
 * format.js · helpers de formato (moneda, fecha, hora).
 *
 * - El dinero se maneja en **centavos enteros** (como en el backend) y se muestra
 *   como `$00.000` (formato rioplatense: `.` para miles, `,` para decimales).
 * - Las fechas de la API llegan en ISO-8601 UTC (`...Z`); se muestran en la zona
 *   de operación.
 *
 * Sin dependencias. Módulo ES: import { formatMoney } from '/assets/js/format.js'
 */

export const APP_TIMEZONE = "America/Argentina/Buenos_Aires";

/** Entero a string con separador de miles: 31800 -> "31.800" */
function groupThousands(intValue) {
  return String(intValue).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

/** Rellena a 2 dígitos: 5 -> "05" */
export function pad2(value) {
  return String(Math.trunc(Math.abs(Number(value)))).padStart(2, "0");
}

/**
 * Formatea un monto en **centavos** a texto.
 * @param {number} cents  monto en centavos (puede ser negativo)
 * @param {{cents?: 'auto'|'always'|'never', symbol?: boolean}} [opts]
 *   - cents 'auto' (def): muestra decimales solo si no son 00
 * @returns {string} p. ej. `formatMoney(3180000)` -> `"$31.800"`
 */
export function formatMoney(cents, { cents: centsMode = "auto", symbol = true } = {}) {
  const rounded = Math.round(Number(cents) || 0);
  const negative = rounded < 0;
  const abs = Math.abs(rounded);
  const whole = Math.floor(abs / 100);
  const frac = abs % 100;

  let out = groupThousands(whole);
  if (centsMode === "always" || (centsMode === "auto" && frac !== 0)) {
    out += `,${String(frac).padStart(2, "0")}`;
  }
  if (symbol) out = `$${out}`;
  return negative ? `-${out}` : out;
}

/** Normaliza a Date: acepta Date | número (epoch ms) | ISO string. */
function toDate(value) {
  if (value instanceof Date) return value;
  if (typeof value === "number") return new Date(value);
  // admite el sufijo 'Z' y offsets; Date lo parsea nativo
  return new Date(value);
}

/**
 * Formatea una fecha.
 * @param {Date|number|string} value
 * @param {{style?: 'short'|'medium'|'long', timeZone?: string}} [opts]
 *   - short  -> "10/09/2026"
 *   - medium -> "10 de sep"
 *   - long   -> "miércoles 10 de septiembre de 2026"
 */
export function formatDate(value, { style = "short", timeZone = APP_TIMEZONE } = {}) {
  const date = toDate(value);
  if (Number.isNaN(date.getTime())) return "";

  const base = { timeZone };
  const options =
    style === "long"
      ? { ...base, weekday: "long", day: "numeric", month: "long", year: "numeric" }
      : style === "medium"
        ? { ...base, day: "numeric", month: "short" }
        : { ...base, day: "2-digit", month: "2-digit", year: "numeric" };

  return new Intl.DateTimeFormat("es-AR", options).format(date);
}

/**
 * Formatea una hora (24 h).
 * @returns {string} p. ej. "12:00"
 */
export function formatTime(value, { timeZone = APP_TIMEZONE, seconds = false } = {}) {
  const date = toDate(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("es-AR", {
    timeZone,
    hour: "2-digit",
    minute: "2-digit",
    ...(seconds ? { second: "2-digit" } : {}),
    hour12: false,
  }).format(date);
}

/**
 * Tiempo relativo aproximado, en pasado o futuro.
 * @returns {string} "hace 3 min", "en 2 h", "recién"
 */
export function formatRelativeTime(value, { now = Date.now() } = {}) {
  const date = toDate(value);
  if (Number.isNaN(date.getTime())) return "";
  const diffSec = Math.round((date.getTime() - now) / 1000);
  const abs = Math.abs(diffSec);
  if (abs < 45) return "recién";

  const units = [
    ["day", 86400],
    ["hour", 3600],
    ["minute", 60],
  ];
  const rtf = new Intl.RelativeTimeFormat("es-AR", { numeric: "always" });
  for (const [unit, secs] of units) {
    if (abs >= secs) return rtf.format(Math.round(diffSec / secs), unit);
  }
  return rtf.format(diffSec, "second");
}

/** Segundos totales -> "HH:MM:SS" (para countdowns). */
export function formatDuration(totalSeconds) {
  const s = Math.max(0, Math.floor(Number(totalSeconds) || 0));
  return `${pad2(Math.floor(s / 3600))}:${pad2(Math.floor((s % 3600) / 60))}:${pad2(s % 60)}`;
}
