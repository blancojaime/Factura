# Manual de implementación y despliegue

## 1. Requisitos

| Componente | Servidor web | Cliente Windows (instalado) | Compilar el instalador |
|---|---|---|---|
| SO | Linux (Ubuntu 22.04+/Debian 12) o Windows Server | Windows 10 (64 bits) o superior | Windows 10/11 |
| Python | 3.11 o superior | (incluido en el instalador) | 3.11+ 64 bits en `PATH` |
| Base de datos | SQLite (incluida) o PostgreSQL 14+ | SQLite (incluida) | — |
| Otros | `pg_dump`/`psql` si usa PostgreSQL | WebView2 Runtime (viene con Windows 10/11 actualizado) | NSIS (`makensis`) opcional |

Dependencias Python: `backend/requirements.txt` (FastAPI, SQLAlchemy, openpyxl, python-docx, reportlab, cryptography, PyJWT…).

## 2. Modalidad Web (servidor)

### 2.1 Instalación paso a paso (Linux)
```bash
sudo apt update && sudo apt install -y python3 python3-venv
sudo useradd -r -m -d /opt/gam gam
sudo -u gam bash -c '
  cd /opt/gam && git clone <URL-DEL-REPOSITORIO> app && cd app/gam-personal/backend
  python3 -m venv /opt/gam/venv
  /opt/gam/venv/bin/pip install -r requirements.txt
'
```
Variables de entorno (archivo `/etc/gam.env`, permisos `600`):
```ini
GAM_DATA_DIR=/var/lib/gam
GAM_BACKUP_DIR=/var/lib/gam/backups
GAM_SECRET_KEY=<cadena aleatoria de 48+ caracteres>   # python3 -c "import secrets;print(secrets.token_urlsafe(48))"
# GAM_DATABASE_URL=postgresql+psycopg://gam:CLAVE@127.0.0.1:5432/gam   (omitir para SQLite)
GAM_BACKUP_PASSWORD=<clave de cifrado de respaldos>
```
Servicio `systemd` (`/etc/systemd/system/gam.service`):
```ini
[Unit]
Description=Gestion de Personal y Asistencia Municipal
After=network.target
[Service]
User=gam
EnvironmentFile=/etc/gam.env
WorkingDirectory=/opt/gam/app/gam-personal/backend
ExecStart=/opt/gam/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=on-failure
[Install]
WantedBy=multi-user.target
```
```bash
sudo mkdir -p /var/lib/gam && sudo chown gam: /var/lib/gam
sudo systemctl daemon-reload && sudo systemctl enable --now gam
curl http://127.0.0.1:8000/api/salud          # {"ok":true,...}
```
**HTTPS obligatorio en producción**: publique el puerto 8000 detrás de un proxy inverso (nginx/Apache/IIS) con certificado TLS; no exponga uvicorn directamente. Abra `https://su-servidor/` → *Primer ingreso* crea el administrador (mín. 8 caracteres).
> Use **un solo worker** con SQLite. Con PostgreSQL puede subir workers.

### 2.2 PostgreSQL (opcional)
```bash
sudo -u postgres psql -c "CREATE USER gam WITH PASSWORD 'CLAVE'" -c "CREATE DATABASE gam OWNER gam ENCODING 'UTF8'"
/opt/gam/venv/bin/pip install "psycopg[binary]"
# Defina GAM_DATABASE_URL y reinicie: las tablas y triggers se crean al iniciar.
# Alternativa manual: psql -d gam -f db/schema_postgresql.sql
```
Se verificó con PostgreSQL 16 (53 pruebas, respaldo con `pg_dump` y restauración con `psql`).

### 2.3 Servidor Windows
```bat
py -3 -m venv C:\gam\venv && C:\gam\venv\Scripts\pip install -r backend\requirements.txt
set GAM_DATA_DIR=C:\gam\datos & set GAM_SECRET_KEY=... 
C:\gam\venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Para ejecutarlo como servicio use NSSM o el Programador de tareas ("Al iniciar el sistema").

## 3. Modalidad Escritorio (Windows 10+)

### 3.1 Compilar el instalador (una vez, en una PC Windows)
```bat
cd gam-personal\desktop
build_windows.bat
```
Genera `dist\GAMPersonal\GAMPersonal.exe` y, si NSIS está instalado, `GAMPersonal_Setup.exe`.
> **Importante:** estos scripts **no pudieron ejecutarse en el entorno de desarrollo (Linux)**. Haga primero una compilación de prueba y verifique: (1) abre la ventana, (2) importa un Excel, (3) genera el `.docx`. Si falta una librería en el `.exe`, agréguela a `hiddenimports` en `gam_personal.spec`.

### 3.2 Instalación en cada PC
Ejecute `GAMPersonal_Setup.exe` (pide permisos de administrador) → acceso directo en escritorio. Los datos quedan en `%APPDATA%\GAMPersonal` (**no se borran al desinstalar**).
Sin instalador: copie la carpeta `dist\GAMPersonal` y ejecute `GAMPersonal.exe`.

### 3.3 Ejecutar desde el código fuente (pruebas)
```bat
cd gam-personal\desktop && py -3 -m venv .venv && .venv\Scripts\pip install -r requirements-desktop.txt
.venv\Scripts\python launcher.py            :: ventana nativa
.venv\Scripts\python launcher.py --sin-ventana   :: solo servidor (imprime la URL)
```

## 4. Protocolo de respaldo y recuperación

**Qué se respalda:** toda la base de datos (personal, contratos, marcas, permisos, instructivos, resultados y bitácora) como script SQL (`.sql`) **cifrado con AES‑256‑GCM** (clave derivada con scrypt de su contraseña). Junto a cada `…sql.enc` se escribe `…sql.enc.sha256` y se registra en `backup_registro` y en la bitácora.

**Regla 3‑2‑1 recomendada:** 3 copias, 2 medios distintos, 1 fuera de la oficina (USB guardado en bóveda). **Anote la contraseña de cifrado en un sobre sellado: sin ella el respaldo no se puede abrir.**

| Cuándo | Cómo |
|---|---|
| **Manual (web o escritorio)** | Menú *Respaldos* → contraseña → *Crear respaldo*. En escritorio, en *Destino* escriba la unidad USB (p. ej. `E:\Respaldos`). Descargable desde la web |
| **Programado – Linux (cron)** | `45 18 * * * gam set -a; . /etc/gam.env; set +a; cd /opt/gam/app/gam-personal/backend && /opt/gam/venv/bin/python -m app.cli backup && /opt/gam/venv/bin/python -m app.cli retencion --dias 90` |
| **Programado – Windows** | Defina `GAM_BACKUP_PASSWORD` (variable de sistema) y `schtasks /create /tn "GAM Respaldo" /tr "\"C:\Program Files\GAMPersonal\respaldo_programado.bat\"" /sc daily /st 18:45` |
| **Verificar** (mensual) | *Respaldos → Verificar integridad* (sube el archivo + hash + contraseña) o `python -m app.cli verificar ARCHIVO.sql.enc` |
| **Restaurar** | *Respaldos → Restaurar* (solo ADMIN): exige el **SHA‑256 de referencia** (contenido del `.sha256`) y la contraseña. Si el hash no coincide o el archivo fue alterado, **no restaura**. En SQLite se guarda antes `gam_personal.db.antes_de_restaurar_<fecha>`; en PostgreSQL se ejecuta en una sola transacción (todo o nada). CLI: `python -m app.cli restaurar ARCHIVO.sql.enc` |

Prueba de recuperación: al menos **una vez por trimestre** restaure un respaldo en una PC de prueba y compare el total de empleados y el último registro de la bitácora.

## 5. Lista de verificación de seguridad antes de producción
- [ ] HTTPS con certificado válido; uvicorn solo en `127.0.0.1`.
- [ ] `GAM_SECRET_KEY` propia y archivos `/etc/gam.env` con permiso `600`.
- [ ] Un usuario por persona (no compartir `admin`); rol CONSULTA para auditoría interna.
- [ ] Respaldos diarios programados + copia externa + prueba de restauración trimestral.
- [ ] Cerrar el periodo luego de aprobar planillas; reapertura solo con motivo (queda en bitácora).
- [ ] Ejecutar *Auditoría → Verificar integridad de la cadena* mensualmente.
- [ ] Revisar parámetros legales (docs/ARQUITECTURA.md §5) con la Unidad Jurídica.

## 6. Actualización
Detenga el servicio → respaldo → actualice el código → `pip install -r requirements.txt` → inicie. Las tablas nuevas se crean automáticamente; **no hay migraciones destructivas** en esta versión (si una versión futura cambia columnas se entregará script de migración).

## 7. Pruebas automáticas
```bash
cd gam-personal/backend && pip install -r requirements-dev.txt && python -m pytest tests -q        # SQLite
GAM_DATABASE_URL=postgresql+psycopg://usuario@host/base_vacia python -m pytest tests -q            # PostgreSQL (base VACÍA)
```
