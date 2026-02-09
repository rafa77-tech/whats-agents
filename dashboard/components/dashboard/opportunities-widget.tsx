/**
 * OpportunitiesWidget - Sprint 54
 *
 * Widget para o dashboard mostrando oportunidades pendentes
 * identificadas pelo pipeline de extraction.
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import type { Route } from 'next'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Target,
  Send,
  Calendar,
  AlertTriangle,
  ChevronRight,
  Sparkles,
} from 'lucide-react'
import { fetchOpportunities, OpportunitiesResponse } from '@/lib/api/extraction'

export function OpportunitiesWidget() {
  const [data, setData] = useState<OpportunitiesResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const result = await fetchOpportunities(50)
      setData(result)
    } catch (err) {
      console.error('Erro ao carregar oportunidades:', err)
      setError('Erro ao carregar')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  if (loading) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <Skeleton className="h-5 w-32" />
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            <Skeleton className="h-20" />
            <Skeleton className="h-20" />
            <Skeleton className="h-20" />
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error || !data) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Target className="h-5 w-5" />
            Oportunidades
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-center text-sm text-muted-foreground">{error || 'Sem dados'}</p>
        </CardContent>
      </Card>
    )
  }

  const hasOpportunities = data.total > 0

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Sparkles className="h-5 w-5 text-primary" />
          Oportunidades Julia
        </CardTitle>
        <Button variant="ghost" size="sm" asChild>
          <Link href={'/oportunidades' as Route}>
            Ver todas
            <ChevronRight className="ml-1 h-4 w-4" />
          </Link>
        </Button>
      </CardHeader>
      <CardContent>
        {hasOpportunities ? (
          <div className="grid grid-cols-3 gap-4">
            <OpportunityCard
              icon={<Send className="h-5 w-5" />}
              count={data.enviar_vagas.length}
              label="Prontos para Vagas"
              color="text-status-success-solid"
              bgColor="bg-status-success/10"
            />
            <OpportunityCard
              icon={<Calendar className="h-5 w-5" />}
              count={data.agendar_followup.length}
              label="Para Follow-up"
              color="text-status-info-solid"
              bgColor="bg-status-info/10"
            />
            <OpportunityCard
              icon={<AlertTriangle className="h-5 w-5" />}
              count={data.escalar_humano.length}
              label="Escalar Humano"
              color="text-status-warning-solid"
              bgColor="bg-status-warning/10"
            />
          </div>
        ) : (
          <div className="py-4 text-center">
            <Target className="mx-auto mb-2 h-8 w-8 text-gray-300" />
            <p className="text-sm text-muted-foreground">Nenhuma oportunidade pendente</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

interface OpportunityCardProps {
  icon: React.ReactNode
  count: number
  label: string
  color: string
  bgColor: string
}

function OpportunityCard({ icon, count, label, color, bgColor }: OpportunityCardProps) {
  return (
    <div className={`rounded-lg p-4 ${bgColor}`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-2xl font-bold">{count}</p>
          <p className="text-xs text-muted-foreground">{label}</p>
        </div>
        <div className={color}>{icon}</div>
      </div>
    </div>
  )
}
