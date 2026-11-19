import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    unoptimized: true,
  },
  async rewrites() {
    const rawBackend =
      process.env.INTERNAL_API_URL ||
      process.env.NEXT_PUBLIC_API_BASE_URL ||
      "https://truthlens-api-nflc.onrender.com";

    let backend = rawBackend.trim().replace(/\/$/, "");
    if (!backend.startsWith("http://") && !backend.startsWith("https://")) {
      backend = `https://${backend}`;
    }

    return [
      {
        source: "/api/:path*",
        destination: `${backend}/api/:path*`,
      },
      {
        source: "/health",
        destination: `${backend}/health`,
      },
      {
        source: "/storage/:path*",
        destination: `${backend}/storage/:path*`,
      },
    ];
  },
};

export default nextConfig;

