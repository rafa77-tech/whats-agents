/**
 * Assigned Doctor Card Component
 *
 * Displays assigned doctor info or button to assign one.
 */

import { User } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface AssignedDoctorCardProps {
  clienteId: string | null
  clienteNome: string | null
  status: string
  onAssignClick: () => void
}

export function AssignedDoctorCard({
  clienteId,
  clienteNome,
  status,
  onAssignClick,
}: AssignedDoctorCardProps) {
  const router = useRouter()

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Medico Atribuido</CardTitle>
      </CardHeader>
      <CardContent>
        {clienteId ? (
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
              <User className="h-6 w-6 text-primary" />
            </div>
            <div>
              <p className="font-medium">{clienteNome || 'Nome nao disponivel'}</p>
              <Button
                variant="link"
                className="h-auto p-0"
                onClick={() => router.push(`/medicos/${clienteId}`)}
              >
                Ver perfil
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex h-32 items-center justify-center text-center">
            <div>
              <User className="mx-auto mb-2 h-8 w-8 text-muted-foreground" />
              <p className="text-muted-foreground">Nenhum medico atribuido</p>
              {status === 'aberta' && (
                <Button variant="outline" className="mt-2" onClick={onAssignClick}>
                  Atribuir Medico
                </Button>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
