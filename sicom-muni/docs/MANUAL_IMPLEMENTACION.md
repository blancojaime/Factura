# Manual de Implementación — SICOM-MUNI

## 1. Arquitectura

```
Navegador ──► Next.js :3000 ──(rewrite /api/*)──► FastAPI :8000 ──► PostgreSQL 15+
                                                         └────────► MinIO/S3 (expedientes PDF) o disco local
```
El navegador solo habla con el frontend (mismo origen); Next.js reenvía `/api/*` al backend. Así la cookie del refresh token es
HTTP-only + `SameSite=Strict` y no se necesita CORS.

## 2. Requisitos
- **Docker**: Docker Engine 24+ y Docker Compose v2 (recomendado), 2 GB RAM libres.
- **Sin Docker**: Python 3.12, Node 20, PostgreSQL 15+, y para WeasyPrint las librerías `pango`, `harfbuzz` y fuentes (en Debian/Ubuntu: `libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b shared-mime-info fonts-dejavu-core`).

## 3. Variables de entorno (backend)
| Variable | Defecto | Descripción |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://sicom:sicom@localhost:5432/sicom` | Conexión SQLAlchemy |
| `SECRET_KEY` | (dev) | Firma JWT y derivación de la clave de cifrado. **≥ 32 caracteres aleatorios** |
| `FERNET_KEY` | derivada | Clave Fernet para ofertas selladas (`python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"`) |
| `ACCESS_TOKEN_MINUTES` / `REFRESH_TOKEN_DAYS` | 15 / 7 | Vigencia de tokens |
| `COOKIE_SECURE` | false | **true** en producción (HTTPS) |
| `CORS_ORIGINS` | `http://localhost:3000` | Orígenes permitidos |
| `PUBLIC_BASE_URL` | `http://localhost:3000` | URL pública impresa en el QR de los PDF |
| `MAX_FAILED_LOGINS` / `LOCKOUT_MINUTES` | 5 / 15 | Bloqueo de cuenta |
| `STORAGE_BACKEND` | local | `local` o `s3` |
| `LOCAL_STORAGE_PATH` | `./storage` | Carpeta de PDF (modo local) |
| `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET`, `S3_REGION` | MinIO | Almacenamiento S3 |
| `SMTP_HOST/PORT/USER/PASSWORD/FROM` | vacío | Envío de fichas por correo; vacío = «NO_CONFIGURADO» |

Frontend: `BACKEND_URL` (se fija en el *build*; en Docker `http://backend:8000`).

## 4. Instalación con Docker Compose
```bash
cd sicom-muni
cp .env.example .env          # edite POSTGRES_PASSWORD, SECRET_KEY, MINIO_*, PUBLIC_BASE_URL
docker compose up -d --build  # db, minio, bucket, backend (migra al arrancar), frontend
docker compose --profile seed run --rm seed   # opcional: usuarios/partidas/catálogo demo (idempotente)
```
Servicios: `db` (PostgreSQL 16), `minio` (+`minio-init` crea el bucket privado `sicom-expedientes`), `backend` (ejecuta
`alembic upgrade head` y luego uvicorn), `frontend` (Next.js *standalone*, puerto 3000). El backend no publica puerto;
para consultar Swagger (`/api/docs`) añada `ports: ["127.0.0.1:8000:8000"]` temporalmente. Alternativa SQL: `db/seeds.sql`
(`psql -f db/seeds.sql`) tras migrar.

> Nota: en el entorno de desarrollo del autor no había daemon Docker; los Dockerfile y el compose se validaron de forma estática
> (`docker compose config`), **no** se construyeron las imágenes. Haga la primera compilación en un entorno de prueba.

## 5. Instalación manual
```bash
# Base de datos
createuser sicom -P && createdb sicom -O sicom
# Backend
cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg://sicom:CLAVE@localhost:5432/sicom SECRET_KEY=...
alembic upgrade head && python -m app.seeds          # seeds opcional
uvicorn app.main:app --host 0.0.0.0 --port 8000
# Frontend
cd ../frontend && npm ci && BACKEND_URL=http://localhost:8000 npm run build
node .next/standalone/server.js        # (copie .next/static y public junto a standalone) o: npm start
```

## 6. Pruebas
```bash
cd backend && pip install -r requirements-dev.txt
pytest                                  # 62 pruebas, SQLite en memoria
TEST_DATABASE_URL=postgresql+psycopg://sicom:sicom@127.0.0.1:5433/sicom_test pytest   # PostgreSQL real (trigger de auditoría incluido)
cd ../frontend && npx tsc --noEmit && npm run lint && npm run build
```
Cobertura: reglas de negocio unitarias (cuantía, formalización, CHB, evaluador, preferencias), flujo completo de bienes (Bs 18.500),
flujo de servicio (Bs 32.000), autenticación/RBAC, casos negativos, generación de PDF y cadena de auditoría. Ver `CASOS_PRUEBA.md`.

## 7. Seguridad
- Contraseñas con **Argon2id**; política ≥ 10 caracteres con mayúscula, minúscula y número; bloqueo tras 5 intentos fallidos (HTTP 423).
- Access token JWT 15 min en memoria del navegador; refresh token **rotativo**, almacenado como hash, en cookie HTTP-only/SameSite=Strict; reutilización de un refresh revocado invalida la sesión.
- RBAC por acción y estado (`services/workflow.py`); respuestas 403/409/422 consistentes.
- **Auditoría inalterable**: tabla `audit_logs` solo-inserción (trigger PostgreSQL impide UPDATE/DELETE) con cadena SHA-256; verificación en *Admin → Auditoría*.
- Ofertas **selladas**: el monto se cifra (Fernet) hasta «Abrir ofertas» vencido el plazo.
- PDF: WeasyPrint con *fetcher* que bloquea recursos externos (solo `data:`).
- Produce: use HTTPS (proxy inverso Nginx/Caddy/Traefik), `COOKIE_SECURE=true`, cambie claves demo, restrinja la consola MinIO.

## 8. Respaldo y operación
- BD: `docker compose exec db pg_dump -U sicom sicom > respaldo.sql` (programar diario). Restauración: `psql < respaldo.sql`.
- Archivos: volumen `miniodata` (o `mc mirror`). Los PDF son verificables contra el hash guardado en la BD.
- Actualizaciones: `git pull && docker compose up -d --build` (las migraciones corren al iniciar).
- Salud: `GET /api/v1/salud`.

## 9. Parámetros normativos — validar antes de operar
Los siguientes valores se configuran en *Admin → Parámetros* y provienen del encargo del cliente; **no se verificaron contra la normativa vigente**:
`tope_contratacion_menor` (50.000), `tope_compra_directa` (20.000), `plazo_orden_max_dias` (15), `min_cotizaciones_consulta` (3, supuesto),
`min_cotizaciones_directa` (1), `chb_min_justificacion` (80). Las referencias a D.S. 4505 (Compro Hecho en Bolivia), formularios (F110, C-31, F500)
y márgenes de preferencia Pro-Bolivia/MyPE deben ser revisadas por la asesoría legal de la entidad. Códigos de partida y catálogo CHB incluidos son **ilustrativos**.

## 10. Solución de problemas
| Síntoma | Causa / solución |
|---|---|
| Backend no inicia: «relation does not exist» | Falta `alembic upgrade head` |
| PDF vacío o error de WeasyPrint | Faltan librerías pango/harfbuzz/fuentes (la imagen Docker ya las incluye) |
| Se cierra la sesión al recargar | `COOKIE_SECURE=true` sin HTTPS, o frontend/API en dominios distintos |
| QR apunta a localhost | Defina `PUBLIC_BASE_URL` o el parámetro `url_publica` |
| 423 al iniciar sesión | Cuenta bloqueada 15 min; el admin puede restablecer la clave |
| `FORMULARIO_110_REQUERIDO` | Monto > 20.000: registre el F110 antes de cotizar |
| Error de migración con trigger | Use PostgreSQL 15+ (no SQLite) en producción |
