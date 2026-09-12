/**
 * Morfi Center · configuración de Tailwind — sistema "Artesanal · Cocina de Olla".
 *
 * Fuente única de verdad de tokens y familias tipográficas. Sirve para:
 *   • el build de producción con Tailwind CLI   →  module.exports
 *   • las páginas en desarrollo con el CDN       →  window.tailwind.config
 *     (incluir <script src="/tailwind.config.js"> DESPUÉS de
 *      <script src="https://cdn.tailwindcss.com">)
 *
 * Referencia: .claude/skills/morfi-frontend/SKILL.md §2
 */
(function () {
  var theme = {
    extend: {
      fontFamily: {
        display: ['"Bricolage Grotesque"', "system-ui", "sans-serif"], // títulos, nombres, precios, números
        hand: ["Caveat", "cursive"], // acentos escritos a mano
        sans: ["Inter", "system-ui", "sans-serif"], // cuerpo, labels, UI
      },
      colors: {
        kraft: "#E9DFC9", // fondo de página (papel de estraza)
        cream: "#F6EFDD", // superficie de tarjetas / paneles
        bark: "#3B2E22", // texto principal / superficies oscuras
        forest: "#2F5D3A", // estado positivo, botón primario, marca
        mustard: "#D69A2D", // acento secundario (labels a mano, badges, cinta)
        brick: "#B0472F", // acento principal (promos, énfasis, CTA confirmar)
      },
    },
  };

  var config = {
    content: [
      "./index.html",
      "./pages/**/*.html",
      "./partials/**/*.html",
      "./_sandbox/**/*.html",
      "./assets/js/**/*.js",
    ],
    theme: theme,
    plugins: [],
  };

  // Build con Tailwind CLI (Node / CommonJS).
  if (typeof module !== "undefined" && module.exports) {
    module.exports = config;
  }

  // Dev con el CDN de Tailwind (navegador). El CDN ignora `content`.
  if (typeof window !== "undefined") {
    window.tailwind = window.tailwind || {};
    window.tailwind.config = { theme: theme, plugins: [] };
  }
})();
