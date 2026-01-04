'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuth } from '@/hooks/use-auth'

interface FunnelData {
  prospecting: number
  engaged: number
  negotiating: number
  converted: number
  total: number
}

function FunnelCardSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-32" />
      </CardHeader>
      <CardContent className="space-y-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="space-y-1">
            <div className="flex items-center justify-between">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-4 w-12" />
            </div>
            <Skeleton className="h-2 w-full" />
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

export function FunnelCard() {
  const { session } = useAuth()
  const [funnel, setFunnel] = useState<FunnelData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchFunnel() {
      if (!session?.access_token) return

      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const response = await fetch(`${apiUrl}/dashboard/status`, {
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        })

        if (response.ok) {
          const data = await response.json()
          setFunnel(data.funnel)
        }
      } catch (err) {
        console.error('Failed to fetch funnel data:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchFunnel()
  }, [session?.access_token])

  if (loading) {
    return <FunnelCardSkeleton />
  }

  // Default mock data if API fails
  const data = funnel || {
    prospecting: 0,
    engaged: 0,
    negotiating: 0,
    converted: 0,
    total: 0,
  }

  const maxValue = Math.max(data.total, 1)

  const stages = [
    {
      label: 'Prospeccao',
      value: data.prospecting,
      percentage: (data.prospecting / maxValue) * 100,
      color: 'bg-blue-500',
    },
    {
      label: 'Engajados',
      value: data.engaged,
      percentage: (data.engaged / maxValue) * 100,
      color: 'bg-emerald-500',
    },
    {
      label: 'Negociando',
      value: data.negotiating,
      percentage: (data.negotiating / maxValue) * 100,
      color: 'bg-amber-500',
    },
    {
      label: 'Convertidos',
      value: data.converted,
      percentage: (data.converted / maxValue) * 100,
      color: 'bg-purple-500',
    },
  ]

  const taxaConversao = data.total > 0 ? ((data.converted / data.total) * 100).toFixed(1) : '0.0'
  const metaConversao = 5 // 5% meta
  const atMeta = parseFloat(taxaConversao) >= metaConversao

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Funil de Vendas</span>
          <span className="text-sm font-normal text-muted-foreground">{data.total} total</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {stages.map((stage) => (
          <div key={stage.label} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">{stage.label}</span>
              <span className="text-muted-foreground">
                {stage.value}
                <span className="ml-1">({stage.percentage.toFixed(1)}%)</span>
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-secondary">
              <div
                className={`h-full ${stage.color} transition-all`}
                style={{ width: `${stage.percentage}%` }}
              />
            </div>
          </div>
        ))}

        {/* Summary */}
        <div className="flex items-center justify-between border-t pt-4">
          <div>
            <p className="text-sm text-muted-foreground">Taxa End-to-End</p>
            <p className="text-2xl font-bold">{taxaConversao}%</p>
          </div>
          <div className="text-right">
            <p className="text-sm text-muted-foreground">Meta</p>
            <p className={`text-lg font-semibold ${atMeta ? 'text-green-500' : 'text-amber-500'}`}>
              {metaConversao}%{atMeta ? ' ✓' : ''}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
