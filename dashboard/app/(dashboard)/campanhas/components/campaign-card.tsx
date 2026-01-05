'use client'

import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { useRouter } from 'next/navigation'
import { Clock, CheckCircle, Send, Users } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'

export interface Campaign {
  id: number
  nome: string
  tipo: string
  status: string
  total_destinatarios: number
  enviados: number
  entregues: number
  respondidos: number
  scheduled_at?: string
  created_at: string
}

interface Props {
  campaign: Campaign
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

export function CampaignCard({ campaign }: Props) {
  const router = useRouter()

  const progress =
    campaign.total_destinatarios > 0 ? (campaign.enviados / campaign.total_destinatarios) * 100 : 0

  const statusBadge = STATUS_BADGES[campaign.status] || {
    label: campaign.status,
    className: 'bg-gray-100 text-gray-800',
  }

  return (
    <Card
      className="cursor-pointer transition-colors hover:bg-muted/50"
      onClick={() => router.push(`/campanhas/${campaign.id}`)}
    >
      <CardContent className="p-4">
        <div className="flex flex-col gap-4 md:flex-row md:items-start">
          <div className="flex-1 space-y-3">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-semibold">{campaign.nome}</h3>
                <p className="text-sm text-muted-foreground">
                  {TIPO_LABELS[campaign.tipo] || campaign.tipo}
                </p>
              </div>
              <Badge className={statusBadge.className}>{statusBadge.label}</Badge>
            </div>

            {campaign.status === 'running' && (
              <div className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span>Progresso</span>
                  <span>
                    {campaign.enviados} / {campaign.total_destinatarios}
                  </span>
                </div>
                <Progress value={progress} className="h-2" />
              </div>
            )}

            <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                <Users className="h-4 w-4" />
                {campaign.total_destinatarios} destinatarios
              </span>
              {campaign.scheduled_at && (
                <span className="flex items-center gap-1">
                  <Clock className="h-4 w-4" />
                  {format(new Date(campaign.scheduled_at), "dd/MM 'as' HH:mm", { locale: ptBR })}
                </span>
              )}
              {campaign.status === 'completed' && (
                <>
                  <span className="flex items-center gap-1">
                    <CheckCircle className="h-4 w-4" />
                    {campaign.entregues} entregues
                  </span>
                  <span className="flex items-center gap-1">
                    <Send className="h-4 w-4" />
                    {campaign.respondidos} responderam
                  </span>
                </>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
