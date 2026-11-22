#!/bin/bash
# Recrea la instancia demo (BD "correspondencia"), importa el Excel del GAM y siembra nombres. Requiere MariaDB en marcha.
R="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$R"
mariadb -uroot -e "DROP DATABASE IF EXISTS correspondencia" && rm -f config/config.php storage/installed.lock storage/uploads/*.pdf storage/uploads/*.txt storage/uploads/entidad/* 2>/dev/null
CORR_DB_HOST=127.0.0.1 CORR_DB_PORT=3306 CORR_DB_NAME=correspondencia CORR_DB_USER=corr CORR_DB_PASS=corr123 CORR_ENTIDAD="Gobierno Autónomo Municipal de Ejemplo" CORR_SIGLA=GAME CORR_ADMIN_LOGIN=admin CORR_ADMIN_PASS=Admin12345 CORR_ADMIN_NOMBRE="Administrador del Sistema" php bin/install.php >/dev/null
php bin/importar.php database/Cargos_y_Oficinas_GAM.xlsx /tmp/claves.csv >/dev/null
php tools/manuales/seed.php
# Escudo de ejemplo para las capturas
mkdir -p "$R/storage/uploads/entidad" && cp "$R/tools/manuales/escudo.png" "$R/storage/uploads/entidad/escudo.png"
mariadb -uroot correspondencia -e "INSERT INTO ajustes (clave,valor) VALUES ('logo','escudo.png') ON DUPLICATE KEY UPDATE valor='escudo.png'" 2>&1 || true
