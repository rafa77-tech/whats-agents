'use client'

import { useCallback, useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { ArrowLeft, Phone, Stethoscope, MapPin, Mail } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuth } from '@/hooks/use-auth'
import { DoctorTimeline } from '../components/doctor-timeline'
import { DoctorStats } from '../components/doctor-stats'
import { DoctorActions } from '../components/doctor-actions'

interface DoctorDetail {
  id: string
  nome: string
  telefone: string
  crm?: string
  especialidade?: string
  cidade?: string
  estado?: string
  email?: string
  stage_jornada?: string
  opt_out: boolean
  opt_out_data?: string
  pressure_score_atual?: number
  contexto_consolidado?: string
  created_at: string
  conversations_count: number
  last_interaction_at?: string
}

const STAGE_COLORS: Record<string, string> = {
  novo: 'bg-gray-100 text-gray-800',
  respondeu: 'bg-blue-100 text-blue-800',
  negociando: 'bg-yellow-100 text-yellow-800',
  convertido: 'bg-green-100 text-green-800',
  perdido: 'bg-red-100 text-red-800',
}

const STAGE_LABELS: Record<string, string> = {
  novo: 'Novo',
  respondeu: 'Respondeu',
  negociando: 'Negociando',
  convertido: 'Convertido',
  perdido: 'Perdido',
}

function DoctorProfileSkeleton() {
  return (
    <div className="space-y-6 p-6">
      <Skeleton className="h-32" />
      <Skeleton className="h-64" />
    </div>
  )
}

export default function DoctorProfilePage() {
  const params = useParams()
  const router = useRouter()
  const { session } = useAuth()
  const doctorId = params.id as string

  const [loading, setLoading] = useState(true)
  const [doctor, setDoctor] = useState<DoctorDetail | null>(null)

  const fetchDoctor = useCallback(async () => {
    if (!session?.access_token) return

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/dashboard/doctors/${doctorId}`, {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      })

      if (response.ok) {
        const result = await response.json()
        setDoctor(result)
      }
    } catch (err) {
      console.error('Failed to fetch doctor:', err)
    } finally {
      setLoading(false)
    }
  }, [session?.access_token, doctorId])

  useEffect(() => {
    fetchDoctor()
  }, [fetchDoctor])

  if (loading) {
    return <DoctorProfileSkeleton />
  }

  if (!doctor) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-muted-foreground">Medico nao encontrado</p>
      </div>
    )
  }

  const initials =
    (doctor.nome || 'XX')
      .split(' ')
      .slice(0, 2)
      .map((n) => n?.[0] || '')
      .join('')
      .toUpperCase() || 'XX'

  const stageColor = STAGE_COLORS[doctor.stage_jornada || ''] || 'bg-gray-100 text-gray-800'
  const stageLabel =
    STAGE_LABELS[doctor.stage_jornada || ''] || doctor.stage_jornada || 'Desconhecido'

  return (
    <div className="flex h-full flex-col overflow-auto">
      {/* Header */}
      <div className="sticky top-0 z-10 border-b bg-background p-4 md:p-6">
        <Button variant="ghost" size="sm" onClick={() => router.back()} className="mb-4">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Voltar
        </Button>

        <div className="flex gap-4">
          <Avatar className="h-16 w-16 flex-shrink-0 md:h-20 md:w-20">
            <AvatarFallback className="bg-primary/10 text-xl text-primary">
              {initials}
            </AvatarFallback>
          </Avatar>

          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between">
              <div>
                <h1 className="text-xl font-bold md:text-2xl">{doctor.nome}</h1>
                <div className="mt-1 flex flex-wrap gap-2">
                  <Badge className={stageColor}>{stageLabel}</Badge>
                  {doctor.opt_out && <Badge variant="destructive">Opt-out</Badge>}
                </div>
              </div>
            </div>

            <div className="mt-3 flex flex-wrap gap-4 text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                <Phone className="h-4 w-4" />
                {doctor.telefone}
              </span>
              {doctor.especialidade && (
                <span className="flex items-center gap-1">
                  <Stethoscope className="h-4 w-4" />
                  {doctor.especialidade}
                </span>
              )}
              {doctor.cidade && (
                <span className="flex items-center gap-1">
                  <MapPin className="h-4 w-4" />
                  {doctor.cidade}
                  {doctor.estado && `, ${doctor.estado}`}
                </span>
              )}
              {doctor.email && (
                <span className="flex items-center gap-1">
                  <Mail className="h-4 w-4" />
                  {doctor.email}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 p-4 md:p-6">
        <Tabs defaultValue="timeline">
          <TabsList className="w-full md:w-auto">
            <TabsTrigger value="timeline" className="flex-1 md:flex-none">
              Historico
            </TabsTrigger>
            <TabsTrigger value="stats" className="flex-1 md:flex-none">
              Metricas
            </TabsTrigger>
            <TabsTrigger value="actions" className="flex-1 md:flex-none">
              Acoes
            </TabsTrigger>
          </TabsList>

          <div className="mt-6">
            <TabsContent value="timeline">
              <DoctorTimeline doctorId={doctorId} />
            </TabsContent>

            <TabsContent value="stats">
              <DoctorStats doctor={doctor} />
            </TabsContent>

            <TabsContent value="actions">
              <DoctorActions doctor={doctor} onRefresh={fetchDoctor} />
            </TabsContent>
          </div>
        </Tabs>
      </div>
    </div>
  )
}
