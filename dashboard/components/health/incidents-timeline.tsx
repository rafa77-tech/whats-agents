'use client'

/**
 * Timeline de Incidentes
 *
 * Sprint 55 E03 T03.3
 *
 * Mostra histórico de incidentes de saúde com estatísticas.
 */

import { useState, useEffect } from 'react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { AlertTriangle, CheckCircle2, Clock } from 'lucide-react'
import { cn } from '@/lib/utils'
import { formatDistanceToNow } from 'date-fns'
import { ptBR } from 'date-fns/locale'

interface Incident {
  id: string
  from_status: string | null
  to_status: string
  from_score: number | null
  to_score: number
  started_at: string
  resolved_at: string | null
  duration_seconds: number | null
}

interface IncidentStats {
  total_incidents: number
  critical_incidents: number
  degraded_incidents: number
  mttr_seconds: number
  uptime_percent: number
}

interface IncidentsTimelineProps {
  className?: string
}

export function IncidentsTimeline({ className }: IncidentsTimelineProps) {
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [stats, setStats] = useState<IncidentStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchData() {
      try {
        const [incidentsRes, statsRes] = await Promise.all([
          fetch('/api/incidents?limit=10'),
          fetch('/api/incidents/stats?dias=7'),
        ])

        if (incidentsRes.ok) {
          const data = await incidentsRes.json()
          setIncidents(data.incidents || [])
        }

        if (statsRes.ok) {
          setStats(await statsRes.json())
        }
      } catch (e) {
        console.error('Error fetching incidents:', e)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  if (loading) {
    return (
      <Card className={className}>
        <CardContent className="flex h-48 items-center justify-center">
          <div className="animate-pulse text-muted-foreground">Carregando...</div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Historico de Incidentes</CardTitle>
          {stats && (
            <Badge variant="outline" className="font-mono">
              Uptime 7d: {stats.uptime_percent}%
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {/* Stats resumo */}
        {stats && (
          <div className="mb-4 grid grid-cols-3 gap-4 text-center text-sm">
            <div>
              <div className="text-2xl font-bold">{stats.total_incidents}</div>
              <div className="text-muted-foreground">Incidentes (7d)</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-status-error-foreground">
                {stats.critical_incidents}
              </div>
              <div className="text-muted-foreground">Criticos</div>
            </div>
            <div>
              <div className="text-2xl font-bold">
                {stats.mttr_seconds > 0 ? `${Math.round(stats.mttr_seconds / 60)}min` : '-'}
              </div>
              <div className="text-muted-foreground">MTTR</div>
            </div>
          </div>
        )}

        {/* Timeline */}
        <div className="space-y-3">
          {incidents.length === 0 ? (
            <div className="py-8 text-center text-muted-foreground">
              <CheckCircle2 className="mx-auto h-8 w-8 text-status-success-foreground" />
              <p className="mt-2">Nenhum incidente registrado</p>
            </div>
          ) : (
            incidents.map((incident) => (
              <div
                key={incident.id}
                className={cn(
                  'flex items-start gap-3 rounded-lg border p-3',
                  incident.to_status === 'critical' &&
                    'border-status-error-border bg-status-error/10',
                  incident.to_status === 'degraded' &&
                    'border-status-warning-border bg-status-warning/10',
                  incident.to_status === 'healthy' &&
                    'border-status-success-border bg-status-success/10'
                )}
              >
                <div className="mt-0.5">
                  {incident.to_status === 'critical' && (
                    <AlertTriangle className="h-5 w-5 text-status-error-foreground" />
                  )}
                  {incident.to_status === 'degraded' && (
                    <AlertTriangle className="h-5 w-5 text-status-warning-foreground" />
                  )}
                  {incident.to_status === 'healthy' && (
                    <CheckCircle2 className="h-5 w-5 text-status-success-foreground" />
                  )}
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-medium capitalize">{incident.to_status}</span>
                    <span className="text-xs text-muted-foreground">
                      {formatDistanceToNow(new Date(incident.started_at), {
                        addSuffix: true,
                        locale: ptBR,
                      })}
                    </span>
                  </div>
                  <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                    <span>Score: {incident.to_score}</span>
                    {incident.duration_seconds && (
                      <>
                        <span>•</span>
                        <Clock className="h-3 w-3" />
                        <span>{Math.round(incident.duration_seconds / 60)}min</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  )
}
