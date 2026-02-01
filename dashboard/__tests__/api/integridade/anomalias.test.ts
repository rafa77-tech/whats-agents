import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { GET } from '@/app/api/integridade/anomalias/route'
import { NextRequest } from 'next/server'

// Mock fetch globally
const mockFetch = vi.fn()
global.fetch = mockFetch

// Mock environment variables
const originalEnv = process.env

function createRequest(params: Record<string, string> = {}) {
  const searchParams = new URLSearchParams(params)
  const url = `http://localhost:3000/api/integridade/anomalias?${searchParams}`
  return new NextRequest(url)
}

describe('GET /api/integridade/anomalias', () => {
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

  it('returns anomalias from backend', async () => {
    const mockAnomalias = {
      anomalias: [
        { id: '1', tipo: 'duplicata', severidade: 'high' },
        { id: '2', tipo: 'faltando', severidade: 'low' },
      ],
      total: 2,
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockAnomalias),
    })

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data).toEqual(mockAnomalias)
  })

  it('passes query params to backend', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ anomalias: [] }),
    })

    const request = createRequest({ limit: '50', offset: '10', resolvidas: 'true' })
    await GET(request)

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/integridade/anomalias?limit=50&offset=10&resolvidas=true',
      expect.any(Object)
    )
  })

  it('uses default query params', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ anomalias: [] }),
    })

    const request = createRequest()
    await GET(request)

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/integridade/anomalias?limit=20&offset=0&resolvidas=false',
      expect.any(Object)
    )
  })

  it('sends authorization header', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ anomalias: [] }),
    })

    const request = createRequest()
    await GET(request)

    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: {
          Authorization: 'Bearer test-secret',
        },
      })
    )
  })

  it('returns empty list when backend fails', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
    })

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data).toEqual({
      anomalias: [],
      total: 0,
      total_abertas: 0,
      total_resolvidas: 0,
    })
  })

  it('returns empty list when fetch throws', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'))

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.anomalias).toEqual([])
  })
})
