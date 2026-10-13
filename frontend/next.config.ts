import type { NextConfig } from "next";

// Backend URL: set NEXT_PUBLIC_API_URL in your .env.local (or deployment env vars).
// Local dev default: http://localhost:5000
const rawBackend = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:5000";
const BACKEND_URL = rawBackend.replace(/\/api\/?$/, "");

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/auth/login/google',
        destination: `${BACKEND_URL}/login/google`,
      },
      {
        source: '/api/auth/login/mock',
        destination: `${BACKEND_URL}/login/mock`,
      },
      {
        source: '/api/auth/google/callback',
        destination: `${BACKEND_URL}/auth/google/callback`,
      },
      {
        source: '/auth/google/callback',
        destination: `${BACKEND_URL}/auth/google/callback`,
      },
      {
        source: '/auth/callback/google',
        destination: `${BACKEND_URL}/auth/google/callback`,
      },
      {
        source: '/api/logout',
        destination: `${BACKEND_URL}/logout`,
      },
      {
        source: '/api/:path*',
        destination: `${BACKEND_URL}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
