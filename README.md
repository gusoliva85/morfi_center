# Morfi Center

Plataforma de **pedidos anticipados de comida** con producción centralizada y
distribución programada. Los clientes hacen su pedido antes de una hora de cierre
configurable; luego la operación valida los pagos, consolida la producción y
organiza el reparto por zona.

- **Uso principal:** móvil (mobile-first), con versión web de escritorio adaptada.
- **Actores:** Cliente · Administrador · Repartidor.

## Stack

| Capa | Tecnología |
|---|---|
| Frontend | HTML + CSS + Tailwind + JavaScript (ES Modules) — multipágina |
| Backend | Python · FastAPI · SQLAlchemy · Alembic |
| Base de datos | SQLite (WAL) |
| Auth | JWT (access + refresh) + Google OAuth |
| Turnos y reservas de stock | Resueltos bajo demanda, sin tareas programadas (ver `documentacion/02_Documento_Tecnico.md §10`) |

Estilo visual del front: **Artesanal · Cocina de Olla**
(`documentacion/mockups/04_Artesanal_Organico.html`, sistema de diseño en
`.claude/skills/morfi-frontend/`).

## Estructura

```
backend/        API, lógica de negocio, modelos, migraciones  (ver documentacion/02_Documento_Tecnico.md §4)
frontend/       páginas por rol, parciales y assets
documentacion/  documentos del proyecto y cierres de fase (documentacion/Fases/)
deploy/         plantillas de despliegue (Nginx, systemd) y runbook del VPS
```

## Desarrollo local

No hay script de arranque de un clic: cada servicio se levanta a mano, en su propia terminal.

```bash
cd backend
python -m venv .venv && .venv/Scripts/activate   # o source .venv/bin/activate en Linux/Mac
pip install -r requirements.txt
alembic upgrade head
python -m app.db.seed          # usuarios y configuración de prueba (ver documentacion/Usuarios.md)
uvicorn app.main:app --reload --port 8000   # docs en /api/docs
```

En otra terminal, el frontend (estático, sin build):

```bash
python -m http.server 5500 --directory frontend
```

## Producción

- **Frontend** → Vercel (deploy automático al conectar el repositorio).
- **Backend + base de datos** → VPS propio (Contabo), con Nginx + Uvicorn (`systemd`) + HTTPS y despliegue continuo vía GitHub Actions en cada push a `master`.

Detalle completo en `documentacion/02_Documento_Tecnico.md §24.4` y en el runbook `deploy/DEPLOY.md` (sin credenciales — esas viven solo en el VPS y en los secrets de GitHub Actions).

## Documentación

| Documento | Contenido |
|---|---|
| `documentacion/01_Documento_General.md` | Documento general / funcional |
| `documentacion/02_Documento_Tecnico.md` | Arquitectura, modelo de datos, API, seguridad, despliegue |
| `documentacion/03_Roadmap.md` | Fases y tareas de implementación |
| `documentacion/Fases/` | Cierre de cada fase completada (qué se hizo, cómo quedó, código) |
| `documentacion/Usuarios.md` | Usuarios de prueba (se crea en la Fase 1) |
| `documentacion/mockups/` | Mockups de la pantalla principal |

## Estado

En reconstrucción desde `T-0.1.1` — ver el avance en `documentacion/03_Roadmap.md`.
