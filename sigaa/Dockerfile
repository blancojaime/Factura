# SIGAA — imagen de producción (API + aplicación web). Base de datos: PostgreSQL (DATABASE_URL) o SQLite en /data.
FROM node:22-bookworm-slim AS build
WORKDIR /app
COPY package*.json ./
COPY server/package.json server/
COPY web/package.json web/
RUN npm ci
COPY . .
RUN npm run build

FROM node:22-bookworm-slim
ENV NODE_ENV=production PORT=3000 SIGAA_WEB_DIR=/app/web/dist SIGAA_FOTOS_DIR=/data/fotos DATABASE_URL=sqlite:/data/sigaa.sqlite
WORKDIR /app/server
COPY --from=build /app/node_modules /app/node_modules
COPY --from=build /app/server/package.json ./
COPY --from=build /app/server/dist ./dist
COPY --from=build /app/server/seed ./seed
COPY --from=build /app/web/dist /app/web/dist
VOLUME /data
EXPOSE 3000
CMD ["node", "dist/index.js"]
