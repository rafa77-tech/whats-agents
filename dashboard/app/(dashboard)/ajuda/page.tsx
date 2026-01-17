'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { useToast } from '@/hooks/use-toast'
import {
  HelpCircle,
  Clock,
  CheckCircle2,
  MessageSquare,
  User,
  Building2,
  Send,
  Loader2,
  RefreshCw,
  Volume2,
  VolumeX,
} from 'lucide-react'
import { formatDistanceToNow, format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

interface PedidoAjuda {
  id: string
  conversa_id: string
  cliente_id: string
  hospital_id?: string
  pergunta_original: string
  contexto?: string
  status: 'pendente' | 'respondido' | 'timeout' | 'cancelado'
  resposta?: string
  respondido_por?: string
  respondido_em?: string
  criado_em: string
  clientes?: { nome: string; telefone: string } | null
  hospitais?: { nome: string } | null
}

const statusConfig = {
  pendente: {
    label: 'Pendente',
    color: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    icon: Clock,
  },
  respondido: {
    label: 'Respondido',
    color: 'bg-green-100 text-green-800 border-green-200',
    icon: CheckCircle2,
  },
  timeout: {
    label: 'Timeout',
    color: 'bg-orange-100 text-orange-800 border-orange-200',
    icon: Clock,
  },
  cancelado: {
    label: 'Cancelado',
    color: 'bg-gray-100 text-gray-800 border-gray-200',
    icon: HelpCircle,
  },
}

export default function CanalAjudaPage() {
  const { toast } = useToast()
  const [pedidos, setPedidos] = useState<PedidoAjuda[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<'pendentes' | 'todos'>('pendentes')
  const [respondendo, setRespondendo] = useState<string | null>(null)
  const [resposta, setResposta] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [soundEnabled, setSoundEnabled] = useState(true)
  const previousCount = useRef(0)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  // Inicializar audio para notificacao sonora
  useEffect(() => {
    audioRef.current = new Audio('/notification.mp3')
  }, [])

  const playNotificationSound = useCallback(() => {
    if (soundEnabled && audioRef.current) {
      audioRef.current.play().catch(() => {
        // Silently fail if audio can't play (user hasn't interacted with page yet)
      })
    }
  }, [soundEnabled])

  const carregarPedidos = useCallback(async () => {
    try {
      const status = tab === 'pendentes' ? 'pendente,timeout' : ''
      const res = await fetch(`/api/ajuda?status=${status}`)
      const data = await res.json()

      // Notificacao sonora para novos pedidos
      if (tab === 'pendentes') {
        const currentCount = Array.isArray(data) ? data.length : 0
        if (currentCount > previousCount.current && previousCount.current > 0) {
          playNotificationSound()
          toast({
            title: 'Novo pedido de ajuda',
            description: 'Um medico precisa de ajuda!',
          })
        }
        previousCount.current = currentCount
      }

      setPedidos(Array.isArray(data) ? data : [])
    } catch (error) {
      console.error('Erro ao carregar:', error)
      setPedidos([])
    } finally {
      setLoading(false)
    }
  }, [tab, playNotificationSound, toast])

  useEffect(() => {
    setLoading(true)
    carregarPedidos()
  }, [carregarPedidos])

  // Auto-refresh a cada 30 segundos para pedidos pendentes
  useEffect(() => {
    if (tab === 'pendentes') {
      const interval = setInterval(carregarPedidos, 30000)
      return () => clearInterval(interval)
    }
    return undefined
  }, [tab, carregarPedidos])

  const handleResponder = async (pedidoId: string) => {
    if (!resposta.trim()) return

    setEnviando(true)

    try {
      const res = await fetch(`/api/ajuda/${pedidoId}/responder`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resposta: resposta.trim() }),
      })

      if (!res.ok) throw new Error('Erro ao responder')

      toast({
        title: 'Resposta enviada',
        description: 'Julia retomara a conversa com o medico.',
      })

      setRespondendo(null)
      setResposta('')
      carregarPedidos()
    } catch {
      toast({
        variant: 'destructive',
        title: 'Erro',
        description: 'Nao foi possivel enviar a resposta.',
      })
    } finally {
      setEnviando(false)
    }
  }

  const pendentesCount = pedidos.filter(
    (p) => p.status === 'pendente' || p.status === 'timeout'
  ).length

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Canal de Ajuda</h1>
          <p className="text-gray-500">Perguntas que Julia nao soube responder</p>
        </div>

        <div className="flex items-center gap-4">
          {/* Toggle de som */}
          <div className="flex items-center gap-2">
            {soundEnabled ? (
              <Volume2 className="h-4 w-4 text-gray-500" />
            ) : (
              <VolumeX className="h-4 w-4 text-gray-400" />
            )}
            <Switch id="sound" checked={soundEnabled} onCheckedChange={setSoundEnabled} />
            <Label htmlFor="sound" className="text-sm text-gray-500">
              Som
            </Label>
          </div>

          <Button variant="outline" onClick={carregarPedidos} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Atualizar
          </Button>
        </div>
      </div>

      {/* Alerta de pendentes */}
      {tab === 'pendentes' && pendentesCount > 0 && (
        <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4">
          <div className="flex items-center gap-2">
            <HelpCircle className="h-5 w-5 text-yellow-600" />
            <span className="font-medium text-yellow-800">
              {pendentesCount} pedido(s) aguardando resposta
            </span>
          </div>
          <p className="mt-1 text-sm text-yellow-700">
            Medicos estao esperando. Responda para Julia continuar a conversa.
          </p>
        </div>
      )}

      <Tabs value={tab} onValueChange={(v) => setTab(v as typeof tab)}>
        <TabsList>
          <TabsTrigger value="pendentes">
            Pendentes
            {pendentesCount > 0 && <Badge className="ml-2 bg-yellow-500">{pendentesCount}</Badge>}
          </TabsTrigger>
          <TabsTrigger value="todos">Todos</TabsTrigger>
        </TabsList>

        <TabsContent value="pendentes" className="mt-4 space-y-4">
          {loading ? (
            <div className="py-8 text-center">
              <Loader2 className="mx-auto h-6 w-6 animate-spin text-gray-400" />
            </div>
          ) : pedidos.length === 0 ? (
            <div className="rounded-lg border bg-white py-12 text-center">
              <CheckCircle2 className="mx-auto mb-4 h-12 w-12 text-green-500" />
              <p className="text-lg font-medium">Tudo em dia!</p>
              <p className="text-gray-500">Nenhum pedido pendente no momento.</p>
            </div>
          ) : (
            pedidos.map((pedido) => (
              <PedidoCard
                key={pedido.id}
                pedido={pedido}
                isExpanded={respondendo === pedido.id}
                onToggle={() => {
                  setRespondendo(respondendo === pedido.id ? null : pedido.id)
                  setResposta('')
                }}
                resposta={resposta}
                onRespostaChange={setResposta}
                onResponder={() => handleResponder(pedido.id)}
                enviando={enviando}
              />
            ))
          )}
        </TabsContent>

        <TabsContent value="todos" className="mt-4 space-y-4">
          {loading ? (
            <div className="py-8 text-center">
              <Loader2 className="mx-auto h-6 w-6 animate-spin text-gray-400" />
            </div>
          ) : pedidos.length === 0 ? (
            <div className="rounded-lg border bg-white py-12 text-center">
              <p className="text-gray-500">Nenhum pedido encontrado.</p>
            </div>
          ) : (
            pedidos.map((pedido) => (
              <PedidoCard
                key={pedido.id}
                pedido={pedido}
                isExpanded={false}
                onToggle={() => {}}
                resposta=""
                onRespostaChange={() => {}}
                onResponder={() => {}}
                enviando={false}
                readOnly
              />
            ))
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}

interface PedidoCardProps {
  pedido: PedidoAjuda
  isExpanded: boolean
  onToggle: () => void
  resposta: string
  onRespostaChange: (value: string) => void
  onResponder: () => void
  enviando: boolean
  readOnly?: boolean
}

function PedidoCard({
  pedido,
  isExpanded,
  onToggle,
  resposta,
  onRespostaChange,
  onResponder,
  enviando,
  readOnly,
}: PedidoCardProps) {
  const status = statusConfig[pedido.status]
  const StatusIcon = status.icon

  const isPending = pedido.status === 'pendente' || pedido.status === 'timeout'

  return (
    <Card className={isPending ? 'border-yellow-200 bg-white' : 'bg-white'}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gray-100">
              <User className="h-5 w-5 text-gray-500" />
            </div>
            <div>
              <CardTitle className="text-lg">{pedido.clientes?.nome ?? 'Medico'}</CardTitle>
              <p className="text-sm text-gray-500">{pedido.clientes?.telefone ?? '-'}</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Badge variant="outline" className={status.color}>
              <StatusIcon className="mr-1 h-3 w-3" />
              {status.label}
            </Badge>
            <span className="text-sm text-gray-400">
              {pedido.criado_em
                ? formatDistanceToNow(new Date(pedido.criado_em), {
                    addSuffix: true,
                    locale: ptBR,
                  })
                : '-'}
            </span>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Hospital */}
        {pedido.hospitais && (
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Building2 className="h-4 w-4" />
            <span>Conversa sobre: {pedido.hospitais.nome}</span>
          </div>
        )}

        {/* Pergunta */}
        <div className="rounded-lg bg-gray-50 p-4">
          <div className="mb-2 flex items-center gap-2 text-sm text-gray-500">
            <MessageSquare className="h-4 w-4" />
            <span>Pergunta do medico:</span>
          </div>
          <p className="font-medium">{pedido.pergunta_original}</p>
        </div>

        {/* Contexto */}
        {pedido.contexto && (
          <div className="text-sm">
            <span className="text-gray-500">Contexto: </span>
            <span>{pedido.contexto}</span>
          </div>
        )}

        {/* Resposta (se ja respondido) */}
        {pedido.resposta && pedido.respondido_em && (
          <div className="rounded-lg bg-green-50 p-4">
            <div className="mb-2 flex items-center gap-2 text-sm text-green-700">
              <CheckCircle2 className="h-4 w-4" />
              <span>Respondido em {format(new Date(pedido.respondido_em), 'dd/MM HH:mm')}</span>
            </div>
            <p>{pedido.resposta}</p>
          </div>
        )}

        {/* Area de resposta (se pendente) */}
        {isPending && !readOnly && (
          <>
            {isExpanded ? (
              <div className="space-y-3">
                <Textarea
                  placeholder="Digite sua resposta para Julia repassar ao medico..."
                  value={resposta}
                  onChange={(e) => onRespostaChange(e.target.value)}
                  rows={3}
                />
                <div className="flex gap-2">
                  <Button onClick={onResponder} disabled={!resposta.trim() || enviando}>
                    {enviando ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Enviando...
                      </>
                    ) : (
                      <>
                        <Send className="mr-2 h-4 w-4" />
                        Enviar Resposta
                      </>
                    )}
                  </Button>
                  <Button variant="outline" onClick={onToggle}>
                    Cancelar
                  </Button>
                </div>
              </div>
            ) : (
              <Button onClick={onToggle}>Responder</Button>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
