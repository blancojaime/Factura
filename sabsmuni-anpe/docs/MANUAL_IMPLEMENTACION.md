# Manual de implementación

## 1. Requisitos del servidor

| Recurso | Mínimo | Recomendado (≈ 20 usuarios, 500 procesos/año) |
|---|---|---|
| CPU / RAM | 2 vCPU / 4 GB | 4 vCPU / 8 GB |
| Disco | 20 GB | 100 GB SSD (el expediente en PDF crece con el uso) |
| SO | Linux x86-64 con Docker Engine ≥ 24 y Docker Compose v2 | Ubuntu 22.04/24.04 LTS |
| Red | Salida a registros de imágenes (solo en la instalación) | Reverse proxy con HTTPS (Caddy / Nginx) delante del puerto 3000 |

Sin Docker (alternativa): Node.js 22, PostgreSQL 16 y un proxy inverso. Ver §7.

## 2. Variables de entorno (`.env`)

Genere el archivo con `./scripts/init-env.sh` (secretos aleatorios) o copie `.env.example`.

| Variable | Obligatoria | Descripción |
|---|:-:|---|
| `POSTGRES_PASSWORD` | ✔ | Contraseña de la base (no se publica fuera de Docker). |
| `JWT_SECRET` | ✔ | ≥ 32 caracteres aleatorios (`openssl rand -hex 32`). El backend **no arranca en producción** sin ella. |
| `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` | ✔ | Administrador inicial. Cambie la clave en el primer ingreso. |
| `PUBLIC_URL` | | URL pública (se codifica en el QR de verificación y fija el CORS). Ej.: `https://contrataciones.migam.gob.bo`. |
| `WEB_PORT` | | Puerto publicado del frontend (3000). |
| `COOKIE_SECURE` | | `true` cuando se sirve por HTTPS (**obligatorio en producción real**). |
| `LOGIN_RATE_LIMIT` | | Intentos de login por minuto y por IP (10). |
| `GAM_NOMBRE` | | Nombre inicial de la entidad (luego editable en Administración). |
| `SWAGGER_ENABLED` | | `true` expone `/api/docs` en producción (apagado por defecto). |
| `SEED_DEMO_USERS` / `SEED_DEMO_PASSWORD` | | Solo capacitación: un usuario por rol (`solicitante@gam.bo`, `presupuesto@gam.bo`, `contrataciones@gam.bo`, `rpa@gam.bo`) y catálogos de ejemplo. |

## 3. Instalación y arranque

```bash
git clone <repositorio> && cd sabsmuni-anpe
./scripts/init-env.sh              # crea .env y muestra la clave del administrador
docker compose up --build -d       # construye y levanta db, backend y frontend
docker compose ps                  # los tres servicios deben quedar "healthy"
docker compose logs -f backend     # verá "prisma migrate deploy" y "Seed completado"
```

Al iniciar, el contenedor del backend ejecuta **automáticamente y de forma idempotente**:
1. `prisma migrate deploy` — aplica las migraciones versionadas (`backend/prisma/migrations`).
2. `node dist/seed.js` — crea roles, configuración inicial y el administrador (y los datos demo solo si se pidió).
3. Levanta la API en el puerto 4000 (interno); el frontend la expone bajo `/api` en el mismo origen.

## 4. Configuración inicial (como administrador)

1. Ingrese en `PUBLIC_URL` con el administrador y **cambie su contraseña** (Administración → usuarios).
2. Cree los usuarios con su rol (US, RP, RC, RPA) con contraseña de ≥ 10 caracteres con letras y números.
3. Cargue los datos institucionales (nombre del GAM, NIT, DA, UE, nombre y cargo del RPA): `PUT /api/config`.
   Estos datos aparecen en encabezados, DBC, contratos y resoluciones.
4. Cargue el **catálogo oficial CHB** (`POST /api/catalogos/chb`) y el **clasificador de partidas vigente** (`POST /api/catalogos/partidas`).
   Los incluidos en el seed de demostración son ejemplos.
5. Cargue los **feriados departamentales/municipales y decretados** de su entidad (`POST /api/catalogos/feriados`).
   Los nacionales (incluidos Carnaval, Viernes Santo y Corpus Christi, calculados por año) ya están incorporados.
6. Opcional: ajuste márgenes de preferencia o plazos de la entidad en `config_institucional.margenes` / `.plazos` (JSON).
7. Revise con la unidad jurídica el documento [`NORMATIVA_Y_SUPUESTOS.md`](NORMATIVA_Y_SUPUESTOS.md).

## 5. HTTPS (obligatorio en producción)

Ponga un proxy inverso con certificado delante del puerto `WEB_PORT`. Ejemplo con Caddy (`Caddyfile`):

```
contrataciones.migam.gob.bo {
    reverse_proxy 127.0.0.1:3000
}
```
Después defina en `.env`: `PUBLIC_URL=https://contrataciones.migam.gob.bo` y `COOKIE_SECURE=true`, y ejecute `docker compose up -d`.
Si cambia `PUBLIC_URL`, los QR de documentos futuros apuntarán a la nueva dirección (los ya emitidos conservan la anterior).

## 6. Respaldo y restauración

```bash
./scripts/backup.sh /ruta/respaldos      # pg_dump + tar de /data/storage + sumas SHA-256
```
Programe el script (cron diario) y copie los archivos fuera del servidor. **Respalde base y documentos juntos**:
la base guarda los hashes, el volumen guarda los PDF.

Restauración en una instalación limpia:
```bash
docker compose up -d db
docker compose exec -T db pg_restore -U anpe -d anpe --clean --if-exists < anpe-db-AAAAMMDD-HHMMSS.dump
docker compose run --rm --no-deps -T backend sh -c 'cd /data && tar xzf -' < anpe-storage-AAAAMMDD-HHMMSS.tar.gz
docker compose up -d
```
Tras restaurar, ejecute `GET /api/auditoria/verificar` (o el botón «Verificar integridad» en Administración) y
vuelva a abrir un expediente: ambos confirman que nada fue alterado.

## 7. Instalación sin Docker (resumen)

```bash
# PostgreSQL 16 con base "anpe"; luego:
cd backend && npm ci
export DATABASE_URL=postgresql://usuario:clave@localhost:5432/anpe?schema=public
export NODE_ENV=production JWT_SECRET=$(openssl rand -hex 32) STORAGE_DIR=/var/lib/anpe/storage
export PUBLIC_URL=https://... SEED_ADMIN_PASSWORD='...'
npm run build && npx prisma migrate deploy && node dist/seed.js && node dist/main.js
cd ../frontend && npm ci && BACKEND_URL=http://127.0.0.1:4000 npm run build && npm start
```

## 8. Actualización de versión

```bash
git pull && docker compose up --build -d     # las migraciones se aplican solas al iniciar
```
Los documentos ya emitidos nunca se modifican. Haga un respaldo antes de actualizar.

## 9. Operación y diagnóstico

| Síntoma | Causa probable | Acción |
|---|---|---|
| `docker compose up` falla con «Defina JWT_SECRET…» | Falta `.env` | `./scripts/init-env.sh` |
| El backend se reinicia en bucle | `DATABASE_URL`/contraseña incorrectas o JWT corto | `docker compose logs backend` |
| «Sesión expirada» al ingresar por HTTPS | `COOKIE_SECURE=false` detrás de HTTPS, o proxy sin `X-Forwarded-*` | Ajustar `COOKIE_SECURE` y el proxy |
| Descarga responde 500 «no coincide con su hash» | Un PDF del volumen fue alterado o el volumen no corresponde a la base | Restaurar ambos desde el mismo respaldo |
| 429 al ingresar | Superó `LOGIN_RATE_LIMIT` | Esperar 1 minuto o subir el límite |
| Fecha rechazada «no es día hábil» | Fin de semana, feriado nacional o cargado | Elegir otra fecha o revisar feriados |

## 10. Pruebas automatizadas

Ver el README. En CI (`.github/workflows/sabsmuni-anpe-ci.yml`) se ejecutan unitarias + integración (con servicio PostgreSQL),
`tsc` y `next build`. Para el E2E: levante el sistema con `SEED_DEMO_USERS=true` y ejecute
`cd frontend && E2E_BASE_URL=http://localhost:3000 E2E_PASSWORD=<SEED_DEMO_PASSWORD> npx playwright test`
(el navegador debe estar disponible: `npx playwright install chromium` o `PW_CHROMIUM_PATH`).
