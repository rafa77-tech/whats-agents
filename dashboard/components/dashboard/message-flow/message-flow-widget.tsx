'use client'

import './message-flow.css'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { MessageFlowData } from '@/types/dashboard'
import { RadialGraph } from './radial-graph'
import { MobilePulse } from './mobile-pulse'
import { Activity } from 'lucide-react'

interface MessageFlowWidgetProps {
  data: MessageFlowData | null
  isLoading: boolean
}

export function MessageFlowWidget({ data, isLoading }: MessageFlowWidgetProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <div className="h-4 w-4 animate-pulse rounded bg-muted" />
            <div className="h-5 w-32 animate-pulse rounded bg-muted" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex h-[200px] items-center justify-center md:h-[240px]">
            <div className="h-32 w-32 animate-pulse rounded-full bg-muted/50" />
          </div>
        </CardContent>
      </Card>
    )
  }

  const isEmpty = !data || data.chips.length === 0

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <Activity className="h-4 w-4 text-muted-foreground" />
            Message Flow
          </CardTitle>
          {data && data.messagesPerMinute > 0 && (
            <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary">
              {data.messagesPerMinute}/min
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {isEmpty ? (
          <div className="flex h-[80px] items-center justify-center text-sm text-muted-foreground md:h-[240px]">
            Nenhum chip ativo
          </div>
        ) : (
          <>
            {/* Desktop/Tablet: Radial Graph */}
            <div className="hidden h-[240px] overflow-hidden md:block">
              <RadialGraph
                chips={data.chips}
                recentMessages={data.recentMessages}
                messagesPerMinute={data.messagesPerMinute}
              />
            </div>
            {/* Mobile: Compact pulse */}
            <div className="block md:hidden">
              <MobilePulse data={data} />
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}
