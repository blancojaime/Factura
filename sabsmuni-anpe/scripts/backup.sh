#!/usr/bin/env sh
# Respaldo completo: base de datos (pg_dump) + volumen de documentos (PDF del expediente).
# Uso: ./scripts/backup.sh [directorio_destino]   ·   Restauración: ver docs/MANUAL_IMPLEMENTACION.md
set -e
cd "$(dirname "$0")/.."
DEST="${1:-./backups}"; STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$DEST"
docker compose exec -T db pg_dump -U anpe -d anpe --format=custom > "$DEST/anpe-db-$STAMP.dump"
docker compose exec -T backend tar -C /data -czf - storage > "$DEST/anpe-storage-$STAMP.tar.gz"
( cd "$DEST" && sha256sum "anpe-db-$STAMP.dump" "anpe-storage-$STAMP.tar.gz" > "anpe-$STAMP.sha256" )
echo "Respaldo creado en $DEST (con sumas SHA-256)."
