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
- [ ] `sudo ufw status` muestra únicamente 22, 80 y 443 permitidos.
- [ ] `apt upgrade` corrido sin errores.
