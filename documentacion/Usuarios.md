# MORFI CENTER
## Usuarios de prueba

> Todas las credenciales de este archivo son **de prueba** (entorno de desarrollo).
> Contraseñas simples a propósito. No usar estos datos en producción.
> Se cargan mediante `python -m app.db.seed` (idempotente).

**Última actualización:** 11 de septiembre de 2026 — creados por `db/seed.py` (`T-1.10.1`)

---

## Credenciales

| Rol | Email | Contraseña | Estado | Notas |
|---|---|---|---|---|
| ADMIN | `admin@morficenter.test` | `admin123` | ✅ activo | Acceso total al panel administrativo |
| CUSTOMER | `cliente@morficenter.test` | `cliente123` | ✅ activo | Cliente con carrito y saldo en $0 |
| DELIVERY | `delivery@morficenter.test` | `delivery123` | ✅ activo | Repartidor (moto, capacidad 3) |

Leyenda de estado: ⬜ pendiente (aún no lo genera el seed) · ✅ activo · ⏸️ suspendido

---

## Cómo se crean

- **ADMIN, CUSTOMER y DELIVERY**: los inserta `db/seed.py` (`seed_users()`, tarea `T-1.10.1`).
  Idempotente: correr `python -m app.db.seed` de nuevo no los duplica.
- Se pueden crear repartidores/admins adicionales desde `pages/admin/usuarios.html`
  (`T-1.11.6`), o con `POST /api/v1/users` (`T-1.7.1`).
- Al ejecutarse el seed, se actualiza la columna **Estado** de este archivo.

## Registro de altas durante el desarrollo

A medida que se creen más usuarios de prueba (más clientes, más repartidores, un
segundo admin, etc.), se agregan acá con su rol, email, contraseña y para qué se usan.

| Fecha | Rol | Email | Contraseña | Motivo |
|---|---|---|---|---|
| — | — | — | — | — |

---

## Notas de seguridad

- Este archivo vive solo en el repositorio de desarrollo.
- En producción los usuarios reales se crean por el flujo de registro / alta de staff;
  no existe un seed de credenciales.
- El `.env` (con `JWT_SECRET`, claves de Google, etc.) **no** se versiona: ver `backend/.env.example`.
