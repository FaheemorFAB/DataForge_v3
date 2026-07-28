import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/auth/login/google',
        destination: 'http://127.0.0.1:5000/login/google',
      },
      {
        source: '/api/auth/google/callback',
        destination: 'http://127.0.0.1:5000/auth/google/callback',
      },
      {
        source: '/api/logout',
        destination: 'http://127.0.0.1:5000/logout',
      },
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:5000/api/:path*',
      },
    ];
  },
};

export default nextConfig;
