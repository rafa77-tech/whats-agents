'use client'

import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { useRouter } from 'next/navigation'
import { Clock, DollarSign, User } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import {
  formatCurrency,
  parseShiftDate,
  getStatusBadgeColor,
  getStatusLabel,
} from '@/lib/vagas'
import type { Shift } from '@/lib/vagas'

// Re-export for backward compatibility
export type { Shift } from '@/lib/vagas'

interface Props {
  shift: Shift
}

export function ShiftCard({ shift }: Props) {
  const router = useRouter()

  const shiftDate = parseShiftDate(shift.data)
  const statusColor = getStatusBadgeColor(shift.status)
  const statusLabel = getStatusLabel(shift.status)

  return (
    <Card
      className="cursor-pointer transition-colors hover:bg-muted/50"
      onClick={() => router.push(`/vagas/${shift.id}`)}
    >
      <CardContent className="p-4">
        <div className="flex flex-col gap-4 md:flex-row md:items-center">
          {/* Data */}
          <div className="w-16 flex-shrink-0 rounded-lg bg-primary/10 p-3 text-center">
            <p className="text-2xl font-bold text-primary">{format(shiftDate, 'dd')}</p>
            <p className="text-xs uppercase text-muted-foreground">
              {format(shiftDate, 'MMM', { locale: ptBR })}
            </p>
          </div>

          {/* Info */}
          <div className="flex-1 space-y-2">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-semibold">{shift.hospital}</h3>
                <p className="text-sm text-muted-foreground">{shift.especialidade}</p>
              </div>
              <Badge className={cn('text-xs', statusColor)}>{statusLabel}</Badge>
            </div>

            <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                <Clock className="h-4 w-4" />
                {shift.hora_inicio} - {shift.hora_fim}
              </span>
              <span className="flex items-center gap-1">
                <DollarSign className="h-4 w-4" />
                {formatCurrency(shift.valor)}
              </span>
              {shift.reservas_count > 0 && (
                <span className="flex items-center gap-1">
                  <User className="h-4 w-4" />
                  {shift.reservas_count} reserva(s)
                </span>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
