# MORFI CENTER
## 02 · Documento Técnico

**Proyecto:** Morfi Center
**Basado en:** `01_Documento_General.md` (funcional) · `MORFI_CENTER_INFO.md` (spec maestra) · mockup aprobado `documentacion/mockups/04_Artesanal_Organico.html`
**Fecha:** 9 de septiembre de 2026
**Estado:** Versión 1.0 — base para implementación

---

## Índice

1. Objetivo y alcance técnico
2. Decisiones tecnológicas
3. Arquitectura general
4. Estructura de carpetas
5. Arquitectura del backend (capas)
6. Modelo de datos físico (SQLite)
7. Enumeraciones y catálogos
8. Máquina de estados del pedido
9. Lógica de negocio (servicios de dominio)
10. Resolución bajo demanda (sin tareas programadas)
11. API REST — convenciones
12. API REST — endpoints por módulo
13. Autenticación y autorización
14. Servicios externos (geocodificación, rutas, notificaciones, almacenamiento)
15. Arquitectura del frontend
16. Sistema de diseño y adaptación mobile ↔ escritorio
17. Integración frontend ↔ backend
18. Seguridad
19. Configuración y variables de entorno
20. Manejo de errores, logging y auditoría
21. Datos semilla y usuarios de prueba
22. Testing
23. Migraciones de base de datos
24. Ejecución local y entornos (desarrollo y despliegue en producción)
25. Estrategia de escalabilidad
26. Zona horaria y manejo de fechas
27. Convenciones de código
28. Orden técnico de implementación
29. Anexos (ER, matriz endpoints/roles)

---

## 1. Objetivo y alcance técnico

Definir **cómo** se construye Morfi Center: stack, arquitectura, modelo de datos, contratos de API, reglas técnicas de negocio, seguridad, frontend y flujo de trabajo de implementación.

Alcance de esta versión: cubre las Fases 1–7 del roadmap funcional. La Fase 8 (optimización avanzada, integraciones de pago, analítica) se contempla a nivel de puntos de extensión, no de implementación.

Premisas fijas del proyecto:

- Frontend: **HTML + CSS + Tailwind** + JavaScript vanilla. Sin framework de UI. Estilo **Artesanal · Cocina de Olla** (skill `morfi-frontend`).
- Backend: **Python + SQLite**.
- **Mobile-first**; al superar el breakpoint móvil se adopta un layout de escritorio propio (no un simple "responsive estirado").
- Arquitectura **simple**, con carpetas `backend/` y `frontend/` separadas, y **escalable** (capas desacopladas, servicios intercambiables, ORM que permite migrar de motor).
- Trabajo incremental por funcionalidad: **lógica → backend → frontend**, una a la vez, validando con el usuario.

---

## 2. Decisiones tecnológicas

| Área | Elección | Motivo |
|---|---|---|
| Lenguaje backend | Python 3.11+ | Requisito del proyecto |
| Framework web | **FastAPI** | Validación con Pydantic, OpenAPI automático (contrato vivo para el front), inyección de dependencias ideal para RBAC, listo para async, curva simple |
| Servidor ASGI | **Uvicorn** | Estándar con FastAPI |
| ORM | **SQLAlchemy 2.0** (estilo declarativo + `Session`) | Desacopla del motor; permite migrar SQLite → PostgreSQL sin reescribir lógica |
| Migraciones | **Alembic** | Versionado del esquema |
| Base de datos | **SQLite** (archivo local) | Requisito. `PRAGMA foreign_keys=ON`, modo **WAL**, `busy_timeout` |
| Validación / schemas | **Pydantic v2** | Entrada/salida de la API, settings |
| Hash de contraseñas | **bcrypt** (librería directa, sin passlib), pin `>=4.1,<5.0` | `passlib` está sin mantenimiento desde 2020 y no es compatible con `bcrypt` ≥ 4.1 (bug verificado al instalar: `AttributeError`/`ValueError` al hashear). Se usa `bcrypt` directo — más simple, sin la capa de abstracción multi-esquema que no hace falta (solo se usa bcrypt). **Límite de 72 bytes por contraseña, y el comportamiento cambia entre versiones**: `bcrypt` 4.x (nuestro pin) trunca en silencio a 72 bytes; `bcrypt` ≥ 5.0 en cambio lanza `ValueError`. Por eso `UserService.validate_password` (§ Fase 1) rechaza contraseñas de más de 72 bytes antes de que lleguen a `hash_password` — así el comportamiento es el mismo (un error de validación claro) sin importar qué versión de `bcrypt` esté instalada |
| Tokens | **PyJWT** (o `python-jose`) | JWT access + refresh |
| OAuth Google | **Authlib** | Cliente OAuth2 / OIDC |
| HTTP client (servicios externos) | **httpx** | Geocodificación, etc. |
| Config | **pydantic-settings** + `.env` | Un único punto de configuración |
| Logging | **logging** stdlib + formato JSON opcional | Trazabilidad |
| Frontend build | **Tailwind CLI** (binario standalone, sin Node obligatorio) | Genera `tailwind.css`. En desarrollo temprano se admite el CDN de Tailwind |
| Frontend runtime | HTML multipágina + **ES Modules** vanilla | Sin dependencias; simple y portable |
| Servido del front | En **dev**: `python -m http.server` (puerto 5500). En **prod**: **Vercel** (hosting estático, build en su CI) | Despliegue independiente del backend, sin servidor Python de por medio |
| Hosting backend + DB | **VPS Contabo** (Ubuntu, 4 vCPU / 8 GB RAM / 100 GB) con Nginx + Uvicorn vía `systemd` + Certbot (HTTPS) | Contratado (plan anual) por el usuario; SQLite vive como archivo en su disco |
| Tests | **pytest** + **httpx.AsyncClient** + SQLite en memoria | Rápidos y aislados |
| Formato/lint | **ruff** + **black** (Python) · Prettier opcional (HTML/JS) | Consistencia |

> No se usa Node.js como dependencia de ejecución. El binario de Tailwind CLI es autónomo. Si el equipo prefiere, puede quedarse en el CDN de Tailwind durante toda la Fase 0–2 y hacer el build recién al empaquetar.

> **Sin tareas programadas de fondo.** El turno (apertura/cierre) y el vencimiento de reservas de stock **no** dependen de un proceso que vigile el reloj: se resuelven **bajo demanda**, calculando el estado a partir de la hora actual en el momento en que alguien lo pide (ver §10). Esto evita un componente más para operar (`APScheduler` u otro *scheduler*) sin perder ninguna regla de negocio — el detalle y el motivo de esta decisión están en §10.

---

## 3. Arquitectura general

```
                          ┌───────────────────────────┐
        Móvil / Web        │        FRONTEND           │
     (cliente, admin,      │  HTML + Tailwind + JS ESM │
      delivery)            │  multipágina por rol      │
                           └────────────┬──────────────┘
                                        │  HTTPS / JSON (fetch)
                                        │  JWT (Authorization: Bearer) + cookie refresh
                           ┌────────────▼──────────────┐
                           │        BACKEND API        │
                           │         FastAPI           │
                           │  api/ → services/ → repos │
                           └───┬───────────┬───────────┘
                               │           │
                 ┌─────────────▼──┐   ┌────▼─────────────┐
                 │   SQLite (WAL) │   │  storage/  (FS)  │
                 │  SQLAlchemy    │   │  comprobantes    │
                 └────────────────┘   └──────────────────┘
                               │
             ┌─────────────────┼─────────────────────────┐
             ▼                 ▼                         ▼
   GeocodingService      NotificationService        RouteService
   (Nominatim/Google)    (in-app → email/push)      (manual → OSRM/Google)
```

Reglas de dependencia entre capas (una sola dirección):

```
api  →  services  →  repositories  →  models (SQLAlchemy)
          ↓
      schemas (Pydantic)      core (config, security, errors, deps)
```

- `api/` no accede a la base directamente; solo llama a `services/`.
- `services/` contiene la lógica de negocio y orquesta `repositories/` + servicios externos.
- `repositories/` es el único lugar con queries. Cambiar de motor = cambiar aquí + connection string.
- Los servicios externos se usan **detrás de una interfaz** (`Protocol`/ABC) con implementación seleccionable por configuración.

---

## 4. Estructura de carpetas

```
Morfi Center/
├── backend/
│   ├── app/
│   │   ├── main.py                 # crea la app FastAPI, monta routers, middlewares, static
│   │   ├── core/
│   │   │   ├── config.py           # Settings (pydantic-settings)
│   │   │   ├── security.py         # hash, verify, JWT encode/decode
│   │   │   ├── errors.py           # excepciones de dominio + handlers
│   │   │   ├── logging.py
│   │   │   └── timezone.py         # helpers de fecha/hora
│   │   ├── db/
│   │   │   ├── session.py          # engine, SessionLocal, get_session()
│   │   │   ├── base.py             # DeclarativeBase + import de todos los modelos
│   │   │   └── seed.py             # datos semilla (idempotente)
│   │   ├── models/                 # SQLAlchemy — 1 archivo por dominio
│   │   │   ├── user.py  address.py  catalog.py  promotion.py  stock.py
│   │   │   ├── cart.py  order.py  payment.py  balance.py
│   │   │   ├── delivery.py  routing.py  shift.py  settings.py
│   │   │   ├── notification.py  audit.py
│   │   ├── schemas/                # Pydantic — request/response por dominio
│   │   ├── repositories/           # acceso a datos por agregado
│   │   ├── services/
│   │   │   ├── auth_service.py  user_service.py
│   │   │   ├── catalog_service.py  pricing_service.py  stock_service.py
│   │   │   ├── cart_service.py  order_service.py  order_state_machine.py
│   │   │   ├── payment_service.py  balance_service.py
│   │   │   ├── coverage_service.py  shipping_service.py  shift_service.py
│   │   │   ├── production_service.py
│   │   │   ├── driver_service.py  assignment_service.py  tracking_service.py
│   │   │   ├── notification_service.py
│   │   │   └── external/
│   │   │       ├── geocoding.py    # GeocodingProvider (Protocol) + NominatimProvider, GoogleProvider
│   │   │       ├── routing.py      # RouteProvider + ManualProvider, OsrmProvider
│   │   │       └── storage.py      # FileStorage + LocalFileStorage
│   │   └── api/
│   │       ├── deps.py             # get_current_user, require_role(...), get_session
│   │       └── routes/             # 1 router por módulo (ver §12)
│   ├── alembic/                    # env.py + versions/
│   ├── tests/
│   │   ├── conftest.py             # app + DB en memoria + fixtures de usuarios
│   │   ├── unit/                   # servicios de dominio
│   │   └── api/                    # endpoints
│   ├── data/                       # morfi.db  (gitignored)
│   ├── storage/
│   │   └── payment_proofs/         # (gitignored)
│   ├── .env.example
│   ├── requirements.txt
│   └── pyproject.toml              # ruff, black, pytest
│
├── frontend/
│   ├── index.html                 # Home cliente (estilo Artesanal · Cocina de Olla)
│   ├── pages/
│   │   ├── auth/     login.html  registro.html  recuperar.html
│   │   ├── cliente/  menu.html  producto.html  carrito.html  direccion.html
│   │   │             pago.html  pedidos.html  seguimiento.html  perfil.html
│   │   ├── admin/    dashboard.html  pedidos.html  validacion.html  produccion.html
│   │   │             categorias.html  productos.html  promociones.html
│   │   │             deliveries.html  logistica.html  configuracion.html
│   │   └── delivery/ inicio.html  ruta.html  parada.html  historial.html
│   ├── partials/                   # header, top-nav, bottom-nav, cart-bar, cards...
│   ├── assets/
│   │   ├── css/  base.css          # utilidades .paper .rule .drop .lift .foodX .grain
│   │   │        tailwind.css       # salida del build (o CDN en dev)
│   │   ├── js/
│   │   │   ├── api.js              # fetch wrapper (baseURL, token, refresh, errores)
│   │   │   ├── auth.js             # login/logout, guardas por rol, sesión
│   │   │   ├── ui.js               # inyección de partials, toasts, helpers DOM
│   │   │   ├── format.js           # moneda $00.000, fechas, tiempos
│   │   │   ├── countdown.js        # cuenta regresiva del turno
│   │   │   └── pages/<pantalla>.js
│   │   └── img/
│   ├── tailwind.config.js
│   └── postcss? (no requerido con Tailwind CLI standalone)
│
├── documentacion/
│   └── Fases/                       # documento de cierre de cada fase completada
├── deploy/
│   ├── nginx.morficenter.conf       # reverse proxy + TLS (plantilla, sin datos reales)
│   ├── morficenter-api.service      # unidad systemd para Uvicorn (plantilla)
│   └── DEPLOY.md                    # runbook de despliegue en el VPS Contabo (sin credenciales)
├── .github/
│   └── workflows/
│       └── deploy-backend.yml       # CD: push a master → SSH al VPS → pull + migrar + reiniciar
├── .claude/skills/morfi-frontend/  # sistema de diseño del front
└── .gitignore
```

`.gitignore` mínimo: `backend/data/*` + `!backend/data/.gitkeep`, `backend/storage/payment_proofs/*` + `!backend/storage/payment_proofs/.gitkeep` (ignora el **contenido**, no la carpeta — así el `.gitkeep` queda versionado y la carpeta existe en cualquier clone nuevo), `backend/.env`, `__pycache__/`, `*.pyc`, `.venv/`, `frontend/assets/css/tailwind.css` (si se genera por build).

---

## 5. Arquitectura del backend (capas)

### 5.1 `core/config.py` — Settings

Un único objeto `settings` (singleton) leído de `.env`. Ver §19 para el listado de variables.

### 5.2 `db/session.py`

```python
engine = create_engine(
    settings.database_url,                 # sqlite:///./data/morfi.db
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)

@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_con, _):
    cur = dbapi_con.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA busy_timeout=5000")
    cur.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

def get_session():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

### 5.3 `repositories/`

Una clase por agregado (`UserRepository`, `OrderRepository`, …). Recibe la `Session`. Expone métodos con intención de negocio (`get_active_products`, `list_orders_pending_validation`, `sum_reserved_stock(product_id)`). **Nada de SQL fuera de aquí.**

### 5.4 `services/`

Lógica de negocio. Transaccional a nivel de caso de uso. Lanza excepciones de dominio (`core/errors.py`), nunca `HTTPException`. Devuelve modelos u objetos de dominio; la conversión a schema Pydantic se hace en `api/`.

### 5.5 `api/routes/`

Routers finos: reciben request validado (Pydantic), resuelven dependencias (`get_current_user`, `require_role`), llaman a un service, devuelven un schema. Los errores de dominio se traducen a HTTP por handlers globales.

### 5.6 `api/deps.py`

```python
def get_current_user(token=Depends(oauth2_scheme), db=Depends(get_session)) -> User: ...
def require_role(*roles: Role):
    def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise ForbiddenError()
        return user
    return _dep
```

---

## 6. Modelo de datos físico (SQLite)

Convenciones:

- PK: `id INTEGER PRIMARY KEY AUTOINCREMENT` salvo indicación.
- Timestamps: `created_at`, `updated_at` `TEXT` ISO-8601 en **UTC** (`YYYY-MM-DDTHH:MM:SSZ`).
- Dinero: `INTEGER` en **centavos** (evita floats). Se muestra como `$00.000`.
- Booleanos: `INTEGER` 0/1.
- Enums: `TEXT` con `CHECK(col IN (...))`.
- Borrado: **lógico** (`status`/`is_active`) en catálogo y usuarios; físico solo en datos efímeros (`cart_items`, `driver_locations` antiguas).
- FKs con `ON DELETE RESTRICT` por defecto; `CASCADE` solo en hijos dependientes (`order_items`, `cart_items`, `product_images`).

### 6.1 Identidad y perfiles

```sql
CREATE TABLE users (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  first_name    TEXT NOT NULL,
  last_name     TEXT NOT NULL,
  email         TEXT NOT NULL UNIQUE,
  phone         TEXT,
  password_hash TEXT,                       -- NULL si solo login externo
  role          TEXT NOT NULL DEFAULT 'CUSTOMER'
                CHECK(role IN ('CUSTOMER','ADMIN','DELIVERY')),
  status        TEXT NOT NULL DEFAULT 'ACTIVE'
                CHECK(status IN ('ACTIVE','SUSPENDED','INACTIVE')),
  created_at    TEXT NOT NULL,
  updated_at    TEXT NOT NULL
);
CREATE INDEX ix_users_role ON users(role);

CREATE TABLE user_auth_providers (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  provider     TEXT NOT NULL CHECK(provider IN ('local','google')),
  provider_uid TEXT,                         -- 'sub' de Google; NULL para local
  linked_at    TEXT NOT NULL,
  UNIQUE(provider, provider_uid)
);
CREATE INDEX ix_uap_user ON user_auth_providers(user_id);

-- Perfil unificado (evita 3 tablas casi vacías; extensible)
CREATE TABLE user_profiles (
  user_id            INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  -- delivery
  vehicle_type       TEXT CHECK(vehicle_type IN ('moto','bici','auto','a_pie') OR vehicle_type IS NULL),
  capacity           INTEGER,               -- pedidos simultáneos sugeridos
  driver_status      TEXT CHECK(driver_status IN ('DISPONIBLE','NO_DISPONIBLE','EN_RUTA','INACTIVO') OR driver_status IS NULL),
  -- notas admin
  notes              TEXT,
  updated_at         TEXT NOT NULL
);
```

### 6.2 Direcciones y cobertura

```sql
CREATE TABLE addresses (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  alias         TEXT,                        -- 'Oficina', 'Casa'
  street        TEXT NOT NULL,
  number        TEXT,
  detail        TEXT,                        -- piso, dpto, referencia
  neighborhood  TEXT,                        -- barrio (normalizado)
  city          TEXT,
  lat           REAL,
  lng           REAL,
  geocoded_at   TEXT,
  is_default    INTEGER NOT NULL DEFAULT 0,
  created_at    TEXT NOT NULL,
  updated_at    TEXT NOT NULL
);
CREATE INDEX ix_addresses_user ON addresses(user_id);

CREATE TABLE delivery_zones (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  type         TEXT NOT NULL CHECK(type IN ('neighborhood','radius')),
  name         TEXT,                          -- nombre de barrio (type='neighborhood')
  radius_km    REAL,                          -- (type='radius')
  enabled      INTEGER NOT NULL DEFAULT 1,
  created_at   TEXT NOT NULL
);
```

### 6.3 Catálogo, stock, promociones

```sql
CREATE TABLE categories (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  name        TEXT NOT NULL,
  slug        TEXT NOT NULL UNIQUE,
  sort_order  INTEGER NOT NULL DEFAULT 0,
  is_active   INTEGER NOT NULL DEFAULT 1,
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
);

CREATE TABLE products (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  category_id  INTEGER NOT NULL REFERENCES categories(id),
  name         TEXT NOT NULL,
  description  TEXT,
  base_price   INTEGER NOT NULL,             -- centavos
  is_active    INTEGER NOT NULL DEFAULT 1,
  sort_order   INTEGER NOT NULL DEFAULT 0,
  created_at   TEXT NOT NULL,
  updated_at   TEXT NOT NULL
);
CREATE INDEX ix_products_category ON products(category_id);
CREATE INDEX ix_products_active ON products(is_active);

CREATE TABLE product_images (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id  INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  path        TEXT NOT NULL,                 -- ruta relativa en storage/ o assets/
  is_primary  INTEGER NOT NULL DEFAULT 0,
  sort_order  INTEGER NOT NULL DEFAULT 0
);

-- Stock por producto y por turno (permite historia y multi-turno futuro)
CREATE TABLE product_stock (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id     INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  shift_id       INTEGER REFERENCES shifts(id),      -- NULL = stock base/plantilla
  initial_qty    INTEGER NOT NULL DEFAULT 0,
  consumed_qty   INTEGER NOT NULL DEFAULT 0,         -- pedidos aprobados
  updated_at     TEXT NOT NULL,
  UNIQUE(product_id, shift_id)
);
-- 'reserved_qty' se calcula sumando stock_reservations vigentes (ver §9.3)

CREATE TABLE stock_reservations (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id   INTEGER NOT NULL REFERENCES products(id),
  order_id     INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  shift_id     INTEGER NOT NULL REFERENCES shifts(id),
  qty          INTEGER NOT NULL,
  status       TEXT NOT NULL DEFAULT 'HELD'
               CHECK(status IN ('HELD','COMMITTED','RELEASED')),
  expires_at   TEXT NOT NULL,
  created_at   TEXT NOT NULL
);
CREATE INDEX ix_resv_product_status ON stock_reservations(product_id, status);
CREATE INDEX ix_resv_expires ON stock_reservations(status, expires_at);

CREATE TABLE promotions (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id    INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  type          TEXT NOT NULL DEFAULT 'PROMO'
                CHECK(type IN ('PROMO','DAILY_SPECIAL')),
  promo_price   INTEGER NOT NULL,            -- centavos
  starts_at     TEXT NOT NULL,               -- UTC
  ends_at       TEXT NOT NULL,
  weekday       INTEGER,                     -- 0..6 opcional (para 'plato del día' recurrente)
  label         TEXT,                        -- texto promocional
  priority      INTEGER NOT NULL DEFAULT 0,  -- mayor gana si hay empate de fechas
  is_active     INTEGER NOT NULL DEFAULT 1,
  created_at    TEXT NOT NULL,
  updated_at    TEXT NOT NULL
);
CREATE INDEX ix_promo_product ON promotions(product_id);
CREATE INDEX ix_promo_window ON promotions(is_active, starts_at, ends_at);
```

> `daily_specials` de la spec conceptual se implementa como `promotions.type='DAILY_SPECIAL'` con `priority` alta y `label`/`weekday`. Una sola tabla, una sola regla de resolución de precio.

### 6.4 Turnos

```sql
CREATE TABLE shifts (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  service_date        TEXT NOT NULL,          -- 'YYYY-MM-DD' (local)
  service_type        TEXT NOT NULL DEFAULT 'LUNCH'
                      CHECK(service_type IN ('BREAKFAST','LUNCH','DINNER')),
  open_time           TEXT NOT NULL,          -- 'HH:MM' local
  close_time          TEXT NOT NULL,
  prep_eta            TEXT,
  dispatch_eta        TEXT,
  cancel_window_min   INTEGER NOT NULL DEFAULT 20,
  status              TEXT NOT NULL DEFAULT 'SCHEDULED'
                      CHECK(status IN ('SCHEDULED','OPEN','CLOSED','IN_PRODUCTION','DISPATCHING','FINISHED')),
  created_at          TEXT NOT NULL,
  updated_at          TEXT NOT NULL,
  UNIQUE(service_date, service_type)
);
```

### 6.5 Carrito

```sql
CREATE TABLE carts (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id     INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  updated_at  TEXT NOT NULL
);
CREATE TABLE cart_items (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  cart_id     INTEGER NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
  product_id  INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  qty         INTEGER NOT NULL CHECK(qty > 0),
  label_for   TEXT,                            -- "Para: Gustavo" (opcional)
  added_at    TEXT NOT NULL,
  UNIQUE(cart_id, product_id, label_for)
);
```

### 6.6 Pedidos

```sql
CREATE TABLE orders (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  code               TEXT NOT NULL UNIQUE,     -- 'MC-2026-000123'
  user_id            INTEGER NOT NULL REFERENCES users(id),
  shift_id           INTEGER NOT NULL REFERENCES shifts(id),
  address_id         INTEGER REFERENCES addresses(id),
  status             TEXT NOT NULL DEFAULT 'DRAFT'
                     CHECK(status IN ('DRAFT','PENDING_PAYMENT','PAYMENT_UNDER_REVIEW',
                       'PAYMENT_APPROVED','PAYMENT_REJECTED','CANCELLED','IN_PREPARATION',
                       'READY_FOR_PICKUP','ASSIGNED_TO_DELIVERY','OUT_FOR_DELIVERY',
                       'DELIVERED','DELIVERY_INCIDENT')),
  -- importes congelados al confirmar (centavos)
  subtotal           INTEGER NOT NULL DEFAULT 0,
  shipping_cost      INTEGER NOT NULL DEFAULT 0,
  discount_total     INTEGER NOT NULL DEFAULT 0,
  balance_applied    INTEGER NOT NULL DEFAULT 0,
  total              INTEGER NOT NULL DEFAULT 0,
  -- cobertura resuelta
  delivery_distance_km REAL,
  is_cancelable_at_creation INTEGER,           -- snapshot informativo
  notes              TEXT,
  created_at         TEXT NOT NULL,
  confirmed_at       TEXT,
  updated_at         TEXT NOT NULL
);
CREATE INDEX ix_orders_shift_status ON orders(shift_id, status);
CREATE INDEX ix_orders_user ON orders(user_id);

CREATE TABLE order_items (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id          INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  product_id        INTEGER NOT NULL REFERENCES products(id),
  product_name      TEXT NOT NULL,             -- congelado
  unit_price        INTEGER NOT NULL,          -- congelado (base o promo)
  is_promo_price    INTEGER NOT NULL DEFAULT 0,
  promotion_id      INTEGER REFERENCES promotions(id),
  qty               INTEGER NOT NULL CHECK(qty > 0),
  line_total        INTEGER NOT NULL,
  label_for         TEXT
);

CREATE TABLE order_status_history (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id     INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  from_status  TEXT,
  to_status    TEXT NOT NULL,
  actor_id     INTEGER REFERENCES users(id),   -- NULL = sistema
  reason       TEXT,
  created_at   TEXT NOT NULL
);
CREATE INDEX ix_osh_order ON order_status_history(order_id);
```

### 6.7 Pagos y comprobantes

```sql
CREATE TABLE payments (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id       INTEGER NOT NULL UNIQUE REFERENCES orders(id) ON DELETE CASCADE,
  method         TEXT NOT NULL DEFAULT 'transfer' CHECK(method IN ('transfer')),
  expected_amount INTEGER NOT NULL,             -- = orders.total al confirmar
  status         TEXT NOT NULL DEFAULT 'PENDING'
                 CHECK(status IN ('PENDING','UNDER_REVIEW','APPROVED','REJECTED')),
  validated_by   INTEGER REFERENCES users(id),
  validated_at   TEXT,
  admin_note     TEXT,
  created_at     TEXT NOT NULL,
  updated_at     TEXT NOT NULL
);

CREATE TABLE payment_proofs (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  payment_id   INTEGER NOT NULL REFERENCES payments(id) ON DELETE CASCADE,
  file_path    TEXT NOT NULL,                  -- storage/payment_proofs/<uuid>.<ext>
  mime_type    TEXT NOT NULL,
  file_size    INTEGER NOT NULL,
  uploaded_by  INTEGER NOT NULL REFERENCES users(id),
  created_at   TEXT NOT NULL
);
```

### 6.8 Saldo a favor

```sql
CREATE TABLE customer_balances (
  user_id     INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  balance     INTEGER NOT NULL DEFAULT 0,      -- centavos, >= 0
  updated_at  TEXT NOT NULL
);

CREATE TABLE balance_transactions (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type           TEXT NOT NULL CHECK(type IN ('credit','debit')),
  amount         INTEGER NOT NULL CHECK(amount > 0),
  origin         TEXT NOT NULL CHECK(origin IN ('cancellation','order_use','admin_adjustment')),
  order_id       INTEGER REFERENCES orders(id),
  balance_after  INTEGER NOT NULL,
  note           TEXT,
  created_at     TEXT NOT NULL,
  actor_id       INTEGER REFERENCES users(id)
);
CREATE INDEX ix_baltx_user ON balance_transactions(user_id);
```

### 6.9 Logística

```sql
CREATE TABLE delivery_assignments (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  shift_id     INTEGER NOT NULL REFERENCES shifts(id),
  driver_id    INTEGER NOT NULL REFERENCES users(id),
  status       TEXT NOT NULL DEFAULT 'DRAFT'
               CHECK(status IN ('DRAFT','ASSIGNED','IN_PROGRESS','COMPLETED')),
  created_at   TEXT NOT NULL,
  updated_at   TEXT NOT NULL,
  UNIQUE(shift_id, driver_id)
);

CREATE TABLE delivery_routes (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  assignment_id INTEGER NOT NULL UNIQUE REFERENCES delivery_assignments(id) ON DELETE CASCADE,
  provider      TEXT NOT NULL DEFAULT 'manual',
  total_distance_km REAL,
  total_eta_min INTEGER,
  computed_at   TEXT
);

CREATE TABLE delivery_stops (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  route_id      INTEGER NOT NULL REFERENCES delivery_routes(id) ON DELETE CASCADE,
  order_id      INTEGER NOT NULL REFERENCES orders(id),
  stop_index    INTEGER NOT NULL,               -- orden de visita (1..n)
  status        TEXT NOT NULL DEFAULT 'PENDING'
                CHECK(status IN ('PENDING','ARRIVED','DELIVERED','INCIDENT')),
  eta          TEXT,
  delivered_at  TEXT,
  incident_note TEXT,
  UNIQUE(route_id, order_id)
);
CREATE INDEX ix_stops_route ON delivery_stops(route_id, stop_index);

CREATE TABLE driver_locations (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  driver_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  assignment_id INTEGER REFERENCES delivery_assignments(id) ON DELETE CASCADE,
  lat          REAL NOT NULL,
  lng          REAL NOT NULL,
  recorded_at  TEXT NOT NULL
);
CREATE INDEX ix_driverloc_latest ON driver_locations(driver_id, recorded_at DESC);
```

### 6.10 Configuración, notificaciones, auditoría

```sql
CREATE TABLE system_settings (
  key         TEXT PRIMARY KEY,
  value       TEXT NOT NULL,                    -- JSON serializado
  value_type  TEXT NOT NULL DEFAULT 'json'
              CHECK(value_type IN ('json','string','int','bool')),
  description TEXT,
  updated_at  TEXT NOT NULL,
  updated_by  INTEGER REFERENCES users(id)
);

CREATE TABLE notifications (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type         TEXT NOT NULL,                   -- ver §7
  title        TEXT NOT NULL,
  body         TEXT,
  order_id     INTEGER REFERENCES orders(id),
  read_at      TEXT,
  created_at   TEXT NOT NULL
);
CREATE INDEX ix_notif_user ON notifications(user_id, read_at);

CREATE TABLE audit_log (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  actor_id     INTEGER REFERENCES users(id),
  action       TEXT NOT NULL,                   -- 'payment.approve', 'product.price_change', ...
  entity_type  TEXT NOT NULL,
  entity_id    TEXT NOT NULL,
  data         TEXT,                            -- JSON con before/after
  ip           TEXT,
  created_at   TEXT NOT NULL
);
CREATE INDEX ix_audit_entity ON audit_log(entity_type, entity_id);
```

### 6.11 Claves de `system_settings` (semilla)

| key | ejemplo (JSON) | uso |
|---|---|---|
| `shift.default` | `{"open":"08:00","close":"12:00","prep_eta":"12:15","dispatch_eta":"12:30","cancel_window_min":20,"weekdays":[1,2,3,4,5]}` | plantilla de turno |
| `timezone` | `"America/Argentina/Buenos_Aires"` | zona horaria de operación |
| `coverage.mode` | `"neighborhood_and_radius"` (`neighborhood` \| `radius` \| `neighborhood_and_radius` \| `off`) | reglas activas |
| `coverage.origin` | `{"lat":-34.63,"lng":-58.41}` | punto de origen para el radio |
| `shipping.mode` | `"by_distance"` (`free` \| `flat` \| `by_distance` \| `off`) | modalidad de envío |
| `shipping.flat_amount` | `200000` | costo fijo (centavos) |
| `shipping.tiers` | `[{"max_km":2,"amount":100000},{"max_km":4,"amount":150000},{"max_km":6,"amount":250000}]` | tabla por rango |
| `payment.transfer` | `{"alias":"MORFI.CENTER","holder":"...","bank":"...","cbu":"..."}` | datos de transferencia |
| `stock.reservation_ttl_min` | `40` | minutos que dura una reserva HELD |
| `promo.tie_breaker` | `"lowest_price"` (`lowest_price` \| `priority`) | resolución de promos simultáneas |
| `orders.code_prefix` | `"MC"` | prefijo de código de pedido |

---

## 7. Enumeraciones y catálogos

| Enum | Valores |
|---|---|
| `Role` | `CUSTOMER`, `ADMIN`, `DELIVERY` |
| `UserStatus` | `ACTIVE`, `SUSPENDED`, `INACTIVE` |
| `AuthProvider` | `local`, `google` |
| `OrderStatus` | `DRAFT`, `PENDING_PAYMENT`, `PAYMENT_UNDER_REVIEW`, `PAYMENT_APPROVED`, `PAYMENT_REJECTED`, `CANCELLED`, `IN_PREPARATION`, `READY_FOR_PICKUP`, `ASSIGNED_TO_DELIVERY`, `OUT_FOR_DELIVERY`, `DELIVERED`, `DELIVERY_INCIDENT` |
| `PaymentStatus` | `PENDING`, `UNDER_REVIEW`, `APPROVED`, `REJECTED` |
| `PromotionType` | `PROMO`, `DAILY_SPECIAL` |
| `ReservationStatus` | `HELD`, `COMMITTED`, `RELEASED` |
| `ShiftStatus` | `SCHEDULED`, `OPEN`, `CLOSED`, `IN_PRODUCTION`, `DISPATCHING`, `FINISHED` |
| `DriverStatus` | `DISPONIBLE`, `NO_DISPONIBLE`, `EN_RUTA`, `INACTIVO` |
| `ZoneType` | `neighborhood`, `radius` |
| `ShippingMode` | `free`, `flat`, `by_distance`, `off` |
| `CoverageMode` | `neighborhood`, `radius`, `neighborhood_and_radius`, `off` |
| `BalanceTxnType` | `credit`, `debit` |
| `BalanceOrigin` | `cancellation`, `order_use`, `admin_adjustment` |
| `NotificationType` | `order_created`, `proof_received`, `payment_approved`, `payment_rejected`, `order_cancelled`, `balance_credited`, `order_in_preparation`, `order_ready`, `order_out_for_delivery`, `order_delivered`, `delivery_incident`, `validation_critical` |
| `AssignmentStatus` | `DRAFT`, `ASSIGNED`, `IN_PROGRESS`, `COMPLETED` |
| `StopStatus` | `PENDING`, `ARRIVED`, `DELIVERED`, `INCIDENT` |
| `SettingValueType` | `json`, `string`, `int`, `bool` |

> `AssignmentStatus`, `StopStatus` y `SettingValueType` se agregan a este catálogo para que coincidan con los `CHECK` de `delivery_assignments.status`, `delivery_stops.status` y `system_settings.value_type` en §6 (no estaban listados en versiones anteriores de esta tabla, aunque sí existían como `CHECK` en el modelo físico).

Se definen como `str, Enum` de Python en `app/core/enums.py` y se reutilizan en modelos, schemas y checks.

---

## 8. Máquina de estados del pedido

Implementada en `services/order_state_machine.py` como un diccionario de transiciones + guardas por rol. Ninguna transición fuera del mapa es válida.

```
DRAFT ──confirm(CUSTOMER)──▶ PENDING_PAYMENT
DRAFT ──abandon/expire──▶ CANCELLED

PENDING_PAYMENT ──upload_proof/report(CUSTOMER)──▶ PAYMENT_UNDER_REVIEW
PENDING_PAYMENT ──approve(ADMIN)──▶ PAYMENT_APPROVED          (pago verificado sin comprobante)
PENDING_PAYMENT ──cancel(CUSTOMER dentro de ventana | ADMIN | expire reserva)──▶ CANCELLED

PAYMENT_UNDER_REVIEW ──approve(ADMIN)──▶ PAYMENT_APPROVED
PAYMENT_UNDER_REVIEW ──reject(ADMIN)──▶ PAYMENT_REJECTED
PAYMENT_UNDER_REVIEW ──cancel(CUSTOMER dentro de ventana | ADMIN)──▶ CANCELLED

PAYMENT_REJECTED ──reupload_proof(CUSTOMER)──▶ PAYMENT_UNDER_REVIEW
PAYMENT_REJECTED ──cancel(CUSTOMER | ADMIN)──▶ CANCELLED

PAYMENT_APPROVED ──start_production(ADMIN)──▶ IN_PREPARATION
PAYMENT_APPROVED ──cancel(ADMIN excepcional)──▶ CANCELLED

IN_PREPARATION ──mark_ready(ADMIN)──▶ READY_FOR_PICKUP
READY_FOR_PICKUP ──assign(ADMIN)──▶ ASSIGNED_TO_DELIVERY
ASSIGNED_TO_DELIVERY ──start_route(DELIVERY)──▶ OUT_FOR_DELIVERY
OUT_FOR_DELIVERY ──deliver(DELIVERY)──▶ DELIVERED
OUT_FOR_DELIVERY ──report_incident(DELIVERY)──▶ DELIVERY_INCIDENT
DELIVERY_INCIDENT ──retry(DELIVERY|ADMIN)──▶ OUT_FOR_DELIVERY
DELIVERY_INCIDENT ──resolve_ok(ADMIN)──▶ DELIVERED
DELIVERY_INCIDENT ──resolve_cancel(ADMIN)──▶ CANCELLED
```

Efectos colaterales de cada transición (los ejecuta el service, en la misma transacción):

| Transición | Efectos |
|---|---|
| `DRAFT→PENDING_PAYMENT` | crea `order_items` con precios congelados, crea `stock_reservations` HELD, crea `payments` (expected_amount=total), aplica saldo (`balance_transactions` debit), registra historia, notifica `order_created` |
| `*→PAYMENT_APPROVED` | `payments.status=APPROVED`, reservas HELD→COMMITTED, `product_stock.consumed_qty += qty`, audit `payment.approve`, notifica `payment_approved` |
| `*→PAYMENT_REJECTED` | `payments.status=REJECTED`, audit, notifica `payment_rejected` (reservas siguen HELD hasta TTL o cancelación) |
| `*→CANCELLED` | reservas → RELEASED; si `consumed` (venía de APPROVED) revertir `consumed_qty`; si hubo pago aprobado → `balance` credit por lo pagado; si hubo saldo aplicado no consumido → devolver; notifica `order_cancelled` (+ `balance_credited`) |
| `PAYMENT_APPROVED→IN_PREPARATION` | entra a producción consolidada |
| `→DELIVERED` | `delivery_stops.status=DELIVERED`, `delivered_at`, notifica |

---

## 9. Lógica de negocio (servicios de dominio)

### 9.1 PricingService — precio vigente de un producto

```
resolve_unit_price(product, at: datetime) -> (price, is_promo, promotion_id|None)
  candidates = promotions activas de product con starts_at <= at <= ends_at
               y (weekday nulo o == at.weekday)
  si no hay candidates -> (product.base_price, False, None)
  si promo.tie_breaker == 'priority':  elegir mayor priority, desempate menor precio
  si 'lowest_price' (default):         elegir menor promo_price
  devolver ese precio si < base_price, si no base_price
```

Se aplica: al mostrar catálogo, al agregar al carrito (solo display), y **de forma vinculante al confirmar el pedido** (congela `order_items.unit_price`).

### 9.2 CoverageService — ¿se entrega en esta dirección?

```
check(address) -> CoverageResult(ok, distance_km, reason)
  if coverage.mode == 'off': return ok=True, distance=None
  if address.lat is None: geocode(address)  # GeocodingProvider
  distance_km = haversine(coverage.origin, address)
  neigh_ok  = address.neighborhood in {z.name for z in zones if type=neighborhood and enabled}
  radius_ok = distance_km <= max(z.radius_km for z in zones if type=radius and enabled)
  mode:
    'neighborhood'             -> ok = neigh_ok
    'radius'                   -> ok = radius_ok
    'neighborhood_and_radius'  -> ok = neigh_ok and radius_ok
  reason = 'out_of_neighborhood' | 'out_of_radius' | None
```

### 9.3 StockService — reserva con vencimiento (resuelto bajo demanda, sin job)

```
_release_expired(product):
  # se corre al principio de available() y de reserve() — nunca aparte, nunca por sí solo
  reservations HELD de product con expires_at < now -> RELEASED
  para cada una: si el pedido sigue en PENDING_PAYMENT/PAYMENT_UNDER_REVIEW sin comprobante,
                 pasarlo a CANCELLED (reason='reservation_expired') y notificar al cliente

available(product, shift):
  _release_expired(product)
  return product_stock.initial_qty
       - sum(reservations HELD vigentes)      # ya sin las vencidas
       - product_stock.consumed_qty

reserve(order, items, shift):
  for item: _release_expired(item.product)
  for item: if available(item.product) < item.qty -> raise OutOfStock
  crear stock_reservations(status=HELD, expires_at = now + stock.reservation_ttl_min)

commit(order):   reservations HELD -> COMMITTED ; consumed_qty += qty
release(order):  reservations HELD|COMMITTED -> RELEASED ; si COMMITTED: consumed_qty -= qty
```

**Sin job `reservation_expiry`.** No hay nada corriendo en segundo plano contando los 60 segundos: la limpieza de reservas vencidas pasa **como primer paso** de `available()`/`reserve()`, así que se ejecuta exactamente cuando hace falta — cuando alguien consulta stock o intenta reservar. Si nadie consulta ese producto, no hay reservas fantasma bloqueando nada (nadie las está mirando); en cuanto alguien lo hace, la reserva vencida se libera ahí mismo, antes de devolver la respuesta.

### 9.4 ShippingService — costo de envío

```
quote(distance_km) -> amount (centavos)
  mode 'off' | 'free'  -> 0
  mode 'flat'          -> shipping.flat_amount
  mode 'by_distance'   -> primer tier con distance_km <= tier.max_km ; si ninguno -> último tier
```

Se calcula tras validar cobertura y se **congela** en `orders.shipping_cost` al confirmar.

### 9.5 CartService → checkout

```
build_summary(user) -> { items[], subtotal, shipping(nullable hasta tener dirección),
                         balance_available, estimated_total }
confirm(user, address_id, use_balance: bool|amount):
  guard: shift OPEN y now < close_time
  guard: address válida (CoverageService.ok)
  guard: stock disponible para todos los items
  resolver precios (PricingService) -> items congelados
  subtotal = sum(line_total)
  shipping = ShippingService.quote(distance)
  balance_applied = min(balance, subtotal + shipping)   # si use_balance
  total = subtotal + shipping - balance_applied
  crear order + order_items ; StockService.reserve ; crear payment
  is_cancelable_at_creation = now <= close_time - cancel_window_min
  transición DRAFT->PENDING_PAYMENT ; vaciar carrito
  return order + datos de transferencia (payment.transfer)
```

### 9.6 CancellationService

```
can_cancel(order, now) ->
  order.status in {PENDING_PAYMENT, PAYMENT_UNDER_REVIEW, PAYMENT_REJECTED}
  and now <= shift.close_time - shift.cancel_window_min
cancel_by_customer(order): guard can_cancel ; state -> CANCELLED (efectos §8)
cancel_by_admin(order, reason): sin restricción de ventana ; state -> CANCELLED
```

### 9.7 BalanceService

```
credit(user, amount, origin, order, actor) -> balance += amount ; balance_transactions(credit)
debit(user, amount, origin='order_use', order) -> guard balance >= amount ; balance -= amount ; (debit)
```

Uso parcial permitido. No transferible. Sin vencimiento (v1).

### 9.8 ProductionService

```
consolidated(shift, include_pending=False):
  base = order_items de orders con status >= PAYMENT_APPROVED (y no CANCELLED)
  group by product  -> { product, qty }              # consolidado por producto
  group by category -> { category, qty }             # consolidado por categoría
  detail            -> por pedido (cliente, items)
  si include_pending: sección aparte con PENDING/UNDER_REVIEW (informativo)
```

### 9.9 ShiftService — todo se resuelve bajo demanda, sin job de fondo

```
resolve_window(shift) -> (open_at_utc, close_at_utc, cancel_deadline_utc)
  convierte open_time/close_time/cancel_window_min (hora local, texto 'HH:MM')
  a instantes UTC, usando system_settings.timezone y shift.service_date.

current_status(shift, now=now_utc()) -> SCHEDULED | OPEN | CLOSED
  se calcula en el momento a partir de resolve_window(shift) — nunca se
  guarda, nunca lo cambia un proceso de fondo. Dos llamadas con el mismo
  `now` siempre dan el mismo resultado (es una función pura).

is_ordering_open(shift, now) -> current_status(shift, now) == OPEN

ensure_today_shift(): si no existe el shift de hoy (según shift.default y
  weekdays), lo crea. Se invoca al principio de cualquier flujo que
  necesite "el turno de hoy" (GET /shift/current, crear un pedido, abrir
  el panel admin) — no hace falta que corra a una hora fija; alguien
  visitando la página después de medianoche lo dispara solo.

on_shift_closed(shift): efecto de **una sola vez** al cerrar (congelar
  `product_stock` del turno, marcar los pedidos sin validar como
  críticos) — se ejecuta la primera vez que algún request detecta
  `current_status(shift, now) == CLOSED` y todavía no se aplicó (una
  columna/flag en `shifts` evita repetirlo si dos requests llegan casi
  a la vez). No es un job: lo dispara el primer request que consulta el
  turno después de la hora de cierre — sea un cliente o el propio admin.

to_production(shift): acción **manual del admin** (nunca automática) —
  decide cuándo arrancar a cocinar. PAYMENT_APPROVED -> IN_PREPARATION
  (masivo, sobre los pedidos de ese turno).
```

### 9.10 AssignmentService / TrackingService

```
assign(shift, driver, order_ids): crea/actualiza delivery_assignment + route + stops (stop_index manual)
reorder(route, order): reordena stop_index (o RouteProvider.optimize -> nuevo orden)
start_route(assignment): assignment IN_PROGRESS ; driver.status EN_RUTA ; stops.order -> OUT_FOR_DELIVERY
push_location(driver, lat, lng): inserta driver_locations (solo si assignment IN_PROGRESS)
  ; de paso, borra las ubicaciones de ese repartidor con más de 7 días (higiene de
  ; datos oportunista — sin job dedicado, ver §10)
customer_view(order): { status, stop_index, stops_before = count(pending antes), eta }  # sin datos de terceros
```

---

## 10. Resolución bajo demanda (sin tareas programadas de fondo)

**Decisión de diseño:** el proyecto no tiene ningún proceso corriendo en segundo plano vigilando el reloj (nada de `APScheduler`, ni `jobs/`, ni un *worker* aparte). Todo lo que antes se pensaba como un *job* con una frecuencia fija se resuelve **en el momento en que un request lo necesita**, calculando contra la hora actual:

| Antes (job con frecuencia) | Ahora (bajo demanda) | Dónde vive |
|---|---|---|
| `shift_open` / `shift_close` cada 1 min | `ShiftService.current_status(shift, now)` — se calcula en cada request que pregunta por el turno | §9.9 |
| `ensure_shift` diario 00:05 | `ShiftService.ensure_today_shift()` — se dispara con el primer request del día que necesita el turno de hoy | §9.9 |
| `reservation_expiry` cada 60 s | `StockService.available()`/`.reserve()` liberan las reservas vencidas como primer paso, antes de calcular disponibilidad | §9.3 |
| `driver_locations_prune` diario | se borran ubicaciones de más de 7 días como parte de `push_location()` (al insertar una nueva, de paso se limpian las viejas de ese repartidor) — sin urgencia de horario, es solo higiene de datos | §9.10 |

**Por qué:** ninguna de estas reglas necesita dispararse en un segundo exacto sin que haya nadie mirando — si nadie visita la app a la medianoche, tampoco hay nadie esperando que el turno haya cambiado de estado en ese instante. La primera visita del día (de un cliente o del admin) dispara el cálculo, y el resultado es idéntico al que hubiera dado un job seguido al segundo. Esto evita un componente de infraestructura entero (el *scheduler*) sin perder ninguna regla de negocio.

**La única salvedad:** los efectos de una sola vez (como congelar el stock al cerrar el turno) necesitan una marca para no repetirse — ver `on_shift_closed` en §9.9. No hace falta un *lock* distribuido tipo *cron*: alcanza con una columna/flag y una escritura idempotente (si dos requests llegan casi a la vez, el segundo encuentra el flag ya puesto y no hace nada).

**Si en el futuro hiciera falta algo realmente asíncrono** (por ejemplo, mandar un mail o una notificación push a las 12:00 en punto aunque nadie esté navegando), ahí sí tendría sentido sumar un *scheduler* — pero sería una adición puntual para ese caso, no una pieza estructural del proyecto.

---

## 11. API REST — convenciones

- Base URL: `/, api/v1`. Ej.: `POST /api/v1/orders`.
- Formato: JSON. `Content-Type: application/json` (salvo subida de comprobante: `multipart/form-data`).
- Autenticación: `Authorization: Bearer <access_token>`. Refresh vía cookie httpOnly.
- Fechas en respuestas: ISO-8601 UTC. El front convierte a `timezone` para mostrar.
- Dinero en respuestas: entero en centavos + string formateado opcional (`total`, `total_display`).
- Paginación: `?page=1&page_size=20` → `{ "items": [...], "page":1, "page_size":20, "total": 134 }`.
- Filtros: query params explícitos (`?status=PENDING_PAYMENT&shift_id=3`).
- Idempotencia en `confirm`/`approve`: si el recurso ya está en el estado destino, `200` con el recurso (no error).
- Errores: ver §20. Siempre `{ "error": { "code", "message", "details" } }`.
- Documentación viva: **OpenAPI** en `/api/docs` (Swagger) y `/api/openapi.json`. Es el contrato de referencia entre front y back.
- CORS: en dev, `http://localhost:5500`. En prod, mismo origen (front servido por FastAPI).

---

## 12. API REST — endpoints por módulo

Rol requerido: `—` público · `C` customer · `A` admin · `D` delivery · `auth` cualquier usuario logueado.

### Auth (`/api/v1/auth`)
| Método | Ruta | Rol | Descripción |
|---|---|---|---|
| POST | `/register` | — | Alta con cuenta propia (crea CUSTOMER + carrito + balance) |
| POST | `/login` | — | Email + password → access token + set-cookie refresh |
| POST | `/refresh` | cookie | Nuevo access token desde refresh cookie |
| POST | `/logout` | auth | Invalida refresh (borra cookie / lista de revocación) |
| GET | `/google/login` | — | Redirección a Google (OAuth2) |
| GET | `/google/callback` | — | Callback: vincula/crea usuario, emite tokens |
| POST | `/password/forgot` | — | Envía email de recuperación (token temporal) |
| POST | `/password/reset` | — | Cambia contraseña con token |
| GET | `/me` | auth | Datos del usuario actual + rol + saldo |

### Usuarios / perfil (`/api/v1/users`)
| GET | `/me/profile` | auth | Perfil |
| PATCH | `/me/profile` | auth | Editar nombre, teléfono |
| GET | `/me/addresses` · POST · PATCH `/{id}` · DELETE `/{id}` | C | CRUD de direcciones |
| POST | `/me/addresses/{id}/validate` | C | Geocodifica + valida cobertura + cotiza envío |
| GET | `/` `?role=` | A | Listado de usuarios |
| POST | `/` | A | Crear ADMIN / DELIVERY |
| PATCH | `/{id}` | A | Editar rol/estado |

### Catálogo (`/api/v1/catalog`)
| GET | `/categories` | — | Categorías activas (público) / todas (`?all=true`, A) |
| POST · PATCH `/{id}` · POST `/reorder` | A | Gestión de categorías |
| GET | `/products` `?category_id=&search=` | — | Productos activos con **precio vigente resuelto** y stock disponible |
| GET | `/products/{id}` | — | Detalle |
| POST · PATCH `/{id}` · DELETE `/{id}` | A | Gestión de productos |
| PUT | `/products/{id}/stock` | A | Set `initial_qty` del turno |
| POST | `/products/{id}/images` (multipart) · DELETE `/images/{id}` | A | Imágenes |

### Promociones (`/api/v1/promotions`)
| GET | `/` `?active=true` | — / A | Listado |
| GET | `/daily-special` | — | Plato(s) del día vigentes (para el home) |
| POST · PATCH `/{id}` · DELETE `/{id}` | A | Gestión (PROMO y DAILY_SPECIAL) |

### Turno (`/api/v1/shift`)
| GET | `/current` | — | Estado del turno actual: `status`, `open_time`, `close_time`, `now`, `seconds_to_close`, `cancel_deadline`, `prep_eta` |
| GET | `/` `?date=` | A | Turnos |
| PATCH | `/{id}` | A | Ajustar horarios/ventana del turno |
| POST | `/{id}/transition` | A | `open` / `close` / `to_production` manual |

### Carrito (`/api/v1/cart`) — rol `C`
| GET | `/` | Carrito + resumen (subtotal, saldo disponible) |
| POST | `/items` | Agrega `{product_id, qty, label_for?}` (valida stock y turno) |
| PATCH | `/items/{id}` | Cambia qty |
| DELETE | `/items/{id}` | Quita ítem |
| DELETE | `/` | Vacía |

### Pedidos (`/api/v1/orders`)
| POST | `/` | C | **Confirma** pedido: `{address_id, use_balance}` → crea order, reserva stock, congela importes, devuelve datos de transferencia |
| GET | `/` | C | Mis pedidos (`?status=`) |
| GET | `/{id}` | C (propio) / A / D (asignado) | Detalle |
| GET | `/{id}/tracking` | C (propio) | Seguimiento (estado, paradas previas, ETA) — sin datos de terceros |
| POST | `/{id}/cancel` | C | Cancela si `can_cancel` |
| GET | `/admin` | A | Todos, con filtros (`?status=&shift_id=&q=`) |
| POST | `/{id}/transition` | A / D | Transición de estado permitida por rol (mark_ready, assign, start_route, deliver, incident, …) |
| GET | `/admin/validation-queue` | A | Cola priorizada (sin validar; críticos primero) |

### Pagos (`/api/v1/payments`)
| GET | `/order/{order_id}` | C (propio) / A | Estado del pago + datos de transferencia |
| POST | `/order/{order_id}/proofs` (multipart) | C / A | Sube comprobante (jpg/jpeg/png/webp/pdf, ≤ 8 MB) → `PENDING→UNDER_REVIEW` |
| GET | `/proofs/{id}` | A / C (propio) | **Descarga autorizada** del archivo (stream; nunca URL pública) |
| POST | `/order/{order_id}/approve` | A | Aprueba pago (con o sin comprobante) + nota |
| POST | `/order/{order_id}/reject` | A | Rechaza + motivo |
| POST | `/order/{order_id}/mark-review` | A | Vuelve a pendiente de resolución + nota |

### Saldo a favor (`/api/v1/balance`)
| GET | `/me` | C | Saldo actual + movimientos |
| POST | `/adjust` | A | Ajuste manual `{user_id, type, amount, note}` |

### Cobertura y envío (`/api/v1/coverage`)
| POST | `/check` | auth | `{lat,lng} | {address}` → `{ok, distance_km, reason, shipping_quote}` |
| GET | `/zones` · POST · PATCH `/{id}` · DELETE `/{id}` | A | Gestión de barrios/radios |
| GET | `/config` · PUT `/config` | A | `coverage.mode`, `coverage.origin`, `shipping.*` |

### Producción (`/api/v1/production`) — rol `A`
| GET | `/shift/{id}/by-product` | Consolidado por producto |
| GET | `/shift/{id}/by-category` | Consolidado por categoría |
| GET | `/shift/{id}/detail` | Detalle por pedido |

### Deliveries y logística (`/api/v1`)
| GET | `/drivers` · POST · PATCH `/{id}` | A | Gestión de repartidores |
| PATCH | `/drivers/me/status` | D | Cambia disponibilidad propia |
| GET | `/assignments` `?shift_id=` | A | Asignaciones del turno |
| POST | `/assignments` | A | `{shift_id, driver_id, order_ids[]}` |
| POST | `/assignments/{id}/route/reorder` | A | Reordena paradas (`order_ids[]` o `optimize:true`) |
| GET | `/assignments/me` | D | Mi ruta y paradas ordenadas |
| POST | `/assignments/{id}/start` | D | Inicia ruta |
| POST | `/stops/{id}/deliver` · `/stops/{id}/incident` | D | Marca entrega / incidencia |
| POST | `/drivers/me/location` | D | `{lat,lng}` (solo con ruta activa) |
| GET | `/assignments/{id}/location` | A | Última ubicación del repartidor |

### Notificaciones (`/api/v1/notifications`) — rol `auth`
| GET | `/` `?unread=true` | Lista |
| POST | `/{id}/read` · POST `/read-all` | Marca leídas |

### Configuración (`/api/v1/settings`) — rol `A`
| GET | `/` · PUT `/{key}` | Lee/actualiza `system_settings` |

Ejemplos representativos:

```jsonc
// POST /api/v1/auth/login
{ "email": "cliente@test.com", "password": "cliente123" }
// 200
{ "access_token": "eyJ...", "token_type": "bearer", "expires_in": 900,
  "user": { "id": 5, "first_name": "Gustavo", "role": "CUSTOMER" } }
// + Set-Cookie: mc_refresh=<jwt>; HttpOnly; Secure; SameSite=Lax; Path=/api/v1/auth
```

```jsonc
// POST /api/v1/orders
{ "address_id": 12, "use_balance": true }
// 201
{ "order": { "id": 88, "code": "MC-2026-000088", "status": "PENDING_PAYMENT",
    "subtotal": 3180000, "shipping_cost": 150000, "balance_applied": 500000,
    "total": 2830000, "total_display": "$28.300",
    "is_cancelable_at_creation": true },
  "transfer": { "alias": "MORFI.CENTER", "holder": "…", "bank": "…", "amount_display": "$28.300" } }
```

```jsonc
// POST /api/v1/payments/order/88/approve
{ "note": "Transferencia identificada en homebanking 11:32" }
// 200 -> order.status = PAYMENT_APPROVED
```

```jsonc
// GET /api/v1/shift/current  -> 200
{ "status": "OPEN", "service_date": "2026-09-09",
  "open_time": "08:00", "close_time": "12:00",
  "now": "2026-09-09T13:18:07Z", "seconds_to_close": 6113,
  "cancel_deadline": "2026-09-09T14:40:00Z", "prep_eta": "12:15" }
```

---

## 13. Autenticación y autorización

### 13.1 Tokens

| Token | Vida | Transporte | Contenido |
|---|---|---|---|
| Access | 15 min | Header `Authorization: Bearer` | `sub` (user_id), `role`, `exp`, `iat`, `type=access` |
| Refresh | 7 días | Cookie httpOnly `mc_refresh`, `Secure`, `SameSite=Lax`, `Path=/api/v1/auth` | `sub`, `exp`, `type=refresh`, `jti` |

- Firma HS256 con `JWT_SECRET` (≥ 32 bytes, en `.env`).
- Revocación de refresh: tabla ligera `revoked_tokens(jti, expires_at)` o rotación (`jti` nuevo en cada `/refresh`, invalidando el anterior).
- El front guarda el **access token en memoria** (variable del módulo `auth.js`), nunca en `localStorage`. Al recargar, hace `/auth/refresh` (usa la cookie) para recuperar sesión.

### 13.2 Flujo local

```
register -> crea user(role=CUSTOMER, password_hash=bcrypt) + user_auth_providers(local) + cart + customer_balance
login    -> verify(password, hash) -> emite access + set-cookie refresh
```

### 13.3 Flujo Google (OIDC)

```
GET /auth/google/login  -> redirect a Google (scope: openid email profile, state, PKCE)
GET /auth/google/callback?code=...
   -> Authlib intercambia code por id_token
   -> valida id_token, extrae sub, email, given_name, family_name
   -> si existe user_auth_providers(google, sub): login
      si existe user por email: vincula provider google a ese user
      si no: crea user(role=CUSTOMER, password_hash=NULL) + provider + cart + balance
   -> emite access + refresh, redirige al front (/#/post-login con el token o set-cookie + fetch /me)
```

### 13.4 RBAC

- `get_current_user`: decodifica access token, carga `User`, valida `status=ACTIVE`.
- `require_role(*roles)`: dependencia que corta con `403` si el rol no coincide.
- Propiedad del recurso: además del rol, los services validan pertenencia (`order.user_id == current_user.id` para CUSTOMER; `stop.route.assignment.driver_id == current_user.id` para DELIVERY).
- **Toda** verificación ocurre en el backend. El front oculta/muestra por UX pero nunca es la barrera.

---

## 14. Servicios externos

Cada uno detrás de una interfaz (`typing.Protocol`) en `services/external/`. Implementación elegida por `.env`.

### 14.1 GeocodingProvider
```python
class GeocodingProvider(Protocol):
    def geocode(self, query: str) -> GeoPoint | None: ...
```
- `NominatimProvider` (OpenStreetMap, gratis, requiere `User-Agent` y respetar rate limit; cachear resultados en `addresses.lat/lng`).
- `GoogleGeocodingProvider` (requiere `GOOGLE_MAPS_API_KEY`).
- Selección: `GEOCODING_PROVIDER=nominatim|google`.
- Distancia: **Haversine** local (no requiere proveedor) para el radio de cobertura.

### 14.2 RouteProvider
```python
class RouteProvider(Protocol):
    def optimize(self, origin: GeoPoint, stops: list[GeoPoint]) -> list[int]: ...  # nuevo orden de índices
```
- `ManualProvider` (v1): devuelve el orden tal cual / por cercanía nearest-neighbor local.
- `OsrmProvider` / `GoogleDirectionsProvider` (fase logística).

### 14.3 NotificationChannel
```python
class NotificationChannel(Protocol):
    def send(self, user: User, notif: Notification) -> None: ...
```
- `InAppChannel` (v1): inserta en tabla `notifications`.
- `EmailChannel`, `PushChannel` (fases posteriores). El `NotificationService` puede enrutar a varios canales según `NotificationType`.

### 14.4 FileStorage
```python
class FileStorage(Protocol):
    def save(self, data: bytes, filename: str, subdir: str) -> str: ...   # devuelve path lógico
    def open(self, path: str) -> BinaryIO: ...
```
- `LocalFileStorage` (v1): `backend/storage/<subdir>/<uuid>.<ext>`. Nunca servido como estático; solo por endpoint autorizado que hace `StreamingResponse`.
- Punto de extensión: `S3Storage`.

---

## 15. Arquitectura del frontend

### 15.1 Enfoque

- **Multipágina**: un `.html` por pantalla, agrupadas por rol en `frontend/pages/`. Sin router SPA, sin bundler de JS.
- **Parciales** comunes (`header`, `top-nav`, `bottom-nav`, `cart-bar`, cards) en `frontend/partials/`, insertados en runtime por `ui.js` (`fetch` + `innerHTML` + hidratación) — o copiados en el paso de build.
- **JS por página** en `assets/js/pages/<pantalla>.js` (ES module), que importa utilidades compartidas.
- **Estado**: mínimo y local. El carrito y la sesión se leen del backend; se cachean en memoria y se refrescan tras cada mutación. `localStorage` solo para preferencias no críticas (última categoría vista, colapsables).

### 15.2 `assets/js/api.js` — cliente HTTP

```js
const BASE = window.__MC_API__ ?? '/api/v1';
let accessToken = null;                          // en memoria
export const setToken = t => { accessToken = t; };

async function request(path, { method='GET', body, form, auth=true, retry=true } = {}) {
  const headers = {};
  if (auth && accessToken) headers.Authorization = `Bearer ${accessToken}`;
  let payload;
  if (form) payload = form;                       // FormData (comprobantes)
  else if (body !== undefined) { headers['Content-Type']='application/json'; payload = JSON.stringify(body); }

  const res = await fetch(`${BASE}${path}`, { method, headers, body: payload, credentials: 'include' });

  if (res.status === 401 && retry && auth) {      // access vencido -> refresh -> reintento
    const ok = await tryRefresh();
    if (ok) return request(path, { method, body, form, auth, retry:false });
  }
  const data = res.status === 204 ? null : await res.json().catch(()=>null);
  if (!res.ok) throw new ApiError(res.status, data?.error);
  return data;
}

async function tryRefresh() {
  try {
    const r = await fetch(`${BASE}/auth/refresh`, { method:'POST', credentials:'include' });
    if (!r.ok) return false;
    const d = await r.json(); setToken(d.access_token); return true;
  } catch { return false; }
}

export const api = {
  get:  (p,o)      => request(p, {...o, method:'GET'}),
  post: (p,body,o) => request(p, {...o, method:'POST', body}),
  patch:(p,body,o) => request(p, {...o, method:'PATCH', body}),
  del:  (p,o)      => request(p, {...o, method:'DELETE'}),
  upload:(p,form)  => request(p, { method:'POST', form }),
};
```

### 15.3 `assets/js/auth.js`

```js
import { api, ApiError, refreshSession, setToken } from './api.js';

const LOGIN_URL = '/pages/auth/login.html';
let currentUser = null;

export function getUser() { return currentUser; }

export async function bootstrapSession() {            // al cargar cualquier página
  try {
    if (!(await refreshSession())) return null;
    currentUser = await api.get('/auth/me');
    return currentUser;
  } catch (err) {
    if (err instanceof ApiError) { currentUser = null; return null; }
    throw err;
  }
}

export async function login(email, password) {
  const d = await api.post('/auth/login', { email, password }, { auth: false });
  setToken(d.access_token); currentUser = d.user; return currentUser;
}

export async function logout() {
  try { await api.post('/auth/logout'); } catch {}
  setToken(null); currentUser = null; location.href = '/';
}

// roles === undefined -> "cualquier usuario logueado" (así se gatean las
// páginas de cliente sin atarlas a un rol puntual). roles: string | string[].
export async function requireRole(roles) {
  const me = await bootstrapSession();
  const allowed = roles == null || [].concat(roles).includes(me?.role);
  if (!me || !allowed) {
    location.href = `${LOGIN_URL}?next=${encodeURIComponent(location.pathname)}`;
    throw new Error('no autorizado');
  }
  return me;
}
```

#### Público vs. sesión requerida (RF-USR-11/12, RN-33 del documento general)

Navegar el catálogo (home, menú, producto, promociones) es **público**. Cualquier
otra acción — carrito, checkout, direcciones, pago, mis pedidos, seguimiento,
perfil, y todo el panel admin/delivery — exige sesión. Tres patrones, todos ya
soportados por `auth.js` sin código adicional:

| Situación | Qué hace la página |
|---|---|
| **Página pública** (home, menú, producto) | Llama `bootstrapSession()` al cargar, **sin redirigir**, solo para saludar al usuario y decidir qué mostrar en el header (nombre vs. "Ingresar"). |
| **Página exclusiva de cliente logueado** (carrito, dirección, pago, pedidos, seguimiento, perfil) | Llama `await requireRole()` **sin argumento** al cargar → exige *cualquier* usuario autenticado (no un rol específico). Sin sesión, redirige a `login.html?next=<pantalla>` y vuelve ahí después de loguear. |
| **Página exclusiva de un rol** (`pages/admin/*`, `pages/delivery/*`) | `await requireRole('ADMIN')` / `await requireRole('DELIVERY')`. |
| **Acción gatillada desde una página pública** (botón "Agregar" en el menú) | El handler del click chequea `getUser()`; si es `null`, redirige a `login.html?next=<pantalla actual>` **en vez de** llamar a la API. No hay redirect al cargar la página. |

El backend es quien manda: cada endpoint exige su propio `Depends(get_current_user)`
/ `require_role(...)` (Tema 1.5) — estas guardas del front son solo UX, nunca la
barrera de seguridad real.

### 15.4 `assets/js/countdown.js`

```js
export function startCountdown({ closeIso, onTick, onClose }) {
  const target = new Date(closeIso);
  const id = setInterval(() => {
    const s = Math.max(0, (target - new Date())/1000|0);
    onTick({ h:(s/3600|0), m:(s%3600/60|0), s:s%60, done: s===0 });
    if (s === 0) { clearInterval(id); onClose?.(); }
  }, 1000);
  return () => clearInterval(id);
}
```
El home pide `GET /shift/current`, usa `now` del servidor para corregir el desfase del reloj local y arranca el contador contra `close_time` del turno.

### 15.5 Páginas por rol (Fase objetivo)

| Rol | Páginas | Acceso |
|---|---|---|
| Auth | `login`, `registro`, `recuperar` | Público |
| Cliente | `index` (home), `menu`, `producto` | Público — navegación del catálogo |
| Cliente | `carrito`, `direccion`, `pago`, `pedidos`, `seguimiento`, `perfil` | 🔒 `requireRole()` sin argumento (cualquier usuario logueado) |
| Admin | `dashboard`, `pedidos`, `validacion`, `produccion`, `categorias`, `productos`, `promociones`, `deliveries`, `logistica`, `configuracion` | 🔒 `requireRole('ADMIN')` |
| Delivery | `inicio`, `ruta`, `parada`, `historial` | 🔒 `requireRole('DELIVERY')` |

Ver §15.3 para el detalle de cómo se gatean el catálogo público y las acciones
puntuales (p. ej. "Agregar al carrito") que se disparan desde una página pública.

### 15.6 Build de Tailwind

- Dev: CDN (`<script src="https://cdn.tailwindcss.com">`) con `tailwind.config` inline.
- Prod: `tailwindcss -i assets/css/base.css -o assets/css/tailwind.css --minify` (binario standalone). `tailwind.config.js` con los tokens del skill y `content: ['./**/*.html','./assets/js/**/*.js']`.

---

## 16. Sistema de diseño y adaptación mobile ↔ escritorio

El detalle completo (tokens, componentes, recetas) vive en la **skill `morfi-frontend`** (`.claude/skills/morfi-frontend/`), derivada de `04_Artesanal_Organico.html` (estilo **"Artesanal · Cocina de Olla"**). Resumen de lo que el backend/API debe habilitar y lo que el front debe cumplir:

### 16.1 Tokens (resumen)
- Colores: `kraft #E9DFC9` (fondo), `cream #F6EFDD` (superficie), `bark #3B2E22` (texto/oscuros), `forest #2F5D3A` (positivo/primario), `mustard #D69A2D` (acento 2°), `brick #B0472F` (acento 1°/CTA).
- Tipografía: **Bricolage Grotesque** (`display` — títulos, nombres, precios, números) + **Caveat** (`hand` — acentos a mano, con moderación) + **Inter** (`sans` — UI, labels, cuerpo).
- Utilidades: `.paper` (superficie con textura), `.blob`/`.blob2` (formas orgánicas), `.stamp` (sello), `.tape` + `.dashed` (ticket), `.lift` (hover con leve giro), `.foodA..D` (placeholders de foto).
- Radios: panel `34px`, Plato del Día `26px`, cards `2xl`, inputs `xl`; elementos interactivos con `.blob` (no `rounded-full`). Bordes `border-2`. Sin neón.

### 16.2 Regla de adaptación (obligatoria)

| Aspecto | Móvil (`< lg` = 1024px) | Escritorio (`≥ lg`) |
|---|---|---|
| Contenedor | full-width, `px-4/5` | `max-w-[1240px]` centrado, `px-10` |
| Navegación | **bottom nav** fija de 5 ítems (`lg:hidden`) | **top nav** horizontal en el header (`hidden lg:flex`) |
| Layout de contenido | 1 columna apilada | grilla intencional 2–4 col + panel lateral (resumen, filtros, promos) |
| Cards | ancho de la columna | tamaño natural en grilla; **prohibido** card suelta a todo el ancho |
| Botones/inputs | pueden ser full-width en formularios | ancho según contenido; **prohibido** estirar “porque sí” |
| Panel admin | listas apiladas | tablas densas + filtros laterales + acciones en fila |

El sobrante de ancho en escritorio se resuelve **con más columnas**, no con más padding ni elementos estirados. La estética (papel kraft, formas orgánicas, calidez de cocina casera) se mantiene idéntica en ambos tamaños.

### 16.3 Implicancia para la API
- `GET /shift/current` debe traer `now` del servidor (corrección de reloj para el countdown).
- `GET /catalog/products` debe traer el **precio ya resuelto** (`price`, `base_price`, `is_promo`, `promo_label`) y `stock_available` para pintar el estado “sin stock” sin cálculos en el front.
- `GET /promotions/daily-special` alimenta el bloque destacado del home.
- Respuestas con `*_display` (moneda formateada) para no duplicar reglas de formato.

---

## 17. Integración frontend ↔ backend

- **Dev**: front en `http://localhost:5500`, API en `http://localhost:8000`. `window.__MC_API__ = 'http://localhost:8000/api/v1'`. CORS habilitado para ese origen, `allow_credentials=True`.
- **Prod**: front y back quedan en **dos hosts distintos** — front en **Vercel** (dominio `*.vercel.app` mientras no haya dominio propio) y API en el **VPS Contabo**, detrás de Nginx con HTTPS vía Certbot. Es **cross-origin real**, no "mismo origen" como se pensaba originalmente:
  - CORS: `allow_origins=[FRONTEND_ORIGIN]` con la URL exacta que asigna Vercel, `allow_credentials=True`. Nunca `allow_origins=['*']` junto con `allow_credentials=True` (el navegador lo rechaza y además es inseguro).
  - Cookie de refresh: al ser cross-site, no alcanza con `SameSite=Lax` — en producción se configura `SameSite=None; Secure` (exige HTTPS en ambos extremos, ya cubierto por Vercel y por Certbot en el VPS).
  - Ambos extremos **deben** servir HTTPS: Vercel lo da por defecto; en el VPS lo resuelve Nginx + Certbot (ver §24.4 y `deploy/DEPLOY.md`).
  - Si en el futuro se compra un dominio propio (p. ej. `app.morficenter.com` / `api.morficenter.com`), conviene pasar la cookie a `Domain=.morficenter.com` con `SameSite=Lax`: deja de ser cross-site para el navegador y es más robusto que `SameSite=None`. Queda anotado como mejora futura, no bloquea el MVP.
- Contrato: OpenAPI (`/api/openapi.json`). Ante cambios de API se actualiza este documento y, si aplica, un `frontend/assets/js/api-types.js` con JSDoc.
- Errores de red / 5xx: `ui.js` muestra un toast estándar; los 4xx de dominio muestran el `error.message` del backend.

---

## 18. Seguridad

| Tema | Medida |
|---|---|
| Contraseñas | bcrypt (librería directa), factor de coste (`rounds`) ≥ 12. Nunca en logs. |
| JWT | `JWT_SECRET` fuerte en `.env`; access corto; refresh httpOnly + rotación/revocación. |
| Autorización | Siempre en backend (`require_role` + verificación de propiedad). El front no es barrera. |
| Comprobantes | Fuera de `static`; nombre `uuid4`; descarga solo por endpoint con auth y verificación de propiedad/rol; `Content-Disposition: attachment`. |
| Subida de archivos | Validar extensión **y** mime real (`python-magic` o cabecera); límite 8 MB; rechazar ejecutables; guardar fuera del webroot. |
| SQL injection | ORM parametrizado; nada de string-format en queries. |
| Validación de entrada | Pydantic en todos los endpoints; `CHECK` en DB como red de seguridad. |
| CORS | Lista blanca explícita; `allow_credentials` solo con orígenes concretos. |
| Rate limiting | `slowapi` en `/auth/login`, `/auth/register`, `/password/*` (p. ej. 10/min por IP). |
| Headers | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin`, CSP básica en las páginas. |
| CSRF | Refresh cookie `SameSite=Lax` (dev) / `SameSite=None; Secure` (prod, front y back en hosts distintos) y `Path` acotado; endpoints mutadores requieren `Authorization` (no cookie) → CSRF no aplica al access. |
| Secretos | `.env` fuera de git; `.env.example` versionado. |
| Ubicación de repartidores | Solo se acepta `POST /drivers/me/location` con `assignment` en `IN_PROGRESS`; se purga a los 7 días. |
| Auditoría | `audit_log` en: aprobación/rechazo de pago, cancelación, cambio de precio/stock, cambios de configuración, alta/cambio de rol de usuario. |
| Datos entre clientes | El seguimiento del cliente nunca expone dirección, nombre ni ítems de terceros (solo “paradas antes: N”, “ETA”). |

---

## 19. Configuración y variables de entorno

`backend/.env` (ejemplo en `.env.example`):

```ini
# App
APP_ENV=development                 # development | production
APP_NAME=Morfi Center
APP_TIMEZONE=America/Argentina/Buenos_Aires
API_PREFIX=/api/v1
FRONTEND_ORIGIN=http://localhost:5500      # prod: URL pública del proyecto en Vercel
COOKIE_SAMESITE=lax                        # lax en dev; "none" en prod (front y back en hosts distintos)

# DB
DATABASE_URL=sqlite:///./data/morfi.db

# Auth
JWT_SECRET=<64 hex chars>
ACCESS_TOKEN_MINUTES=15
REFRESH_TOKEN_DAYS=7

# Google OAuth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback

# Servicios externos
GEOCODING_PROVIDER=nominatim         # nominatim | google
NOMINATIM_USER_AGENT=morfi-center-dev
GOOGLE_MAPS_API_KEY=
ROUTE_PROVIDER=manual                # manual | osrm | google

# Storage
STORAGE_DIR=./storage
MAX_UPLOAD_MB=8

# Turnos y reservas
RESERVATION_TTL_MIN=40
```

`core/config.py` expone `settings` tipado (pydantic-settings). En `production`, `APP_ENV=production` fuerza `Secure` y `SameSite=None` en cookies (front y back en hosts distintos) y CSP estricta.

> **Secretos reales:** `backend/.env` con valores reales existe **únicamente en el VPS Contabo** (nunca en git, ni siquiera en `documentacion/`). `.env.example` documenta qué claves hacen falta, sin valores reales; se cargan a mano la primera vez que se configura el servidor (ver Fase 0, Tema 0.7, y `deploy/DEPLOY.md`).

---

## 20. Manejo de errores, logging y auditoría

### 20.1 Formato de error

```json
{ "error": { "code": "OUT_OF_STOCK",
             "message": "No hay stock suficiente de Canelones de verdura.",
             "details": { "product_id": 14, "available": 3, "requested": 5 } } }
```

| HTTP | Cuándo | `code` ejemplos |
|---|---|---|
| 400 | Entrada inválida de dominio | `INVALID_INPUT`, `ADDRESS_NOT_GEOCODABLE` |
| 401 | Sin credenciales / access vencido | `NOT_AUTHENTICATED` |
| 403 | Rol o propiedad insuficiente | `FORBIDDEN` |
| 404 | Recurso inexistente o ajeno | `NOT_FOUND` |
| 409 | Conflicto de estado / reglas | `SHIFT_CLOSED`, `OUT_OF_STOCK`, `CANCEL_WINDOW_CLOSED`, `INVALID_TRANSITION`, `OUT_OF_COVERAGE` |
| 413 | Archivo demasiado grande | `FILE_TOO_LARGE` |
| 422 | Validación Pydantic | `VALIDATION_ERROR` (detalle por campo) |
| 429 | Rate limit | `TOO_MANY_REQUESTS` |
| 500 | No controlado | `INTERNAL_ERROR` (sin filtrar detalles) |

Excepciones de dominio (`core/errors.py`): `DomainError` base → `NotFoundError`, `ForbiddenError`, `ConflictError`, `OutOfStockError`, `ShiftClosedError`, `CancelWindowClosedError`, `OutOfCoverageError`, `InvalidTransitionError`. Handler global las mapea a HTTP + formato.

### 20.2 Logging

- `logging` stdlib. En `production`, formato JSON (timestamp, level, logger, request_id, user_id, msg).
- `request_id` por request (middleware) propagado a logs y devuelto en header `X-Request-Id`.
- Se loguean: request/response de mutaciones, transiciones de estado, errores 5xx (con stack), llamadas a servicios externos (latencia, resultado).

### 20.3 Auditoría

`audit_log` se escribe desde los services (no desde la API) para no perder eventos internos/jobs. Cada entrada: `actor_id` (o NULL sistema), `action`, `entity_type`, `entity_id`, `data` (JSON before/after), `ip`.

---

## 21. Datos semilla y usuarios de prueba

`db/seed.py` (idempotente, corre en dev o con `python -m app.db.seed`):

- `system_settings` con los valores de §6.11.
- Turno del día (`ensure_today_shift`).
- 6 categorías + ~15 productos con stock y una promo + un Plato del Día.
- **Usuarios de prueba** (contraseñas simples, solo test) — se documentan en `documentacion/Usuarios.md`, no aquí en detalle. Formato previsto:

| Rol | Email | Password |
|---|---|---|
| Admin | `admin@morficenter.test` | `admin123` |
| Cliente | `cliente@morficenter.test` | `cliente123` |
| Delivery | `delivery@morficenter.test` | `delivery123` |

`documentacion/Usuarios.md` mantiene la lista viva y se actualiza con cada usuario de prueba que se cree durante el desarrollo.

---

## 22. Testing

- **Framework**: `pytest`. DB de test: SQLite en memoria (`sqlite://`) creada por fixture, esquema vía `Base.metadata.create_all` (o Alembic `upgrade head`).
- **Fixtures** (`conftest.py`): `session`, `client` (`httpx.AsyncClient` sobre la app con override de `get_session`), `customer`, `admin`, `delivery` (usuarios + tokens), `open_shift`, `catalog`.
- **Capas**:
  - `tests/unit/`: servicios de dominio puros — `PricingService` (promos vigentes / empate), `StockService` (reserva/vencimiento/commit/release), `CoverageService` (modos), `ShippingService` (tiers), `CancellationService` (ventana), `OrderStateMachine` (transiciones válidas e inválidas), `BalanceService` (uso parcial).
  - `tests/api/`: flujos end-to-end por endpoint — registro/login/refresh, alta de producto, confirmar pedido (feliz + sin stock + turno cerrado + fuera de cobertura), subir comprobante, aprobar/rechazar pago, cancelar con saldo, cola de validación, asignación y entrega.
- **Cobertura objetivo**: 100% en `services/` de reglas de negocio; > 80% global.
- **Regla del proyecto**: ninguna tarea se cierra sin su prueba (automática y/o validación manual del usuario en el front).

---

## 23. Migraciones de base de datos

- **Alembic**. `alembic/env.py` toma `settings.database_url` y `Base.metadata`.
- Flujo:
  ```
  alembic revision --autogenerate -m "add promotions.priority"
  alembic upgrade head
  alembic downgrade -1
  ```
- Cada cambio de modelo → una migración versionada en `alembic/versions/`. Nunca editar el esquema a mano.
- En local, las migraciones se corren a mano (`alembic upgrade head`) antes de levantar el backend; en el VPS, el runbook de despliegue (`deploy/DEPLOY.md`) las corre como parte del deploy.
- SQLite: para `ALTER` complejos, Alembic usa *batch mode* (`render_as_batch=True`).

---

## 24. Ejecución local y entornos

No existe ningún script tipo `iniciar.bat`: en local cada servicio se levanta a mano (§24.2) y en producción el despliegue es a través de Vercel (front) y del runbook del VPS (back) — ver §24.4.

### 24.1 Puertos

| Servicio | Puerto | URL |
|---|---|---|
| Backend (FastAPI/Uvicorn) | 8000 | http://localhost:8000 · docs en `/api/docs` |
| Frontend (dev static server) | 5500 | http://localhost:5500 |

### 24.2 Arranque en desarrollo (manual)

Cada servicio se levanta a mano, en su propia terminal:

```
# Terminal 1 — backend
cd backend
python -m venv .venv
call .venv\Scripts\activate          # o el shell equivalente
pip install -r requirements.txt
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
python -m http.server 5500 --directory frontend
```

Documentado también en el `README.md` de la raíz del proyecto.

### 24.3 Entornos

- **development**: `--reload`, CORS a `localhost:5500`, cookies sin `Secure` y `SameSite=Lax`, CSP laxa, seed automático, Swagger visible.
- **production**: Uvicorn como servicio `systemd` en el VPS Contabo detrás de Nginx (reverse proxy + TLS); frontend servido aparte por Vercel. Cookies `Secure` + `SameSite=None` (hosts distintos), CSP estricta, sin `--reload`, Swagger detrás de auth admin o deshabilitado, `alembic upgrade head` como paso del deploy.

### 24.4 Despliegue en producción: Vercel (front) + VPS Contabo (back + DB)

**Frontend → Vercel**
- Proyecto de Vercel conectado al repositorio Git; deploy automático en cada push (rama a definir: `master` o una rama `prod` separada).
- Build: sirve `frontend/` como sitio estático. Si Tailwind se compila por CLI, el *build command* de Vercel corre `tailwindcss -i ... -o ... --minify`; al principio, más simple, se puede commitear `tailwind.css` ya generado.
- `window.__MC_API__` apunta a la URL pública del backend en el VPS.
- Dominio: mientras no haya dominio propio, se usa el `*.vercel.app` que asigna Vercel.

**Backend + base de datos → VPS Contabo**
- Servidor contratado: Ubuntu LTS, 4 vCPU / 8 GB RAM / 100 GB (plan anual).
- Acceso: usuario no-root dedicado, SSH solo por clave pública/privada (login por contraseña deshabilitado), firewall (`ufw`) abierto únicamente a 22/80/443.
- Runtime: `venv` de Python + `requirements.txt`; `backend/data/morfi.db` (SQLite) y `backend/storage/` viven en el disco del VPS.
- Proceso: Uvicorn como servicio `systemd` (`deploy/morficenter-api.service`), con reinicio automático ante caída.
- Nginx como reverse proxy hacia Uvicorn + Certbot para HTTPS (`deploy/nginx.morficenter.conf`).
- Variables de entorno reales en `backend/.env`, **solo en el servidor** (nunca en git); `.env.example` es la referencia de qué claves hacen falta.
- Backups: cron diario que copia `backend/data/morfi.db` y `backend/storage/payment_proofs/` a otro destino (cumple el requisito de backup diario del Documento General §12).
- Runbook paso a paso, sin credenciales reales, en `deploy/DEPLOY.md`. La puesta a punto inicial del servidor es la Fase 0, Tema 0.7 del Roadmap.

**Despliegue continuo (después del primer deploy manual)**

El proyecto vive siempre desplegado: cada tarea del Roadmap aprobada se commitea y se pushea a `master`, y ese push despliega solo:

- **Frontend**: Vercel ya redeploya automáticamente al estar conectado al repositorio (T-0.7.5) — no requiere configuración adicional.
- **Backend**: `.github/workflows/deploy-backend.yml` (GitHub Actions) se conecta por SSH al VPS en cada push a `master` y ejecuta `git pull` + instalación de dependencias si cambiaron + `alembic upgrade head` + `systemctl restart morficenter-api`. Las credenciales SSH (`VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`) se cargan como *GitHub Actions secrets* — nunca quedan en el repositorio ni en `documentacion/`.
- Una tarea `[Lógica]`/`[Backend]` sin su `[Frontend]` todavía también se despliega; simplemente no hay cambio visible hasta que ese Frontend llegue (ciclo normal Lógica → Backend → Frontend del proyecto).

---

## 25. Estrategia de escalabilidad

Simple hoy, sin cerrarse puertas:

| Vector | Hoy (v1) | Camino de crecimiento |
|---|---|---|
| Motor de datos | SQLite (WAL) | Cambiar `DATABASE_URL` a PostgreSQL; repos y ORM ya lo permiten; migrar con Alembic |
| Concurrencia de escritura | 1 proceso Uvicorn | Postgres + varios workers Uvicorn/Gunicorn |
| Tiempo real (GPS/estado) | Polling (`GET` cada N s) | SSE (`/events`) → WebSocket cuando se aborde la fase de tracking |
| Archivos | `LocalFileStorage` | `S3Storage` (misma interfaz `FileStorage`) |
| Mapas/rutas | `ManualProvider` / Haversine | `OsrmProvider` / Google (misma interfaz `RouteProvider`) |
| Notificaciones | `InAppChannel` | Agregar `EmailChannel`, `PushChannel` sin tocar los services que notifican |
| Multi-turno | 1 turno LUNCH/día | `shifts.service_type` ya soporta BREAKFAST/DINNER; el resto del modelo referencia `shift_id` |
| Empresas | dirección + `label_for` por ítem | tabla `companies` + `company_members` + `orders.company_id` (punto de extensión) |
| Cache | — | Cachear catálogo/promos/settings en memoria con invalidación por mutación; luego Redis |
| API pública / apps nativas | web multipágina | La API REST ya es el límite; una app nativa consumiría los mismos endpoints |
| Hosting | 1 VPS Contabo (backend + DB) + Vercel (front) | Más VPS / balanceo si el tráfico lo pide; base de datos gestionada (Postgres) en un servicio aparte del que corre la API |

Principios que lo hacen posible: capas de una sola dirección, repos como única puerta a datos, servicios externos detrás de interfaces, dinero en enteros, estados y settings en tablas (no en código), IDs y timestamps consistentes.

---

## 26. Zona horaria y manejo de fechas

- **Almacenamiento**: todo `datetime` absoluto se guarda en **UTC** ISO-8601 (`...Z`).
- **Operación**: la zona del negocio es la configuración `timezone` de `system_settings` (§6.11), que el admin puede cambiar sin tocar el servidor. `APP_TIMEZONE` (`America/Argentina/Buenos_Aires`) es solo su **valor inicial** (el default mientras nadie la guardó) y el respaldo de los helpers de `core/timezone.py` cuando no se les pasa zona.
- **Turnos**: `open_time`/`close_time` se guardan como **hora de pared local** (`"12:00"`); para una `service_date` dada se resuelven a un instante absoluto con la zona `timezone` de la configuración y se comparan en UTC.
- **Countdown**: el front usa el `now` que devuelve `GET /shift/current` para no depender del reloj del dispositivo.
- **Ventana de cancelación**: `cancel_deadline = close_datetime_utc - cancel_window_min`.
- Librería: `zoneinfo` (stdlib) + paquete `tzdata` (verificado: en Windows `zoneinfo` no trae la base de datos IANA integrada y `ZoneInfo("America/Argentina/Buenos_Aires")` falla con `ZoneInfoNotFoundError` sin `tzdata` instalado; en Linux suele venir del sistema, pero `tzdata` lo garantiza en cualquier entorno de desarrollo o despliegue). Helpers en `core/timezone.py` (`now_utc()`, `to_local()`, `resolve_shift_instant(date, "HH:MM")`).

---

## 27. Convenciones de código

### Python
- PEP 8 + **black** (line length 100) + **ruff** (lint). Type hints obligatorios en `services/` y `repositories/`.
- Nombres: módulos y funciones `snake_case`, clases `PascalCase`, constantes `UPPER_SNAKE`.
- Un service = una responsabilidad de dominio. Sin lógica de negocio en `api/` ni en `models/`.
- Excepciones de dominio, nunca `HTTPException` fuera de `api/`.
- Docstring breve en cada service público describiendo la regla que implementa.

### JavaScript
- ES Modules, sin bundler. `camelCase`. Sin variables globales (todo en módulos).
- `api.js` es el único que hace `fetch`. Las páginas no arman URLs a mano.
- DOM: `data-*` para hooks de JS; nunca seleccionar por clases de Tailwind.
- Accesibilidad: `<button>` para acciones, `<a>` para navegación; `aria-*` donde corresponda.

### HTML / Tailwind
- Seguir la skill `morfi-frontend`. Solo tokens del sistema. Mobile-first; el salto `lg` cambia el layout.
- Parciales reutilizables en `partials/`. Nada de copiar-pegar headers/navs.

### Commits
- Mensajes en español, imperativo: `feat(pedidos): confirmar pedido con reserva de stock`.
- Prefijos: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`.
- Cierre de commit:
  ```
  Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
  ```

---

## 28. Orden técnico de implementación

Se sigue el roadmap funcional (§19 del Documento General) y, **dentro de cada tarea**, el ciclo obligatorio:

```
1. LÓGICA      → servicios de dominio + tests unitarios (sin API, sin front)
2. BACKEND     → modelos + migración + repos + endpoints + tests de API
3. FRONTEND    → pantalla(s) con el estilo Artesanal · Cocina de Olla, consumiendo la API
4. VALIDACIÓN  → el usuario prueba en el navegador y aprueba (check en el roadmap)
```

Nunca se implementa todo junto. El front empieza en Fase 0 como HTML con estilo (sin funcionalidad) y va incorporando de a una las funcionalidades.

Bloques técnicos, en orden:

| # | Bloque | Entregable técnico |
|---|---|---|
| T0 | Andamiaje | Repos `backend/` + `frontend/`, `main.py`, config, `session.py`, Alembic init, home HTML con estilo, infraestructura de despliegue (Vercel + VPS Contabo) |
| T1 | Usuarios y auth | `users`, `user_auth_providers`, `user_profiles`, `carts`, `customer_balances`; registro/login/refresh/me; RBAC; login Google; front de auth + guardas |
| T2 | Configuración y turnos | `system_settings`, `shifts`; endpoints de settings y `shift/current`; `ShiftService` resuelve apertura/cierre bajo demanda (sin job); countdown en el home |
| T3 | Catálogo | `categories`, `products`, `product_images`, `product_stock`; CRUD admin; listado público con precio resuelto; front catálogo + admin productos |
| T4 | Promociones | `promotions` (PROMO + DAILY_SPECIAL); `PricingService`; endpoints; bloque Plato del Día y precios promo en el front |
| T5 | Stock | `stock_reservations`; `StockService` libera vencidas al leer (sin job); “sin stock” en el front |
| T6 | Carrito | `cart_items`; `CartService` + resumen; front carrito |
| T7 | Direcciones y cobertura | `addresses`, `delivery_zones`; `GeocodingProvider`, `CoverageService`; endpoints; front dirección + resultado de cobertura |
| T8 | Envío | `ShippingService` + settings; cotización en el carrito |
| T9 | Confirmación de pedido | `orders`, `order_items`, `order_status_history`; `OrderStateMachine` (parte); `confirm`; congelado de importes; front “pedido creado” + datos de transferencia |
| T10 | Pagos y comprobantes | `payments`, `payment_proofs`; `FileStorage`; subida + descarga autorizada; front carga de comprobante |
| T11 | Validación administrativa | cola priorizada; approve/reject/mark-review; efectos sobre stock; `audit_log`; panel admin de validación |
| T12 | Saldo a favor y cancelaciones | `balance_transactions`; `BalanceService`, `CancellationService`; aplicar saldo en checkout; cancelar; front saldo + aviso “no cancelable” |
| T13 | Estados y producción | máquina de estados completa; `ProductionService`; consolidados; panel admin de pedidos y producción |
| T14 | Deliveries y asignación | `user_profiles` (driver), `delivery_assignments`, `delivery_routes`, `delivery_stops`; asignación manual + orden de paradas; front admin logística + app delivery |
| T15 | Seguimiento | `driver_locations`; `TrackingService`; vista de seguimiento del cliente (sin datos de terceros); ubicación del repartidor para el admin |
| T16 | Notificaciones | `notifications` + `InAppChannel`; centro de notificaciones en el front |

---

## 29. Anexos

### 29.1 Diagrama entidad-relación (texto)

```
users ─1:1─ user_profiles
users ─1:N─ user_auth_providers
users ─1:N─ addresses
users ─1:1─ carts ─1:N─ cart_items ─N:1─ products
users ─1:1─ customer_balances
users ─1:N─ balance_transactions ─N:1─ orders
users ─1:N─ notifications
users ─1:N─ orders

categories ─1:N─ products ─1:N─ product_images
products ─1:N─ product_stock ─N:1─ shifts
products ─1:N─ promotions
products ─1:N─ stock_reservations ─N:1─ orders
                                   └─N:1─ shifts

shifts ─1:N─ orders ─1:N─ order_items ─N:1─ products
orders ─1:N─ order_status_history ─N:1─ users (actor)
orders ─1:1─ payments ─1:N─ payment_proofs
orders ─N:1─ addresses

shifts ─1:N─ delivery_assignments ─N:1─ users (driver)
delivery_assignments ─1:1─ delivery_routes ─1:N─ delivery_stops ─N:1─ orders
users (driver) ─1:N─ driver_locations ─N:1─ delivery_assignments

delivery_zones (standalone)
system_settings (standalone)
audit_log ─N:1─ users (actor)
```

### 29.2 Matriz endpoints ↔ rol (extracto)

| Recurso | CUSTOMER | ADMIN | DELIVERY |
|---|:--:|:--:|:--:|
| `catalog/*` (GET) | ✅ | ✅ | ➖ |
| `catalog/*` (mutación) | ❌ | ✅ | ❌ |
| `cart/*` | ✅ | ❌ | ❌ |
| `orders` (POST confirm) | ✅ | ❌ | ❌ |
| `orders/{id}` (GET) | ✅ propio | ✅ | ✅ asignado |
| `orders/{id}/cancel` | ✅ (ventana) | ✅ | ❌ |
| `orders/{id}/transition` | ❌ | ✅ | ✅ (subset) |
| `payments/*/approve|reject` | ❌ | ✅ | ❌ |
| `payments/proofs/{id}` (GET) | ✅ propio | ✅ | ❌ |
| `production/*` | ❌ | ✅ | ❌ |
| `assignments` (POST) | ❌ | ✅ | ❌ |
| `assignments/me` | ❌ | ➖ | ✅ |
| `drivers/me/status` · `drivers/me/location` | ❌ | ✅ | ✅ |
| `settings/*` · `coverage/zones` · `coverage/config` | ❌ | ✅ | ❌ |
| `balance/me` | ✅ | ➖ | ➖ |
| `balance/adjust` | ❌ | ✅ | ❌ |
| `notifications/*` | ✅ | ✅ | ✅ |

### 29.3 Máquina de estados (referencia rápida)

Ver §8. Estados terminales: `DELIVERED`, `CANCELLED`. `PAYMENT_REJECTED` es recuperable (→ `PAYMENT_UNDER_REVIEW`). Solo `PAYMENT_APPROVED` y posteriores alimentan la producción consolidada.

---

*Fin del documento 02 · Documento Técnico. Próximo paso: `03_Roadmap.md` con fases y tareas detalladas, y arranque del bloque T0. Esperando aprobación.*
