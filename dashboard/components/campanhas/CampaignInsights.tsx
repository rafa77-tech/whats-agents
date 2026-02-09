'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { ThumbsUp, ThumbsDown, Meh, AlertTriangle, BarChart3, HelpCircle } from 'lucide-react'
import { CampaignReportMetrics } from '@/lib/api/extraction'

interface CampaignInsightsProps {
  metrics: CampaignReportMetrics | null
  loading?: boolean
}

export function CampaignInsights({ metrics, loading }: CampaignInsightsProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Insights da Campanha
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-20 rounded-lg" />
            ))}
          </div>
          <Skeleton className="mt-4 h-6 w-full" />
        </CardContent>
      </Card>
    )
  }

  if (!metrics || metrics.total_respostas === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Insights da Campanha
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="py-8 text-center">
            <HelpCircle className="mx-auto mb-4 h-12 w-12 text-gray-300" />
            <p className="text-gray-500">Ainda nao ha dados de insights para esta campanha.</p>
            <p className="mt-1 text-sm text-gray-400">
              Os insights sao gerados automaticamente apos as respostas.
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5" />
          Insights da Campanha
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Cards de métricas */}
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <MetricCard
            icon={<ThumbsUp className="h-6 w-6" />}
            value={metrics.interesse_positivo}
            label="Positivo"
            color="text-status-success-solid"
            bgColor="bg-status-success/10"
          />
          <MetricCard
            icon={<ThumbsDown className="h-6 w-6" />}
            value={metrics.interesse_negativo}
            label="Negativo"
            color="text-status-error-solid"
            bgColor="bg-status-error/10"
          />
          <MetricCard
            icon={<Meh className="h-6 w-6" />}
            value={metrics.interesse_neutro}
            label="Neutro"
            color="text-muted-foreground"
            bgColor="bg-muted"
          />
          <MetricCard
            icon={<AlertTriangle className="h-6 w-6" />}
            value={metrics.total_objecoes}
            label="Objecoes"
            color="text-status-warning-solid"
            bgColor="bg-status-warning/10"
          />
        </div>

        {/* Barra de interesse */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">Score Medio de Interesse</span>
            <span className="text-muted-foreground">
              {metrics.interesse_score_medio.toFixed(1)}/10
            </span>
          </div>
          <Progress value={metrics.interesse_score_medio * 10} className="h-3" />
        </div>

        {/* Métricas adicionais */}
        <div className="grid grid-cols-3 gap-4 border-t pt-4 text-center">
          <div>
            <p className="text-2xl font-bold text-status-success-solid">
              {metrics.prontos_para_vagas}
            </p>
            <p className="text-xs text-muted-foreground">Prontos para Vagas</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-status-info-solid">{metrics.para_followup}</p>
            <p className="text-xs text-muted-foreground">Para Follow-up</p>
          </div>
          <div>
            <p className="text-2xl font-bold">{metrics.taxa_interesse_pct.toFixed(0)}%</p>
            <p className="text-xs text-muted-foreground">Taxa de Interesse</p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

interface MetricCardProps {
  icon: React.ReactNode
  value: number
  label: string
  color: string
  bgColor: string
}

function MetricCard({ icon, value, label, color, bgColor }: MetricCardProps) {
  return (
    <div className={`rounded-lg p-4 ${bgColor}`}>
      <div className="flex items-center justify-between">
        <div className={color}>{icon}</div>
        <span className="text-2xl font-bold">{value}</span>
      </div>
      <p className="mt-1 text-sm text-muted-foreground">{label}</p>
    </div>
  )
}
