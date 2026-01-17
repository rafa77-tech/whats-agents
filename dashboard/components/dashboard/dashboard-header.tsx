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
}

export function DashboardHeader({
  juliaStatus,
  lastHeartbeat,
  uptime30d,
  selectedPeriod,
  onPeriodChange,
  onExport,
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
        <ExportMenu onExport={onExport} />
      </div>
    </div>
  )
}
