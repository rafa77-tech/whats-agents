/**
 * Tests for Meta API client
 * @see dashboard/lib/api/meta.ts
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { MetaApiError, metaApi } from '@/lib/api/meta'

const mockFetch = vi.fn()

beforeEach(() => {
  vi.stubGlobal('fetch', mockFetch)
  mockFetch.mockReset()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('MetaApiError', () => {
  it('should create error with status and message', () => {
    const error = new MetaApiError(404, 'Not found')
    expect(error.status).toBe(404)
    expect(error.message).toBe('Not found')
    expect(error.name).toBe('MetaApiError')
  })

  it('should be instance of Error', () => {
    const error = new MetaApiError(500, 'Server error')
    expect(error).toBeInstanceOf(Error)
  })
})

describe('metaApi', () => {
  describe('getQualityOverview', () => {
    it('should fetch quality overview and return data', async () => {
      const mockOverview = {
        total: 5,
        green: 3,
        yellow: 1,
        red: 1,
        unknown: 0,
        chips: [],
      }

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: 'ok', data: mockOverview }),
      })

      const result = await metaApi.getQualityOverview()
      expect(result).toEqual(mockOverview)
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/dashboard/meta/quality',
        expect.objectContaining({
          headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
        })
      )
    })
  })

  describe('getCostSummary', () => {
    it('should fetch cost summary with default period', async () => {
      const mockSummary = {
        total_messages: 100,
        free_messages: 20,
        paid_messages: 80,
        total_cost_usd: 5.5,
        by_category: {},
      }

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: 'ok', data: mockSummary }),
      })

      const result = await metaApi.getCostSummary()
      expect(result).toEqual(mockSummary)
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/dashboard/meta/costs/summary?period=7d',
        expect.any(Object)
      )
    })

    it('should pass custom period param', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: 'ok', data: {} }),
      })

      await metaApi.getCostSummary('30d')
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/dashboard/meta/costs/summary?period=30d',
        expect.any(Object)
      )
    })
  })

  describe('error handling', () => {
    it('should throw MetaApiError on non-ok response', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      })

      await expect(metaApi.getTemplates()).rejects.toThrow(MetaApiError)
    })
  })
})
