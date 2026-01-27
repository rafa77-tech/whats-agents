'use client'

import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { MessageCircle, Calendar, TrendingUp, Clock } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface Doctor {
  id: string
  nome: string
  stage_jornada?: string
  pressure_score_atual?: number
  contexto_consolidado?: string
  conversations_count: number
  last_interaction_at?: string
  created_at: string
}

interface Props {
  doctor: Doctor
}

export function DoctorStats({ doctor }: Props) {
  const stats = [
    {
      title: 'Conversas',
      value: doctor.conversations_count,
      icon: MessageCircle,
      description: 'Total de conversas',
    },
    {
      title: 'Pressure Score',
      value: doctor.pressure_score_atual ?? 'N/A',
      icon: TrendingUp,
      description: 'Indice de saturacao',
    },
    {
      title: 'Cadastro',
      value: format(new Date(doctor.created_at), 'dd/MM/yyyy', { locale: ptBR }),
      icon: Calendar,
      description: 'Data de cadastro',
    },
    {
      title: 'Ultima Interacao',
      value: doctor.last_interaction_at
        ? format(new Date(doctor.last_interaction_at), 'dd/MM/yyyy', { locale: ptBR })
        : 'Nunca',
      icon: Clock,
      description: 'Ultimo contato',
    },
  ]

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2">
        {stats.map((stat) => (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
              <stat.icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
              <p className="text-xs text-muted-foreground">{stat.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {doctor.contexto_consolidado && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Contexto Consolidado</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-wrap text-sm text-muted-foreground">
              {doctor.contexto_consolidado}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
