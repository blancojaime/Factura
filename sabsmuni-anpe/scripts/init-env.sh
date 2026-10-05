#!/usr/bin/env sh
# Genera .env con secretos aleatorios la primera vez. No sobrescribe un .env existente.
set -e
cd "$(dirname "$0")/.."
if [ -f .env ]; then echo ".env ya existe: no se modifica."; exit 0; fi
rand() { if command -v openssl >/dev/null 2>&1; then openssl rand -hex "$1"; else head -c "$1" /dev/urandom | od -An -tx1 | tr -d ' \n'; fi; }
ADMIN_PASS="Anpe-$(rand 6)-A1"
sed -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(rand 16)|" \
    -e "s|^JWT_SECRET=.*|JWT_SECRET=$(rand 32)|" \
    -e "s|^SEED_ADMIN_PASSWORD=.*|SEED_ADMIN_PASSWORD=${ADMIN_PASS}|" .env.example > .env
chmod 600 .env
echo ".env creado. Administrador inicial: admin@gam.bo / ${ADMIN_PASS}"
echo "Cambie esta contraseña tras el primer ingreso."
