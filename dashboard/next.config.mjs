/** @type {import('next').NextConfig} */
const nextConfig = {
  // Permitir imagens do Supabase
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "*.supabase.co",
      },
    ],
  },

  // Headers de segurança
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
        ],
      },
    ];
  },

  // TypeScript strict mode
  typescript: {
    ignoreBuildErrors: false,
  },

  // ESLint strict mode
  eslint: {
    ignoreDuringBuilds: false,
  },

  // Output standalone for Docker/Railway
  output: "standalone",

  // Optimize for production
  poweredByHeader: false,
  reactStrictMode: true,
};

export default nextConfig;
