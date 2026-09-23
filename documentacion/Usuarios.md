# Morfi Center · Usuarios de prueba

Se generan con `python -m app.db.seed` (desde `backend/`). El comando es **idempotente**: correrlo dos veces no duplica nada, así que se puede usar sin miedo cada vez que se recrea la base local.

## ⚠️ Solo desarrollo

Estas contraseñas son simples **y públicas** (este repositorio lo es), así que el seed **se niega a crear estos usuarios en producción**: crear ahí un admin con contraseña conocida por cualquiera sería dejar la puerta abierta. Si se corre con `APP_ENV=production`, avisa por log y no crea ninguno.

| Rol | Email | Password | Notas |
|---|---|---|---|
| CUSTOMER | `cliente@morficenter.test` | `cliente1234` | Tiene carrito vacío y saldo en $0 |
| ADMIN | `admin@morficenter.test` | `admin1234` | Acceso al panel de administración |
| DELIVERY | `repartidor@morficenter.test` | `repartidor1234` | Moto, capacidad 4, arranca `NO_DISPONIBLE` |

Los tres se crean `ACTIVE` y con ingreso por email + contraseña. Verificado: los tres loguean correctamente con estas credenciales y devuelven su rol (`T-1.10.1`).

## El primer admin de producción

En producción no hay usuarios, y crear uno por la API exige **ya ser admin**. Para resolver ese círculo, el seed crea un admin a partir de dos variables de entorno del servidor:

```bash
# en backend/.env del VPS, nunca en el repositorio
SEED_ADMIN_EMAIL=...
SEED_ADMIN_PASSWORD=...
```

Con esas variables cargadas, `python -m app.db.seed` crea ese admin (una sola vez; si ya existe, no hace nada). Sin ellas, no crea ninguno.

**Esas credenciales no se documentan acá ni en ningún archivo versionado.** Van en el gestor de contraseñas de quien administra, igual que el resto de los accesos del servidor (ver `Guia_Servidor_Contabo.md`).

Desde ese admin ya se pueden crear los demás usuarios del staff con `POST /api/v1/users`.
