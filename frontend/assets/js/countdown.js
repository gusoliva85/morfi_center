// Reloj del turno: una sola fuente de verdad para "¿se puede pedir? ¿cuánto
// falta?", compartida por el chip del header (todas las páginas) y el ticket
// del home. Pide GET /shift/current, corrige la diferencia entre el reloj del
// dispositivo y el del servidor, y sigue solo: al llegar a la hora de apertura
// o de cierre cambia de estado sin recargar la página.
import { api } from "./api.js";
import { pad2 } from "./format.js";

const TICK_MS = 250; // el display se actualiza cuando cambia el segundo
const RESYNC_MS = 5 * 60_000; // se vuelve a preguntar al servidor cada tanto
const RETRY_MS = 15_000; // si el servidor no responde
const STALE_MS = 30_000; // al volver a la pestaña, se re-sincroniza si pasó más que esto

/** 3725 -> { h: 1, m: 2, s: 5 } */
export function splitDuration(totalSeconds) {
  const total = Math.max(0, Math.floor(totalSeconds));
  return { h: Math.floor(total / 3600), m: Math.floor((total % 3600) / 60), s: total % 60 };
}

/** 3725 -> "01:02:05" */
export function formatCountdown(totalSeconds) {
  const { h, m, s } = splitDuration(totalSeconds);
  return `${pad2(h)}:${pad2(m)}:${pad2(s)}`;
}

/**
 * Fases que emite el reloj:
 *   LOADING / ERROR : todavía no hay datos (o el servidor no respondió y no hay nada previo)
 *   SCHEDULED       : falta para abrir      (`remaining` = segundos hasta la apertura)
 *   OPEN            : se puede pedir        (`remaining` = segundos hasta el cierre)
 *   CLOSED          : ya cerró (o el admin ya arrancó la cocina)
 *   NO_SERVICE      : hoy no es día de operación
 * Además: openTime, closeTime ("HH:MM" del negocio), cancelTime y canCancel.
 */
function createShiftClock() {
  const listeners = new Set();
  let data = null; // última respuesta del servidor
  let offset = 0; // hora del servidor menos hora del dispositivo, en ms
  let inProduction = false; // el reloj diría "abierto" pero el admin ya arrancó la cocina
  let failed = false;
  let refreshing = false;
  let lastRefresh = 0;
  let lastPhase = null;
  let lastKey = "";
  let refreshTimer = null;
  let started = false;

  const serverNow = () => Date.now() + offset;

  function view() {
    if (!data) return { phase: failed ? "ERROR" : "LOADING", remaining: 0 };
    if (data.status === "NO_SERVICE") return { phase: "NO_SERVICE", remaining: 0 };

    const now = serverNow();
    const openAt = Date.parse(data.open_at);
    const closeAt = Date.parse(data.close_at);
    let phase = "CLOSED";
    let remaining = 0;
    if (!inProduction) {
      if (now < openAt) {
        phase = "SCHEDULED";
        remaining = Math.ceil((openAt - now) / 1000);
      } else if (now < closeAt) {
        phase = "OPEN";
        remaining = Math.ceil((closeAt - now) / 1000);
      }
    }
    return {
      phase,
      remaining,
      openTime: data.open_time,
      closeTime: data.close_time,
      cancelTime: data.cancel_deadline_time,
      canCancel: phase === "OPEN" && now < Date.parse(data.cancel_deadline),
    };
  }

  function emit(force = false) {
    const v = view();
    const key = `${v.phase}|${v.remaining}|${v.canCancel}`;
    if (!force && key === lastKey) return;
    lastKey = key;
    listeners.forEach((fn) => fn(v));
  }

  async function refresh() {
    if (refreshing) return;
    refreshing = true;
    clearTimeout(refreshTimer);
    let delay = RESYNC_MS;
    try {
      const sentAt = Date.now();
      const res = await api.get("/shift/current", { auth: false });
      // El servidor midió `now` a mitad de camino entre el envío y la respuesta.
      offset = Date.parse(res.now) - (sentAt + Date.now()) / 2;
      data = res;
      inProduction = res.status === "OPEN" && !res.ordering_open;
      failed = false;
    } catch {
      failed = true; // con datos previos, el conteo sigue con lo que ya se sabe
      delay = RETRY_MS;
    } finally {
      refreshing = false;
      lastRefresh = Date.now();
    }
    lastPhase = view().phase; // recién sincronizado: no es un cambio "por reloj"
    emit(true);
    refreshTimer = setTimeout(refresh, delay);
  }

  function tick() {
    const { phase } = view();
    // Pasó la hora de apertura o de cierre: el reloj local ya cambió de fase,
    // pero quien manda es el servidor (el admin pudo mover los horarios).
    if (lastPhase && phase !== lastPhase && !refreshing) refresh();
    else emit();
  }

  function start() {
    if (started) return;
    started = true;
    refresh();
    setInterval(tick, TICK_MS);
    // Un celular dormido o una pestaña en segundo plano frenan los timers.
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible" && Date.now() - lastRefresh > STALE_MS) refresh();
    });
  }

  return {
    /** Llama a `fn` ya mismo y en cada cambio. Devuelve la función para desuscribir. */
    subscribe(fn) {
      listeners.add(fn);
      fn(view());
      start();
      return () => listeners.delete(fn);
    },
  };
}

let shared = null;
/** Un único reloj por página: el chip y el ticket comparten la misma consulta. */
export function getShiftClock() {
  shared ??= createShiftClock();
  return shared;
}

const CHIP_OPEN = ["border-brick/30", "bg-brick/10", "text-brick"];
const CHIP_IDLE = ["border-bark/20", "bg-bark/8", "text-bark/60"];

function chipText(v) {
  switch (v.phase) {
    case "OPEN":
      return `⏳ ${formatCountdown(v.remaining)}`;
    case "SCHEDULED":
      return `Abre ${v.openTime}`;
    case "CLOSED":
      return "Cerrado";
    case "NO_SERVICE":
      return "Sin servicio";
    default:
      return "⏳ --:--:--";
  }
}

/** Conecta el chip del header (`[data-countdown-chip]`), si la página lo tiene. */
export function bindHeaderChip(clock = getShiftClock()) {
  const chip = document.querySelector("[data-countdown-chip]");
  if (!chip) return;
  clock.subscribe((v) => {
    chip.textContent = chipText(v);
    chip.title = v.phase === "OPEN" ? "Tiempo que queda para pedir" : "";
    const open = v.phase === "OPEN";
    chip.classList.remove(...(open ? CHIP_IDLE : CHIP_OPEN));
    chip.classList.add(...(open ? CHIP_OPEN : CHIP_IDLE));
  });
}
