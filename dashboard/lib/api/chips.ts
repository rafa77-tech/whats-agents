/**
 * Chips API Client - Sprint 36
 *
 * Cliente para comunicação com endpoints de chips do backend.
 */

import {
  PoolStatus,
  PoolHealthStatus,
  ChipsListParams,
  ChipsListResponse,
  ChipListItem,
  ChipFullDetail,
  ChipMetrics,
  ChipTrustHistory,
  ChipInteractionsResponse,
  ChipAlertsListParams,
  ChipAlertsListResponse,
  ChipAlert,
  ScheduledActivity,
  SchedulerStats,
  PoolConfig,
  ChipActionResponse,
  CreateInstanceRequest,
  CreateInstanceResponse,
  QRCodeResponse,
  ConnectionStateResponse,
} from '@/types/chips'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ''

// ============================================================================
// Error Handling
// ============================================================================

export class ChipsApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message)
    this.name = 'ChipsApiError'
  }
}

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const url = path.startsWith('/api/') ? path : `${API_BASE}${path}`

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (!response.ok) {
    throw new ChipsApiError(response.status, `API error: ${response.statusText}`)
  }

  return response.json()
}

// ============================================================================
// Pool Status
// ============================================================================

export async function getPoolStatus(): Promise<PoolStatus> {
  return fetchApi<PoolStatus>('/api/dashboard/chips')
}

export async function getPoolHealth(): Promise<PoolHealthStatus> {
  return fetchApi<PoolHealthStatus>('/api/dashboard/chips/health')
}

// ============================================================================
// Chips List
// ============================================================================

export async function listChips(params: ChipsListParams = {}): Promise<ChipsListResponse> {
  const searchParams = new URLSearchParams()

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      if (Array.isArray(value)) {
        value.forEach((v) => searchParams.append(key, String(v)))
      } else {
        searchParams.set(key, String(value))
      }
    }
  })

  const query = searchParams.toString()
  return fetchApi<ChipsListResponse>(`/api/dashboard/chips/list${query ? `?${query}` : ''}`)
}

// ============================================================================
// Chip Details
// ============================================================================

export async function getChip(id: string): Promise<ChipListItem> {
  return fetchApi<ChipListItem>(`/api/dashboard/chips/${id}`)
}

export async function getChipDetail(id: string): Promise<ChipFullDetail> {
  return fetchApi<ChipFullDetail>(`/api/dashboard/chips/${id}/detail`)
}

export async function getChipMetrics(
  id: string,
  period: '1h' | '6h' | '24h' | '7d' | '30d' = '24h'
): Promise<ChipMetrics> {
  return fetchApi<ChipMetrics>(`/api/dashboard/chips/${id}/metrics?period=${period}`)
}

export async function getChipTrustHistory(
  id: string,
  days: number = 30
): Promise<ChipTrustHistory> {
  return fetchApi<ChipTrustHistory>(`/api/dashboard/chips/${id}/trust-history?days=${days}`)
}

export async function getChipInteractions(
  id: string,
  params: { limit?: number; offset?: number; type?: string } = {}
): Promise<ChipInteractionsResponse> {
  const searchParams = new URLSearchParams()
  if (params.limit) searchParams.set('limit', String(params.limit))
  if (params.offset) searchParams.set('offset', String(params.offset))
  if (params.type) searchParams.set('type', params.type)

  const query = searchParams.toString()
  return fetchApi<ChipInteractionsResponse>(
    `/api/dashboard/chips/${id}/interactions${query ? `?${query}` : ''}`
  )
}

// ============================================================================
// Chip Actions
// ============================================================================

export async function pauseChip(id: string): Promise<ChipActionResponse> {
  return fetchApi<ChipActionResponse>(`/api/dashboard/chips/${id}/pause`, {
    method: 'POST',
  })
}

export async function resumeChip(id: string): Promise<ChipActionResponse> {
  return fetchApi<ChipActionResponse>(`/api/dashboard/chips/${id}/resume`, {
    method: 'POST',
  })
}

export async function promoteChip(id: string): Promise<ChipActionResponse> {
  return fetchApi<ChipActionResponse>(`/api/dashboard/chips/${id}/promote`, {
    method: 'POST',
  })
}

// ============================================================================
// Alerts
// ============================================================================

export async function listAlerts(
  params: ChipAlertsListParams = {}
): Promise<ChipAlertsListResponse> {
  const searchParams = new URLSearchParams()

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      if (Array.isArray(value)) {
        value.forEach((v) => searchParams.append(key, String(v)))
      } else {
        searchParams.set(key, String(value))
      }
    }
  })

  const query = searchParams.toString()
  return fetchApi<ChipAlertsListResponse>(`/api/dashboard/chips/alerts${query ? `?${query}` : ''}`)
}

export async function getAlert(id: string): Promise<ChipAlert> {
  return fetchApi<ChipAlert>(`/api/dashboard/chips/alerts/${id}`)
}

export async function resolveAlert(id: string, notes: string): Promise<{ success: boolean }> {
  return fetchApi<{ success: boolean }>(`/api/dashboard/chips/alerts/${id}/resolve`, {
    method: 'POST',
    body: JSON.stringify({ notes }),
  })
}

export async function getAlertsCount(): Promise<{
  total: number
  critical: number
  warning: number
}> {
  return fetchApi<{ total: number; critical: number; warning: number }>(
    '/api/dashboard/chips/alerts/count'
  )
}

// ============================================================================
// Scheduler
// ============================================================================

export async function getScheduledActivities(params: {
  date?: string
  chipId?: string
  limit?: number
}): Promise<ScheduledActivity[]> {
  const searchParams = new URLSearchParams()
  if (params.date) searchParams.set('date', params.date)
  if (params.chipId) searchParams.set('chipId', params.chipId)
  if (params.limit) searchParams.set('limit', String(params.limit))

  const query = searchParams.toString()
  return fetchApi<ScheduledActivity[]>(`/api/dashboard/chips/scheduler${query ? `?${query}` : ''}`)
}

export async function getSchedulerStats(date?: string): Promise<SchedulerStats> {
  const query = date ? `?date=${date}` : ''
  return fetchApi<SchedulerStats>(`/api/dashboard/chips/scheduler/stats${query}`)
}

// ============================================================================
// Config
// ============================================================================

export async function getPoolConfig(): Promise<PoolConfig> {
  return fetchApi<PoolConfig>('/api/dashboard/chips/config')
}

export async function updatePoolConfig(config: Partial<PoolConfig>): Promise<PoolConfig> {
  return fetchApi<PoolConfig>('/api/dashboard/chips/config', {
    method: 'PUT',
    body: JSON.stringify(config),
  })
}

// ============================================================================
// Instance Management (Sprint 40)
// ============================================================================

export async function createInstance(data: CreateInstanceRequest): Promise<CreateInstanceResponse> {
  return fetchApi<CreateInstanceResponse>('/api/dashboard/chips/instances', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function getInstanceQRCode(instanceName: string): Promise<QRCodeResponse> {
  return fetchApi<QRCodeResponse>(
    `/api/dashboard/chips/instances/${encodeURIComponent(instanceName)}/qr-code`
  )
}

export async function getInstanceConnectionState(
  instanceName: string
): Promise<ConnectionStateResponse> {
  return fetchApi<ConnectionStateResponse>(
    `/api/dashboard/chips/instances/${encodeURIComponent(instanceName)}/connection-state`
  )
}

// ============================================================================
// Export all as namespace
// ============================================================================

export const chipsApi = {
  // Pool
  getPoolStatus,
  getPoolHealth,
  // List
  listChips,
  // Detail
  getChip,
  getChipDetail,
  getChipMetrics,
  getChipTrustHistory,
  getChipInteractions,
  // Actions
  pauseChip,
  resumeChip,
  promoteChip,
  // Alerts
  listAlerts,
  getAlert,
  resolveAlert,
  getAlertsCount,
  // Scheduler
  getScheduledActivities,
  getSchedulerStats,
  // Config
  getPoolConfig,
  updatePoolConfig,
  // Instance Management (Sprint 40)
  createInstance,
  getInstanceQRCode,
  getInstanceConnectionState,
}
