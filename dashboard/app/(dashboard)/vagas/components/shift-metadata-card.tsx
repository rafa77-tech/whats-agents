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
    <Card className="md:col-span-2">
      <CardHeader>
        <CardTitle className="text-lg">Metadados</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <p className="text-sm text-muted-foreground">ID</p>
            <p className="font-mono text-sm">{id}</p>
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
        </div>
      </CardContent>
    </Card>
  )
}
