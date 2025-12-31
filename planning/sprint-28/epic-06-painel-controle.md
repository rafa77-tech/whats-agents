# E06: Painel de Controle

**Épico:** Toggle Julia + Feature Flags + Rate Limit
**Estimativa:** 6h
**Prioridade:** P0 (Core)
**Dependências:** E01, E02, E04

---

## Objetivo

Implementar interface de controle operacional:
- Toggle on/off da Julia
- Pause temporário com timer
- Feature flags management
- Visualização e ajuste de rate limits
- Reset de circuit breakers

---

## Estrutura de Arquivos

```
app/(dashboard)/sistema/
├── page.tsx               # Página principal de controle
├── julia/
│   └── page.tsx           # Controle específico Julia
├── flags/
│   └── page.tsx           # Feature flags
└── components/
    ├── julia-toggle.tsx
    ├── julia-pause-dialog.tsx
    ├── rate-limit-card.tsx
    ├── circuit-breaker-card.tsx
    ├── feature-flag-item.tsx
    └── confirmation-dialog.tsx
```

---

## Stories

### S06.1: Julia Toggle Component

**Arquivo:** `app/(dashboard)/sistema/components/julia-toggle.tsx`

```typescript
'use client'

import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Power, Pause, Play, AlertTriangle } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useToast } from '@/components/ui/use-toast'
import { api } from '@/lib/api/client'
import { useAuth } from '@/hooks/use-auth'
import { JuliaPauseDialog } from './julia-pause-dialog'
import { ConfirmationDialog } from './confirmation-dialog'

interface JuliaStatus {
  is_active: boolean
  mode: 'auto' | 'paused' | 'maintenance'
  paused_until?: string
  pause_reason?: string
}

interface Props {
  status: JuliaStatus
}

export function JuliaToggle({ status }: Props) {
  const [showPauseDialog, setShowPauseDialog] = useState(false)
  const [showConfirmDialog, setShowConfirmDialog] = useState(false)
  const [pendingAction, setPendingAction] = useState<'on' | 'off' | null>(null)

  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { hasPermission } = useAuth()

  const canControl = hasPermission('operator')

  const toggleMutation = useMutation({
    mutationFn: async (active: boolean) => {
      return api.post('/dashboard/controls/julia/toggle', {
        active,
        reason: active ? null : 'Desligada via dashboard'
      })
    },
    onSuccess: (_, active) => {
      queryClient.invalidateQueries({ queryKey: ['dashboard-status'] })
      toast({
        title: active ? 'Julia ativada' : 'Julia desativada',
        description: active
          ? 'Julia voltou a responder automaticamente'
          : 'Julia está pausada. Mensagens não serão respondidas.',
        variant: active ? 'default' : 'destructive'
      })
    },
    onError: (error) => {
      toast({
        title: 'Erro',
        description: 'Não foi possível alterar o status da Julia',
        variant: 'destructive'
      })
    }
  })

  const handleToggleClick = (newState: boolean) => {
    if (!newState) {
      // Desligar requer confirmação
      setPendingAction('off')
      setShowConfirmDialog(true)
    } else {
      // Ligar pode ser direto
      toggleMutation.mutate(true)
    }
  }

  const confirmAction = () => {
    if (pendingAction === 'off') {
      toggleMutation.mutate(false)
    }
    setShowConfirmDialog(false)
    setPendingAction(null)
  }

  const getStatusBadge = () => {
    if (status.is_active) {
      return <Badge className="bg-green-500">Ativa</Badge>
    }
    if (status.mode === 'paused' && status.paused_until) {
      return <Badge variant="secondary">Pausada temporariamente</Badge>
    }
    return <Badge variant="destructive">Desativada</Badge>
  }

  const getPauseInfo = () => {
    if (!status.paused_until) return null

    const pausedUntil = new Date(status.paused_until)
    const now = new Date()
    const diffMs = pausedUntil.getTime() - now.getTime()

    if (diffMs <= 0) return null

    const diffMins = Math.ceil(diffMs / 60000)
    return `Volta em ${diffMins} min`
  }

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-full ${status.is_active ? 'bg-green-100' : 'bg-red-100'}`}>
                <Power className={`h-5 w-5 ${status.is_active ? 'text-green-600' : 'text-red-600'}`} />
              </div>
              <div>
                <CardTitle className="text-lg">Julia</CardTitle>
                <CardDescription>Controle do agente</CardDescription>
              </div>
            </div>
            {getStatusBadge()}
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Toggle principal */}
          <div className="flex items-center justify-between p-4 bg-muted rounded-lg">
            <div>
              <p className="font-medium">Status do Agente</p>
              <p className="text-sm text-muted-foreground">
                {status.is_active
                  ? 'Julia está respondendo automaticamente'
                  : 'Julia não está respondendo'}
              </p>
            </div>
            <Switch
              checked={status.is_active}
              onCheckedChange={handleToggleClick}
              disabled={!canControl || toggleMutation.isPending}
            />
          </div>

          {/* Info de pausa */}
          {status.pause_reason && (
            <div className="flex items-center gap-2 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg text-sm">
              <AlertTriangle className="h-4 w-4 text-yellow-600" />
              <div>
                <p className="font-medium">Motivo: {status.pause_reason}</p>
                {getPauseInfo() && (
                  <p className="text-muted-foreground">{getPauseInfo()}</p>
                )}
              </div>
            </div>
          )}

          {/* Ações */}
          <div className="flex gap-2">
            <Button
              variant="outline"
              className="flex-1"
              onClick={() => setShowPauseDialog(true)}
              disabled={!canControl || !status.is_active}
            >
              <Pause className="h-4 w-4 mr-2" />
              Pausar
            </Button>

            {!status.is_active && (
              <Button
                className="flex-1"
                onClick={() => toggleMutation.mutate(true)}
                disabled={!canControl || toggleMutation.isPending}
              >
                <Play className="h-4 w-4 mr-2" />
                Reativar
              </Button>
            )}
          </div>

          {!canControl && (
            <p className="text-xs text-muted-foreground text-center">
              Você precisa de permissão de Operador para controlar a Julia
            </p>
          )}
        </CardContent>
      </Card>

      {/* Dialogs */}
      <JuliaPauseDialog
        open={showPauseDialog}
        onOpenChange={setShowPauseDialog}
      />

      <ConfirmationDialog
        open={showConfirmDialog}
        onOpenChange={setShowConfirmDialog}
        title="Desativar Julia?"
        description="A Julia vai parar de responder todas as mensagens. Médicos esperando resposta podem ficar sem atendimento."
        confirmText="Sim, desativar"
        variant="destructive"
        onConfirm={confirmAction}
      />
    </>
  )
}
```

**DoD:**
- [ ] Toggle com confirmação para desativar
- [ ] Mostra status atual com badge
- [ ] Mostra motivo da pausa se houver
- [ ] Desabilitado para viewers

---

### S06.2: Julia Pause Dialog

**Arquivo:** `app/(dashboard)/sistema/components/julia-pause-dialog.tsx`

```typescript
'use client'

import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Clock } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { useToast } from '@/components/ui/use-toast'
import { api } from '@/lib/api/client'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const PRESET_DURATIONS = [
  { label: '15 min', value: 15 },
  { label: '30 min', value: 30 },
  { label: '1 hora', value: 60 },
  { label: '2 horas', value: 120 },
]

export function JuliaPauseDialog({ open, onOpenChange }: Props) {
  const [duration, setDuration] = useState(30)
  const [reason, setReason] = useState('')

  const queryClient = useQueryClient()
  const { toast } = useToast()

  const pauseMutation = useMutation({
    mutationFn: async () => {
      return api.post('/dashboard/controls/julia/pause', {
        duration_minutes: duration,
        reason: reason || 'Pausa via dashboard'
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard-status'] })
      toast({
        title: 'Julia pausada',
        description: `Julia voltará automaticamente em ${duration} minutos`,
      })
      onOpenChange(false)
      setReason('')
    },
    onError: () => {
      toast({
        title: 'Erro',
        description: 'Não foi possível pausar a Julia',
        variant: 'destructive'
      })
    }
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Pausar Julia
          </DialogTitle>
          <DialogDescription>
            Julia voltará automaticamente após o tempo definido
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Presets */}
          <div className="space-y-2">
            <Label>Duração rápida</Label>
            <div className="flex gap-2">
              {PRESET_DURATIONS.map((preset) => (
                <Button
                  key={preset.value}
                  variant={duration === preset.value ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setDuration(preset.value)}
                >
                  {preset.label}
                </Button>
              ))}
            </div>
          </div>

          {/* Slider customizado */}
          <div className="space-y-2">
            <div className="flex justify-between">
              <Label>Duração customizada</Label>
              <span className="text-sm font-medium">{duration} min</span>
            </div>
            <Slider
              value={[duration]}
              onValueChange={(values) => setDuration(values[0])}
              min={5}
              max={240}
              step={5}
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>5 min</span>
              <span>4 horas</span>
            </div>
          </div>

          {/* Motivo */}
          <div className="space-y-2">
            <Label htmlFor="reason">Motivo (opcional)</Label>
            <Input
              id="reason"
              placeholder="Ex: Reunião de equipe"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button
            onClick={() => pauseMutation.mutate()}
            disabled={pauseMutation.isPending}
          >
            {pauseMutation.isPending ? 'Pausando...' : `Pausar por ${duration} min`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
```

**DoD:**
- [ ] Presets de tempo rápido
- [ ] Slider para tempo customizado
- [ ] Campo de motivo opcional
- [ ] Feedback visual do tempo

---

### S06.3: Rate Limit Card

**Arquivo:** `app/(dashboard)/sistema/components/rate-limit-card.tsx`

```typescript
'use client'

import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Gauge, Settings } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useToast } from '@/components/ui/use-toast'
import { api } from '@/lib/api/client'
import { useAuth } from '@/hooks/use-auth'

interface RateLimitStatus {
  messages_hour: number
  messages_day: number
  limit_hour: number
  limit_day: number
  percent_hour: number
  percent_day: number
}

interface Props {
  status: RateLimitStatus
}

export function RateLimitCard({ status }: Props) {
  const [showSettings, setShowSettings] = useState(false)
  const [newLimitHour, setNewLimitHour] = useState(status.limit_hour)
  const [newLimitDay, setNewLimitDay] = useState(status.limit_day)

  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { hasPermission } = useAuth()

  const canEdit = hasPermission('admin')

  const updateMutation = useMutation({
    mutationFn: async () => {
      return api.put('/dashboard/controls/rate-limit', {
        messages_per_hour: newLimitHour,
        messages_per_day: newLimitDay
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard-status'] })
      toast({
        title: 'Limites atualizados',
        description: `Novo limite: ${newLimitHour}/hora, ${newLimitDay}/dia`
      })
      setShowSettings(false)
    },
    onError: () => {
      toast({
        title: 'Erro',
        description: 'Não foi possível atualizar os limites',
        variant: 'destructive'
      })
    }
  })

  const getProgressColor = (percent: number) => {
    if (percent >= 90) return 'bg-red-500'
    if (percent >= 70) return 'bg-yellow-500'
    return 'bg-green-500'
  }

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-full bg-blue-100">
                <Gauge className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <CardTitle className="text-lg">Rate Limit</CardTitle>
                <CardDescription>Controle de envios</CardDescription>
              </div>
            </div>
            {canEdit && (
              <Button variant="ghost" size="icon" onClick={() => setShowSettings(true)}>
                <Settings className="h-4 w-4" />
              </Button>
            )}
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Por hora */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Esta hora</span>
              <span className="font-medium">
                {status.messages_hour} / {status.limit_hour}
              </span>
            </div>
            <Progress
              value={status.percent_hour}
              className="h-2"
              indicatorClassName={getProgressColor(status.percent_hour)}
            />
          </div>

          {/* Por dia */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Hoje</span>
              <span className="font-medium">
                {status.messages_day} / {status.limit_day}
              </span>
            </div>
            <Progress
              value={status.percent_day}
              className="h-2"
              indicatorClassName={getProgressColor(status.percent_day)}
            />
          </div>

          {/* Alertas */}
          {status.percent_hour >= 90 && (
            <div className="p-2 bg-red-50 dark:bg-red-900/20 rounded text-sm text-red-600">
              Limite horário quase atingido!
            </div>
          )}
          {status.percent_day >= 90 && (
            <div className="p-2 bg-red-50 dark:bg-red-900/20 rounded text-sm text-red-600">
              Limite diário quase atingido!
            </div>
          )}
        </CardContent>
      </Card>

      {/* Settings Dialog */}
      <Dialog open={showSettings} onOpenChange={setShowSettings}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Configurar Rate Limit</DialogTitle>
            <DialogDescription>
              Ajuste os limites de mensagens. Valores muito altos podem causar ban.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="limit-hour">Limite por hora</Label>
              <Input
                id="limit-hour"
                type="number"
                min={1}
                max={50}
                value={newLimitHour}
                onChange={(e) => setNewLimitHour(parseInt(e.target.value))}
              />
              <p className="text-xs text-muted-foreground">
                Recomendado: 20. Máximo seguro: 50
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="limit-day">Limite por dia</Label>
              <Input
                id="limit-day"
                type="number"
                min={10}
                max={200}
                value={newLimitDay}
                onChange={(e) => setNewLimitDay(parseInt(e.target.value))}
              />
              <p className="text-xs text-muted-foreground">
                Recomendado: 100. Máximo seguro: 200
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSettings(false)}>
              Cancelar
            </Button>
            <Button
              onClick={() => updateMutation.mutate()}
              disabled={updateMutation.isPending}
            >
              Salvar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
```

**DoD:**
- [ ] Mostra consumo atual hora/dia
- [ ] Progress bars com cores
- [ ] Alertas quando próximo do limite
- [ ] Dialog de configuração (admin only)

---

### S06.4: Circuit Breaker Card

**Arquivo:** `app/(dashboard)/sistema/components/circuit-breaker-card.tsx`

```typescript
'use client'

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Activity, RefreshCcw } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useToast } from '@/components/ui/use-toast'
import { api } from '@/lib/api/client'
import { useAuth } from '@/hooks/use-auth'

interface CircuitStatus {
  evolution: string
  claude: string
  supabase: string
}

interface Props {
  status: CircuitStatus
}

const SERVICES = [
  { key: 'evolution', label: 'Evolution API', description: 'WhatsApp' },
  { key: 'claude', label: 'Claude AI', description: 'LLM' },
  { key: 'supabase', label: 'Supabase', description: 'Database' },
]

export function CircuitBreakerCard({ status }: Props) {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { hasPermission } = useAuth()

  const canReset = hasPermission('manager')

  const resetMutation = useMutation({
    mutationFn: async (service: string) => {
      return api.post(`/dashboard/controls/circuit/${service}/reset`)
    },
    onSuccess: (_, service) => {
      queryClient.invalidateQueries({ queryKey: ['dashboard-status'] })
      toast({
        title: 'Circuit resetado',
        description: `${service} foi resetado para estado fechado`
      })
    },
    onError: () => {
      toast({
        title: 'Erro',
        description: 'Não foi possível resetar o circuit',
        variant: 'destructive'
      })
    }
  })

  const getStatusBadge = (state: string) => {
    switch (state) {
      case 'closed':
        return <Badge className="bg-green-500">Fechado</Badge>
      case 'open':
        return <Badge variant="destructive">Aberto</Badge>
      case 'half-open':
        return <Badge variant="secondary">Half-Open</Badge>
      default:
        return <Badge variant="outline">Desconhecido</Badge>
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-full bg-purple-100">
            <Activity className="h-5 w-5 text-purple-600" />
          </div>
          <div>
            <CardTitle className="text-lg">Circuit Breakers</CardTitle>
            <CardDescription>Status das integrações</CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <div className="space-y-3">
          {SERVICES.map((service) => {
            const state = status[service.key as keyof CircuitStatus]
            const isOpen = state === 'open'

            return (
              <div
                key={service.key}
                className="flex items-center justify-between p-3 bg-muted rounded-lg"
              >
                <div>
                  <p className="font-medium">{service.label}</p>
                  <p className="text-xs text-muted-foreground">{service.description}</p>
                </div>
                <div className="flex items-center gap-2">
                  {getStatusBadge(state)}
                  {isOpen && canReset && (
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => resetMutation.mutate(service.key)}
                      disabled={resetMutation.isPending}
                    >
                      <RefreshCcw className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </div>
            )
          })}
        </div>

        {Object.values(status).some(s => s === 'open') && (
          <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 rounded text-sm">
            <p className="font-medium text-red-600">Atenção!</p>
            <p className="text-muted-foreground">
              Há circuits abertos. Algumas funcionalidades podem estar indisponíveis.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
```

**DoD:**
- [ ] Lista os 3 serviços principais
- [ ] Badge com cor por estado
- [ ] Botão reset para circuits abertos
- [ ] Alerta quando há circuits abertos

---

### S06.5: Feature Flags Page

**Arquivo:** `app/(dashboard)/sistema/flags/page.tsx`

```typescript
'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Flag, Search } from 'lucide-react'
import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { useToast } from '@/components/ui/use-toast'
import { api } from '@/lib/api/client'
import { useAuth } from '@/hooks/use-auth'
import { RequireRole } from '@/components/providers/auth-provider'

interface FeatureFlag {
  id: string
  name: string
  description: string
  enabled: boolean
  category: string
  updated_at: string
  updated_by?: string
}

export default function FeatureFlagsPage() {
  const [search, setSearch] = useState('')

  const { hasPermission } = useAuth()
  const canEdit = hasPermission('manager')

  const queryClient = useQueryClient()
  const { toast } = useToast()

  const { data, isLoading } = useQuery({
    queryKey: ['feature-flags'],
    queryFn: () => api.get<{ flags: FeatureFlag[] }>('/dashboard/controls/flags')
  })

  const updateMutation = useMutation({
    mutationFn: async ({ name, enabled }: { name: string; enabled: boolean }) => {
      return api.put(`/dashboard/controls/flags/${name}`, { enabled })
    },
    onSuccess: (_, { name, enabled }) => {
      queryClient.invalidateQueries({ queryKey: ['feature-flags'] })
      toast({
        title: 'Flag atualizada',
        description: `${name} está agora ${enabled ? 'ativada' : 'desativada'}`
      })
    },
    onError: () => {
      toast({
        title: 'Erro',
        description: 'Não foi possível atualizar a flag',
        variant: 'destructive'
      })
    }
  })

  const flags = data?.flags || []
  const filteredFlags = flags.filter(
    f => f.name.toLowerCase().includes(search.toLowerCase()) ||
         f.description.toLowerCase().includes(search.toLowerCase())
  )

  // Agrupar por categoria
  const groupedFlags = filteredFlags.reduce((acc, flag) => {
    const cat = flag.category || 'Geral'
    if (!acc[cat]) acc[cat] = []
    acc[cat].push(flag)
    return acc
  }, {} as Record<string, FeatureFlag[]>)

  if (isLoading) {
    return (
      <div className="space-y-4 p-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Feature Flags</h1>
        <p className="text-muted-foreground">
          Controle funcionalidades do sistema
        </p>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Buscar flags..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Grouped flags */}
      {Object.entries(groupedFlags).map(([category, categoryFlags]) => (
        <Card key={category}>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Flag className="h-4 w-4" />
              {category}
            </CardTitle>
            <CardDescription>
              {categoryFlags.length} flag{categoryFlags.length !== 1 && 's'}
            </CardDescription>
          </CardHeader>

          <CardContent>
            <div className="space-y-4">
              {categoryFlags.map((flag) => (
                <div
                  key={flag.id}
                  className="flex items-center justify-between p-4 bg-muted rounded-lg"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <p className="font-medium font-mono text-sm">{flag.name}</p>
                      <Badge variant={flag.enabled ? 'default' : 'secondary'}>
                        {flag.enabled ? 'ON' : 'OFF'}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">
                      {flag.description}
                    </p>
                    {flag.updated_by && (
                      <p className="text-xs text-muted-foreground mt-2">
                        Atualizado por {flag.updated_by}
                      </p>
                    )}
                  </div>

                  <Switch
                    checked={flag.enabled}
                    onCheckedChange={(enabled) =>
                      updateMutation.mutate({ name: flag.name, enabled })
                    }
                    disabled={!canEdit || updateMutation.isPending}
                  />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ))}

      {filteredFlags.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            Nenhuma flag encontrada
          </CardContent>
        </Card>
      )}

      {!canEdit && (
        <p className="text-sm text-muted-foreground text-center">
          Você precisa de permissão de Manager para editar flags
        </p>
      )}
    </div>
  )
}
```

**DoD:**
- [ ] Lista flags agrupadas por categoria
- [ ] Busca por nome/descrição
- [ ] Toggle para ativar/desativar
- [ ] Mostra quem atualizou por último
- [ ] Desabilitado para roles menores que manager

---

### S06.6: Página Principal Sistema

**Arquivo:** `app/(dashboard)/sistema/page.tsx`

```typescript
'use client'

import { useQuery } from '@tanstack/react-query'
import { Settings, Flag, Shield } from 'lucide-react'
import Link from 'next/link'
import { api } from '@/lib/api/client'
import { JuliaToggle } from './components/julia-toggle'
import { RateLimitCard } from './components/rate-limit-card'
import { CircuitBreakerCard } from './components/circuit-breaker-card'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'

export default function SistemaPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['dashboard-status'],
    queryFn: () => api.get('/dashboard/status'),
    refetchInterval: 30000 // Refresh a cada 30s
  })

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-6 md:grid-cols-2">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Sistema</h1>
          <p className="text-muted-foreground">
            Controles operacionais da Julia
          </p>
        </div>
      </div>

      {/* Grid principal */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Julia Toggle */}
        <JuliaToggle status={data.julia} />

        {/* Rate Limit */}
        <RateLimitCard status={data.rate_limit} />

        {/* Circuit Breakers */}
        <CircuitBreakerCard status={data.circuits} />

        {/* Quick Links */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Configurações
            </CardTitle>
            <CardDescription>Acesso rápido</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Link href="/sistema/flags">
              <Button variant="outline" className="w-full justify-start">
                <Flag className="h-4 w-4 mr-2" />
                Feature Flags
              </Button>
            </Link>
            <Link href="/auditoria">
              <Button variant="outline" className="w-full justify-start">
                <Shield className="h-4 w-4 mr-2" />
                Logs de Auditoria
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
```

**DoD:**
- [ ] Grid responsivo com cards
- [ ] Julia toggle funcional
- [ ] Rate limit visual
- [ ] Circuit breakers visual
- [ ] Links para feature flags e auditoria

---

## Checklist Final

- [ ] Julia toggle com confirmação
- [ ] Julia pause com timer
- [ ] Rate limit card com progress
- [ ] Rate limit configurável (admin)
- [ ] Circuit breakers com reset
- [ ] Feature flags página
- [ ] Feature flags toggle (manager+)
- [ ] Página sistema unificada
- [ ] Todas ações logadas para auditoria
- [ ] Mobile responsivo
