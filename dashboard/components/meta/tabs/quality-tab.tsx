'use client'

import { useEffect, useState, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useToast } from '@/hooks/use-toast'
import { metaApi } from '@/lib/api/meta'
import type { MetaQualityOverview, MetaQualityRating } from '@/types/meta'
import { cn } from '@/lib/utils'

const RATING_CONFIG: Record<MetaQualityRating, { label: string; className: string }> = {
  GREEN: { label: 'Verde', className: 'bg-status-success text-status-success-foreground' },
  YELLOW: { label: 'Amarelo', className: 'bg-status-warning text-status-warning-foreground' },
  RED: { label: 'Vermelho', className: 'bg-status-error text-status-error-foreground' },
  UNKNOWN: { label: 'Desconhecido', className: 'bg-muted text-muted-foreground' },
}

export default function QualityTab() {
  const { toast } = useToast()
  const [overview, setOverview] = useState<MetaQualityOverview | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const data = await metaApi.getQualityOverview()
      setOverview(data)
    } catch (err) {
      toast({
        title: 'Erro ao carregar qualidade',
        description: err instanceof Error ? err.message : 'Erro desconhecido',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }, [toast])

  useEffect(() => {
    void fetchData()
  }, [fetchData])

  if (loading) {
    return <div className="text-sm text-muted-foreground">Carregando qualidade...</div>
  }

  if (!overview) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          Dados de qualidade indisponiveis.
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Overview cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Total Chips</p>
            <p className="text-3xl font-bold tabular-nums">{overview.total}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Verde</p>
            <p className="text-3xl font-bold tabular-nums text-status-success-foreground">
              {overview.green}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Amarelo</p>
            <p className="text-3xl font-bold tabular-nums text-status-warning-foreground">
              {overview.yellow}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Vermelho</p>
            <p className="text-3xl font-bold tabular-nums text-status-error-foreground">
              {overview.red}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Chip list */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Chips por Qualidade</CardTitle>
        </CardHeader>
        <CardContent>
          {overview.chips.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nenhum chip Meta ativo.</p>
          ) : (
            <div className="space-y-2">
              {overview.chips.map((chip) => {
                const config = RATING_CONFIG[chip.quality_rating]
                return (
                  <div
                    key={chip.chip_id}
                    className="flex items-center justify-between rounded-lg border p-3"
                  >
                    <div>
                      <p className="text-sm font-medium">{chip.chip_nome}</p>
                      <p className="text-xs text-muted-foreground">Trust: {chip.trust_score}</p>
                    </div>
                    <Badge className={cn('text-xs', config.className)}>{config.label}</Badge>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
