/**
 * Mock Data Index - E2E Tests
 *
 * Centralized mock data for running E2E tests without a backend.
 * These mocks are used when the E2E_MOCK environment variable is set.
 */

export * from './chips'
export * from './dashboard'
export * from './sistema'

/**
 * Check if we should use mock data
 * Returns true when:
 * - E2E_MOCK env var is set to 'true'
 * - NODE_ENV is 'test' without Supabase configured
 *
 * NOTE: Do NOT check CI=true here as Railway sets CI=true during builds,
 * which would incorrectly enable mocks in production.
 */
export function shouldUseMock(): boolean {
  return (
    process.env.E2E_MOCK === 'true' ||
    (process.env.NODE_ENV === 'test' && !process.env.SUPABASE_URL)
  )
}
