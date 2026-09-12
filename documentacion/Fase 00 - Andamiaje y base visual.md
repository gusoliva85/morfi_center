# Fase 00 · Andamiaje y base visual

**Proyecto:** Morfi Center
**Estado:** ✅ Completa y aprobada
**Inicio:** 10 de septiembre de 2026
**Cierre:** 10 de septiembre de 2026
**Temas de esta fase:** 0.1 Estructura del repositorio · 0.2 Esqueleto del backend · 0.3 Base de datos y migraciones · 0.4 Frontend — base visual · 0.5 Tooling y arranque · 0.6 Documentación viva
**Roadmap:** `documentacion/03_Roadmap.md` (Fase 0)

---

## 1. Objetivo de la fase

Dejar el proyecto en condiciones de empezar a construir funcionalidad: estructura de carpetas definitiva, un backend FastAPI que arranca y responde con logging y manejo de errores unificados, una base de datos SQLite con migraciones Alembic funcionando, un frontend con el sistema de diseño aprobado ya aplicado a la pantalla principal (sin lógica de negocio todavía), y las herramientas para levantar todo con un doble clic y para documentar cada fase siguiente.

Al cerrar esta fase, cualquiera puede clonar el repositorio, ejecutar `iniciar.bat` y ver la home de Morfi Center funcionando visualmente, con el backend respondiendo en paralelo — aunque todavía no haya ninguna funcionalidad de negocio conectada entre los dos.

---

## 2. Qué quedó implementado

### Tema 0.1 · Estructura del repositorio

El proyecto quedó organizado en dos raíces independientes, `backend/` y `frontend/`, más `documentacion/`. El backend sigue una estructura por capas (`core`, `db`, `models`, `schemas`, `repositories`, `services`, `api`, `jobs`) que se va a ir poblando fase a fase; hoy la mayoría son paquetes vacíos preparados para recibirlo.

```
backend/
├── app/
│   ├── core/     db/     models/     schemas/     repositories/
│   ├── services/ (+ external/)
│   ├── api/ (+ routes/)
│   └── jobs/
├── alembic/
├── tests/ (unit/, api/)
├── data/            # morfi.db (gitignored)
└── storage/         # comprobantes (gitignored)

frontend/
├── index.html
├── pages/ (cliente/, auth/, admin/, delivery/)
├── partials/
├── assets/ (css/, js/, img/)
└── _sandbox/        # páginas de prueba visual, no forman parte de la app
```

El repositorio Git se inicializó con un `.gitignore` que excluye el entorno virtual, la base de datos, los comprobantes subidos y el CSS compilado de Tailwind, pero conserva esas carpetas vacías vía `.gitkeep`:

```gitignore
backend/data/*
!backend/data/.gitkeep
backend/storage/payment_proofs/*
!backend/storage/payment_proofs/.gitkeep
*.db
*.db-wal
*.db-shm
frontend/assets/css/tailwind.css
```

Las dependencias del backend quedaron fijadas en `backend/requirements.txt` (FastAPI, SQLAlchemy, Alembic, Pydantic, passlib/bcrypt, PyJWT, Authlib, httpx, APScheduler, slowapi, más pytest/ruff/black para desarrollo) y la configuración de las herramientas en `backend/pyproject.toml` (black a 100 columnas, reglas de ruff, `pytest` con `asyncio_mode = "auto"`).

**Archivos principales:** `.gitignore`, `README.md`, `backend/requirements.txt`, `backend/pyproject.toml`
**Tareas:** T-0.1.1 ✅ · T-0.1.2 ✅ · T-0.1.3 ✅

---

### Tema 0.2 · Esqueleto del backend

La configuración de la aplicación vive en un único objeto `settings` (`app/core/config.py`), leído de variables de entorno y de `backend/.env`. Todos los valores tienen un default de desarrollo razonable, salvo el secreto de JWT: si `APP_ENV=production` y sigue con el valor de desarrollo, la aplicación se niega a arrancar.

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", case_sensitive=False, extra="ignore")

    app_env: Literal["development", "production"] = "development"
    database_url: str = "sqlite:///./data/morfi.db"
    jwt_secret: str = _INSECURE_DEV_SECRET
    ...

    def model_post_init(self, __context: Any) -> None:
        if self.is_production and self.jwt_secret == _INSECURE_DEV_SECRET:
            raise ValueError("JWT_SECRET sin configurar...")
```

Todos los enumerados de negocio (`Role`, `OrderStatus`, `PaymentStatus`, `ShiftStatus`, etc. — más de 20) quedaron centralizados en `app/core/enums.py` como `StrEnum`, con un helper `.values()` para usar en `CHECK` constraints y tests.

Las reglas de negocio nunca lanzan `HTTPException` directamente: lanzan una subclase de `DomainError` (`app/core/errors.py`), y un handler global las traduce siempre al mismo formato de respuesta:

```json
{ "error": { "code": "OUT_OF_STOCK", "message": "No hay stock suficiente...", "details": { "product_id": 3 } } }
```

Ese mismo handler también envuelve los errores de validación de Pydantic (422), las `HTTPException` sueltas (404 de ruteo, 405, etc.) y cualquier excepción no controlada, que siempre devuelve un 500 genérico sin filtrar el detalle interno (que sí queda en el log, con traceback completo).

El logging (`app/core/logging.py`) usa formato legible en desarrollo y una línea JSON por evento en producción. Un middleware ASGI (`RequestContextMiddleware`) asigna un `request_id` a cada request —tomando el header entrante `X-Request-Id` si existe, o generando uno— lo propaga a todos los logs de esa request mediante un `ContextVar`, y lo devuelve en la respuesta:

```python
async def __call__(self, scope, receive, send):
    request_id = _incoming_request_id(scope)
    token = _request_id_ctx.set(request_id)
    async def send_wrapper(message):
        if message["type"] == "http.response.start":
            MutableHeaders(scope=message)["X-Request-Id"] = request_id
        await send(message)
    try:
        await self.app(scope, receive, send_wrapper)
    finally:
        ...  # log de acceso + reset del contexto
```

Todo esto se ensambla en `app/main.py`: `create_app()` configura logging, agrega CORS (solo en desarrollo, restringido a `FRONTEND_ORIGIN`), agrega el middleware de contexto, registra los handlers de error y monta el router `/api/v1` con el primer endpoint real, `GET /health`. La documentación interactiva queda en `/api/docs`.

**Archivos principales:** `app/core/{config,enums,errors,logging,timezone}.py`, `app/main.py`, `app/api/routes/health.py`
**Tareas:** T-0.2.1 ✅ · T-0.2.2 ✅ · T-0.2.3 ✅ · T-0.2.4 ✅ · T-0.2.5 ✅ · T-0.2.6 ✅

---

### Tema 0.3 · Base de datos y migraciones

El acceso a datos gira alrededor de `app/db/session.py`. `build_engine(url)` arma el `Engine` de SQLAlchemy y, si es SQLite, agrega un listener que activa las foreign keys, el modo WAL y un `busy_timeout` en cada conexión nueva:

```python
@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, _):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
```

`get_session()` (la dependencia de FastAPI) y `session_scope()` (para jobs y scripts) comparten la misma semántica: commit si todo salió bien, rollback ante excepción, y siempre cierran la sesión.

La base declarativa (`app/db/base.py`) define una convención de nombres para índices y constraints (`pk_<tabla>`, `uq_<tabla>_<columna>`, `fk_...`, `ix_...`) para que Alembic genere migraciones estables, y un `TimestampMixin` con `created_at`/`updated_at`. Esas columnas usan un tipo a medida, `UtcDateTime` (`app/db/types.py`), que persiste el `datetime` como texto ISO-8601 UTC con sufijo `Z` —tal como define el documento técnico— y lo devuelve como `datetime` *aware* en Python.

`app/models/__init__.py` es el punto único que va a ir importando cada modelo de dominio a medida que se creen, para que tanto Alembic como los tests los conozcan.

Alembic quedó inicializado en `backend/alembic/`, con la URL de conexión tomada siempre de `settings.database_url` (nunca hardcodeada en `alembic.ini`) y `render_as_batch=True` para poder alterar tablas en SQLite:

```python
_DB_URL = (config.get_main_option("sqlalchemy.url") or "").strip() or settings.database_url
target_metadata = Base.metadata
_IS_SQLITE = _DB_URL.startswith("sqlite")
```

Un hook de post-escritura formatea con `black` cada migración generada. La migración raíz (`da2fde5df91d_baseline.py`) es intencionalmente vacía: sirve como punto de partida de la cadena de migraciones.

Por último, `app/db/seed.py` define el esqueleto idempotente de datos de prueba: la función `run_seed(session)` (vacía por ahora, con un comentario por cada fase que la va a completar) y un helper genérico `get_or_create(session, modelo, defaults=..., **filtros)` que se va a reutilizar en todas las fases siguientes. Se ejecuta con `python -m app.db.seed`.

**Archivos principales:** `app/db/{session,base,types,seed}.py`, `app/models/__init__.py`, `backend/alembic/`, `backend/alembic.ini`
**Tareas:** T-0.3.1 ✅ · T-0.3.2 ✅ · T-0.3.3 ✅ · T-0.3.4 ✅

---

### Tema 0.4 · Frontend — base visual (sin funcionalidad)

El front adoptó el sistema de diseño **"Artesanal · Cocina de Olla"**, basado en el mockup aprobado `documentacion/mockups/04_Artesanal_Organico.html`. El sistema completo (tokens, tipografía, componentes, reglas de adaptación mobile↔escritorio) está documentado en la skill del proyecto `.claude/skills/morfi-frontend/`, y se resume en `documentacion/02_Documento_Tecnico.md §16`.

Los tokens de color y las tres familias tipográficas viven en un único archivo, `frontend/tailwind.config.js`, escrito para servir tanto al build de producción (`module.exports`) como al CDN de Tailwind en desarrollo (`window.tailwind.config`):

```js
var theme = {
  extend: {
    fontFamily: {
      display: ['"Bricolage Grotesque"', "system-ui", "sans-serif"],
      hand: ["Caveat", "cursive"],
      sans: ["Inter", "system-ui", "sans-serif"],
    },
    colors: { kraft: "#E9DFC9", cream: "#F6EFDD", bark: "#3B2E22", forest: "#2F5D3A", mustard: "#D69A2D", brick: "#B0472F" },
  },
};
```

Las utilidades visuales que Tailwind no cubre quedaron en `frontend/assets/css/base.css`: `.paper` (superficie con textura de papel), `.blob`/`.blob2` (formas orgánicas para todo elemento interactivo — botones, chips, miniaturas, el logo), `.stamp` (el sello inclinado del Plato del Día), `.tape` + `.dashed` (la cinta de papel y la perforación del ticket de countdown), `.lift` (hover con una leve elevación y giro), y las cuatro variantes `.foodA`–`.foodD` como placeholder de fotos de producto. Todo respeta `prefers-reduced-motion`.

La navegación se resolvió como cuatro parciales HTML en `frontend/partials/` (`header`, `top-nav`, `bottom-nav`, `cart-bar`), inyectados en runtime por `assets/js/ui.js`. `injectPartials()` resuelve incluso parciales anidados (el `top-nav` vive dentro del `header`) en varias pasadas:

```js
export async function injectPartials(root = document) {
  for (let pass = 0; pass < MAX_PARTIAL_PASSES; pass += 1) {
    const slots = $$("[data-partial]", root).filter((el) => !el.dataset.partialState);
    if (slots.length === 0) break;
    await Promise.all(slots.map(async (el) => {
      const res = await fetch(`${PARTIALS_BASE}/${el.dataset.partial}.html`);
      el.innerHTML = await res.text();
      el.dataset.partialState = "loaded";
    }));
  }
  markActiveNav(root);
}
```

Un detalle de implementación importante: el panel principal usa `overflow-hidden` para redondear sus esquinas y contener los blobs decorativos, pero eso rompe `position: sticky`. Por eso la **bottom-nav quedó `fixed`** (fuera del panel, siempre visible en móvil) y la **barra de carrito quedó flotante y `sticky`, como hermana del panel** —no dentro—, apoyada justo encima de la bottom-nav. `ui.js` también expone `toast()` para notificaciones efímeras, con los tonos del sistema (`bark`/`forest`/`brick`).

`frontend/index.html` porta el mockup completo a esta estructura real, con **todos los datos hardcodeados** (sin `fetch` a la API todavía): el chip de estado, el ticket de countdown (con un contador local que corre contra las 12:00, sin sincronizar con el servidor — eso llega en la Fase 2), el Plato del Día, dos promociones, la lista de productos con un ítem sin stock, el panel de dirección y la barra de carrito.

Como utilidades reutilizables ya quedaron listas `assets/js/format.js` (moneda en centavos → `"$31.800"`, fechas y horas con `Intl` en la zona de Buenos Aires, tiempo relativo, duración para countdowns) y el cliente HTTP `assets/js/api.js` + `assets/js/auth.js`:

```js
// api.js — reintento automático ante un 401
if (res.status === 401 && canRetry) {
  const ok = await refreshSession();
  if (ok) return request(path, { ...options, retry: false });
}
```

`api.js` resuelve la URL base del backend según dónde corre el front (`assets/js/config.js`: `:5500` → apunta a `:8000`; mismo origen → `/api/v1`), guarda el access token solo en memoria, y traduce cualquier error del backend a una `ApiError` con `status`/`code`/`details`. `auth.js` queda como esqueleto (`bootstrapSession`, `login`, `logout`, `requireRole`) a la espera del backend de autenticación de la Fase 1.

**Archivos principales:** `frontend/tailwind.config.js`, `frontend/assets/css/base.css`, `frontend/partials/*.html`, `frontend/assets/js/{ui,format,config,api,auth}.js`, `frontend/index.html`
**Tareas:** T-0.4.1 ✅ · T-0.4.2 ✅ · T-0.4.3 ✅ · T-0.4.4 ✅ · T-0.4.5 ✅ · T-0.4.6 ✅

---

### Tema 0.5 · Tooling y arranque

`iniciar.bat`, en la raíz, hace todo el arranque en un doble clic: crea el entorno virtual si falta, instala `backend/requirements.txt`, corre `alembic upgrade head` y `python -m app.db.seed`, levanta el backend (`uvicorn app.main:app --reload --port 8000`) y el frontend (`python -m http.server 5500 --directory frontend`) cada uno en su propia ventana, y por último abre el navegador en `http://localhost:5500`. Las ventanas de servicio se abren con rutas relativas al directorio de trabajo heredado (en vez de rutas absolutas anidadas en comillas), para que funcione aunque la carpeta del proyecto tenga espacios en el nombre.

Del lado de las pruebas, `backend/tests/conftest.py` centraliza tres fixtures para toda la suite: `engine` (SQLite en memoria con `StaticPool`, esquema recreado en cada test desde `Base.metadata`), `session` (una `Session` sobre ese engine) y `client` (`httpx.AsyncClient` contra la app real, con `get_session` apuntando a la misma `session` del test, así lo que arma el test es visible para el endpoint sin necesidad de commitear):

```python
@pytest_asyncio.fixture
async def client(engine, session):
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
```

**Archivos principales:** `iniciar.bat`, `backend/tests/conftest.py`
**Tareas:** T-0.5.1 ✅ · T-0.5.2 ✅

---

### Tema 0.6 · Documentación viva

`documentacion/Usuarios.md` quedó como el registro único de credenciales de prueba (todas simples, de desarrollo): admin, cliente y repartidor, marcadas como pendientes hasta que el seed de las Fases 1 y 14 las genere.

Este mismo documento es la primera instancia de la plantilla definida para el cierre de fase (`documentacion/_Plantilla_Fase.md`): un archivo `Fase 0X - <Nombre>.md` por fase, que se va completando a medida que se aprueban sus tareas y describe siempre la versión final de lo implementado —nunca el historial de idas y vueltas— con fragmentos de código representativos y los pasos para probarla.

**Archivos principales:** `documentacion/Usuarios.md`, `documentacion/_Plantilla_Fase.md`
**Tareas:** T-0.6.1 ✅ · T-0.6.2 ✅

---

## 3. Cómo probarlo

1. Ejecutar `iniciar.bat` desde la raíz del proyecto.
2. Verificar `http://localhost:8000/api/v1/health` → `{"status":"ok","env":"development","app":"Morfi Center",...}`.
3. Abrir `http://localhost:8000/api/docs` → Swagger con el endpoint `/api/v1/health`.
4. Abrir `http://localhost:5500/` → home de Morfi Center con el estilo Artesanal · Cocina de Olla: countdown corriendo, Plato del Día, menú, ítem sin stock, panel de entrega. A 360px de ancho se ve la bottom-nav fija y la barra de carrito flotante encima; a 1440px el nav pasa al header, la bottom-nav desaparece y el contenido usa una grilla de dos columnas.
5. Abrir `http://localhost:5500/_sandbox/` para revisar cada pieza por separado: `index.html` (utilidades del sistema), `partials.html` (header/navs/carrito), `format.html` (helpers de formato) y `api.html` (`api.get('/health')` contra el backend).
6. Dentro de `backend/`, correr `pytest` → toda la suite en verde; `ruff check .` y `black --check .` sin observaciones.

---

## 4. Usuarios de prueba involucrados

No aplica en esta fase: todavía no existe backend de autenticación. `documentacion/Usuarios.md` ya está creado y se va a completar en la Fase 1.

---

## 5. Decisiones y notas técnicas

- **Estilo visual definitivo:** "Artesanal · Cocina de Olla" (mockup `04_Artesanal_Organico.html`), documentado como skill del proyecto para que todo el frontend futuro lo siga de forma consistente.
- **Sticky vs. overflow-hidden:** el panel principal necesita `overflow-hidden` para sus esquinas redondeadas y sus blobs decorativos, lo cual es incompatible con una barra de carrito `sticky` dentro de él. Se resolvió con una bottom-nav `fixed` y una barra de carrito flotante `sticky` fuera del panel — patrón que va a repetirse en el resto de las pantallas con navegación.
- **Timestamps:** se persisten como texto ISO-8601 UTC (no como `DATETIME` nativo de SQLite) para que ordenen lexicográficamente igual que cronológicamente, vía el tipo a medida `UtcDateTime`.
- **Sesión de base de datos en tests:** un engine SQLite en memoria nuevo por test (no una transacción compartida) prioriza la simplicidad y el aislamiento total por sobre la velocidad, razonable para el tamaño actual del proyecto.
- **`iniciar.bat` sin Node.js:** el frontend no depende de Node para desarrollo (Tailwind vía CDN); el build de producción con Tailwind CLI standalone se aborda en una fase posterior.

---

## 6. Estado final de la fase

| Tarea | Estado |
|---|---|
| T-0.1.1 · Árbol de carpetas | ✅ |
| T-0.1.2 · `.gitignore` y archivos raíz | ✅ |
| T-0.1.3 · `requirements.txt` / `pyproject.toml` | ✅ |
| T-0.2.1 · `core/config.py` | ✅ |
| T-0.2.2 · `core/enums.py` | ✅ |
| T-0.2.3 · `core/errors.py` | ✅ |
| T-0.2.4 · `core/logging.py` + middleware | ✅ |
| T-0.2.5 · `core/timezone.py` | ✅ |
| T-0.2.6 · `main.py` + healthcheck | ✅ |
| T-0.3.1 · `db/session.py` | ✅ |
| T-0.3.2 · `db/base.py` | ✅ |
| T-0.3.3 · Alembic + `env.py` | ✅ |
| T-0.3.4 · `db/seed.py` | ✅ |
| T-0.4.1 · `assets/css/base.css` | ✅ |
| T-0.4.2 · `tailwind.config.js` + fuentes | ✅ |
| T-0.4.3 · Parciales base + `ui.js` | ✅ |
| T-0.4.4 · `index.html` (solo estilo) | ✅ |
| T-0.4.5 · `assets/js/format.js` | ✅ |
| T-0.4.6 · `api.js` / `auth.js` (esqueleto) | ✅ |
| T-0.5.1 · `iniciar.bat` | ✅ |
| T-0.5.2 · `pytest` + `conftest.py` | ✅ |
| T-0.6.1 · `Usuarios.md` | ✅ |
| T-0.6.2 · Plantilla de fase | ✅ |

*Fase cerrada y aprobada el 10 de septiembre de 2026. Continúa en `Fase 01 - Usuarios, roles y autenticación.md`.*
