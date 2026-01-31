/**
 * Jobs Stats Cards - Sprint 42
 *
 * Grid de 4 cards com estatisticas de jobs.
 */

'use client'

import { Card, CardContent } from '@/components/ui/card'
import { Server, CheckCircle, XCircle, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'

interface JobsStatsCardsProps {
  stats: {
    totalJobs: number
    successRate24h: number
    failedJobs24h: number
    runningJobs: number
    staleJobs: number
  } | null
  isLoading?: boolean
}

export function JobsStatsCards({ stats, isLoading }: JobsStatsCardsProps) {
  if (isLoading || !stats) {
    return (
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="p-4">
              <div className="animate-pulse space-y-2">
                <div className="h-4 w-16 rounded bg-gray-200" />
                <div className="h-8 w-12 rounded bg-gray-200" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  const cards = [
    {
      label: 'Total Jobs',
      value: stats.totalJobs,
      icon: Server,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
    },
    {
      label: 'Taxa de Sucesso',
      value: `${stats.successRate24h}%`,
      icon: CheckCircle,
      color:
        stats.successRate24h >= 95
          ? 'text-green-600'
          : stats.successRate24h >= 80
            ? 'text-yellow-600'
            : 'text-red-600',
      bgColor:
        stats.successRate24h >= 95
          ? 'bg-green-50'
          : stats.successRate24h >= 80
            ? 'bg-yellow-50'
            : 'bg-red-50',
    },
    {
      label: 'Jobs com Erro',
      value: stats.failedJobs24h,
      icon: XCircle,
      color:
        stats.failedJobs24h === 0
          ? 'text-green-600'
          : stats.failedJobs24h <= 3
            ? 'text-yellow-600'
            : 'text-red-600',
      bgColor:
        stats.failedJobs24h === 0
          ? 'bg-green-50'
          : stats.failedJobs24h <= 3
            ? 'bg-yellow-50'
            : 'bg-red-50',
    },
    {
      label: 'Jobs Atrasados',
      value: stats.staleJobs,
      icon: AlertTriangle,
      color:
        stats.staleJobs === 0
          ? 'text-green-600'
          : stats.staleJobs <= 2
            ? 'text-yellow-600'
            : 'text-red-600',
      bgColor:
        stats.staleJobs === 0 ? 'bg-green-50' : stats.staleJobs <= 2 ? 'bg-yellow-50' : 'bg-red-50',
    },
  ]

  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
      {cards.map((card) => (
        <Card key={card.label}>
          <CardContent className={cn('p-4', card.bgColor)}>
            <div className="flex items-center gap-3">
              <card.icon className={cn('h-8 w-8', card.color)} />
              <div>
                <div className="text-sm text-gray-600">{card.label}</div>
                <div className={cn('text-2xl font-bold', card.color)}>{card.value}</div>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
