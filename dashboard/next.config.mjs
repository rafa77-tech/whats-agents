import bundleAnalyzer from '@next/bundle-analyzer'

const withBundleAnalyzer = bundleAnalyzer({
  enabled: process.env.ANALYZE === 'true',
})

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Redirects para URLs antigas do modulo de chips (Sprint 45)
  async redirects() {
    return [
      {
        source: '/chips/alertas',
        destination: '/chips?tab=alertas',
        permanent: true,
      },
      {
        source: '/chips/grupos',
        destination: '/grupos',
        permanent: true,
      },
      {
        source: '/chips/warmup',
        destination: '/chips?tab=warmup',
        permanent: true,
      },
      {
        source: '/chips/configuracoes',
        destination: '/chips?tab=configuracoes',
        permanent: true,
      },
    ]
  },

  // Permitir imagens do Supabase
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '*.supabase.co',
      },
    ],
  },

  // Headers de segurança
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
        ],
      },
    ]
  },

  // TypeScript strict mode
  typescript: {
    // Fail build on TypeScript errors
    ignoreBuildErrors: false,
  },

  // ESLint strict mode
  eslint: {
    // Fail build on ESLint errors
    ignoreDuringBuilds: false,
  },

  // Experimental features
  experimental: {
    // Type-safe server actions
    typedRoutes: true,
  },

  // Output standalone for Docker/Railway
  output: 'standalone',

  // Optimize for production
  poweredByHeader: false,
  reactStrictMode: true,
}

export default withBundleAnalyzer(nextConfig)
