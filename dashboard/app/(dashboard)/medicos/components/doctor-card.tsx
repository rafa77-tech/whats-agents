'use client'

import { useRouter } from 'next/navigation'
import { Phone, Stethoscope, MapPin } from 'lucide-react'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { getInitials, getStageColor, getStageLabel } from '@/lib/medicos'
import type { Doctor } from '@/lib/medicos'

export type { Doctor }

interface Props {
  doctor: Doctor
}

export function DoctorCard({ doctor }: Props) {
  const router = useRouter()

  const initials = getInitials(doctor.nome)
  const stageColor = getStageColor(doctor.stage_jornada)
  const stageLabel = getStageLabel(doctor.stage_jornada)

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
