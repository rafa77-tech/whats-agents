'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useToast } from '@/hooks/use-toast'
import {
  Megaphone,
  Plus,
  Clock,
  CheckCircle2,
  Play,
  Pause,
  FileEdit,
  Users,
  Send,
  MessageSquare,
  Loader2,
  RefreshCw,
  MoreHorizontal,
  Eye,
  Trash2,
  Copy,
} from 'lucide-react'
import { formatDistanceToNow, format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { NovaCampanhaWizard } from '@/components/campanhas/nova-campanha-wizard'

interface Campanha {
  id: number
  nome_template: string
  tipo_campanha: string
  categoria: string
  status: 'rascunho' | 'agendada' | 'ativa' | 'concluida' | 'pausada' | 'cancelada'
  objetivo?: string
  total_destinatarios: number
  enviados: number
  entregues: number
  respondidos: number
  agendar_para?: string
  iniciada_em?: string
  concluida_em?: string
  created_at: string
  created_by?: string
}

const statusConfig = {
  rascunho: {
    label: 'Rascunho',
    color: 'bg-status-neutral text-status-neutral-foreground border-muted',
    icon: FileEdit,
  },
  agendada: {
    label: 'Agendada',
    color: 'bg-status-info text-status-info-foreground border-status-info-border',
    icon: Clock,
  },
  ativa: {
    label: 'Ativa',
    color: 'bg-status-warning text-status-warning-foreground border-status-warning-border',
    icon: Play,
  },
  concluida: {
    label: 'Concluida',
    color: 'bg-status-success text-status-success-foreground border-status-success-border',
    icon: CheckCircle2,
  },
  pausada: {
    label: 'Pausada',
    color: 'bg-trust-laranja text-trust-laranja-foreground border-trust-laranja',
    icon: Pause,
  },
  cancelada: {
    label: 'Cancelada',
    color: 'bg-status-error text-status-error-foreground border-status-error-border',
    icon: Trash2,
  },
}

const tipoCampanhaLabels: Record<string, string> = {
  oferta_plantao: 'Oferta de Plantao',
  reativacao: 'Reativacao',
  followup: 'Follow-up',
  descoberta: 'Descoberta',
}

export default function CampanhasPage() {
  const { toast } = useToast()
  const [campanhas, setCampanhas] = useState<Campanha[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<'ativas' | 'historico'>('ativas')
  const [wizardOpen, setWizardOpen] = useState(false)

  const [error, setError] = useState<string | null>(null)

  const carregarCampanhas = useCallback(async () => {
    try {
      setError(null)
      const status = tab === 'ativas' ? 'rascunho,agendada,ativa,pausada' : 'concluida,cancelada'
      const res = await fetch(`/api/campanhas?status=${status}`)
      const data = await res.json()

      if (!res.ok) {
        setError(data.detail || 'Erro ao carregar campanhas')
        setCampanhas([])
        return
      }

      setCampanhas(Array.isArray(data) ? data : [])
    } catch (err) {
      console.error('Erro ao carregar campanhas:', err)
      setError('Erro de conexao com o servidor')
      setCampanhas([])
    } finally {
      setLoading(false)
    }
  }, [tab])

  useEffect(() => {
    setLoading(true)
    carregarCampanhas()
  }, [carregarCampanhas])

  const handleCampanhaCreated = () => {
    setWizardOpen(false)
    carregarCampanhas()
    toast({
      title: 'Campanha criada',
      description: 'A campanha foi criada com sucesso.',
    })
  }

  const ativasCount = campanhas.filter(
    (c) => c.status === 'ativa' || c.status === 'agendada'
  ).length

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Campanhas</h1>
          <p className="text-gray-500">Gerencie campanhas de prospecção e reativacao</p>
        </div>

        <div className="flex items-center gap-4">
          <Button variant="outline" onClick={carregarCampanhas} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Atualizar
          </Button>
          <Button onClick={() => setWizardOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Nova Campanha
          </Button>
        </div>
      </div>

      {/* Erro */}
      {error && (
        <div className="rounded-lg border border-status-error-border bg-status-error p-4">
          <p className="text-sm text-status-error-foreground">{error}</p>
        </div>
      )}

      {/* Cards de métricas */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Campanhas Ativas</p>
                <p className="text-2xl font-bold">{ativasCount}</p>
              </div>
              <Megaphone className="h-8 w-8 text-status-info-solid" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Enviados</p>
                <p className="text-2xl font-bold">
                  {campanhas.reduce((acc, c) => acc + (c.enviados || 0), 0)}
                </p>
              </div>
              <Send className="h-8 w-8 text-status-success-solid" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Entregues</p>
                <p className="text-2xl font-bold">
                  {campanhas.reduce((acc, c) => acc + (c.entregues || 0), 0)}
                </p>
              </div>
              <CheckCircle2 className="h-8 w-8 text-status-info-solid" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Respostas</p>
                <p className="text-2xl font-bold">
                  {campanhas.reduce((acc, c) => acc + (c.respondidos || 0), 0)}
                </p>
              </div>
              <MessageSquare className="h-8 w-8 text-accent" />
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs value={tab} onValueChange={(v) => setTab(v as typeof tab)}>
        <TabsList>
          <TabsTrigger value="ativas">
            Ativas
            {ativasCount > 0 && <Badge className="ml-2 bg-status-info-solid">{ativasCount}</Badge>}
          </TabsTrigger>
          <TabsTrigger value="historico">Historico</TabsTrigger>
        </TabsList>

        <TabsContent value="ativas" className="mt-4 space-y-4">
          {loading ? (
            <div className="py-8 text-center">
              <Loader2 className="mx-auto h-6 w-6 animate-spin text-gray-400" />
            </div>
          ) : campanhas.length === 0 ? (
            <div className="rounded-lg border bg-white py-12 text-center">
              <Megaphone className="mx-auto mb-4 h-12 w-12 text-gray-300" />
              <p className="text-lg font-medium">Nenhuma campanha ativa</p>
              <p className="mb-4 text-gray-500">
                Crie uma nova campanha para comecar a prospectar medicos.
              </p>
              <Button onClick={() => setWizardOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Nova Campanha
              </Button>
            </div>
          ) : (
            campanhas.map((campanha) => (
              <CampanhaCard key={campanha.id} campanha={campanha} onUpdate={carregarCampanhas} />
            ))
          )}
        </TabsContent>

        <TabsContent value="historico" className="mt-4 space-y-4">
          {loading ? (
            <div className="py-8 text-center">
              <Loader2 className="mx-auto h-6 w-6 animate-spin text-gray-400" />
            </div>
          ) : campanhas.length === 0 ? (
            <div className="rounded-lg border bg-white py-12 text-center">
              <p className="text-gray-500">Nenhuma campanha no historico.</p>
            </div>
          ) : (
            campanhas.map((campanha) => (
              <CampanhaCard
                key={campanha.id}
                campanha={campanha}
                onUpdate={carregarCampanhas}
                readOnly
              />
            ))
          )}
        </TabsContent>
      </Tabs>

      <NovaCampanhaWizard
        open={wizardOpen}
        onOpenChange={setWizardOpen}
        onSuccess={handleCampanhaCreated}
      />
    </div>
  )
}

interface CampanhaCardProps {
  campanha: Campanha
  onUpdate: () => void
  readOnly?: boolean
}

function CampanhaCard({ campanha, onUpdate, readOnly }: CampanhaCardProps) {
  const router = useRouter()
  const { toast } = useToast()
  const [duplicating, setDuplicating] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const status = statusConfig[campanha.status] || statusConfig.rascunho
  const StatusIcon = status.icon

  const handleDelete = async () => {
    setDeleting(true)
    try {
      const res = await fetch(`/api/campanhas/${campanha.id}`, { method: 'DELETE' })
      const data = await res.json()
      if (!res.ok) {
        toast({ title: 'Erro ao excluir', description: data.detail, variant: 'destructive' })
        return
      }
      toast({ title: 'Campanha excluida', description: 'A campanha foi removida com sucesso.' })
      onUpdate()
    } catch {
      toast({ title: 'Erro ao excluir', description: 'Erro de conexao', variant: 'destructive' })
    } finally {
      setDeleting(false)
      setConfirmDelete(false)
    }
  }

  const handleDuplicate = async (e: React.MouseEvent) => {
    e.stopPropagation()
    setDuplicating(true)
    try {
      const res = await fetch(`/api/campanhas/${campanha.id}/duplicate`, { method: 'POST' })
      const data = await res.json()
      if (!res.ok) {
        toast({ title: 'Erro ao duplicar', description: data.detail, variant: 'destructive' })
        return
      }
      toast({ title: 'Campanha duplicada', description: 'Redirecionando para edicao...' })
      router.push(`/campanhas/${data.id}/editar`)
    } catch {
      toast({ title: 'Erro ao duplicar', description: 'Erro de conexao', variant: 'destructive' })
    } finally {
      setDuplicating(false)
    }
  }

  const taxaEntrega =
    campanha.enviados > 0 ? Math.round((campanha.entregues / campanha.enviados) * 100) : 0

  const taxaResposta =
    campanha.entregues > 0 ? Math.round((campanha.respondidos / campanha.entregues) * 100) : 0

  return (
    <Card
      className="cursor-pointer transition-shadow hover:shadow-md"
      onClick={() => router.push(`/campanhas/${campanha.id}`)}
    >
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Megaphone className="h-5 w-5 text-gray-400" />
              {campanha.nome_template}
            </CardTitle>
            <p className="mt-1 text-sm text-gray-500">
              {tipoCampanhaLabels[campanha.tipo_campanha] || campanha.tipo_campanha}
              {campanha.categoria && ` • ${campanha.categoria}`}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Badge variant="outline" className={status.color}>
              <StatusIcon className="mr-1 h-3 w-3" />
              {status.label}
            </Badge>

            <DropdownMenu>
              <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                <Button variant="ghost" size="icon">
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
                <DropdownMenuItem
                  onClick={(e) => {
                    e.stopPropagation()
                    router.push(`/campanhas/${campanha.id}`)
                  }}
                >
                  <Eye className="mr-2 h-4 w-4" />
                  Ver Detalhes
                </DropdownMenuItem>
                <DropdownMenuItem onClick={handleDuplicate} disabled={duplicating}>
                  {duplicating ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Copy className="mr-2 h-4 w-4" />
                  )}
                  Duplicar
                </DropdownMenuItem>
                {!readOnly && campanha.status === 'rascunho' && (
                  <DropdownMenuItem
                    className="text-destructive"
                    onClick={(e) => {
                      e.stopPropagation()
                      setConfirmDelete(true)
                    }}
                    disabled={deleting}
                  >
                    {deleting ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="mr-2 h-4 w-4" />
                    )}
                    Excluir
                  </DropdownMenuItem>
                )}
              </DropdownMenuContent>
            </DropdownMenu>

            <AlertDialog open={confirmDelete} onOpenChange={setConfirmDelete}>
              <AlertDialogContent onClick={(e) => e.stopPropagation()}>
                <AlertDialogHeader>
                  <AlertDialogTitle>Excluir campanha?</AlertDialogTitle>
                  <AlertDialogDescription>
                    A campanha &quot;{campanha.nome_template}&quot; sera excluida permanentemente.
                    Esta acao nao pode ser desfeita.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel disabled={deleting}>Cancelar</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={() => void handleDelete()}
                    disabled={deleting}
                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                  >
                    {deleting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Excluir
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {/* Métricas */}
        <div className="grid grid-cols-4 gap-4 border-t py-4">
          <div className="text-center">
            <div className="flex items-center justify-center gap-1 text-gray-500">
              <Users className="h-4 w-4" />
              <span className="text-xs">Destinatarios</span>
            </div>
            <p className="text-lg font-semibold">{campanha.total_destinatarios || 0}</p>
          </div>

          <div className="text-center">
            <div className="flex items-center justify-center gap-1 text-gray-500">
              <Send className="h-4 w-4" />
              <span className="text-xs">Enviados</span>
            </div>
            <p className="text-lg font-semibold">{campanha.enviados || 0}</p>
          </div>

          <div className="text-center">
            <div className="flex items-center justify-center gap-1 text-gray-500">
              <CheckCircle2 className="h-4 w-4" />
              <span className="text-xs">Entregues</span>
            </div>
            <p className="text-lg font-semibold">
              {campanha.entregues || 0}
              {taxaEntrega > 0 && (
                <span className="ml-1 text-xs text-gray-400">({taxaEntrega}%)</span>
              )}
            </p>
          </div>

          <div className="text-center">
            <div className="flex items-center justify-center gap-1 text-gray-500">
              <MessageSquare className="h-4 w-4" />
              <span className="text-xs">Respostas</span>
            </div>
            <p className="text-lg font-semibold">
              {campanha.respondidos || 0}
              {taxaResposta > 0 && (
                <span className="ml-1 text-xs text-gray-400">({taxaResposta}%)</span>
              )}
            </p>
          </div>
        </div>

        {/* Datas */}
        <div className="flex items-center justify-between border-t pt-2 text-sm text-gray-500">
          <span>
            Criada{' '}
            {campanha.created_at
              ? formatDistanceToNow(new Date(campanha.created_at), {
                  addSuffix: true,
                  locale: ptBR,
                })
              : '-'}
          </span>

          {campanha.agendar_para && (
            <span>Agendada para {format(new Date(campanha.agendar_para), 'dd/MM/yyyy HH:mm')}</span>
          )}

          {campanha.concluida_em && (
            <span>Concluida em {format(new Date(campanha.concluida_em), 'dd/MM/yyyy HH:mm')}</span>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
