'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { MessageSquare, Clock, TrendingUp } from 'lucide-react'
import { formatTempoMedio } from '@/lib/health'
import type { QueueData } from '@/lib/health'

interface QueueStatusPanelProps {
  queue: QueueData | undefined
}

export function QueueStatusPanel({ queue }: QueueStatusPanelProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Fila de Mensagens</CardTitle>
        <CardDescription>Status da fila de processamento</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <div className="rounded-lg bg-status-neutral p-4 text-center">
            <div className="flex items-center justify-center gap-2 text-muted-foreground">
              <MessageSquare className="h-4 w-4" />
              <span className="text-xs">Pendentes</span>
            </div>
            <p className="mt-1 text-2xl font-bold text-foreground">{queue?.pendentes || 0}</p>
          </div>

          <div className="rounded-lg bg-status-info p-4 text-center">
            <div className="flex items-center justify-center gap-2 text-status-info-foreground">
              <TrendingUp className="h-4 w-4" />
              <span className="text-xs">Processando</span>
            </div>
            <p className="mt-1 text-2xl font-bold text-status-info-foreground">
              {queue?.processando || 0}
            </p>
          </div>

          <div className="rounded-lg bg-status-success p-4 text-center">
            <div className="flex items-center justify-center gap-2 text-status-success-foreground">
              <TrendingUp className="h-4 w-4" />
              <span className="text-xs">Processadas/h</span>
            </div>
            <p className="mt-1 text-2xl font-bold text-status-success-foreground">
              {queue?.processadasPorHora !== undefined ? queue.processadasPorHora : '-'}
            </p>
          </div>

          <div className="rounded-lg bg-status-neutral p-4 text-center">
            <div className="flex items-center justify-center gap-2 text-muted-foreground">
              <Clock className="h-4 w-4" />
              <span className="text-xs">Tempo Medio</span>
            </div>
            <p className="mt-1 text-2xl font-bold text-foreground">
              {formatTempoMedio(queue?.tempoMedioMs)}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
