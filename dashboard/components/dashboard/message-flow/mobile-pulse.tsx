'use client'

import type { MessageFlowData } from '@/types/dashboard'
import { ArrowDown, ArrowUp } from 'lucide-react'

interface MobilePulseProps {
  data: MessageFlowData
}

export function MobilePulse({ data }: MobilePulseProps) {
  const activeChips = data.chips.filter((c) => c.isActive).length
  const totalChips = data.chips.length
  const isActive = data.messagesPerMinute > 0

  const totalOutbound = data.chips.reduce((sum, c) => sum + c.recentOutbound, 0)
  const totalInbound = data.chips.reduce((sum, c) => sum + c.recentInbound, 0)

  // Pulse speed: faster when more active (2s base, down to 0.8s)
  const pulseSpeed = isActive ? `${Math.max(0.8, 2 - data.messagesPerMinute * 0.05)}s` : '2s'

  return (
    <div className="flex flex-col gap-2 py-1">
      {/* Row 1: Status + msg/min */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className={`inline-block h-3 w-3 rounded-full ${
              isActive ? 'mf-mobile-pulse bg-primary' : 'bg-muted-foreground'
            }`}
            style={
              isActive ? ({ '--mf-pulse-speed': pulseSpeed } as React.CSSProperties) : undefined
            }
          />
          <span className="text-sm font-medium">Julia {isActive ? 'Ativa' : 'Idle'}</span>
        </div>
        <span className="text-sm text-muted-foreground">{data.messagesPerMinute} msg/min</span>
      </div>

      {/* Row 2: Chip bar */}
      <div className="flex items-center gap-2">
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary transition-all duration-500"
            style={{
              width: totalChips > 0 ? `${(activeChips / totalChips) * 100}%` : '0%',
            }}
          />
        </div>
        <span className="whitespace-nowrap text-xs text-muted-foreground">
          {activeChips}/{totalChips} chips
        </span>
      </div>

      {/* Row 3: Inbound/Outbound counters */}
      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1">
          <ArrowUp className="h-3 w-3 text-status-info-solid" />
          {totalOutbound} enviadas
        </span>
        <span className="flex items-center gap-1">
          <ArrowDown className="h-3 w-3 text-status-success-solid" />
          {totalInbound} recebidas
        </span>
      </div>
    </div>
  )
}
