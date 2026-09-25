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

/**
 * "12:00" -> "las 12 del mediodía", "08:30" -> "las 8:30 de la mañana",
 * "13:00" -> "la 1 de la tarde", "21:00" -> "las 9 de la noche".
 * Sirve para frases ("Pedí hasta las 12 del mediodía"): el backend manda la
 * hora de pared del negocio en "HH:MM" y acá solo se la dice como la diría una
 * persona, sin hacer cuentas de zona horaria.
 */
export function spokenTime(hhmm) {
  const [hour, minute] = hhmm.split(":").map(Number);
  const hour12 = hour % 12 || 12;
  const clock = minute === 0 ? String(hour12) : `${hour12}:${pad2(minute)}`;
  const article = hour12 === 1 ? "la" : "las";
  let period = "de la tarde";
  if (hour === 12 && minute === 0) period = "del mediodía";
  else if (hour < 12) period = "de la mañana";
  else if (hour >= 20) period = "de la noche";
  return `${article} ${clock} ${period}`;
}
