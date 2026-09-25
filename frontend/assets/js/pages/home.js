import "../config.js"; // primero: api.js lee window.__MC_API__ al cargarse
import { bootstrapSession, renderSessionUI } from "../auth.js";
import { bindHeaderChip, getShiftClock, splitDuration } from "../countdown.js";
import { pad2, spokenTime } from "../format.js";
import { $, injectPartials } from "../ui.js";

await injectPartials();

const clock = getShiftClock();
bindHeaderChip(clock); // el chip del header, en escritorio y mobile

const badge = $("[data-shift-badge]");
const badgeDot = $("[data-shift-dot]");
const badgeText = $("[data-shift-badge-text]");
const headlineTop = $("[data-shift-headline-top]");
const headline = $("[data-shift-headline]");
const label = $("[data-shift-label]");
const hours = $("[data-shift-hours]");
const minutes = $("[data-shift-minutes]");
const seconds = $("[data-shift-seconds]");
const footerLeft = $("[data-shift-footer-left]");
const footerRight = $("[data-shift-footer-right]");

const BADGE_BASE =
  "inline-flex items-center gap-2 rounded-full px-3 py-1 text-[12px] font-semibold ";
const BADGE_STYLE = {
  OPEN: { box: "bg-forest/12 text-forest", dot: "bg-forest" },
  SCHEDULED: { box: "bg-mustard/20 text-bark", dot: "bg-mustard" },
  CLOSED: { box: "bg-brick/10 text-brick", dot: "bg-brick" },
  NO_SERVICE: { box: "bg-brick/10 text-brick", dot: "bg-brick" },
  IDLE: { box: "bg-bark/8 text-bark/60", dot: "bg-bark/30" },
};

// Todo lo que cambia con el estado del turno, en un solo lugar.
function copyFor(v) {
  switch (v.phase) {
    case "OPEN":
      return {
        style: "OPEN",
        badge: "La olla está abierta",
        top: "Pedí tu vianda",
        bottom: `hasta ${spokenTime(v.closeTime)}`,
        label: "nos quedan…",
        left: `Cierre ${v.closeTime}`,
        right: v.canCancel ? `Cancelás hasta ${v.cancelTime}` : "Ya no se puede cancelar",
      };
    case "SCHEDULED":
      return {
        style: "SCHEDULED",
        badge: `La olla abre a las ${v.openTime}`,
        top: "Pedí tu vianda",
        bottom: `desde ${spokenTime(v.openTime)}`,
        label: "abrimos en…",
        left: `Abre ${v.openTime}`,
        right: `Cierre ${v.closeTime}`,
      };
    case "CLOSED":
      return {
        style: "CLOSED",
        badge: "Pedidos cerrados por hoy",
        top: "Los pedidos de hoy",
        bottom: "ya cerraron",
        label: "cerramos a las " + (v.closeTime ?? "--:--"),
        left: "Los pedidos vuelven a abrir en el próximo turno",
        right: "",
      };
    case "NO_SERVICE":
      return {
        style: "NO_SERVICE",
        badge: "Hoy la olla descansa",
        top: "Hoy la olla",
        bottom: "descansa",
        label: "hoy no hay servicio",
        left: "",
        right: "",
      };
    default: // LOADING / ERROR: nada falso mientras no se sepa
      return {
        style: "IDLE",
        badge: v.phase === "ERROR" ? "No pudimos consultar la olla" : "Consultando la olla…",
        top: "Pedí tu vianda",
        bottom: "hasta que cierre la olla",
        label: "nos quedan…",
        left: "",
        right: "",
      };
  }
}

function render(v) {
  const copy = copyFor(v);
  const style = BADGE_STYLE[copy.style];
  badge.className = BADGE_BASE + style.box;
  badgeDot.className = "h-2 w-2 rounded-full " + style.dot;
  badgeText.textContent = copy.badge;
  headlineTop.textContent = copy.top;
  headline.textContent = copy.bottom;
  label.textContent = copy.label;
  footerLeft.textContent = copy.left;
  footerRight.textContent = copy.right;

  const counting = v.phase === "OPEN" || v.phase === "SCHEDULED";
  if (counting) {
    const { h, m, s } = splitDuration(v.remaining);
    hours.textContent = pad2(h);
    minutes.textContent = pad2(m);
    seconds.textContent = pad2(s);
  } else {
    const filler = v.phase === "CLOSED" ? "00" : "--";
    hours.textContent = minutes.textContent = seconds.textContent = filler;
  }
}

clock.subscribe(render);

// Página pública (RN-33 / RF-USR-11): solo para saludar si hay sesión,
// nunca bloquea ni redirige — navegar el catálogo no requiere estar logueado.
renderSessionUI(await bootstrapSession());
