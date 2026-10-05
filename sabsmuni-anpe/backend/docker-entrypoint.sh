#!/bin/sh
set -e
# Migraciones versionadas (idempotentes) y datos iniciales antes de levantar la API.
npx prisma migrate deploy
node dist/seed.js
exec node dist/main.js
