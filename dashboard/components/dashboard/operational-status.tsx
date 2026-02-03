'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { RateLimitBar } from './rate-limit-bar'
import { InstanceStatusList } from './instance-status-list'
import { type OperationalStatusData } from '@/types/dashboard'
import { Activity, Cpu, MessageSquare } from 'lucide-react'

interface OperationalStatusProps {
  data: OperationalStatusData
}

export function OperationalStatus({ data }: OperationalStatusProps) {
  const { rateLimitHour, rateLimitDay, queueSize, llmUsage, instances } = data

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <Activity className="h-4 w-4" />
          Status Operacional
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Rate Limits */}
        <div className="space-y-3">
          <RateLimitBar data={rateLimitHour} />
          <RateLimitBar data={rateLimitDay} />
        </div>

        {/* Fila e LLM */}
        <div className="flex items-center justify-between border-t pt-2">
          <div className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-muted-foreground/70" />
            <span className="text-sm text-foreground/80">
              Fila: <span className="font-medium">{queueSize} msgs</span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Cpu className="h-4 w-4 text-muted-foreground/70" />
            <span className="text-sm text-foreground/80">
              <span className="font-medium">{llmUsage.haiku}%</span> Haiku /{' '}
              <span className="font-medium">{llmUsage.sonnet}%</span> Sonnet
            </span>
          </div>
        </div>

        {/* Instancias */}
        <div className="border-t pt-2">
          <InstanceStatusList instances={instances} />
        </div>
      </CardContent>
    </Card>
  )
}
