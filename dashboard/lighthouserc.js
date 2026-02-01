/**
 * Lighthouse CI Configuration
 * @see https://github.com/GoogleChrome/lighthouse-ci/blob/main/docs/configuration.md
 */
module.exports = {
  ci: {
    collect: {
      // Start the Next.js server
      startServerCommand: 'npm run start',
      startServerReadyPattern: 'Ready in',
      startServerReadyTimeout: 30000,

      // URL(s) to test
      url: ['http://localhost:3000/', 'http://localhost:3000/login'],

      // Number of runs per URL (more runs = more accurate)
      numberOfRuns: 3,

      // Chromium settings
      settings: {
        chromeFlags: '--no-sandbox --disable-gpu --headless',
        // Throttling preset (mobile simulation)
        preset: 'desktop',
        // Skip audits that require network
        skipAudits: ['uses-http2'],
      },
    },

    assert: {
      // Assertion preset
      preset: 'lighthouse:recommended',

      assertions: {
        // Performance (0-100)
        'categories:performance': ['warn', { minScore: 0.7 }],
        'categories:accessibility': ['error', { minScore: 0.9 }],
        'categories:best-practices': ['warn', { minScore: 0.8 }],
        'categories:seo': ['warn', { minScore: 0.8 }],

        // Core Web Vitals
        'first-contentful-paint': ['warn', { maxNumericValue: 2000 }],
        'largest-contentful-paint': ['warn', { maxNumericValue: 2500 }],
        'cumulative-layout-shift': ['warn', { maxNumericValue: 0.1 }],
        'total-blocking-time': ['warn', { maxNumericValue: 300 }],
        interactive: ['warn', { maxNumericValue: 3500 }],
        'speed-index': ['warn', { maxNumericValue: 3000 }],

        // Accessibility
        'color-contrast': 'error',
        'document-title': 'error',
        'html-has-lang': 'error',
        'meta-viewport': 'error',
        'image-alt': 'error',
        'link-name': 'error',
        'button-name': 'error',
        label: 'error',

        // Best Practices
        'errors-in-console': 'off', // CI doesn't have backend, so console errors are expected
        'valid-source-maps': 'off',
        'inspector-issues': 'warn',

        // SEO
        viewport: 'error',
        'meta-description': 'warn',
        'crawlable-anchors': 'warn',
        'robots-txt': 'off', // Not applicable for SPA

        // PWA (optional, set to off if not PWA)
        'installable-manifest': 'off',
        'service-worker': 'off',
        'maskable-icon': 'off',

        // Security
        'is-on-https': 'off', // Localhost doesn't have HTTPS
        'csp-xss': 'warn',

        // Disable audits that return NaN on pages without applicable content
        // (e.g., login page has no LCP image, no animations)
        'lcp-lazy-loaded': 'off',
        'non-composited-animations': 'off',
        'prioritize-lcp-image': 'off',

        // Allow some unused JS/CSS (Next.js/Tailwind framework overhead is unavoidable)
        'unused-javascript': 'off',
        'unused-css-rules': 'off',

        // Disable deprecated/removed audits
        'no-unload-listeners': 'off',
      },
    },

    upload: {
      // Upload to temporary public storage (free, reports expire after 7 days)
      target: 'temporary-public-storage',

      // OR upload to Lighthouse CI Server (self-hosted)
      // target: 'lhci',
      // serverBaseUrl: 'https://your-lhci-server.com',
      // token: process.env.LHCI_TOKEN,

      // GitHub status check integration
      githubAppToken: process.env.LHCI_GITHUB_APP_TOKEN,
      githubStatusContextSuffix: '/dashboard',
    },
  },
}
