'use client'

import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Send,
  Calendar,
  User,
  Star,
  ChevronRight,
  Users,
} from 'lucide-react'
import { MedicoDestaque, proximoPassoLabels } from '@/lib/api/extraction'

interface ActionableContactsProps {
  medicos: MedicoDestaque[]
  loading?: boolean
}

export function ActionableContacts({ medicos, loading }: ActionableContactsProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            Medicos para Acao
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </CardContent>
      </Card>
    )
  }

  // Separar por tipo de ação
  const prontosVagas = medicos.filter((m) => m.proximo_passo === 'enviar_vagas')
  const paraFollowup = medicos.filter((m) => m.proximo_passo === 'agendar_followup')

  if (medicos.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            Medicos para Acao
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="py-8 text-center">
            <Users className="mx-auto mb-4 h-12 w-12 text-gray-300" />
            <p className="text-gray-500">
              Nenhum medico com acao pendente.
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Users className="h-5 w-5" />
          Medicos para Acao
        </CardTitle>
        <CardDescription>
          {medicos.length} medico(s) identificado(s) para acao
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Prontos para Vagas */}
        {prontosVagas.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Send className="h-4 w-4 text-status-success-solid" />
              <h4 className="font-semibold">Prontos para Vagas ({prontosVagas.length})</h4>
            </div>
            <div className="space-y-2">
              {prontosVagas.slice(0, 5).map((medico) => (
                <MedicoCard key={medico.cliente_id} medico={medico} />
              ))}
              {prontosVagas.length > 5 && (
                <p className="text-center text-sm text-muted-foreground">
                  +{prontosVagas.length - 5} mais
                </p>
              )}
            </div>
          </div>
        )}

        {/* Para Follow-up */}
        {paraFollowup.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Calendar className="h-4 w-4 text-status-info-solid" />
              <h4 className="font-semibold">Para Follow-up ({paraFollowup.length})</h4>
            </div>
            <div className="space-y-2">
              {paraFollowup.slice(0, 3).map((medico) => (
                <MedicoCard key={medico.cliente_id} medico={medico} />
              ))}
              {paraFollowup.length > 3 && (
                <p className="text-center text-sm text-muted-foreground">
                  +{paraFollowup.length - 3} mais
                </p>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

interface MedicoCardProps {
  medico: MedicoDestaque
}

function MedicoCard({ medico }: MedicoCardProps) {
  const scoreColor =
    medico.interesse_score >= 0.7
      ? 'text-status-success-solid'
      : medico.interesse_score >= 0.4
        ? 'text-status-warning-solid'
        : 'text-muted-foreground'

  return (
    <div className="flex items-center justify-between rounded-lg border p-3 transition-colors hover:bg-muted/50">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
          <User className="h-5 w-5 text-muted-foreground" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-medium">{medico.nome}</span>
            <div className={`flex items-center gap-0.5 ${scoreColor}`}>
              <Star className="h-3 w-3 fill-current" />
              <span className="text-xs">{medico.interesse_score.toFixed(1)}</span>
            </div>
          </div>
          <p className="text-sm text-muted-foreground">
            {medico.especialidade || 'Especialidade nao informada'}
          </p>
          {medico.insight && (
            <p className="mt-1 text-xs italic text-gray-500">"{medico.insight}"</p>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Badge variant="outline" className="text-xs">
          {proximoPassoLabels[medico.proximo_passo] || medico.proximo_passo}
        </Badge>
        <Button variant="ghost" size="icon" asChild>
          <Link href={`/medicos/${medico.cliente_id}`}>
            <ChevronRight className="h-4 w-4" />
          </Link>
        </Button>
      </div>
    </div>
  )
}
