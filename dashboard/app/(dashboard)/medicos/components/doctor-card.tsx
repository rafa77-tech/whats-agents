'use client'

import { useRouter } from 'next/navigation'
import { Phone, Stethoscope, MapPin } from 'lucide-react'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

export interface Doctor {
  id: string
  nome: string
  telefone: string
  especialidade?: string
  cidade?: string
  stage_jornada?: string
  opt_out: boolean
  created_at: string
}

interface Props {
  doctor: Doctor
}

const STAGE_COLORS: Record<string, string> = {
  novo: 'bg-gray-100 text-gray-800',
  prospecting: 'bg-gray-100 text-gray-800',
  respondeu: 'bg-blue-100 text-blue-800',
  engaged: 'bg-blue-100 text-blue-800',
  negociando: 'bg-yellow-100 text-yellow-800',
  negotiating: 'bg-yellow-100 text-yellow-800',
  convertido: 'bg-green-100 text-green-800',
  converted: 'bg-green-100 text-green-800',
  perdido: 'bg-red-100 text-red-800',
  lost: 'bg-red-100 text-red-800',
}

const STAGE_LABELS: Record<string, string> = {
  novo: 'Novo',
  prospecting: 'Prospeccao',
  respondeu: 'Respondeu',
  engaged: 'Engajado',
  negociando: 'Negociando',
  negotiating: 'Negociando',
  convertido: 'Convertido',
  converted: 'Convertido',
  perdido: 'Perdido',
  lost: 'Perdido',
}

export function DoctorCard({ doctor }: Props) {
  const router = useRouter()

  const initials =
    (doctor.nome || 'XX')
      .split(' ')
      .slice(0, 2)
      .map((n) => n?.[0] || '')
      .join('')
      .toUpperCase() || 'XX'

  const stageColor = STAGE_COLORS[doctor.stage_jornada || ''] || 'bg-gray-100 text-gray-800'
  const stageLabel =
    STAGE_LABELS[doctor.stage_jornada || ''] || doctor.stage_jornada || 'Desconhecido'

  return (
    <div
      onClick={() => router.push(`/medicos/${doctor.id}`)}
      className="flex cursor-pointer gap-3 rounded-lg border bg-card p-4 transition-colors hover:bg-accent/50"
    >
      <Avatar className="h-12 w-12 flex-shrink-0">
        <AvatarFallback className="bg-primary/10 text-primary">{initials}</AvatarFallback>
      </Avatar>

      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <h3 className="truncate font-medium">{doctor.nome}</h3>
          <div className="flex flex-shrink-0 gap-1">
            <Badge className={cn('text-xs', stageColor)}>{stageLabel}</Badge>
            {doctor.opt_out && (
              <Badge variant="destructive" className="text-xs">
                Opt-out
              </Badge>
            )}
          </div>
        </div>

        <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-sm text-muted-foreground">
          <span className="flex items-center gap-1">
            <Phone className="h-3 w-3" />
            {doctor.telefone}
          </span>
          {doctor.especialidade && (
            <span className="flex items-center gap-1">
              <Stethoscope className="h-3 w-3" />
              {doctor.especialidade}
            </span>
          )}
          {doctor.cidade && (
            <span className="flex items-center gap-1">
              <MapPin className="h-3 w-3" />
              {doctor.cidade}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
