# E14: Preview Pool de Chips

**Épico:** Visualização do Pool de Números WhatsApp
**Estimativa:** 4h
**Prioridade:** P2 (Importante)
**Dependências:** E01, E02, E04, Sprint 25/26 (Chip Pool)

---

## Objetivo

Implementar visualização do pool de chips WhatsApp:
- Lista de chips com status
- Trust score de cada chip
- Métricas de uso
- Preview (read-only na Sprint 28)

> **Nota:** Esta sprint é preview apenas. O gerenciamento completo
> será implementado após Sprint 25/26 estabilizarem.

---

## Estrutura de Arquivos

```
app/(dashboard)/chips/
├── page.tsx                   # Lista de chips
├── components/
│   ├── chip-list.tsx
│   ├── chip-card.tsx
│   ├── chip-stats.tsx
│   └── trust-score-badge.tsx
```

---

## Stories

### S14.1: Lista de Chips

**Arquivo:** `app/(dashboard)/chips/page.tsx`

```typescript
'use client'

import { useQuery } from '@tanstack/react-query'
import { Smartphone, RefreshCw, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { api } from '@/lib/api/client'
import { ChipList } from './components/chip-list'
import { ChipStats } from './components/chip-stats'

export default function ChipsPage() {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['chips'],
    queryFn: () => api.get('/dashboard/chips'),
    refetchInterval: 60000 // Refresh a cada minuto
  })

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton className="h-32" />
        <div className="grid gap-4 md:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-40" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 md:p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Smartphone className="h-6 w-6 text-primary" />
          <div>
            <h1 className="text-2xl font-bold">Pool de Chips</h1>
            <p className="text-muted-foreground">
              {data?.chips?.length || 0} chips no pool
            </p>
          </div>
        </div>
        <Button variant="outline" size="icon" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* Preview Alert */}
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          <strong>Modo Preview:</strong> Visualização apenas. O gerenciamento completo
          de chips será disponibilizado em uma sprint futura.
        </AlertDescription>
      </Alert>

      {/* Stats Overview */}
      <ChipStats stats={data?.stats} />

      {/* Lista de Chips */}
      <ChipList chips={data?.chips || []} />
    </div>
  )
}
```

---

### S14.2: Card de Chip

**Arquivo:** `app/(dashboard)/chips/components/chip-card.tsx`

```typescript
'use client'

import { Smartphone, Activity, MessageCircle, AlertTriangle } from 'lucide-react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'
import { TrustScoreBadge } from './trust-score-badge'

interface Chip {
  id: string
  phone_number: string
  instance_name: string
  status: 'active' | 'warming' | 'cooldown' | 'banned' | 'inactive'
  trust_score: number
  messages_today: number
  messages_limit: number
  last_message_at?: string
  health_status: 'healthy' | 'degraded' | 'critical'
}

interface Props {
  chip: Chip
}

export function ChipCard({ chip }: Props) {
  const getStatusBadge = () => {
    switch (chip.status) {
      case 'active':
        return <Badge className="bg-green-100 text-green-800">Ativo</Badge>
      case 'warming':
        return <Badge className="bg-blue-100 text-blue-800">Aquecendo</Badge>
      case 'cooldown':
        return <Badge className="bg-yellow-100 text-yellow-800">Cooldown</Badge>
      case 'banned':
        return <Badge variant="destructive">Banido</Badge>
      case 'inactive':
        return <Badge variant="secondary">Inativo</Badge>
    }
  }

  const usagePercent = (chip.messages_today / chip.messages_limit) * 100

  return (
    <Card className={cn(
      chip.status === 'banned' && 'border-destructive/50',
      chip.health_status === 'critical' && 'border-yellow-500/50'
    )}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <Smartphone className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="font-medium font-mono text-sm">
                {chip.phone_number}
              </p>
              <p className="text-xs text-muted-foreground">
                {chip.instance_name}
              </p>
            </div>
          </div>
          {getStatusBadge()}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Trust Score */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Trust Score</span>
          <TrustScoreBadge score={chip.trust_score} />
        </div>

        {/* Usage */}
        <div className="space-y-1">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Uso hoje</span>
            <span className="font-medium">
              {chip.messages_today} / {chip.messages_limit}
            </span>
          </div>
          <Progress
            value={usagePercent}
            className="h-2"
            indicatorClassName={cn(
              usagePercent >= 90 ? 'bg-red-500' :
              usagePercent >= 70 ? 'bg-yellow-500' :
              'bg-green-500'
            )}
          />
        </div>

        {/* Health */}
        {chip.health_status !== 'healthy' && (
          <div className="flex items-center gap-2 text-sm text-yellow-600">
            <AlertTriangle className="h-4 w-4" />
            <span>
              {chip.health_status === 'degraded' ? 'Performance reduzida' : 'Atenção necessária'}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
```

---

### S14.3: Trust Score Badge

**Arquivo:** `app/(dashboard)/chips/components/trust-score-badge.tsx`

```typescript
'use client'

import { cn } from '@/lib/utils'

interface Props {
  score: number
}

export function TrustScoreBadge({ score }: Props) {
  const getColor = () => {
    if (score >= 80) return 'bg-green-100 text-green-800'
    if (score >= 60) return 'bg-blue-100 text-blue-800'
    if (score >= 40) return 'bg-yellow-100 text-yellow-800'
    return 'bg-red-100 text-red-800'
  }

  const getLabel = () => {
    if (score >= 80) return 'Excelente'
    if (score >= 60) return 'Bom'
    if (score >= 40) return 'Regular'
    return 'Baixo'
  }

  return (
    <div className={cn('px-2 py-1 rounded text-xs font-medium', getColor())}>
      {score}% - {getLabel()}
    </div>
  )
}
```

---

### S14.4: Stats Overview

**Arquivo:** `app/(dashboard)/chips/components/chip-stats.tsx`

```typescript
'use client'

import { Smartphone, Activity, MessageCircle, AlertTriangle } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'

interface ChipStats {
  total: number
  active: number
  warming: number
  cooldown: number
  banned: number
  avg_trust_score: number
  messages_today: number
}

interface Props {
  stats?: ChipStats
}

export function ChipStats({ stats }: Props) {
  if (!stats) return null

  const cards = [
    {
      label: 'Chips Ativos',
      value: stats.active,
      total: stats.total,
      icon: Smartphone,
      color: 'text-green-600'
    },
    {
      label: 'Aquecendo',
      value: stats.warming,
      icon: Activity,
      color: 'text-blue-600'
    },
    {
      label: 'Mensagens Hoje',
      value: stats.messages_today,
      icon: MessageCircle,
      color: 'text-purple-600'
    },
    {
      label: 'Trust Score Médio',
      value: `${stats.avg_trust_score}%`,
      icon: Activity,
      color: 'text-yellow-600'
    }
  ]

  return (
    <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
      {cards.map((card, index) => (
        <Card key={index}>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2">
              <card.icon className={cn('h-5 w-5', card.color)} />
              <p className="text-sm text-muted-foreground">{card.label}</p>
            </div>
            <p className="text-2xl font-bold mt-2">
              {card.value}
              {card.total && (
                <span className="text-sm font-normal text-muted-foreground">
                  {' '}/ {card.total}
                </span>
              )}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
```

---

## Backend Endpoints

```python
# app/api/routes/dashboard/chips.py

@router.get("")
async def list_chips(user: CurrentUser):
    """Lista chips do pool com stats."""

    # Buscar chips
    chips_result = supabase.table("whatsapp_instances").select("*").execute()

    # Calcular stats
    chips = chips_result.data
    stats = {
        "total": len(chips),
        "active": len([c for c in chips if c["status"] == "active"]),
        "warming": len([c for c in chips if c["status"] == "warming"]),
        "cooldown": len([c for c in chips if c["status"] == "cooldown"]),
        "banned": len([c for c in chips if c["status"] == "banned"]),
        "avg_trust_score": sum(c.get("trust_score", 0) for c in chips) / len(chips) if chips else 0,
        "messages_today": sum(c.get("messages_today", 0) for c in chips)
    }

    return {
        "chips": chips,
        "stats": stats
    }
```

---

## Checklist Final

- [ ] Lista de chips com cards
- [ ] Trust score badge visual
- [ ] Status por chip
- [ ] Stats overview
- [ ] Alerta de modo preview
- [ ] Refresh automático
- [ ] Mobile responsivo
