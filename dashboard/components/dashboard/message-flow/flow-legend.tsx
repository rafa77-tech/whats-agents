import type { ChipNodeStatus } from '@/types/dashboard'

const LEGEND_ITEMS: Array<{ status: ChipNodeStatus; label: string; color: string }> = [
  { status: 'active', label: 'ativo', color: 'bg-green-500' },
  { status: 'warming', label: 'aquecendo', color: 'bg-yellow-500' },
  { status: 'degraded', label: 'degradado', color: 'bg-red-500' },
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
        <span className="inline-block h-2 w-2 rounded-full bg-blue-400" />
        enviada
      </span>
      <span className="flex items-center gap-1.5">
        <span className="inline-block h-2 w-2 rounded-full bg-green-400" />
        recebida
      </span>
    </div>
  )
}
