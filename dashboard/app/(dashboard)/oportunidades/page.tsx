'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Send,
  Calendar,
  AlertTriangle,
  User,
  Star,
  ChevronRight,
  RefreshCw,
  Target,
  Phone,
  Stethoscope,
  Clock,
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import {
  fetchOpportunities,
  Opportunity,
  OpportunitiesResponse,
} from '@/lib/api/extraction'

export default function OportunidadesPage() {
  const [data, setData] = useState<OpportunitiesResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const carregarOportunidades = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchOpportunities(100)
      setData(result)
    } catch (err) {
      console.error('Erro ao carregar oportunidades:', err)
      setError('Erro ao carregar oportunidades')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    carregarOportunidades()
  }, [carregarOportunidades])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold">
            <Target className="h-6 w-6" />
            Oportunidades
          </h1>
          <p className="text-muted-foreground">
            Acoes pendentes identificadas pela Julia
          </p>
        </div>
        <Button variant="outline" onClick={carregarOportunidades} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Atualizar
        </Button>
      </div>

      {/* Stats */}
      {data && (
        <div className="grid grid-cols-3 gap-4">
          <StatCard
            icon={<Send className="h-5 w-5" />}
            value={data.enviar_vagas.length}
            label="Prontos para Vagas"
            color="text-status-success-solid"
            bgColor="bg-status-success/10"
          />
          <StatCard
            icon={<Calendar className="h-5 w-5" />}
            value={data.agendar_followup.length}
            label="Para Follow-up"
            color="text-status-info-solid"
            bgColor="bg-status-info/10"
          />
          <StatCard
            icon={<AlertTriangle className="h-5 w-5" />}
            value={data.escalar_humano.length}
            label="Escalar para Humano"
            color="text-status-warning-solid"
            bgColor="bg-status-warning/10"
          />
        </div>
      )}

      {/* Error */}
      {error && (
        <Card>
          <CardContent className="py-8 text-center">
            <AlertTriangle className="mx-auto mb-4 h-12 w-12 text-status-error-solid" />
            <p className="text-status-error-foreground">{error}</p>
            <Button className="mt-4" onClick={carregarOportunidades}>
              Tentar Novamente
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Loading */}
      {loading && !data && (
        <div className="space-y-4">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      )}

      {/* Content */}
      {data && !error && (
        <Tabs defaultValue="enviar_vagas">
          <TabsList className="mb-4">
            <TabsTrigger value="enviar_vagas" className="gap-2">
              <Send className="h-4 w-4" />
              Prontos para Vagas ({data.enviar_vagas.length})
            </TabsTrigger>
            <TabsTrigger value="agendar_followup" className="gap-2">
              <Calendar className="h-4 w-4" />
              Para Follow-up ({data.agendar_followup.length})
            </TabsTrigger>
            <TabsTrigger value="escalar_humano" className="gap-2">
              <AlertTriangle className="h-4 w-4" />
              Escalar Humano ({data.escalar_humano.length})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="enviar_vagas">
            <OpportunityList
              opportunities={data.enviar_vagas}
              emptyMessage="Nenhum medico pronto para receber vagas no momento."
              actionLabel="Enviar Vagas"
              actionIcon={<Send className="h-4 w-4" />}
            />
          </TabsContent>

          <TabsContent value="agendar_followup">
            <OpportunityList
              opportunities={data.agendar_followup}
              emptyMessage="Nenhum medico para follow-up no momento."
              actionLabel="Agendar"
              actionIcon={<Calendar className="h-4 w-4" />}
            />
          </TabsContent>

          <TabsContent value="escalar_humano">
            <OpportunityList
              opportunities={data.escalar_humano}
              emptyMessage="Nenhuma situacao para escalar no momento."
              actionLabel="Assumir"
              actionIcon={<User className="h-4 w-4" />}
            />
          </TabsContent>
        </Tabs>
      )}

      {/* Empty state */}
      {data && data.total === 0 && !loading && (
        <Card>
          <CardContent className="py-12 text-center">
            <Target className="mx-auto mb-4 h-12 w-12 text-gray-300" />
            <h3 className="text-lg font-medium">Nenhuma oportunidade pendente</h3>
            <p className="mt-1 text-muted-foreground">
              Todas as acoes foram processadas. Volte mais tarde para novas oportunidades.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

interface StatCardProps {
  icon: React.ReactNode
  value: number
  label: string
  color: string
  bgColor: string
}

function StatCard({ icon, value, label, color, bgColor }: StatCardProps) {
  return (
    <Card className={bgColor}>
      <CardContent className="flex items-center justify-between p-4">
        <div>
          <p className="text-3xl font-bold">{value}</p>
          <p className="text-sm text-muted-foreground">{label}</p>
        </div>
        <div className={color}>{icon}</div>
      </CardContent>
    </Card>
  )
}

interface OpportunityListProps {
  opportunities: Opportunity[]
  emptyMessage: string
  actionLabel: string
  actionIcon: React.ReactNode
}

function OpportunityList({
  opportunities,
  emptyMessage,
  actionLabel,
  actionIcon,
}: OpportunityListProps) {
  if (opportunities.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <Target className="mx-auto mb-4 h-12 w-12 text-gray-300" />
          <p className="text-muted-foreground">{emptyMessage}</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-3">
      {opportunities.map((opp) => (
        <OpportunityCard
          key={opp.id}
          opportunity={opp}
          actionLabel={actionLabel}
          actionIcon={actionIcon}
        />
      ))}
    </div>
  )
}

interface OpportunityCardProps {
  opportunity: Opportunity
  actionLabel: string
  actionIcon: React.ReactNode
}

function OpportunityCard({ opportunity, actionLabel, actionIcon }: OpportunityCardProps) {
  const scoreColor =
    opportunity.interesse_score >= 0.7
      ? 'text-status-success-solid'
      : opportunity.interesse_score >= 0.4
        ? 'text-status-warning-solid'
        : 'text-muted-foreground'

  return (
    <Card className="transition-shadow hover:shadow-md">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          {/* Info do médico */}
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
              <User className="h-5 w-5 text-muted-foreground" />
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-medium">{opportunity.cliente_nome}</span>
                <div className={`flex items-center gap-0.5 ${scoreColor}`}>
                  <Star className="h-3 w-3 fill-current" />
                  <span className="text-xs">{opportunity.interesse_score.toFixed(1)}</span>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                {opportunity.cliente_especialidade && (
                  <span className="flex items-center gap-1">
                    <Stethoscope className="h-3 w-3" />
                    {opportunity.cliente_especialidade}
                  </span>
                )}
                {opportunity.cliente_telefone && (
                  <span className="flex items-center gap-1">
                    <Phone className="h-3 w-3" />
                    {opportunity.cliente_telefone}
                  </span>
                )}
              </div>

              {/* Contexto */}
              {(opportunity.disponibilidade_mencionada ||
                (opportunity.preferencias && opportunity.preferencias.length > 0)) && (
                <p className="mt-1 text-sm italic text-gray-500">
                  {opportunity.disponibilidade_mencionada ||
                    opportunity.preferencias?.slice(0, 2).join(', ')}
                </p>
              )}

              {/* Objeção (para escalar) */}
              {opportunity.objecao_tipo && (
                <Badge variant="outline" className="mt-1 text-status-warning-foreground">
                  Objecao: {opportunity.objecao_tipo}
                </Badge>
              )}
            </div>
          </div>

          {/* Meta info e ações */}
          <div className="flex flex-col items-end gap-2">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" />
              {formatDistanceToNow(new Date(opportunity.created_at), {
                addSuffix: true,
                locale: ptBR,
              })}
            </div>

            {opportunity.campanha_nome && (
              <Badge variant="secondary" className="text-xs">
                {opportunity.campanha_nome}
              </Badge>
            )}

            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" asChild>
                <Link href={`/medicos/${opportunity.cliente_id}`}>
                  Ver Perfil
                  <ChevronRight className="ml-1 h-3 w-3" />
                </Link>
              </Button>
              <Button size="sm" className="gap-1">
                {actionIcon}
                {actionLabel}
              </Button>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
