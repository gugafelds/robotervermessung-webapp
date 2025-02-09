/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*', // Proxy to Backend
      },
    ];
  },
  experimental: {
    proxyTimeout: 1000000,
  },
};

module.exports = nextConfig;
