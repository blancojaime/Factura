/** @type {import('next').NextConfig} */
// El navegador solo habla con el frontend (mismo origen): las rutas /api/* se reenvian al backend.
// Asi la cookie HTTP-only del refresh token es de primer nivel (SameSite=Strict) y no hace falta CORS.
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

module.exports = {
  output: "standalone",
  reactStrictMode: true,
  poweredByHeader: false,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` }];
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "SAMEORIGIN" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        ],
      },
    ];
  },
};
