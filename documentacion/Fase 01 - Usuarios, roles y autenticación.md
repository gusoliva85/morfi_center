# Fase 01 · Usuarios, roles y autenticación

**Proyecto:** Morfi Center
**Estado:** ✅ Completa y aprobada
**Inicio:** 11 de septiembre de 2026
**Cierre:** 11 de septiembre de 2026
**Temas de esta fase:** 1.1 Modelo y lógica de usuarios · 1.2 Persistencia de usuarios · 1.3 Registro · 1.4 Login local + sesión · 1.5 Autorización (RBAC) · 1.6 Perfil · 1.7 Gestión de usuarios por admin · 1.8 Login con Google · 1.9 Recuperación de contraseña · 1.10 Seed y usuarios de prueba · 1.11 Frontend de autenticación
**Roadmap:** `documentacion/03_Roadmap.md` (Fase 1)

---

## 1. Objetivo de la fase

Fundación de identidad de toda la plataforma: quién es cada usuario, cómo prueba quién dice ser, y qué puede hacer según su rol. Al cerrar esta fase existe un sistema completo de registro, login local, login con Google, sesión (access + refresh JWT), recuperación de contraseña, edición de perfil y gestión de personal (admin/delivery) por parte de un administrador — con su parte de frontend correspondiente en cada caso.

También quedó resuelta la regla de navegación que gobierna todo el frontend de acá en adelante: **el catálogo es público, actuar requiere sesión**. Cualquiera puede navegar el menú, ver productos y promociones sin loguearse; recién cuando intenta hacer algo (pedir, ver su perfil, su carrito) se le pide sesión, en el momento y con retorno a donde estaba — nunca con una pantalla de login que bloquee el sitio entero.

Al terminar, el front muestra únicamente lo de usuarios (registro, login, sesión, perfil, alta de personal); el resto de la aplicación (catálogo, turnos, pedidos, pagos...) sigue hardcodeado o inexistente hasta sus propias fases.

---

## 2. Qué quedó implementado

### Tema 1.1 · Modelo y lógica de usuarios

Tres módulos de lógica pura, sin FastAPI ni base de datos, que sostienen todo lo demás. `app/services/user_service.py` valida forma (nunca unicidad, eso es de la capa de repositorio): email con una regex simple pero suficiente, nombre/apellido sin dígitos, teléfono opcional con formato laxo, y una política de contraseña mínima (8 caracteres, al menos una letra y un número). Cada función que rechaza algo lanza `InvalidInputError` con `details.field` — así el handler global ya arma la respuesta 400 correcta sin lógica extra en la API, y el frontend puede mapear el error al campo exacto del formulario.

```python
def validate_password(password: str | None) -> None:
    value = password or ""
    failed: list[str] = []
    if len(value) < MIN_PASSWORD_LENGTH:
        failed.append(f"mínimo {MIN_PASSWORD_LENGTH} caracteres")
    if not any(ch.isalpha() for ch in value):
        failed.append("al menos una letra")
    if not any(ch.isdigit() for ch in value):
        failed.append("al menos un número")
    if failed:
        raise InvalidInputError(
            "La contraseña no cumple los requisitos: " + ", ".join(failed) + ".",
            details={"field": "password", "requirements_failed": failed},
        )
```

`app/core/security.py` concentra hashing (bcrypt vía passlib, costo 12) y JWT (PyJWT). Los tres tipos de token que terminó necesitando la fase — access, refresh y de reseteo de contraseña — comparten el mismo patrón: claims `sub` + `type` (y `jti` los dos últimos, para poder revocarlos individualmente), firmados con `settings.jwt_secret`.

**Archivos principales:** `app/services/user_service.py`, `app/core/security.py`
**Tareas de este tema:** T-1.1.1 ✅ · T-1.1.2 ✅ · T-1.1.3 ✅

---

### Tema 1.2 · Persistencia de usuarios

El modelo de identidad (`app/models/user.py`) separa `User` (datos + rol + estado), `UserAuthProvider` (qué métodos de login tiene vinculados — `local`, `google` — único por `provider`+`provider_uid`) y `UserProfile` (extendido, hoy solo con los campos de repartidor: `vehicle_type`, `capacity`, `driver_status`). `Cart` y `CustomerBalance` quedaron como tablas 1:1 vacías desde esta fase — se crean junto con cada `CUSTOMER` aunque su lógica de negocio llegue recién en las Fases 6 y 12.

`UserRepository` (`app/repositories/user_repository.py`) es puro acceso a datos — nunca comitea, solo `flush()` — con `list(role=, page=, page_size=)` devolviendo el `Page` genérico que después reusaron el resto de los listados paginados del proyecto.

**Archivos principales:** `app/models/{user,cart,balance}.py`, `app/repositories/{user_repository,pagination}.py`, migración `fase1 usuarios`
**Tareas de este tema:** T-1.2.1 ✅ · T-1.2.2 ✅ · T-1.2.3 ✅ · T-1.2.4 ✅

---

### Tema 1.3 · Registro (cuenta propia)

`AuthService.register` es la primera pieza de lo que se volvió el servicio central de identidad: valida cada dato con `user_service`, verifica que el email no exista (`ConflictError` si ya está), hashea la contraseña, y crea en una sola unidad de trabajo el `User(role=CUSTOMER)`, su `UserAuthProvider(local)`, su `Cart` y su `CustomerBalance` en 0. `POST /api/v1/auth/register` lo expone y, a diferencia de un alta "seca", deja al usuario logueado — emite el mismo par de tokens que un login, evitando un paso extra en el frontend.

**Archivos principales:** `app/services/auth_service.py`, `app/api/routes/auth.py`, `app/schemas/user.py`
**Tareas de este tema:** T-1.3.1 ✅ · T-1.3.2 ✅

---

### Tema 1.4 · Login local + sesión

`AuthService.authenticate` responde siempre con el mismo mensaje genérico ante email inexistente o contraseña incorrecta (no revela cuál de los dos falló); una cuenta suspendida se informa aparte, pero solo **después** de validar la contraseña, para que no se pueda usar el estado de la cuenta como oráculo probando contraseñas al azar.

La sesión quedó como access token de 15 min (en el cuerpo de la respuesta) + refresh de 7 días (cookie httpOnly, `Path` acotado a `/api/v1/auth`). El refresh **rota en cada uso**: `POST /auth/refresh` decodifica la cookie, revoca ese `jti` en la tabla `revoked_tokens` y emite un par nuevo — así reusar un refresh ya rotado (por ejemplo, uno copiado) falla igual que uno inválido:

```python
def refresh_session(self, refresh_token: str | None) -> User:
    payload = decode_token(refresh_token, expected_type="refresh")
    if self.tokens.is_revoked(payload["jti"]):
        raise NotAuthenticatedError(_SESSION_INVALID_MESSAGE)
    user = self.users.get_by_id(int(payload["sub"]))
    ...
    self.tokens.revoke(payload["jti"], expires_at=...)  # uso único
    return user
```

El rate limiting (`slowapi`, 10 peticiones/min por IP en `/login`, `/register` y los dos endpoints de `/password/*`) trajo el hallazgo más filoso de la fase: el decorador `@limiter.limit` combinado con `from __future__ import annotations` le rompía a Pydantic la resolución de los modelos de los parámetros de ruta (una incompatibilidad conocida de slowapi con anotaciones diferidas). Se resolvió sacando ese import únicamente de `app/api/routes/auth.py`, con un comentario explicando por qué — el resto del proyecto lo sigue usando normalmente.

**Archivos principales:** `app/services/auth_service.py`, `app/api/routes/auth.py`, `app/core/rate_limit.py`, `app/models/token.py`, `app/repositories/token_repository.py`
**Tareas de este tema:** T-1.4.1 ✅ · T-1.4.2 ✅ · T-1.4.3 ✅ · T-1.4.4 ✅ · T-1.4.5 ✅

---

### Tema 1.5 · Autorización (RBAC)

`app/api/deps.py` define las dos dependencias que gatean el resto de la API. `get_current_user` extrae el Bearer, decodifica el **access** token (nunca acepta un refresh ahí) y carga el usuario, validando que exista y esté `ACTIVE`. `require_role(*roles)` es una fábrica de dependencia que se apoya en la anterior y corta con 403 si el rol no coincide:

```python
def require_role(*roles: Role) -> Callable[[User], User]:
    def _dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise ForbiddenError()
        return user
    return _dependency
```

`GET /auth/me` quedó como el endpoint que el frontend usa para "quién soy" — devuelve también el saldo (`CustomerBalance`), que ya existía desde el registro aunque su lógica de negocio llegue en la Fase 12.

**Archivos principales:** `app/api/deps.py`, `app/api/routes/auth.py`, `app/schemas/user.py`
**Tareas de este tema:** T-1.5.1 ✅ · T-1.5.2 ✅ · T-1.5.3 ✅

---

### Tema 1.6 · Perfil

`UserService.update_profile(user, updates)` aplica un PATCH parcial de verdad: solo toca las claves presentes en el dict `updates` (no reenviar un campo lo deja como estaba), y `phone: None` explícito lo borra. `email` no se acepta por acá a propósito — cambiarlo implicaría reverificación, fuera de alcance de esta fase. `PATCH /api/v1/users/me/profile` lo expone, protegido con `get_current_user`.

**Archivos principales:** `app/services/user_service.py`, `app/api/routes/users.py`, `app/schemas/user.py`
**Tareas de este tema:** T-1.6.1 ✅

---

### Tema 1.7 · Gestión de usuarios por admin

`AuthService.create_staff` es el alta de personal (`ADMIN`/`DELIVERY`) hecha por un admin: a diferencia de `register`, no emite tokens (la persona inicia sesión después, con sus propias credenciales) y no crea carrito ni saldo — son conceptos de cliente. Si no se le pasa contraseña, genera una temporal aleatoria y la devuelve en texto plano **una sola vez** — no hay envío de mail todavía, así que el admin se la comunica a la persona por fuera del sistema.

`GET /api/v1/users?role=&page=` y `PATCH /api/v1/users/{id}` (rol y/o estado) completan la gestión. Cambiar rol o estado queda auditado en una tabla nueva, `audit_log` (no existía en el diseño original de la Fase 0 — se agregó acá porque esta era la primera funcionalidad que realmente la necesitaba), escrita desde el propio service con el actor, la acción y el before/after en JSON:

```python
self.audit.record(
    actor_id=actor.id,
    action="user.update_role_status",
    entity_type="user",
    entity_id=str(user.id),
    data={"before": before, "after": after},
    ip=ip,
)
```

**Archivos principales:** `app/services/auth_service.py`, `app/api/routes/users.py`, `app/models/audit.py`, `app/repositories/audit_repository.py`
**Tareas de este tema:** T-1.7.1 ✅ · T-1.7.2 ✅

---

### Tema 1.8 · Login con Google

El cliente OAuth2/OIDC de Google (`app/services/external/google_oauth.py`, con Authlib) arma la URL de autorización con `state` + PKCE (S256). Como el proyecto no usa sesión de servidor (todo es JWT stateless, sin `Starlette SessionMiddleware`), el `state` y el `code_verifier` viajan firmados en una cookie httpOnly de 10 minutos (`mc_oauth_state`) entre el `/login` y el `/callback`. El `id_token` que devuelve Google se valida de verdad — firma RS256 contra su JWKS (cacheado con `PyJWKClient`), issuer y audience — antes de confiar en sus claims.

`AuthService.login_with_google` resuelve los tres caminos posibles, en este orden: ya existe el provider `google` vinculado → login; no existe el provider pero sí un usuario con ese email (alta local previa) → se vincula el provider sin tocar la contraseña; no existe ninguno de los dos → se crea un `CUSTOMER` nuevo con `password_hash=NULL` (solo puede entrar por Google). El callback siempre **redirige al front** — nunca devuelve JSON, porque se llega por navegación de página completa — con el access token en el fragmento de la URL (`#access_token=...`) en el éxito, o `?error=google_auth_failed` en cualquier falla.

**Archivos principales:** `app/services/external/google_oauth.py`, `app/services/auth_service.py`, `app/api/routes/auth.py`
**Tareas de este tema:** T-1.8.1 ✅ · T-1.8.2 ✅

---

### Tema 1.9 · Recuperación de contraseña

`request_password_reset` genera un token (30 min, uso único vía la misma tabla `revoked_tokens`) solo si el email corresponde a una cuenta **local activa** — una cuenta solo-Google no tiene contraseña que resetear. La función nunca lanza y el endpoint siempre responde 200, exista o no la cuenta: no hay forma de usar este flujo para confirmar si un email está registrado. Sin envío de mail todavía, el token se loguea en la consola del backend en desarrollo.

Una decisión que se apartó del patrón de los tokens de sesión: cualquier problema con el token de reseteo (vencido, ya usado, malformado) devuelve **400** `INVALID_INPUT` con `details.field: "token"`, no 401 — el roadmap lo pedía así explícitamente, porque conceptualmente es un dato de formulario mal formado o vencido, no una sesión que expiró.

**Archivos principales:** `app/services/auth_service.py`, `app/core/security.py`, `app/api/routes/auth.py`
**Tareas de este tema:** T-1.9.1 ✅

---

### Tema 1.10 · Seed y usuarios de prueba

`seed_users()` (`app/db/seed.py`) crea, si no existen, los tres usuarios de prueba documentados en `Usuarios.md`: un `ADMIN`, un `CUSTOMER` (con su carrito y saldo) y un `DELIVERY` (con su `UserProfile` de moto). Reutiliza el mismo `AuthService` que usa el resto de la app en vez de insertar filas a mano, así el seed siempre está en sincronía con las reglas reales de alta.

**Archivos principales:** `app/db/seed.py`, `documentacion/Usuarios.md`
**Tareas de este tema:** T-1.10.1 ✅

---

### Tema 1.11 · Frontend de autenticación

Las tres pantallas de auth (`login`, `registro`, `recuperar`) comparten el mismo layout enfocado — una card `.paper` centrada, sin header/nav completos — y el mismo patrón: validan en vivo lo que se puede validar en el cliente, y dejan que el backend tenga la última palabra (los errores con `details.field` van al campo exacto; el resto, a un banner). `login.js` además completa el aterrizaje del flujo de Google: detecta `#access_token=...` en la URL, pide `/auth/me` y redirige.

El mecanismo de sesión (`auth.js`) quedó con dos guardas distintas según el tipo de pantalla, que es la regla de navegación pública-vs-gateada de esta fase hecha código:

```js
// Página pública: nunca bloquea, solo saluda si hay sesión.
export async function mountSessionUI(root = document) {
  const user = await bootstrapSession();
  paintSessionSlot(user, root);
  return user;
}

// Página exclusiva de un rol (o de cualquier usuario logueado si `roles` es undefined):
export async function requireRole(roles) {
  const me = await bootstrapSession();
  const allowed = roles == null || [].concat(roles).includes(me?.role);
  if (!me || !allowed) {
    window.location.href = `${LOGIN_URL}?next=${encodeURIComponent(location.pathname)}`;
    throw new Error("no autorizado");
  }
  return me;
}
```

`pages/cliente/perfil.html` fue la primera pantalla gateada real (`requireRole()` sin argumentos — cualquier usuario logueado, no solo `CUSTOMER`) y probó el mecanismo de punta a punta: sin sesión redirige a login con `?next=`, y al loguear vuelve. `pages/admin/usuarios.html` (gateada con `requireRole("ADMIN")`) es la contraparte administrativa: tabla con filtro por rol y paginación, alta de personal con la contraseña temporal a la vista si el backend la generó, y por fila un cambio de rol o de estado. `index.html` quedó con `mountSessionUI()` — saluda si hay sesión, muestra "Ingresar" si no, sin redirigir nunca.

**Archivos principales:** `frontend/pages/auth/{login,registro,recuperar}.html` + sus `.js`, `frontend/pages/cliente/perfil.html`, `frontend/pages/admin/usuarios.html`, `frontend/assets/js/auth.js`, `frontend/partials/header.html`, `frontend/index.html`
**Tareas de este tema:** T-1.11.1 ✅ · T-1.11.2 ✅ · T-1.11.3 ✅ · T-1.11.4 ✅ · T-1.11.5 ✅ · T-1.11.6 ✅ · T-1.11.7 ✅

---

## 3. Cómo probarlo

1. Ejecutar `iniciar.bat` desde la raíz del proyecto (aplica migraciones y corre el seed automáticamente).
2. Abrir `http://localhost:5500/index.html` sin sesión → se ve completa, con un link "Ingresar" en el header (escritorio).
3. Ir a `http://localhost:5500/pages/auth/login.html` y entrar con `cliente@morficenter.test` / `cliente123` (ver `documentacion/Usuarios.md`) → redirige a la home, que ahora saluda por el nombre y ofrece "Cerrar sesión".
4. Abrir `http://localhost:5500/pages/cliente/perfil.html` **sin sesión** (en otra pestaña o tras cerrar sesión) → redirige a login con `?next=`, y al loguear vuelve directo a esa pantalla. Con sesión, cambiar el teléfono y recargar → persiste.
5. Loguear con `admin@morficenter.test` / `admin123`, ir a `http://localhost:5500/pages/admin/usuarios.html`, crear un `DELIVERY` nuevo sin poner contraseña → aparece la temporal en pantalla; loguear con esas credenciales en otra pestaña funciona.
6. Probar "Continuar con Google" desde `login.html` requiere credenciales reales de un proyecto de Google Cloud en `backend/.env` (`GOOGLE_CLIENT_ID`/`SECRET`) — sin ellas, el botón redirige pero Google va a rechazar el `client_id`. El flujo está probado con `id_token` mockeado en los tests automatizados.
7. Dentro de `backend/`, correr `pytest` → **335 tests en verde**; `ruff check .` y `black --check .` sin observaciones.

---

## 4. Usuarios de prueba involucrados

Los tres usuarios documentados en `documentacion/Usuarios.md` ya existen y están activos (los crea `seed_users()`):

| Rol | Email | Contraseña |
|---|---|---|
| ADMIN | `admin@morficenter.test` | `admin123` |
| CUSTOMER | `cliente@morficenter.test` | `cliente123` |
| DELIVERY | `delivery@morficenter.test` | `delivery123` |

---

## 5. Decisiones y notas técnicas

- **Regla de navegación pública-vs-gateada** (RF-USR-11/12, RN-33 de `01_Documento_General.md`): aclarada explícitamente a mitad de fase — navegar el catálogo nunca pide sesión; solo actuar (pedir, ver carrito/perfil) la pide, en el momento y con retorno a donde estaba. Gobierna todo el frontend de acá en adelante, no solo esta fase.
- **`audit_log`**: no estaba en el modelo de datos original de la Fase 0; se agregó en T-1.7.2 porque fue la primera funcionalidad (cambios de rol/estado por un admin) que realmente la necesitaba, siguiendo el esquema ya previsto en `02_Documento_Tecnico.md §6.10`.
- **slowapi + anotaciones diferidas**: incompatibilidad real entre `@limiter.limit` y `from __future__ import annotations` que rompía la resolución de modelos Pydantic en las rutas. Se resolvió sacando ese import puntualmente de `app/api/routes/auth.py` (documentado con un comentario en el propio archivo), no del resto del proyecto.
- **Reset de contraseña en 400, no 401**: a diferencia de los tokens de sesión (access/refresh), un token de reseteo inválido/vencido/usado se trata como un dato de entrada incorrecto (`InvalidInputError`), no como una sesión expirada — así lo pedía el roadmap explícitamente.
- **OAuth de Google sin sesión de servidor**: el proyecto es JWT stateless de punta a punta; en vez de agregar `Starlette SessionMiddleware` solo para guardar `state`/`code_verifier` entre el `/login` y el `/callback` de Google, se firmaron en una cookie httpOnly de corta duración con el mismo secreto de JWT que ya usa el resto de la app.
- **`paintSessionSlot` separado de `mountSessionUI`**: una página gateada (que ya resolvió la sesión con `requireRole()`) pinta el header con ese mismo usuario en vez de pedir `/auth/me` una segunda vez solo para el saludo.
- **Rate limiting extendido a `/password/*`**: el diseño original de T-1.4.5 ya preveía extenderlo a los endpoints de recuperación de contraseña cuando se construyeran (T-1.9.1); se aplicó en esa misma tarea.

---

## 6. Estado final de la fase

| Tarea | Estado |
|---|---|
| T-1.1.1 · Reglas de validación de usuario | ✅ |
| T-1.1.2 · Hash y verificación de contraseñas | ✅ |
| T-1.1.3 · Emisión y verificación de JWT | ✅ |
| T-1.2.1 · Modelos `User`/`UserAuthProvider`/`UserProfile` | ✅ |
| T-1.2.2 · Modelos `Cart`/`CustomerBalance` (vacíos) | ✅ |
| T-1.2.3 · Migración Alembic de la Fase 1 | ✅ |
| T-1.2.4 · `UserRepository` | ✅ |
| T-1.3.1 · `AuthService.register` | ✅ |
| T-1.3.2 · `POST /auth/register` | ✅ |
| T-1.4.1 · `AuthService.authenticate` | ✅ |
| T-1.4.2 · `POST /auth/login` | ✅ |
| T-1.4.3 · `POST /auth/refresh` | ✅ |
| T-1.4.4 · `POST /auth/logout` | ✅ |
| T-1.4.5 · Rate limiting en auth | ✅ |
| T-1.5.1 · `get_current_user` | ✅ |
| T-1.5.2 · `require_role(*roles)` | ✅ |
| T-1.5.3 · `GET /auth/me` | ✅ |
| T-1.6.1 · Editar perfil | ✅ |
| T-1.7.1 · Crear ADMIN / DELIVERY | ✅ |
| T-1.7.2 · Listar y editar usuarios (admin) | ✅ |
| T-1.8.1 · Cliente OAuth con Authlib | ✅ |
| T-1.8.2 · Callback y vinculación | ✅ |
| T-1.9.1 · Solicitar y resetear contraseña | ✅ |
| T-1.10.1 · Seed de usuarios base | ✅ |
| T-1.11.1 · `login.html` + `login.js` | ✅ |
| T-1.11.2 · `registro.html` + `registro.js` | ✅ |
| T-1.11.3 · `recuperar.html` + `recuperar.js` | ✅ |
| T-1.11.4 · Sesión, guardas por rol y logout | ✅ |
| T-1.11.5 · `pages/cliente/perfil.html` + js | ✅ |
| T-1.11.6 · `pages/admin/usuarios.html` + js | ✅ |
| T-1.11.7 · Home: integrar sesión (mínimo) | ✅ |

*Fase cerrada y aprobada el 11 de septiembre de 2026. Continúa en `Fase 02 - Configuración del sistema y turnos.md`.*
