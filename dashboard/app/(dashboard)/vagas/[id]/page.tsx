'use client'

import dynamic from 'next/dynamic'
import { useCallback, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { ArrowLeft, Edit, ExternalLink, Megaphone, Trash2, User } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import {
  useShiftDetail,
  useDoctorSearch,
  getStatusBadgeColor,
  getStatusLabel,
  buildCampaignInitialData,
} from '@/lib/vagas'
import type { Shift, WizardInitialData } from '@/lib/vagas'
import { ShiftInfoCard } from '../components/shift-info-card'
import { AssignedDoctorCard } from '../components/assigned-doctor-card'
import { ShiftMetadataCard } from '../components/shift-metadata-card'
import { AssignDoctorDialog } from '../components/assign-doctor-dialog'
import { EditarVagaDialog } from '../components/editar-vaga-dialog'

const NovaCampanhaWizard = dynamic(
  () =>
    import('@/components/campanhas/nova-campanha-wizard').then((mod) => ({
      default: mod.NovaCampanhaWizard,
    })),
  { ssr: false }
)

export default function ShiftDetailPage() {
  const params = useParams()
  const id = params.id as string
  const router = useRouter()

  const [showAssignDialog, setShowAssignDialog] = useState(false)
  const [showEditDialog, setShowEditDialog] = useState(false)
  const [wizardOpen, setWizardOpen] = useState(false)
  const [wizardInitialData, setWizardInitialData] = useState<WizardInitialData | null>(null)

  const { shift, loading, error, deleting, assigning, updating, actions } = useShiftDetail(id)
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

  const handleCreateCampaign = useCallback(() => {
    if (!shift) return
    // Convert ShiftDetail to Shift shape for the helper
    const shiftForCampaign: Shift = {
      id: shift.id,
      hospital: shift.hospital,
      hospital_id: shift.hospital_id,
      especialidade: shift.especialidade,
      especialidade_id: shift.especialidade_id,
      data: shift.data,
      hora_inicio: shift.hora_inicio,
      hora_fim: shift.hora_fim,
      valor: shift.valor,
      status: shift.status,
      reservas_count: 0,
      created_at: shift.created_at,
      contato_nome: shift.contato_nome,
      contato_whatsapp: shift.contato_whatsapp,
    }
    const initialData = buildCampaignInitialData([shiftForCampaign])
    setWizardInitialData(initialData)
    setWizardOpen(true)
  }, [shift])

  const handleWizardSuccess = useCallback(() => {
    setWizardOpen(false)
    setWizardInitialData(null)
    actions.refresh()
    toast.success('Campanha criada com sucesso')
  }, [actions])

  const handleWizardClose = useCallback((open: boolean) => {
    if (!open) {
      setWizardOpen(false)
      setWizardInitialData(null)
    }
  }, [])

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
            <Button variant="outline" size="sm" onClick={handleCreateCampaign}>
              <Megaphone className="mr-2 h-4 w-4" />
              <span className="hidden md:inline">Criar Campanha</span>
            </Button>
            <Button variant="outline" size="icon" onClick={() => setShowEditDialog(true)}>
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
          {/* [1,1] Informacoes do Plantao */}
          <ShiftInfoCard
            data={shift.data}
            horaInicio={shift.hora_inicio}
            horaFim={shift.hora_fim}
            valor={shift.valor}
            hospital={shift.hospital}
            especialidade={shift.especialidade}
            setor={shift.setor}
          />

          {/* [1,2] Medico Atribuido */}
          <AssignedDoctorCard
            clienteId={shift.cliente_id}
            clienteNome={shift.cliente_nome}
            status={shift.status}
            onAssignClick={() => setShowAssignDialog(true)}
          />

          {/* [2,1] Contato Responsavel */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <User className="h-5 w-5" />
                Contato Responsavel
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {shift.contato_nome ? (
                <>
                  <div>
                    <p className="text-sm text-muted-foreground">Nome</p>
                    <p className="text-sm font-medium">{shift.contato_nome}</p>
                  </div>
                  {shift.contato_whatsapp && (
                    <div>
                      <p className="text-sm text-muted-foreground">WhatsApp</p>
                      <a
                        href={`https://wa.me/${shift.contato_whatsapp}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
                      >
                        {shift.contato_whatsapp}
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </div>
                  )}
                </>
              ) : (
                <div className="rounded-md border border-dashed p-3">
                  <p className="text-sm text-muted-foreground">
                    Nenhum contato informado. Sem essa informacao, a Julia nao consegue intermediar
                    esta vaga.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* [2,2] Metadados */}
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

      {/* Edit Shift Dialog */}
      {shift && (
        <EditarVagaDialog
          open={showEditDialog}
          onOpenChange={setShowEditDialog}
          shift={shift}
          onSave={actions.updateShift}
          saving={updating}
        />
      )}

      {/* Campaign wizard (dynamic import for bundle optimization) */}
      {wizardOpen && (
        <NovaCampanhaWizard
          open={wizardOpen}
          onOpenChange={handleWizardClose}
          onSuccess={handleWizardSuccess}
          initialData={wizardInitialData}
        />
      )}
    </div>
  )
}
