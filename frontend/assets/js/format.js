// Formato de moneda, fecha y hora — es-AR, zona horaria única del negocio.

const APP_TIMEZONE = "America/Argentina/Buenos_Aires";

export function pad2(n) {
  return String(n).padStart(2, "0");
}

/** cents: entero en centavos (como los devuelve el backend) -> "$31.800" */
export function formatMoney(cents) {
  const pesos = Math.round(cents / 100);
  return `$${pesos.toLocaleString("es-AR")}`;
}

/** isoString: fecha/hora ISO-8601 en UTC (como la devuelve el backend) -> "10/09/2026" */
export function formatDate(isoString) {
  return new Date(isoString).toLocaleDateString("es-AR", {
    timeZone: APP_TIMEZONE,
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

const ROLE_LABELS = { CUSTOMER: "Cliente", ADMIN: "Administrador/a", DELIVERY: "Repartidor/a" };

/** "CUSTOMER" -> "Cliente". Un solo lugar para esta traducción: perfil.html y
 * el panel de admin la necesitan igual, y así no pueden desalinearse. */
export function roleLabel(role) {
  return ROLE_LABELS[role] ?? role;
}

/** isoString: fecha/hora ISO-8601 en UTC (como la devuelve el backend) -> "12:00" */
export function formatTime(isoString) {
  return new Date(isoString).toLocaleTimeString("es-AR", {
    timeZone: APP_TIMEZONE,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false, // sin esto, es-AR devuelve "12:00 p. m." en vez de "12:00"
  });
}
