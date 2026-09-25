# Fase 02 · Configuración del sistema y turnos

**Estado:** Completa y aprobada
**Fecha de cierre:** 2026-09-24
**Roadmap:** `03_Roadmap.md` — Fase 2

---

## 1. Objetivo

Que el home deje de mostrar un contador inventado (`01:42:15`) y pase a reflejar **el turno real, configurable por el admin**: cuándo abre, cuándo cierra, cuánto falta, hasta cuándo se puede cancelar. Para eso la fase construye dos cosas que el resto del proyecto va a usar todo el tiempo:

1. **La configuración del negocio** (`system_settings`): horarios, zona horaria, envío, datos de transferencia, etc., editables desde el panel de admin sin tocar el servidor.
2. **El turno** (`shifts`): la ventana diaria en la que se puede pedir, con su ciclo de vida (por abrir → abierto → cerrado → en producción), sin ningún proceso de fondo.

## 2. Temas y tareas cerradas

| Tema | Tareas |
|---|---|
| 2.1 · `system_settings` | T-2.1.1, T-2.1.2, T-2.1.3, T-2.1.4 |
| 2.2 · Turnos | T-2.2.1, T-2.2.2, T-2.2.3, T-2.2.4 |
| 2.4 · Endpoint del turno y front | T-2.4.1, T-2.4.2, T-2.4.3, T-2.4.4 |

> El roadmap no tiene un Tema 2.3: la numeración salta de 2.2 a 2.4. No falta ninguna tarea; es solo el número.

**Endpoints nuevos:**

| Método y ruta | Quién | Para qué |
|---|---|---|
| `GET /api/v1/settings` | admin | Las 11 configuraciones (guardadas o con su valor por defecto) |
| `PUT /api/v1/settings/{key}` | admin | Cambiar una configuración (validada, con auditoría) |
| `GET /api/v1/shift/current` | público | Estado del turno de hoy para el home |
| `GET /api/v1/shift` | admin | Listar turnos (`?date=`, paginado) |
| `PATCH /api/v1/shift/{id}` | admin | Ajustar horarios / ventana de cancelación de un turno |
| `POST /api/v1/shift/{id}/transition` | admin | `open` · `close` · `to_production` |

**Migraciones nuevas:** `91da6202efd6` (`system_settings`), `bd8b80aca114` (`shifts`), `fc1ed56c4a3d` (columna `shifts.closed_effects_applied_at`).

**Pantallas nuevas:** contador real en el home y en el header (todas las páginas con header), y `pages/admin/configuracion.html`.

## 3. Qué se hizo y cómo quedó implementado

### Tema 2.1 · `system_settings`

**En palabras:** una tabla clave/valor donde el valor es **siempre JSON real**; el tipo (`json`/`string`/`int`/`bool`) se infiere solo al guardar (con el `bool` chequeado antes que el `int`, porque en Python `True` "es" un entero). Sobre esa tabla, `SettingsService` conoce **las 11 claves permitidas** (una clave inventada da 404, no crea una configuración nueva) y, para cada una, su **forma** (Pydantic estricto: `"40"` no es un `40`, los objetos rechazan campos de más), su **valor por defecto** y su descripción. Una clave sin guardar rige por su default: el sistema anda desde el primer día. Al guardar se valida y se guarda la forma **canónica** (sin espacios sobrantes, días ordenados), con auditoría de antes/después; un PUT que no cambia nada no escribe ni audita.

Reglas de negocio dentro de los "moldes": el turno cierra después de abrir; la ventana de cancelación no puede ser más larga que el turno; `weekdays` va de 1 (lunes) a 7 (domingo) sin repetir; los rangos de envío van de menor a mayor distancia; el CBU, si se carga, tiene 22 dígitos; el prefijo de pedido son 1–6 letras mayúsculas o números.

**Código clave** (`backend/app/services/settings_service.py`): una sola fuente de verdad por clave.

```python
@dataclass(frozen=True)
class SettingSpec:
    key: SettingKey
    adapter: TypeAdapter   # cómo validarla
    default: Any           # valor JSON con el que arranca
    description: str       # el texto que muestra el panel de admin
```

`GET /settings` devuelve siempre las 11 (con `is_default: true` las que nadie tocó); el seed (`python -m app.db.seed`) las "materializa" como filas sin pisar nunca lo que un admin cambió.

**Cómo se probó:** ~140 tests entre repositorio, servicio, API y seed: los 11 defaults pasan su propio molde; guardar inválido (tipo, rango, campo de más, horario incoherente, tiers desordenados, CBU corto, zona inexistente) da 422 **sin escribir ni auditar nada**; cliente y repartidor → 403; un dato corrupto en la base da `SETTING_CORRUPT` al usarlo pero se puede **ver y reparar desde el panel**; el seed es idempotente y no pisa cambios.

### Tema 2.2 · Turnos

**En palabras:** el turno guarda sus horarios como **texto de hora local** (`"08:00"`) y su fecha local; convertirlos a instantes UTC lo hace `ShiftService` con la zona configurada. **El estado abierto/cerrado no se guarda: se deriva de la hora**, así que no hay nada que "abrir" ni "cerrar" por un job y dos consultas con el mismo `now` dan siempre lo mismo. Abre en la hora de apertura (inclusive) y cierra en la de cierre (**exclusive**: a las 12:00 en punto ya está cerrado).

**Código clave** (`backend/app/services/shift_service.py`):

```python
def current_status(shift: Shift, now: datetime, tz: str) -> ShiftStatus:
    window = resolve_window(shift, tz)
    if now < window.open_at:
        return ShiftStatus.SCHEDULED
    if now < window.close_at:
        return ShiftStatus.OPEN
    return ShiftStatus.CLOSED
```

Lo que **sí** necesita recordarse se guarda: `IN_PRODUCTION`/`DISPATCHING`/`FINISHED` (acciones del admin) y una marca de "los efectos del cierre ya se aplicaron".

- **`ensure_today_shift`** crea el turno de hoy con la plantilla la primera vez que alguien lo necesita (el home, un pedido, el panel), solo en los días de operación. "Hoy" es la fecha **local** (a las 23:00 de Buenos Aires ya es el día siguiente en UTC, pero el turno sigue siendo el de hoy). Un turno ya creado no se toca aunque después cambie la plantilla. Si dos visitas lo crean a la vez, la base frena a la segunda (`UNIQUE`) y se devuelve el ganador.
- **`on_shift_closed`** aplica **una sola vez** los efectos del cierre (hoy ninguno: la Fase 4 congelará el stock y la 11 marcará pedidos críticos, registrándolos con `register_close_effect`). La garantía la da la base, no el código:

```python
claimed = self.session.execute(
    update(Shift)
    .where(Shift.id == shift.id, Shift.closed_effects_applied_at.is_(None))
    .values(closed_effects_applied_at=now)
).rowcount
if claimed == 0:
    self.session.refresh(shift)  # otro request ya lo aplicó: no repetir
    return False
```

  La marca y los efectos van en la misma transacción: si un efecto falla, se deshace todo y el próximo request reintenta.
- **`to_production`**: solo un admin, solo después del cierre, una sola vez, y deja rastro en `audit_log`.

**Cómo se probó:** ~85 tests: conversión a UTC (incluidas otras zonas y horario de verano), los bordes de segundo a segundo, día no operativo, "hoy" local vs. UTC, la carrera de creación simulada **contra el `UNIQUE` real**, y la de los efectos del cierre con una vista vieja del turno. Verificado que el test de esa carrera **falla si se quita la condición del `UPDATE`** (o sea, protege lo que dice proteger).

### Tema 2.4 · Endpoint del turno y front

**`GET /shift/current`** (público, `no-store`) devuelve el estado, los instantes ya resueltos en UTC (`open_at`, `close_at`, `cancel_deadline`), `seconds_to_close`, la hora del servidor (`now`) y `ordering_open`. Un día sin servicio responde **200 con `status: "NO_SERVICE"`**, no un error. Es también quien dispara, de forma perezosa, la creación del turno y el cierre.

**Admin de turnos.** *Abrir ahora* y *Cerrar ahora* no fuerzan un estado (no existe uno guardado): **mueven el horario al minuto actual** (redondeado hacia abajo, para que el turno ya quede en el estado pedido), y cerrar aplica los efectos en el acto. Las transiciones sin sentido dan 409 sin tocar nada. `PATCH` valida el turno **resultante** con las mismas reglas que la plantilla, y una vez aplicados los efectos del cierre **ya no se pueden cambiar** apertura, cierre ni ventana de cancelación (reabrir no deshace lo que el cierre ya hizo); las horas estimadas se pueden corregir siempre.

**Front del contador** (`assets/js/countdown.js`): un solo reloj por página, compartido por el chip del header y el ticket del home. Corrige la diferencia entre el reloj del celular y el del servidor, y **cambia de estado solo** al pasar la hora de apertura o de cierre — pero quien manda es el servidor (en cada cambio vuelve a preguntar, porque el admin pudo mover horarios; también se re-sincroniza cada 5 minutos y al volver a la pestaña).

```js
// El servidor midió `now` a mitad de camino entre el envío y la respuesta.
offset = Date.parse(res.now) - (sentAt + Date.now()) / 2;
```

Estados: consultando (texto neutro, nada que pueda ser falso), por abrir, abierto (con "Cancelás hasta 11:40" que pasa a "Ya no se puede cancelar"), cerrado (también si el admin ya arrancó la cocina), sin servicio y error (reintenta cada 15 s).

**Pantalla `configuracion.html`:** plantilla del turno (horarios, ventana, días), zona horaria, y un bloque "Turno de hoy" con el estado y los botones *Abrir ahora / Cerrar ahora / Empezar a cocinar*. Editar la plantilla solo afecta a los turnos que se creen desde ahora, así que el formulario trae la casilla **"Aplicar también al turno de hoy"** (visible solo si ese turno todavía se puede editar). Guardar hace hasta tres pasos en orden (plantilla → zona → turno de hoy), informa qué quedó hecho si alguno falla, y muestra los errores del backend debajo de cada campo.

**Cómo se probó:** 58 tests de API para los endpoints del turno (público y de admin: permisos, forma exacta de la respuesta, cada transición válida e inválida, auditoría, bloqueo tras el cierre) y, para el front, todo en un navegador real (Chromium) contra el backend local:

```
Home, escritorio y celular a la vez, con el turno configurado para cerrar en ~2 min:
  21:11:31  chip ⏳ 00:01:29 · "La olla está abierta" · "hasta las 9:13 de la noche"
  21:12:00  "Cancelás hasta 21:12"  ->  "Ya no se puede cancelar"
  21:13:00  chip "Cerrado" · "Pedidos cerrados por hoy"   (sin recargar, en los dos)
Con respuestas del servidor simuladas: por abrir (y el paso a abierto solo), día sin servicio,
turno en cocina, servidor caído con reintento a los 15 s, celular con 10 min de desfase
(mostró los 90 s reales).
Configuración: el admin edita cierre y ventana, guarda, y GET /shift/current devuelve
close_time 23:30 y cancel_deadline_time 22:45.
```

## 4. Usuarios de prueba agregados en esta fase

Ninguno. Se usaron los tres de la Fase 1 (`documentacion/Usuarios.md`); el admin de prueba para probar `configuracion.html`.

## 5. Decisiones y hallazgos no triviales

**Contradicciones del propio diseño que se resolvieron:**

- **¿Qué zona horaria manda?** El documento técnico decía dos cosas: la variable `APP_TIMEZONE` (§17) y la configuración `timezone` (§6.11/§9.9). Se decidió que **manda la configuración de la base** (el admin la cambia sin tocar el servidor) y que `APP_TIMEZONE` es solo su **valor inicial**. Documento técnico actualizado.
- **"Forzar abrir/cerrar" no cabía en un estado derivado** (`T-2.4.2`): si el estado sale de la hora, no hay un interruptor que accionar. Se resolvió moviendo el horario al minuto actual, en vez de inventar un segundo modelo (un estado forzado que conviviera con el derivado).
- **La tabla "Estado global" del roadmap seguía marcando la Fase 1 como pendiente** después de cerrarla. Corregido junto con este cierre.

**Errores encontrados (y de quién eran):**

- `audit_log` (Fase 1) nunca se había sumado al test que compara el esquema migrado contra los modelos; lo detectó la migración de `system_settings`.
- Dos veces un **test mío estaba mal y la API bien**: una cuenta de segundos (52 min 30 s son 3150, no 2550) y un test que intentaba probar el `CHECK` de la base pero SQLAlchemy frenaba el valor antes. En ambos casos se corrigió el test, no el código.
- **El estado de error del contador parecía no recuperarse**: era mi comprobación, que miró unos segundos antes del reintento (que sale a los 15 s). Verificado con un registro con marcas de tiempo.
- **Un destello de 0,15 s en las pastillas de los días** de `configuracion.html`: lo primero que se supuso (Tailwind tardando en generar estilos) era **incorrecto**; medido, era la animación de color al rellenar el formulario. Se quitó la animación.
- **El chip de otras páginas seguía mostrando `01:42:15`**: el header es un parcial compartido, así que conectar el contador solo al home dejaba a "Mi cuenta" con la hora falsa. Se conectó en toda página que use el header.
- **Faltaba "Cerrar sesión" en el celular** (pedido del usuario durante la fase): existía solo en el header de escritorio; se agregó una tarjeta "Sesión" en "Mi cuenta".

**Otras decisiones:**

- **Los defaults de la transferencia salen vacíos** (salvo el alias): no se le muestra a un cliente un CBU inventado.
- **Un dato corrupto falla fuerte** (`SETTING_CORRUPT`) en el código de negocio en vez de asumir un default: un horario o una cuenta equivocados salen más caros que un error claro. En el panel sí se ve y se repara.
- **`GET /shift/current` escribe** (crea el turno, aplica el cierre) siendo un GET. Es idempotente, va con `no-store`, y evita cualquier job; es la contrapartida de "todo se resuelve bajo demanda".
- **Auditoría unificada** en los turnos (`shift.update/open/close/to_production`): `before`/`after` son objetos con solo los campos que cambiaron.
- **`ensure_today_shift` debe llamarse al principio del flujo**: ante una carrera hace `rollback` de la transacción entera (mismo patrón que el registro), lo que descartaría lo pendiente sin guardar.
- Los avisos `UP042` de Ruff (22, en `core/enums.py`) son de una versión más nueva de Ruff y ya estaban antes de la fase; no se tocaron.

## 6. Pendientes / deuda técnica dejada para después

- **Producción todavía no tiene un admin.** Sin usuarios en el servidor real, el panel de configuración no se puede usar ahí. Hace falta cargar `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` en el VPS y correr el seed (ver `Usuarios.md` y `deploy/DEPLOY.md`). Con el admin creado, **cargar los datos de transferencia reales** (`payment.transfer`: hoy sin CBU ni titular) **antes de abrir al público**.
- **El deploy automático no corre el seed** (`deploy/DEPLOY.md §7.5`): las configuraciones no están guardadas como filas en el servidor hasta que alguien lo corra a mano. La app anda igual con los defaults. Es una línea en el workflow si se prefiere automatizar; cuando llegue el catálogo demo (Fase 3) habrá que separar qué del seed es seguro para producción.
- **Verificación en producción de esta fase:** se comprobó, sin escribir nada, que las rutas nuevas existen en el servidor real (`/settings` y `/shift` piden sesión, `/shift/{id}` existe para `PATCH`); como el workflow corre las migraciones con `set -e` antes de reiniciar, que estén vivas implica que las tres migraciones se aplicaron. **No se llamó a `GET /shift/current` en producción** para no crear filas allí desde una verificación, ni se pudo consultar el historial de Actions (el repo es privado). La primera visita real al home creará el primer turno.
- **Solo 2 de las 11 configuraciones tienen pantalla** (plantilla del turno y zona horaria). Las otras 9 (cobertura, envío, transferencia, TTL de reservas, desempate de promos, prefijo de pedidos) ya tienen API, validación y auditoría, pero cada fase que las use suma su pantalla.
- **Piezas que esperan a fases posteriores:** los efectos del cierre (congelar `product_stock`, Fase 4; marcar pedidos críticos, Fase 11) y el paso masivo `PAYMENT_APPROVED → IN_PREPARATION` de `to_production` (Fase 9) — el punto de enganche ya existe.
- **`format.js` sigue con la zona de Buenos Aires escrita fija** para `formatDate`/`formatTime`; debe salir de la configuración cuando esas funciones se usen con horarios reales (Fase 6 en adelante). `GET /shift/current` ya devuelve `cancel_deadline_time` en hora local justamente para que el contador no dependa de eso.
- **Sigue en pausa lo de la Fase 1** (a pedido del usuario): login con Google con credenciales reales (`T-1.8.2`) y un servicio de mail para recuperar contraseña (`T-1.9.1`).
- El carrito del header (la insignia "3") y la barra de carrito siguen con datos fijos hasta la Fase 6.
