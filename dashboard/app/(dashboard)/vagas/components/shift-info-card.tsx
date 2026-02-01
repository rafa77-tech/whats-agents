/**
 * Shift Info Card Component
 *
 * Displays shift information: date, time, value, hospital, specialty, sector.
 */

import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { Calendar, Clock, DollarSign, Building2, Stethoscope } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatCurrency, parseShiftDate } from '@/lib/vagas'

interface ShiftInfoCardProps {
  data: string
  horaInicio: string
  horaFim: string
  valor: number
  hospital: string
  especialidade: string
  setor?: string | null
}

export function ShiftInfoCard({
  data,
  horaInicio,
  horaFim,
  valor,
  hospital,
  especialidade,
  setor,
}: ShiftInfoCardProps) {
  const shiftDate = parseShiftDate(data)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Informacoes do Plantao</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-3">
          <Calendar className="h-5 w-5 text-muted-foreground" />
          <div>
            <p className="text-sm text-muted-foreground">Data</p>
            <p className="font-medium">
              {format(shiftDate, "EEEE, dd 'de' MMMM 'de' yyyy", { locale: ptBR })}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Clock className="h-5 w-5 text-muted-foreground" />
          <div>
            <p className="text-sm text-muted-foreground">Horario</p>
            <p className="font-medium">
              {horaInicio} - {horaFim}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <DollarSign className="h-5 w-5 text-muted-foreground" />
          <div>
            <p className="text-sm text-muted-foreground">Valor</p>
            <p className="font-medium">{formatCurrency(valor)}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Building2 className="h-5 w-5 text-muted-foreground" />
          <div>
            <p className="text-sm text-muted-foreground">Hospital</p>
            <p className="font-medium">{hospital}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Stethoscope className="h-5 w-5 text-muted-foreground" />
          <div>
            <p className="text-sm text-muted-foreground">Especialidade</p>
            <p className="font-medium">{especialidade}</p>
          </div>
        </div>

        {setor && (
          <div className="flex items-center gap-3">
            <Building2 className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="text-sm text-muted-foreground">Setor</p>
              <p className="font-medium">{setor}</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
