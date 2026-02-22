'use client'

import { useEffect, useState, useCallback } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useToast } from '@/hooks/use-toast'
import { metaApi } from '@/lib/api/meta'
import type { MetaTemplateWithAnalytics, TemplateStatus } from '@/types/meta'
import { WhatsAppPreview } from '../whatsapp-preview'
import { Send, CheckCircle2, Eye } from 'lucide-react'

const STATUS_VARIANT: Record<TemplateStatus, 'default' | 'secondary' | 'destructive' | 'outline'> =
  {
    APPROVED: 'default',
    PENDING: 'secondary',
    REJECTED: 'destructive',
    PAUSED: 'outline',
    DISABLED: 'outline',
  }

const CATEGORY_COLORS: Record<string, string> = {
  MARKETING: 'bg-status-info text-status-info-foreground',
  UTILITY: 'bg-status-success text-status-success-foreground',
  AUTHENTICATION: 'bg-status-warning text-status-warning-foreground',
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
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {templates.map((t) => (
        <Card key={t.id} className="overflow-hidden">
          <CardContent className="p-0">
            <div className="flex flex-col gap-0 lg:flex-row">
              {/* Left: Info */}
              <div className="flex flex-1 flex-col justify-between p-4">
                <div>
                  <div className="mb-2 flex items-center gap-2">
                    <Badge variant={STATUS_VARIANT[t.status]} className="text-[10px]">
                      {t.status}
                    </Badge>
                    <Badge
                      variant="outline"
                      className={`border-0 text-[10px] ${CATEGORY_COLORS[t.category] ?? ''}`}
                    >
                      {t.category}
                    </Badge>
                  </div>
                  <p className="font-mono text-sm font-medium">{t.template_name}</p>
                  {t.variable_mapping && Object.keys(t.variable_mapping).length > 0 && (
                    <p className="mt-1 text-xs text-muted-foreground">
                      {Object.keys(t.variable_mapping).length} variavel(is)
                    </p>
                  )}
                </div>

                {/* Metrics */}
                {t.analytics && (
                  <div className="mt-3 flex gap-3 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1" title="Enviados">
                      <Send className="h-3 w-3" />
                      {t.analytics.total_sent}
                    </span>
                    <span className="flex items-center gap-1" title="Entrega">
                      <CheckCircle2 className="h-3 w-3" />
                      {(t.analytics.delivery_rate * 100).toFixed(0)}%
                    </span>
                    <span className="flex items-center gap-1" title="Leitura">
                      <Eye className="h-3 w-3" />
                      {(t.analytics.read_rate * 100).toFixed(0)}%
                    </span>
                  </div>
                )}
              </div>

              {/* Right: WhatsApp Preview */}
              <WhatsAppPreview
                components={t.components}
                className="min-h-[160px] border-t lg:w-[260px] lg:border-l lg:border-t-0"
              />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
