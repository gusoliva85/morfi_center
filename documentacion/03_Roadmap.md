# MORFI CENTER
## 03 · Roadmap de implementación

**Proyecto:** Morfi Center
**Basado en:** `01_Documento_General.md` (funcional) · `02_Documento_Tecnico.md` (técnico) · `MORFI_CENTER_INFO.md` (spec maestra) · mockup aprobado `mockups/04_Artesanal_Organico.html` (estilo "Artesanal · Cocina de Olla")
**Fecha:** 10 de septiembre de 2026
**Estado:** Versión 1.0 — plan de trabajo activo

---

## Cómo se usa este roadmap

### Regla de oro: nada se implementa todo junto

Se avanza **una tarea a la vez**. Dentro de cada tema, el orden es siempre:

```
1. LÓGICA     → reglas de negocio puras (servicios de dominio) + tests unitarios. Sin API, sin front.
2. BACKEND    → modelos + migración + repositorios + endpoints + tests de API.
3. FRONTEND   → solo la pantalla/funcionalidad de ese tema, con el estilo Artesanal · Cocina de Olla,
                consumiendo la API real.
4. VALIDACIÓN → el usuario prueba en el navegador y aprueba.
```

El frontend arranca en la **Fase 0** como HTML con el estilo aplicado y **sin funcionalidad**. A partir de ahí incorpora **de a una** las funcionalidades: primero solo se ve "usuarios", en la fase siguiente "usuarios" + lo nuevo, y así sucesivamente.

### Convención de estado de cada tarea

- `- [ ]` pendiente
- `- [~]` en revisión (implementada, esperando prueba del usuario)
- `- [x]` aprobada por el usuario

**Solo el usuario aprueba.** Al recibir el OK, se marca `- [x]`. Si el usuario pide correcciones, la tarea vuelve a `- [ ]` / `- [~]` y se revisa (no se crea una tarea nueva).

### Commit y despliegue por tarea aprobada

El proyecto vive **siempre desplegado** (Vercel para el front, VPS Contabo para el back — ver Fase 0, Tema 0.7). El flujo por tarea es:

```
1. Se implementa la tarea (Lógica / Backend / Frontend según corresponda).
2. El usuario la prueba (local, o ya en producción una vez montada la Fase 0).
3. El usuario aprueba → se marca [x].
4. Se hace un commit puntual de esa tarea (mensaje con su ID, ej. "feat(T-1.3.1): registro de usuarios").
5. Se hace push a `master` → dispara el deploy automático:
   - Vercel redeploya el frontend.
   - El GitHub Action de `deploy-backend.yml` actualiza el backend en el VPS (pull + migración + reinicio del servicio).
```

No se agrupan varias tareas en un mismo commit. Una tarea `[Lógica]` o `[Backend]` (sin su `[Frontend]` todavía) también se commitea y despliega al aprobarse — no habrá cambio visible en pantalla hasta que llegue la tarea de Frontend de esa misma funcionalidad; eso es el ciclo normal del proyecto, no una falla del deploy.

### Identificador de tarea

`T-<fase>.<tema>.<n>` — por ejemplo `T-1.3.2` = Fase 1, Tema 3, tarea 2.
Cada tarea indica: **capa** (`[Lógica]` / `[Backend]` / `[Frontend]` / `[Infra]` / `[Docs]`), **qué se hace** (descripción breve, con o sin código), **cómo se prueba** y **de qué depende**.

### Documentación por fase

Cuando una fase queda **completa y aprobada**, se crea `documentacion/Fases/Fase 0X - <nombre>.md` explicando, con código y en palabras, qué se hizo y cómo quedó implementado (versión final, sin necesidad de detallar cada corrección intermedia), y se actualiza al cerrar cada tarea de esa fase. Los usuarios de prueba se registran en `documentacion/Usuarios.md`.

### Alcance

Este roadmap cubre las **Fases 0 a 17** (hasta un MVP funcional completo con seguimiento básico y notificaciones in-app). La *Etapa 8: Evolución* de la spec maestra (optimización avanzada de rutas, asignación automática, analítica, pasarelas de pago, notificaciones multicanal, empresas como entidad) queda como **backlog posterior** (Fase 18+), listada al final.

---

## Índice de fases

| Fase | Nombre | Objetivo |
|---|---|---|
| 0 | Andamiaje y base visual | Repos, esqueleto backend, DB, home con estilo, tooling, despliegue (Vercel + VPS Contabo) |
| 1 | Usuarios, roles y autenticación | Registro, login local + Google, RBAC, perfil, admin de usuarios |
| 2 | Configuración del sistema y turnos | `system_settings`, turnos (resueltos bajo demanda, sin jobs), countdown en el home |
| 3 | Catálogo: categorías y productos | CRUD admin + menú del cliente |
| 4 | Stock | Disponibilidad, reservas con vencimiento, "sin stock" |
| 5 | Promociones y Plato del Día | Precio vigente, bloque destacado |
| 6 | Carrito | Composición del pedido y resumen |
| 7 | Direcciones y cobertura | Geocodificación, barrios/radio, validación |
| 8 | Costos de envío | Modalidades y cotización |
| 9 | Confirmación del pedido | Máquina de estados base, congelado de importes, datos de transferencia |
| 10 | Pagos y comprobantes | Subida y descarga autorizada |
| 11 | Validación administrativa de pagos | Cola priorizada, aprobación, auditoría |
| 12 | Saldo a favor y cancelaciones | Ventana de cancelación, crédito, uso parcial |
| 13 | Estados del pedido y producción | Máquina completa, consolidados |
| 14 | Repartidores y asignación | Alta, disponibilidad, asignación manual, app delivery |
| 15 | Seguimiento en tiempo real (básico) | Ubicación del repartidor, vista del cliente |
| 16 | Notificaciones | Centro de notificaciones in-app |
| 17 | Cierre de MVP: pulido y QA | Criterios de aceptación, adaptación escritorio, accesibilidad |

---

# FASE 0 · Andamiaje y base visual

> Deja el proyecto listo para trabajar: estructura de carpetas, backend que responde, base de datos con migraciones, home del cliente con el estilo Artesanal · Cocina de Olla (sin lógica), y la infraestructura de despliegue (Vercel para el front, VPS Contabo para el back y la base de datos).

## Tema 0.1 · Estructura del repositorio

- [x] **T-0.1.1 · [Infra] Crear el árbol de carpetas del proyecto**
  Crear `backend/app/{core,db,models,schemas,repositories,services,services/external,api,api/routes}`, `backend/tests/{unit,api}`, `backend/data`, `backend/storage/payment_proofs`, `frontend/{pages/{auth,cliente,admin,delivery},partials,assets/{css,js,js/pages,img}}`, `documentacion/Fases`, `deploy`, `.github/workflows`. Agregar `.gitkeep` en las vacías. `backend/alembic/` no se crea acá: lo genera `alembic init` en T-0.3.3 (crearlo antes rompería ese comando). No se crea `backend/app/jobs/`: el proyecto no tiene procesos de fondo (ver `02_Documento_Tecnico.md §10`) — la mención a `jobs` en versiones anteriores de esta tarea era un resabio de antes de esa decisión.
  _Prueba:_ el árbol coincide con `02_Documento_Tecnico.md §4`. _Depende de:_ —

- [x] **T-0.1.2 · [Infra] `.gitignore` y archivos raíz**
  `.gitignore` con `backend/data/*` + `!backend/data/.gitkeep`, `backend/storage/payment_proofs/*` + `!backend/storage/payment_proofs/.gitkeep` (se ignora el contenido, no la carpeta, para que el `.gitkeep` de T-0.1.1 quede versionado), `backend/.env`, `__pycache__/`, `*.pyc`, `.venv/`, `frontend/assets/css/tailwind.css`. Crear `README.md` mínimo del proyecto (qué es, stack, cómo se arranca en local — ver `02_Documento_Tecnico.md §24.2`).
  _Prueba:_ `git status` no lista datos ni entorno; `backend/data/.gitkeep` y `backend/storage/payment_proofs/.gitkeep` siguen versionados. _Depende de:_ T-0.1.1

- [x] **T-0.1.3 · [Infra] `requirements.txt` y `pyproject.toml`**
  `requirements.txt`: fastapi, uvicorn[standard], sqlalchemy, alembic, pydantic, pydantic-settings, **bcrypt** (no `passlib[bcrypt]`: se probó al armar esta tarea y `passlib` 1.7.4, sin mantenimiento desde 2020, rompe con `bcrypt` ≥ 4.1 — se usa `bcrypt` directo, ver `02_Documento_Tecnico.md §2`), pyjwt, authlib, httpx, python-multipart, slowapi, **pytest, pytest-asyncio, ruff, black** (estas 4 últimas hacían falta para que la config de `pyproject.toml` sirva de algo — no estaban en versiones anteriores de esta tarea). `pyproject.toml` con config de ruff, black (line 100) y pytest (incluye `asyncio_mode` para los tests con `httpx.AsyncClient` de §22).
  _Prueba:_ `pip install -r requirements.txt` sin errores en un venv limpio; `python -c "import fastapi, pytest, ruff, bcrypt"` no falla; un hash+verify de prueba con `bcrypt` funciona. _Depende de:_ T-0.1.1
  > **Nota (Fase 2):** originalmente incluía `apscheduler` — se sacó al decidir que turnos y reservas se resuelven bajo demanda, sin tareas programadas (ver `02_Documento_Tecnico.md` §10).

## Tema 0.2 · Esqueleto del backend

- [x] **T-0.2.1 · [Backend] `core/config.py` — Settings**
  `Settings(BaseSettings)` con las variables de `02_Documento_Tecnico.md §19` (APP_ENV, APP_TIMEZONE, DATABASE_URL, JWT_*, GOOGLE_*, GEOCODING_*, STORAGE_DIR, etc.). Exponer `settings` singleton. Crear `backend/.env.example`.
  _Prueba:_ `python -c "from app.core.config import settings; print(settings.app_name)"`. _Depende de:_ T-0.1.3

- [x] **T-0.2.2 · [Backend] `core/enums.py`**
  Todos los enums de `02_Documento_Tecnico.md §7` como `class X(str, Enum)` — 18 en total, incluyendo `AssignmentStatus`, `StopStatus` y `SettingValueType` (se agregaron a §7 al armar esta tarea: existían como `CHECK` en el modelo físico de §6 pero no estaban en el catálogo de enums).
  _Prueba:_ test que importa y verifica valores. _Depende de:_ T-0.1.1

- [x] **T-0.2.3 · [Backend] `core/errors.py` — excepciones de dominio + handlers**
  `DomainError` base y subclases (`NotFoundError`, `ForbiddenError`, `ConflictError`, `OutOfStockError`, `ShiftClosedError`, `CancelWindowClosedError`, `OutOfCoverageError`, `InvalidTransitionError`). Handler global que las mapea al formato `{"error":{"code","message","details"}}` (§20).
  _Prueba:_ test de API que fuerza un `NotFoundError` y valida el JSON y el status. _Depende de:_ T-0.2.1

- [x] **T-0.2.4 · [Backend] `core/logging.py` y middleware de `request_id`**
  Logging stdlib; en `production` formato JSON. Middleware que asigna `X-Request-Id` y lo agrega a los logs.
  _Prueba:_ una request devuelve header `X-Request-Id` y aparece en el log. _Depende de:_ T-0.2.1

- [x] **T-0.2.5 · [Backend] `core/timezone.py`**
  Helpers `now_utc()`, `to_local(dt)`, `resolve_shift_instant(date, "HH:MM")` usando `zoneinfo` y `APP_TIMEZONE`. Agregar **`tzdata`** a `requirements.txt`: se verificó que en Windows `zoneinfo.ZoneInfo("America/Argentina/Buenos_Aires")` falla con `ZoneInfoNotFoundError` sin ese paquete (Windows no trae la base IANA integrada) — sin él, cualquiera desarrollando en Windows tendría el backend roto desde este punto.
  _Prueba:_ tests: `resolve_shift_instant("2026-09-10","12:00")` da el instante UTC correcto para Buenos Aires. _Depende de:_ T-0.2.1

- [x] **T-0.2.6 · [Backend] `main.py` — app FastAPI + healthcheck**
  Crea la app, registra handlers de error, middleware de `request_id`, CORS (dev: `FRONTEND_ORIGIN`), prefija routers en `/api/v1`. Endpoint `GET /api/v1/health` → `{"status":"ok","env":...}`. `lifespan` mínimo (arranque/apagado, sin scheduler — ver `02_Documento_Tecnico.md §10`, resolución bajo demanda).
  _Prueba:_ `uvicorn app.main:app` y `GET /api/v1/health` responde 200. `GET /api/docs` abre Swagger. _Depende de:_ T-0.2.3, T-0.2.4

## Tema 0.3 · Base de datos y migraciones

- [x] **T-0.3.1 · [Backend] `db/session.py` — engine SQLite + PRAGMAs**
  `create_engine(settings.database_url, connect_args={"check_same_thread": False})`, listener que aplica `PRAGMA foreign_keys=ON`, `journal_mode=WAL`, `busy_timeout=5000`. `SessionLocal` y `get_session()` (commit/rollback/close). Crea `backend/data/` si falta.
  _Prueba:_ script que abre sesión y ejecuta `PRAGMA foreign_keys` → `1`. _Depende de:_ T-0.2.1

- [x] **T-0.3.2 · [Backend] `db/base.py` — DeclarativeBase**
  `class Base(DeclarativeBase): ...` con convención de nombres de constraints/índices. Módulo que importa todos los modelos (se irá completando fase a fase).
  _Prueba:_ importar `Base` sin errores. _Depende de:_ T-0.3.1

- [x] **T-0.3.3 · [Infra] Alembic init y `env.py` conectado a Settings**
  `alembic init alembic`; ajustar `env.py` para tomar `settings.database_url` y `Base.metadata`, `render_as_batch=True` (SQLite). `alembic.ini` sin URL hardcodeada.
  _Prueba:_ `alembic revision -m "baseline"` y `alembic upgrade head` sin errores (aún sin tablas). _Depende de:_ T-0.3.2

- [x] **T-0.3.4 · [Backend] `db/seed.py` — esqueleto idempotente**
  Función `run_seed(session)` vacía pero ejecutable vía `python -m app.db.seed`. Se completa en cada fase.
  _Prueba:_ `python -m app.db.seed` termina sin error. _Depende de:_ T-0.3.1

## Tema 0.4 · Frontend — base visual (sin funcionalidad)

> Nota (histórico de la decisión de estilo): la elección original del proyecto fue `01_Editorial_Premium.html`. El 2026-09-10 se migró a **"Artesanal · Cocina de Olla"** (`mockups/04_Artesanal_Organico.html`), que es el estilo **confirmado y vigente**. El 2026-09-11, al retomar el proyecto en un chat nuevo, hubo una confusión momentánea que revirtió por error toda la documentación a Editorial Premium; se corrigió el mismo día y quedó definitivamente en **Artesanal · Cocina de Olla**. Además, el código de `backend/` y `frontend/` (Fases 0-2) se reinició desde cero, por lo que todas las tareas de Fases 0-2 vuelven a `[ ]` y se re-implementan y re-validan contra el sistema Artesanal · Cocina de Olla.

- [x] **T-0.4.1 · [Frontend] `assets/css/base.css` — utilidades del sistema**
  Declarar `.paper`, `.blob`/`.blob2`, `.stamp`, `.tape`, `.dashed`, `.lift`, `.foodA..D` y el media query de `prefers-reduced-motion` (según skill `morfi-frontend`).
  _Prueba:_ una página de test muestra las utilidades y una card con hover `.lift`. _Depende de:_ —

- [x] **T-0.4.2 · [Frontend] `tailwind.config.js` + carga de fuentes**
  Tokens (`kraft/cream/bark/forest/mustard/brick`), `fontFamily` display=Bricolage Grotesque / hand=Caveat / sans=Inter, `content` con html y js. Link a Google Fonts. En dev se admite el CDN de Tailwind. **Corrección a `base.css` de T-0.4.1**: le faltaban las directivas `@tailwind base/components/utilities` — sin ellas, el build de producción del §15.6 (`tailwindcss -i assets/css/base.css -o assets/css/tailwind.css`) no generaría ninguna clase de Tailwind, solo las utilidades custom. Se detectó corriendo un build real de Tailwind (no solo revisando el JS), y se corrigió.
  _Prueba:_ el texto renderiza con las 3 fuentes y los colores del token aplican. _Depende de:_ —

- [x] **T-0.4.3 · [Frontend] Parciales base: `header`, `bottom-nav`, `top-nav`, `cart-bar`**
  HTML de los parciales en `frontend/partials/` según las recetas de la skill. `assets/js/ui.js` con `injectPartials()` (fetch + innerHTML) y helpers (`$`, `toast`).
  _Prueba:_ una página incluye los parciales vía `ui.js` y se ven bien en móvil y escritorio. _Depende de:_ T-0.4.2

- [x] **T-0.4.4 · [Frontend] `index.html` — Home del cliente (solo estilo)**
  Portar el mockup `04_Artesanal_Organico.html` a la estructura real, usando los parciales de T-0.4.3 (`header`, `cart-bar`, `bottom-nav` vía `data-partial`): chip de estado, countdown (ticket de kraft, estático), Plato del Día (sello), promos, chips de categoría, lista de productos con un ítem "sin stock", panel de dirección. **Todo con datos hardcodeados**, sin fetch. **Fotos reales en vez de emoji/gradiente**: el usuario proveyó 9 fotos de platos (`documentacion/platos_test/`, copiadas a `frontend/assets/img/platos/`) — se usan en el Plato del Día y en 8 ítems del menú (uno marcado "sin stock"), reemplazando los placeholders `.foodA..D` + emoji del mockup original.
  _Prueba:_ a 360px se ve la versión móvil con bottom nav; a 1440px el layout cambia (nav arriba, grilla, sin elementos estirados). _Depende de:_ T-0.4.3

- [x] **T-0.4.5 · [Frontend] `assets/js/format.js`**
  `formatMoney(cents)` → `$00.000`, `formatDate`, `formatTime`, `pad2`. **`formatTime` fuerza `hour12: false`**: sin eso, `toLocaleTimeString("es-AR")` devuelve 12hs con sufijo (`"12:00 p. m."`) en vez de las 24hs que usa el resto del proyecto ("Cierre 12:00") — se detectó corriendo la función de verdad, no revisando el código a ojo.
  _Prueba:_ tests manuales en consola: `formatMoney(3180000) === "$31.800"`. _Depende de:_ —

- [x] **T-0.4.6 · [Frontend] `assets/js/api.js` y `auth.js` (esqueleto)**
  `api.js` con el wrapper de `fetch` (baseURL, token en memoria, `refreshSession`, `ApiError`) y `auth.js` con `setToken`/`bootstrapSession`/`login`/`logout`/`requireRole` (todavía sin backend de auth: `T-1.11.4` ya da por hecho que esto existe desde acá). Documentar `window.__MC_API__`. **Nota:** el §15.2/§15.3 nombraba la función privada de refresh `tryRefresh` en `api.js` pero `auth.js` importaba `refreshSession` — se unificó exportando una sola función, `refreshSession`.
  _Prueba:_ `api.get('/health')` desde la consola del navegador devuelve el JSON del backend. _Depende de:_ T-0.2.6, T-0.4.2

## Tema 0.5 · Tooling

> **Nota:** este tema tenía una tarea `T-0.5.1` para un script `iniciar.bat`. Se descartó definitivamente al pivotear a despliegue en producción (Vercel + VPS): el proyecto deja de pensarse como "correr local con un doble clic". El desarrollo local se arranca a mano (§24.2 del Documento Técnico, documentado en el `README.md`); el despliegue real es la nueva Tema 0.7 de esta fase.

- [x] **T-0.5.2 · [Infra] `pytest` configurado + `conftest.py` base**
  `conftest.py` con fixtures `session` (SQLite en memoria + `create_all`) y `client` (`httpx.AsyncClient` con override de `get_session`).
  _Prueba:_ `pytest` corre (0 tests o 1 test dummy de `/health`) en verde. _Depende de:_ T-0.3.2, T-0.2.6

## Tema 0.6 · Documentación viva

- [x] **T-0.6.1 · [Docs] `documentacion/Usuarios.md`**
  Archivo de usuarios de prueba (tabla rol / email / password / notas). Se completa cuando el seed de la Fase 1 los genere (`T-1.10.1`).
  _Prueba:_ el archivo existe y está enlazado desde este roadmap. _Depende de:_ —

- [x] **T-0.6.2 · [Docs] Plantilla `Fase 0X - <nombre>.md`**
  Definir el esqueleto que tendrán los documentos de cierre de fase (objetivo, temas, qué se hizo y cómo quedó explicado con código y en palabras, cómo probar), guardados en `documentacion/Fases/`. Creada en `documentacion/Fases/_Plantilla_Fase.md`.
  _Prueba:_ plantilla acordada con el usuario. _Depende de:_ —

## Tema 0.7 · Despliegue: Vercel (frontend) + VPS Contabo (backend y base de datos)

> El VPS ya está contratado (Contabo, 4 vCPU / 8 GB RAM / 100 GB, plan anual). No se documentan credenciales reales en ningún archivo del repo: acceso SSH por clave pública/privada, y todo secreto vive en `backend/.env` únicamente dentro del servidor. Runbook completo (sin credenciales) en `deploy/DEPLOY.md`.

- [x] **T-0.7.1 · [Infra] Alta y hardening inicial del VPS Contabo**
  Usuario no-root dedicado con sudo; acceso SSH solo por clave pública/privada (deshabilitar login por contraseña); firewall `ufw` abierto solo a 22/80/443; actualizaciones del sistema. Runbook completo en `deploy/DEPLOY.md §1`. Dos gotchas reales encontrados y documentados ahí: el servicio se llama `ssh` (no `sshd`) en Ubuntu, y `/etc/ssh/sshd_config.d/50-cloud-init.conf` pisa `PasswordAuthentication` de `sshd_config` si no se corrige también.
  _Prueba:_ login SSH por clave funciona; login por contraseña rechazado; `ufw status` muestra solo los puertos esperados. **Verificado en el VPS real**: `ssh morfi@<IP>` entra sin contraseña; `ssh root@<IP>` rechaza inmediato con `Permission denied (publickey)`; `ufw status` muestra exactamente OpenSSH/80/443 (v4 y v6). _Depende de:_ —

- [x] **T-0.7.2 · [Infra] Stack del servidor**
  Instalar Python 3.11+, `venv`, Nginx y Certbot en el VPS. Clonar el repositorio en el servidor (solo lectura de despliegue, sin credenciales de escritura innecesarias). Runbook en `deploy/DEPLOY.md §2`. El repositorio es **público** (confirmado vía API de GitHub), así que el clonado no necesita ninguna credencial — si en el futuro pasa a privado, hace falta una *deploy key* de solo lectura.
  _Prueba:_ `python3 --version`, `nginx -v` y `certbot --version` responden en el servidor. **Verificado en el VPS real:** Python 3.12.3, Nginx 1.24.0, Certbot 2.9.0; repo clonado en `~/morfi_center` con la estructura completa. _Depende de:_ T-0.7.1

- [x] **T-0.7.3 · [Infra] Servicio `systemd` + Nginx reverse proxy + HTTPS**
  `deploy/morficenter-api.service` corriendo Uvicorn con reinicio automático; `deploy/nginx.morficenter.conf` como reverse proxy hacia Uvicorn; certificado HTTPS con Certbot. Sin dominio propio: se usa `sslip.io` (gratis) para tener un hostname válido para Certbot. Runbook completo en `deploy/DEPLOY.md §3`, incluidos los gotchas reales de `sudo` no interactivo por SSH y de `nohup ... &` dejando la sesión colgada. **Nota de orden:** esta tarea en la práctica necesitó primero el contenido de `T-0.7.4` (venv, `.env`, migraciones) — no se puede arrancar un servicio `systemd` de algo que todavía no está instalado ni migrado. Se hicieron juntas.
  _Prueba:_ `systemctl status morficenter-api` en verde; `https://<host-contabo>/api/v1/health` responde 200 con candado válido. **Verificado en el VPS real:** `Active: active (running)`; `curl https://<host-sslip>/api/v1/health` → 200 con certificado válido (sin `-k`); `http://` redirige a `https://`. _Depende de:_ T-0.7.2, T-0.2.6

- [x] **T-0.7.4 · [Infra] Primer deploy del backend al VPS**
  Traer el código al servidor (git pull o rsync), `venv` + `requirements.txt`, `backend/.env` real cargado a mano en el servidor, `alembic upgrade head`, `python -m app.db.seed`. **Nota de orden:** se hizo junto con `T-0.7.3` (ver nota ahí) — depende de `T-0.7.2` en la práctica, no de `T-0.7.3`.
  _Prueba:_ el healthcheck responde en producción con datos semilla cargados. **Verificado:** `{"status":"ok","env":"production"}` en el VPS real, con la migración `baseline` aplicada y el seed (todavía vacío, `run_seed()` sin contenido hasta Fase 1) corrido sin error. _Depende de:_ T-0.7.2

- [x] **T-0.7.5 · [Infra] Proyecto en Vercel + primer deploy del frontend**
  Conectar el repositorio a Vercel; configurar el *build command* del front (Tailwind) o commitear `tailwind.css` ya generado; `window.__MC_API__` apuntando a la URL pública del backend en el VPS. **Gotcha real:** el repo es un monorepo (`backend/`, `frontend/`, `documentacion/` al mismo nivel) — Vercel por defecto sirve desde la raíz del repo, no desde `frontend/`, y da 404 en `/`. Hay que fijar **Root Directory = `frontend`** en Settings → Build and Deployment.
  _Prueba:_ la URL de Vercel sirve el home con estilo; las llamadas a `/health` desde la consola del navegador llegan al backend del VPS. **Verificado con un navegador real (Playwright)** contra el sitio en vivo: `fetch(window.__MC_API__ + '/health', {credentials:'include'})` desde `https://morfi-center.vercel.app` devuelve `{"status":"ok","env":"production"}`, sin errores de CORS en consola (requirió adelantar el `FRONTEND_ORIGIN` de `T-0.7.6`, ver nota ahí). _Depende de:_ T-0.7.4, T-0.4.4

- [x] **T-0.7.6 · [Backend] CORS y cookies cross-site en producción**
  `FRONTEND_ORIGIN` = URL real de Vercel; `allow_origins=[FRONTEND_ORIGIN]` + `allow_credentials=True`; cookie de refresh con `SameSite=None; Secure` en producción (ver `02_Documento_Tecnico.md §17`). **Parte ya hecha, adelantada para que `T-0.7.5` pudiera probarse:** `FRONTEND_ORIGIN` en el `.env` del VPS ya apunta a `https://morfi-center.vercel.app` (verificado: el header `access-control-allow-origin` responde correcto). `COOKIE_SAMESITE=none` ya estaba seteado desde `T-0.7.3`. **Queda pendiente** la única parte que de verdad depende de `T-1.4.2` (que no existe hasta Fase 1): probar que el login real deja la cookie de refresh y que `/auth/refresh` funciona cross-site. Esta tarea se cierra recién cuando eso se verifique en Fase 1.
  _Prueba:_ login desde el front en Vercel contra el backend del VPS deja la cookie de refresh y `/auth/refresh` funciona entre los dos dominios. **Cerrada al completar el Tema 1.5 (2026-09-23), verificado contra producción real** con el `Origin` de Vercel en cada request:
  - **Preflight** `OPTIONS /auth/login` → `200` con `access-control-allow-origin: https://morfi-center.vercel.app`, `allow-credentials: true` y `allow-headers: content-type` (es lo primero que pregunta el navegador antes de un POST cross-site).
  - **Cookie de refresh** con los atributos exactos que exige el caso cross-site: `HttpOnly; Max-Age=604800; Path=/api/v1/auth; SameSite=none; Secure`.
  - **Ciclo completo cross-site**: `register` → `201`, `login` → token, `GET /auth/me` con ese token → datos correctos, **`POST /auth/refresh` con la cookie → 200** (el punto que quedaba pendiente), `logout` → 204.
  - **Origen no autorizado** (`https://sitio-malicioso.com`): la respuesta **no** incluye ningún header `access-control-allow-origin`, así que el navegador bloquea la lectura.
  El usuario de prueba creado para esto se borró de la base de producción. La comprobación con un navegador real haciendo clic en un formulario llega naturalmente con `T-1.11.1`; lo que esta tarea debía garantizar —el contrato del backend— está verificado. _Depende de:_ T-0.7.5, T-1.4.2

- [x] **T-0.7.7 · [Infra] Backups automáticos**
  Cron diario en el VPS que copia `backend/data/morfi.db` y `backend/storage/payment_proofs/` a otro destino (otro directorio del disco como mínimo; almacenamiento externo cuando se defina). `deploy/backup.sh` + cron de usuario (sin `sudo`), retiene los últimos 14. Runbook en `deploy/DEPLOY.md §6`.
  _Prueba:_ tras forzar la corrida del cron, aparece una copia nueva con timestamp. **Verificado en el VPS real:** `~/backups/20260916_024343/` con `morfi.db` y `payment_proofs/` adentro; cron instalado (`0 3 * * *`) y confirmado con `crontab -l`. _Depende de:_ T-0.7.4

- [x] **T-0.7.8 · [Infra] Despliegue continuo del backend (GitHub Actions → VPS)**
  `.github/workflows/deploy-backend.yml`: en cada push a `master`, se conecta por SSH al VPS (usando `secrets.VPS_HOST`, `secrets.VPS_USER`, `secrets.VPS_SSH_KEY` cargados por el usuario en GitHub → *Settings → Secrets and variables → Actions*, nunca en el repo) y ejecuta `git pull`, instala dependencias si cambiaron, `alembic upgrade head` y reinicia `systemctl restart morficenter-api`. El front no necesita este paso: Vercel ya redeploya solo al conectarlo al repositorio (T-0.7.5). Clave SSH dedicada (no la personal); regla `sudo NOPASSWD` acotada a un único comando (`systemctl restart morficenter-api`, no `sudo` general). Runbook en `deploy/DEPLOY.md §7`.
  _Prueba:_ un push a `master` con un cambio trivial en el backend se ve reflejado en `https://<host-contabo>/api/v1/health` sin tocar el servidor a mano. **Verificado dos veces en el VPS real** (el cambio de prueba y su revert): el Action terminó en `success`, el servidor pulleó el commit exacto solo, el `MainPID` del servicio cambió las dos veces (reinicio real, no el proceso viejo), y `/health` siguió respondiendo 200. _Depende de:_ T-0.7.4

- [x] **T-0.7.9 · [Docs] Runbook `deploy/DEPLOY.md`**
  Pasos reproducibles de todo lo anterior, sin ninguna credencial real (IP, usuarios y contraseñas quedan fuera del repo). Checklist de accesos necesarios para retomar el despliegue desde cero (incluye qué secretos cargar en GitHub Actions y dónde). Se fue armando incrementalmente en cada tarea (§1 a §7); esta tarea agregó el checklist de accesos consolidado al principio del archivo.
  _Prueba:_ siguiendo el runbook al pie de la letra (con datos propios) se puede reconstruir el despliegue en un VPS nuevo. Todas las secciones (1-7) fueron ejecutadas y verificadas de verdad contra el VPS real durante T-0.7.1 a T-0.7.8, no son teóricas. _Depende de:_ T-0.7.1 a T-0.7.8

## Cierre de fase

- [x] **T-0.99 · [Docs] `Fase 00 - Andamiaje y base visual.md`**
  Documento final de la fase: qué se hizo y cómo quedó implementado (estructura del proyecto, esqueleto del backend, base de datos y migraciones, base visual del front con el estilo Artesanal · Cocina de Olla, tooling, documentación viva, y toda la infraestructura de despliegue — Vercel + VPS Contabo + CI/CD), fragmentos de código clave, cómo probar. **Nota:** esta tarea no existía en versiones anteriores del roadmap (todas las demás fases sí tienen su cierre) — se agrega ahora, al completar la Fase 0, para que use la plantilla de `T-0.6.2`.

---

# FASE 1 · Usuarios, roles y autenticación

> Fundación de identidad. Al terminar, el front muestra **solo** lo de usuarios: registro, login (local y Google), sesión, perfil, y el admin puede crear repartidores y otros admins.

## Tema 1.1 · Modelo y lógica de usuarios

- [x] **T-1.1.1 · [Lógica] Reglas de validación de usuario**
  `UserService` (puro): validar email (formato + unicidad delegada al repo), teléfono opcional, nombre/apellido requeridos, política de contraseña (mínimo 8, al menos una letra y un número). Funciones `normalize_email`, `validate_password`. **Corrección (al armar `T-1.1.2`):** se le agregó un **máximo de 72 bytes** a `validate_password` — sin él, una contraseña más larga hace que `bcrypt.hashpw` explote con `ValueError` (límite duro de bcrypt) en vez de dar un error de validación prolijo.
  _Prueba:_ tests unitarios de cada regla (válidos e inválidos). _Depende de:_ T-0.2.2

- [x] **T-1.1.2 · [Lógica] Hash y verificación de contraseñas**
  `core/security.py`: `hash_password`, `verify_password` con `bcrypt` directo (`rounds` ≥ 12). **Hallazgo real:** `bcrypt` 4.x (nuestro pin, `<5.0`) trunca en silencio contraseñas de más de 72 bytes en vez de lanzar error — comportamiento distinto a `bcrypt` ≥ 5.0 (que sí lanza `ValueError`). Verificado empíricamente instalando ambas versiones. Documentado en `02_Documento_Tecnico.md §2`.
  _Prueba:_ test: `verify_password(p, hash_password(p))` True; contraseña distinta False; el hash no es el texto plano. **Además:** cost factor real = 12; misma contraseña hasheada dos veces da hashes distintos (sal); comportamiento de truncado a 72 bytes documentado con un test. _Depende de:_ T-0.1.3

- [x] **T-1.1.3 · [Lógica] Emisión y verificación de JWT**
  `core/security.py`: `create_access_token(user)` (15 min, claims `sub`,`role`,`type=access`), `create_refresh_token(user)` (7 días, `jti`,`type=refresh`), `decode_token`. Errores claros para expirado/inválido: se agregan `TokenExpiredError`/`TokenInvalidError` a `core/errors.py` (extensión de `T-0.2.3`), ambas con `status_code=401` y `code="NOT_AUTHENTICATED"` (coincide con la tabla de §20) aunque sean clases distintas — permite que el código interno distinga la causa sin cambiar el contrato de la API. `user` se tipa como `Protocol` (`id`+`role`) para no depender todavía del modelo `User` real, que llega en `T-1.2.1`.
  _Prueba:_ tests: token válido decodifica; token expirado y firma inválida lanzan el error esperado. _Depende de:_ T-0.2.1

## Tema 1.2 · Persistencia de usuarios

- [x] **T-1.2.1 · [Backend] Modelos `User`, `UserAuthProvider`, `UserProfile`**
  SQLAlchemy según `02_Documento_Tecnico.md §6.1`. Timestamps UTC automáticos. **Agregado al armar la tarea:** `app/db/types.py`, con las piezas reutilizables por todos los modelos que vienen — `UTCDateTime` (guarda y devuelve siempre UTC, y **rechaza** datetimes naive en vez de persistir una hora ambigua), `enum_column()` (enum de Python → `TEXT` + `CHECK`, persistiendo el *valor* y no el nombre del miembro, como exige §6) y `TimestampMixin` (`created_at`/`updated_at` automáticos). Además, `app/db/base.py` ahora importa `app.models` al final del módulo para que `Base.metadata` conozca las tablas (lo necesita el `--autogenerate` de `T-1.2.3`).
  _Prueba:_ crear un `User` en una sesión de test y releerlo. **Verificado con 15 tests:** defaults (`CUSTOMER`/`ACTIVE`), `updated_at` se mueve en cada update y `created_at` no, email duplicado y rol inválido rechazados por la base, misma cuenta de Google en dos usuarios rechazada, varios proveedores `local` con `provider_uid` NULL sí permitidos, borrado de usuario en cascada a proveedores y perfil, `vehicle_type` inválido rechazado, y conversión horaria real (12:00 -03:00 se relee como 15:00 UTC). _Depende de:_ T-0.3.2, T-1.1.1

- [x] **T-1.2.2 · [Backend] Modelos `Cart` y `CustomerBalance` (vacíos, para el alta)**
  Se crean junto al usuario CUSTOMER (aunque su lógica llegue en Fases 6 y 12). Solo tabla + relación. `carts` y `customer_balances` de §6.5/§6.8; **no** se crean todavía `cart_items` ni `balance_transactions` (dependen de `products` y `orders`, que llegan en Fases 3 y 9). Se agregó a `customer_balances` un `CHECK(balance >= 0)`, que §6.8 pedía en comentario (`-- centavos, >= 0`) pero no tenía como constraint.
  **Corrección a `T-1.2.1`:** su test `test_updated_at_changes_on_update...` era **intermitente** — comparaba dos `now_utc()` consecutivos y en Windows el reloj tiene ~15 ms de resolución, así que a veces devolvía el mismo instante y el test fallaba sin que nada estuviera roto (se manifestó recién al correr la suite completa, no en aislamiento). Se reescribió con timestamps fijos explícitos. Además, el test de saldo duplicado de esta tarea se reescribió con `INSERT` crudo: con el ORM, el *identity map* de SQLAlchemy corta el duplicado antes de la base y la restricción real nunca se probaba.
  _Prueba:_ al persistir un usuario CUSTOMER de test, existen su cart y su balance en 0. **Verificado con 9 tests:** carrito y saldo creados con el usuario, unicidad de ambos por usuario, saldo negativo rechazado por la base, acreditación, cascada al borrar el usuario, FK contra usuario inexistente, y dinero persistido como entero de centavos. Suite completa corrida 4 veces seguidas (114 tests) sin intermitencias. _Depende de:_ T-1.2.1

- [x] **T-1.2.3 · [Backend] Migración Alembic de la Fase 1**
  `alembic revision --autogenerate -m "fase1 usuarios"`; revisar el script; `upgrade head`. Crea las 5 tablas de la fase (`users`, `user_auth_providers`, `user_profiles`, `carts`, `customer_balances`).
  **Dos bugs reales encontrados al revisar el script autogenerado (por eso se revisa, no se aplica a ciegas):**
  1. Alembic renderizó las columnas de fecha como `app.db.types.UTCDateTime()` **sin importar `app`** en el script → `NameError` al correr la migración. En local no se habría notado (las tablas ya existían por `create_all` en los tests): habría explotado en el **deploy automático al VPS**, dejando el servidor a medio migrar. Arreglado de raíz con un `render_item` en `alembic/env.py` que renderiza los tipos propios por su tipo SQL base (`sa.DateTime()`) — aplica a toda migración futura. Además es lo correcto de por sí: una migración no debe importar código de la app, porque ese código puede renombrarse o desaparecer y las migraciones viejas tienen que seguir corriendo.
  2. El primer test de migraciones corría **contra la base de desarrollo real**, no contra una temporal: `env.py` pisa la URL del `Config` con la de `Settings` (T-0.3.3), así que `config.set_main_option(...)` desde el test no tiene efecto (el `downgrade` del test llegó a revertir `data/morfi.db`, vacía, sin pérdida). Se corrige parcheando `settings.database_url`, y se verificó que la base real queda intacta tras correr la suite.
  _Prueba:_ `alembic upgrade head` y `downgrade -1` limpios; las tablas existen en `morfi.db`. **Verificado:** ciclo `upgrade` → `downgrade -1` → `upgrade` sin errores, y 4 tests nuevos, incluido uno que compara el esquema migrado contra `Base.metadata` con `compare_metadata` y **falla si alguien toca un modelo y se olvida de generar la migración**. _Depende de:_ T-1.2.2

- [x] **T-1.2.4 · [Backend] `UserRepository`**
  `get_by_email`, `get_by_id`, `create`, `list(role=None, page, page_size)`, `get_provider(provider, uid)`, `link_provider`. **Decisiones al implementarlo:** `list` devuelve `(items, total)` y no solo los ítems — el total sin paginar lo necesita el formato de respuesta paginada de §21 (`{items, page, page_size, total}`); `create` y `get_by_email` **normalizan el email** (además del servicio), porque es un invariante de persistencia: si se guardara sin normalizar, `Ana@Example.com` y `ana@example.com` convivirían como dos cuentas distintas de la misma persona; `create` hace `flush` (asigna el `id`) pero no `commit` — la transacción la cierra `get_session` (T-0.3.1).
  _Prueba:_ tests de cada método contra la DB de test. **Verificado con 16 tests**, entre ellos: búsqueda por email insensible a mayúsculas y espacios, el `total` del paginado es el global y no el de la página, pedir una página más allá de la última devuelve vacío en vez de error, el filtro por rol cuenta solo ese rol, y `get_provider` no confunde dos proveedores distintos que compartan el mismo `uid`. _Depende de:_ T-1.2.3

## Tema 1.3 · Registro (cuenta propia)

- [x] **T-1.3.1 · [Lógica] `AuthService.register`**
  Recibe datos validados → normaliza email → verifica que no exista → hashea contraseña → crea `User(role=CUSTOMER)` + `UserAuthProvider(local)` + `Cart` + `CustomerBalance`. Devuelve el usuario. Lanza `ConflictError` si el email existe. `AuthService` recibe la `Session` y arma su propio `UserRepository`. **Las reglas de formato (política de contraseña, formato de email) no se revalidan acá**: el roadmap las asigna al schema del endpoint (`T-1.3.2`), que las convierte en el `422 VALIDATION_ERROR` por campo de §20 — el servicio resuelve unicidad y composición, no formato.
  **Bug propio encontrado por un test:** el manejo del alta duplicada simultánea (dos requests que pasan los dos el chequeo previo y una choca contra el `UNIQUE`) estaba envuelto solo alrededor del `flush` final, pero el `UNIQUE` salta **antes**, en el `flush` de `UserRepository.create` — así que el `IntegrityError` se escapaba y habría sido un 500 en vez de un 409. El `try` ahora cubre todo el bloque de creación.
  _Prueba:_ test unitario con repo real: alta OK; alta duplicada → `ConflictError`. **Verificado con 13 tests**, incluidos: contraseña verificable pero nunca en texto plano, carrito y saldo en 0 creados, teléfono vacío guardado como `NULL` y no como string vacío, duplicado detectado ignorando mayúsculas y espacios, un alta fallida no deja usuario a medias, y el caso simultáneo de arriba (simulado con `monkeypatch` sobre `get_by_email`). _Depende de:_ T-1.2.4, T-1.1.2

- [x] **T-1.3.2 · [Backend] `POST /api/v1/auth/register`**
  Schema `RegisterIn` (first_name, last_name, email, phone?, password). Llama a `AuthService.register`. Devuelve 201 con el usuario (sin datos sensibles) y ya emite tokens (login automático). `RegisterIn` aplica las reglas puras de `T-1.1.1` (`is_valid_name`, `is_valid_email`, `validate_password`) como `field_validator`, así que la política de contraseña sale como `422` por campo y no como error genérico. Se agregan `app/schemas/user.py` (`UserOut`, sin `password_hash`), `TokenOut`, y en `app/api/routes/auth.py` los helpers `set_refresh_cookie` / `session_response` que **reutilizan `T-1.4.2`, `T-1.4.3` y `T-1.4.4`**. Cookie `mc_refresh`: `HttpOnly`, `Path=/api/v1/auth`, `max_age` de 7 días, `SameSite` desde `COOKIE_SAMESITE` y `Secure` solo en `production` (en dev es `http://localhost`, donde `Secure` la bloquearía). Se usa `Annotated[Session, Depends(get_session)]` en vez de `Depends` como default: `ruff` marca lo segundo (B008) y `Annotated` es la forma recomendada por FastAPI.
  **Extensión de `T-0.2.3` que hacía falta acá:** no existía handler de `RequestValidationError`, así que los 422 de Pydantic salían en el formato propio de FastAPI (`{"detail": [...]}`) y no en el `{"error": {"code": "VALIDATION_ERROR", ...}}` que exige §20 — el front habría tenido que entender dos formatos de error distintos. Se agregó el handler, con `details.fields` = lista de `{field, message}` para pintar el error debajo de cada input.
  _Prueba:_ test de API: 201 + cookie de refresh + `access_token`; email repetido → 409 con `code: CONFLICT`. **Verificado con 19 tests y, además, contra un servidor real** (`uvicorn` en local, con `curl`): alta → `201` con `Set-Cookie: mc_refresh=...; HttpOnly; Max-Age=604800; Path=/api/v1/auth`; email repetido con otras mayúsculas → `409 CONFLICT`; contraseña débil → `422 VALIDATION_ERROR` con `field: password`; y en la base, el usuario con su carrito y su saldo en 0. Los tests cubren también que la respuesta nunca incluya la contraseña ni su hash, que una entrada inválida no cree usuarios a medias, y que una contraseña más larga que el límite de bcrypt dé 422 en vez de explotar. _Depende de:_ T-1.3.1, T-1.1.3

## Tema 1.4 · Login local + sesión

- [x] **T-1.4.1 · [Lógica] `AuthService.authenticate`**
  Email + password → busca usuario → `verify_password` → valida `status=ACTIVE` → devuelve usuario o lanza `ForbiddenError`/`NotAuthenticated` (mensaje genérico "credenciales inválidas" para no filtrar existencia). Se agrega `NotAuthenticatedError` (401, `NOT_AUTHENTICATED`) a `core/errors.py` — extensión de `T-0.2.3`, como las de `T-1.1.3`.
  **Tres decisiones de seguridad tomadas al implementarlo:**
  1. **Mismo mensaje** para email inexistente, contraseña incorrecta y cuenta sin contraseña (solo Google) — distinguirlos permitiría enumerar qué emails están registrados. Una cuenta Google-only tampoco explota al pasarle una contraseña (`verify_password(p, None)` habría tirado excepción).
  2. **Mismo tiempo de respuesta**: si el email no existe no se corre bcrypt y la respuesta vuelve instantánea, y ese desfase delata la existencia igual que un mensaje distinto. Se verifica contra un `_DUMMY_HASH` de módulo cuando no hay usuario o no tiene contraseña. **Medido:** 185 ms con email existente y contraseña mala vs 185 ms con email inexistente — 0 ms de diferencia.
  3. El chequeo de `status` va **después** de verificar la contraseña: así el aviso "tu cuenta no está habilitada" (`ForbiddenError`, necesario para que un suspendido no crea que olvidó la contraseña) solo lo ve quien demostró ser el dueño de la cuenta, y no sirve para enumerar emails.
  > **Para `T-1.11.1` (pantalla de login):** como el backend no puede decir "esta cuenta entra con Google" sin filtrar existencia, la pantalla necesita un texto fijo tipo "¿te registraste con Google? Usá el botón de Google" — si no, ese usuario queda sin forma de darse cuenta.
  _Prueba:_ tests: credenciales OK; password mala; usuario suspendido. **Verificado con 11 tests**, incluidos: los mensajes de email inexistente y contraseña incorrecta son *exactamente el mismo texto*, un suspendido con contraseña mala recibe el genérico (no el de suspensión), cuenta Google-only rechazada sin explotar, email en cualquier combinación de mayúsculas, contraseña vacía, y login de staff (ADMIN). _Depende de:_ T-1.2.4, T-1.1.2

- [x] **T-1.4.2 · [Backend] `POST /api/v1/auth/login`**
  Devuelve `{access_token, token_type, expires_in, user}` y `Set-Cookie: mc_refresh` (httpOnly, SameSite=Lax, Path acotado, Secure en prod). Reutiliza `set_refresh_cookie` y `session_response` de `T-1.3.2`. **`LoginIn` a propósito no aplica las validaciones de formato de `RegisterIn`**: si el login exigiera la política de contraseña vigente, endurecerla en el futuro dejaría a las cuentas viejas sin poder entrar nunca más. Credenciales que no cumplen simplemente no coinciden con ninguna cuenta → 401.
  _Prueba:_ test de API: login OK setea cookie y token; login inválido → 401. **Verificado con 11 tests**: contraseña incorrecta y email inexistente devuelven respuestas **idénticas** (mismo status y mismo cuerpo), suspendido → 403, cada login emite un `jti` distinto, email en cualquier combinación de mayúsculas, campo faltante → 422 en formato del proyecto, la respuesta nunca incluye la contraseña, y una cuenta con contraseña que hoy no pasaría el registro **sí** puede loguearse. _Depende de:_ T-1.4.1, T-1.1.3
  > **Hallazgo de entorno (no del código), encontrado probando esta tarea contra un servidor real:** en la máquina de desarrollo (Windows, proyecto en `D:`), tras un `POST /auth/register` exitoso el dato queda invisible unos segundos para otras conexiones — un login inmediato da 401 y después funciona. Se verificó que el código emite `INSERT` + `COMMIT` correctamente (traza SQL), que con la base en `C:` no ocurre, y que **en producción no ocurre** (registro en el VPS → dato visible al instante, confirmado por un registro duplicado inmediato que dio 409 y por lectura directa de la base por SSH). No afecta los tests (usan SQLite en memoria) ni producción (Linux). Causa exacta sin determinar; el candidato más probable es el antivirus sobre los archivos `-wal`/`-shm`. Se descartó que fuera Google Drive: su configuración no tiene ninguna carpeta local sincronizada (`roots` y `mirror_item` vacíos).

- [x] **T-1.4.3 · [Backend] `POST /api/v1/auth/refresh`**
  Lee la cookie, valida el refresh (tipo + expiración + no revocado), rota el `jti`, emite nuevo access (+ nueva cookie). De las dos opciones que dejaba abiertas §16.1 (tabla `revoked_tokens` o rotación) se implementan **las dos juntas**: rotación de **un solo uso** respaldada por la tabla — el refresh usado se quema, así que si alguien roba la cookie, en cuanto el dueño legítimo refresca la copia robada deja de servir. Modelo `RevokedToken(jti PK, expires_at indexado)` + migración `c12854fa93c4` (probada con `upgrade`/`downgrade`/`upgrade`). **`_purge_expired_revocations`:** en cada rotación se borran las revocaciones de tokens ya vencidos — no aportan nada (el token falla igual por vencido) y sin eso la tabla crecería sin límite, una fila por cada refresh de cada usuario para siempre.
  **Dos arreglos de deuda que aparecieron acá:** (1) `test_downgrade_removes_every_phase1_table` (T-1.2.3) hacía `downgrade -1`, que al existir una segunda migración ya solo revertía la última y dejaba de probar lo que decía — ahora baja a `base`; (2) `ruff` marcaba 6 errores en los scripts que genera Alembic (su plantilla usa `typing.Union` y líneas largas), así que se agregó `extend-exclude = ["alembic/versions"]` en `pyproject.toml`: es código generado, no propio.
  _Prueba:_ test: con cookie válida → nuevo access; sin cookie → 401; refresh ya rotado → 401. **Verificado con 14 tests y con el ciclo completo contra un servidor real** (cookie jar de `curl`, como un navegador): refresh → `200` con cookie nueva distinta; reusar la vieja → `401`; la nueva sigue sirviendo; sin cookie → `401`. Los tests cubren además: un access token no sirve como refresh, token vencido, token alterado, token firmado con otra clave, usuario suspendido → 403, limpieza efectiva de revocaciones vencidas, **dos sesiones (dos dispositivos) que rotan sin desloguearse entre sí**, y que quemar el refresh no bloquea la cuenta (se puede volver a loguear). _Depende de:_ T-1.4.2

- [x] **T-1.4.4 · [Backend] `POST /api/v1/auth/logout`**
  Revoca el refresh (tabla `revoked_tokens` de `T-1.4.3`) y borra la cookie. **204 siempre, nunca falla**: sin cookie, con una vencida, alterada, de otro tipo o ya quemada, el logout termina bien — si devolviera error, alguien con una cookie rara quedaría sin forma de cerrar sesión. Es idempotente y cierra **solo ese dispositivo**. El `delete_cookie` repite los mismos atributos (`path`, `httponly`, `secure`, `samesite`) que el `set_cookie`: si no coinciden, el navegador no la reconoce como la misma cookie y no la borra.
  **Bug real encontrado probando contra un servidor de verdad (los tests no lo veían):** reusar la cookie ya quemada devolvía **500** en vez de 401. Causa: `rotate_refresh`/`logout` **consultaban** si el `jti` estaba revocado y **después** lo insertaban; con dos usos simultáneos del mismo refresh (dos pestañas, doble click, o un token robado usado en paralelo) los dos pasan la consulta y el segundo choca contra la PK de `revoked_tokens` → `IntegrityError` sin manejar. Justo el caso que la rotación existe para frenar terminaba en error del servidor. Arreglado en ambos métodos (401 en refresh, 204 en logout) y cubierto con dos tests que **simulan la carrera** (`monkeypatch` sobre `session.get`), porque la suite normal usa una sola conexión y ahí el problema no se manifiesta. **Es el tercer caso del mismo patrón en la fase** (registro duplicado, rotación, logout): *consultar y después escribir necesita siempre que la base tenga la última palabra*.
  _Prueba:_ test: tras logout, `refresh` con esa cookie → 401. **Verificado con 13 tests y con el ciclo completo contra un servidor real:** logout → `204` con la cookie borrada (`Max-Age=0`, mismo `Path`); cookie quemada → `401`; logout repetido → `204`; logout sin sesión → `204`; volver a loguear → `200`. Los tests cubren también que el logout no borre la cuenta y que cerrar sesión en un dispositivo no cierre la del otro. _Depende de:_ T-1.4.3

- [x] **T-1.4.5 · [Backend] Rate limiting en auth**
  `slowapi` en `/auth/login`, `/auth/register`, `/auth/password/*` (p. ej. 10/min por IP). `app/core/rate_limit.py` con `AUTH_RATE_LIMIT = "10/minute"`, el `limiter` y un handler propio de `RateLimitExceeded` (slowapi trae su formato, distinto al `{"error": {...}}` de §20.1) que además manda `Retry-After`. **`/auth/password/*` todavía no existe — se aplica en `T-1.9.1`, que ya tiene la nota.**
  **Tres decisiones:**
  1. **La IP tiene que ser la del cliente, no la de Nginx.** En producción la API está detrás de un reverse proxy, así que sin proxy headers *todas* las requests comparten un solo bucket y un único atacante agotaría el límite de todos los usuarios a la vez. Nginx ya manda `X-Forwarded-For` (`T-0.7.3`) y Uvicorn lo usa por su default (`proxy_headers=True`, confiando en 127.0.0.1). **Verificado con la configuración exacta de producción** (sin `--forwarded-allow-ips` explícito, como corre el `systemd`): 12 intentos desde una IP → `401` ×10 y después `429`; otra IP sigue respondiendo `401` normal.
  2. **El límite corta incluso con la contraseña correcta** — si no, quien la adivina en el intento 15 entraría igual y el límite no serviría de nada.
  3. **`/auth/refresh` queda sin límite** a propósito: el front lo llama de forma legítima cada vez que vence el access (cada 15 min), y limitarlo desconectaría a usuarios normales.
  **En tests:** el límite vive en memoria del proceso y todos los tests comparten la misma IP, así que un test con varios logins dejaba a los siguientes en 429 — se agregó una fixture `autouse` en `conftest.py` que resetea el limiter antes y después de cada test.
  _Prueba:_ test: la petición 11 en un minuto → 429 `TOO_MANY_REQUESTS`. **Verificado con 10 tests**: login y registro tienen buckets separados (agotar uno no bloquea el otro), un registro bloqueado no crea el usuario, el 429 sale en formato del proyecto con `Retry-After: 60`, y `/refresh` sigue respondiendo 200 después de 15 llamadas seguidas. _Depende de:_ T-1.4.2

## Tema 1.5 · Autorización (RBAC)

- [x] **T-1.5.1 · [Backend] `api/deps.py` — `get_current_user`**
  Extrae el Bearer, decodifica, carga `User`, valida `ACTIVE`. Lanza 401 si falla. Expone los alias `SessionDep` y `CurrentUser` (`Annotated[...]`) para que los endpoints no repitan `Depends`. **`HTTPBearer(auto_error=False)`**: con el default, un header faltante devuelve el error propio de FastAPI (403, otro formato) en vez del `{"error": {"code": "NOT_AUTHENTICATED"}}` de §20.1.
  **Dos decisiones:**
  1. **Solo acepta tokens `type=access`.** Aceptar un refresh acá saltearía la rotación de un solo uso de `T-1.4.3` y dejaría esa protección sin efecto.
  2. **El `status` se revalida en cada request**: suspender a alguien lo echa al instante en vez de dejarlo operar hasta 15 min más con su access token vigente (403 `FORBIDDEN`).
  **Limpieza:** `SessionDep` estaba definido también en `api/routes/auth.py` (de `T-1.3.2`); ahora vive solo en `deps.py` y `auth.py` lo importa.
  _Prueba:_ endpoint protegido de test: con token válido 200, sin token 401, token expirado 401. **Verificado con 12 tests** sobre un endpoint de prueba creado por fixture (el primero real, `/auth/me`, llega en `T-1.5.3`): token válido identifica al usuario, sin token → 401, header sin el esquema `Bearer` → 401, `Bearer ` vacío → 401, token vencido → 401, token alterado → 401, **refresh usado como access → 401**, token de un usuario borrado → 401, suspendido → 403, y funciona con los tres roles. _Depende de:_ T-1.1.3, T-1.2.4

- [x] **T-1.5.2 · [Backend] `require_role(*roles)`**
  Dependencia que corta con 403 si `user.role` no está en `roles`. Devuelve el usuario (no `None`) para que el endpoint no tenga que pedir `get_current_user` por separado. Alias listos: `AdminUser`, `DeliveryUser`, `LoggedInUser`.
  **Tres decisiones:**
  1. **`require_role()` sin argumentos = "cualquiera con sesión"**, no `CUSTOMER`. Es lo que pide RN-33 / `T-1.11.4`: las pantallas de cliente (carrito, pedidos, perfil) no se atan al rol `CUSTOMER` porque un ADMIN también puede querer pedir comida.
  2. **Sin jerarquía de roles**: ADMIN no entra a los endpoints de DELIVERY por ser admin. Cada permiso se declara explícito; si alguna vez hace falta, se agrega a mano. Evita accesos heredados sin querer.
  3. **401 vs 403 bien separados**, porque el front actúa distinto: 401 ("no sé quién sos") → redirige a login; 403 ("sé quién sos y no te corresponde") → mensaje, sin cerrar la sesión. Confundirlos desloguearía a un cliente que simplemente tocó una URL de admin.
  _Prueba:_ endpoint `require_role(ADMIN)`: admin 200, customer 403. **Verificado con 14 tests** sobre endpoints de prueba creados por fixture: admin entra, CUSTOMER y DELIVERY → 403, DELIVERY entra a lo suyo, **ADMIN no entra a lo de DELIVERY**, los tres roles entran donde se exige solo sesión, un endpoint con dos roles permitidos acepta ambos y rechaza el tercero, sin sesión siempre 401 (nunca 403) en las cuatro variantes, y un ADMIN suspendido no entra. _Depende de:_ T-1.5.1

- [x] **T-1.5.3 · [Backend] `GET /api/v1/auth/me`**
  Devuelve `{id, first_name, last_name, email, phone, role, balance}` del usuario actual. Primer endpoint protegido real del proyecto. Schema `MeOut(UserOut)` con `balance` **en centavos** (§11: el dinero viaja como entero, nunca float). **Un usuario sin fila de saldo (staff) devuelve 0, no error** — `customer_balances` es solo de clientes.
  _Prueba:_ test: con token de cada rol devuelve sus datos. **Verificado con 10 tests y el recorrido completo contra un servidor real**: funcionan los tokens que vienen del registro, del login y de una rotación de refresh; sin token → 401; token inválido → 401; suspendido → 403. Los tests además fijan el contrato: la respuesta trae **exactamente** esos 7 campos (nada sensible) y cada usuario ve solo sus propios datos. _Depende de:_ T-1.5.1

## Tema 1.6 · Perfil

- [x] **T-1.6.1 · [Lógica + Backend] Editar perfil**
  `update_profile(user, changes)` con validación (función de módulo en `services/user_service.py`, no método de una clase `UserService`: ese módulo es lógica pura desde `T-1.1.1` y no hay estado que justificar una clase). `PATCH /api/v1/users/me/profile`, con router nuevo `api/routes/users.py`. Devuelve `MeOut` (lo mismo que `/auth/me`) para que el front refresque su estado sin una segunda llamada.
  **Tres decisiones:**
  1. **Semántica real de PATCH**: se aplica solo lo que el cliente mandó (`model_dump(exclude_unset=True)`), y se distingue **campo ausente** (no se toca) de **`phone: null`** (lo borra a propósito). Sin esa distinción, editar solo el nombre borraría el teléfono — el error clásico de este endpoint.
  2. **`extra="forbid"` en `ProfileUpdateIn`**: mandar `email`, `role` o `password` devuelve `422` en vez de ignorarse en silencio. Ignorarlo dejaría al front mostrando "guardado" mientras el email sigue igual. Cada uno necesita su propio flujo: el email requiere verificar el nuevo, el rol lo cambia un admin (`T-1.7.2`).
  3. La lógica queda **sin dependencia del modelo `User`** (tipada con un `Protocol`), así se testea sin base de datos y la reutiliza `T-1.7.2` cuando el admin edite a otros usuarios.
  **Limpieza:** la construcción de la respuesta de usuario estaba duplicada entre este endpoint y `/auth/me`; ahora vive en `MeOut.from_user()`.
  _Prueba:_ test: cambia teléfono y persiste; email no editable por este endpoint. **Verificado con 33 tests** (10 de lógica pura + 23 de API): los cambios se releen **desde la base** (no se confía en la respuesta), un cambio parcial no borra los otros campos, `phone: null` borra y `"   "` guarda `NULL` y no `""`, la respuesta es **idéntica** a la de `/auth/me`, email/rol/contraseña → 422, nombre en blanco → 422 por campo, sin sesión → 401, suspendido → 403, staff también puede editarse (con `balance: 0`), y **editar el propio perfil no toca el de otro usuario**. _Depende de:_ T-1.5.1

## Tema 1.7 · Gestión de usuarios por admin

- [x] **T-1.7.1 · [Lógica + Backend] Crear ADMIN / DELIVERY**
  `UserAdminService.create_staff(role, datos)` (sin auto-login; la contraseña la define el admin y se valida con la misma política del registro). `POST /api/v1/users` (`require_role(ADMIN)`). Para DELIVERY crea también `UserProfile` con `vehicle_type`, `capacity`. Se agrega el enum `VehicleType` (`moto/bici/auto/a_pie`), que existía como `CHECK` en §6.1 pero no en el catálogo de §7 — se usa para validar en el borde; la columna sigue siendo `String` con su `CHECK`, así no hace falta migración.
  **Decisiones:**
  1. **No se pueden crear CUSTOMER acá** (`role` es un `Literal[ADMIN, DELIVERY]`): los clientes se registran solos y crearlos por esta vía los dejaría **sin carrito ni saldo**, o sea clientes a medias.
  2. **El DELIVERY nuevo arranca en `NO_DISPONIBLE`**: si arrancara disponible, el admin podría asignarle pedidos antes de que empiece el turno o antes de que la persona sepa que tiene cuenta.
  3. **Validación cruzada por rol**: DELIVERY **exige** `vehicle_type` (RF-DLV-01 lista el transporte entre sus datos y marca solo la capacidad como opcional) y ADMIN **rechaza** `vehicle_type`/`capacity`, para no guardar datos sin sentido.
  4. **Sin auto-login ni tokens en la respuesta**: el admin crea la cuenta y pasa las credenciales; la sesión la abre la persona.
  **Dependencia circular encontrada al implementarlo:** poner la clase en `services/user_service.py` cerraba un ciclo — `UserRepository` importa las reglas puras de ese módulo, así que el módulo no puede importar el repositorio (los repositorios están **debajo** de los servicios). Se resolvió con un módulo nuevo, `services/user_admin_service.py` (`UserAdminService`), que además es el lugar natural para los cambios de rol/estado de `T-1.7.2`. Se prefirió eso antes que forzar el nombre `UserService.create_staff` del roadmap.
  _Prueba:_ test: admin crea un delivery; customer intentándolo → 403. **Verificado con 25 tests**: el repartidor creado **se loguea de verdad**, contraseña hasheada y nunca en la respuesta, staff sin carrito ni saldo, provider `local` y estado `ACTIVE`, CUSTOMER y DELIVERY → 403 sin crear nada, `role=CUSTOMER` → 422, vehículo faltante o inválido → 422, ADMIN con datos de reparto → 422, capacidad 0 o negativa → 422 y opcional cuando se omite, email duplicado → 409 (también si el email ya es de un cliente, y con otras mayúsculas), y email normalizado. _Depende de:_ T-1.5.2

- [x] **T-1.7.2 · [Backend] Listar y editar usuarios (admin)**
  `GET /api/v1/users?role=&page=` (respuesta paginada `{items, page, page_size, total}` de §11) y `PATCH /api/v1/users/{id}` (rol, `status`). Auditar cambios de rol/estado en `audit_log`: se crea el modelo `AuditLog` según §6.10 + migración `603c07c0f910` (probada `upgrade`/`downgrade`/`upgrade`), con `actor_id`, `action`, `entity_type`, `entity_id`, `data` (JSON before/after), `ip` y `created_at`. El `actor_id` **no** borra en cascada: si algún día se borra un usuario, su rastro tiene que sobrevivir, que es justamente el sentido de auditar.
  **Cuatro decisiones:**
  1. **Un admin no puede cambiar su propio rol ni su propio estado** (403). Suspenderse o bajarse de rol lo deja afuera en el acto y sin forma de revertirlo desde la app — habría que entrar al servidor a mano. A otros admins sí los puede editar.
  2. **No se audita un PATCH que no cambió nada**: el log se llenaría de ruido y los cambios reales quedarían escondidos. Se compara valor por valor antes de registrar.
  3. **Pasar a `CUSTOMER` crea carrito y saldo si faltan** (`_ensure_customer_records`): si no, quedaría un cliente a medias sin poder pedir nada — el mismo problema que evita el `Literal` de `T-1.7.1`.
  4. **`page_size` topeado en 100** (`Query(ge=1, le=100)`): sin tope, `?page_size=999999` devolvería la tabla entera de usuarios en una sola respuesta.
  _Prueba:_ test: listado filtra por rol; suspender un usuario le impide loguearse. **Verificado con 34 tests**: forma paginada exacta, filtro por rol, paginado con `total` global, página vacía más allá de la última, sin hashes en la respuesta, params inválidos → 422, CUSTOMER → 403 y sin sesión → 401; **suspender impide loguearse de verdad** (probado con el login real) y reactivar vuelve a permitirlo, rol y estado se pueden cambiar juntos, PATCH vacío no cambia nada, autoedición → 403 pero otro admin sí, usuario inexistente → 404, campos prohibidos (`email`, `first_name`, `password`) → 422; y en auditoría: se registra `user.update` con actor y before/after, cada cambio suma su entrada, **un cambio nulo no deja entrada** y **un intento rechazado tampoco**. _Depende de:_ T-1.7.1

## Tema 1.8 · Login con Google

- [x] **T-1.8.1 · [Backend] Cliente OAuth con Authlib**
  Registrar el proveedor Google (OIDC) con `GOOGLE_CLIENT_ID/SECRET/REDIRECT_URI`. `GET /api/v1/auth/google/login` → redirección con `state` + PKCE. `app/core/oauth.py` registra el cliente y expone `google_is_configured()`.
  **Decisiones:**
  1. **Endpoints de Google explícitos** en vez de su documento de descubrimiento (`server_metadata_url`): ni el arranque ni el primer login dependen de una llamada extra a Google, y **los tests corren sin red ni credenciales reales**.
  2. **Sesión firmada propia para el `state` y el PKCE** (`SessionMiddleware`, cookie `mc_oauth`, 10 min, `same_site="lax"` fijo — **no** `COOKIE_SAMESITE`): la vuelta desde Google es una navegación de primer nivel hacia la propia API, donde `lax` alcanza. Agrega la dependencia `itsdangerous` (la exige `SessionMiddleware`).
  3. **Sin credenciales responde `503 SERVICE_UNAVAILABLE`** con un mensaje que manda al login normal, en vez de fallar con un error interno — es exactamente el estado actual de producción. Se agrega `ServiceUnavailableError` a `core/errors.py` (extensión de `T-0.2.3`; §20 no tenía 503).
  _Prueba:_ el endpoint redirige a `accounts.google.com` con los params correctos. **Verificado con 9 tests**: destino `accounts.google.com`, `response_type=code` con nuestro `client_id` y `redirect_uri`, scopes `openid email profile`, `state` presente, `code_challenge_method=S256` con su desafío, dos logins generan `state` y desafío distintos, la cookie es `httponly` + `samesite=lax`, no requiere sesión previa, y sin credenciales → 503 (**confirmado también contra un servidor real**, con el resto de la API sana).
  > **⚠️ Pendiente del usuario (no bloquea el resto del proyecto):** crear las credenciales en Google Cloud (proyecto, pantalla de consentimiento, `Client ID` + `Client Secret` y la URI de retorno) y cargarlas en el `.env` del VPS. Son de su cuenta de Google. Decisión del 2026-09-23: **se deja para más adelante** y se sigue avanzando; hasta entonces el botón de Google responde 503 con mensaje claro y el login local funciona normal. _Depende de:_ T-0.2.1

- [~] **T-1.8.2 · [Lógica + Backend] Callback y vinculación**
  `GET /auth/google/callback`: valida `id_token`, obtiene `sub`/`email`/nombre. `AuthService.login_with_google`: si existe provider→login; si existe email→vincula; si no→crea CUSTOMER (`password_hash=NULL`) + cart + balance. Emite tokens y redirige al front.
  **Decisiones:**
  1. **Se rechaza un email que Google no confirmó** (`email_verified`): vincular con un email sin confirmar permitiría reclamar la cuenta de otra persona con solo declarar su dirección.
  2. **La identidad es el `sub` de Google, no el email**: si la persona cambia su email en Google sigue siendo la misma cuenta, sin duplicarse.
  3. **El access token no viaja en la URL** (quedaría en el historial, en los logs y en el `Referer`): el callback deja la cookie de refresh y redirige al front, que pide el access con `/auth/refresh` al cargar — lo que ya hace `bootstrapSession()` (T-0.4.6).
  4. **Los errores vuelven al front con un aviso**, no a un JSON de error: acá hay un navegador, no un cliente de API. `?auth_error=google` (intercambio fallido, `state` inválido o cancelación), `google_email_unverified` y `account_not_active`. **Para `T-1.11.1`:** la pantalla de login tiene que leer ese parámetro y mostrar el mensaje correspondiente.
  _Prueba:_ tests con `id_token` mockeado: los tres caminos (nuevo, vincula, login). **Verificado con 19 tests**: los tres caminos, vinculación sin duplicar cuenta ni provider, la contraseña local sigue funcionando después de vincular, reconoce la cuenta aunque cambie el email en Google, email normalizado, funciona sin `given_name`/`family_name`, el token no aparece en la URL, y ningún error (intercambio fallido, email sin verificar, claims faltantes, cuenta suspendida —también dando la vuelta por Google—) deja usuarios a medias.
  > **Queda en `[~]` a pedido del usuario (2026-09-23):** el código está completo y cubierto por tests, pero **la validación real depende de las credenciales de Google** (ver `T-1.8.1`), que quedaron en suspenso. Se cierra cuando se carguen y se pruebe el login con una cuenta real. _Depende de:_ T-1.8.1, T-1.3.1

## Tema 1.9 · Recuperación de contraseña

- [~] **T-1.9.1 · [Lógica + Backend] Solicitar y resetear**
  `POST /auth/password/forgot` (token firmado de 30 min, `PASSWORD_RESET_MINUTES`) y `POST /auth/password/reset` (token + nueva contraseña). Respuesta **siempre** 200 y con el mismo cuerpo en `forgot`, exista o no el email. Rate limiting de `T-1.4.5` aplicado en los dos.
  **Decisiones:**
  1. **El link muere si la contraseña ya cambió.** El token lleva una huella (`pwd`) del `password_hash` vigente al emitirlo; si no coincide, se rechaza. Así un link viejo (un mail reenviado, por ejemplo) no sirve para volver a cambiar la contraseña durante sus 30 minutos, y pedir un link nuevo invalida los anteriores en cuanto se usa uno.
  2. **Un solo uso**, reutilizando la tabla `revoked_tokens` de `T-1.4.3`. Por eso `revoke_refresh` se renombró a **`revoke_token`**: ya no es solo de refresh (refresh rotado, logout y link de recuperación guardan su `jti` en la misma tabla).
  3. **Una cuenta sin contraseña (solo Google) puede fijarse una por acá** y queda con los dos métodos de ingreso — es el camino que la nota de `T-1.8.2` daba por hecho.
  4. Un **reseteo rechazado no quema el link** (contraseña débil → 422), así el usuario reintenta con el mismo mail.
  _Prueba:_ test: flujo completo cambia la contraseña; token vencido → 400 (se implementó **401**, coherente con `NOT_AUTHENTICATED` de §20 y con el resto de los tokens del proyecto). **Verificado con 24 tests**: respuesta idéntica para email conocido y desconocido, no se genera link para email inexistente ni para cuenta suspendida, la contraseña nueva funciona y la vieja deja de funcionar, hash real en base, un solo uso, link viejo muerto tras el cambio, cuenta Google-only pasa a tener contraseña y ambos providers, token basura / vencido / firmado con otra clave / un access token → 401, suspendido → 401, usuario borrado → 401, contraseña débil → 422 sin quemar el link y sin tocar la vieja, y ambos endpoints con límite de intentos.
  > **Pendiente de infraestructura (no bloquea la fase):** el stack **no tiene servicio de mail**, así que el link se escribe en el log del servidor (`journalctl -u morficenter-api`) en lugar de enviarse por email. Para producción real hace falta elegir y conectar un proveedor de envío — queda anotado como tarea de infraestructura a definir. Por eso la tarea queda en `[~]`: funciona de punta a punta, pero el usuario final todavía no recibe el mail. _Depende de:_ T-1.1.2, T-1.1.3

## Tema 1.10 · Seed y usuarios de prueba

- [x] **T-1.10.1 · [Backend + Docs] Seed de usuarios base**
  `db/seed.py` crea (idempotente) admin, cliente y delivery de prueba. Credenciales registradas en `documentacion/Usuarios.md`. El cliente se crea con `AuthService.register` (carrito + saldo + provider local) y el staff con `UserAdminService.create_staff`.
  **Dos decisiones de seguridad:**
  1. **Los usuarios de prueba NO se crean en producción** (`seed_test_users` corta si `APP_ENV=production` y avisa por log). Sus contraseñas están documentadas en un repositorio **público**: crearlas en el servidor real sería dejar un admin con contraseña conocida por cualquiera. El deploy automático **no** corre el seed (solo `alembic upgrade head`), así que no pueden aparecer ahí por accidente.
  2. **`seed_admin_from_env`** crea el primer ADMIN real desde `SEED_ADMIN_EMAIL`/`SEED_ADMIN_PASSWORD` (variables del `.env` del servidor, nunca en el repo). Resuelve un círculo real: `POST /users` exige ya ser admin, así que sin esto producción no tendría forma de crear su primer admin sin tocar la base a mano. Es idempotente y sí funciona en producción.
  **Bug de infraestructura de tests encontrado acá:** un test de `caplog` fallaba solo al correr la suite completa. Causa: `alembic/env.py` llamaba `fileConfig(...)` con su default `disable_existing_loggers=True`, así que correr las migraciones (en `test_migrations.py`, alfabéticamente anterior) **apagaba los loggers ya creados** y los tests posteriores dejaban de capturar logs. Arreglado con `disable_existing_loggers=False`, que además es lo correcto de por sí: correr una migración no debería silenciar los logs de la app.
  _Prueba:_ `python -m app.db.seed` deja los 3 usuarios; correr dos veces no duplica. **Verificado con 19 tests y corriendo el comando de verdad dos veces** (segunda corrida sin cambios), más el login real de los tres usuarios contra un servidor (`200` con `CUSTOMER`/`ADMIN`/`DELIVERY`). Los tests cubren: roles correctos, **las contraseñas documentadas realmente funcionan** (si el seed y `Usuarios.md` se desincronizan, nadie puede entrar), el cliente tiene carrito y saldo y el staff no, el repartidor tiene su perfil en moto y `NO_DISPONIBLE`, todos `ACTIVE` con provider local, en producción no se crea ninguno (y avisa), y el admin por variables de entorno se crea, es idempotente, funciona en producción y puede autenticarse. _Depende de:_ T-1.3.1, T-1.7.1

## Tema 1.11 · Frontend de autenticación

- [x] **T-1.11.1 · [Frontend] `pages/auth/login.html` + `assets/js/pages/login.js`**
  Formulario (email, password) con estilo Artesanal · Cocina de Olla (inputs/labels/errores de la skill), botón "Iniciar sesión" y botón "Continuar con Google". Al enviar: `auth.login()` → si OK, redirige según rol (CUSTOMER→`/index.html`, ADMIN→`/pages/admin/dashboard.html`, DELIVERY→`/pages/delivery/inicio.html`). Muestra errores del backend.
  **Decisiones:**
  1. **Pantalla enfocada**: sin header con carrito ni nav — solo la marca, que enlaza al home. En escritorio el panel queda **centrado y acotado** (`max-w-[480px]`), porque §16.2 prohíbe la card suelta estirada a todo el ancho.
  2. **`.blob` no va en los botones anchos.** Sus radios son porcentuales, así que en un elemento ancho y bajo se deforma en una elipse (se vio en la captura del navegador); en el mockup solo aparece en elementos compactos o cuadrados. Los botones de formulario usan `rounded-2xl` con `border-2`, y `.blob` queda para la marca y las formas decorativas.
  3. **Destino por rol en un solo lugar** (`HOME_BY_ROLE`): CUSTOMER → `/index.html`. **ADMIN → `/pages/admin/usuarios.html`** y **DELIVERY → `/index.html`**, en vez de los `dashboard.html`/`delivery/inicio.html` del texto original: esas pantallas no existen todavía (la de admin llega en `T-1.11.6`, la del repartidor en Fase 14) y mandar ahí sería un 404. Actualizar cuando existan.
  4. **`next` solo acepta rutas internas** (`/...` y no `//...`): un `next` con URL externa convertiría el login en un salto a cualquier sitio, que es el truco clásico para hacer phishing con un link que parece nuestro.
  5. **El botón de Google consulta antes de navegar**: el endpoint redirige (necesita navegación real), pero sin credenciales responde 503 y navegar mostraría un JSON crudo. Se consulta primero y el aviso se muestra dentro de la pantalla.
  6. **Aviso fijo sobre Google**: como el backend no puede decir "esta cuenta entra con Google" sin filtrar qué emails existen (`T-1.4.1`), el texto está en la pantalla.
  **Cambios de apoyo:** `assets/js/config.js` centraliza la URL de la API (antes iba inline en cada página: cambiar el backend habría obligado a editar todas) e `index.html` pasa a usarlo; y en el backend, los errores de Google ahora redirigen a `/pages/auth/login.html?auth_error=...` en vez de al home, que es la pantalla que sabe mostrarlos.
  _Prueba:_ el usuario loguea con cada usuario de prueba y cae en la pantalla correcta; credenciales malas muestran el error. **Verificado en un navegador real (Chromium vía Playwright)**, a 390px y a 1440px: sin errores de consola, sin scroll horizontal, los **tres usuarios de prueba loguean y caen en su pantalla** dejando la cookie de sesión, credenciales incorrectas muestran "Email o contraseña incorrectos" sin salir de la página y con el botón reactivado, `?auth_error=` pinta el aviso correcto, y el botón de Google avisa dentro de la pantalla. _Depende de:_ T-1.4.2, T-0.4.6

- [x] **T-1.11.2 · [Frontend] `pages/auth/registro.html` + js**
  Formulario (nombre, apellido, email, teléfono, contraseña + repetir) con validación en vivo. Al registrar: alta + login automático + redirección al home. `assets/js/auth.js` gana `register()` (mismo patrón que `login()`, ya devuelve tokens del 201). Mismo lenguaje visual que `login.html` (`T-1.11.1`): fondo `bg-kraft`, panel acotado, botones `rounded-2xl`.
  **Decisiones:**
  1. **Validación en vivo espeja las reglas del backend** (`is_valid_name`, `is_valid_email`, `validate_password` de `app/services/user_service.py`) para que el error aparezca al tipear, no recién tras un viaje al servidor — pero la validación real sigue siendo la del backend; esto es solo UX. Se activa recién después de que el campo perdió el foco una vez (`blur`), no en el primer caracter, para no mostrar "Requerido." mientras el usuario todavía está escribiendo.
  2. **La repetición de contraseña se revalida sola** si la contraseña principal cambia después de haber tocado el segundo campo — si no, "coinciden" podía quedar desactualizado hasta el submit.
  3. **Los errores del servidor van al campo que corresponde**, no a un cartel genérico: un email duplicado (`409 CONFLICT`) se muestra bajo el campo email con el mensaje real del backend, y cada error de `422 VALIDATION_ERROR` se ubica bajo su campo por nombre; solo lo que no tiene campo asociado cae en el cartel general.
  _Prueba:_ alta de un cliente nuevo entra directo al home logueado; email repetido muestra el mensaje. **Verificado en un navegador real (Chromium vía Playwright)**, a 390px y 1440px: sin errores de consola ni scroll horizontal; validación en vivo completa (nombre vacío, email con formato inválido y su corrección en tiempo real sin submit, contraseña débil, contraseñas que no coinciden y su corrección); **alta real que redirige al home ya logueado** dejando la cookie de sesión; y email repetido que muestra "Ya existe una cuenta registrada con ese email." bajo el campo, sin navegar, con el botón reactivado. _Depende de:_ T-1.3.2

- [x] **T-1.11.3 · [Frontend] `pages/auth/recuperar.html` + js**
  Paso 1: pedir email. Paso 2 (con `?token=`): nueva contraseña. Mensajes neutros. `assets/js/auth.js` gana `requestPasswordReset()`/`resetPassword()`. Se extrajo `assets/js/validators.js` (email/nombre/contraseña) para no duplicar las reglas entre `registro.js` y `recuperar.js` — `registro.js` se actualizó para usarlo en vez de su copia local.
  **Decisiones:**
  1. **El mensaje del paso 1 es siempre el mismo**, exista o no el email — es lo que ya hace el backend (`T-1.9.1`); el front solo lo muestra tal cual, sin agregar nada que pudiera distinguir un caso del otro.
  2. **Un link inválido o ya usado no intenta explicarse**: como no hay forma de "arreglarlo" desde esa misma pantalla, el único camino que se ofrece es pedir uno nuevo (vuelve al paso 1).
  3. **Sin auto-login tras cambiar la contraseña** (el backend no emite tokens ahí): se muestra el éxito y un botón a login, en vez de simular una sesión que el backend no abrió.
  **Bug encontrado por la propia prueba en navegador:** el paso 1 (`data-step="request"`) no tenía `hidden` por defecto en el HTML — confiaba en que el JS lo mostrara, pero con `?token=` en la URL nunca se llama a esa función, así que **los dos pasos quedaban visibles a la vez**. Se detectó con la aserción "paso 1 oculto" fallando en la prueba automatizada, no a simple vista. Corregido agregando `hidden` por defecto.
  _Prueba:_ con el token que aparece en consola (dev) se completa el cambio y se puede loguear. **Verificado en un navegador real (Chromium vía Playwright), extrayendo el token real del log del servidor** (así se genera hoy, sin servicio de mail — nota de `T-1.9.1`): paso 1 visible por defecto y paso 2 oculto (y viceversa con `?token=`); el mensaje es **idéntico** para un email real y uno inexistente; validación en vivo de la contraseña nueva y de que coincida; tras cambiarla, **el login funciona con la contraseña nueva de verdad**; y reusar el mismo link ya gastado muestra el aviso con el link para pedir uno nuevo. _Depende de:_ T-1.9.1

- [x] **T-1.11.4 · [Frontend] Sesión, guardas por rol y logout**
  `auth.js` ya define el mecanismo (implementado desde T-0.4.6); acá se **aplica**, con dos patrones distintos según la pantalla (RF-USR-11/12 y RN-33 — **navegar el catálogo es público, actuar requiere sesión**):
  - **Página pública**: `bootstrapSession()` al cargar (sin redirigir), solo para saludar. Aplicado a `index.html`, la única página pública que existe hoy.
  - **Página exclusiva de un rol**: `await requireRole(...)` al cargar, con el mismo comportamiento ya construido en `T-0.4.6` (`next` para volver tras loguear, `requireRole()` sin argumento = cualquier logueado).
  Header: widget de sesión (nombre + "Cerrar sesión", o "Ingresar") agregado a `partials/header.html`, **sin ocultar el resto del header** — solo en escritorio (`lg:flex`, mismo corte que `top-nav`); en mobile el tab "Cuenta" del `bottom-nav` ya cumple ese rol, y agregar el widget ahí apretaría un header angosto. `auth.js` gana `renderSessionUI(user)` (la pinta) y un listener delegado para `[data-session-logout]` (queda conectado en cualquier página que traiga el header, sin cablearlo a mano); `requireRole()` la llama sola al resolver.
  > **Alcance real de esta tarea en este punto del proyecto:** de las páginas que el ítem menciona (`carrito`, `direccion`, `pago`, `pedidos`, `seguimiento`, `perfil`, `admin/*`, `delivery/*`), **ninguna existe todavía** — llegan en `T-1.11.5`/`T-1.11.6` y fases posteriores. No se puede "aplicar una guarda" a una página que no está construida. Lo que sí se deja armado y probado es el **mecanismo reutilizable** (`requireRole()` + el widget de sesión), para que cada página nueva solo tenga que llamarlo — que es exactamente lo que hará `T-1.11.5` al construir `perfil.html`. Tampoco hay todavía ninguna acción real gatillada desde una página pública (los botones "+" del menú son decorativos hasta la Fase 6): esa regla se aplica cuando `carrito` conecte esos clics de verdad. La infraestructura (el mecanismo reutilizable) está completa y verificada; su cobertura sobre "todas las páginas" se completa sola a medida que cada página nueva llama a `requireRole()` — ya ocurrió en `T-1.11.5` y `T-1.11.6`.
  _Prueba:_ entrar a `carrito.html`/`perfil.html`/una página admin sin sesión redirige a login y, tras loguear, vuelve a esa misma pantalla; con sesión de cliente a una página admin también redirige; logout limpia y vuelve al inicio; la home y el menú se ven completos sin sesión. **Verificado en un navegador real (Chromium vía Playwright) lo que sí existe hoy:** sin sesión, escritorio muestra "Ingresar" y el resto del header (logo, nav, carrito) sigue intacto; en mobile el widget no ocupa lugar y el tab "Cuenta" del bottom-nav sigue ahí; tras loguear como el cliente de prueba, el home muestra "Hola, Cliente" y "Cerrar sesión"; al hacer clic en "Cerrar sesión" vuelve a la home sin sesión, la cookie de sesión desaparece, y el header vuelve a mostrar "Ingresar". La redirección con `next` y el corte por rol ya estaban cubiertos por los tests de `T-0.4.6`/backend; acá solo se confirmó que el widget nuevo no los rompió. _Depende de:_ T-1.5.3, T-1.4.4

- [x] **T-1.11.5 · [Frontend] `pages/cliente/perfil.html` + js** 🔒 requiere sesión
  Ver y editar nombre/teléfono. Mostrar email (no editable) y rol. Placeholder de "Saldo a favor" y "Direcciones" (se completan en Fases 12 y 7). Gateada con `requireRole()` (T-1.11.4): sin sesión, redirige a login con retorno a `perfil.html`.
  **Decisiones:**
  1. **"Saldo a favor" no es un placeholder de mentira**: `/auth/me` ya devuelve el saldo real (persistido, hoy $0 para todos), así que se muestra ese valor de verdad con `formatMoney`. Lo que falta para Fase 12 es *usarlo* al pagar, no el dato en sí — inventar un cartel "próximamente" habría escondido información real ya disponible. "Direcciones" sí es placeholder completo: esa tabla no existe hasta Fase 7.
  2. **Reutiliza `requireRole()` sin argumento** (cualquier rol logueado, no solo `CUSTOMER`): un admin o un repartidor entrando a su propio perfil también deben poder editarlo.
  3. **Sin `cart-bar`**: esa barra muestra un resumen de carrito todavía **hardcodeado** (T-0.4.4, sin fetch real hasta Fase 6); replicarla en una página nueva de verdad habría mostrado "3 cosas · $31.800" inventados, no un dato real.
  **Bug real encontrado al construir la segunda página del sitio:** la pestaña "activa" del menú (arriba en escritorio, abajo en mobile) estaba **escrita a mano en el HTML** de `top-nav.html`/`bottom-nav.html`, siempre marcando "Inicio" — invisible mientras solo existía `index.html`, pero ya incorrecto con `perfil.html` (marcaría "Inicio" estando en "Mi cuenta"). Se corrigió de raíz: los partials arrancan neutros y `ui.js#injectPartials` calcula sola qué pestaña resaltar comparando el `href` contra `location.pathname`, para **cualquier página futura** sin que cada una tenga que acordarse de hacerlo.
  _Prueba:_ el cliente cambia su teléfono y al recargar persiste; entrar sin sesión redirige a login. **Verificado en un navegador real (Chromium vía Playwright):** sin sesión redirige a login con `next=/pages/cliente/perfil.html` y, tras loguear, vuelve ahí; los datos precargados son los reales (nombre, email, rol traducido, saldo); validación en vivo de nombre vacío; **cambiar el teléfono y recargar la página conserva el valor nuevo** (persistencia real, no solo en memoria); un admin también puede entrar y editar su perfil; y el menú resalta "Mi cuenta"/"Cuenta" en esta página y vuelve a resaltar "Inicio" al volver al home. _Depende de:_ T-1.6.1, T-1.11.4

- [x] **T-1.11.6 · [Frontend] `pages/admin/usuarios.html` + js**
  Tabla de usuarios con filtro por rol, alta de ADMIN/DELIVERY (formulario), y acciones de suspender/activar y cambiar rol. Layout de escritorio (tabla densa, no cards estiradas). Header propio (no el `header.html` de cliente): sin carrito ni countdown, que no aplican en un panel de administración — solo logo + `renderSessionUI`/logout, reutilizando el mismo mecanismo de `T-1.11.4` sin el partial completo.
  **Bug real de backend encontrado al construir la pantalla:** `UserOut` (usado por `GET /users`, entre otros) no incluía `status` — sin eso, el panel no podía saber si ofrecer "Suspender" o "Reactivar" para cada fila. Se agregó `status: UserStatus` a `UserOut` (no a un schema aparte: no es un dato sensible, y ya se muestra sin problema en el propio `/auth/me` de cada usuario). Actualiza el contrato de `TokenOut.user` y `MeOut` también, sin romper nada — se ajustó el test que fijaba el conjunto exacto de campos de `/auth/me` y se agregó uno nuevo que confirma que el listado trae el estado correcto de cada usuario.
  **Bug real de frontend, más interesante, encontrado recién al probarlo en un navegador de verdad:** crear un usuario (o cambiarle el rol/estado) y volver a pedirle la lista completa al servidor **no garantiza ver el cambio recién hecho** — en esta máquina de desarrollo, esa segunda lectura a veces llega antes de que el propio servidor termine de asentar la escritura anterior (la misma familia de problema ya documentada en `T-1.4.2`/`T-1.9.1`, exclusiva de este entorno). Como el código no reintentaba, la tabla se quedaba mostrando el dato viejo **indefinidamente**, no unos segundos — hacía falta recargar la página a mano. La solución no fue "esperar más": se eliminó la necesidad de volver a leer después de escribir. Crear/editar un usuario ya devuelve el usuario actualizado en la propia respuesta (`POST`/`PATCH`), así que la tabla se actualiza en memoria con ese dato directamente (`applyUpdatedUser`), sin una segunda ida al servidor. De paso, se agregó `cache: "no-store"` al cliente HTTP central (`api.js`) — no era la causa de este bug (se probó y no lo resolvió), pero es la práctica correcta para cualquier GET de datos dinámicos y autenticados, así que se dejó.
  _Prueba:_ el admin crea un repartidor y aparece en la lista; puede loguear con esas credenciales. **Verificado en un navegador real (Chromium vía Playwright):** sin sesión y con sesión de CUSTOMER, ambos redirigidos a login (esta pantalla es solo ADMIN); la fila del propio admin muestra "(vos)" sin selector de rol ni botón de acción (no puede tocarse a sí mismo, regla ya existente de `T-1.7.2`); alta de un repartidor aparece **al instante** en la tabla (antes del arreglo, esto fallaba de forma consistente) y **ese usuario puede loguearse de verdad** con las credenciales cargadas; suspenderlo desde la tabla le impide loguearse acto seguido (403 real); cambiarle el rol a Cliente se refleja al instante; y el filtro por rol excluye correctamente a quien no corresponde. _Depende de:_ T-1.7.2

- [x] **T-1.11.7 · [Frontend] Home: integrar sesión (mínimo)**
  El `index.html` deja de ser 100% estático solo en lo relativo a sesión: saluda al usuario, muestra el estado de login. **Sigue siendo pública** (nadie es redirigido por no tener sesión); **el resto sigue hardcodeado** hasta sus fases.
  **Ya resuelta como parte de `T-1.11.4`**: el widget de sesión del header (nombre + "Cerrar sesión", o "Ingresar") se construyó ahí mismo y se aplicó a `index.html` en esa misma tarea, con `bootstrapSession()` sin redirigir — exactamente el alcance que pide esta tarea. Se re-verificó ahora, al cierre del Tema 1.11, porque el home cambió bastante desde entonces (revamp del home mobile — countdown movido al header — e ícono del sitio, ambos a pedido del usuario fuera de una tarea puntual del roadmap): sigue funcionando igual.
  _Prueba:_ logueado se ve el nombre; sin sesión, botón "Ingresar" — y la pantalla se ve igual de completa en ambos casos. **Reverificado en un navegador real**, escritorio y mobile: sin sesión no redirige y el menú del día se ve completo; con sesión saluda "Hola, Cliente", muestra "Cerrar sesión" y el resto del header (carrito) sigue intacto. _Depende de:_ T-1.11.4

## Cierre de fase

- [x] **T-1.99 · [Docs] `Fase 01 - Usuarios, roles y autenticación.md`**
  Documento final de la fase: qué se hizo, cómo quedó implementado (auth, JWT, RBAC, Google, front), fragmentos de código clave, cómo probar. Actualizar `Usuarios.md`. `Usuarios.md` ya estaba al día desde `T-1.10.1`, sin cambios necesarios. Cierra con 2 tareas explícitamente en pausa a pedido del usuario (`T-1.8.2` sin credenciales de Google, `T-1.9.1` sin servicio de mail) — documentado en el §6 del cierre de fase, no bloquean el resto del proyecto.

---

# FASE 2 · Configuración del sistema y turnos

> El home deja de tener el countdown hardcodeado: pasa a reflejar el turno real configurable por el admin.

## Tema 2.1 · `system_settings`

- [ ] **T-2.1.1 · [Backend] Modelo `SystemSetting` + `SettingsRepository`**
  Tabla clave/valor JSON (§6.10). Repo con `get(key, default)`, `get_typed`, `set(key, value, actor)`.
  _Prueba:_ set/get de una clave JSON compleja (tiers de envío) ida y vuelta. _Depende de:_ T-0.3.2

- [ ] **T-2.1.2 · [Lógica] `SettingsService` con claves conocidas y defaults**
  Enum/constantes de claves (`SHIFT_DEFAULT`, `TIMEZONE`, `COVERAGE_MODE`, ...). `get_shift_default()`, `get_payment_transfer()`, etc., con defaults de `02_Documento_Tecnico.md §6.11`. Validación de forma por clave.
  _Prueba:_ tests: leer una clave sin valor devuelve el default; setear un valor con forma inválida → error. _Depende de:_ T-2.1.1

- [ ] **T-2.1.3 · [Backend] Endpoints de configuración (admin)**
  `GET /api/v1/settings` (todas), `PUT /api/v1/settings/{key}` con validación y `audit_log`.
  _Prueba:_ test: admin actualiza `payment.transfer`; customer → 403. _Depende de:_ T-2.1.2, T-1.5.2

- [ ] **T-2.1.4 · [Backend + Docs] Seed de `system_settings`**
  `db/seed.py` inserta todas las claves con sus defaults.
  _Prueba:_ tras el seed, `GET /settings` devuelve el set completo. _Depende de:_ T-2.1.2

## Tema 2.2 · Turnos

- [ ] **T-2.2.1 · [Backend] Modelo `Shift` + `ShiftRepository`**
  Tabla `shifts` (§6.4). Repo: `get_current()`, `get_by_date_type`, `create_from_default`, `set_status`.
  _Prueba:_ crear un turno y recuperarlo por fecha/tipo. _Depende de:_ T-0.3.2

- [ ] **T-2.2.2 · [Lógica] `ShiftService` — resolución de instantes y estado**
  `resolve_window(shift)` → `(open_dt_utc, close_dt_utc, cancel_deadline_utc)` con `core/timezone`. `current_status(shift, now)` deriva `SCHEDULED/OPEN/CLOSED`. `is_ordering_open(now)`.
  _Prueba:_ tests con distintos "now": antes de apertura, dentro, después del cierre. _Depende de:_ T-2.2.1, T-0.2.5

- [ ] **T-2.2.3 · [Lógica] `ShiftService.ensure_today_shift`**
  Si no existe el turno del día (según `SHIFT_DEFAULT` y `weekdays`), lo crea. Idempotente.
  _Prueba:_ test: primera llamada crea, segunda no duplica; en día no operativo no crea. _Depende de:_ T-2.2.2, T-2.1.2

- [ ] **T-2.2.4 · [Lógica] Transiciones de turno**
  `open()`/`close()` **no son un job**: se resuelven solas al calcular `current_status(shift, now)` (T-2.2.2) — no hay una transición que "correr", el estado siempre se deriva de la hora. Lo que sí necesita una acción explícita es `on_shift_closed(shift)`: el efecto de **una sola vez** al detectar el cierre (congela `product_stock` del turno — se integra en Fase 4; marca pedidos sin validar como críticos — se integra en Fase 11), disparado por el primer request que consulta el turno después de la hora de cierre, con una marca en `shifts` para no repetirlo. `to_production()` sigue siendo una acción manual del admin.
  _Prueba:_ tests: `current_status` antes/durante/después del cierre sin llamar nada más; `on_shift_closed` se aplica una sola vez aunque se detecte en dos requests seguidos; `to_production()` solo lo dispara el admin. _Depende de:_ T-2.2.2

> **Nota:** este roadmap tenía un `Tema 2.3 · Jobs de turno` con un scheduler (`APScheduler`) para abrir/cerrar el turno y expirar reservas de stock por tiempo. Se decidió sacarlo: nada de esto necesita un proceso corriendo en segundo plano — todo se calcula bajo demanda, en el momento en que un request lo pregunta (detalle y motivo en `02_Documento_Tecnico.md` §10). Los antiguos `T-2.3.1`/`T-2.3.2` quedan reemplazados por `T-2.2.4` de arriba; las tareas de otras fases que dependían de ellos se actualizaron para depender de `T-2.2.4` en su lugar.

## Tema 2.4 · Endpoint del turno y front

- [ ] **T-2.4.1 · [Backend] `GET /api/v1/shift/current`**
  Devuelve `{status, service_date, open_time, close_time, now, seconds_to_close, cancel_deadline, prep_eta}`. `now` es la hora del servidor en UTC.
  _Prueba:_ test: turno abierto devuelve `seconds_to_close > 0`; cerrado → `status CLOSED`. _Depende de:_ T-2.2.2

- [ ] **T-2.4.2 · [Backend] `GET /shift` y `PATCH /shift/{id}` y `POST /shift/{id}/transition` (admin)**
  Listar por fecha, ajustar horarios/ventana del turno, forzar `open`/`close`/`to_production`.
  _Prueba:_ test: admin adelanta el `close_time` y `shift/current` lo refleja. _Depende de:_ T-2.2.4, T-1.5.2

- [ ] **T-2.4.3 · [Frontend] `assets/js/countdown.js` + integración en el home**
  El home pide `shift/current`, corrige el desfase con `now`, arranca el contador contra `close_time`. Muestra estado ("Pedidos abiertos" / "Pedidos cerrados"), hora límite y cuenta regresiva reales. Al llegar a 0 cambia a estado cerrado sin recargar.
  _Prueba:_ el admin cambia el `close_time` y el home lo refleja al recargar; el contador corre y llega a cero correctamente. _Depende de:_ T-2.4.1, T-0.4.4

- [ ] **T-2.4.4 · [Frontend] `pages/admin/configuracion.html` (turnos)**
  Formulario para horarios del turno (apertura, cierre, prep_eta, dispatch_eta), ventana de cancelación, días operativos, zona horaria. Guarda vía `settings` / `shift`.
  _Prueba:_ el admin edita los horarios, guarda, y el cambio impacta en `shift/current`. _Depende de:_ T-2.4.2, T-2.1.3

## Cierre de fase

- [ ] **T-2.99 · [Docs] `Fase 02 - Configuración y turnos.md`**

---

# FASE 3 · Catálogo: categorías y productos

> El menú del home y la página de menú dejan de estar hardcodeados: se cargan del backend. El admin gestiona el catálogo.

## Tema 3.1 · Categorías

- [ ] **T-3.1.1 · [Lógica] Reglas de categoría**
  `CatalogService`: nombre requerido, `slug` autogenerado y único, `sort_order`, activación/desactivación. Reordenamiento por lista de ids.
  _Prueba:_ tests: slug se deriva y colisiones se resuelven; reordenar cambia `sort_order`. _Depende de:_ T-0.2.2

- [ ] **T-3.1.2 · [Backend] Modelo `Category` + repo + migración**
  §6.3. Repo: `list_active`, `list_all`, `create`, `update`, `reorder`.
  _Prueba:_ CRUD contra DB de test. _Depende de:_ T-3.1.1

- [ ] **T-3.1.3 · [Backend] Endpoints de categorías**
  `GET /catalog/categories` (público: activas; `?all=true` admin: todas), `POST`, `PATCH /{id}`, `POST /reorder` (admin).
  _Prueba:_ test: público no ve inactivas; admin crea y reordena. _Depende de:_ T-3.1.2, T-1.5.2

## Tema 3.2 · Productos

- [ ] **T-3.2.1 · [Lógica] Reglas de producto**
  Nombre, `category_id` válido, `base_price` > 0 (centavos), descripción opcional, activación. `CatalogService.create_product/update_product`.
  _Prueba:_ tests: precio 0 o negativo → error; categoría inexistente → error. _Depende de:_ T-3.1.1

- [ ] **T-3.2.2 · [Backend] Modelos `Product`, `ProductImage` + repo + migración**
  §6.3. Repo: `list_public(category_id?, search?)`, `get`, `create`, `update`, `set_active`.
  _Prueba:_ CRUD; `list_public` excluye inactivos y de categorías inactivas. _Depende de:_ T-3.2.1

- [ ] **T-3.2.3 · [Backend] Endpoints de productos (admin)**
  `POST /catalog/products`, `PATCH /{id}`, `DELETE /{id}` (baja lógica).
  _Prueba:_ test: alta/edición/baja; customer → 403. _Depende de:_ T-3.2.2, T-1.5.2

- [ ] **T-3.2.4 · [Backend] Catálogo público `GET /catalog/products`**
  Devuelve productos activos con `base_price`, `price` (= base por ahora; precio vigente real llega en Fase 5), `price_display`, `category`, imagen principal y `stock_available` (placeholder `null` hasta Fase 4).
  _Prueba:_ test: estructura correcta; filtro por `category_id` y `search`. _Depende de:_ T-3.2.2

- [ ] **T-3.2.5 · [Backend] Carga de imágenes de producto**
  `POST /catalog/products/{id}/images` (multipart, jpg/png/webp, ≤ 4 MB, se guarda en `storage/products/`), `DELETE /catalog/images/{id}`, marcar principal.
  _Prueba:_ test: sube una imagen y aparece como principal; archivo no imagen → 400. _Depende de:_ T-3.2.2, (FileStorage mínimo)

- [ ] **T-3.2.6 · [Backend + Docs] Seed de catálogo demo**
  6 categorías (Principales, Pastas, Empanadas, Pizza, Sándwiches, Acompañamientos) y ~15 productos con precios.
  _Prueba:_ tras el seed, `GET /catalog/products` devuelve el catálogo demo. _Depende de:_ T-3.2.2

## Tema 3.3 · Frontend admin

- [ ] **T-3.3.1 · [Frontend] `pages/admin/categorias.html` + js**
  Lista ordenable (drag o flechas), alta/edición inline, toggle activo. Estilo del sistema.
  _Prueba:_ el admin crea "Woks", la reordena y la desactiva; el cambio persiste. _Depende de:_ T-3.1.3

- [ ] **T-3.3.2 · [Frontend] `pages/admin/productos.html` + js**
  Tabla de productos con filtros (categoría, estado, búsqueda), formulario de alta/edición (nombre, categoría, descripción, precio en pesos → se envía en centavos, imagen), baja lógica. Layout de escritorio aprovechado.
  _Prueba:_ el admin da de alta un producto con imagen y lo ve en el catálogo del cliente. _Depende de:_ T-3.2.3, T-3.2.5

## Tema 3.4 · Frontend cliente

- [ ] **T-3.4.1 · [Frontend] Home: menú real por categorías**
  El bloque "El menú de hoy" y las chips de categoría se cargan de `GET /catalog/categories` y `GET /catalog/products`. Los ítems usan las cards de producto de la skill. Sigue sin carrito funcional (el botón "+" es visual hasta Fase 6).
  _Prueba:_ los productos y categorías del admin aparecen en el home; filtrar por chip funciona. _Depende de:_ T-3.2.4, T-0.4.4

- [ ] **T-3.4.2 · [Frontend] `pages/cliente/menu.html` + `producto.html`**
  Página de menú completa (todas las categorías con scroll/anclas) y detalle de producto (imagen, descripción, precio). Botón "Agregar" visual.
  _Prueba:_ navegar del home al menú y al detalle; datos correctos. _Depende de:_ T-3.2.4

## Cierre de fase

- [ ] **T-3.99 · [Docs] `Fase 03 - Catálogo.md`**

---

# FASE 4 · Stock

> Los productos muestran disponibilidad real y el "sin stock" deja de ser un ítem fijo.

## Tema 4.1 · Modelo y disponibilidad

- [ ] **T-4.1.1 · [Backend] Modelos `ProductStock` y `StockReservation` + repo + migración**
  §6.3. Repo: `get_or_create_for_shift`, `sum_held_active(product_id, now)`, `set_initial`, `add_consumed`, `sub_consumed`.
  _Prueba:_ CRUD y sumas contra DB de test. _Depende de:_ T-3.2.2, T-2.2.1

- [ ] **T-4.1.2 · [Lógica] `StockService.available(product, shift, now)`**
  `available = initial_qty - sum(reservations HELD no vencidas) - consumed_qty`. Nunca negativo.
  _Prueba:_ tests: sin reservas; con reservas vigentes; con reservas vencidas (no restan); con consumido. _Depende de:_ T-4.1.1

## Tema 4.2 · Reservas

- [ ] **T-4.2.1 · [Lógica] `StockService.reserve(order_id, items, shift, now)`**
  Valida `available >= qty` para cada ítem; crea `StockReservation(HELD, expires_at = now + STOCK_RESERVATION_TTL_MIN)`. Si algún ítem no alcanza → `OutOfStockError` con detalle y no crea ninguna.
  _Prueba:_ tests: reserva OK; falta stock en un ítem → nada se reserva. _Depende de:_ T-4.1.2, T-2.1.2

- [ ] **T-4.2.2 · [Lógica] `commit` y `release`**
  `commit(order_id)`: HELD→COMMITTED y `consumed_qty += qty`. `release(order_id)`: HELD|COMMITTED→RELEASED y si estaba COMMITTED `consumed_qty -= qty`.
  _Prueba:_ tests de ambos y de idempotencia (llamar dos veces no rompe). _Depende de:_ T-4.2.1

- [ ] **T-4.2.3 · [Lógica] Liberar reservas vencidas al leer (sin job)**
  `StockService.available()`/`.reserve()` liberan primero las reservas HELD con `expires_at < now` (→ RELEASED) antes de calcular disponibilidad — no hay un proceso aparte corriendo cada 60 s, se resuelve en el momento en que alguien consulta o intenta reservar ese producto. Marca los pedidos afectados (integración de estado en Fase 9) y deja log.
  _Prueba:_ test: crea reserva con `expires_at` en el pasado, llama `available()` del mismo producto, la reserva queda RELEASED y el stock vuelve a estar disponible — sin invocar nada más. _Depende de:_ T-4.2.1

## Tema 4.3 · Integraciones y front

- [ ] **T-4.3.1 · [Backend] `PUT /catalog/products/{id}/stock` (admin)**
  Setea `initial_qty` del `ProductStock` del turno actual.
  _Prueba:_ test: admin fija stock 20 y `available` refleja 20. _Depende de:_ T-4.1.1, T-1.5.2

- [ ] **T-4.3.2 · [Backend] `stock_available` real en el catálogo**
  `GET /catalog/products` completa `stock_available` y `in_stock` (bool) usando `StockService`.
  _Prueba:_ test: producto con stock 0 → `in_stock=false`. _Depende de:_ T-4.1.2, T-3.2.4

- [ ] **T-4.3.3 · [Backend] Congelar stock al cerrar el turno**
  `ShiftService.on_shift_closed()` (T-2.2.4) toma snapshot: fija `initial_qty` del turno = disponible al momento del cierre (o deja el configurado). Se dispara sola, la primera vez que un request detecta el turno cerrado — no hace falta integrarlo a nada aparte.
  _Prueba:_ test: tras cierre, el stock del turno queda fijo. _Depende de:_ T-2.2.4, T-4.1.1

- [ ] **T-4.3.4 · [Frontend] Admin: gestión de stock**
  En `productos.html`, campo/columna de stock del turno con edición rápida; indicador de reservado/consumido/disponible.
  _Prueba:_ el admin cambia el stock y lo ve reflejado; el consumido aparece cuando haya pedidos (Fase 11). _Depende de:_ T-4.3.1

- [ ] **T-4.3.5 · [Frontend] Cliente: estado "sin stock"**
  Las cards de producto usan `in_stock`/`stock_available`: si 0 → estilo "sin stock" de la skill y botón deshabilitado; si es bajo (≤ 5) → leyenda "quedan N".
  _Prueba:_ poner un producto en stock 0 desde el admin y verlo "sin stock" en el home. _Depende de:_ T-4.3.2, T-3.4.1

## Cierre de fase

- [ ] **T-4.99 · [Docs] `Fase 04 - Stock.md`**

---

# FASE 5 · Promociones y Plato del Día

> El home muestra un Plato del Día real y los precios promocionales; el precio se resuelve por vigencia.

## Tema 5.1 · Precio vigente

- [ ] **T-5.1.1 · [Backend] Modelo `Promotion` + repo + migración**
  §6.3 (`type` PROMO/DAILY_SPECIAL, ventana, `weekday`, `priority`, `label`). Repo: `active_for_product(product_id, at)`, `list`, CRUD.
  _Prueba:_ recuperar promos vigentes de un producto para un instante dado. _Depende de:_ T-3.2.2

- [ ] **T-5.1.2 · [Lógica] `PricingService.resolve_unit_price(product, at)`**
  Sin promos vigentes → `base_price`. Con promos → según `promo.tie_breaker` (`lowest_price` por defecto: el menor `promo_price`; `priority`: mayor prioridad). Devuelve `(price, is_promo, promotion_id, label)`.
  _Prueba:_ tests: sin promo; una promo; dos promos simultáneas (elige la menor); fuera de ventana (vuelve a base); `weekday` que no matchea. _Depende de:_ T-5.1.1, T-2.1.2

## Tema 5.2 · Backend de promociones

- [ ] **T-5.2.1 · [Backend] Endpoints de promociones (admin)**
  `GET /promotions?active=`, `POST`, `PATCH /{id}`, `DELETE /{id}`. Sirve tanto PROMO como DAILY_SPECIAL.
  _Prueba:_ test: crear una promo con vigencia futura no afecta el precio actual. _Depende de:_ T-5.1.1, T-1.5.2

- [ ] **T-5.2.2 · [Backend] `GET /promotions/daily-special`**
  Devuelve el/los Plato(s) del Día vigentes (producto, precio base, precio promo, `label`, imagen) para el home.
  _Prueba:_ test: con un DAILY_SPECIAL vigente lo devuelve; sin ninguno → lista vacía. _Depende de:_ T-5.1.2

- [ ] **T-5.2.3 · [Backend] Integrar precio resuelto en el catálogo**
  `GET /catalog/products` usa `PricingService`: `price`, `is_promo`, `promo_label`, `base_price`.
  _Prueba:_ test: un producto con promo vigente muestra `price < base_price` y `is_promo=true`. _Depende de:_ T-5.1.2, T-3.2.4

- [ ] **T-5.2.4 · [Backend + Docs] Seed de una promo y un Plato del Día**
  _Prueba:_ tras el seed, el home tiene Plato del Día y al menos un producto con precio promo. _Depende de:_ T-5.1.1

## Tema 5.3 · Frontend

- [ ] **T-5.3.1 · [Frontend] Admin: `pages/admin/promociones.html` + js**
  Alta/edición de promociones y Platos del Día: producto, tipo, precio promo (pesos), fecha inicio/fin, weekday opcional, `label`, prioridad. Lista con estado vigente/programada/vencida.
  _Prueba:_ el admin crea un Plato del Día para hoy y aparece en el home. _Depende de:_ T-5.2.1

- [ ] **T-5.3.2 · [Frontend] Cliente: bloque Plato del Día + precios promo**
  El home consume `GET /promotions/daily-special` para la card destacada (label gold, precio tachado + `text-clay`) y las cards de producto muestran el precio promo cuando `is_promo`.
  _Prueba:_ cambiar el Plato del Día desde el admin y verlo en el home; un producto en promo muestra ambos precios. _Depende de:_ T-5.2.2, T-5.2.3

## Cierre de fase

- [ ] **T-5.99 · [Docs] `Fase 05 - Promociones y Plato del Día.md`**

---

# FASE 6 · Carrito

> El botón "Agregar" pasa a funcionar. Aparece la página de carrito con el resumen (sin envío ni saldo todavía).

## Tema 6.1 · Lógica y persistencia

- [ ] **T-6.1.1 · [Backend] Modelo `CartItem` + repo + migración**
  §6.5. El `Cart` ya existe (Fase 1). Repo: `get_cart_with_items(user)`, `add_or_increment`, `set_qty`, `remove`, `clear`.
  _Prueba:_ CRUD contra DB de test. _Depende de:_ T-1.2.2, T-3.2.2

- [ ] **T-6.1.2 · [Lógica] `CartService`**
  `add(user, product_id, qty, label_for?)`: valida producto activo, turno abierto (`ShiftService.is_ordering_open`) y `StockService.available >= qty_total`. `set_qty`, `remove`, `clear`. `summary(user)`: ítems con precio vigente (`PricingService`), `subtotal`, `count`.
  _Prueba:_ tests: agregar OK; agregar con turno cerrado → `ShiftClosedError`; superar stock → `OutOfStockError`; subtotal correcto con promo. _Depende de:_ T-6.1.1, T-5.1.2, T-4.1.2, T-2.2.2

## Tema 6.2 · Backend

- [ ] **T-6.2.1 · [Backend] Endpoints de carrito (rol CUSTOMER)**
  `GET /cart`, `POST /cart/items`, `PATCH /cart/items/{id}`, `DELETE /cart/items/{id}`, `DELETE /cart`.
  _Prueba:_ test end-to-end: agregar 2 productos, cambiar cantidad, quitar uno, ver el resumen. _Depende de:_ T-6.1.2, T-1.5.2

## Tema 6.3 · Frontend

- [ ] **T-6.3.1 · [Frontend] Botón "Agregar" funcional + barra de carrito viva**
  En home, menú y detalle (pantallas **públicas**), "Agregar"/"+" llama a `POST /cart/items` y actualiza la barra de carrito (contador y subtotal) y el badge del header. Feedback (toast) y manejo de errores (sin stock, turno cerrado). **Si no hay sesión** (`getUser()` es `null`), el click no llama a la API: redirige a `login.html?next=<pantalla actual>` (RF-USR-12); al loguear, vuelve y puede reintentar.
  _Prueba:_ agregar productos logueado actualiza la barra en vivo; con turno cerrado muestra el aviso; agregar sin sesión redirige a login y, tras loguear, vuelve al menú/producto. _Depende de:_ T-6.2.1, T-0.4.3, T-1.11.4

- [ ] **T-6.3.2 · [Frontend] `pages/cliente/carrito.html` + js** 🔒 requiere sesión
  Lista de ítems con +/− / eliminar, subtotal, y un total provisorio (= subtotal; "envío a calcular" y "saldo" como placeholders hasta Fases 8 y 12). Botón "Continuar" deshabilitado hasta tener dirección (Fase 7). Gateada con `requireRole()`: sin sesión, redirige a login con retorno a `carrito.html`.
  _Prueba:_ modificar cantidades desde el carrito recalcula el subtotal; vaciar el carrito funciona; entrar a `carrito.html` sin sesión redirige a login. _Depende de:_ T-6.2.1, T-1.11.4

## Cierre de fase

- [ ] **T-6.99 · [Docs] `Fase 06 - Carrito.md`**

---

# FASE 7 · Direcciones y cobertura

> El cliente carga direcciones y el sistema le dice si se entrega ahí. El admin configura barrios y radio.

## Tema 7.1 · Direcciones

- [ ] **T-7.1.1 · [Backend] Modelo `Address` + repo + migración**
  §6.2. Repo: `list_by_user`, `get_owned(user, id)`, `create`, `update`, `delete`, `set_default`.
  _Prueba:_ CRUD; `get_owned` de otro usuario → None. _Depende de:_ T-1.2.1

- [ ] **T-7.1.2 · [Backend] Endpoints de direcciones (CUSTOMER)**
  `GET/POST /users/me/addresses`, `PATCH/DELETE /users/me/addresses/{id}`.
  _Prueba:_ test: alta, edición, baja; no se puede tocar la dirección de otro. _Depende de:_ T-7.1.1, T-1.5.2

## Tema 7.2 · Geocodificación y cobertura

- [ ] **T-7.2.1 · [Backend] `services/external/geocoding.py`**
  `GeocodingProvider` (Protocol) + `NominatimProvider` (httpx, User-Agent, timeout, manejo de rate limit y errores) + selección por `GEOCODING_PROVIDER`. Cachea el resultado en `Address.lat/lng/geocoded_at`.
  _Prueba:_ test con httpx mockeado: una dirección conocida devuelve lat/lng; dirección inexistente → `None`. _Depende de:_ T-0.2.1

- [ ] **T-7.2.2 · [Lógica] Haversine + `CoverageService`**
  `haversine(a, b)` en km. `CoverageService.check(address)` según `COVERAGE_MODE` (`neighborhood` / `radius` / `neighborhood_and_radius` / `off`) usando `delivery_zones` y `COVERAGE_ORIGIN`. Devuelve `(ok, distance_km, reason)`.
  _Prueba:_ tests de los 4 modos con direcciones dentro y fuera; `reason` correcto. _Depende de:_ T-7.2.1, T-2.1.2

- [ ] **T-7.2.3 · [Backend] Modelo `DeliveryZone` + repo + endpoints (admin)**
  §6.2. `GET/POST /coverage/zones`, `PATCH/DELETE /coverage/zones/{id}`, `GET/PUT /coverage/config` (`coverage.mode`, `coverage.origin`).
  _Prueba:_ test: admin habilita el barrio "Boedo" y define radio 5 km; customer → 403. _Depende de:_ T-7.2.2, T-1.5.2

- [ ] **T-7.2.4 · [Backend] `POST /coverage/check`**
  Recibe `address_id` o `{address}` o `{lat,lng}`; geocodifica si hace falta; devuelve `{ok, distance_km, reason}` (la cotización de envío se suma en Fase 8).
  _Prueba:_ test: dirección dentro → `ok:true`; fuera de radio → `ok:false, reason:"out_of_radius"`. _Depende de:_ T-7.2.2

- [ ] **T-7.2.5 · [Backend + Docs] Seed de cobertura**
  Origen (coords de Morfi Center demo), 3-4 barrios habilitados, radio 5 km, modo `neighborhood_and_radius`.
  _Prueba:_ tras el seed, `coverage/check` de la dirección demo da `ok:true`. _Depende de:_ T-7.2.3

## Tema 7.3 · Frontend

- [ ] **T-7.3.1 · [Frontend] `pages/cliente/direccion.html` + js** 🔒 requiere sesión
  Lista de direcciones guardadas + alta (calle, número, detalle, barrio, ciudad). Al guardar/seleccionar: `coverage/check` y muestra el resultado ("Entregamos acá · 2,3 km" o el motivo de rechazo). Marcar predeterminada. Gateada con `requireRole()`.
  _Prueba:_ cargar una dirección dentro de cobertura la habilita; una fuera muestra el motivo y no permite continuar; sin sesión redirige a login. _Depende de:_ T-7.1.2, T-7.2.4, T-1.11.4

- [ ] **T-7.3.2 · [Frontend] Carrito: selección de dirección**
  El carrito muestra la dirección elegida (panel oscuro de la skill) con "Cambiar"; el botón "Continuar" se habilita solo si la dirección está dentro de cobertura.
  _Prueba:_ elegir dirección válida habilita "Continuar"; cambiarla a una inválida lo deshabilita. _Depende de:_ T-7.3.1, T-6.3.2

- [ ] **T-7.3.3 · [Frontend] `pages/admin/configuracion.html` (cobertura)**
  Sección para el modo de cobertura, el origen, la lista de barrios (habilitar/deshabilitar) y el radio.
  _Prueba:_ el admin deshabilita un barrio y una dirección de ese barrio pasa a estar fuera de cobertura. _Depende de:_ T-7.2.3

- [ ] **T-7.3.4 · [Frontend] Perfil: sección Direcciones**
  Reusar el componente de direcciones dentro de `perfil.html`.
  _Prueba:_ el cliente administra sus direcciones desde el perfil. _Depende de:_ T-7.3.1

## Cierre de fase

- [ ] **T-7.99 · [Docs] `Fase 07 - Direcciones y cobertura.md`**

---

# FASE 8 · Costos de envío

> El carrito muestra el costo de envío real según la configuración.

- [ ] **T-8.1.1 · [Lógica] `ShippingService.quote(distance_km)`**
  Según `SHIPPING_MODE`: `off`/`free` → 0; `flat` → `SHIPPING_FLAT_AMOUNT`; `by_distance` → primer tier con `distance_km <= max_km`, si ninguno el último. Devuelve centavos.
  _Prueba:_ tests de los 4 modos y de los bordes de los tiers. _Depende de:_ T-2.1.2

- [ ] **T-8.1.2 · [Backend] Config de envío (admin)**
  `GET/PUT /coverage/config` amplía a `shipping.mode`, `shipping.flat_amount`, `shipping.tiers`. Validación de la tabla de tiers (ordenada, montos ≥ 0).
  _Prueba:_ test: guardar tiers desordenados → error; guardar válidos OK. _Depende de:_ T-8.1.1, T-1.5.2

- [ ] **T-8.1.3 · [Backend] Cotización en `coverage/check` y en el resumen del carrito**
  `coverage/check` agrega `shipping_quote` cuando `ok`. `GET /cart` incluye `shipping` si hay dirección válida seleccionada (se guarda la dirección elegida en el carrito o se pasa por query).
  _Prueba:_ test: dirección a 2,3 km → `shipping_quote` = tier correspondiente. _Depende de:_ T-8.1.1, T-7.2.4

- [ ] **T-8.1.4 · [Frontend] Admin: configuración de envío**
  UI para modo de envío y tabla de rangos (agregar/quitar filas). Vista previa del costo para una distancia de ejemplo.
  _Prueba:_ el admin pasa a modo `by_distance` con tres rangos y el carrito refleja el costo. _Depende de:_ T-8.1.2

- [ ] **T-8.1.5 · [Frontend] Carrito: costo de envío y total**
  El carrito muestra subtotal + envío + total. Si el envío está en `off` muestra "Envío bonificado / $0".
  _Prueba:_ el total del carrito = subtotal + envío según la dirección elegida. _Depende de:_ T-8.1.3, T-7.3.2

- [ ] **T-8.99 · [Docs] `Fase 08 - Costos de envío.md`**

---

# FASE 9 · Confirmación del pedido

> El cliente confirma el pedido: se congelan los importes, se reserva el stock y se le muestran los datos de transferencia.

## Tema 9.1 · Modelo y máquina de estados (base)

- [ ] **T-9.1.1 · [Backend] Modelos `Order`, `OrderItem`, `OrderStatusHistory` + repo + migración**
  §6.6. Repo: `create`, `get_owned`, `list_by_user(status?)`, `list_admin(filtros)`, `add_history`, `generate_code`.
  _Prueba:_ crear un pedido con ítems y leer su historial. _Depende de:_ T-3.2.2, T-2.2.1

- [ ] **T-9.1.2 · [Lógica] `OrderStateMachine` (parte 1)**
  Mapa de transiciones + guardas por rol para: `DRAFT→PENDING_PAYMENT`, `PENDING_PAYMENT→CANCELLED` (cliente/admin/sistema), `PENDING_PAYMENT→PAYMENT_APPROVED` (admin, sin comprobante). Toda transición fuera del mapa → `InvalidTransitionError`. Cada transición escribe `OrderStatusHistory`.
  _Prueba:_ tests: transición válida OK y registra historia; inválida lanza error; guarda de rol (customer no puede aprobar). _Depende de:_ T-9.1.1, T-0.2.2

- [ ] **T-9.1.3 · [Lógica] Código de pedido**
  `MC-<AAAA>-<secuencial 6 dígitos>` (`ORDERS_CODE_PREFIX`). Único.
  _Prueba:_ test: dos pedidos consecutivos → códigos distintos y con formato. _Depende de:_ T-9.1.1

## Tema 9.2 · Checkout

- [ ] **T-9.2.1 · [Lógica] `OrderService.confirm(user, address_id, use_balance)`**
  Guardas: turno abierto, dirección propia y dentro de cobertura, stock disponible para todos los ítems. Resuelve precios (`PricingService`) y **congela** `OrderItem.unit_price`/`product_name`. Calcula `subtotal`, `shipping_cost` (`ShippingService`), `balance_applied` (Fase 12; por ahora 0), `total`. Crea `Order` + `OrderItem`, llama `StockService.reserve`, crea `Payment(expected_amount=total)`, transición `DRAFT→PENDING_PAYMENT`, `is_cancelable_at_creation = now <= cancel_deadline`, vacía el carrito.
  _Prueba:_ tests: confirmación feliz (pedido creado, stock reservado, carrito vacío); turno cerrado → `ShiftClosedError`; sin stock → `OutOfStockError` y nada se crea; dirección fuera de cobertura → `OutOfCoverageError`. _Depende de:_ T-9.1.2, T-6.1.2, T-4.2.1, T-8.1.1

- [ ] **T-9.2.2 · [Backend] `POST /api/v1/orders`**
  Body `{address_id, use_balance}`. Respuesta 201 con `{order, transfer}` (datos de `payment.transfer` + monto exacto).
  _Prueba:_ test end-to-end: arma carrito → confirma → 201 con datos de transferencia y `order.status=PENDING_PAYMENT`. _Depende de:_ T-9.2.1, T-1.5.2

- [ ] **T-9.2.3 · [Backend] `GET /orders` y `GET /orders/{id}` (cliente)**
  Mis pedidos (con filtro por estado) y detalle (solo el propio; 404 si es de otro).
  _Prueba:_ test: el cliente ve sus pedidos y no los de otro. _Depende de:_ T-9.1.1, T-1.5.1

- [ ] **T-9.2.4 · [Backend] `GET /orders/admin` (admin)**
  Listado con filtros `status`, `shift_id`, `q` (código/cliente) y paginación.
  _Prueba:_ test: admin lista y filtra por estado. _Depende de:_ T-9.1.1, T-1.5.2

## Tema 9.3 · Frontend

- [ ] **T-9.3.1 · [Frontend] Carrito → Confirmar**
  El botón "Confirmar pedido" llama a `POST /orders`. Si el pedido se hace dentro del período no cancelable, mostrar **antes** de confirmar el aviso de la skill ("Este pedido no podrá cancelarse para este turno").
  _Prueba:_ confirmar un pedido válido lleva a la pantalla de pago; el aviso aparece cuando corresponde. _Depende de:_ T-9.2.2, T-8.1.5

- [ ] **T-9.3.2 · [Frontend] `pages/cliente/pago.html` + js (datos de transferencia)** 🔒 requiere sesión
  Muestra alias, titular, banco/CBU y **monto exacto**. Botón "Ya transferí" (la carga de comprobante llega en Fase 10). Estado del pedido visible. Gateada con `requireRole()`.
  _Prueba:_ tras confirmar, la pantalla muestra los datos de transferencia y el monto del pedido; sin sesión redirige a login. _Depende de:_ T-9.2.2, T-1.11.4

- [ ] **T-9.3.3 · [Frontend] `pages/cliente/pedidos.html` + js** 🔒 requiere sesión
  Lista de pedidos del cliente con código, fecha, total y estado (etiqueta visible de la skill). Link al detalle/seguimiento. Gateada con `requireRole()`.
  _Prueba:_ el pedido recién creado aparece con estado "Pendiente de pago"; sin sesión redirige a login. _Depende de:_ T-9.2.3, T-1.11.4

- [ ] **T-9.3.4 · [Frontend] `pages/admin/pedidos.html` (lista básica)**
  Tabla de pedidos del turno con filtros por estado. Detalle en panel lateral. (Las acciones de estado llegan en Fase 13.)
  _Prueba:_ el admin ve el pedido creado por el cliente. _Depende de:_ T-9.2.4

## Cierre de fase

- [ ] **T-9.99 · [Docs] `Fase 09 - Confirmación del pedido.md`**

---

# FASE 10 · Pagos y comprobantes

> El cliente adjunta el comprobante y el pedido pasa a "Pago en verificación".

- [ ] **T-10.1.1 · [Backend] Modelos `Payment`, `PaymentProof` + repo + migración**
  §6.7. `Payment` ya se crea en el checkout (Fase 9); acá se agrega `PaymentProof` y los métodos del repo (`add_proof`, `list_proofs`, `set_status`).
  _Prueba:_ asociar un proof a un payment y listarlo. _Depende de:_ T-9.1.1

- [ ] **T-10.1.2 · [Backend] `services/external/storage.py`**
  `FileStorage` (Protocol) + `LocalFileStorage` (`storage/<subdir>/<uuid>.<ext>`, `save`/`open`). Nunca servido como estático.
  _Prueba:_ guardar bytes y volver a leerlos; el nombre es un uuid. _Depende de:_ T-0.2.1

- [ ] **T-10.1.3 · [Lógica] Validación de archivos**
  Extensión ∈ {jpg,jpeg,png,webp,pdf}, mime real coherente, tamaño ≤ `MAX_UPLOAD_MB`. `FileTooLargeError` / `InvalidInputError`.
  _Prueba:_ tests: imagen válida OK; `.exe` renombrado → rechazado; archivo de 20 MB → 413. _Depende de:_ T-10.1.2

- [ ] **T-10.1.4 · [Lógica] `PaymentService.attach_proof(order, file, uploader)`**
  Valida el archivo, lo guarda, crea `PaymentProof`, transición del pedido `PENDING_PAYMENT|PAYMENT_REJECTED → PAYMENT_UNDER_REVIEW`, `payment.status=UNDER_REVIEW`.
  _Prueba:_ test: subir comprobante mueve el pedido a "en verificación". _Depende de:_ T-10.1.3, T-9.1.2

- [ ] **T-10.1.5 · [Backend] `POST /payments/order/{id}/proofs` (multipart)**
  Rol CUSTOMER (propio) o ADMIN. Devuelve el pedido actualizado.
  _Prueba:_ test end-to-end: cliente sube comprobante → 200 y estado nuevo. _Depende de:_ T-10.1.4, T-1.5.2

- [ ] **T-10.1.6 · [Backend] `GET /payments/proofs/{id}` — descarga autorizada**
  Solo ADMIN o el CUSTOMER dueño. `StreamingResponse` con `Content-Disposition: attachment`. Nunca URL pública.
  _Prueba:_ test: el dueño y el admin descargan; otro cliente → 403/404. _Depende de:_ T-10.1.1, T-1.5.1

- [ ] **T-10.1.7 · [Backend] `GET /payments/order/{order_id}`**
  Estado del pago + datos de transferencia + lista de comprobantes (metadatos).
  _Prueba:_ test: devuelve `expected_amount` y `status`. _Depende de:_ T-10.1.1

- [ ] **T-10.1.8 · [Frontend] Pago: carga de comprobante**
  En `pago.html`: input de archivo (con preview para imágenes), subida a `POST .../proofs`, y el estado del pedido cambia a "Pago en verificación". Permite reemplazar mientras esté pendiente.
  _Prueba:_ el cliente sube una imagen y ve el estado actualizado. _Depende de:_ T-10.1.5

- [ ] **T-10.99 · [Docs] `Fase 10 - Pagos y comprobantes.md`**

---

# FASE 11 · Validación administrativa de pagos

> El admin valida los pagos desde una cola priorizada; solo los aprobados consumen stock y entran a producción.

- [ ] **T-11.1.1 · [Backend] Modelo `AuditLog` + `audit_log(actor, action, entity, data)` helper**
  §6.10. Se escribe desde los services.
  _Prueba:_ una aprobación de pago deja una fila en `audit_log`. _Depende de:_ T-0.3.2

- [ ] **T-11.1.2 · [Lógica] `PaymentService.approve / reject / mark_review`**
  `approve(order, admin, note)`: `payment.status=APPROVED`, transición `→PAYMENT_APPROVED`, `StockService.commit(order)`, `audit_log('payment.approve')`, notificación (Fase 16 engancha después). `reject(order, admin, reason)`: `→PAYMENT_REJECTED`. `mark_review(order, note)`: mantiene en revisión con nota. Idempotencia (aprobar dos veces no rompe).
  _Prueba:_ tests: approve mueve estado y consume stock; reject deja recuperable; sin rol admin → 403. _Depende de:_ T-9.1.2, T-4.2.2, T-11.1.1

- [ ] **T-11.1.3 · [Lógica] Cola de validación priorizada**
  `PaymentService.validation_queue(shift)`: pedidos `PENDING_PAYMENT`/`PAYMENT_UNDER_REVIEW` ordenados por criticidad (más cerca del cierre primero), con flag `critical` si faltan < X min para el cierre.
  _Prueba:_ test: un pedido próximo al cierre aparece primero y marcado `critical`. _Depende de:_ T-2.2.2

- [ ] **T-11.1.4 · [Backend] Endpoints de validación**
  `GET /orders/admin/validation-queue`, `POST /payments/order/{id}/approve`, `/reject`, `/mark-review`.
  _Prueba:_ test end-to-end: cliente crea y paga → admin ve en la cola → aprueba → estado `PAYMENT_APPROVED`. _Depende de:_ T-11.1.2, T-11.1.3

- [ ] **T-11.1.5 · [Backend] `on_shift_closed`: marcar sin validar como críticos**
  Parte del efecto de una sola vez al detectar el cierre (T-2.2.4): los pedidos aún sin aprobar quedan señalados para decisión del admin (no entran a producción).
  _Prueba:_ test: tras el cierre, un pedido sin validar no aparece en el consolidado de producción. _Depende de:_ T-2.2.4, T-11.1.2

- [ ] **T-11.1.6 · [Frontend] `pages/admin/dashboard.html`**
  Tarjetas: pedidos del día, **pedidos sin validar**, **críticos**, ventas del turno, stock bajo, deliveries disponibles. Estilo del sistema, layout de escritorio.
  _Prueba:_ los contadores reflejan el estado real del turno. _Depende de:_ T-11.1.3, T-9.2.4

- [ ] **T-11.1.7 · [Frontend] `pages/admin/validacion.html` + js**
  Cola priorizada (críticos destacados). Por pedido: monto esperado, comprobante (visor de imagen / link a PDF vía descarga autorizada), datos del cliente, y acciones Aprobar / Rechazar / Dejar pendiente con campo de nota.
  _Prueba:_ el admin abre un comprobante, aprueba el pago y el pedido cambia de estado; el stock consumido sube. _Depende de:_ T-11.1.4, T-10.1.6

- [ ] **T-11.1.8 · [Frontend] Cliente: reflejo del resultado**
  `pedidos.html` y `pago.html` muestran "Pago aprobado" / "Pago rechazado — volvé a adjuntar" según el estado.
  _Prueba:_ tras la aprobación del admin, el cliente ve "Pago aprobado" al recargar. _Depende de:_ T-11.1.4, T-9.3.3

- [ ] **T-11.99 · [Docs] `Fase 11 - Validación administrativa de pagos.md`**

---

# FASE 12 · Saldo a favor y cancelaciones

> El cliente puede cancelar dentro de la ventana y usar el saldo generado en pedidos futuros.

- [ ] **T-12.1.1 · [Backend] Modelo `BalanceTransaction` + repo + migración**
  §6.8. `CustomerBalance` ya existe (Fase 1). Repo: `get_balance`, `add_transaction`, `list_by_user`.
  _Prueba:_ registrar un credit y ver el saldo actualizado y el `balance_after`. _Depende de:_ T-1.2.2

- [ ] **T-12.1.2 · [Lógica] `BalanceService`**
  `credit(user, amount, origin, order, actor)`, `debit(user, amount, origin, order)` con guarda `balance >= amount`. Uso parcial permitido. No transferible. Sin vencimiento.
  _Prueba:_ tests: credit y debit ajustan el saldo; debit mayor al saldo → error; cada movimiento queda registrado. _Depende de:_ T-12.1.1

- [ ] **T-12.1.3 · [Lógica] `CancellationService`**
  `can_cancel(order, now)`: estado ∈ {PENDING_PAYMENT, PAYMENT_UNDER_REVIEW, PAYMENT_REJECTED} y `now <= shift.close_time - cancel_window_min`. `cancel_by_customer(order)` (guarda la ventana) y `cancel_by_admin(order, reason)` (sin restricción).
  _Prueba:_ tests: dentro de la ventana cancela; fuera → `CancelWindowClosedError`; admin siempre puede. _Depende de:_ T-2.2.2, T-9.1.2

- [ ] **T-12.1.4 · [Lógica] Efectos de la cancelación**
  Al pasar a `CANCELLED`: `StockService.release(order)`; si el pago estaba `APPROVED` → `BalanceService.credit` por lo efectivamente pagado; si se había aplicado saldo y el pedido no se consumió → devolver ese saldo. Todo en la misma transacción + `audit_log`.
  _Prueba:_ tests: cancelar un pedido pagado acredita saldo por el total pagado y libera el stock. _Depende de:_ T-12.1.2, T-4.2.2

- [ ] **T-12.1.5 · [Lógica] Aplicar saldo en el checkout**
  `OrderService.confirm` con `use_balance`: `balance_applied = min(balance, subtotal + shipping)`; `total = subtotal + shipping - balance_applied`; `BalanceService.debit(origin='order_use')`.
  _Prueba:_ tests: con saldo suficiente el total baja y se registra el debit; sin saldo, `balance_applied=0`. _Depende de:_ T-12.1.2, T-9.2.1

- [ ] **T-12.1.6 · [Backend] Endpoints**
  `POST /orders/{id}/cancel` (CUSTOMER), `GET /balance/me` (saldo + movimientos), `POST /balance/adjust` (ADMIN), cancelación admin vía `POST /orders/{id}/transition` (`cancel` + reason).
  _Prueba:_ test end-to-end: cancelar un pedido pagado deja saldo consultable en `/balance/me`. _Depende de:_ T-12.1.3, T-12.1.4

- [ ] **T-12.1.7 · [Frontend] Carrito/checkout: usar saldo**
  Si el cliente tiene saldo, checkbox "Usar mi saldo a favor ($…)"; el total se recalcula mostrando "Saldo aplicado −$…".
  _Prueba:_ con saldo disponible, aplicarlo baja el total del pedido. _Depende de:_ T-12.1.6, T-8.1.5

- [ ] **T-12.1.8 · [Frontend] Cliente: cancelar pedido + aviso de ventana**
  En `pedidos.html`/detalle: botón "Cancelar" visible solo si `can_cancel`; si no, leyenda "La cancelación ya no está disponible para este turno". Confirmación explicando que el importe queda como saldo a favor.
  _Prueba:_ cancelar dentro de la ventana funciona y muestra el saldo generado; fuera de la ventana el botón no está. _Depende de:_ T-12.1.6

- [ ] **T-12.1.9 · [Frontend] Perfil: saldo a favor y movimientos**
  Sección con el saldo actual y el listado de movimientos (origen, monto, fecha, pedido).
  _Prueba:_ el saldo y los movimientos coinciden con las cancelaciones/usos. _Depende de:_ T-12.1.6, T-1.11.5

- [ ] **T-12.1.10 · [Frontend] Admin: ajuste de saldo y cancelación**
  Desde el detalle del pedido/usuario: cancelar pedido con motivo y ajustar saldo manualmente (con nota).
  _Prueba:_ el admin cancela un pedido fuera de la ventana del cliente y acredita/ajusta saldo. _Depende de:_ T-12.1.6

- [ ] **T-12.99 · [Docs] `Fase 12 - Saldo a favor y cancelaciones.md`**

---

# FASE 13 · Estados del pedido y producción

> Máquina de estados completa y vista consolidada de producción para la cocina.

- [ ] **T-13.1.1 · [Lógica] `OrderStateMachine` (completa)**
  Agregar todas las transiciones de `02_Documento_Tecnico.md §8`: `PAYMENT_APPROVED→IN_PREPARATION`, `→READY_FOR_PICKUP`, `→ASSIGNED_TO_DELIVERY`, `→OUT_FOR_DELIVERY`, `→DELIVERED`, `→DELIVERY_INCIDENT` y sus retornos, con guardas por rol (ADMIN / DELIVERY). Efectos colaterales declarados por transición.
  _Prueba:_ tests exhaustivos: cada transición válida y una muestra de inválidas; guardas de rol. _Depende de:_ T-9.1.2

- [ ] **T-13.1.2 · [Lógica] Paso masivo a producción**
  `ShiftService.to_production(shift)`: `PAYMENT_APPROVED → IN_PREPARATION` para todos los pedidos del turno. Idempotente.
  _Prueba:_ test: tras `to_production`, los aprobados quedan en preparación y los no aprobados no. _Depende de:_ T-13.1.1, T-2.2.4

- [ ] **T-13.1.3 · [Lógica] `ProductionService`**
  `by_product(shift)`, `by_category(shift)`, `detail(shift)` sobre pedidos con estado ≥ `PAYMENT_APPROVED` (sin `CANCELLED`). Opción `include_pending` para una sección informativa aparte.
  _Prueba:_ tests: cantidades por producto/categoría correctas; los cancelados no cuentan. _Depende de:_ T-9.1.1

- [ ] **T-13.1.4 · [Backend] `POST /orders/{id}/transition` (ADMIN / DELIVERY)**
  Acción (`mark_ready`, `assign`, `start_route`, `deliver`, `incident`, `cancel`, …) validada por la máquina de estados y el rol. Registra historia y ejecuta efectos.
  _Prueba:_ test: admin marca `IN_PREPARATION→READY_FOR_PICKUP`; un cliente intentándolo → 403. _Depende de:_ T-13.1.1, T-1.5.2

- [ ] **T-13.1.5 · [Backend] Endpoints de producción (ADMIN)**
  `GET /production/shift/{id}/by-product`, `/by-category`, `/detail`.
  _Prueba:_ test: el consolidado coincide con los pedidos aprobados del turno. _Depende de:_ T-13.1.3

- [ ] **T-13.1.6 · [Frontend] `pages/admin/pedidos.html` (completo)**
  Lista con filtros por estado, búsqueda, historial de estados por pedido, y acciones de transición contextuales según el estado.
  _Prueba:_ el admin recorre un pedido por sus estados desde la UI. _Depende de:_ T-13.1.4

- [ ] **T-13.1.7 · [Frontend] `pages/admin/produccion.html` + js**
  Consolidado por producto y por categoría (tablas densas), y detalle por pedido (cliente + ítems). Botón "Pasar turno a producción".
  _Prueba:_ el consolidado muestra las cantidades a preparar del turno. _Depende de:_ T-13.1.5

- [ ] **T-13.1.8 · [Frontend] Cliente: línea de tiempo de estados**
  En el detalle del pedido, una línea de tiempo con las etiquetas visibles de la skill (Pendiente de pago → … → Entregado) marcando el estado actual.
  _Prueba:_ el cliente ve avanzar el estado de su pedido cuando el admin lo mueve. _Depende de:_ T-13.1.4, T-9.3.3

- [ ] **T-13.99 · [Docs] `Fase 13 - Estados y producción.md`**

---

# FASE 14 · Repartidores y asignación

> El admin arma la logística del turno; el repartidor trabaja desde su interfaz móvil.

## Tema 14.1 · Repartidores

- [ ] **T-14.1.1 · [Backend] Perfil de repartidor y disponibilidad**
  `UserProfile` (driver): `vehicle_type`, `capacity`, `driver_status`. `DriverService.set_status(driver, status)` con reglas (`DISPONIBLE/NO_DISPONIBLE/EN_RUTA/INACTIVO`; `EN_RUTA` solo lo pone el sistema).
  _Prueba:_ tests: el repartidor puede pasar a `NO_DISPONIBLE` pero no forzar `EN_RUTA`. _Depende de:_ T-1.7.1

- [ ] **T-14.1.2 · [Backend] Endpoints de repartidores**
  `GET /drivers`, `POST /drivers`, `PATCH /drivers/{id}` (ADMIN); `PATCH /drivers/me/status` (DELIVERY).
  _Prueba:_ test: admin da de alta un repartidor; el repartidor cambia su disponibilidad. _Depende de:_ T-14.1.1

## Tema 14.2 · Asignación y rutas

- [ ] **T-14.2.1 · [Backend] Modelos `DeliveryAssignment`, `DeliveryRoute`, `DeliveryStop` + repo + migración**
  §6.9.
  _Prueba:_ crear una asignación con 3 paradas ordenadas. _Depende de:_ T-9.1.1, T-14.1.1

- [ ] **T-14.2.2 · [Lógica] `AssignmentService`**
  `assign(shift, driver, order_ids)`: valida pedidos `READY_FOR_PICKUP`, crea/actualiza `DeliveryAssignment` + `DeliveryRoute` + `DeliveryStop` (`stop_index` según orden recibido), transición de los pedidos a `ASSIGNED_TO_DELIVERY`. `reorder(route, order_ids)`.
  _Prueba:_ tests: asignar mueve los pedidos de estado; reasignar quita del repartidor anterior. _Depende de:_ T-13.1.1, T-14.2.1

- [ ] **T-14.2.3 · [Lógica] `services/external/routing.py`**
  `RouteProvider` (Protocol) + `ManualProvider` (respeta el orden dado) + `NearestNeighborProvider` (ordena por cercanía desde el origen usando Haversine). Selección por `ROUTE_PROVIDER`.
  _Prueba:_ tests: `NearestNeighbor` produce un orden razonable para un set de coords conocido. _Depende de:_ T-7.2.2

- [ ] **T-14.2.4 · [Lógica] Flujo del repartidor**
  `start_route(assignment, driver)`: assignment `IN_PROGRESS`, driver `EN_RUTA`, paradas → `OUT_FOR_DELIVERY`. `deliver_stop(stop)` / `incident_stop(stop, note)`: transición del pedido correspondiente. Al completar todas → assignment `COMPLETED`, driver `DISPONIBLE`.
  _Prueba:_ tests: iniciar ruta cambia estados; entregar todas cierra la asignación. _Depende de:_ T-14.2.2, T-13.1.1

## Tema 14.3 · Backend y front

- [ ] **T-14.3.1 · [Backend] Endpoints de asignación y ruta**
  `GET /assignments?shift_id=`, `POST /assignments`, `POST /assignments/{id}/route/reorder` (ADMIN); `GET /assignments/me`, `POST /assignments/{id}/start`, `POST /stops/{id}/deliver`, `POST /stops/{id}/incident` (DELIVERY).
  _Prueba:_ test end-to-end: admin asigna → repartidor ve su ruta → inicia → entrega parada por parada. _Depende de:_ T-14.2.2, T-14.2.4

- [ ] **T-14.3.2 · [Frontend] `pages/admin/deliveries.html`**
  Lista de repartidores con disponibilidad, alta/edición.
  _Prueba:_ el admin gestiona la nómina de repartidores. _Depende de:_ T-14.1.2

- [ ] **T-14.3.3 · [Frontend] `pages/admin/logistica.html` + js**
  Pedidos `READY_FOR_PICKUP` sin asignar; asignación por repartidor (arrastrar o seleccionar); reordenar paradas; ver la ruta resultante.
  _Prueba:_ el admin asigna 3 pedidos a un repartidor y ordena las paradas. _Depende de:_ T-14.3.1

- [ ] **T-14.3.4 · [Frontend] App del repartidor: `inicio`, `ruta`, `parada`, `historial`**
  Interfaz mobile-first muy simple (skill): disponibilidad, lista de paradas ordenada, parada actual con dirección y datos mínimos, botón "Navegar" (link a Google/Waze), "Marcar entregado" / "Incidencia".
  _Prueba:_ el repartidor completa una ruta de prueba desde el teléfono/emulación. _Depende de:_ T-14.3.1

- [ ] **T-14.3.5 · [Backend + Docs] Seed de repartidores**
  1-2 repartidores de prueba en `Usuarios.md`.
  _Prueba:_ login del repartidor y acceso a su interfaz. _Depende de:_ T-14.1.1

- [ ] **T-14.99 · [Docs] `Fase 14 - Repartidores y asignación.md`**

---

# FASE 15 · Seguimiento en tiempo real (básico)

> El cliente ve el avance de su entrega sin ver datos de otros; el admin ve a sus repartidores.

- [ ] **T-15.1.1 · [Backend] Modelo `DriverLocation` + repo + migración**
  §6.9. Repo: `add`, `latest_for_driver`, `prune_older_than`.
  _Prueba:_ insertar posiciones y recuperar la última. _Depende de:_ T-14.2.1

- [ ] **T-15.1.2 · [Lógica] `TrackingService`**
  `push_location(driver, lat, lng)`: solo si el repartidor tiene una asignación `IN_PROGRESS` (si no, se ignora). `driver_last_location(assignment)`. `customer_view(order)`: `{status, stop_index, stops_before, eta}` — **sin** direcciones, nombres ni ítems de terceros.
  _Prueba:_ tests: push sin ruta activa se ignora; `customer_view` no expone datos de otros pedidos; `stops_before` correcto. _Depende de:_ T-14.2.4

- [ ] **T-15.1.3 · [Backend] Endpoints**
  `POST /drivers/me/location` (DELIVERY), `GET /assignments/{id}/location` (ADMIN), `GET /orders/{id}/tracking` (CUSTOMER dueño).
  _Prueba:_ test: el repartidor reporta ubicación, el admin la ve, el cliente ve su posición relativa. _Depende de:_ T-15.1.2

- [ ] **T-15.1.4 · [Backend] Purga de ubicaciones viejas (> 7 días) al escribir, sin job**
  `push_location()` (T-15.1.3), de paso, borra las ubicaciones de ese repartidor con más de 7 días — sin scheduler dedicado, es solo higiene de datos y no tiene apuro de horario.
  _Prueba:_ test: al reportar una ubicación nueva, las viejas de ese repartidor (> 7 días) se eliminan. _Depende de:_ T-15.1.1, T-15.1.3

- [ ] **T-15.1.5 · [Frontend] App del repartidor: envío de ubicación**
  Con ruta activa, `navigator.geolocation.watchPosition` → `POST /drivers/me/location` cada N segundos. Manejo de permisos denegados.
  _Prueba:_ al iniciar ruta, la ubicación del repartidor llega al backend. _Depende de:_ T-15.1.3, T-14.3.4

- [ ] **T-15.1.6 · [Frontend] Cliente: `pages/cliente/seguimiento.html` + js** 🔒 requiere sesión
  Estado del pedido, "Paradas antes de tu entrega: N", ETA estimada, y (si hay datos) una indicación de que el repartidor está en camino. Polling cada N segundos. Sin mapa con direcciones de terceros. Gateada con `requireRole()`.
  _Prueba:_ mientras el repartidor avanza, el cliente ve bajar el contador de paradas; sin sesión redirige a login. _Depende de:_ T-15.1.3, T-1.11.4

- [ ] **T-15.1.7 · [Frontend] Admin: monitoreo de repartidores**
  En `logistica.html`, panel con el estado de cada asignación y la última ubicación conocida (+ hora) de cada repartidor en ruta.
  _Prueba:_ el admin ve la última posición y el "hace X min". _Depende de:_ T-15.1.3

- [ ] **T-15.99 · [Docs] `Fase 15 - Seguimiento.md`**

---

# FASE 16 · Notificaciones

> Centro de notificaciones in-app para los tres roles.

- [ ] **T-16.1.1 · [Backend] Modelo `Notification` + repo + migración**
  §6.10. Repo: `create`, `list(user, unread?)`, `mark_read`, `mark_all_read`.
  _Prueba:_ CRUD y contador de no leídas. _Depende de:_ T-1.2.1

- [ ] **T-16.1.2 · [Lógica] `NotificationService` + `InAppChannel`**
  `notify(user, type, context)` construye título/cuerpo por `NotificationType` y lo enruta a los canales activos (v1: solo `InAppChannel` → tabla). Interfaz `NotificationChannel` lista para email/push.
  _Prueba:_ test: `notify` crea la fila con el texto correcto por tipo. _Depende de:_ T-16.1.1

- [ ] **T-16.1.3 · [Lógica] Enganchar eventos**
  Emitir notificaciones en: pedido creado (cliente+admin), comprobante recibido (admin), pago aprobado/rechazado (cliente), pedido cancelado + saldo acreditado (cliente), en preparación / en camino / entregado (cliente), listo/asignado (repartidor), incidencia (admin), pedidos críticos sin validar (admin).
  _Prueba:_ tests: cada evento del flujo genera su notificación a los destinatarios correctos. _Depende de:_ T-16.1.2, (services de Fases 9–15)

- [ ] **T-16.1.4 · [Backend] Endpoints**
  `GET /notifications?unread=true`, `POST /notifications/{id}/read`, `POST /notifications/read-all`.
  _Prueba:_ test: listar, marcar una y marcar todas. _Depende de:_ T-16.1.1, T-1.5.1

- [ ] **T-16.1.5 · [Frontend] Centro de notificaciones (los 3 roles)**
  Ícono de campana en el header con badge de no leídas; panel desplegable con la lista (título, tiempo relativo, link al pedido). Marcar leídas. Polling ligero.
  _Prueba:_ al aprobarse un pago, al cliente le aparece la campana con "Pago aprobado". _Depende de:_ T-16.1.4

- [ ] **T-16.99 · [Docs] `Fase 16 - Notificaciones.md`**

---

# FASE 17 · Cierre de MVP: pulido y QA

> Repaso transversal contra los criterios de aceptación y la calidad visual.

- [ ] **T-17.1.1 · [QA] Checklist de criterios de aceptación del MVP**
  Recorrer los 15 criterios de `01_Documento_General.md §20` y marcar cada uno con evidencia.
  _Prueba:_ los 15 criterios cumplidos y documentados. _Depende de:_ Fases 1–16

- [ ] **T-17.1.2 · [Frontend] Revisión de adaptación escritorio (todas las pantallas)**
  Recorrer cada página a 360 / 768 / 1024 / 1440 px: nav correcta por breakpoint, sin cards/botones estirados, uso del ancho con columnas, estética Artesanal · Cocina de Olla consistente. Ajustar contra el checklist de la skill.
  _Prueba:_ ninguna pantalla "rompe" ni deja huecos en escritorio. _Depende de:_ T-17.1.1

- [ ] **T-17.1.3 · [Frontend] Estados vacíos, de carga y de error**
  Cada listado tiene su empty state; cada acción, su estado de carga; los errores del backend se muestran con el mensaje correcto y tono del sistema.
  _Prueba:_ recorrer los flujos sin datos y con fallos simulados. _Depende de:_ T-17.1.2

- [ ] **T-17.1.4 · [QA] Accesibilidad**
  Contraste AA, foco visible, navegación por teclado en el panel admin, áreas táctiles ≥ 44px, `alt` en imágenes, estados no solo por color, `prefers-reduced-motion`.
  _Prueba:_ auditoría manual + Lighthouse/axe sin errores críticos. _Depende de:_ T-17.1.2

- [ ] **T-17.1.5 · [QA] Prueba de flujo completa end-to-end**
  Un turno simulado: apertura → cliente pide y paga → admin valida → cierre → producción → asignación → reparto → entrega → notificaciones, más una cancelación con saldo y su reutilización.
  _Prueba:_ el flujo completo funciona sin intervención manual en DB. _Depende de:_ Fases 1–16

- [ ] **T-17.1.6 · [QA] Repaso de seguridad**
  Autorización backend en cada endpoint, comprobantes no accesibles sin permiso, rate limiting activo, `.env` fuera de git, headers de seguridad, auditoría completa de acciones sensibles.
  _Prueba:_ checklist de `02_Documento_Tecnico.md §18` verificado. _Depende de:_ Fases 1–16

- [ ] **T-17.1.7 · [Backend + Docs] Seed/demo final y `Usuarios.md` al día**
  Datos demo coherentes para una demo completa; credenciales de todos los usuarios de prueba documentadas.
  _Prueba:_ siguiendo el arranque manual del `README.md` (local) o el runbook `deploy/DEPLOY.md` (VPS), el proyecto queda listo para demo. _Depende de:_ T-17.1.5

- [ ] **T-17.99 · [Docs] `Fase 17 - Cierre de MVP.md`**

---

## Backlog posterior (Fase 18+) — Etapa "Evolución"

No forma parte de este roadmap detallado; se planificará al cerrar el MVP.

- Optimización avanzada de rutas con proveedor externo (OSRM / Google Directions) y ventanas horarias.
- Sugerencia automática de distribución de pedidos entre repartidores.
- Seguimiento GPS de alta frecuencia y mapa en vivo.
- Notificaciones por email y push (PWA).
- Empresas como entidad (`companies`, `company_members`, pedidos por empresa).
- Múltiples turnos (desayuno / cena).
- Pedidos grupales colaborativos.
- Etiquetas por ítem ("Para: …") en la UI de reparto.
- Propina y evidencia de entrega (PIN / foto / firma).
- Integración con pasarelas de pago.
- Analítica y reporting (ventas, demanda, performance de reparto).
- Migración a PostgreSQL y workers de tareas dedicados.

---

## Estado global

| Fase | Estado | Doc de cierre |
|---|---|---|
| 0 · Andamiaje y base visual | ✅ Completa | `Fase 00 - Andamiaje y base visual.md` |
| 1 · Usuarios, roles y autenticación | ⬜ Pendiente | — |
| 2 · Configuración y turnos | ⬜ Pendiente | — |
| 3 · Catálogo | ⬜ Pendiente | — |
| 4 · Stock | ⬜ Pendiente | — |
| 5 · Promociones y Plato del Día | ⬜ Pendiente | — |
| 6 · Carrito | ⬜ Pendiente | — |
| 7 · Direcciones y cobertura | ⬜ Pendiente | — |
| 8 · Costos de envío | ⬜ Pendiente | — |
| 9 · Confirmación del pedido | ⬜ Pendiente | — |
| 10 · Pagos y comprobantes | ⬜ Pendiente | — |
| 11 · Validación administrativa | ⬜ Pendiente | — |
| 12 · Saldo a favor y cancelaciones | ⬜ Pendiente | — |
| 13 · Estados y producción | ⬜ Pendiente | — |
| 14 · Repartidores y asignación | ⬜ Pendiente | — |
| 15 · Seguimiento | ⬜ Pendiente | — |
| 16 · Notificaciones | ⬜ Pendiente | — |
| 17 · Cierre de MVP | ⬜ Pendiente | — |

Leyenda: ⬜ Pendiente · 🟨 En curso · ✅ Completa y aprobada

---

*Fin del documento 03 · Roadmap. El trabajo arranca en `T-0.1.1` tras la aprobación del usuario.*
