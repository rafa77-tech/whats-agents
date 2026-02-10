import type { ChipNodeStatus } from '@/types/dashboard'

const LEGEND_ITEMS: Array<{ status: ChipNodeStatus; label: string; color: string }> = [
  { status: 'active', label: 'ativo', color: 'bg-status-success-solid' },
  { status: 'warming', label: 'aquecendo', color: 'bg-status-warning-solid' },
  { status: 'degraded', label: 'degradado', color: 'bg-status-error-solid' },
  { status: 'paused', label: 'pausado', color: 'bg-gray-400' },
]

export function FlowLegend() {
  return (
    <div className="hidden items-center justify-center gap-4 text-xs text-muted-foreground md:flex">
      {LEGEND_ITEMS.map(({ status, label, color }) => (
        <span key={status} className="flex items-center gap-1.5">
          <span className={`inline-block h-2 w-2 rounded-full ${color}`} />
          {label}
        </span>
      ))}
      <span className="mx-1 text-border">|</span>
      <span className="flex items-center gap-1.5">
        <span className="inline-block h-2 w-2 rounded-full bg-status-info-solid" />
        enviada
      </span>
      <span className="flex items-center gap-1.5">
        <span className="inline-block h-2 w-2 rounded-full bg-status-success-solid" />
        recebida
      </span>
    </div>
  )
}
