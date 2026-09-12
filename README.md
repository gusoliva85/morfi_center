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
| Tareas programadas | APScheduler |

Estilo visual del front: **Artesanal · Cocina de Olla**
(`documentacion/mockups/04_Artesanal_Organico.html`, sistema de diseño en
`.claude/skills/morfi-frontend/`).

## Estructura

```
backend/    API, lógica de negocio, modelos, migraciones  (ver documentacion/02_Documento_Tecnico.md §4)
frontend/   páginas por rol, parciales y assets
documentacion/  documentos del proyecto
```

## Desarrollo local

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

Pensado para desplegarse como servicio (no como script local de un solo click).
La guía de despliegue se documenta a medida que se define la infraestructura
(ver `documentacion/03_Roadmap.md`).

## Documentación

| Documento | Contenido |
|---|---|
| `documentacion/MORFI_CENTER_INFO.md` | Especificación maestra del producto |
| `documentacion/01_Documento_General.md` | Documento general / funcional |
| `documentacion/02_Documento_Tecnico.md` | Arquitectura, modelo de datos, API, seguridad |
| `documentacion/03_Roadmap.md` | Fases y tareas de implementación |
| `documentacion/Usuarios.md` | Usuarios de prueba |
| `documentacion/mockups/` | Mockups de la pantalla principal |

## Estado

En desarrollo — Fase 0 y Fase 1 completas (andamiaje, usuarios/roles/autenticación);
Fase 2 (configuración y turnos) en curso. Ver el avance en `documentacion/03_Roadmap.md`.
