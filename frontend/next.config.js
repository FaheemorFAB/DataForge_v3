/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    const backend = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:5000";

    return {
      beforeFiles: [
        { source: "/", destination: `${backend}/` },
        { source: "/workspace", destination: `${backend}/workspace` },
        { source: "/dashboard", destination: `${backend}/dashboard` },
        { source: "/projects", destination: `${backend}/projects` },
        { source: "/login", destination: `${backend}/login` },
        { source: "/login/:path*", destination: `${backend}/login/:path*` },
        { source: "/auth/:path*", destination: `${backend}/auth/:path*` },
        { source: "/logout", destination: `${backend}/logout` },
        { source: "/api/:path*", destination: `${backend}/api/:path*` },
        { source: "/static/:path*", destination: `${backend}/static/:path*` },
        { source: "/socket.io/:path*", destination: `${backend}/socket.io/:path*` }
      ]
    };
  }
};

module.exports = nextConfig;
