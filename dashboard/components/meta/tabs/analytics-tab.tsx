'use client'

import { useEffect, useState, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useToast } from '@/hooks/use-toast'
import { metaApi } from '@/lib/api/meta'
import type { MetaCostSummary, MetaCostByChip, MetaCostByTemplate } from '@/types/meta'

export default function AnalyticsTab() {
  const { toast } = useToast()
  const [summary, setSummary] = useState<MetaCostSummary | null>(null)
  const [byChip, setByChip] = useState<MetaCostByChip[]>([])
  const [byTemplate, setByTemplate] = useState<MetaCostByTemplate[]>([])
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const [s, c, t] = await Promise.all([
        metaApi.getCostSummary(),
        metaApi.getCostByChip(),
        metaApi.getCostByTemplate(),
      ])
      setSummary(s)
      setByChip(c)
      setByTemplate(t)
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

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Total Mensagens</p>
              <p className="text-3xl font-bold tabular-nums">{summary.total_messages}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Gratuitas</p>
              <p className="text-3xl font-bold tabular-nums text-status-success-foreground">
                {summary.free_messages}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Pagas</p>
              <p className="text-3xl font-bold tabular-nums">{summary.paid_messages}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Custo Total (USD)</p>
              <p className="text-3xl font-bold tabular-nums">
                ${summary.total_cost_usd.toFixed(2)}
              </p>
            </CardContent>
          </Card>
        </div>
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
            <div className="overflow-x-auto">
              <table className="w-full text-sm" role="table">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="pb-3 pr-4 font-medium">Chip</th>
                    <th className="pb-3 pr-4 text-right font-medium">Mensagens</th>
                    <th className="pb-3 text-right font-medium">Custo (USD)</th>
                  </tr>
                </thead>
                <tbody>
                  {byChip.map((c) => (
                    <tr key={c.chip_id} className="border-b last:border-0">
                      <td className="py-3 pr-4 font-medium">
                        {c.chip_nome || c.chip_id.slice(0, 8)}
                      </td>
                      <td className="py-3 pr-4 text-right tabular-nums">{c.total_messages}</td>
                      <td className="py-3 text-right tabular-nums">
                        ${c.total_cost_usd.toFixed(4)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

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
