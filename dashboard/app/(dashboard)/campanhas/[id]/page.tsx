'use client'

import { useState, useEffect, useCallback } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useToast } from '@/hooks/use-toast'
import {
  ArrowLeft,
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
  Eye,
  XCircle,
  AlertTriangle,
  Phone,
  User,
  Stethoscope,
  Calendar,
  StopCircle,
  MapPin,
  Sparkles,
  X,
  UserPlus,
  Search,
} from 'lucide-react'
import { formatDistanceToNow, format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

interface Cliente {
  id: string
  primeiro_nome: string
  sobrenome?: string
  telefone: string
  especialidade?: string
}

interface Envio {
  id: number
  cliente_id: string
  status: string
  conteudo_enviado: string
  created_at: string
  enviado_em?: string
  entregue_em?: string
  visualizado_em?: string
  falhou_em?: string
  clientes: Cliente | null
}

interface Metricas {
  total: number
  enviados: number
  entregues: number
  visualizados: number
  falhas: number
  taxa_entrega: number
  taxa_visualizacao: number
}

interface Campanha {
  id: number
  nome_template: string
  tipo_campanha: string
  categoria: string
  status: 'rascunho' | 'agendada' | 'em_execucao' | 'concluida' | 'pausada' | 'cancelada'
  objetivo?: string
  corpo: string
  tom?: string
  agendar_para?: string
  iniciada_em?: string
  concluida_em?: string
  created_at: string
  created_by?: string
  audience_filters?: Record<string, unknown>
  envios: Envio[]
  metricas: Metricas
}

interface AudienciaCliente {
  id: string
  primeiro_nome: string
  sobrenome?: string
  telefone: string
  especialidade?: string
  cidade?: string
  estado?: string
}

interface ExemploMensagem {
  destinatario: string
  mensagem: string
}

interface Audiencia {
  total: number
  filters: Record<string, unknown>
  clientes: AudienciaCliente[]
  exemplos_mensagens: ExemploMensagem[]
  variacoes_possiveis: number
  modo: 'manual' | 'filtros'
}

interface ClienteBusca extends AudienciaCliente {
  na_campanha: boolean
}

const statusConfig = {
  rascunho: {
    label: 'Rascunho',
    color: 'bg-gray-100 text-gray-800 border-gray-200',
    icon: FileEdit,
  },
  agendada: {
    label: 'Agendada',
    color: 'bg-blue-100 text-blue-800 border-blue-200',
    icon: Clock,
  },
  em_execucao: {
    label: 'Em Execucao',
    color: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    icon: Play,
  },
  concluida: {
    label: 'Concluida',
    color: 'bg-green-100 text-green-800 border-green-200',
    icon: CheckCircle2,
  },
  pausada: {
    label: 'Pausada',
    color: 'bg-orange-100 text-orange-800 border-orange-200',
    icon: Pause,
  },
  cancelada: {
    label: 'Cancelada',
    color: 'bg-red-100 text-red-800 border-red-200',
    icon: XCircle,
  },
}

const envioStatusConfig: Record<string, { label: string; color: string; icon: typeof CheckCircle2 }> = {
  pendente: { label: 'Pendente', color: 'text-gray-500', icon: Clock },
  enviado: { label: 'Enviado', color: 'text-blue-500', icon: Send },
  entregue: { label: 'Entregue', color: 'text-green-500', icon: CheckCircle2 },
  visualizado: { label: 'Visualizado', color: 'text-purple-500', icon: Eye },
  falhou: { label: 'Falhou', color: 'text-red-500', icon: XCircle },
}

const tipoCampanhaLabels: Record<string, string> = {
  oferta_plantao: 'Oferta de Plantao',
  reativacao: 'Reativacao',
  followup: 'Follow-up',
  descoberta: 'Descoberta',
}

export default function CampanhaDetalhesPage() {
  const params = useParams()
  const { toast } = useToast()
  const [campanha, setCampanha] = useState<Campanha | null>(null)
  const [audiencia, setAudiencia] = useState<Audiencia | null>(null)
  const [loading, setLoading] = useState(true)
  const [audienciaLoading, setAudienciaLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean
    action: string
    title: string
    description: string
  }>({ open: false, action: '', title: '', description: '' })

  // Estado para gerenciar audiencia
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<ClienteBusca[]>([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [audienciaActionLoading, setAudienciaActionLoading] = useState<string | null>(null)
  const [selectedClientes, setSelectedClientes] = useState<Set<string>>(new Set())
  const [bulkActionLoading, setBulkActionLoading] = useState(false)

  const carregarCampanha = useCallback(async () => {
    try {
      setError(null)
      const res = await fetch(`/api/campanhas/${params.id}`)
      const data = await res.json()

      if (!res.ok) {
        setError(data.detail || 'Erro ao carregar campanha')
        return
      }

      setCampanha(data)
    } catch (err) {
      console.error('Erro ao carregar campanha:', err)
      setError('Erro de conexao com o servidor')
    } finally {
      setLoading(false)
    }
  }, [params.id])

  const carregarAudiencia = useCallback(async () => {
    try {
      setAudienciaLoading(true)
      const res = await fetch(`/api/campanhas/${params.id}/audiencia`)
      const data = await res.json()

      if (!res.ok) {
        console.error('Erro ao carregar audiencia:', data.detail)
        return
      }

      setAudiencia(data)
    } catch (err) {
      console.error('Erro ao carregar audiencia:', err)
    } finally {
      setAudienciaLoading(false)
    }
  }, [params.id])

  useEffect(() => {
    carregarCampanha()
  }, [carregarCampanha])

  useEffect(() => {
    if (campanha) {
      carregarAudiencia()
    }
  }, [campanha, carregarAudiencia])

  // Funcoes para gerenciar audiencia
  const removerMedico = async (clienteId: string) => {
    setAudienciaActionLoading(clienteId)
    try {
      const res = await fetch(`/api/campanhas/${params.id}/audiencia`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'remove', cliente_ids: [clienteId] }),
      })

      if (!res.ok) {
        const data = await res.json()
        toast({
          title: 'Erro',
          description: data.detail || 'Erro ao remover medico',
          variant: 'destructive',
        })
        return
      }

      toast({ title: 'Medico removido da campanha' })
      carregarAudiencia()
    } catch (err) {
      console.error('Erro ao remover medico:', err)
      toast({
        title: 'Erro',
        description: 'Erro de conexao',
        variant: 'destructive',
      })
    } finally {
      setAudienciaActionLoading(null)
    }
  }

  const buscarMedicos = async (query: string) => {
    if (query.length < 2) {
      setSearchResults([])
      return
    }

    setSearchLoading(true)
    try {
      const res = await fetch(`/api/campanhas/${params.id}/audiencia`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      })

      const data = await res.json()

      if (!res.ok) {
        console.error('Erro ao buscar medicos:', data.detail)
        return
      }

      setSearchResults(data.clientes || [])
    } catch (err) {
      console.error('Erro ao buscar medicos:', err)
    } finally {
      setSearchLoading(false)
    }
  }

  const adicionarMedico = async (clienteId: string) => {
    setAudienciaActionLoading(clienteId)
    try {
      const res = await fetch(`/api/campanhas/${params.id}/audiencia`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'add', cliente_ids: [clienteId] }),
      })

      if (!res.ok) {
        const data = await res.json()
        toast({
          title: 'Erro',
          description: data.detail || 'Erro ao adicionar medico',
          variant: 'destructive',
        })
        return
      }

      toast({ title: 'Medico adicionado a campanha' })

      // Atualizar resultados da busca
      setSearchResults((prev) =>
        prev.map((c) => (c.id === clienteId ? { ...c, na_campanha: true } : c))
      )
      carregarAudiencia()
    } catch (err) {
      console.error('Erro ao adicionar medico:', err)
      toast({
        title: 'Erro',
        description: 'Erro de conexao',
        variant: 'destructive',
      })
    } finally {
      setAudienciaActionLoading(null)
    }
  }

  // Funcoes para selecao em massa
  const toggleSelectCliente = (clienteId: string) => {
    setSelectedClientes((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(clienteId)) {
        newSet.delete(clienteId)
      } else {
        newSet.add(clienteId)
      }
      return newSet
    })
  }

  const toggleSelectAll = () => {
    if (!audiencia) return

    if (selectedClientes.size === audiencia.clientes.length) {
      // Desselecionar todos
      setSelectedClientes(new Set())
    } else {
      // Selecionar todos
      setSelectedClientes(new Set(audiencia.clientes.map((c) => c.id)))
    }
  }

  const removerSelecionados = async () => {
    if (selectedClientes.size === 0) return

    setBulkActionLoading(true)
    try {
      const res = await fetch(`/api/campanhas/${params.id}/audiencia`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'remove',
          cliente_ids: Array.from(selectedClientes),
        }),
      })

      if (!res.ok) {
        const data = await res.json()
        toast({
          title: 'Erro',
          description: data.detail || 'Erro ao remover medicos',
          variant: 'destructive',
        })
        return
      }

      toast({
        title: 'Sucesso',
        description: `${selectedClientes.size} medico(s) removido(s) da campanha`,
      })
      setSelectedClientes(new Set())
      carregarAudiencia()
    } catch (err) {
      console.error('Erro ao remover medicos:', err)
      toast({
        title: 'Erro',
        description: 'Erro de conexao',
        variant: 'destructive',
      })
    } finally {
      setBulkActionLoading(false)
    }
  }

  // Limpar selecao quando audiencia mudar
  useEffect(() => {
    setSelectedClientes(new Set())
  }, [audiencia])

  // Debounce para busca
  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchQuery) {
        buscarMedicos(searchQuery)
      }
    }, 300)

    return () => clearTimeout(timer)
  }, [searchQuery])

  const executarAcao = async (action: string) => {
    setActionLoading(true)
    try {
      const res = await fetch(`/api/campanhas/${params.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      })

      const data = await res.json()

      if (!res.ok) {
        toast({
          title: 'Erro',
          description: data.detail || 'Erro ao executar acao',
          variant: 'destructive',
        })
        return
      }

      toast({
        title: 'Sucesso',
        description: `Campanha ${action === 'iniciar' ? 'iniciada' : action === 'pausar' ? 'pausada' : action === 'retomar' ? 'retomada' : action === 'cancelar' ? 'cancelada' : 'atualizada'} com sucesso`,
      })

      carregarCampanha()
    } catch (err) {
      console.error('Erro ao executar acao:', err)
      toast({
        title: 'Erro',
        description: 'Erro de conexao com o servidor',
        variant: 'destructive',
      })
    } finally {
      setActionLoading(false)
      setConfirmDialog({ open: false, action: '', title: '', description: '' })
    }
  }

  const abrirConfirmacao = (action: string, title: string, description: string) => {
    setConfirmDialog({ open: true, action, title, description })
  }

  if (loading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (error || !campanha) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link href="/campanhas">
              <ArrowLeft className="h-5 w-5" />
            </Link>
          </Button>
          <h1 className="text-2xl font-bold text-gray-900">Campanha nao encontrada</h1>
        </div>
        <Card>
          <CardContent className="py-12 text-center">
            <AlertTriangle className="mx-auto mb-4 h-12 w-12 text-yellow-500" />
            <p className="text-lg font-medium">{error || 'Campanha nao encontrada'}</p>
            <Button className="mt-4" asChild>
              <Link href="/campanhas">Voltar para Campanhas</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const status = statusConfig[campanha.status] || statusConfig.rascunho
  const StatusIcon = status.icon

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link href="/campanhas">
              <ArrowLeft className="h-5 w-5" />
            </Link>
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900">{campanha.nome_template}</h1>
              <Badge variant="outline" className={status.color}>
                <StatusIcon className="mr-1 h-3 w-3" />
                {status.label}
              </Badge>
            </div>
            <p className="text-gray-500">
              {tipoCampanhaLabels[campanha.tipo_campanha] || campanha.tipo_campanha}
              {campanha.categoria && ` - ${campanha.categoria}`}
            </p>
            {campanha.agendar_para && (
              <p className="mt-1 flex items-center gap-1 text-sm text-blue-600">
                <Calendar className="h-4 w-4" />
                Agendada para{' '}
                {format(new Date(campanha.agendar_para), "EEEE, d 'de' MMMM 'às' HH:mm", { locale: ptBR })}
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={carregarCampanha} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Atualizar
          </Button>

          {/* Botao de editar (rascunho ou agendada) */}
          {['rascunho', 'agendada'].includes(campanha.status) && (
            <Button variant="outline" asChild>
              <Link href={`/campanhas/${campanha.id}/editar`}>
                <FileEdit className="mr-2 h-4 w-4" />
                Editar
              </Link>
            </Button>
          )}

          {/* Acoes baseadas no status */}
          {campanha.status === 'rascunho' && (
            <Button
              onClick={() =>
                abrirConfirmacao(
                  'iniciar',
                  'Iniciar Campanha',
                  'Tem certeza que deseja iniciar esta campanha? Os envios comecaram imediatamente.'
                )
              }
              disabled={actionLoading}
            >
              {actionLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
              Iniciar
            </Button>
          )}

          {campanha.status === 'agendada' && (
            <>
              <Button
                variant="outline"
                onClick={() =>
                  abrirConfirmacao(
                    'cancelar',
                    'Cancelar Campanha',
                    'Tem certeza que deseja cancelar esta campanha agendada?'
                  )
                }
                disabled={actionLoading}
              >
                <XCircle className="mr-2 h-4 w-4" />
                Cancelar
              </Button>
              <Button
                onClick={() =>
                  abrirConfirmacao(
                    'iniciar',
                    'Iniciar Agora',
                    'Tem certeza que deseja iniciar esta campanha agora, ignorando o agendamento?'
                  )
                }
                disabled={actionLoading}
              >
                <Play className="mr-2 h-4 w-4" />
                Iniciar Agora
              </Button>
            </>
          )}

          {campanha.status === 'em_execucao' && (
            <>
              <Button
                variant="outline"
                onClick={() =>
                  abrirConfirmacao('pausar', 'Pausar Campanha', 'Tem certeza que deseja pausar esta campanha?')
                }
                disabled={actionLoading}
              >
                <Pause className="mr-2 h-4 w-4" />
                Pausar
              </Button>
              <Button
                variant="destructive"
                onClick={() =>
                  abrirConfirmacao(
                    'cancelar',
                    'Cancelar Campanha',
                    'Tem certeza que deseja cancelar esta campanha? Esta acao nao pode ser desfeita.'
                  )
                }
                disabled={actionLoading}
              >
                <StopCircle className="mr-2 h-4 w-4" />
                Cancelar
              </Button>
            </>
          )}

          {campanha.status === 'pausada' && (
            <>
              <Button
                variant="outline"
                onClick={() =>
                  abrirConfirmacao(
                    'cancelar',
                    'Cancelar Campanha',
                    'Tem certeza que deseja cancelar esta campanha? Esta acao nao pode ser desfeita.'
                  )
                }
                disabled={actionLoading}
              >
                <XCircle className="mr-2 h-4 w-4" />
                Cancelar
              </Button>
              <Button
                onClick={() =>
                  abrirConfirmacao('retomar', 'Retomar Campanha', 'Tem certeza que deseja retomar esta campanha?')
                }
                disabled={actionLoading}
              >
                <Play className="mr-2 h-4 w-4" />
                Retomar
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Metricas */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Destinatarios</p>
                <p className="text-2xl font-bold">{audiencia?.total || campanha.metricas.total}</p>
              </div>
              <Users className="h-8 w-8 text-gray-400" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Enviados</p>
                <p className="text-2xl font-bold">{campanha.metricas.enviados}</p>
              </div>
              <Send className="h-8 w-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Entregues</p>
                <p className="text-2xl font-bold">
                  {campanha.metricas.entregues}
                  {campanha.metricas.taxa_entrega > 0 && (
                    <span className="ml-1 text-sm font-normal text-gray-400">
                      ({campanha.metricas.taxa_entrega}%)
                    </span>
                  )}
                </p>
              </div>
              <CheckCircle2 className="h-8 w-8 text-green-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Visualizados</p>
                <p className="text-2xl font-bold">
                  {campanha.metricas.visualizados}
                  {campanha.metricas.taxa_visualizacao > 0 && (
                    <span className="ml-1 text-sm font-normal text-gray-400">
                      ({campanha.metricas.taxa_visualizacao}%)
                    </span>
                  )}
                </p>
              </div>
              <Eye className="h-8 w-8 text-purple-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Falhas</p>
                <p className="text-2xl font-bold text-red-600">{campanha.metricas.falhas}</p>
              </div>
              <XCircle className="h-8 w-8 text-red-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Detalhes e Mensagem */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Detalhes da Campanha</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {campanha.objetivo && (
              <div>
                <p className="text-sm font-medium text-gray-500">Objetivo</p>
                <p>{campanha.objetivo}</p>
              </div>
            )}

            <div>
              <p className="text-sm font-medium text-gray-500">Tom</p>
              <p className="capitalize">{campanha.tom || 'Amigavel'}</p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium text-gray-500">Criada em</p>
                <p className="flex items-center gap-1">
                  <Calendar className="h-4 w-4" />
                  {format(new Date(campanha.created_at), "dd/MM/yyyy 'as' HH:mm", { locale: ptBR })}
                </p>
              </div>

              {campanha.created_by && (
                <div>
                  <p className="text-sm font-medium text-gray-500">Criada por</p>
                  <p>{campanha.created_by}</p>
                </div>
              )}
            </div>

            {campanha.agendar_para && (
              <div>
                <p className="text-sm font-medium text-gray-500">Agendada para</p>
                <p className="flex items-center gap-1">
                  <Clock className="h-4 w-4" />
                  {format(new Date(campanha.agendar_para), "dd/MM/yyyy 'as' HH:mm", { locale: ptBR })}
                </p>
              </div>
            )}

            {campanha.iniciada_em && (
              <div>
                <p className="text-sm font-medium text-gray-500">Iniciada em</p>
                <p className="flex items-center gap-1">
                  <Play className="h-4 w-4" />
                  {format(new Date(campanha.iniciada_em), "dd/MM/yyyy 'as' HH:mm", { locale: ptBR })}
                </p>
              </div>
            )}

            {campanha.concluida_em && (
              <div>
                <p className="text-sm font-medium text-gray-500">Finalizada em</p>
                <p className="flex items-center gap-1">
                  <CheckCircle2 className="h-4 w-4" />
                  {format(new Date(campanha.concluida_em), "dd/MM/yyyy 'as' HH:mm", { locale: ptBR })}
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Exemplos de Mensagens de Abertura */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-yellow-500" />
              Mensagens de Abertura
            </CardTitle>
            <CardDescription>
              Julia gera mensagens unicas para cada medico
              {audiencia && (
                <span className="ml-1 text-xs">
                  ({audiencia.variacoes_possiveis.toLocaleString()} variacoes possiveis)
                </span>
              )}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {audienciaLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
              </div>
            ) : audiencia?.exemplos_mensagens && audiencia.exemplos_mensagens.length > 0 ? (
              <div className="space-y-4">
                {audiencia.exemplos_mensagens.map((exemplo, index) => (
                  <div key={index} className="rounded-lg border bg-gray-50 p-3">
                    <p className="mb-2 text-xs font-medium text-gray-500">
                      Para: {exemplo.destinatario}
                    </p>
                    <pre className="whitespace-pre-wrap font-sans text-sm">{exemplo.mensagem}</pre>
                  </div>
                ))}
                <p className="text-center text-xs text-gray-400">
                  Cada medico recebe uma variacao unica
                </p>
              </div>
            ) : (
              <div className="rounded-lg bg-gray-50 p-4">
                <pre className="whitespace-pre-wrap font-sans text-sm">{campanha.corpo}</pre>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Publico e Envios */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            Publico da Campanha
          </CardTitle>
          <CardDescription>
            {audiencia
              ? `${audiencia.total} medicos selecionados`
              : 'Carregando audiencia...'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="publico">
            <TabsList className="mb-4">
              <TabsTrigger value="publico">
                <Users className="mr-2 h-4 w-4" />
                Medicos Selecionados ({audiencia?.total || 0})
              </TabsTrigger>
              <TabsTrigger value="envios">
                <Send className="mr-2 h-4 w-4" />
                Status dos Envios ({campanha.envios.length})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="publico">
              {/* Barra de acoes (adicionar + acoes em massa) */}
              {campanha.status === 'rascunho' && (
                <div className="mb-4 flex items-center justify-between">
                  {/* Acoes em massa (aparece quando tem selecao) */}
                  {selectedClientes.size > 0 ? (
                    <div className="flex items-center gap-3">
                      <span className="text-sm text-gray-600">
                        {selectedClientes.size} selecionado(s)
                      </span>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={removerSelecionados}
                        disabled={bulkActionLoading}
                      >
                        {bulkActionLoading ? (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                          <X className="mr-2 h-4 w-4" />
                        )}
                        Remover Selecionados
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedClientes(new Set())}
                      >
                        Limpar Selecao
                      </Button>
                    </div>
                  ) : (
                    <div />
                  )}

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setAddDialogOpen(true)
                      setSearchQuery('')
                      setSearchResults([])
                    }}
                  >
                    <UserPlus className="mr-2 h-4 w-4" />
                    Adicionar Medico
                  </Button>
                </div>
              )}

              {audienciaLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                </div>
              ) : audiencia && audiencia.clientes.length > 0 ? (
                <div className="max-h-[400px] overflow-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        {campanha.status === 'rascunho' && (
                          <TableHead className="w-[50px]">
                            <Checkbox
                              checked={
                                audiencia.clientes.length > 0 &&
                                selectedClientes.size === audiencia.clientes.length
                              }
                              onCheckedChange={toggleSelectAll}
                              aria-label="Selecionar todos"
                            />
                          </TableHead>
                        )}
                        <TableHead>Nome</TableHead>
                        <TableHead>Telefone</TableHead>
                        <TableHead>Especialidade</TableHead>
                        <TableHead>Localizacao</TableHead>
                        {campanha.status === 'rascunho' && <TableHead className="w-[80px]">Acoes</TableHead>}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {audiencia.clientes.map((cliente) => (
                        <TableRow
                          key={cliente.id}
                          className={selectedClientes.has(cliente.id) ? 'bg-blue-50' : ''}
                        >
                          {campanha.status === 'rascunho' && (
                            <TableCell>
                              <Checkbox
                                checked={selectedClientes.has(cliente.id)}
                                onCheckedChange={() => toggleSelectCliente(cliente.id)}
                                aria-label={`Selecionar ${cliente.primeiro_nome}`}
                              />
                            </TableCell>
                          )}
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <User className="h-4 w-4 text-gray-400" />
                              {cliente.primeiro_nome} {cliente.sobrenome || ''}
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Phone className="h-4 w-4 text-gray-400" />
                              {cliente.telefone}
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Stethoscope className="h-4 w-4 text-gray-400" />
                              {cliente.especialidade || '-'}
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <MapPin className="h-4 w-4 text-gray-400" />
                              {cliente.cidade && cliente.estado
                                ? `${cliente.cidade}/${cliente.estado}`
                                : cliente.estado || '-'}
                            </div>
                          </TableCell>
                          {campanha.status === 'rascunho' && (
                            <TableCell>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 text-red-500 hover:bg-red-50 hover:text-red-600"
                                onClick={() => removerMedico(cliente.id)}
                                disabled={audienciaActionLoading === cliente.id}
                              >
                                {audienciaActionLoading === cliente.id ? (
                                  <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                  <X className="h-4 w-4" />
                                )}
                              </Button>
                            </TableCell>
                          )}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ) : (
                <div className="py-8 text-center">
                  <Users className="mx-auto mb-4 h-12 w-12 text-gray-300" />
                  <p className="text-gray-500">Nenhum medico encontrado com os filtros selecionados</p>
                  {campanha.status === 'rascunho' && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-4"
                      onClick={() => {
                        setAddDialogOpen(true)
                        setSearchQuery('')
                        setSearchResults([])
                      }}
                    >
                      <UserPlus className="mr-2 h-4 w-4" />
                      Adicionar Medico
                    </Button>
                  )}
                </div>
              )}
            </TabsContent>

            <TabsContent value="envios">
              {campanha.envios.length === 0 ? (
                <div className="py-8 text-center">
                  <MessageSquare className="mx-auto mb-4 h-12 w-12 text-gray-300" />
                  <p className="text-gray-500">Nenhum envio registrado ainda</p>
                  {campanha.status === 'rascunho' && (
                    <p className="mt-1 text-sm text-gray-400">
                      Os envios serao criados quando a campanha for iniciada
                    </p>
                  )}
                </div>
              ) : (
                <div className="max-h-[400px] overflow-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Destinatario</TableHead>
                        <TableHead>Telefone</TableHead>
                        <TableHead>Especialidade</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Data</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {campanha.envios.map((envio) => {
                        const defaultStatus = { label: 'Pendente', color: 'text-gray-500', icon: Clock }
                        const envioStatus = envioStatusConfig[envio.status] ?? defaultStatus
                        const EnvioStatusIcon = envioStatus.icon

                        return (
                          <TableRow key={envio.id}>
                            <TableCell>
                              <div className="flex items-center gap-2">
                                <User className="h-4 w-4 text-gray-400" />
                                {envio.clientes
                                  ? `${envio.clientes.primeiro_nome} ${envio.clientes.sobrenome || ''}`.trim()
                                  : 'Nome nao disponivel'}
                              </div>
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-2">
                                <Phone className="h-4 w-4 text-gray-400" />
                                {envio.clientes?.telefone || '-'}
                              </div>
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-2">
                                <Stethoscope className="h-4 w-4 text-gray-400" />
                                {envio.clientes?.especialidade || '-'}
                              </div>
                            </TableCell>
                            <TableCell>
                              <div className={`flex items-center gap-1 ${envioStatus.color}`}>
                                <EnvioStatusIcon className="h-4 w-4" />
                                {envioStatus.label}
                              </div>
                            </TableCell>
                            <TableCell className="text-gray-500">
                              {envio.enviado_em
                                ? formatDistanceToNow(new Date(envio.enviado_em), {
                                    addSuffix: true,
                                    locale: ptBR,
                                  })
                                : format(new Date(envio.created_at), 'dd/MM HH:mm')}
                            </TableCell>
                          </TableRow>
                        )
                      })}
                    </TableBody>
                  </Table>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Dialog de confirmacao */}
      <AlertDialog
        open={confirmDialog.open}
        onOpenChange={(open) => setConfirmDialog({ ...confirmDialog, open })}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{confirmDialog.title}</AlertDialogTitle>
            <AlertDialogDescription>{confirmDialog.description}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={actionLoading}>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={() => executarAcao(confirmDialog.action)} disabled={actionLoading}>
              {actionLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Confirmar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Dialog para adicionar medicos */}
      <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <UserPlus className="h-5 w-5" />
              Adicionar Medico a Campanha
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <Input
                placeholder="Buscar por nome ou telefone..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>

            {searchLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
              </div>
            ) : searchResults.length > 0 ? (
              <div className="max-h-[300px] overflow-auto rounded-lg border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Nome</TableHead>
                      <TableHead>Telefone</TableHead>
                      <TableHead>Especialidade</TableHead>
                      <TableHead className="w-[100px]">Acao</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {searchResults.map((cliente) => (
                      <TableRow key={cliente.id}>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <User className="h-4 w-4 text-gray-400" />
                            {cliente.primeiro_nome} {cliente.sobrenome || ''}
                          </div>
                        </TableCell>
                        <TableCell>{cliente.telefone}</TableCell>
                        <TableCell>{cliente.especialidade || '-'}</TableCell>
                        <TableCell>
                          {cliente.na_campanha ? (
                            <span className="text-sm text-green-600">Na campanha</span>
                          ) : (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => adicionarMedico(cliente.id)}
                              disabled={audienciaActionLoading === cliente.id}
                            >
                              {audienciaActionLoading === cliente.id ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                'Adicionar'
                              )}
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : searchQuery.length >= 2 ? (
              <div className="py-8 text-center">
                <Users className="mx-auto mb-4 h-12 w-12 text-gray-300" />
                <p className="text-gray-500">Nenhum medico encontrado</p>
              </div>
            ) : (
              <div className="py-8 text-center">
                <Search className="mx-auto mb-4 h-12 w-12 text-gray-300" />
                <p className="text-gray-500">Digite pelo menos 2 caracteres para buscar</p>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
