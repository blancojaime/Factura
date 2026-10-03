#!/bin/bash
# Linux / macOS: instala, prepara y abre SIGAA
cd "$(dirname "$0")"
command -v node >/dev/null || { echo "Instale Node.js desde https://nodejs.org"; exit 1; }
[ -x node_modules/.bin/vite ] || npm install --include=dev || exit 1
[ -f web/dist/index.html ] || npm run build || exit 1
[ -f server/data/sigaa.sqlite ] || npm run seed || exit 1
(sleep 8; (xdg-open http://localhost:3000 || open http://localhost:3000) >/dev/null 2>&1) &
npm start
