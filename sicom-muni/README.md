# SICOM-MUNI — Sistema Integrado de Contratación Menor Municipal

Aplicación web de código abierto para tramitar la **Contratación Menor (Bs 1 – 50.000)** de un Gobierno Autónomo Municipal
de Bolivia, de la solicitud (C-1) al devengado, con expediente digital verificable.

| Capa | Tecnología |
|---|---|
| API | FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, PostgreSQL 15+ |
| Web | Next.js 14 (App Router), TypeScript, Tailwind, componentes estilo Shadcn, Lucide |
| PDF | Jinja2 + WeasyPrint, QR de verificación y SHA-256 |
| Archivos | Disco local o S3/MinIO |
| Seguridad | JWT (acceso 15 min) + refresh rotativo en cookie HTTP-only, Argon2id, RBAC de 6 roles, auditoría encadenada por hash |

## Inicio rápido (Docker)

```bash
cp .env.example .env            # cambie TODOS los secretos
docker compose up -d --build
docker compose --profile seed run --rm seed   # usuarios y datos demo (opcional)
# Web: http://localhost:3000   API/Swagger: solo interna; para exponerla vea el Manual de Implementación
```

Usuarios demo (clave `Sicom#2026Demo`): `solicitante`, `presupuesto`, `contrataciones`, `rpa`, `recepcion`, `admin`.
**Cambie las claves antes de usar datos reales.**

## Pruebas

```bash
cd backend && pip install -r requirements-dev.txt && pytest          # SQLite por defecto
TEST_DATABASE_URL=postgresql+psycopg://... pytest                     # contra PostgreSQL real
cd frontend && npm ci && npx tsc --noEmit && npm run lint && npm run build
```

## Documentación

- [Manual de Implementación](docs/MANUAL_IMPLEMENTACION.md)
- [Manual de Usuario](docs/MANUAL_USUARIO.md)
- [Casos de prueba de validación](docs/CASOS_PRUEBA.md) (Bs 18.500 bienes; Bs 32.000 servicio)

## Avisos importantes

1. **Las referencias normativas, umbrales, plazos y mínimos de cotizaciones son parámetros configurables y NO fueron verificados
   contra la normativa vigente.** La entidad debe validarlos con su asesoría legal antes de operar (ver Manual de Implementación §9).
2. El hash SHA-256 impreso al pie de cada PDF es el del **contenido canónico** (un archivo no puede imprimir su propio hash);
   el hash del archivo final se guarda en la base y se compara en la página pública de verificación (`/verificar/{id}`).
3. El sistema **no se conecta al SIGEP ni al SICOES**: genera el bloque de captura para copiar y pegar y registra los números
   (C-31, F110, CUCE) que el operador obtiene allí.
