import type { NextConfig } from "next";

const rawBackendUrl =
  process.env.BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

// Ensure the URL has a protocol — Render service names like
// "vinschool-ai-backend" need "https://" prepended.
const backendUrl =
  rawBackendUrl.startsWith("http://") || rawBackendUrl.startsWith("https://")
    ? rawBackendUrl
    : `https://${rawBackendUrl}`;

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${backendUrl}/api/:path*` },
      { source: "/uploads/:path*", destination: `${backendUrl}/uploads/:path*` },
    ];
  },
};

export default nextConfig;
