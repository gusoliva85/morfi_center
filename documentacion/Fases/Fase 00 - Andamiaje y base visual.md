# Fase 00 · Andamiaje y base visual

**Estado:** Completa y aprobada
**Fecha de cierre:** 2026-09-16
**Roadmap:** `03_Roadmap.md` — Fase 0

---

## 1. Objetivo

Dejar el proyecto listo para trabajar: estructura de carpetas, backend que responde, base de datos con migraciones, home del cliente con el estilo **Artesanal · Cocina de Olla** (sin lógica), y toda la infraestructura de despliegue (Vercel para el frontend, VPS Contabo para el backend y la base de datos, con despliegue continuo).

## 2. Temas y tareas cerradas

| Tema | Tareas |
|---|---|
| 0.1 · Estructura del repositorio | T-0.1.1, T-0.1.2, T-0.1.3 |
| 0.2 · Esqueleto del backend | T-0.2.1 a T-0.2.6 |
| 0.3 · Base de datos y migraciones | T-0.3.1 a T-0.3.4 |
| 0.4 · Frontend — base visual | T-0.4.1 a T-0.4.6 |
| 0.5 · Tooling | T-0.5.2 (T-0.5.1, `iniciar.bat`, se descartó — ver §5) |
| 0.6 · Documentación viva | T-0.6.1, T-0.6.2 |
| 0.7 · Despliegue | T-0.7.1 a T-0.7.9 |

## 3. Qué se hizo y cómo quedó implementado

### Tema 0.1 · Estructura del repositorio

**En palabras:** árbol de carpetas completo según `02_Documento_Tecnico.md §4` (sin `app/jobs/`, que no aplica — ver §10, el proyecto no tiene procesos de fondo). `.gitignore` ignora el *contenido* de `backend/data/` y `backend/storage/payment_proofs/` (no las carpetas enteras), para que los `.gitkeep` queden versionados. `requirements.txt` + `pyproject.toml` (ruff, black, pytest).

**Código clave** (`backend/requirements.txt`, extracto):
```
fastapi>=0.115,<1.0
sqlalchemy>=2.0,<3.0
alembic>=1.13,<2.0
bcrypt>=4.1,<5.0        # no passlib[bcrypt] — ver §5
tzdata>=2024.1          # ver §5
pytest>=8.3,<9.0
```

**Cómo se probó:** `pip install -r requirements.txt` en un venv limpio, sin errores.

### Tema 0.2 · Esqueleto del backend

**En palabras:** `Settings` (pydantic-settings) con las ~20 variables de §19, con un validador que **rechaza el arranque** si `APP_ENV=production` y `JWT_SECRET` quedó en el valor por defecto de desarrollo. 18 enums (`str, Enum`) — incluye 3 que faltaban en el catálogo del §7 (`AssignmentStatus`, `StopStatus`, `SettingValueType`), agregados al detectar que existían como `CHECK` en el modelo físico pero no como enum. `DomainError` + 8 subclases con handler global al formato `{"error":{...}}`. `RequestIdMiddleware` + `JsonFormatter`/formato plano según entorno. `main.py` con CORS, Swagger en `/api/docs`, healthcheck.

**Código clave** (`backend/app/main.py`):
```python
app = FastAPI(title=settings.app_name, docs_url="/api/docs", lifespan=lifespan)
register_error_handlers(app)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_credentials=True, ...)

@app.get(f"{settings.api_prefix}/health")
def health(): return {"status": "ok", "env": settings.app_env}
```

**Cómo se probó:** `uvicorn app.main:app` real + `curl /api/v1/health` → 200; 48 tests de pytest.

### Tema 0.3 · Base de datos y migraciones

**En palabras:** engine SQLite con PRAGMAs (`foreign_keys=ON`, `journal_mode=WAL`, `busy_timeout=5000`), `get_session()` con commit/rollback automático. `DeclarativeBase` con convención de nombres de constraints. Alembic inicializado de verdad (`alembic init`), `env.py` conectado a `Settings` + `Base.metadata`, `render_as_batch=True`. `db/seed.py` — esqueleto idempotente, vacío hasta Fase 1.

**Cómo se probó:** `alembic revision -m "baseline"` + `upgrade head` + `downgrade -1` + `upgrade head` de nuevo, todo limpio, contra el VPS real también.

### Tema 0.4 · Frontend — base visual

**En palabras:** `base.css` con las utilidades del sistema (`.paper`, `.blob`/`.blob2`, `.stamp`, `.tape`, `.dashed`, `.foodA..D`, `.lift`), extraídas del mockup aprobado `04_Artesanal_Organico.html`. `tailwind.config.js` con los tokens de color/tipografía. Parciales (`header`, `top-nav`, `bottom-nav`, `cart-bar`) + `ui.js` (`injectPartials()` recursivo, `toast()`). `index.html` — Home completa, con **fotos reales de platos** (provistas por el usuario) en vez de emoji/gradiente. `format.js` (moneda, fecha, hora — con zona horaria única). `api.js`/`auth.js` completos (wrapper de fetch, `ApiError`, `bootstrapSession`/`login`/`logout`/`requireRole`), aunque el backend de auth llega recién en Fase 1.

**Cómo se probó:** cada pieza tuvo su página de sandbox (`frontend/_sandbox/`), revisada visualmente por el usuario. La Home tuvo una segunda vuelta: el primer diseño desbordaba en mobile (se midió con Playwright headless a 360px: la sección izquierda medía 408px sobre un viewport de 360, y el panel con `overflow-hidden` recortaba en vez de hacer scroll). Se corrigió con `min-w-0` en las columnas de grilla y un layout mobile-first real (foto del Plato del Día arriba a todo el ancho en mobile, texto abajo; columnas lado a lado desde `sm:`). Verificado sin desborde en 320/360/414/768/1440px, y confirmado en el celular real del usuario.

### Tema 0.5 · Tooling

**En palabras:** `conftest.py` con fixtures `session` (SQLite en memoria, `StaticPool` — sin esto se pierde el esquema entre queries) y `client` (`httpx.AsyncClient` con `get_session` sobreescrito). `T-0.5.1` (`iniciar.bat`) se descartó por completo — ver §5.

**Cómo se probó:** verificación explícita de aislamiento — corriendo solo los tests nuevos (sin `test_db_session.py`, que usa la sesión real a propósito), `backend/data/` queda vacío.

### Tema 0.6 · Documentación viva

**En palabras:** `documentacion/Usuarios.md` (vacío hasta el seed de Fase 1). Plantilla `documentacion/Fases/_Plantilla_Fase.md` — este mismo documento es la primera vez que se usa.

### Tema 0.7 · Despliegue

**En palabras:** infraestructura completa y verificada contra el VPS real (Contabo, 4 vCPU/8GB/100GB) — hardening (usuario no-root, SSH solo por clave, firewall), stack (Python/Nginx/Certbot), servicio `systemd` + Nginx + HTTPS (con `sslip.io`, sin dominio propio), frontend en Vercel, CORS habilitado para el dominio real de Vercel, backups automáticos por cron, y despliegue continuo del backend vía GitHub Actions (clave SSH dedicada + `sudo NOPASSWD` acotado a un único comando). Runbook completo, paso a paso, en `deploy/DEPLOY.md`.

**Cómo se probó:** cada pieza se verificó en el servidor real, no en teoría — incluyendo forzar dos deploys automáticos de punta a punta (un cambio de prueba y su revert) y confirmar que el `MainPID` del servicio cambiaba en cada uno.

## 4. Usuarios de prueba agregados en esta fase

Ninguno — `db/seed.py` sigue vacío. Se completa desde `T-1.10.1` (Fase 1).

## 5. Decisiones y hallazgos no triviales

- **`passlib[bcrypt]` reemplazado por `bcrypt` directo**: `passlib` 1.7.4 (sin mantenimiento desde 2020) rompe con `bcrypt` ≥ 4.1 (`AttributeError`/`ValueError` al hashear). Verificado reproduciendo el bug antes de decidir el cambio.
- **`tzdata` agregado a `requirements.txt`**: en Windows, `zoneinfo` no trae la base IANA integrada — `ZoneInfo("America/Argentina/Buenos_Aires")` falla sin ese paquete.
- **3 enums faltantes** en el catálogo del §7 (`AssignmentStatus`, `StopStatus`, `SettingValueType`) que ya existían como `CHECK` en el modelo físico del §6.
- **`app/jobs/` no se crea**: contradice la decisión de §10 (sin procesos de fondo) que ya estaba tomada pero no se había limpiado del todo del roadmap.
- **`base.css` sin las directivas `@tailwind base/components/utilities`**: sin ellas, el build de producción de Tailwind no generaba ninguna clase (`bg-kraft`, `font-display`, etc.) — detectado corriendo un build real, no revisando el JS de la config.
- **Mockup de front**: hubo una confusión real entre `01_Editorial_Premium` y `04_Artesanal_Organico` al retomar el proyecto en un chat nuevo — quedó resuelta y documentada la decisión final (`04_Artesanal_Organico`, "Artesanal · Cocina de Olla").
- **`iniciar.bat` descartado por completo**: el proyecto pasa a pensarse como "siempre desplegado" (Vercel + VPS), no como algo que se levanta con un doble clic local.
- **Certbot no emite certificados para una IP sola**: se resolvió con `sslip.io` (gratis, sin dominio propio) en vez de bloquear el HTTPS o comprar un dominio antes de lo planeado.
- **Vercel + monorepo**: por defecto sirve desde la raíz del repo (`backend/`, `frontend/`, `documentacion/` al mismo nivel) y da 404 en `/` hasta fijar `Root Directory = frontend`.
- **`sudo` no funciona en `ssh host "comando"` no interactivo**: todo lo que lleva `sudo` lo tipea la propia persona, salvo la única regla `NOPASSWD` acotada a `systemctl restart morficenter-api` para el pipeline de CI/CD.
- **`nohup comando &` por SSH puede dejar la sesión colgada** aunque el proceso ya se haya desprendido bien.
- **Servicio SSH se llama `ssh`, no `sshd`**, en Ubuntu.
- **`/etc/ssh/sshd_config.d/50-cloud-init.conf`** pisa `PasswordAuthentication` de `sshd_config` si no se corrige también ahí (se procesa antes).

## 6. Pendientes / deuda técnica dejada para después

- La cookie de refresh cross-site (`T-0.7.6`) solo tiene resuelta la parte de CORS; la prueba real con login/`/auth/refresh` queda pendiente hasta que exista `T-1.4.2` en Fase 1.
- Si en el futuro se compra un dominio propio, conviene pasar la cookie a `Domain=.dominio.com` + `SameSite=Lax` (más robusto que `SameSite=None` con `sslip.io`).
- Backups actuales son solo locales al VPS (otro directorio del mismo disco); almacenamiento externo queda como mejora futura si se define.
