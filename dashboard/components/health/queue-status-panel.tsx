'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { MessageSquare, Clock, TrendingUp } from 'lucide-react'

interface QueueStatusPanelProps {
  queue:
    | {
        pendentes: number
        processando: number
      }
    | undefined
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
          <div className="rounded-lg bg-gray-50 p-4 text-center">
            <div className="flex items-center justify-center gap-2 text-gray-500">
              <MessageSquare className="h-4 w-4" />
              <span className="text-xs">Pendentes</span>
            </div>
            <p className="mt-1 text-2xl font-bold text-gray-900">{queue?.pendentes || 0}</p>
          </div>

          <div className="rounded-lg bg-blue-50 p-4 text-center">
            <div className="flex items-center justify-center gap-2 text-blue-500">
              <TrendingUp className="h-4 w-4" />
              <span className="text-xs">Processando</span>
            </div>
            <p className="mt-1 text-2xl font-bold text-blue-600">{queue?.processando || 0}</p>
          </div>

          <div className="rounded-lg bg-gray-50 p-4 text-center">
            <div className="flex items-center justify-center gap-2 text-gray-500">
              <TrendingUp className="h-4 w-4" />
              <span className="text-xs">Processadas/h</span>
            </div>
            <p className="mt-1 text-2xl font-bold text-gray-900">-</p>
          </div>

          <div className="rounded-lg bg-gray-50 p-4 text-center">
            <div className="flex items-center justify-center gap-2 text-gray-500">
              <Clock className="h-4 w-4" />
              <span className="text-xs">Tempo Medio</span>
            </div>
            <p className="mt-1 text-2xl font-bold text-gray-900">-</p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
