/**
 * Testes para lib/swr/config
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { FetchError, fetcher, postFetcher } from '@/lib/swr/config'

// Mock global fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('FetchError', () => {
  it('deve criar erro com name, status e info', () => {
    const error = new FetchError('test error', 404, { detail: 'not found' })

    expect(error.name).toBe('FetchError')
    expect(error.message).toBe('test error')
    expect(error.status).toBe(404)
    expect(error.info).toEqual({ detail: 'not found' })
  })

  it('deve criar erro sem status e info', () => {
    const error = new FetchError('test error')

    expect(error.name).toBe('FetchError')
    expect(error.status).toBeUndefined()
    expect(error.info).toBeUndefined()
  })
})

describe('fetcher', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('deve retornar JSON parsed quando resposta ok', async () => {
    const mockData = { id: 1, name: 'test' }
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    })

    const result = await fetcher('/api/test')

    expect(result).toEqual(mockData)
    expect(mockFetch).toHaveBeenCalledWith('/api/test')
  })

  it('deve lancar FetchError com info JSON quando resposta nao ok', async () => {
    const errorInfo = { message: 'Not found' }
    mockFetch.mockResolvedValue({
      ok: false,
      status: 404,
      json: () => Promise.resolve(errorInfo),
    })

    await expect(fetcher('/api/test')).rejects.toThrow(FetchError)

    try {
      await fetcher('/api/test')
    } catch (e) {
      const error = e as FetchError
      expect(error.status).toBe(404)
      expect(error.info).toEqual(errorInfo)
    }
  })

  it('deve usar statusText como fallback quando JSON parse falha', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: () => Promise.reject(new Error('invalid json')),
    })

    try {
      await fetcher('/api/test')
    } catch (e) {
      const error = e as FetchError
      expect(error.status).toBe(500)
      expect(error.info).toEqual({ message: 'Internal Server Error' })
    }
  })
})

describe('postFetcher', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('deve enviar POST com headers e body corretos e retornar JSON', async () => {
    const mockData = { success: true }
    const body = { chipId: 'chip-1', action: 'pause' }

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    })

    const result = await postFetcher('/api/chips/action', body)

    expect(result).toEqual(mockData)
    expect(mockFetch).toHaveBeenCalledWith('/api/chips/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  })

  it('deve lancar FetchError quando resposta nao ok', async () => {
    const errorInfo = { message: 'Bad request' }
    mockFetch.mockResolvedValue({
      ok: false,
      status: 400,
      json: () => Promise.resolve(errorInfo),
    })

    await expect(postFetcher('/api/test', {})).rejects.toThrow(FetchError)

    try {
      await postFetcher('/api/test', {})
    } catch (e) {
      const error = e as FetchError
      expect(error.status).toBe(400)
      expect(error.info).toEqual(errorInfo)
    }
  })

  it('deve usar statusText como fallback quando JSON parse falha em erro', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 503,
      statusText: 'Service Unavailable',
      json: () => Promise.reject(new Error('not json')),
    })

    try {
      await postFetcher('/api/test', { data: 1 })
    } catch (e) {
      const error = e as FetchError
      expect(error.status).toBe(503)
      expect(error.info).toEqual({ message: 'Service Unavailable' })
    }
  })
})
