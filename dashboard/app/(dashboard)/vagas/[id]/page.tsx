'use client'

import { useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { ArrowLeft, Edit, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import {
  useShiftDetail,
  useDoctorSearch,
  getStatusBadgeColor,
  getStatusLabel,
} from '@/lib/vagas'
import { ShiftInfoCard } from '../components/shift-info-card'
import { AssignedDoctorCard } from '../components/assigned-doctor-card'
import { ShiftMetadataCard } from '../components/shift-metadata-card'
import { AssignDoctorDialog } from '../components/assign-doctor-dialog'

export default function ShiftDetailPage() {
  const params = useParams()
  const id = params.id as string
  const router = useRouter()

  const [showAssignDialog, setShowAssignDialog] = useState(false)

  const { shift, loading, error, deleting, assigning, actions } = useShiftDetail(id)
  const doctorSearch = useDoctorSearch()

  const handleDelete = async () => {
    if (!confirm('Tem certeza que deseja excluir esta vaga?')) return

    try {
      const success = await actions.deleteShift()
      if (success) {
        toast.success('Vaga excluida com sucesso')
        router.push('/vagas')
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro ao excluir vaga'
      toast.error(message)
    }
  }

  const handleAssignDoctor = async (doctorId: string) => {
    try {
      const success = await actions.assignDoctor(doctorId)
      if (success) {
        setShowAssignDialog(false)
        doctorSearch.clear()
        toast.success('Medico atribuido com sucesso')
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro ao atribuir medico'
      toast.error(message)
    }
  }

  if (loading) {
    return (
      <div className="flex h-full flex-col">
        <div className="border-b p-4 md:p-6">
          <Skeleton className="mb-2 h-8 w-48" />
          <Skeleton className="h-4 w-32" />
        </div>
        <div className="flex-1 space-y-4 p-4 md:p-6">
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
        </div>
      </div>
    )
  }

  if (error || !shift) {
    return (
      <div className="flex h-full flex-col items-center justify-center">
        <p className="mb-4 text-muted-foreground">{error || 'Vaga nao encontrada'}</p>
        <Button variant="outline" onClick={() => router.push('/vagas')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Voltar
        </Button>
      </div>
    )
  }

  const statusColor = getStatusBadgeColor(shift.status)
  const statusLabel = getStatusLabel(shift.status)

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b p-4 md:p-6">
        <div className="mb-4 flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.push('/vagas')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="flex-1">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">{shift.hospital}</h1>
              <Badge className={cn('text-xs', statusColor)}>{statusLabel}</Badge>
            </div>
            <p className="text-muted-foreground">{shift.especialidade}</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="icon">
              <Edit className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              onClick={handleDelete}
              disabled={deleting}
              className="text-destructive hover:bg-destructive hover:text-destructive-foreground"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4 md:p-6">
        <div className="grid gap-6 md:grid-cols-2">
          <ShiftInfoCard
            data={shift.data}
            horaInicio={shift.hora_inicio}
            horaFim={shift.hora_fim}
            valor={shift.valor}
            hospital={shift.hospital}
            especialidade={shift.especialidade}
            setor={shift.setor}
          />

          <AssignedDoctorCard
            clienteId={shift.cliente_id}
            clienteNome={shift.cliente_nome}
            status={shift.status}
            onAssignClick={() => setShowAssignDialog(true)}
          />

          <ShiftMetadataCard
            id={shift.id}
            createdAt={shift.created_at}
            updatedAt={shift.updated_at}
          />
        </div>
      </div>

      {/* Assign Doctor Dialog */}
      <AssignDoctorDialog
        open={showAssignDialog}
        onOpenChange={setShowAssignDialog}
        search={doctorSearch.search}
        onSearchChange={doctorSearch.setSearch}
        doctors={doctorSearch.doctors}
        searching={doctorSearch.searching}
        assigning={assigning}
        onAssign={handleAssignDoctor}
      />
    </div>
  )
}
