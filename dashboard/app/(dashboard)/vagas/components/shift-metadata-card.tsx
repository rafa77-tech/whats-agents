/**
 * Shift Metadata Card Component
 *
 * Displays shift metadata: ID, created_at, updated_at.
 */

import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface ShiftMetadataCardProps {
  id: string
  createdAt: string | null
  updatedAt: string | null
}

function formatDate(value: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (isNaN(date.getTime())) return '—'
  return format(date, "dd/MM/yyyy 'as' HH:mm", { locale: ptBR })
}

export function ShiftMetadataCard({ id, createdAt, updatedAt }: ShiftMetadataCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Metadados</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div>
          <p className="text-sm text-muted-foreground">ID</p>
          <p className="truncate font-mono text-sm" title={id}>
            {id}
          </p>
        </div>
        <div>
          <p className="text-sm text-muted-foreground">Criado em</p>
          <p className="text-sm">{formatDate(createdAt)}</p>
        </div>
        {updatedAt && (
          <div>
            <p className="text-sm text-muted-foreground">Atualizado em</p>
            <p className="text-sm">{formatDate(updatedAt)}</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
