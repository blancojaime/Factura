/** @type {import('next').NextConfig} */
// Modos de despliegue:
//  * NEXT_EXPORT=1 -> pantalla web estatica (carpeta "out") servida por la propia API (instalador de Windows).
//  * por defecto   -> servidor Node (Docker): las rutas /api/* se reenvian al backend (mismo origen, cookies HTTP-only).
const exportar = process.env.NEXT_EXPORT === "1";
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

const comun = { reactStrictMode: true, poweredByHeader: false };

module.exports = exportar
  ? { ...comun, output: "export", trailingSlash: true, images: { unoptimized: true } }
  : {
      ...comun,
      output: "standalone",
      async rewrites() {
        return [{ source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` }];
      },
      async headers() {
        return [{
          source: "/(.*)",
          headers: [
            { key: "X-Content-Type-Options", value: "nosniff" },
            { key: "X-Frame-Options", value: "SAMEORIGIN" },
            { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          ],
        }];
      },
    };
