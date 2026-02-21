'use client'

import { useEffect, useState, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useToast } from '@/hooks/use-toast'
import { metaApi } from '@/lib/api/meta'
import type { MetaTemplateWithAnalytics, TemplateStatus } from '@/types/meta'

const STATUS_VARIANT: Record<TemplateStatus, 'default' | 'secondary' | 'destructive' | 'outline'> =
  {
    APPROVED: 'default',
    PENDING: 'secondary',
    REJECTED: 'destructive',
    PAUSED: 'outline',
    DISABLED: 'outline',
  }

export default function TemplatesTab() {
  const { toast } = useToast()
  const [templates, setTemplates] = useState<MetaTemplateWithAnalytics[]>([])
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const data = await metaApi.getTemplates()
      setTemplates(data)
    } catch (err) {
      toast({
        title: 'Erro ao carregar templates',
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
    return <div className="text-sm text-muted-foreground">Carregando templates...</div>
  }

  if (templates.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          Nenhum template Meta encontrado.
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Templates Meta</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm" role="table">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="pb-3 pr-4 font-medium">Nome</th>
                <th className="pb-3 pr-4 font-medium">Categoria</th>
                <th className="pb-3 pr-4 font-medium">Status</th>
                <th className="pb-3 pr-4 text-right font-medium">Enviados</th>
                <th className="pb-3 pr-4 text-right font-medium">Entrega</th>
                <th className="pb-3 text-right font-medium">Leitura</th>
              </tr>
            </thead>
            <tbody>
              {templates.map((t) => (
                <tr key={t.id} className="border-b last:border-0">
                  <td className="py-3 pr-4 font-medium">{t.template_name}</td>
                  <td className="py-3 pr-4">
                    <Badge variant="outline" className="text-xs">
                      {t.category}
                    </Badge>
                  </td>
                  <td className="py-3 pr-4">
                    <Badge variant={STATUS_VARIANT[t.status]}>{t.status}</Badge>
                  </td>
                  <td className="py-3 pr-4 text-right tabular-nums">
                    {t.analytics?.total_sent ?? '-'}
                  </td>
                  <td className="py-3 pr-4 text-right tabular-nums">
                    {t.analytics ? `${(t.analytics.delivery_rate * 100).toFixed(0)}%` : '-'}
                  </td>
                  <td className="py-3 text-right tabular-nums">
                    {t.analytics ? `${(t.analytics.read_rate * 100).toFixed(0)}%` : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}
