import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { POST } from '@/app/api/integridade/anomalias/[id]/resolver/route'
import { NextRequest } from 'next/server'

// Mock fetch globally
const mockFetch = vi.fn()
global.fetch = mockFetch

// Mock environment variables
const originalEnv = process.env

function createRequest(body: Record<string, unknown>) {
  return new NextRequest('http://localhost:3000/api/integridade/anomalias/test-id/resolver', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })
}

describe('POST /api/integridade/anomalias/[id]/resolver', () => {
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

  it('resolves anomaly successfully', async () => {
    const mockResult = {
      success: true,
      anomaly_id: 'anomaly-123',
      resolved_at: '2026-01-15T10:30:00Z',
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResult),
    })

    const request = createRequest({
      notas: '[Corrigido] Fixed the issue',
      usuario: 'dashboard',
    })

    const response = await POST(request, { params: Promise.resolve({ id: 'anomaly-123' }) })
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data).toEqual(mockResult)
  })

  it('calls backend with correct URL and body', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ success: true }),
    })

    const body = {
      notas: '[Falso Positivo] Not a real issue',
      usuario: 'admin',
    }

    const request = createRequest(body)
    await POST(request, { params: Promise.resolve({ id: 'my-anomaly-id' }) })

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/integridade/anomalias/my-anomaly-id/resolver',
      expect.objectContaining({
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer test-secret',
        },
        body: JSON.stringify(body),
      })
    )
  })

  it('returns 500 when backend fails', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: () => Promise.resolve({ detail: 'Anomaly not found' }),
    })

    const request = createRequest({ notas: 'test' })
    const response = await POST(request, { params: Promise.resolve({ id: 'not-found' }) })
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.error).toBe('Anomaly not found')
  })

  it('returns generic error when backend returns no detail', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: () => Promise.resolve({}),
    })

    const request = createRequest({ notas: 'test' })
    const response = await POST(request, { params: Promise.resolve({ id: 'anomaly-123' }) })
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.error).toBe('Erro ao resolver anomalia')
  })

  it('returns 500 when fetch throws', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Connection refused'))

    const request = createRequest({ notas: 'test' })
    const response = await POST(request, { params: Promise.resolve({ id: 'anomaly-123' }) })
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.error).toBe('Connection refused')
  })

  it('handles json parse error in error response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: () => Promise.reject(new Error('Invalid JSON')),
    })

    const request = createRequest({ notas: 'test' })
    const response = await POST(request, { params: Promise.resolve({ id: 'anomaly-123' }) })
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.error).toBe('Erro ao resolver anomalia')
  })

  it('passes different anomaly ids correctly', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ success: true }),
    })

    const request = createRequest({ notas: 'test' })
    await POST(request, { params: Promise.resolve({ id: 'uuid-1234-5678-90ab' }) })

    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/integridade/anomalias/uuid-1234-5678-90ab/resolver',
      expect.any(Object)
    )
  })
})
