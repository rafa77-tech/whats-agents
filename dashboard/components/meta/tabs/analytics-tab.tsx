'use client'

import { useEffect, useState, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useToast } from '@/hooks/use-toast'
import { metaApi } from '@/lib/api/meta'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import type {
  MetaCostSummary,
  MetaCostByChip,
  MetaCostByTemplate,
  MetaBudgetStatus,
} from '@/types/meta'
import { MessageSquare, Gift, CreditCard, DollarSign, Gauge } from 'lucide-react'
import { cn } from '@/lib/utils'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'

const CATEGORY_COLORS: Record<string, string> = {
  MARKETING: '#a855f7',
  UTILITY: '#3b82f6',
  AUTHENTICATION: '#f59e0b',
}

export default function AnalyticsTab() {
  const { toast } = useToast()
  const [summary, setSummary] = useState<MetaCostSummary | null>(null)
  const [byChip, setByChip] = useState<MetaCostByChip[]>([])
  const [byTemplate, setByTemplate] = useState<MetaCostByTemplate[]>([])
  const [budget, setBudget] = useState<MetaBudgetStatus | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const [s, c, t, b] = await Promise.all([
        metaApi.getCostSummary(),
        metaApi.getCostByChip(),
        metaApi.getCostByTemplate(),
        metaApi.getBudgetStatus(),
      ])
      setSummary(s)
      setByChip(c)
      setByTemplate(t)
      setBudget(b)
    } catch (err) {
      toast({
        title: 'Erro ao carregar custos',
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
    return <div className="text-sm text-muted-foreground">Carregando custos...</div>
  }

  const pieData = summary?.by_category
    ? Object.entries(summary.by_category).map(([name, { count }]) => ({
        name,
        value: count,
      }))
    : []

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-2">
                <MessageSquare className="h-4 w-4 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">Total Mensagens</p>
              </div>
              <p className="mt-1 text-3xl font-bold tabular-nums">{summary.total_messages}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-2">
                <Gift className="h-4 w-4 text-status-success-foreground" />
                <p className="text-sm text-muted-foreground">Gratuitas</p>
              </div>
              <p className="mt-1 text-3xl font-bold tabular-nums text-status-success-foreground">
                {summary.free_messages}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-2">
                <CreditCard className="h-4 w-4 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">Pagas</p>
              </div>
              <p className="mt-1 text-3xl font-bold tabular-nums">{summary.paid_messages}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-2">
                <DollarSign className="h-4 w-4 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">Custo Total (USD)</p>
              </div>
              <p className="mt-1 text-3xl font-bold tabular-nums">
                ${summary.total_cost_usd.toFixed(2)}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Budget status */}
      {budget && <BudgetStatusCard budget={budget} />}

      {/* Pie chart + cost by chip side by side */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Category distribution */}
        {pieData.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Distribuicao por Categoria</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[250px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={55}
                      outerRadius={85}
                      paddingAngle={3}
                      dataKey="value"
                    >
                      {pieData.map((entry) => (
                        <Cell
                          key={entry.name}
                          fill={CATEGORY_COLORS[entry.name] ?? '#94a3b8'}
                          strokeWidth={0}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        borderRadius: '8px',
                        border: '1px solid hsl(var(--border))',
                        backgroundColor: 'hsl(var(--popover))',
                        color: 'hsl(var(--popover-foreground))',
                        fontSize: '12px',
                      }}
                    />
                    <Legend
                      verticalAlign="bottom"
                      iconType="circle"
                      iconSize={8}
                      formatter={(value: string) => (
                        <span className="text-xs text-muted-foreground">{value}</span>
                      )}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Cost by chip */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Custo por Chip</CardTitle>
          </CardHeader>
          <CardContent>
            {byChip.length === 0 ? (
              <p className="text-sm text-muted-foreground">Sem dados de custo por chip.</p>
            ) : (
              <div className="space-y-2">
                {byChip.map((c) => (
                  <div
                    key={c.chip_id}
                    className="flex items-center justify-between rounded-lg border p-3"
                  >
                    <div>
                      <p className="text-sm font-medium">{c.chip_nome || c.chip_id.slice(0, 8)}</p>
                      <p className="text-xs text-muted-foreground">{c.total_messages} mensagens</p>
                    </div>
                    <p className="text-sm font-medium tabular-nums">
                      ${c.total_cost_usd.toFixed(4)}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Cost by template */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Custo por Template</CardTitle>
        </CardHeader>
        <CardContent>
          {byTemplate.length === 0 ? (
            <p className="text-sm text-muted-foreground">Sem dados de custo por template.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm" role="table">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="pb-3 pr-4 font-medium">Template</th>
                    <th className="pb-3 pr-4 font-medium">Categoria</th>
                    <th className="pb-3 pr-4 text-right font-medium">Enviados</th>
                    <th className="pb-3 text-right font-medium">Custo (USD)</th>
                  </tr>
                </thead>
                <tbody>
                  {byTemplate.map((t) => (
                    <tr key={t.template_name} className="border-b last:border-0">
                      <td className="py-3 pr-4 font-medium">{t.template_name}</td>
                      <td className="py-3 pr-4 text-xs text-muted-foreground">{t.category}</td>
                      <td className="py-3 pr-4 text-right tabular-nums">{t.total_sent}</td>
                      <td className="py-3 text-right tabular-nums">
                        ${t.total_cost_usd.toFixed(4)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

const BUDGET_FALLBACK = { label: 'OK', variant: 'default' as const }

const BUDGET_STATUS_CONFIG: Record<
  string,
  { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }
> = {
  ok: { label: 'OK', variant: 'default' },
  warning: { label: 'Alerta', variant: 'secondary' },
  critical: { label: 'Critico', variant: 'destructive' },
  blocked: { label: 'Bloqueado', variant: 'destructive' },
}

function BudgetStatusCard({ budget }: { budget: MetaBudgetStatus }) {
  const config = BUDGET_STATUS_CONFIG[budget.status] ?? BUDGET_FALLBACK

  const rows = [
    {
      label: 'Diario',
      used: budget.daily_used_usd,
      limit: budget.daily_limit_usd,
      percent: budget.daily_percent,
    },
    {
      label: 'Semanal',
      used: budget.weekly_used_usd,
      limit: budget.weekly_limit_usd,
      percent: budget.weekly_percent,
    },
    {
      label: 'Mensal',
      used: budget.monthly_used_usd,
      limit: budget.monthly_limit_usd,
      percent: budget.monthly_percent,
    },
  ]

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <Gauge className="h-4 w-4" />
            Budget
          </CardTitle>
          <Badge variant={config.variant}>{config.label}</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {rows.map((row) => (
            <div key={row.label}>
              <div className="mb-1 flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{row.label}</span>
                <span className="tabular-nums">
                  ${row.used.toFixed(2)} / ${row.limit.toFixed(0)}
                </span>
              </div>
              <Progress
                value={Math.min(row.percent, 100)}
                className={cn(
                  'h-2',
                  row.percent >= 90
                    ? '[&>div]:bg-status-error'
                    : row.percent >= 80
                      ? '[&>div]:bg-status-warning'
                      : '[&>div]:bg-status-success'
                )}
              />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
