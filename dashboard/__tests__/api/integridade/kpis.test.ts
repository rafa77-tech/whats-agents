import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { GET } from '@/app/api/integridade/kpis/route'

// Mock fetch globally
const mockFetch = vi.fn()
global.fetch = mockFetch

// Mock environment variables
const originalEnv = process.env

describe('GET /api/integridade/kpis', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    process.env = {
      ...originalEnv,
      NEXT_PUBLIC_API_URL: 'http://localhost:8000',
      API_SECRET: 'test-secret',
    }
  })

  afterEach(() => {
    process.env = originalEnv
    vi.restoreAllMocks()
  })

  it('returns KPIs data from backend', async () => {
    const mockKpis = {
      health_score: 85,
      conversion_rate: 72,
      time_to_fill: 4.2,
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockKpis),
    })

    const response = await GET()
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data).toEqual(mockKpis)
  })

  it('calls backend with correct URL', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({}),
    })

    await GET()

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/integridade/kpis',
      expect.objectContaining({
        headers: {
          Authorization: 'Bearer test-secret',
        },
        cache: 'no-store',
      })
    )
  })

  it('returns mock data when backend fails', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
    })

    const response = await GET()
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data).toEqual({
      health_score: 85,
      conversion_rate: 72,
      time_to_fill: 4.2,
    })
  })

  it('returns mock data when fetch throws', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'))

    const response = await GET()
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.health_score).toBeDefined()
  })

  it('handles empty API_SECRET', async () => {
    process.env.API_SECRET = ''

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ health_score: 90 }),
    })

    await GET()

    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: {
          Authorization: 'Bearer ',
        },
      })
    )
  })
})
