import { describe, it, expect, vi, beforeEach } from 'vitest'
import { NextRequest } from 'next/server'

// Mock fetch before importing routes
const mockFetch = vi.fn()
global.fetch = mockFetch

// We test the route handlers by importing them dynamically
describe('Group Entry API Routes', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.stubEnv('NEXT_PUBLIC_API_URL', 'http://localhost:8000')
    vi.stubEnv('API_SECRET', 'test-secret')
  })

  describe('GET /api/group-entry/dashboard', () => {
    it('returns dashboard data on success', async () => {
      const mockData = {
        links: { total: 100, pending: 10, validated: 20, scheduled: 30, processed: 40 },
        queue: { queued: 5, processing: 2 },
        processed_today: { success: 15, failed: 3 },
      }

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockData),
      })

      const { GET } = await import('@/app/api/group-entry/dashboard/route')
      const response = await GET()
      const data = await response.json()

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/group-entry/dashboard',
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer test-secret',
          }),
        })
      )
      expect(data).toEqual(mockData)
    })

    it('returns error on backend failure', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        json: () => Promise.resolve({ detail: 'Backend error' }),
      })

      const { GET } = await import('@/app/api/group-entry/dashboard/route')
      const response = await GET()

      expect(response.status).toBe(500)
    })
  })

  describe('GET /api/group-entry/capacity', () => {
    it('returns capacity data on success', async () => {
      const mockData = { used: 50, total: 100 }

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockData),
      })

      const { GET } = await import('@/app/api/group-entry/capacity/route')
      const response = await GET()
      const data = await response.json()

      expect(data).toEqual(mockData)
    })
  })

  describe('GET /api/group-entry/links', () => {
    it('returns links data on success', async () => {
      const mockData = {
        links: [
          { id: '1', url: 'https://chat.whatsapp.com/abc', status: 'pending' },
        ],
      }

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockData),
      })

      const { GET } = await import('@/app/api/group-entry/links/route')

      const request = new NextRequest('http://localhost:3000/api/group-entry/links?status=pending')
      const response = await GET(request)
      const data = await response.json()

      expect(data).toEqual(mockData)
    })
  })

  describe('GET /api/group-entry/queue', () => {
    it('returns queue data on success', async () => {
      const mockData = {
        queue: [
          { id: '1', link_url: 'https://chat.whatsapp.com/abc', status: 'queued' },
        ],
      }

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockData),
      })

      const { GET } = await import('@/app/api/group-entry/queue/route')
      const response = await GET()
      const data = await response.json()

      expect(data).toEqual(mockData)
    })
  })

  describe('GET /api/group-entry/config', () => {
    it('returns config on success', async () => {
      const mockData = {
        grupos_por_dia: 10,
        intervalo_min: 30,
        intervalo_max: 60,
      }

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockData),
      })

      const { GET } = await import('@/app/api/group-entry/config/route')
      const response = await GET()
      const data = await response.json()

      expect(data).toEqual(mockData)
    })
  })

  describe('PATCH /api/group-entry/config', () => {
    it('updates config on success', async () => {
      const mockData = { success: true }

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockData),
      })

      const { PATCH } = await import('@/app/api/group-entry/config/route')

      const request = new NextRequest('http://localhost:3000/api/group-entry/config', {
        method: 'PATCH',
        body: JSON.stringify({ grupos_por_dia: 15 }),
      })

      const response = await PATCH(request)
      const data = await response.json()

      expect(data).toEqual(mockData)
    })
  })

  describe('POST /api/group-entry/validate/batch', () => {
    it('validates batch on success', async () => {
      const mockData = { validated: 10 }

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockData),
      })

      const { POST } = await import('@/app/api/group-entry/validate/batch/route')

      const request = new NextRequest('http://localhost:3000/api/group-entry/validate/batch', {
        method: 'POST',
        body: JSON.stringify({ status: 'pending' }),
      })

      const response = await POST(request)
      const data = await response.json()

      expect(data).toEqual(mockData)
    })
  })

  describe('POST /api/group-entry/schedule/batch', () => {
    it('schedules batch on success', async () => {
      const mockData = { scheduled: 5 }

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockData),
      })

      const { POST } = await import('@/app/api/group-entry/schedule/batch/route')

      const request = new NextRequest('http://localhost:3000/api/group-entry/schedule/batch', {
        method: 'POST',
        body: JSON.stringify({ status: 'validated' }),
      })

      const response = await POST(request)
      const data = await response.json()

      expect(data).toEqual(mockData)
    })
  })

  describe('POST /api/group-entry/process', () => {
    it('processes queue on success', async () => {
      const mockData = { processed: 3 }

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockData),
      })

      const { POST } = await import('@/app/api/group-entry/process/route')
      const response = await POST()
      const data = await response.json()

      expect(data).toEqual(mockData)
    })
  })

  describe('POST /api/group-entry/validate/[id]', () => {
    it('validates single link on success', async () => {
      const mockData = { validated: true }

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockData),
      })

      const { POST } = await import('@/app/api/group-entry/validate/[id]/route')

      const request = new NextRequest('http://localhost:3000/api/group-entry/validate/link-123', {
        method: 'POST',
      })

      const response = await POST(request, { params: Promise.resolve({ id: 'link-123' }) })
      const data = await response.json()

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/group-entry/validate/link-123',
        expect.any(Object)
      )
      expect(data).toEqual(mockData)
    })
  })

  describe('POST /api/group-entry/schedule/[id]', () => {
    it('schedules single link on success', async () => {
      const mockData = { scheduled: true }

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockData),
      })

      const { POST } = await import('@/app/api/group-entry/schedule/[id]/route')

      const request = new NextRequest('http://localhost:3000/api/group-entry/schedule/link-123', {
        method: 'POST',
      })

      const response = await POST(request, { params: Promise.resolve({ id: 'link-123' }) })
      const data = await response.json()

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/group-entry/schedule/link-123',
        expect.any(Object)
      )
      expect(data).toEqual(mockData)
    })
  })

  describe('POST /api/group-entry/process/[id]', () => {
    it('processes single item on success', async () => {
      const mockData = { processed: true }

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockData),
      })

      const { POST } = await import('@/app/api/group-entry/process/[id]/route')

      const request = new NextRequest('http://localhost:3000/api/group-entry/process/queue-123', {
        method: 'POST',
      })

      const response = await POST(request, { params: Promise.resolve({ id: 'queue-123' }) })
      const data = await response.json()

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/group-entry/process/queue-123',
        expect.any(Object)
      )
      expect(data).toEqual(mockData)
    })
  })

  describe('DELETE /api/group-entry/queue/[id]', () => {
    it('deletes queue item on success', async () => {
      const mockData = { deleted: true }

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockData),
      })

      const { DELETE } = await import('@/app/api/group-entry/queue/[id]/route')

      const request = new NextRequest('http://localhost:3000/api/group-entry/queue/queue-123', {
        method: 'DELETE',
      })

      const response = await DELETE(request, { params: Promise.resolve({ id: 'queue-123' }) })
      const data = await response.json()

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/group-entry/queue/queue-123',
        expect.objectContaining({
          method: 'DELETE',
        })
      )
      expect(data).toEqual(mockData)
    })
  })

  describe('POST /api/group-entry/schedule', () => {
    it('schedules link with body on success', async () => {
      const mockData = { scheduled: true }

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockData),
      })

      const { POST } = await import('@/app/api/group-entry/schedule/route')

      const request = new NextRequest('http://localhost:3000/api/group-entry/schedule', {
        method: 'POST',
        body: JSON.stringify({ link_id: 'link-123' }),
      })

      const response = await POST(request)
      const data = await response.json()

      expect(data).toEqual(mockData)
    })
  })
})
