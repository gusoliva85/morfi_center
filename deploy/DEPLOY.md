# Morfi Center · Runbook de despliegue

Sin credenciales reales en este archivo — nunca. Reemplazá `<...>` por tus propios datos al ejecutar cada paso; no los pegues acá.

---

## 1. Alta y hardening inicial del VPS Contabo (T-0.7.1)

### 1.1 Conseguir los datos de acceso

En el panel de Contabo (`my.contabo.com`) → tu VPS → **Manage** / **Detalles de acceso**: ahí figura la **IP pública** del servidor y la **contraseña inicial de `root`** (llega también por email al contratarlo). Guardalos en tu gestor de contraseñas, no en ningún archivo del repo.

### 1.2 Primer login (como `root`, con contraseña — todavía sin hardening)

Desde PowerShell, en tu máquina:

```powershell
ssh root@<IP_DEL_VPS>
```

Te va a pedir la contraseña inicial. Puede pedirte cambiarla en el primer login — hacelo.

### 1.3 Actualizar el sistema

Ya conectado, en el servidor:

```bash
apt update && apt upgrade -y
```

### 1.4 Crear un usuario no-root con sudo

En el servidor (reemplazá `morfi` por el usuario que prefieras):

```bash
adduser morfi
usermod -aG sudo morfi
```

### 1.5 Generar un par de claves SSH (en tu máquina, NO en el servidor)

En PowerShell, en tu máquina:

```powershell
ssh-keygen -t ed25519 -C "morfi-center-deploy"
```

Enter para la ubicación default (`$env:USERPROFILE\.ssh\id_ed25519`) y para la passphrase si no querés una (opcional, pero recomendable). Esto genera **dos** archivos: `id_ed25519` (privada — nunca la compartas, ni conmigo) e `id_ed25519.pub` (pública — esa sí se copia al servidor).

### 1.6 Copiar la clave pública al usuario nuevo

Windows no trae `ssh-copy-id`. Alternativa con PowerShell:

```powershell
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub | ssh root@<IP_DEL_VPS> "mkdir -p /home/morfi/.ssh && cat >> /home/morfi/.ssh/authorized_keys && chmod 700 /home/morfi/.ssh && chmod 600 /home/morfi/.ssh/authorized_keys && chown -R morfi:morfi /home/morfi/.ssh"
```

### 1.7 Probar el login por clave ANTES de desactivar la contraseña

En otra ventana de PowerShell (dejá la sesión de `root` abierta por si algo falla):

```powershell
ssh morfi@<IP_DEL_VPS>
```

No debería pedir contraseña. Si pide, **no sigas al siguiente paso** — algo falló en 1.5/1.6.

### 1.8 Deshabilitar login de `root` y por contraseña

En el servidor, ya logueado como el usuario nuevo (con `sudo`):

```bash
sudo sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart ssh
```

> **El servicio se llama `ssh`, no `sshd`**, en Ubuntu (`sshd.service` no existe — es el nombre del paquete Debian/Ubuntu, no el de la unidad systemd). `systemctl restart sshd` falla con "Unit sshd.service not found".

> **Gotcha real encontrado en el primer despliegue:** las imágenes de Ubuntu de Contabo traen `/etc/ssh/sshd_config.d/50-cloud-init.conf` con `PasswordAuthentication yes`, que se procesa **antes** que `/etc/ssh/sshd_config` (el `Include` de `sshd_config.d/*.conf` va casi al principio del archivo, y en la config de SSH gana la **primera** aparición de cada directiva). Resultado: aunque `sshd_config` diga `no`, ese drop-in lo pisa y el login por contraseña sigue funcionando. Se nota porque `ssh root@<IP>` sigue pidiendo contraseña en vez de rechazar directo. Solución:
> ```bash
> sudo grep -rn "PasswordAuthentication" /etc/ssh/sshd_config /etc/ssh/sshd_config.d/
> sudo sed -i 's/^PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config.d/50-cloud-init.conf
> sudo systemctl restart ssh
> ```
> Después de esto, `ssh root@<IP>` debe rechazar **inmediatamente** con `Permission denied (publickey)`, sin pedir contraseña.

### 1.9 Firewall (`ufw`): solo 22 (SSH), 80 (HTTP) y 443 (HTTPS)

```bash
sudo apt install ufw -y
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

### Checklist de esta tarea (T-0.7.1)

- [ ] Login SSH con la clave (`ssh morfi@<IP>`) funciona sin pedir contraseña.
- [ ] Intentar login por contraseña (o como `root`) es rechazado.
- [ ] `sudo ufw status` muestra únicamente 22, 80 y 443 permitidos.
- [ ] `apt upgrade` corrido sin errores.

---

## 2. Stack del servidor (T-0.7.2)

### 2.1 Instalar Python, Nginx, Certbot y git

Ya logueado como el usuario no-root (`morfi`):

```bash
sudo apt install -y python3 python3-venv python3-pip nginx certbot python3-certbot-nginx git
```

### 2.2 Verificar versiones

```bash
python3 --version
nginx -v
certbot --version
```

Se espera Python 3.11+ (Ubuntu 24.04 trae 3.12), Nginx y Certbot recientes.

### 2.3 Clonar el repositorio

El repo es **público**, así que no hace falta ninguna clave para clonarlo (si en algún momento pasa a privado, acá va a hacer falta una *deploy key* de solo lectura agregada en GitHub → Settings del repo → Deploy keys):

```bash
git clone https://github.com/gusoliva85/morfi_center.git ~/morfi_center
cd ~/morfi_center
ls
```

### Checklist de esta tarea (T-0.7.2)

- [ ] `python3 --version`, `nginx -v` y `certbot --version` responden.
- [ ] El repositorio queda clonado en el servidor con la misma estructura que en local.

---

## 3. Servicio systemd + Nginx + HTTPS (T-0.7.3)

> **Sin dominio propio:** Certbot/Let's Encrypt no emite certificados para una IP sola. Se usa [sslip.io](https://sslip.io) (gratis, sin registro): `<IP-con-guiones>.sslip.io` resuelve siempre a esa IP. Ej. `13.140.36.93` → `13-140-36-93.sslip.io`. Si en el futuro hay dominio propio, se reemplaza acá y se vuelve a correr Certbot para ese dominio.

### 3.1 Backend: entorno virtual, `.env` de producción, migraciones

```bash
cd ~/morfi_center/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
sed -i "s|^APP_ENV=.*|APP_ENV=production|" .env
sed -i "s|^COOKIE_SAMESITE=.*|COOKIE_SAMESITE=none|" .env
sed -i "s|^JWT_SECRET=.*|JWT_SECRET=$(python3 -c 'import secrets; print(secrets.token_hex(32))')|" .env
# FRONTEND_ORIGIN se completa en T-0.7.6, cuando exista la URL real de Vercel.

alembic upgrade head
python -m app.db.seed
```

> El `sed` de `JWT_SECRET` genera el valor random **dentro** del propio comando — nunca se ve en pantalla ni queda en el historial como texto plano visible.

### 3.2 Servicio `systemd`

```bash
sudo cp ~/morfi_center/deploy/morficenter-api.service /etc/systemd/system/morficenter-api.service
sudo systemctl daemon-reload
sudo systemctl enable morficenter-api
sudo systemctl start morficenter-api
sudo systemctl status morficenter-api --no-pager
```

Debe decir `Active: active (running)`.

### 3.3 Nginx (reverse proxy)

Reemplazar `13-140-36-93.sslip.io` por el hostname real de sslip.io de cada servidor:

```bash
sed "s|<SSLIP_HOSTNAME>|13-140-36-93.sslip.io|" ~/morfi_center/deploy/nginx.morficenter.conf | sudo tee /etc/nginx/sites-available/morficenter.conf > /dev/null
sudo ln -sf /etc/nginx/sites-available/morficenter.conf /etc/nginx/sites-enabled/morficenter.conf
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### 3.4 HTTPS con Certbot

```bash
sudo certbot --nginx -d 13-140-36-93.sslip.io
```

Pide un email de contacto (avisos de vencimiento) y aceptar los términos; ante "¿redirigir HTTP a HTTPS?" responder que sí. Certbot edita `sites-enabled/morficenter.conf` solo, agregando el bloque `443` y la redirección, y programa la renovación automática.

### Gotchas reales encontrados en el primer despliegue

- **`sudo` no funciona en un `ssh host "comando"` no interactivo** ("a terminal is required to read the password"). Todo lo que lleva `sudo` lo tiene que tipear la propia persona en una sesión interactiva — no se puede automatizar así (para eso está la automatización de `T-0.7.8`, con una regla `sudo` sin contraseña acotada a comandos puntuales).
- **`nohup comando &` por SSH puede dejar la sesión colgada** aunque el proceso ya se haya desconectado bien — el canal SSH espera a que se cierren los file descriptors. No es un problema del proceso en sí, solo corta la sesión manualmente si pasa.

### Checklist de esta tarea (T-0.7.3)

- [ ] `sudo systemctl status morficenter-api` en verde (`active (running)`).
- [ ] `curl https://<host-sslip>/api/v1/health` responde 200 con certificado válido (sin `-k`).
- [ ] `http://<host-sslip>/...` redirige solo a `https://`.

---

## 4. Vercel: proyecto y primer deploy del frontend (T-0.7.5)

### 4.1 Conectar el repositorio

1. Entrar a [vercel.com](https://vercel.com) y loguearse con **"Continue with GitHub"**.
2. **"Add New..." → "Project"**.
3. Seleccionar el repo `morfi_center` (puede pedir instalar la app de Vercel en GitHub con acceso a ese repo).

### 4.2 Root Directory — gotcha real

El repo es un **monorepo** (`backend/`, `frontend/`, `documentacion/`, `deploy/` al mismo nivel). Por defecto Vercel intenta servir desde la **raíz del repo**, no encuentra `index.html` ahí (está en `frontend/index.html`) y da **404** en `/` (aunque `/frontend/index.html` sí responda 200 — esa es la pista para detectarlo).

Arreglo: **Settings → Build and Deployment → Root Directory → `frontend`** → Save → Redeploy (a veces no dispara solo, hay que forzarlo desde la pestaña *Deployments*).

### 4.3 `window.__MC_API__`

Ya resuelto en el código (`frontend/index.html`): detecta el host automáticamente — `localhost`/`127.0.0.1` usa el backend de desarrollo, cualquier otro host (Vercel, o el que sea) usa la URL HTTPS real del backend en el VPS. No hace falta configurar nada aparte en Vercel para esto.

### Checklist de esta tarea (T-0.7.5)

- [ ] La URL de Vercel sirve el home con estilo (no 404).
- [ ] Los assets (`assets/css/base.css`, `assets/img/...`) cargan con 200.
- [ ] Desde la consola del navegador en esa URL, `fetch(window.__MC_API__ + '/health', {credentials:'include'})` devuelve `{"status":"ok",...}` sin error de CORS.

---

## 5. CORS y cookies cross-site (T-0.7.6, parcial)

La parte de CORS no depende de que exista login (eso sí depende de `T-1.4.2`, Fase 1) — se adelantó para que `T-0.7.5` pudiera probarse de verdad.

```bash
# en el servidor, dentro de backend/
sed -i "s|^FRONTEND_ORIGIN=.*|FRONTEND_ORIGIN=<URL_DE_VERCEL>|" .env
```

Y reiniciar el servicio (con `sudo`, a mano):

```bash
sudo systemctl restart morficenter-api
```

`COOKIE_SAMESITE=none` ya se configuró en la sección 3.1 — no hace falta tocarlo de nuevo.

### Checklist de esta parte

- [ ] `curl -H "Origin: <URL_DE_VERCEL>" https://<host-sslip>/api/v1/health` devuelve el header `access-control-allow-origin: <URL_DE_VERCEL>`.
- [ ] **Pendiente hasta Fase 1** (necesita `T-1.4.2`): login real desde el front deja la cookie de refresh y `/auth/refresh` funciona cross-site.

---

## 6. Backups automáticos (T-0.7.7)

`deploy/backup.sh` copia `backend/data/morfi.db` y `backend/storage/payment_proofs/` a `~/backups/<timestamp>/`, y retiene solo los últimos 14. Sin `sudo` (cron de usuario).

```bash
cd ~/morfi_center && git pull
chmod +x deploy/backup.sh
./deploy/backup.sh   # corrida manual, para probar

# Cron diario a las 3am (reemplaza cualquier entrada previa del mismo script):
(crontab -l 2>/dev/null | grep -v 'morfi_center/deploy/backup.sh'; echo '0 3 * * * /home/morfi/morfi_center/deploy/backup.sh >> /home/morfi/backups/backup.log 2>&1') | crontab -
crontab -l   # confirmar
```

### Checklist de esta tarea (T-0.7.7)

- [ ] Corrida manual de `backup.sh` crea `~/backups/<timestamp>/` con `morfi.db` y `payment_proofs/`.
- [ ] `crontab -l` muestra la entrada diaria a las 3am.
