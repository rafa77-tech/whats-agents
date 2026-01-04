'use client'

import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { useRouter } from 'next/navigation'
import { Clock, DollarSign, User } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

export interface Shift {
  id: string
  hospital: string
  hospital_id: string
  especialidade: string
  especialidade_id: string
  data: string
  hora_inicio: string
  hora_fim: string
  valor: number
  status: string
  reservas_count: number
  created_at: string
}

interface Props {
  shift: Shift
}

const STATUS_COLORS: Record<string, string> = {
  aberta: 'bg-green-100 text-green-800',
  reservada: 'bg-yellow-100 text-yellow-800',
  confirmada: 'bg-blue-100 text-blue-800',
  cancelada: 'bg-red-100 text-red-800',
  realizada: 'bg-gray-100 text-gray-800',
  fechada: 'bg-gray-100 text-gray-800',
}

const STATUS_LABELS: Record<string, string> = {
  aberta: 'Aberta',
  reservada: 'Reservada',
  confirmada: 'Confirmada',
  cancelada: 'Cancelada',
  realizada: 'Realizada',
  fechada: 'Fechada',
}

export function ShiftCard({ shift }: Props) {
  const router = useRouter()

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    }).format(value)
  }

  const shiftDate = new Date(shift.data + 'T00:00:00')
  const statusColor = STATUS_COLORS[shift.status] || 'bg-gray-100 text-gray-800'
  const statusLabel = STATUS_LABELS[shift.status] || shift.status

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
