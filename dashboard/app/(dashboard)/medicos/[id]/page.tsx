'use client'

import { useCallback, useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { ArrowLeft, Phone, Stethoscope, MapPin, Mail, Smartphone } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Skeleton } from '@/components/ui/skeleton'
import { DoctorTimeline } from '../components/doctor-timeline'
import { DoctorStats } from '../components/doctor-stats'
import { DoctorActions } from '../components/doctor-actions'
import { DoctorInsights } from '../components/doctor-insights'
import { getInitials, getStageColor, getStageLabel } from '@/lib/medicos'
import type { DoctorDetail } from '@/lib/medicos'

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
  const doctorId = params.id as string

  const [loading, setLoading] = useState(true)
  const [doctor, setDoctor] = useState<DoctorDetail | null>(null)

  const fetchDoctor = useCallback(async () => {
    try {
      const response = await fetch(`/api/medicos/${doctorId}`)

      if (response.ok) {
        const result = await response.json()
        setDoctor(result)
      }
    } catch (err) {
      console.error('Failed to fetch doctor:', err)
    } finally {
      setLoading(false)
    }
  }, [doctorId])

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

  const initials = getInitials(doctor.nome)
  const stageColor = getStageColor(doctor.stage_jornada)
  const stageLabel = getStageLabel(doctor.stage_jornada)

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
                  {doctor.app_enviado && (
                    <Badge variant="secondary" className="gap-1">
                      <Smartphone className="h-3 w-3" />
                      App Enviado
                    </Badge>
                  )}
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
            <TabsTrigger value="insights" className="flex-1 md:flex-none">
              Insights
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

            <TabsContent value="insights">
              <DoctorInsights doctorId={doctorId} />
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
