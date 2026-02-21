'use client'

import { useEffect, useState, useCallback } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useToast } from '@/hooks/use-toast'
import { metaApi } from '@/lib/api/meta'
import type { MetaFlow, FlowStatus } from '@/types/meta'
import { FlowScreenPreview } from '../flow-screen-preview'
import { Send, Archive, MessageSquare, Loader2 } from 'lucide-react'

const STATUS_CONFIG: Record<
  FlowStatus,
  { variant: 'default' | 'secondary' | 'destructive' | 'outline'; label: string }
> = {
  DRAFT: { variant: 'secondary', label: 'Rascunho' },
  PUBLISHED: { variant: 'default', label: 'Publicado' },
  DEPRECATED: { variant: 'outline', label: 'Descontinuado' },
  BLOCKED: { variant: 'destructive', label: 'Bloqueado' },
}

export default function FlowsTab() {
  const { toast } = useToast()
  const [flows, setFlows] = useState<MetaFlow[]>([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const data = await metaApi.getFlows()
      setFlows(data)
    } catch (err) {
      toast({
        title: 'Erro ao carregar flows',
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

  const handlePublish = async (flow: MetaFlow) => {
    setActionLoading(flow.id)
    try {
      await metaApi.publishFlow(flow.id)
      toast({ title: 'Flow publicado', description: `"${flow.name}" foi publicado.` })
      await fetchData()
    } catch (err) {
      toast({
        title: 'Erro ao publicar flow',
        description: err instanceof Error ? err.message : 'Erro desconhecido',
        variant: 'destructive',
      })
    } finally {
      setActionLoading(null)
    }
  }

  const handleDeprecate = async (flow: MetaFlow) => {
    setActionLoading(flow.id)
    try {
      await metaApi.deprecateFlow(flow.id)
      toast({ title: 'Flow descontinuado', description: `"${flow.name}" foi descontinuado.` })
      await fetchData()
    } catch (err) {
      toast({
        title: 'Erro ao descontinuar flow',
        description: err instanceof Error ? err.message : 'Erro desconhecido',
        variant: 'destructive',
      })
    } finally {
      setActionLoading(null)
    }
  }

  if (loading) {
    return <div className="text-sm text-muted-foreground">Carregando flows...</div>
  }

  if (flows.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          Nenhum WhatsApp Flow encontrado.
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {flows.map((flow) => {
        const config = STATUS_CONFIG[flow.status] ?? STATUS_CONFIG.DRAFT
        const hasScreens = flow.json_definition?.screens && flow.json_definition.screens.length > 0
        const isActioning = actionLoading === flow.id

        return (
          <Card key={flow.id} className="overflow-hidden">
            <CardContent className="p-0">
              <div className="flex flex-col">
                {/* Info section */}
                <div className="flex flex-1 flex-col justify-between p-4">
                  <div>
                    <div className="mb-2 flex items-center gap-2">
                      <Badge variant={config.variant} className="text-[10px]">
                        {config.label}
                      </Badge>
                      <Badge variant="outline" className="text-[10px]">
                        {flow.flow_type}
                      </Badge>
                    </div>
                    <p className="text-sm font-medium">{flow.name}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {new Date(flow.created_at).toLocaleDateString('pt-BR')}
                    </p>
                  </div>

                  {/* Metrics */}
                  <div className="mt-3 flex items-center gap-3 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1" title="Respostas">
                      <MessageSquare className="h-3 w-3" />
                      {flow.response_count ?? 0} respostas
                    </span>
                  </div>

                  {/* Actions */}
                  <div className="mt-3 flex gap-2">
                    {flow.status === 'DRAFT' && (
                      <Button
                        size="sm"
                        variant="default"
                        className="h-7 text-xs"
                        disabled={isActioning}
                        onClick={() => void handlePublish(flow)}
                      >
                        {isActioning ? (
                          <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                        ) : (
                          <Send className="mr-1 h-3 w-3" />
                        )}
                        Publicar
                      </Button>
                    )}
                    {flow.status === 'PUBLISHED' && (
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7 text-xs"
                        disabled={isActioning}
                        onClick={() => void handleDeprecate(flow)}
                      >
                        {isActioning ? (
                          <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                        ) : (
                          <Archive className="mr-1 h-3 w-3" />
                        )}
                        Descontinuar
                      </Button>
                    )}
                  </div>
                </div>

                {/* Screen preview */}
                {hasScreens && (
                  <FlowScreenPreview
                    screens={flow.json_definition!.screens}
                    className="min-h-[180px] border-t bg-muted/20"
                  />
                )}
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
