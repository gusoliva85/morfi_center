# Fase 01 · Usuarios, roles y autenticación

**Estado:** Completa y aprobada (con 2 tareas deliberadamente en pausa — ver §6)
**Fecha de cierre:** 2026-09-24
**Roadmap:** `03_Roadmap.md` — Fase 1

---

## 1. Objetivo

Fundación de identidad del proyecto. Al terminar, el front muestra **solo** lo de usuarios: registro, login (local y Google), sesión, perfil, y el admin puede crear repartidores y otros admins. Con esta fase cerrada, todo el resto de las fases (catálogo, carrito, pedidos, etc.) ya tiene sobre qué pararse: quién es el usuario, qué puede hacer, y cómo se lo protege.

## 2. Temas y tareas cerradas

| Tema | Tareas |
|---|---|
| 1.1 · Modelo y lógica de usuarios | T-1.1.1, T-1.1.2, T-1.1.3 |
| 1.2 · Persistencia de usuarios | T-1.2.1 a T-1.2.4 |
| 1.3 · Registro (cuenta propia) | T-1.3.1, T-1.3.2 |
| 1.4 · Login local + sesión | T-1.4.1 a T-1.4.5 |
| 1.5 · Autorización (RBAC) | T-1.5.1 a T-1.5.3 |
| 1.6 · Perfil | T-1.6.1 |
| 1.7 · Gestión de usuarios por admin | T-1.7.1, T-1.7.2 |
| 1.8 · Login con Google | T-1.8.1 (T-1.8.2 en pausa — ver §6) |
| 1.9 · Recuperación de contraseña | T-1.9.1 (funcional, con una pieza de infraestructura pendiente — ver §6) |
| 1.10 · Seed y usuarios de prueba | T-1.10.1 |
| 1.11 · Frontend de autenticación | T-1.11.1 a T-1.11.7 |

**Corrección de tildado al cerrar la fase:** T-1.11.1 y T-1.11.4 habían quedado marcadas `[~]` por tener un alcance necesariamente parcial en el momento de implementarlas (dependían de páginas que todavía no existían), pero el usuario ya las había aprobado para seguir adelante — se pasaron a `[x]` acá, sin cambiar una línea de código, porque `[~]`/`[x]` distingue "¿lo aprobó el usuario?" y no "¿tiene cobertura del 100% del enunciado abstracto de la tarea?".

## 3. Qué se hizo y cómo quedó implementado

### Tema 1.1 · Modelo y lógica de usuarios

**En palabras:** reglas de negocio puras, sin base de datos ni API — `normalize_email`, `is_valid_email`, `validate_password` (8-72 bytes, letra + número), `is_valid_name`. Hash de contraseñas con `bcrypt` directo (`rounds=12`). Emisión y verificación de JWT (`create_access_token` 15 min, `create_refresh_token` 7 días con `jti`, `decode_token`).

**Código clave** (`backend/app/services/user_service.py`):
```python
def validate_password(password: str) -> bool:
    if len(password) < 8 or len(password.encode("utf-8")) > 72:
        return False
    return any(c.isalpha() for c in password) and any(c.isdigit() for c in password)
```

**Cómo se probó:** tests unitarios de cada regla, más un hallazgo empírico real: `bcrypt` 4.x trunca en silencio contraseñas de más de 72 bytes en vez de lanzar error (comportamiento distinto a `bcrypt` ≥ 5.0), verificado instalando ambas versiones — de ahí el tope explícito en `validate_password`, sin el cual `hash_password` explotaría con `ValueError`.

### Tema 1.2 · Persistencia de usuarios

**En palabras:** modelos `User`, `UserAuthProvider`, `UserProfile`, `Cart`, `CustomerBalance` (SQLAlchemy). `UTCDateTime` propio que **rechaza** datetimes sin zona horaria en vez de guardar una hora ambigua. `UserRepository` con paginado (`(items, total)`, no solo `items`). Migración de Alembic para las 5 tablas.

**Código clave** (`backend/app/db/types.py`):
```python
class UTCDateTime(TypeDecorator):
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("UTCDateTime requiere un datetime con zona horaria (tz-aware).")
        return value.astimezone(UTC)
```

**Cómo se probó:** 40+ tests entre modelos, repositorio y migraciones — incluido uno que compara el esquema migrado contra `Base.metadata` con `compare_metadata` y **falla si alguien toca un modelo y se olvida de generar la migración**.

### Tema 1.3 · Registro (cuenta propia)

**En palabras:** `AuthService.register` normaliza el email, verifica unicidad, hashea la contraseña, crea el usuario con su carrito y su saldo en 0. `POST /api/v1/auth/register` con login automático (devuelve tokens en el 201).

**Cómo se probó:** alta real vía HTTP, contraseña nunca en la respuesta, email duplicado → 409, y el caso de dos altas simultáneas con el mismo email (una de las dos debe perder contra el `UNIQUE` de la base, no romper con un 500).

### Tema 1.4 · Login local + sesión

**En palabras:** `authenticate` valida credenciales con **el mismo mensaje y el mismo tiempo de respuesta** para email inexistente, contraseña incorrecta o cuenta solo-Google (para no permitir enumerar emails registrados). Refresh con **rotación de un solo uso** (tabla `revoked_tokens`): cada uso del refresh lo quema, así que un token robado deja de servir en cuanto el dueño legítimo renueva. Logout que **nunca falla**, ni sin cookie, ni con una vencida o alterada. Rate limiting (`slowapi`, 10/min por IP real, no la del proxy).

**Código clave** (`backend/app/services/auth_service.py`):
```python
# Hash descartable para gastar el mismo tiempo cuando el email no existe: sin
# esto, un email inexistente responde muchísimo más rápido que uno real.
_DUMMY_HASH = hash_password("contrasena-que-nadie-usa-1")
```

**Cómo se probó:** medición empírica de tiempos (185ms en los dos casos, 0ms de diferencia); dos usos simultáneos del mismo refresh (una carrera real, encontrada por un test, que daba 500 en vez de 401 antes del arreglo); verificación completa cross-site contra producción (Vercel + VPS) con el `Origin` real, cerrando de paso `T-0.7.6` de la Fase 0.

### Tema 1.5 · Autorización (RBAC)

**En palabras:** `get_current_user` (extrae y valida el Bearer; revalida `status` en cada request, para que suspender a alguien lo eche al instante y no recién cuando venza su token de 15 min). `require_role(*roles)`, con la decisión de que `require_role()` sin argumentos significa "cualquier usuario logueado" (no `CUSTOMER`), porque un admin también puede querer pedir comida (RN-33). `GET /auth/me`.

**Cómo se probó:** 401 vs 403 bien diferenciados en cada caso (el front actúa distinto: uno redirige a login, el otro no); sin jerarquía de roles verificada explícitamente (un ADMIN no entra a lo de DELIVERY).

### Tema 1.6 · Perfil

**En palabras:** `update_profile` con semántica real de PATCH — solo se toca lo que el cliente mandó, y se distingue "campo ausente" de "`phone: null`" (que sí lo borra). Email, rol y contraseña **no** editables por acá (`extra="forbid"`, da 422 si se intentan, no los ignora en silencio).

**Cómo se probó:** los cambios se releen desde la base (no se confía en la respuesta), y un cambio parcial no borra el resto de los campos.

### Tema 1.7 · Gestión de usuarios por admin

**En palabras:** `UserAdminService.create_staff` — solo ADMIN/DELIVERY (los CUSTOMER se registran solos, por diseño); un repartidor nuevo arranca `NO_DISPONIBLE`. Listado paginado con filtro por rol y edición de rol/estado con auditoría (`audit_log`, con actor, IP y valores antes/después). Un admin **no puede** cambiar su propio rol ni su propio estado.

**Cómo se probó:** el repartidor creado se loguea de verdad; suspender a alguien le impide loguearse de verdad (403 real, no solo un campo en la base); un PATCH que no cambia nada no deja rastro en la auditoría.

### Tema 1.8 · Login con Google

**En palabras:** `GET /auth/google/login` arma la redirección con `state` + PKCE (Authlib), guardados en una cookie de sesión propia de vida corta. `login_with_google` resuelve los tres casos (ya vinculado, email existente → vincula, nuevo → crea) usando el `sub` de Google como identidad, no el email. Sin credenciales configuradas, responde `503` con un mensaje claro en vez de un error interno.

**Cómo se probó:** todo simulado (sin llamar a Google de verdad) más una verificación contra un servidor real de que el `503` sin credenciales no rompe el resto de la API. **Ver §6: el callback (T-1.8.2) quedó en pausa a pedido del usuario**, sin credenciales reales de Google para probarlo de punta a punta.

### Tema 1.9 · Recuperación de contraseña

**En palabras:** `forgot`/`reset` con respuesta **siempre idéntica** exista o no el email. El link muere si la contraseña ya cambió (huella del `password_hash` vigente al emitirlo), además de ser de un solo uso. Una cuenta solo-Google puede fijarse una contraseña por acá.

**Cómo se probó:** flujo completo con el token real extraído del log del servidor (todavía no hay servicio de mail — ver §6); un link viejo muere en cuanto se usa uno más nuevo.

### Tema 1.10 · Seed y usuarios de prueba

**En palabras:** `seed_test_users` crea cliente/admin/repartidor de prueba, documentados en `Usuarios.md` — pero **se niega a correr en producción**, porque sus contraseñas están en un repositorio público. `seed_admin_from_env` resuelve un círculo real: producción no tiene usuarios, y crear uno por la API exige ya ser admin; este crea el primero desde `SEED_ADMIN_EMAIL`/`SEED_ADMIN_PASSWORD` (variables del servidor, nunca en el repo).

**Cómo se probó:** los tres usuarios de prueba loguean de verdad contra un servidor real, cada uno con su rol correcto.

### Tema 1.11 · Frontend de autenticación

**En palabras:** las primeras pantallas reales del sitio — login, registro, recuperar contraseña, perfil, panel de admin — todas con el estilo Artesanal · Cocina de Olla, validación en vivo que espeja las reglas del backend, y errores del servidor ubicados bajo el campo que corresponde. El mecanismo de sesión (`requireRole`/`bootstrapSession`/widget del header) se construyó una sola vez y lo reutiliza cada página nueva.

**Código clave** (`frontend/assets/js/pages/admin-usuarios.js` — evita releer después de escribir):
```js
function applyUpdatedUser(updatedUser) {
  state.items = state.items.map((u) => (u.id === updatedUser.id ? updatedUser : u));
  renderRows();
}
```

**Cómo se probó:** cada pantalla, en un navegador real (Chromium vía Playwright), no solo con tests de backend — capturas de pantalla, formularios completados de verdad, sesiones reales iniciadas y cerradas. Fue en estas pruebas donde aparecieron la mayoría de los bugs reales de la fase (ver §5).

## 4. Usuarios de prueba agregados en esta fase

Los tres primeros del proyecto — documentados en `documentacion/Usuarios.md`:

| Rol | Email | Password |
|---|---|---|
| CUSTOMER | `cliente@morficenter.test` | `cliente1234` |
| ADMIN | `admin@morficenter.test` | `admin1234` |
| DELIVERY | `repartidor@morficenter.test` | `repartidor1234` |

## 5. Decisiones y hallazgos no triviales

**Bugs reales encontrados por tests o por pruebas en navegador (no a simple vista):**

- **Carrera en el alta duplicada** (`T-1.3.1`): dos registros simultáneos con el mismo email pasaban el chequeo previo y uno chocaba contra el `UNIQUE` sin manejar — daba 500 en vez de 409. El `try` estaba envolviendo el bloque equivocado.
- **Misma familia de carrera en la rotación del refresh** (`T-1.4.4`): dos usos simultáneos del mismo token daban 500 en vez de 401 — justo el caso que la rotación existe para frenar.
- **Migración de Alembic autogenerada rota** (`T-1.2.3`): escribía `app.db.types.UTCDateTime()` sin importar `app` — habría explotado recién en el deploy automático al VPS, no en local. Se arregló de raíz con un `render_item` en `alembic/env.py` para toda migración futura, no solo esa.
- **`fileConfig` de Alembic apagaba los loggers de la app** (`T-1.10.1`): un test de `caplog` fallaba solo al correr la suite completa, porque correr las migraciones (alfabéticamente antes) silenciaba los logs para los tests siguientes.
- **Paso 1 de "recuperar contraseña" sin `hidden` por defecto** (`T-1.11.3`): con `?token=` en la URL, los dos pasos del formulario quedaban visibles a la vez. Lo agarró una aserción automatizada, no la vista.
- **La pestaña "activa" del menú estaba escrita a mano en el HTML** (`T-1.11.5`): invisible con una sola página (`index.html`), incorrecta apenas existió una segunda (`perfil.html`). Se corrigió con `ui.js#injectPartials` calculando sola la pestaña activa por URL, para toda página futura.
- **`UserOut` no incluía `status`** (`T-1.11.6`): el panel de admin no podía saber si ofrecer "Suspender" o "Reactivar".
- **Volver a leer después de escribir, sin reintentar** (`T-1.11.6`): crear/editar un usuario y refrescar la lista completa no garantizaba ver el cambio recién hecho en esta máquina de desarrollo — la tabla quedaba mostrando el dato viejo indefinidamente. Se arregló usando directamente la respuesta del propio `POST`/`PATCH` en vez de volver a preguntarle al servidor.

**La misma lección se repitió tres veces en la fase**, con causas distintas cada vez pero el mismo síntoma superficial ("lo que acabo de escribir no aparece al leerlo de nuevo, en esta máquina Windows"): un registro que no se veía al loguear inmediatamente después (`T-1.4.2`), un `seed` que fallaba con `ConflictError` contra un usuario que un `SELECT` directo no mostraba (`T-1.9.1`), y la tabla del admin (`T-1.11.6`). Se investigó a fondo cada vez (se descartó Google Drive, se descartó el caché del navegador con `cache: "no-store"`) y **se confirmó que no ocurre en producción** (Linux, VPS real) — es un comportamiento exclusivo de SQLite en este entorno de desarrollo puntual. La solución que quedó, y que debería aplicarse por default de acá en adelante: **cuando una mutación (POST/PATCH) ya devuelve el recurso actualizado, usar esa respuesta directamente en vez de volver a pedirle la lista al servidor** — no solo evita la demora, es además menos tráfico.

**Otras decisiones:**

- **Seguridad por diseño en toda la fase**: mismo mensaje y mismo tiempo de respuesta para no enumerar emails (`T-1.4.1`); refresh de un solo uso (`T-1.4.3`); un admin no puede tocarse a sí mismo (`T-1.7.2`); un link de recuperación muere si la contraseña ya cambió (`T-1.9.1`).
- **`UserOut` ganó `status`** en vez de crear un schema aparte para el admin: no es un dato sensible, ya se devolvía sin problema en `/auth/me`.
- **Sin jerarquía de roles** (`T-1.5.2`): un ADMIN no hereda automáticamente los permisos de DELIVERY. Cada permiso se declara explícito.
- **Los usuarios de prueba nunca se crean en producción** (`T-1.10.1`): sus contraseñas están en un repositorio público.

## 6. Pendientes / deuda técnica dejada para después

- **Login con Google, callback (`T-1.8.2`): en pausa a pedido del usuario.** El código está completo y cubierto por tests (simulando la respuesta de Google), pero falta cargar credenciales reales de Google Cloud para probarlo de punta a punta con una cuenta real. No bloquea nada del resto del proyecto — hasta entonces, el botón de Google responde con un mensaje claro y el login local funciona normal.
- **Recuperación de contraseña sin servicio de mail (`T-1.9.1`).** El link se escribe en el log del servidor en vez de enviarse por correo — funciona para probar, pero un cliente real todavía no puede recuperar su contraseña sola. Falta elegir y conectar un proveedor de envío (queda como tarea de infraestructura a definir).
- **La demora ocasional de lecturas justo después de escribir**, documentada en §5, es exclusiva de este entorno de desarrollo (Windows) y no afecta producción — no requiere una solución adicional, pero vale tenerla presente si vuelve a aparecer en fases futuras: la respuesta es usar el resultado de la propia mutación, no una relectura.
- Como en toda la Fase 1, el front de cliente sigue mostrando **solo** lo de usuarios — catálogo, carrito, pedidos, etc. llegan recién en las fases siguientes.
