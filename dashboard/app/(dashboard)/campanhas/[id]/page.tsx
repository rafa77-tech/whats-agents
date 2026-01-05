'use client'

import { useCallback, useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { ArrowLeft, Play, Pause, Users, Send, CheckCircle, MessageCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuth } from '@/hooks/use-auth'

interface CampaignDetail {
  id: number
  nome: string
  tipo: string
  mensagem: string
  status: string
  total_destinatarios: number
  enviados: number
  entregues: number
  respondidos: number
  scheduled_at?: string
  started_at?: string
  completed_at?: string
  created_at: string
  created_by?: string
}

const STATUS_BADGES: Record<string, { label: string; className: string }> = {
  draft: { label: 'Rascunho', className: 'bg-gray-100 text-gray-800' },
  scheduled: { label: 'Agendada', className: 'bg-blue-100 text-blue-800' },
  running: { label: 'Em execucao', className: 'bg-yellow-100 text-yellow-800' },
  completed: { label: 'Concluida', className: 'bg-green-100 text-green-800' },
  paused: { label: 'Pausada', className: 'bg-orange-100 text-orange-800' },
}

const TIPO_LABELS: Record<string, string> = {
  discovery: 'Discovery',
  oferta: 'Oferta de Vaga',
  reativacao: 'Reativacao',
  followup: 'Follow-up',
  custom: 'Personalizada',
}

export default function CampaignDetailPage() {
  const params = useParams()
  const id = params.id as string
  const router = useRouter()
  const { session } = useAuth()
  const [campaign, setCampaign] = useState<CampaignDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchCampaign = useCallback(async () => {
    if (!session?.access_token) return

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/dashboard/campaigns/${id}`, {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      })

      if (response.ok) {
        const data = await response.json()
        setCampaign(data)
      } else if (response.status === 404) {
        setError('Campanha nao encontrada')
      } else {
        setError('Erro ao carregar campanha')
      }
    } catch (err) {
      console.error('Failed to fetch campaign:', err)
      setError('Erro ao carregar campanha')
    } finally {
      setLoading(false)
    }
  }, [id, session?.access_token])

  useEffect(() => {
    fetchCampaign()
  }, [fetchCampaign])

  const handleStart = async () => {
    if (!session?.access_token) return

    setActionLoading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/dashboard/campaigns/${id}/start`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      })

      if (response.ok) {
        fetchCampaign()
      } else {
        const data = await response.json()
        alert(data.detail || 'Erro ao iniciar campanha')
      }
    } catch (err) {
      console.error('Failed to start campaign:', err)
      alert('Erro ao iniciar campanha')
    } finally {
      setActionLoading(false)
    }
  }

  const handlePause = async () => {
    if (!session?.access_token) return

    setActionLoading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/dashboard/campaigns/${id}/pause`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      })

      if (response.ok) {
        fetchCampaign()
      } else {
        const data = await response.json()
        alert(data.detail || 'Erro ao pausar campanha')
      }
    } catch (err) {
      console.error('Failed to pause campaign:', err)
      alert('Erro ao pausar campanha')
    } finally {
      setActionLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex h-full flex-col">
        <div className="border-b p-4 md:p-6">
          <Skeleton className="mb-2 h-8 w-48" />
          <Skeleton className="h-4 w-32" />
        </div>
        <div className="flex-1 space-y-4 p-4 md:p-6">
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
        </div>
      </div>
    )
  }

  if (error || !campaign) {
    return (
      <div className="flex h-full flex-col items-center justify-center">
        <p className="mb-4 text-muted-foreground">{error || 'Campanha nao encontrada'}</p>
        <Button variant="outline" onClick={() => router.push('/campanhas')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Voltar
        </Button>
      </div>
    )
  }

  const progress =
    campaign.total_destinatarios > 0 ? (campaign.enviados / campaign.total_destinatarios) * 100 : 0

  const statusBadge = STATUS_BADGES[campaign.status] || {
    label: campaign.status,
    className: 'bg-gray-100 text-gray-800',
  }

  const canStart = ['draft', 'scheduled', 'paused'].includes(campaign.status)
  const canPause = campaign.status === 'running'

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b p-4 md:p-6">
        <div className="mb-4 flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.push('/campanhas')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="flex-1">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">{campaign.nome}</h1>
              <Badge className={statusBadge.className}>{statusBadge.label}</Badge>
            </div>
            <p className="text-muted-foreground">{TIPO_LABELS[campaign.tipo] || campaign.tipo}</p>
          </div>
          <div className="flex gap-2">
            {canStart && (
              <Button onClick={handleStart} disabled={actionLoading}>
                <Play className="mr-2 h-4 w-4" />
                Iniciar
              </Button>
            )}
            {canPause && (
              <Button variant="outline" onClick={handlePause} disabled={actionLoading}>
                <Pause className="mr-2 h-4 w-4" />
                Pausar
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4 md:p-6">
        <div className="grid gap-6 md:grid-cols-2">
          {/* Progress Card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Progresso</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Enviados</span>
                  <span>
                    {campaign.enviados} / {campaign.total_destinatarios}
                  </span>
                </div>
                <Progress value={progress} className="h-3" />
              </div>

              <div className="grid grid-cols-2 gap-4 pt-4">
                <div className="flex items-center gap-3">
                  <Users className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-2xl font-bold">{campaign.total_destinatarios}</p>
                    <p className="text-sm text-muted-foreground">Destinatarios</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Send className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-2xl font-bold">{campaign.enviados}</p>
                    <p className="text-sm text-muted-foreground">Enviados</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <CheckCircle className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-2xl font-bold">{campaign.entregues}</p>
                    <p className="text-sm text-muted-foreground">Entregues</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <MessageCircle className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-2xl font-bold">{campaign.respondidos}</p>
                    <p className="text-sm text-muted-foreground">Responderam</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Message Card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Mensagem</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="whitespace-pre-wrap rounded-lg bg-muted p-4 text-sm">
                {campaign.mensagem || 'Sem mensagem definida'}
              </div>
            </CardContent>
          </Card>

          {/* Metadata Card */}
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle className="text-lg">Informacoes</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-4">
                <div>
                  <p className="text-sm text-muted-foreground">Criado em</p>
                  <p className="text-sm">
                    {format(new Date(campaign.created_at), "dd/MM/yyyy 'as' HH:mm", {
                      locale: ptBR,
                    })}
                  </p>
                </div>
                {campaign.created_by && (
                  <div>
                    <p className="text-sm text-muted-foreground">Criado por</p>
                    <p className="text-sm">{campaign.created_by}</p>
                  </div>
                )}
                {campaign.scheduled_at && (
                  <div>
                    <p className="text-sm text-muted-foreground">Agendado para</p>
                    <p className="text-sm">
                      {format(new Date(campaign.scheduled_at), "dd/MM/yyyy 'as' HH:mm", {
                        locale: ptBR,
                      })}
                    </p>
                  </div>
                )}
                {campaign.started_at && (
                  <div>
                    <p className="text-sm text-muted-foreground">Iniciado em</p>
                    <p className="text-sm">
                      {format(new Date(campaign.started_at), "dd/MM/yyyy 'as' HH:mm", {
                        locale: ptBR,
                      })}
                    </p>
                  </div>
                )}
                {campaign.completed_at && (
                  <div>
                    <p className="text-sm text-muted-foreground">Concluido em</p>
                    <p className="text-sm">
                      {format(new Date(campaign.completed_at), "dd/MM/yyyy 'as' HH:mm", {
                        locale: ptBR,
                      })}
                    </p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
