# Morfi Center · Guía del servidor (Contabo / VPS)

> **Para qué sirve este documento:** explicar en criollo qué es el servidor que estás pagando, qué tiene adentro, cómo se entra, y cómo se relaciona todo esto con la app. Es el documento "para entender"; el paso a paso técnico con comandos exactos para reconstruirlo ya existe en [`deploy/DEPLOY.md`](../deploy/DEPLOY.md) — este documento es el que explica el *por qué* de cada cosa que hay ahí.
>
> Referencia cruzada: `03_Roadmap.md`, Fase 0 → Tema 0.7 (todas las tareas de despliegue).

---

## 1. ¿Qué es Contabo? ¿Qué es un VPS?

**Contabo** es una empresa que alquila servidores. Le pagás una cuota (en tu caso, un plan anual) y a cambio tenés una computadora prendida 24 horas al día, todos los días, conectada a internet, en un data center de ellos. Vos no la ves ni la tocás físicamente — te conectás a ella por internet, desde tu propia PC.

Eso que alquilaste se llama **VPS** (*Virtual Private Server* / servidor privado virtual). La palabra clave es **privado**: aunque la máquina física de Contabo probablemente esté compartida con otros clientes, tu "porción" funciona como si fuera una computadora entera y exclusiva tuya. Podés instalar lo que quieras, borrar lo que quieras, y nadie más tiene acceso — a diferencia de un "hosting compartido" (como los planes baratos de hosting de páginas web), donde estás mucho más limitado en lo que podés instalar y configurar.

**Analogía:** un hosting compartido es como alquilar un escritorio en una oficina compartida. Un VPS es como alquilar tu propia oficina con llave propia, dentro de un edificio que administra otra empresa. Vos decidís qué muebles poner (qué programas instalar), pero el edificio (la luz, el internet, la seguridad física) lo mantiene Contabo.

### Lo que contrataste específicamente

| Ítem | Valor |
|---|---|
| Proveedor | Contabo |
| Plan | 4 vCPU (núcleos de procesador virtuales) / 8 GB de RAM / 100 GB de disco |
| Sistema operativo | Ubuntu (una distribución de Linux) |
| Forma de pago | Plan anual |
| Dirección pública (IP) | `13.140.36.93` |

Esa **IP** es literalmente la "dirección postal" de tu servidor en internet. Cualquier cosa que quiera hablar con tu backend (el navegador de un cliente, GitHub, vos desde tu PC) le habla a esa dirección. No es un secreto — de hecho ya está escrita en el código del frontend (`frontend/index.html`), porque el navegador del cliente necesita saber a dónde mandar los pedidos. Lo que **sí** es secreto es cómo entrar a manejarla (ver sección 3).

---

## 2. ¿Qué hay corriendo adentro, en criollo?

Pensá el servidor como un edificio con varios empleados, cada uno con un trabajo puntual. Ahora mismo, adentro de tu VPS conviven:

```
Internet
   │
   ▼
┌─────────────────────────────────────────────┐
│   NGINX  (el/la recepcionista)               │
│   - Atiende todo lo que llega por 80 y 443   │
│   - Redirige http:// → https://              │
│   - Tiene el "candado" (certificado HTTPS)   │
└───────────────┬───────────────────────────────┘
                │  le pasa el pedido para adentro
                ▼
┌─────────────────────────────────────────────┐
│   UVICORN, corriendo tu backend en Python    │
│   (FastAPI) — el "cerebro" de Morfi Center   │
│   - Mantenido prendido por systemd            │
│   - Servicio: morficenter-api                │
└───────────────┬───────────────────────────────┘
                │  lee/escribe
                ▼
┌─────────────────────────────────────────────┐
│  Archivos en disco:                          │
│  - morfi.db (base de datos SQLite)           │
│  - storage/payment_proofs/ (comprobantes)    │
└─────────────────────────────────────────────┘
```

Cada pieza, explicada:

- **Nginx** — es lo primero que recibe cualquier visita de internet a tu servidor. Su trabajo es: escuchar en las "puertas" 80 (HTTP normal) y 443 (HTTPS, la segura), poner el candado de seguridad, y reenviar el pedido hacia adentro, a donde está corriendo tu programa de verdad. Sin Nginx, tu backend estaría "desnudo" hacia internet, sin HTTPS y compitiendo directamente por esas puertas.
- **Certbot** — es quien consiguió gratis el "candado" (certificado HTTPS/SSL) y lo va renovando solo antes de que venza. Sin él, el navegador mostraría "sitio no seguro".
- **Uvicorn** — es el programa que efectivamente ejecuta tu código Python (FastAPI). Es tu aplicación en sí, corriendo.
- **systemd** (el servicio `morficenter-api`) — es el "supervisor" que mantiene Uvicorn siempre prendido. Si el proceso se cae por cualquier motivo, systemd lo vuelve a levantar solo. También hace que arranque automáticamente si el servidor se reinicia (por ejemplo, tras una actualización de Ubuntu).
- **morfi.db** — es un único archivo (base de datos SQLite) donde vive absolutamente toda la información: usuarios, pedidos, productos, todo. Por eso los backups (sección 6) son tan importantes: si se pierde ese archivo, se pierde la base de datos entera.
- **`storage/payment_proofs/`** — carpeta donde se guardan las imágenes/comprobantes de pago que suben los clientes.

### El truco del "candado sin dominio propio" (sslip.io)

Para tener HTTPS (el candado), normalmente hace falta un **dominio** (algo como `morficenter.com`). Como todavía no compraron uno, se usa un servicio gratuito llamado **sslip.io**, que convierte tu IP en un nombre válido: `13.140.36.93` se transforma en `13-140-36-93.sslip.io`. Es un truco 100% legítimo y gratis, pero el día que compren un dominio propio, se cambia por ese y listo (queda anotado como mejora futura).

---

## 3. ¿Cómo se entra al servidor? (acceso)

Para "entrar" a manejar el servidor (instalar cosas, ver logs, reiniciar el programa a mano) se usa una tecnología llamada **SSH** — es básicamente abrir una terminal de comandos, pero de una computadora que está en otro lado del mundo, como si estuviera en tu escritorio.

### Usuario y contraseña vs. llaves

Lo normal (y lo más inseguro) sería entrar con un usuario y contraseña, como al Home Banking. Contabo lo entrega así por default (usuario `root`, con una contraseña que te mandan por email). **Eso se desactivó a propósito.** En cambio, se usa un sistema de **llaves criptográficas**:

- Generás un par de archivos en tu computadora: una **llave privada** (nunca se comparte, ni conmigo, ni se sube a ningún lado) y una **llave pública** (esa sí se puede compartir, no sirve para nada sola).
- Copiás la llave pública al servidor.
- A partir de ahí, tu computadora demuestra "soy yo" mostrando que tiene la llave privada que hace pareja con esa pública — sin escribir ninguna contraseña.

**Analogía:** es como una cerradura que en vez de combinación numérica, usa una llave física. Cualquiera puede ver la cerradura (la llave pública), pero solo entra quien tiene la llave física exacta (la privada).

### Cómo queda configurado hoy

- **Usuario para entrar:** `morfi` (un usuario normal, sin privilegios de administrador por default).
- **`root` (el superusuario) está desactivado** para entrar directo — ni con contraseña, ni siquiera con llave. Hay que entrar como `morfi` primero.
- **Login por contraseña: desactivado por completo.** Solo funciona con llave.
- Para tareas que necesitan permisos de administrador (instalar algo, reiniciar servicios del sistema), el usuario `morfi` usa el comando `sudo`, que sí pide una contraseña interactiva — **excepto** por un único comando específico que quedó habilitado sin pedir contraseña (reiniciar el programa de Morfi Center), para que la automatización de despliegue (sección 5) pueda funcionar sola. Ese es el único permiso "sin llave" que existe, y está limitado a esa sola acción.

### El firewall (ufw) — qué puertas están abiertas

Un **firewall** es literalmente eso: un muro que bloquea todo el tráfico de red excepto el que decidas dejar pasar explícitamente. En tu servidor solo estas 3 "puertas" (puertos) están abiertas hacia internet:

| Puerto | Para qué |
|---|---|
| 22 | SSH (para que vos puedas entrar a administrar) |
| 80 | HTTP (tráfico web normal, que Nginx redirige a 443) |
| 443 | HTTPS (tráfico web seguro, el que usa la app en producción) |

Todo lo demás está bloqueado. Esto reduce muchísimo la superficie de ataque: aunque instales algo nuevo que abra otro puerto por error, nadie de afuera puede llegar a él mientras el firewall no lo permita explícitamente.

### Cómo entrar (comando real)

Desde tu PC, con la llave que ya está configurada:

```powershell
ssh morfi@13.140.36.93
```

No debería pedir contraseña. Si alguna vez te la pide, algo cambió y hay que revisar (ver `deploy/DEPLOY.md §1`).

---

## 4. ¿Cómo llega el código nuevo al servidor? (despliegue automático / CI/CD)

Esta es la parte "mágica" que hace que no tengas que entrar a mano cada vez que se aprueba una tarea.

**CI/CD** son siglas en inglés (*Continuous Integration / Continuous Deployment*) que significan, en criollo: *"cada vez que subís código, una máquina lo prueba y/o lo lleva sola a producción, sin que un humano tenga que hacerlo a mano"*.

En Morfi Center funciona así:

1. Aprobás una tarea → se hace `git push` a la rama `master` (esto ya lo hacemos juntos como parte del flujo normal).
2. Eso dispara automáticamente un robot de **GitHub Actions** (un servicio de GitHub que ejecuta tareas automáticas cuando pasa algo en el repositorio).
3. Ese robot se conecta por SSH a tu VPS **con una llave dedicada solo para esto** (no la tuya personal) y ejecuta, él solo:
   - `git pull` (trae el código nuevo)
   - Si cambiaron las dependencias, las reinstala
   - `alembic upgrade head` (aplica cambios pendientes a la base de datos, si los hay)
   - Reinicia el programa (`systemctl restart morficenter-api`) — usando exactamente el único permiso sin contraseña que mencionamos en la sección 3.
4. A los pocos segundos, tu backend en producción ya tiene el código nuevo corriendo.

El archivo que define estos pasos es [`.github/workflows/deploy-backend.yml`](../.github/workflows/deploy-backend.yml). Las credenciales que ese robot usa (la IP, el usuario, la llave privada dedicada) **no están en el repositorio** — viven guardadas en GitHub, en un lugar especial para secretos (*Settings → Secrets and variables → Actions*, en el repo), que ni siquiera se puede volver a leer una vez guardado, solo reemplazar.

> El frontend (la parte visual) no necesita nada de esto: **Vercel** ya redespliega solo apenas detecta un `push` al repositorio, sin ningún script adicional.

---

## 5. ¿Qué pasa con los datos? (backups)

Todos los días a las 3 AM, un cron (una tarea programada del sistema operativo, la versión de Linux de un "recordatorio automático") corre un script (`deploy/backup.sh`) que copia:

- `morfi.db` (la base de datos completa)
- `storage/payment_proofs/` (los comprobantes subidos)

...a una carpeta con fecha, dentro de `~/backups/`. Se guardan los últimos 14 días; los más viejos se van borrando solos para no llenar el disco.

Esto vive **en el mismo servidor** (no en otro lugar todavía) — es una primera red de seguridad ante "borré algo por error" o "se corrompió el archivo", pero no protege si el servidor entero se pierde (por ejemplo, si Contabo tuviera un desastre total). Eso quedaría como una mejora futura (backup en otro lugar, como un servicio de almacenamiento externo).

---

## 6. La otra mitad: el frontend en Vercel

Todo lo de arriba es la mitad "backend" (el cerebro + los datos). La otra mitad, la parte visual que ve el cliente en el navegador, **no vive en el VPS** — vive en **Vercel**, un servicio gratuito (mientras el proyecto sea chico) que está pensado justo para eso: sitios que son solo HTML/CSS/JS, sin necesidad de un servidor propio.

Como quedan en dos lugares distintos (`https://morfi-center.vercel.app` por un lado, `https://13-140-36-93.sslip.io` por el otro), el navegador los trata como "sitios distintos" por seguridad, y hace falta una configuración especial llamada **CORS** para que se dejen hablar entre sí. Esto ya está resuelto y funcionando (backend configurado para aceptar pedidos que vengan específicamente de esa URL de Vercel, ni una más).

---

## 7. Qué es secreto y qué no

| Dato | ¿Es secreto? | ¿Dónde vive? |
|---|---|---|
| IP del servidor (`13.140.36.93`) | No — ya está en el código del frontend, el navegador del cliente necesita saberla | Repositorio (`frontend/index.html`) |
| Usuario SSH (`morfi`) | No especialmente, pero no se publicita | `deploy/DEPLOY.md` (como ejemplo) |
| Llave SSH privada (la tuya, personal) | **Sí, secreto absoluto** | Solo tu PC (`~/.ssh/`) |
| Llave SSH privada (la dedicada a GitHub Actions) | **Sí, secreto absoluto** | Solo dentro de GitHub Secrets |
| Contraseña de `sudo` | **Sí, secreto** | Solo la sabés vos |
| `JWT_SECRET`, credenciales de Google OAuth, etc. | **Sí, secreto** | Solo en el archivo `.env` real, dentro del servidor — nunca en el repositorio |

Regla de oro del proyecto (ya la venimos siguiendo): **ningún secreto real se escribe en ningún archivo versionado en git.** Todo lo que hace falta para reconstruir el despliegue desde cero, sin secretos, está en `deploy/DEPLOY.md`.

---

## 8. Cómo revisar vos mismo que todo sigue en pie

No necesitás depender de que yo lo revise — estos comandos los podés correr cuando quieras, desde una PowerShell en tu PC:

```powershell
# ¿El backend responde?
curl https://13-140-36-93.sslip.io/api/v1/health

# ¿El frontend responde?
curl -o NUL -w "%{http_code}`n" https://morfi-center.vercel.app/

# Entrar al servidor y ver si el programa está prendido + qué versión del código tiene
ssh morfi@13.140.36.93 "systemctl is-active morficenter-api && cd ~/morfi_center && git log -1 --oneline"

# Ver si los backups se siguen generando
ssh morfi@13.140.36.93 "ls -la ~/backups | tail -5"
```

Y en GitHub, en la pestaña **Actions** del repositorio, tenés que ver el último workflow `Deploy backend to VPS` en verde (✅), no en rojo.

---

## 9. Para tus próximos proyectos: qué de todo esto se repite siempre

Esto es lo importante para generalizar: **no importa qué apliques hagas en el futuro (con Python, Node, lo que sea)**, si querés tenerla en producción con tu propio servidor (en vez de un servicio todo-en-uno tipo Vercel/Railway), casi siempre vas a necesitar las mismas piezas:

1. **Un servidor** (VPS, como este de Contabo, o cualquier otro proveedor — DigitalOcean, Hetzner, AWS, etc. — el concepto es idéntico).
2. **Un usuario sin privilegios + acceso por llave SSH**, nunca trabajar como `root` ni con contraseña.
3. **Un firewall** que bloquee todo excepto lo que tu app necesita (normalmente: SSH + HTTP + HTTPS).
4. **Un proceso que corra tu programa** (en Python suele ser Uvicorn/Gunicorn; en Node sería el propio `node`, etc.).
5. **Un supervisor que lo mantenga prendido** (`systemd` en Linux es el estándar — le decís "esto tiene que estar siempre corriendo" y él se encarga).
6. **Un reverse proxy** (Nginx, o su alternativa Caddy/Traefik) delante de tu programa — te da HTTPS gratis (con Certbot o similar) y te permite, el día de mañana, **tener más de un proyecto en el mismo servidor** (cada proyecto con su propio "bloque" de configuración en Nginx, escuchando en un puerto interno distinto, pero todos compartiendo los mismos 80/443 hacia afuera).
7. **Backups automáticos** de lo que sea que guarde datos (base de datos, archivos subidos).
8. **Automatizar el despliegue** (CI/CD) para no tener que entrar a mano cada vez — opcional al principio, pero ahorra muchísimo tiempo ni bien el proyecto crece.

> **Nota para más adelante:** un mismo VPS puede alojar **varios proyectos a la vez**, siempre que los recursos (CPU/RAM/disco) alcancen — cada uno con su propio servicio `systemd` y su propio bloque de Nginx. Vi en tu configuración de SSH una entrada llamada `contabo-chillgames` que apunta a esta misma IP (`13.140.36.93`) — si ya tenés (o estás armando) otro proyecto ahí, avisame y documentamos cómo convive con Morfi Center sin pisarse.

---

## 10. Glosario rápido

- **VPS**: servidor privado virtual — tu "computadora alquilada" prendida 24/7.
- **SSH**: forma segura de conectarte por terminal a una computadora remota.
- **Llave pública/privada**: par de archivos que reemplazan la contraseña para entrar por SSH; la privada nunca se comparte.
- **Firewall / `ufw`**: filtro que bloquea todo el tráfico de red excepto los puertos que explícitamente permitís.
- **Puerto**: número que identifica "a qué servicio" le hablás dentro de una misma IP (80=web, 443=web segura, 22=SSH, etc.).
- **Nginx**: programa que recibe el tráfico web y lo redirige internamente a tu aplicación (reverse proxy), y gestiona HTTPS.
- **Certbot**: herramienta que consigue y renueva certificados HTTPS gratis (Let's Encrypt).
- **HTTPS / certificado SSL**: el "candado" del navegador; cifra la comunicación para que nadie en el medio pueda leerla.
- **systemd / servicio**: el supervisor de Linux que mantiene un programa siempre prendido y lo reinicia si se cae.
- **CI/CD**: automatizar que el código nuevo llegue solo a producción cuando se sube al repositorio.
- **GitHub Actions**: el robot de GitHub que ejecuta esos pasos automáticos.
- **Secrets (de GitHub)**: lugar donde se guardan contraseñas/llaves para que las use la automatización, sin que queden visibles en el código.
- **`.env`**: archivo (nunca subido al repositorio) donde vive la configuración sensible real de cada entorno (desarrollo vs. producción).
- **Cron**: el "reloj despertador" de Linux — ejecuta un comando en un horario programado (lo usamos para los backups diarios).
- **CORS**: regla de seguridad del navegador que controla qué sitios pueden pedirle datos a tu backend desde un dominio distinto.
