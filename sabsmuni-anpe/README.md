# SABSMUNI-ANPE

Sistema integrado de gestión y documentación de contrataciones estatales en la modalidad **ANPE**
(Bs 50.001 a Bs 1.000.000) para Bienes, Servicios Generales y Obras, bajo las NB-SABS (D.S. 0181),
con trazabilidad documental para auditoría.

100 % open source: NestJS · PostgreSQL · Prisma · Next.js · Tailwind · pdfkit / pdf-lib.

> **Antes de usarlo en un proceso real**, lea [`docs/NORMATIVA_Y_SUPUESTOS.md`](docs/NORMATIVA_Y_SUPUESTOS.md):
> los plazos, márgenes, garantías y catálogos están parametrizados según el requerimiento del proyecto y
> **deben ser validados por la unidad jurídica** de la entidad; los catálogos CHB/partidas incluidos son *de ejemplo*.

## Inicio rápido (un solo comando)

```bash
./scripts/init-env.sh          # genera .env con secretos aleatorios (solo la primera vez)
docker compose up --build      # PostgreSQL + API + Web
```

Abrir <http://localhost:3000>. El contrato de la API está en `docs/openapi.json`; el Swagger interactivo
(`/api/docs`) solo se sirve fuera de producción o con `SWAGGER_ENABLED=true`.
Para capacitación con un usuario por rol, ponga `SEED_DEMO_USERS=true` y `SEED_DEMO_PASSWORD=...` en `.env`.

## Qué automatiza

| Módulo | Qué hace | Código |
|---|---|---|
| **A** Requerimiento + CHB | Asistente de ET/TdR por secciones; detecta marcas, patentes y exclusividad; cruza UNSPSC con el catálogo de manufactura nacional (D.S. 4505) y emite el *Formulario de Justificación de Insuficiencia Técnica* | `domain/especificaciones.ts`, `domain/chb.ts`, `requerimiento.service.ts`, `requerimiento-asistente.tsx` |
| **B** Cronograma + DBC | Plazos hábiles Art. 47 (4 d.h. ≤ Bs 200.000; 8 d.h. hasta Bs 1.000.000) con feriados bolivianos; DBC Parte I y II en PDF | `domain/calendario-bolivia.ts`, `domain/cronograma.ts`, `pdf/templates/index.ts` |
| **C** SIGEP | Interfaz espejo del C-31, validación aritmética (total y por partida, en centavos), glosa estandarizada y «Copiar bloque para SIGEP» | `domain/sigep.ts`, `sigep-captura.tsx` |
| **D** Evaluación | Matriz V-1 Presentó/No presentó, subasta, márgenes 10 %/18 %, PEMB y Calidad-Propuesta-Costo, cuadro comparativo e informe de recomendación | `domain/evaluacion.ts`, `matriz-comparativa.tsx` |
| **E** Contrato + expediente | Contrato u Orden (≤ 15 d. calendario), garantía 7 % / 3,5 %, Expediente Único foliado con marcadores y sello SHA-256 verificable por QR | `domain/garantia.ts`, `expediente.service.ts` |

Seguridad: JWT (15 min) + refresh rotativo en cookies HTTP-only, bcrypt (costo 12), RBAC por rol y estado,
limitador de intentos, `helmet`, validación estricta de entradas, auditoría **encadenada por hash** (cada registro sella al anterior).

## Documentación

- [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md) — árbol de archivos, modelo de datos, flujo de estados, matriz RBAC.
- [`docs/MANUAL_IMPLEMENTACION.md`](docs/MANUAL_IMPLEMENTACION.md) — requisitos, variables, migraciones, HTTPS, respaldos.
- [`docs/MANUAL_USUARIO.md`](docs/MANUAL_USUARIO.md) — guía por rol con el caso *Lote de cemento para pavimento – Bs 180.000*.
- [`docs/NORMATIVA_Y_SUPUESTOS.md`](docs/NORMATIVA_Y_SUPUESTOS.md) — qué parámetros validar y qué **no** hace el sistema.
- [`docs/openapi.json`](docs/openapi.json) — contrato de la API (41 rutas).

## Pruebas

```bash
cd backend && npm ci
npx jest test/unit                                   # 58 pruebas del núcleo legal/aritmético (sin BD)
DATABASE_URL=postgresql://... npx jest test/integration   # flujo completo con Nest + PostgreSQL real
cd ../frontend && npm ci && npm run build && npx playwright test   # E2E por roles (sistema levantado)
```

Resultados de la última corrida: 63 pruebas de backend (58 unitarias + 5 de integración) y 1 E2E de navegador, todas en verde.
