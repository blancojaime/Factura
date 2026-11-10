# JB-Personal — Manual de implementación y despliegue

> El manual completo con capturas está en **`Manual_JB-Personal.docx` / `.pdf`**. Esta es la versión resumida para GitHub.

## 1. Requisitos
| | Windows (instalador) | Servidor Linux |
|---|---|---|
| SO | Windows 10+ 64 bits | Ubuntu 22.04+/Debian 12 |
| Software previo | Ninguno (incluye Python) | Python 3.11+; PostgreSQL 14+ opcional |
| Permisos | **Administrador** (registra el servicio) | root/sudo |

## 2. Windows: instalador como servicio (independiente de la sesión)
1. Ejecute `JBPersonal_Setup.exe` como administrador (SmartScreen: *Más información → Ejecutar de todas formas*; no está firmado).
2. **Siguiente → Instalar → Finalizar** (sin más preguntas). Acceso desde otras PC (opcional): menú Inicio → JB-Personal → *Habilitar acceso desde la red* (abre el puerto 8765 para redes de dominio/privadas); *Solo esta PC* lo revierte.
3. Se registra la tarea programada **JB-Personal** (al arrancar, cuenta SYSTEM, reinicio automático cada minuto). **Funciona sin que haya sesión de usuario abierta.**
4. Se abre `http://127.0.0.1:8765/`; cree el administrador y active la licencia.

| Elemento | Ruta |
|---|---|
| Programa | `C:\\Program Files\\JB-Personal` |
| Datos, respaldos, registro, `config.ini` | `C:\\ProgramData\\JB-Personal` (no se borra al desinstalar) |
| Administrar (iniciar/detener/ver registro) | Menú Inicio → JB-Personal → *Administrar el servicio* · `schtasks /Run|/End|/Query /TN "JB-Personal"` |
| Puerto / red | `config.ini`: `host = 127.0.0.1` (solo esta PC) o `0.0.0.0` (red); `port = 8765` |

Actualizar: ejecute el instalador nuevo sobre el anterior (conserva datos y licencia). **No pudo probarse en Windows durante el desarrollo**: valídelo en una PC piloto (lista de aceptación del manual §9.7, incluida la prueba «reiniciar sin iniciar sesión»).

## 3. Construir los instaladores
```bash
cd jb-personal/desktop
python build_installer.py --version 1.1.0 --manual ../docs/Manual_JB-Personal.pdf ../docs/Manual_JB-Personal.docx   # -> JBPersonal_Setup.exe
python build_activador.py --clave-privada RUTA/clave_privada.pem                                                    # -> JBActivador_Setup.exe (solo emisor)
```
Requiere Python 3.9+, NSIS (`makensis`) e Internet. Los `.exe` y la clave privada **no se versionan**.

## 4. Activación y licencia
30 días de prueba; luego **solo lectura** (consultar, respaldar, activar). Menú **Licencia**: copie el *código de equipo* (`JBP-XXXXX-XXXXX-XXXXX`), envíelo al proveedor y pegue el *código de activación* (`JBP1.…`). Alternativa: copiar `licencia.jbp` a `C:\\ProgramData\\JB-Personal\\` y reiniciar el servicio. El código está ligado a un equipo.
Emisión: **JB-Activador** (`activador/jb_activador.py`, Anexo A del manual). La clave privada debe respaldarse y **nunca** subirse a un repositorio.

## 5. Servidor web en Linux
```bash
sudo apt install -y python3 python3-venv && sudo useradd -r -m -d /opt/jb jb
sudo -u jb bash -c 'cd /opt/jb && git clone <URL> app && cd app/jb-personal/backend && python3 -m venv /opt/jb/venv && /opt/jb/venv/bin/pip install -r requirements.txt'
sudo mkdir -p /var/lib/jb-personal && sudo chown jb: /var/lib/jb-personal
```
`/etc/jb-personal.env` (600): `GAM_DATA_DIR`, `GAM_BACKUP_DIR`, `GAM_SECRET_KEY` (48+ caracteres aleatorios), `GAM_BACKUP_PASSWORD`, y opcional `GAM_DATABASE_URL=postgresql+psycopg://…`.
`/etc/systemd/system/jb-personal.service`: `User=jb`, `EnvironmentFile=/etc/jb-personal.env`, `WorkingDirectory=/opt/jb/app/jb-personal/backend`, `ExecStart=/opt/jb/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1`, `Restart=on-failure`.
Publique detrás de nginx/Apache con **HTTPS**. Con SQLite, un solo worker.

### PostgreSQL (opcional)
Cree usuario y base UTF8, `pip install "psycopg[binary]"`, defina `GAM_DATABASE_URL`; las tablas y triggers se crean al iniciar (o `psql -f db/schema_postgresql.sql`). Verificado con PostgreSQL 16.

## 6. Respaldos
Script SQL cifrado AES-256-GCM + `.sha256`. Manual: menú *Respaldos*. Programado — Windows: variable de sistema `GAM_BACKUP_PASSWORD` y `schtasks /create /tn "JB Respaldo" /tr "\\"C:\\Program Files\\JB-Personal\\desktop\\respaldo_programado.bat\\"" /sc daily /st 18:45 /ru SYSTEM`; Linux: cron con `python -m app.cli backup` y `retencion --dias 90`. Verificar mensualmente; restaurar exige hash + contraseña (la contraseña perdida no se recupera). Restaurar en otro equipo requiere nuevo código de activación.

## 7. Seguridad (lista previa a producción)
- [ ] Un usuario por persona; rol CONSULTA para auditoría.
- [ ] Acceso de red solo si es necesario; HTTP sin cifrar → VPN o proxy HTTPS.
- [ ] `GAM_SECRET_KEY` propia (Linux); respaldos diarios + copia externa + prueba trimestral de restauración.
- [ ] Cerrar el periodo tras aprobar planillas; verificar la cadena de auditoría mensualmente.
- [ ] Validar los parámetros legales con la Unidad Jurídica (`ARQUITECTURA.md` §5).

## 8. Pruebas automáticas
```bash
cd jb-personal/backend && pip install -r requirements-dev.txt && python -m pytest tests -q          # 86 pruebas (SQLite)
GAM_DATABASE_URL=postgresql+psycopg://usuario@host/base_vacia python -m pytest tests -q            # PostgreSQL (base VACÍA)
```
