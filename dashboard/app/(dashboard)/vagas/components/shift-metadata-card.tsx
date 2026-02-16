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
  createdAt: string
  updatedAt: string | null
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
          <p className="text-sm">
            {format(new Date(createdAt), "dd/MM/yyyy 'as' HH:mm", {
              locale: ptBR,
            })}
          </p>
        </div>
        {updatedAt && (
          <div>
            <p className="text-sm text-muted-foreground">Atualizado em</p>
            <p className="text-sm">
              {format(new Date(updatedAt), "dd/MM/yyyy 'as' HH:mm", {
                locale: ptBR,
              })}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
