'use client'

import { formatDistanceToNow } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { PeriodSelector } from './period-selector'
import { ExportMenu } from './export-menu'
import { type DashboardPeriod } from '@/types/dashboard'

interface DashboardHeaderProps {
  juliaStatus: 'online' | 'offline' | 'degraded'
  lastHeartbeat: Date | null
  uptime30d: number
  selectedPeriod: DashboardPeriod
  onPeriodChange: (period: DashboardPeriod) => void
  onExport: (format: 'csv' | 'pdf') => void
  onRefresh?: () => void
  isRefreshing?: boolean
}

export function DashboardHeader({
  juliaStatus,
  lastHeartbeat,
  uptime30d,
  selectedPeriod,
  onPeriodChange,
  onExport,
  onRefresh,
  isRefreshing = false,
}: DashboardHeaderProps) {
  const isOnline = juliaStatus === 'online'
  const isDegraded = juliaStatus === 'degraded'

  return (
    <div className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-6 py-4">
      <div className="flex items-center gap-6">
        {/* Status Julia */}
        <div className="flex items-center gap-2">
          <span
            className={`h-3 w-3 rounded-full ${
              isOnline
                ? 'animate-pulse bg-green-500'
                : isDegraded
                  ? 'animate-pulse bg-yellow-500'
                  : 'bg-red-500'
            }`}
          />
          <span className="font-medium text-gray-900">
            Julia {isOnline ? 'Online' : isDegraded ? 'Degraded' : 'Offline'}
          </span>
        </div>

        {/* Separador */}
        <div className="h-6 w-px bg-gray-200" />

        {/* Ultimo Heartbeat */}
        {lastHeartbeat && (
          <div className="text-sm text-gray-500">
            Ultimo:{' '}
            <span className="text-gray-700">
              {formatDistanceToNow(lastHeartbeat, {
                addSuffix: true,
                locale: ptBR,
              })}
            </span>
          </div>
        )}

        {/* Separador */}
        <div className="h-6 w-px bg-gray-200" />

        {/* Uptime */}
        <div className="text-sm text-gray-500">
          Uptime 30d:{' '}
          <span
            className={`font-medium ${
              uptime30d >= 99
                ? 'text-green-600'
                : uptime30d >= 95
                  ? 'text-yellow-600'
                  : 'text-red-600'
            }`}
          >
            {uptime30d.toFixed(1)}%
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <PeriodSelector value={selectedPeriod} onChange={onPeriodChange} />
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="flex h-9 w-9 items-center justify-center rounded-md border border-gray-200 bg-white text-gray-600 transition-colors hover:bg-gray-50 hover:text-gray-900 disabled:cursor-not-allowed disabled:opacity-50"
            title="Atualizar dados"
            aria-label="Atualizar dados"
          >
            <svg
              className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          </button>
        )}
        <ExportMenu onExport={onExport} />
      </div>
    </div>
  )
}
