/**
 * Meta API Client - Sprint 69
 *
 * Cliente para comunicação com endpoints Meta do backend.
 */

import type {
  MetaQualityOverview,
  MetaQualityHistoryPoint,
  MetaCostSummary,
  MetaCostByChip,
  MetaCostByTemplate,
  MetaTemplateWithAnalytics,
  MetaDashboardResponse,
} from '@/types/meta'

// ============================================================================
// Error Handling
// ============================================================================

export class MetaApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message)
    this.name = 'MetaApiError'
  }
}

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const message =
      (body as Record<string, unknown>).error ?? response.statusText ?? 'Erro desconhecido'
    throw new MetaApiError(response.status, String(message))
  }

  return response.json()
}

// ============================================================================
// Quality
// ============================================================================

export async function getQualityOverview(): Promise<MetaQualityOverview> {
  const res = await fetchApi<MetaDashboardResponse<MetaQualityOverview>>(
    '/api/dashboard/meta/quality'
  )
  return res.data
}

export async function getQualityHistory(chipId: string): Promise<MetaQualityHistoryPoint[]> {
  const res = await fetchApi<MetaDashboardResponse<MetaQualityHistoryPoint[]>>(
    `/api/dashboard/meta/quality/history?chip_id=${chipId}`
  )
  return res.data
}

export async function triggerKillSwitch(chipId: string): Promise<void> {
  await fetchApi('/api/dashboard/meta/quality/kill-switch', {
    method: 'POST',
    body: JSON.stringify({ chip_id: chipId }),
  })
}

// ============================================================================
// Costs
// ============================================================================

export async function getCostSummary(period: string = '7d'): Promise<MetaCostSummary> {
  const res = await fetchApi<MetaDashboardResponse<MetaCostSummary>>(
    `/api/dashboard/meta/costs/summary?period=${period}`
  )
  return res.data
}

export async function getCostByChip(): Promise<MetaCostByChip[]> {
  const res = await fetchApi<MetaDashboardResponse<MetaCostByChip[]>>(
    '/api/dashboard/meta/costs/by-chip'
  )
  return res.data
}

export async function getCostByTemplate(): Promise<MetaCostByTemplate[]> {
  const res = await fetchApi<MetaDashboardResponse<MetaCostByTemplate[]>>(
    '/api/dashboard/meta/costs/by-template'
  )
  return res.data
}

// ============================================================================
// Templates
// ============================================================================

export async function getTemplates(): Promise<MetaTemplateWithAnalytics[]> {
  const res = await fetchApi<MetaDashboardResponse<MetaTemplateWithAnalytics[]>>(
    '/api/dashboard/meta/templates'
  )
  return res.data
}

// ============================================================================
// Export as namespace
// ============================================================================

export const metaApi = {
  getQualityOverview,
  getQualityHistory,
  triggerKillSwitch,
  getCostSummary,
  getCostByChip,
  getCostByTemplate,
  getTemplates,
}
