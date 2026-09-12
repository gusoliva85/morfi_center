---
name: morfi-frontend
description: >
  Sistema de diseño del frontend de Morfi Center — estilo "Artesanal · Cocina de
  Olla" (mockup aprobado documentacion/mockups/04_Artesanal_Organico.html).
  Invocar SIEMPRE antes de crear o modificar cualquier pantalla, componente, HTML,
  CSS o config de Tailwind del proyecto, tanto en la vista mobile como en la web de
  escritorio. Define tokens de color, tipografía, formas orgánicas, utilidades,
  componentes, navegación y reglas de adaptación mobile-first ↔ escritorio.
---

# Morfi Center · Frontend "Artesanal · Cocina de Olla"

Front **aprobado**: `documentacion/mockups/04_Artesanal_Organico.html`.
Toda pantalla nueva parte de `reference/base.html` (este skill) y respeta lo que sigue.

Stack: **HTML + Tailwind CSS + JavaScript vanilla**. Sin frameworks de UI, sin neón,
sin degradados chillones.
Estética: **papel kraft y crema, tinta marrón, formas orgánicas (blobs), calidez de
cocina casera**. Toques a mano alzada, sellos, cinta de papel, ticket perforado.
Verde olla, mostaza y ladrillo. Nada rígido ni corporativo.

---

## 1. Principio rector

**Mobile-first de verdad.** Se diseña primero la columna móvil (≤ `lg`).
Al pasar a escritorio (`lg` = 1024px) **no se estira**: cambia el layout.

| | Móvil (`< lg`) | Escritorio (`≥ lg`) |
|---|---|---|
| Contenedor | full-width, `px-4/5` | `max-w-[1200px]` centrado, `px-10` |
| Navegación primaria | **bottom nav** fija (`grid-cols-5`) | **top nav** horizontal en el header (`hidden lg:flex`) |
| Contenido | 1 columna, secciones apiladas | grilla `lg:grid-cols-[1.1fr_1fr]` (u otra proporción intencional) |
| Header | logo + bajada a mano + acción mínima | + nav de escritorio |
| Carrito | barra sticky abajo (sobre la bottom nav) | barra sticky abajo del panel, ancho del contenedor |
| Tarjetas | ancho completo de la columna | tamaño natural en grilla; **nunca** una card suelta ocupando todo el ancho |

Reglas duras para escritorio:
- Prohibido botones o inputs de ~100% de ancho "porque sí". Un botón mide lo que su texto + padding.
- Prohibido cards vacías estiradas. Si sobra ancho → más columnas, no más padding.
- Aprovechar el ancho con grillas de 2–4 columnas y paneles laterales (resumen, filtros, promos).
- La bottom nav de móvil **desaparece** en `lg` (`lg:hidden`); su equivalente vive en el header.

---

## 2. Tokens (Tailwind config)

Fuente única de verdad: `frontend/tailwind.config.js` (sirve para el build CLI y para el CDN en dev).

```js
theme: {
  extend: {
    fontFamily: {
      display: ['"Bricolage Grotesque"', 'system-ui', 'sans-serif'], // títulos, nombres, precios, números
      hand:    ['Caveat', 'cursive'],                                // acentos escritos a mano
      sans:    ['Inter', 'system-ui', 'sans-serif'],                 // cuerpo, labels, UI
    },
    colors: {
      kraft:   '#E9DFC9',  // fondo de página (papel de estraza)
      cream:   '#F6EFDD',  // superficie de tarjetas / paneles
      bark:    '#3B2E22',  // texto principal / superficies oscuras
      forest:  '#2F5D3A',  // estado positivo, botón primario, marca
      mustard: '#D69A2D',  // acento secundario (labels a mano, badges, cinta)
      brick:   '#B0472F',  // acento principal (precios promo, énfasis, CTA confirmar)
    },
  },
}
```

Fuentes (Google Fonts):

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,600;12..96,700&family=Caveat:wght@600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet" />
```

Fondo de página (en `base.css`):

```css
body {
  background:
    radial-gradient(60% 45% at 85% 8%, #efe6cf 0%, rgba(239,230,207,0) 60%),
    #e9dfc9;                 /* kraft */
  color: #3b2e22;            /* bark */
}
```

---

## 3. Utilidades CSS del proyecto

Se declaran una sola vez en `frontend/assets/css/base.css`.

```css
/* Superficie principal: papel crema con textura y sombra cálida */
.paper {
  background: #f6efdd;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='2'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.06'/%3E%3C/svg%3E");
  box-shadow: 0 2px 0 #ffffff80 inset, 0 26px 50px -30px #3b2e2255, 0 3px 10px -4px #3b2e2222;
}

/* Formas orgánicas: botones, chips, miniaturas, logo, blobs decorativos */
.blob  { border-radius: 62% 38% 44% 56% / 55% 48% 52% 45%; }
.blob2 { border-radius: 40% 60% 58% 42% / 52% 40% 60% 48%; }

/* Sello inclinado (etiqueta "Plato del día", "hecho hoy") */
.stamp { transform: rotate(-7deg); border: 2px solid currentColor; }

/* Cinta de papel (encima de un ticket) */
.tape {
  position: absolute; height: 26px; width: 96px;
  background: rgba(214,154,45,0.35);       /* mustard translúcido */
  top: -12px; left: 50%; transform: translateX(-50%) rotate(-3deg);
}

/* Línea perforada del ticket */
.dashed { height: 2px; background-image: repeating-linear-gradient(90deg, #3b2e2233 0 8px, transparent 8px 16px); }

/* Hover de tarjeta interactiva (con leve giro juguetón) */
.lift { transition: transform .3s ease; }
.lift:hover { transform: translateY(-4px) rotate(-.4deg); }

/* Placeholders duotono para fotos de comida mientras no hay imagen real */
.foodA { background: linear-gradient(150deg,#C97A4A,#7c3a20); } /* carnes / principales */
.foodB { background: linear-gradient(150deg,#3E6A45,#284a30); } /* verdes / milanesas   */
.foodC { background: linear-gradient(150deg,#C99A3E,#8a6a1f); } /* pastas              */
.foodD { background: linear-gradient(150deg,#9C6B4E,#5E3B29); } /* empanadas / masas    */

@media (prefers-reduced-motion: reduce) {
  .lift, .lift:hover { transition: none; transform: none; }
}
```

Cuando haya imágenes reales: `<img class="object-cover">` con `.foodX` como fallback del contenedor.

---

## 4. Tipografía

| Uso | Familia / clase | Notas |
|---|---|---|
| Título de pantalla (H1) | `font-display font-bold text-[36px] leading-[1.05] lg:text-[52px]` | palabra clave en `text-brick` |
| Título de sección (H2) | `font-display font-bold text-[20px]` | |
| Título de card / producto | `font-display font-bold text-[16px]…[24px] leading-tight` | |
| Precio | `font-display font-bold` (promo: `text-[30px] text-brick`; en línea: `font-bold`) | precio viejo `text-bark/40 line-through` |
| Números / countdown | `font-display font-bold tabular-nums` | |
| **Acento a mano** | `font-hand text-[15px]/[16px]` | bajadas, "hecho hoy", "ver todo →", "nos quedan…", labels de promo (en `text-mustard` o `text-brick`/`text-forest`) |
| Cuerpo | `text-[13px]/[14px] leading-relaxed text-bark/60` | |
| Label mayúscula | `text-[10px]/[11px] uppercase tracking-widest text-bark/40` | |

Regla:
- **`font-display` (Bricolage Grotesque)** = títulos, nombres, precios, tiempo — todo lo estructural con peso.
- **`font-hand` (Caveat)** = un toque cálido y humano, con moderación (1–3 por pantalla). Nunca para datos críticos ni botones.
- **`font-sans` (Inter)** = cuerpo, ayudas, labels, formularios.

---

## 5. Componentes

### Header
- Móvil: `relative flex items-center justify-between px-5 pt-6` — logo blob (`bg-forest text-cream font-display`) + `Morfi Center` (`font-display font-bold text-xl`) con bajada a mano (`font-hand text-[15px] text-brick` — "cocina de olla, todos los días") + botón de carrito blob (`bg-bark text-cream`, emoji 🧺, badge `bg-mustard`).
- Escritorio: agrega `<nav class="hidden lg:flex items-center gap-7 text-[13px] font-medium text-bark/60" data-partial="top-nav">`.
- El panel raíz puede llevar 2 blobs decorativos absolutos (`.blob bg-forest/10` arriba-derecha, `.blob2 bg-mustard/15` abajo-izquierda, `pointer-events-none`).

### Chip de estado (olla abierta / cerrada)
```html
<span class="inline-flex items-center gap-2 rounded-full bg-forest/12 px-3 py-1 text-[12px] font-semibold text-forest">
  <span class="h-2 w-2 rounded-full bg-forest"></span> La olla está abierta
</span>
```
Cerrada: `bg-bark/8 text-bark/50`, punto `bg-bark/40`, texto "La olla cerró por hoy".

### Countdown (ticket de kraft)
Contenedor `relative inline-block` con `<span class="tape"></span>` encima.
Interior: `lift rounded-2xl border-2 border-dashed border-bark/25 bg-cream px-6 py-5`.
- `font-hand text-[16px] text-brick` → "nos quedan…"
- fila `flex items-end gap-3`: cada unidad `text-center`, número `font-display text-4xl font-bold tabular-nums` (segundos en `text-brick`), label `text-[10px] uppercase tracking-widest text-bark/40`; separadores `:` en `text-2xl text-bark/30`.
- `<div class="dashed mt-3"></div>` (perforación)
- pie `flex justify-between text-[12px] text-bark/50`: "Cierre 12:00" · "Cancelás hasta 11:40".
IDs `#h #m #s` para el JS (o `data-countdown-h/m/s`).

### Card de Plato del Día
`article.lift.overflow-hidden.rounded-[26px].border-2.border-bark/12.bg-cream`, grid `grid-cols-[1fr_130px] sm:grid-cols-[1fr_200px]`.
- Texto `p-6`: `<span class="stamp inline-block rounded-md px-2.5 py-1 font-display text-[11px] font-bold uppercase tracking-wide text-brick">Plato del día</span>` → H3 `font-display` → `font-hand text-[16px] text-forest` ("hecho hoy, a fuego lento") → precios (`line-through` + `font-display text-[30px] font-bold text-brick`) → botón blob primario.
- Imagen: `.foodA` + emoji/`<img>`.

### Card de promo
`div.lift.rounded-2xl.border-2.border-bark/12.bg-cream.p-4` → label a mano `font-hand text-[15px] text-mustard` → nombre `font-display font-bold text-[16px]` → precios.

### Chips de categoría
Activo: `blob bg-bark px-3.5 py-1.5 text-[12px] font-medium text-cream`.
Inactivo: `blob border-2 border-bark/15 px-3.5 py-1.5 text-[12px] text-bark/60 hover:border-bark/40`.

### Ítem de producto (lista)
`div.lift.flex.items-center.gap-4.rounded-2xl.border-2.border-bark/12.bg-cream.p-3`:
miniatura `.foodX.blob h-16 w-16` · nombre `font-display font-bold text-[16px]` + detalle `text-[12px] text-bark/50` ("quedan 24 porciones") · precio `font-bold` + botón `+` (`blob border-2 border-bark/20 px-3 py-1 hover:bg-bark hover:text-cream`).
Sin stock: `border-dashed border-bark/20 bg-cream/50 opacity-55`, miniatura `bg-bark/8 grayscale`, nota a mano `font-hand text-[15px] text-bark/45` ("se terminó por hoy") + etiqueta `text-[11px] uppercase tracking-widest text-bark/40` ("sin stock").

### Panel de entrega (verde suave)
`div.rounded-2xl.border-2.border-forest/25.bg-forest/8.p-4`: label `text-bark/55` + link a mano `font-hand text-[15px] text-brick` ("cambiar") → dirección `font-display font-bold text-[16px]` → fila `text-[12px] text-bark/55` con "✓ llegamos hasta acá · 2,3 km" (`text-forest`) y "envío $1.500".

### Panel oscuro (avisos importantes)
`div.rounded-2xl.bg-bark.p-4.text-cream`, links en `text-mustard underline underline-offset-4`, datos secundarios `text-cream/70`.

### Barra de carrito (flotante, sticky)
Parcial `cart-bar`. Va como **hermano del panel** (no dentro), para que `sticky` funcione
(un ancestro con `overflow-hidden` la rompe).
Contenedor `div.sticky.bottom-[84px].z-20.mt-4.lg:bottom-6`; adentro una barra
`flex items-center justify-between rounded-2xl border-2 border-bark/12 bg-cream/95 px-5 py-3.5 backdrop-blur shadow-[…] lg:px-6`.
Izquierda: `font-hand text-[15px] text-bark/50` ("tu vianda · N cosas") + total `font-display text-[20px] font-bold` (`+ envío` en `text-[12px] font-sans text-bark/40`).
Derecha: CTA `blob bg-brick px-6 py-2.5 text-[13px] font-semibold text-cream hover:bg-bark`.
En móvil queda **por encima** de la bottom nav fija (`bottom-[84px]`).

### Bottom nav (solo móvil, FIJA)
Parcial `bottom-nav`. `nav.fixed.inset-x-0.bottom-0.z-30.grid.grid-cols-5.border-t-2.border-bark/12.bg-cream.py-2.text-[11px].text-bark/45.lg:hidden` (+ sombra hacia arriba), ítem activo `text-forest`.
Destinos: Inicio · Olla (menú) · Vianda (carrito) · Pedidos · Cuenta.
Al ser `fixed`, la página necesita **`pb-[84px] lg:pb-0` en `<body>`** para que el contenido no quede tapado.

### Botones
| Tipo | Clase |
|---|---|
| Primario | `blob bg-forest px-6 py-2.5 text-[13px] font-semibold text-cream transition hover:bg-bark` |
| CTA confirmar | `blob bg-brick px-7 py-3 text-[13px] font-semibold text-cream transition hover:bg-bark` |
| Secundario | `blob border-2 border-bark/20 px-4 py-2 text-[13px] text-bark hover:bg-bark hover:text-cream` |
| Link | `font-hand text-[15px] text-brick` (a mano) o `text-brick underline underline-offset-4` |

### Formularios (auth, direcciones, checkout, panel admin)
- Input: `w-full rounded-xl border-2 border-bark/15 bg-cream px-4 py-3 text-[15px] placeholder-bark/35 focus:border-forest focus:outline-none focus:ring-2 focus:ring-forest/15`.
- Label: `text-[11px] uppercase tracking-widest text-bark/45 mb-1.5`.
- Error: texto `text-[12px] text-brick mt-1`, borde `border-brick`.
- Grupo: `space-y-4`; en escritorio, campos relacionados en `sm:grid-cols-2 gap-4`.

---

## 6. Radios, bordes y espaciado

- Radios: panel raíz `rounded-[34px]` · Plato del Día `rounded-[26px]` · cards `rounded-2xl` · inputs `rounded-xl` · **elementos interactivos (botones, chips, miniaturas, logo) usan `.blob`**, no `rounded-full`.
- Bordes: casi siempre **`border-2`** — `border-bark/12` (cards) · `border-bark/15`–`/20` (inputs, chips) · `border-dashed border-bark/25` (ticket, sin stock). Panel raíz `border border-bark/10`.
- Ritmo vertical: secciones `mt-4`→`mt-8`; interior de card `p-3`/`p-4`/`p-6`; grilla principal `gap-8`.
- Sombras: solo la de `.paper`. Nada de `shadow-2xl` de Tailwind ni sombras duras.

---

## 7. Interacción y motion

- Hover de cards: `.lift` (translateY −4px + `rotate(-.4deg)`, 300ms). El giro leve es parte de la identidad.
- Botones/inputs: `transition` de color 150–200ms.
- Countdown: actualización por segundo, sin parpadeo (reemplazar textContent).
- `prefers-reduced-motion`: `base.css` desactiva `.lift` y neutraliza animaciones/transiciones.
- Foco visible siempre (`focus:ring-2 focus:ring-forest/15` o `outline`).

---

## 8. Accesibilidad

- Contraste: `text-bark` sobre `cream/kraft` cumple AA. `text-bark/45` solo para texto ≥ 12px no esencial.
- Área táctil ≥ 44px en controles de móvil (los botones `+` de la lista deben tener padding suficiente).
- `<button>` real para acciones, `<a>` para navegación. Íconos/emojis decorativos con `aria-hidden`.
- Estados (olla abierta/cerrada, sin stock, error) nunca solo por color: agregar texto.
- La `font-hand` no debe usarse para información crítica (poca legibilidad a tamaños chicos).
- `lang="es-AR"`, jerarquía de headings correcta, `alt` en imágenes de producto.

---

## 9. Estructura de archivos del frontend

```
frontend/
├── index.html                # Home cliente
├── pages/
│   ├── cliente/               # menu, producto, carrito, direccion, pago, pedidos, seguimiento, perfil
│   ├── auth/                  # login, registro, recuperar
│   ├── admin/                 # dashboard, pedidos, validacion, produccion, catalogo, ...
│   └── delivery/              # inicio, ruta, parada, historial
├── partials/                  # header, top-nav, bottom-nav, cart-bar, card-*, ... (inyectados por JS)
├── assets/
│   ├── css/  base.css  tailwind.css (build)
│   ├── js/   api.js  auth.js  ui.js  countdown.js  format.js  pages/<pantalla>.js
│   └── img/
├── _sandbox/                  # páginas de prueba visual del sistema (no son parte de la app)
└── tailwind.config.js
```

- Multipágina (una HTML por pantalla). Sin router SPA.
- Parciales comunes en `partials/`, insertados con `injectPartials()` de `ui.js` (`fetch` + `innerHTML`, resuelve anidados).
- `<head>` estándar de cada página: charset/viewport/title + fuentes + `<script src="https://cdn.tailwindcss.com">` + `<script src="/tailwind.config.js">` + `<link rel="stylesheet" href="/assets/css/base.css">`. En prod se reemplazan el CDN + config por `<link href="/assets/css/tailwind.css">`.
- JS por página, modular, sin dependencias. `api.js` centraliza `fetch` (base URL, token, errores).

---

## 10. Checklist antes de dar una pantalla por terminada

- [ ] Se ve bien a 360px de ancho y a 1440px, y en el salto `lg` **cambia el layout** (no se estira).
- [ ] En escritorio no hay botones/inputs/cards estirados; el ancho sobrante se usa con columnas.
- [ ] Bottom nav solo en móvil; nav de escritorio en el header.
- [ ] Solo tokens del sistema (kraft/cream/bark/forest/mustard/brick), `font-display` para lo estructural, `font-hand` con moderación, `font-sans` para UI.
- [ ] Elementos interactivos con `.blob`; bordes `border-2`; hover `.lift`; sin neón ni degradados fuertes.
- [ ] Estados por texto además de color; foco visible; áreas táctiles ≥ 44px.
- [ ] `prefers-reduced-motion` respetado; `font-hand` no usada para datos críticos.
- [ ] Copys en español rioplatense, tono de cocina casera ("Pedí", "Sumar a mi vianda", "La olla está abierta").
```
