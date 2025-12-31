# E05: Dashboard Principal

**Épico:** Cards status + métricas + atividade
**Estimativa:** 8h
**Prioridade:** P0 (Bloqueante)
**Dependências:** E01, E02, E03, E04

---

## Objetivo

Criar dashboard principal com:
- Cards de status rápido (Julia, Rate Limit, Health, Mensagens)
- Funil de vendas do dia
- Lista de conversas ativas
- Feed de atividade recente
- Alertas ativos

---

## Wireframe Mobile

```
┌─────────────────────────────┐
│ [☰] Julia     [🔔] [👤]    │
├─────────────────────────────┤
│                             │
│  ┌─────────┐ ┌─────────┐   │
│  │ 🔵 JULIA │ │ 📨 RATE │   │
│  │  ATIVA   │ │ 15/20 h │   │
│  └─────────┘ └─────────┘   │
│                             │
│  ┌─────────┐ ┌─────────┐   │
│  │ ⚡ HEALTH│ │ 💬 HOJE │   │
│  │  100%   │ │   127   │   │
│  └─────────┘ └─────────┘   │
│                             │
│  FUNIL DE VENDAS            │
│  ─────────────────────────  │
│  Enviadas   ████████ 127    │
│  Respostas  ███░░░░░  28    │
│  Interesse  █░░░░░░░  12    │
│  Conversões ░░░░░░░░   3    │
│                             │
│  CONVERSAS ATIVAS (12)      │
│  ─────────────────────────  │
│  🟢 Dr. Carlos - 5min       │
│     "Pode me mandar..."     │
│  🟡 Dra. Ana - 12min        │
│     "Qual o valor?"         │
│  🔴 Dr. Pedro - HANDOFF     │
│     Pediu humano            │
│                             │
│  [Ver todas →]              │
│                             │
├─────────────────────────────┤
│ [🏠] [💬] [👥] [📊] [⚙️]   │
└─────────────────────────────┘
```

---

## Stories

### S05.1: Cards de Status

**Arquivo:** `app/(dashboard)/page.tsx`

```tsx
import { Suspense } from 'react'
import { StatusCards } from '@/components/dashboard/status-cards'
import { FunnelCard } from '@/components/dashboard/funnel-card'
import { ActiveConversations } from '@/components/dashboard/active-conversations'
import { ActivityFeed } from '@/components/dashboard/activity-feed'
import { AlertsList } from '@/components/dashboard/alerts-list'
import { Skeleton } from '@/components/ui/skeleton'

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Visão geral das operações de hoje
          </p>
        </div>
        {/* Date filter could go here */}
      </div>

      {/* Status Cards */}
      <Suspense fallback={<StatusCardsSkeleton />}>
        <StatusCards />
      </Suspense>

      {/* Main Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Funnel */}
        <Suspense fallback={<CardSkeleton className="h-[300px]" />}>
          <FunnelCard />
        </Suspense>

        {/* Active Conversations */}
        <Suspense fallback={<CardSkeleton className="h-[300px]" />}>
          <ActiveConversations />
        </Suspense>
      </div>

      {/* Alerts & Activity */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Alerts */}
        <Suspense fallback={<CardSkeleton className="h-[200px]" />}>
          <AlertsList />
        </Suspense>

        {/* Activity Feed */}
        <Suspense fallback={<CardSkeleton className="h-[200px]" />}>
          <ActivityFeed />
        </Suspense>
      </div>
    </div>
  )
}

function StatusCardsSkeleton() {
  return (
    <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
      {[...Array(4)].map((_, i) => (
        <Skeleton key={i} className="h-24" />
      ))}
    </div>
  )
}

function CardSkeleton({ className }: { className?: string }) {
  return <Skeleton className={className} />
}
```

**Arquivo:** `components/dashboard/status-cards.tsx`

```tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { api } from '@/lib/api/client'
import {
  Activity,
  MessageSquare,
  Zap,
  TrendingUp,
} from 'lucide-react'

interface DashboardStatus {
  julia: {
    status: 'ativo' | 'pausado'
    motivo?: string
  }
  rate_limit: {
    hora_atual: number
    hora_limite: number
    dia_atual: number
    dia_limite: number
    proximo_slot_segundos: number
  }
  health: {
    score: number
    circuits: {
      evolution: 'closed' | 'open' | 'half_open'
      claude: 'closed' | 'open' | 'half_open'
      supabase: 'closed' | 'open' | 'half_open'
    }
  }
  mensagens_hoje: {
    enviadas: number
    recebidas: number
    variacao_percentual: number
  }
}

async function getStatus(): Promise<DashboardStatus> {
  return api.get('/api/v1/dashboard/status')
}

export async function StatusCards() {
  const status = await getStatus()

  const juliaActive = status.julia.status === 'ativo'
  const healthGood = status.health.score === 100

  return (
    <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
      {/* Julia Status */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Julia</CardTitle>
          <Activity className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2">
            <Badge variant={juliaActive ? 'default' : 'destructive'}>
              <span
                className={`mr-1.5 h-2 w-2 rounded-full ${
                  juliaActive ? 'bg-green-400 animate-pulse' : 'bg-red-400'
                }`}
              />
              {juliaActive ? 'Ativa' : 'Pausada'}
            </Badge>
          </div>
          {!juliaActive && status.julia.motivo && (
            <p className="text-xs text-muted-foreground mt-1 truncate">
              {status.julia.motivo}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Rate Limit */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Rate Limit</CardTitle>
          <Zap className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {status.rate_limit.hora_atual}/{status.rate_limit.hora_limite}
            <span className="text-sm font-normal text-muted-foreground">/h</span>
          </div>
          <div className="flex items-center gap-2 mt-1">
            <div className="flex-1 h-1.5 bg-secondary rounded-full overflow-hidden">
              <div
                className="h-full bg-primary transition-all"
                style={{
                  width: `${(status.rate_limit.hora_atual / status.rate_limit.hora_limite) * 100}%`,
                }}
              />
            </div>
            <span className="text-xs text-muted-foreground">
              {status.rate_limit.dia_atual}/{status.rate_limit.dia_limite}/d
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Health */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Saúde</CardTitle>
          <div className="flex gap-0.5">
            {Object.values(status.health.circuits).map((circuit, i) => (
              <span
                key={i}
                className={`h-2 w-2 rounded-full ${
                  circuit === 'closed'
                    ? 'bg-green-500'
                    : circuit === 'open'
                    ? 'bg-red-500'
                    : 'bg-yellow-500'
                }`}
              />
            ))}
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {status.health.score}%
          </div>
          <p className="text-xs text-muted-foreground">
            {healthGood ? 'Todos sistemas OK' : 'Verificar circuits'}
          </p>
        </CardContent>
      </Card>

      {/* Messages Today */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Mensagens Hoje</CardTitle>
          <MessageSquare className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {status.mensagens_hoje.enviadas}
          </div>
          <div className="flex items-center gap-1 text-xs">
            <TrendingUp
              className={`h-3 w-3 ${
                status.mensagens_hoje.variacao_percentual >= 0
                  ? 'text-green-500'
                  : 'text-red-500'
              }`}
            />
            <span
              className={
                status.mensagens_hoje.variacao_percentual >= 0
                  ? 'text-green-500'
                  : 'text-red-500'
              }
            >
              {status.mensagens_hoje.variacao_percentual >= 0 ? '+' : ''}
              {status.mensagens_hoje.variacao_percentual}%
            </span>
            <span className="text-muted-foreground">vs ontem</span>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
```

**DoD:**
- [ ] 4 cards de status
- [ ] Dados em tempo real
- [ ] Indicadores visuais claros
- [ ] Responsivo (2 cols mobile, 4 desktop)

---

### S05.2: Funil de Vendas

**Arquivo:** `components/dashboard/funnel-card.tsx`

```tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { api } from '@/lib/api/client'

interface FunnelData {
  enviadas: number
  respostas: number
  interesse: number
  conversoes: number
  taxa_resposta: number
  taxa_conversao: number
  meta_conversao: number
}

async function getFunnel(): Promise<FunnelData> {
  return api.get('/api/v1/dashboard/metrics/funnel')
}

export async function FunnelCard() {
  const funnel = await getFunnel()

  const stages = [
    {
      label: 'Enviadas',
      value: funnel.enviadas,
      percentage: 100,
      color: 'bg-blue-500',
    },
    {
      label: 'Respostas',
      value: funnel.respostas,
      percentage: (funnel.respostas / funnel.enviadas) * 100,
      color: 'bg-emerald-500',
    },
    {
      label: 'Interesse',
      value: funnel.interesse,
      percentage: (funnel.interesse / funnel.enviadas) * 100,
      color: 'bg-amber-500',
    },
    {
      label: 'Conversões',
      value: funnel.conversoes,
      percentage: (funnel.conversoes / funnel.enviadas) * 100,
      color: 'bg-purple-500',
    },
  ]

  const atMeta = funnel.taxa_conversao >= funnel.meta_conversao

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Funil de Vendas</span>
          <span className="text-sm font-normal text-muted-foreground">
            Hoje
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {stages.map((stage, i) => (
          <div key={stage.label} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">{stage.label}</span>
              <span className="text-muted-foreground">
                {stage.value}
                {i > 0 && (
                  <span className="ml-1">
                    ({stage.percentage.toFixed(1)}%)
                  </span>
                )}
              </span>
            </div>
            <div className="h-2 bg-secondary rounded-full overflow-hidden">
              <div
                className={`h-full ${stage.color} transition-all`}
                style={{ width: `${stage.percentage}%` }}
              />
            </div>
          </div>
        ))}

        {/* Summary */}
        <div className="pt-4 border-t flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">Taxa End-to-End</p>
            <p className="text-2xl font-bold">
              {funnel.taxa_conversao.toFixed(1)}%
            </p>
          </div>
          <div className="text-right">
            <p className="text-sm text-muted-foreground">Meta</p>
            <p
              className={`text-lg font-semibold ${
                atMeta ? 'text-green-500' : 'text-amber-500'
              }`}
            >
              {funnel.meta_conversao}%
              {atMeta ? ' ✓' : ' ⚠️'}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
```

**DoD:**
- [ ] 4 estágios do funil
- [ ] Barras de progresso
- [ ] Percentuais calculados
- [ ] Indicador de meta

---

### S05.3: Conversas Ativas

**Arquivo:** `components/dashboard/active-conversations.tsx`

```tsx
import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { api } from '@/lib/api/client'
import { formatDistanceToNow } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { ArrowRight } from 'lucide-react'

interface Conversation {
  id: string
  cliente: {
    id: string
    nome: string
    especialidade: string
  }
  status: 'active' | 'escalated' | 'waiting'
  controlled_by: 'ai' | 'human'
  ultima_mensagem: {
    conteudo: string
    created_at: string
    origem: 'medico' | 'julia'
  }
}

interface ConversationsData {
  total: number
  conversas: Conversation[]
}

async function getActiveConversations(): Promise<ConversationsData> {
  return api.get('/api/v1/dashboard/conversations', {
    params: { status: 'active', limit: 5 },
  })
}

export async function ActiveConversations() {
  const data = await getActiveConversations()

  const getStatusColor = (conv: Conversation) => {
    if (conv.controlled_by === 'human') return 'text-red-500'
    if (conv.status === 'waiting') return 'text-amber-500'
    return 'text-green-500'
  }

  const getStatusLabel = (conv: Conversation) => {
    if (conv.controlled_by === 'human') return 'HANDOFF'
    if (conv.status === 'waiting') return 'Aguardando'
    return 'Ativa'
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <span>Conversas Ativas</span>
          <Badge variant="secondary">{data.total}</Badge>
        </CardTitle>
        <Button variant="ghost" size="sm" asChild>
          <Link href="/conversas">
            Ver todas
            <ArrowRight className="ml-1 h-4 w-4" />
          </Link>
        </Button>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[240px] pr-4">
          <div className="space-y-4">
            {data.conversas.map((conv) => (
              <Link
                key={conv.id}
                href={`/conversas/${conv.id}`}
                className="block"
              >
                <div className="flex items-start gap-3 p-3 rounded-lg hover:bg-accent transition-colors">
                  {/* Status indicator */}
                  <span
                    className={`mt-1.5 h-2 w-2 rounded-full ${
                      conv.controlled_by === 'human'
                        ? 'bg-red-500'
                        : conv.status === 'waiting'
                        ? 'bg-amber-500'
                        : 'bg-green-500'
                    }`}
                  />

                  <div className="flex-1 min-w-0">
                    {/* Header */}
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-medium truncate">
                        {conv.cliente.nome}
                      </p>
                      <span className="text-xs text-muted-foreground whitespace-nowrap">
                        {formatDistanceToNow(
                          new Date(conv.ultima_mensagem.created_at),
                          { addSuffix: false, locale: ptBR }
                        )}
                      </span>
                    </div>

                    {/* Specialty & Status */}
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span>{conv.cliente.especialidade}</span>
                      <span>•</span>
                      <span className={getStatusColor(conv)}>
                        {getStatusLabel(conv)}
                      </span>
                    </div>

                    {/* Last message */}
                    <p className="text-sm text-muted-foreground mt-1 line-clamp-1">
                      {conv.ultima_mensagem.origem === 'julia' && 'Julia: '}
                      {conv.ultima_mensagem.conteudo}
                    </p>
                  </div>
                </div>
              </Link>
            ))}

            {data.conversas.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                Nenhuma conversa ativa no momento
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
```

**DoD:**
- [ ] Lista de conversas ativas
- [ ] Indicador de status (cor)
- [ ] Última mensagem truncada
- [ ] Link para detalhes
- [ ] ScrollArea para overflow

---

### S05.4: Feed de Atividade

**Arquivo:** `components/dashboard/activity-feed.tsx`

```tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { api } from '@/lib/api/client'
import { formatDistanceToNow } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import {
  MessageSquare,
  CheckCircle,
  AlertTriangle,
  UserPlus,
  Send,
  Megaphone,
} from 'lucide-react'

interface ActivityItem {
  id: string
  tipo: 'mensagem' | 'plantao_confirmado' | 'handoff' | 'novo_medico' | 'campanha' | 'resposta'
  descricao: string
  created_at: string
  metadata?: Record<string, any>
}

const ACTIVITY_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  mensagem: Send,
  plantao_confirmado: CheckCircle,
  handoff: AlertTriangle,
  novo_medico: UserPlus,
  campanha: Megaphone,
  resposta: MessageSquare,
}

const ACTIVITY_COLORS: Record<string, string> = {
  mensagem: 'text-blue-500 bg-blue-50',
  plantao_confirmado: 'text-green-500 bg-green-50',
  handoff: 'text-red-500 bg-red-50',
  novo_medico: 'text-purple-500 bg-purple-50',
  campanha: 'text-amber-500 bg-amber-50',
  resposta: 'text-emerald-500 bg-emerald-50',
}

async function getActivity(): Promise<ActivityItem[]> {
  return api.get('/api/v1/dashboard/activity', { params: { limit: 10 } })
}

export async function ActivityFeed() {
  const activities = await getActivity()

  return (
    <Card>
      <CardHeader>
        <CardTitle>Atividade Recente</CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[200px] pr-4">
          <div className="space-y-4">
            {activities.map((activity) => {
              const Icon = ACTIVITY_ICONS[activity.tipo] || MessageSquare
              const colorClass = ACTIVITY_COLORS[activity.tipo] || 'text-gray-500 bg-gray-50'

              return (
                <div key={activity.id} className="flex items-start gap-3">
                  <div className={`p-1.5 rounded-full ${colorClass}`}>
                    <Icon className="h-3.5 w-3.5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm">{activity.descricao}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatDistanceToNow(new Date(activity.created_at), {
                        addSuffix: true,
                        locale: ptBR,
                      })}
                    </p>
                  </div>
                </div>
              )
            })}

            {activities.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                Nenhuma atividade recente
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
```

**DoD:**
- [ ] Feed de atividades
- [ ] Ícones por tipo
- [ ] Cores diferenciadas
- [ ] Timestamps relativos

---

### S05.5: Alertas Ativos

**Arquivo:** `components/dashboard/alerts-list.tsx`

```tsx
import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { api } from '@/lib/api/client'
import { AlertTriangle, AlertCircle, Info, ArrowRight } from 'lucide-react'

interface AlertItem {
  id: string
  tipo: 'critical' | 'warning' | 'info'
  titulo: string
  mensagem: string
  action_url?: string
  created_at: string
}

const ALERT_ICONS = {
  critical: AlertTriangle,
  warning: AlertCircle,
  info: Info,
}

const ALERT_VARIANTS = {
  critical: 'destructive' as const,
  warning: 'default' as const,
  info: 'default' as const,
}

async function getAlerts(): Promise<AlertItem[]> {
  return api.get('/api/v1/dashboard/alerts', { params: { resolved: false, limit: 3 } })
}

export async function AlertsList() {
  const alerts = await getAlerts()

  if (alerts.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Alertas</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-6 text-muted-foreground">
            <Info className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>Nenhum alerta ativo</p>
            <p className="text-sm">Tudo funcionando normalmente</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <span>Alertas</span>
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-destructive text-destructive-foreground text-xs">
            {alerts.length}
          </span>
        </CardTitle>
        <Button variant="ghost" size="sm" asChild>
          <Link href="/sistema/alertas">
            Ver todos
            <ArrowRight className="ml-1 h-4 w-4" />
          </Link>
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        {alerts.map((alert) => {
          const Icon = ALERT_ICONS[alert.tipo]

          return (
            <Alert key={alert.id} variant={ALERT_VARIANTS[alert.tipo]}>
              <Icon className="h-4 w-4" />
              <AlertTitle className="text-sm">{alert.titulo}</AlertTitle>
              <AlertDescription className="text-xs">
                {alert.mensagem}
                {alert.action_url && (
                  <Link
                    href={alert.action_url}
                    className="ml-2 underline hover:no-underline"
                  >
                    Ver detalhes
                  </Link>
                )}
              </AlertDescription>
            </Alert>
          )
        })}
      </CardContent>
    </Card>
  )
}
```

**DoD:**
- [ ] Lista de alertas ativos
- [ ] Cores por severidade
- [ ] Links de ação
- [ ] Estado vazio amigável

---

## API Backend

**Arquivo:** `app/api/routes/dashboard/status.py`

```python
from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
from typing import Optional

from app.services.supabase import supabase
from app.services.rate_limiter import rate_limiter
from app.services.circuit_breaker import (
    circuit_evolution,
    circuit_claude,
    circuit_supabase,
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/status")
async def get_dashboard_status(user=Depends(get_current_user)):
    """Retorna status geral do sistema para o dashboard."""

    # Julia status
    julia_result = supabase.table("julia_status").select("*").order(
        "created_at", desc=True
    ).limit(1).execute()

    julia_status = julia_result.data[0] if julia_result.data else {
        "status": "ativo",
        "motivo": None
    }

    # Rate limit
    stats = await rate_limiter.obter_estatisticas()

    # Mensagens hoje
    hoje = datetime.now().date()
    msgs_result = supabase.table("interacoes").select(
        "id", count="exact"
    ).gte(
        "created_at", hoje.isoformat()
    ).eq("origem", "julia").execute()

    msgs_hoje = msgs_result.count or 0

    # Mensagens ontem (para comparação)
    ontem = hoje - timedelta(days=1)
    msgs_ontem_result = supabase.table("interacoes").select(
        "id", count="exact"
    ).gte(
        "created_at", ontem.isoformat()
    ).lt(
        "created_at", hoje.isoformat()
    ).eq("origem", "julia").execute()

    msgs_ontem = msgs_ontem_result.count or 1  # Evitar divisão por zero
    variacao = ((msgs_hoje - msgs_ontem) / msgs_ontem) * 100

    # Health score
    circuits = {
        "evolution": circuit_evolution.estado.value,
        "claude": circuit_claude.estado.value,
        "supabase": circuit_supabase.estado.value,
    }

    circuits_ok = sum(1 for c in circuits.values() if c == "closed")
    health_score = int((circuits_ok / len(circuits)) * 100)

    return {
        "julia": {
            "status": julia_status["status"],
            "motivo": julia_status.get("motivo"),
        },
        "rate_limit": {
            "hora_atual": stats.get("mensagens_hora", 0),
            "hora_limite": 20,
            "dia_atual": stats.get("mensagens_dia", 0),
            "dia_limite": 100,
            "proximo_slot_segundos": stats.get("proximo_slot", 0),
        },
        "health": {
            "score": health_score,
            "circuits": circuits,
        },
        "mensagens_hoje": {
            "enviadas": msgs_hoje,
            "recebidas": 0,  # TODO: contar recebidas
            "variacao_percentual": round(variacao, 1),
        },
    }
```

---

## Checklist Final

- [ ] Page dashboard criada
- [ ] 4 status cards funcionando
- [ ] Funil de vendas com dados reais
- [ ] Lista de conversas ativas
- [ ] Feed de atividade
- [ ] Alertas ativos
- [ ] Loading states (Skeleton)
- [ ] Responsivo em todos breakpoints
- [ ] APIs backend funcionando
- [ ] Refresh automático (React Query)
