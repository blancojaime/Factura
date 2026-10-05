/** El navegador solo habla con el origen del frontend; Next reenvía /api al backend (cookies same-site). */
const backend = process.env.BACKEND_URL ?? 'http://localhost:4000';
export default {
  output: 'standalone',
  poweredByHeader: false,
  eslint: { ignoreDuringBuilds: true },
  async rewrites() { return [{ source: '/api/:path*', destination: `${backend}/api/:path*` }]; },
  async headers() {
    return [{ source: '/:path*', headers: [{ key: 'X-Frame-Options', value: 'DENY' }, { key: 'X-Content-Type-Options', value: 'nosniff' }, { key: 'Referrer-Policy', value: 'same-origin' }] }];
  },
};
