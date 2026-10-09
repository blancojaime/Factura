#!/usr/bin/env bash
# Inicio automatico para Mac/Linux:  ./iniciar.sh
set -e
cd "$(dirname "$0")"
command -v docker >/dev/null || { echo "Instale Docker (https://www.docker.com/products/docker-desktop) y repita."; exit 1; }
docker info >/dev/null 2>&1 || { echo "Abra Docker Desktop, espere a que inicie y repita."; exit 1; }
if [ ! -f .env ]; then
  gen() { head -c 200 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c "$1"; }
  cat > .env <<EOT
POSTGRES_PASSWORD=$(gen 24)
SECRET_KEY=$(gen 64)
FERNET_KEY=
MINIO_ROOT_USER=sicomminio
MINIO_ROOT_PASSWORD=$(gen 24)
PUBLIC_BASE_URL=http://localhost:3000
COOKIE_SECURE=false
EOT
  echo "Archivo .env creado."
fi
docker compose up -d --build
docker compose --profile seed run --rm seed
sleep 8
(open http://localhost:3000 || xdg-open http://localhost:3000) 2>/dev/null || true
echo "LISTO: http://localhost:3000  usuario: solicitante  clave: Sicom#2026Demo"
