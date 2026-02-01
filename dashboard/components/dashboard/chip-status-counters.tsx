'use client'

import { type ChipStatusCount, type ChipStatus } from '@/types/dashboard'

interface ChipStatusCountersProps {
  counts: ChipStatusCount[]
}

const statusConfig: Record<string, { label: string; bgColor: string; textColor: string }> = {
  active: { label: 'Active', bgColor: 'bg-status-success', textColor: 'text-status-success-foreground' },
  ready: { label: 'Ready', bgColor: 'bg-status-info', textColor: 'text-status-info-foreground' },
  warming: { label: 'Warming', bgColor: 'bg-status-warning', textColor: 'text-status-warning-foreground' },
  degraded: { label: 'Degraded', bgColor: 'bg-orange-100', textColor: 'text-orange-700' },
  banned: { label: 'Banned', bgColor: 'bg-status-error', textColor: 'text-status-error-foreground' },
  provisioned: { label: 'Provisioned', bgColor: 'bg-status-neutral', textColor: 'text-status-neutral-foreground' },
  pending: { label: 'Pending', bgColor: 'bg-status-neutral', textColor: 'text-status-neutral-foreground' },
  paused: { label: 'Paused', bgColor: 'bg-status-neutral', textColor: 'text-status-neutral-foreground' },
  cancelled: { label: 'Cancelled', bgColor: 'bg-status-neutral', textColor: 'text-status-neutral-foreground' },
  offline: { label: 'Offline', bgColor: 'bg-status-error', textColor: 'text-status-error-foreground' },
}

const defaultConfig = { label: 'Unknown', bgColor: 'bg-status-neutral', textColor: 'text-status-neutral-foreground' }

export function ChipStatusCounters({ counts = [] }: ChipStatusCountersProps) {
  // Filtrar apenas status relevantes
  const relevantStatuses: ChipStatus[] = ['active', 'ready', 'warming', 'degraded']
  const filteredCounts = counts.filter((c) => relevantStatuses.includes(c.status))

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-medium text-foreground/80">Status do Pool</h4>
      <div className="grid grid-cols-4 gap-2">
        {filteredCounts.map((item) => {
          const config = statusConfig[item.status] || defaultConfig
          return (
            <div key={item.status} className={`${config.bgColor} rounded-lg p-3 text-center`}>
              <div className={`text-2xl font-bold ${config.textColor}`}>{item.count}</div>
              <div className={`text-xs ${config.textColor}`}>{config.label}</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
