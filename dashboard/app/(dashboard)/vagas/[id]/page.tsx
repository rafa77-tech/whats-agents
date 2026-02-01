'use client'

import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { useRouter } from 'next/navigation'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import {
  ArrowLeft,
  Calendar,
  Clock,
  DollarSign,
  Building2,
  Stethoscope,
  User,
  Edit,
  Trash2,
  Search,
  Loader2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { cn } from '@/lib/utils'

interface ShiftDetail {
  id: string
  hospital: string
  hospital_id: string
  especialidade: string
  especialidade_id: string
  setor: string | null
  setor_id: string | null
  data: string
  hora_inicio: string
  hora_fim: string
  valor: number
  status: string
  cliente_id: string | null
  cliente_nome: string | null
  created_at: string
  updated_at: string | null
}

interface Doctor {
  id: string
  nome: string
  telefone: string
  especialidade?: string
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

export default function ShiftDetailPage() {
  const params = useParams()
  const id = params.id as string
  const router = useRouter()
  const [shift, setShift] = useState<ShiftDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Dialog state
  const [showAssignDialog, setShowAssignDialog] = useState(false)
  const [doctorSearch, setDoctorSearch] = useState('')
  const [doctors, setDoctors] = useState<Doctor[]>([])
  const [searchingDoctors, setSearchingDoctors] = useState(false)
  const [assigningDoctor, setAssigningDoctor] = useState(false)

  const fetchShift = useCallback(async () => {
    try {
      const response = await fetch(`/api/vagas/${id}`)

      if (response.ok) {
        const data = await response.json()
        setShift(data)
      } else if (response.status === 404) {
        setError('Vaga nao encontrada')
      } else {
        setError('Erro ao carregar vaga')
      }
    } catch (err) {
      console.error('Failed to fetch shift:', err)
      setError('Erro ao carregar vaga')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    fetchShift()
  }, [fetchShift])

  // Search doctors with debounce
  useEffect(() => {
    if (!doctorSearch || doctorSearch.length < 2) {
      setDoctors([])
      return
    }

    const timer = setTimeout(async () => {
      setSearchingDoctors(true)
      try {
        const response = await fetch(`/api/medicos?search=${encodeURIComponent(doctorSearch)}&per_page=10`)
        if (response.ok) {
          const result = await response.json()
          setDoctors(result.data || [])
        }
      } catch (err) {
        console.error('Failed to search doctors:', err)
      } finally {
        setSearchingDoctors(false)
      }
    }, 300)

    return () => clearTimeout(timer)
  }, [doctorSearch])

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    }).format(value)
  }

  const handleDelete = async () => {
    if (!confirm('Tem certeza que deseja excluir esta vaga?')) return

    try {
      const response = await fetch(`/api/vagas/${id}`, {
        method: 'DELETE',
      })

      if (response.ok) {
        router.push('/vagas')
      } else {
        const data = await response.json()
        alert(data.error || 'Erro ao excluir vaga')
      }
    } catch (err) {
      console.error('Failed to delete shift:', err)
      alert('Erro ao excluir vaga')
    }
  }

  const handleAssignDoctor = async (doctorId: string) => {
    setAssigningDoctor(true)
    try {
      const response = await fetch(`/api/vagas/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cliente_id: doctorId }),
      })

      if (response.ok) {
        setShowAssignDialog(false)
        setDoctorSearch('')
        setDoctors([])
        // Refresh shift data
        await fetchShift()
      } else {
        const data = await response.json()
        alert(data.error || 'Erro ao atribuir medico')
      }
    } catch (err) {
      console.error('Failed to assign doctor:', err)
      alert('Erro ao atribuir medico')
    } finally {
      setAssigningDoctor(false)
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

  const shiftDate = new Date(shift.data + 'T00:00:00')
  const statusColor = STATUS_COLORS[shift.status] || 'bg-gray-100 text-gray-800'
  const statusLabel = STATUS_LABELS[shift.status] || shift.status

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
          {/* Info Card */}
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
                    {shift.hora_inicio} - {shift.hora_fim}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <DollarSign className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="text-sm text-muted-foreground">Valor</p>
                  <p className="font-medium">{formatCurrency(shift.valor)}</p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Building2 className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="text-sm text-muted-foreground">Hospital</p>
                  <p className="font-medium">{shift.hospital}</p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Stethoscope className="h-5 w-5 text-muted-foreground" />
                <div>
                  <p className="text-sm text-muted-foreground">Especialidade</p>
                  <p className="font-medium">{shift.especialidade}</p>
                </div>
              </div>

              {shift.setor && (
                <div className="flex items-center gap-3">
                  <Building2 className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Setor</p>
                    <p className="font-medium">{shift.setor}</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Assigned Doctor Card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Medico Atribuido</CardTitle>
            </CardHeader>
            <CardContent>
              {shift.cliente_id ? (
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
                    <User className="h-6 w-6 text-primary" />
                  </div>
                  <div>
                    <p className="font-medium">{shift.cliente_nome || 'Nome nao disponivel'}</p>
                    <Button
                      variant="link"
                      className="h-auto p-0"
                      onClick={() => router.push(`/medicos/${shift.cliente_id}`)}
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
                    {shift.status === 'aberta' && (
                      <Button
                        variant="outline"
                        className="mt-2"
                        onClick={() => setShowAssignDialog(true)}
                      >
                        Atribuir Medico
                      </Button>
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Metadata Card */}
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle className="text-lg">Metadados</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <p className="text-sm text-muted-foreground">ID</p>
                  <p className="font-mono text-sm">{shift.id}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Criado em</p>
                  <p className="text-sm">
                    {format(new Date(shift.created_at), "dd/MM/yyyy 'as' HH:mm", {
                      locale: ptBR,
                    })}
                  </p>
                </div>
                {shift.updated_at && (
                  <div>
                    <p className="text-sm text-muted-foreground">Atualizado em</p>
                    <p className="text-sm">
                      {format(new Date(shift.updated_at), "dd/MM/yyyy 'as' HH:mm", {
                        locale: ptBR,
                      })}
                    </p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Assign Doctor Dialog */}
      <Dialog open={showAssignDialog} onOpenChange={setShowAssignDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Atribuir Medico</DialogTitle>
            <DialogDescription>
              Busque e selecione um medico para atribuir a esta vaga.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Buscar por nome, telefone ou CRM..."
                value={doctorSearch}
                onChange={(e) => setDoctorSearch(e.target.value)}
                className="pl-10"
              />
            </div>

            <div className="max-h-64 space-y-2 overflow-auto">
              {searchingDoctors && (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                </div>
              )}

              {!searchingDoctors && doctorSearch.length >= 2 && doctors.length === 0 && (
                <p className="py-4 text-center text-sm text-muted-foreground">
                  Nenhum medico encontrado
                </p>
              )}

              {!searchingDoctors &&
                doctors.map((doctor) => (
                  <button
                    key={doctor.id}
                    onClick={() => handleAssignDoctor(doctor.id)}
                    disabled={assigningDoctor}
                    className="flex w-full items-center gap-3 rounded-lg border p-3 text-left transition-colors hover:bg-accent disabled:opacity-50"
                  >
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                      <User className="h-5 w-5 text-primary" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium">{doctor.nome}</p>
                      <p className="truncate text-sm text-muted-foreground">
                        {doctor.telefone}
                        {doctor.especialidade && ` • ${doctor.especialidade}`}
                      </p>
                    </div>
                    {assigningDoctor && <Loader2 className="h-4 w-4 animate-spin" />}
                  </button>
                ))}

              {!searchingDoctors && doctorSearch.length < 2 && (
                <p className="py-4 text-center text-sm text-muted-foreground">
                  Digite ao menos 2 caracteres para buscar
                </p>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
