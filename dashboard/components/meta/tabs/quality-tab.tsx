'use client'

import { useEffect, useState, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { useToast } from '@/hooks/use-toast'
import { metaApi } from '@/lib/api/meta'
import type {
  MetaQualityOverview,
  MetaQualityRating,
  MetaQualityHistoryPoint,
  MetaWindowSummary,
} from '@/types/meta'
import { cn } from '@/lib/utils'
import { Shield, CheckCircle, AlertTriangle, XCircle, Clock, Wifi } from 'lucide-react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

const RATING_CONFIG: Record<MetaQualityRating, { label: string; className: string }> = {
  GREEN: { label: 'Verde', className: 'bg-status-success text-status-success-foreground' },
  YELLOW: { label: 'Amarelo', className: 'bg-status-warning text-status-warning-foreground' },
  RED: { label: 'Vermelho', className: 'bg-status-error text-status-error-foreground' },
  UNKNOWN: { label: 'Desconhecido', className: 'bg-muted text-muted-foreground' },
}

const TRUST_COLOR: Record<string, string> = {
  high: '[&>div]:bg-trust-verde-solid',
  medium: '[&>div]:bg-trust-amarelo-solid',
  low: '[&>div]:bg-trust-vermelho-solid',
}

function getTrustLevel(score: number): string {
  if (score >= 70) return 'high'
  if (score >= 40) return 'medium'
  return 'low'
}

export default function QualityTab() {
  const { toast } = useToast()
  const [overview, setOverview] = useState<MetaQualityOverview | null>(null)
  const [history, setHistory] = useState<MetaQualityHistoryPoint[]>([])
  const [windows, setWindows] = useState<MetaWindowSummary | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const data = await metaApi.getQualityOverview()
      setOverview(data)

      // Load history for first chip if available
      const firstChip = data.chips[0]
      if (firstChip) {
        const h = await metaApi.getQualityHistory(firstChip.chip_id)
        setHistory(h)
      }

      // Load window summary
      try {
        const w = await metaApi.getWindowSummary()
        setWindows(w)
      } catch {
        // Windows endpoint may not exist yet
      }
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
            <div className="flex items-center gap-2">
              <Shield className="h-4 w-4 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">Total Chips</p>
            </div>
            <p className="mt-1 text-3xl font-bold tabular-nums">{overview.total}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-status-success-foreground" />
              <p className="text-sm text-muted-foreground">Verde</p>
            </div>
            <p className="mt-1 text-3xl font-bold tabular-nums text-status-success-foreground">
              {overview.green}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-status-warning-foreground" />
              <p className="text-sm text-muted-foreground">Amarelo</p>
            </div>
            <p className="mt-1 text-3xl font-bold tabular-nums text-status-warning-foreground">
              {overview.yellow}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              <XCircle className="h-4 w-4 text-status-error-foreground" />
              <p className="text-sm text-muted-foreground">Vermelho</p>
            </div>
            <p className="mt-1 text-3xl font-bold tabular-nums text-status-error-foreground">
              {overview.red}
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Chip list with progress bars */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Chips por Qualidade</CardTitle>
          </CardHeader>
          <CardContent>
            {overview.chips.length === 0 ? (
              <p className="text-sm text-muted-foreground">Nenhum chip Meta ativo.</p>
            ) : (
              <div className="space-y-3">
                {overview.chips.map((chip) => {
                  const config = RATING_CONFIG[chip.quality_rating]
                  const trustLevel = getTrustLevel(chip.trust_score)
                  return (
                    <div key={chip.chip_id} className="rounded-lg border p-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium">{chip.chip_nome}</p>
                        </div>
                        <Badge className={cn('text-xs', config.className)}>{config.label}</Badge>
                      </div>
                      <div className="mt-2 flex items-center gap-2">
                        <Progress
                          value={chip.trust_score}
                          className={cn('h-2', TRUST_COLOR[trustLevel])}
                        />
                        <span className="min-w-[3ch] text-right text-xs tabular-nums text-muted-foreground">
                          {chip.trust_score}
                        </span>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Quality timeline chart */}
        {history.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Timeline de Trust Score</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[250px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={history.map((h) => ({
                      ...h,
                      time: new Date(h.timestamp).toLocaleDateString('pt-BR', {
                        day: '2-digit',
                        month: '2-digit',
                        hour: '2-digit',
                        minute: '2-digit',
                      }),
                    }))}
                    margin={{ top: 5, right: 20, bottom: 5, left: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis dataKey="time" className="text-[10px]" />
                    <YAxis domain={[0, 100]} className="text-[10px]" />
                    <Tooltip
                      contentStyle={{
                        borderRadius: '8px',
                        border: '1px solid hsl(var(--border))',
                        backgroundColor: 'hsl(var(--popover))',
                        color: 'hsl(var(--popover-foreground))',
                        fontSize: '12px',
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="trust_score"
                      stroke="#25D366"
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      name="Trust Score"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Window summary */}
      {windows && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Wifi className="h-4 w-4" />
              Janelas de Conversa
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4">
              <div className="rounded-lg border p-3 text-center">
                <p className="text-xs text-muted-foreground">Ativas</p>
                <p className="text-2xl font-bold tabular-nums text-status-success-foreground">
                  {windows.active}
                </p>
              </div>
              <div className="rounded-lg border p-3 text-center">
                <div className="flex items-center justify-center gap-1">
                  <Clock className="h-3 w-3 text-status-warning-foreground" />
                  <p className="text-xs text-muted-foreground">Expirando</p>
                </div>
                <p className="text-2xl font-bold tabular-nums text-status-warning-foreground">
                  {windows.expiring}
                </p>
              </div>
              <div className="rounded-lg border p-3 text-center">
                <p className="text-xs text-muted-foreground">Expiradas</p>
                <p className="text-2xl font-bold tabular-nums text-muted-foreground">
                  {windows.expired}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
