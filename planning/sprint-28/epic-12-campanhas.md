# E12: Sistema de Campanhas

**Épico:** Lista + Criação + Monitoramento
**Estimativa:** 6h
**Prioridade:** P2 (Importante)
**Dependências:** E01, E02, E04, E09

---

## Objetivo

Implementar gestão de campanhas de mensagens:
- Lista de campanhas
- Criação com segmentação
- Monitoramento de execução
- Métricas de performance
- Agendamento

---

## Estrutura de Arquivos

```
app/(dashboard)/campanhas/
├── page.tsx                   # Lista de campanhas
├── nova/
│   └── page.tsx               # Criar campanha
├── [id]/
│   └── page.tsx               # Detalhe/monitoramento
├── components/
│   ├── campaign-list.tsx
│   ├── campaign-card.tsx
│   ├── campaign-form.tsx
│   ├── campaign-progress.tsx
│   ├── campaign-stats.tsx
│   └── audience-selector.tsx
```

---

## Stories

### S12.1: Lista de Campanhas

**Arquivo:** `app/(dashboard)/campanhas/page.tsx`

```typescript
'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Send, Plus, Filter } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { api } from '@/lib/api/client'
import { useAuth } from '@/hooks/use-auth'
import { CampaignList } from './components/campaign-list'

type StatusFilter = 'all' | 'draft' | 'scheduled' | 'running' | 'completed'

export default function CampanhasPage() {
  const router = useRouter()
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [page, setPage] = useState(1)

  const { hasPermission } = useAuth()
  const canCreate = hasPermission('operator')

  const { data, isLoading } = useQuery({
    queryKey: ['campaigns', page, statusFilter],
    queryFn: () => api.get('/dashboard/campaigns', {
      params: {
        page,
        per_page: 20,
        status: statusFilter === 'all' ? undefined : statusFilter
      }
    })
  })

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 md:p-6 border-b">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold">Campanhas</h1>
            <p className="text-muted-foreground">
              {data?.total || 0} campanhas
            </p>
          </div>
          {canCreate && (
            <Button onClick={() => router.push('/campanhas/nova')}>
              <Plus className="h-4 w-4 mr-2" />
              <span className="hidden md:inline">Nova Campanha</span>
            </Button>
          )}
        </div>

        <Tabs value={statusFilter} onValueChange={(v) => setStatusFilter(v as StatusFilter)}>
          <TabsList className="w-full md:w-auto overflow-x-auto">
            <TabsTrigger value="all">Todas</TabsTrigger>
            <TabsTrigger value="draft">Rascunho</TabsTrigger>
            <TabsTrigger value="scheduled">Agendada</TabsTrigger>
            <TabsTrigger value="running">Em execução</TabsTrigger>
            <TabsTrigger value="completed">Concluída</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Lista */}
      <div className="flex-1 overflow-auto">
        {isLoading ? (
          <div className="p-4 space-y-4">
            {[...Array(3)].map((_, i) => (
              <Skeleton key={i} className="h-32" />
            ))}
          </div>
        ) : (
          <CampaignList
            campaigns={data?.data || []}
            total={data?.total || 0}
            page={page}
            pages={data?.pages || 1}
            onPageChange={setPage}
          />
        )}
      </div>
    </div>
  )
}
```

---

### S12.2: Card de Campanha

**Arquivo:** `app/(dashboard)/campanhas/components/campaign-card.tsx`

```typescript
'use client'

import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { useRouter } from 'next/navigation'
import { Send, Clock, CheckCircle, Play, Pause, Users } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'

interface Campaign {
  id: string
  nome: string
  tipo: string
  status: string
  total_destinatarios: number
  enviados: number
  entregues: number
  respondidos: number
  scheduled_at?: string
  created_at: string
}

interface Props {
  campaign: Campaign
}

export function CampaignCard({ campaign }: Props) {
  const router = useRouter()

  const progress = campaign.total_destinatarios > 0
    ? (campaign.enviados / campaign.total_destinatarios) * 100
    : 0

  const getStatusBadge = () => {
    switch (campaign.status) {
      case 'draft':
        return <Badge variant="secondary">Rascunho</Badge>
      case 'scheduled':
        return <Badge className="bg-blue-100 text-blue-800">Agendada</Badge>
      case 'running':
        return <Badge className="bg-yellow-100 text-yellow-800">Em execução</Badge>
      case 'completed':
        return <Badge className="bg-green-100 text-green-800">Concluída</Badge>
      case 'paused':
        return <Badge variant="secondary">Pausada</Badge>
      default:
        return <Badge variant="outline">{campaign.status}</Badge>
    }
  }

  return (
    <Card
      className="cursor-pointer hover:bg-muted/50 transition-colors"
      onClick={() => router.push(`/campanhas/${campaign.id}`)}
    >
      <CardContent className="p-4">
        <div className="flex flex-col md:flex-row md:items-start gap-4">
          {/* Info */}
          <div className="flex-1 space-y-3">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-semibold">{campaign.nome}</h3>
                <p className="text-sm text-muted-foreground">
                  {campaign.tipo}
                </p>
              </div>
              {getStatusBadge()}
            </div>

            {/* Progress */}
            {campaign.status === 'running' && (
              <div className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span>Progresso</span>
                  <span>{campaign.enviados} / {campaign.total_destinatarios}</span>
                </div>
                <Progress value={progress} className="h-2" />
              </div>
            )}

            {/* Stats */}
            <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                <Users className="h-4 w-4" />
                {campaign.total_destinatarios} destinatários
              </span>
              {campaign.scheduled_at && (
                <span className="flex items-center gap-1">
                  <Clock className="h-4 w-4" />
                  {format(new Date(campaign.scheduled_at), "dd/MM 'às' HH:mm", { locale: ptBR })}
                </span>
              )}
              {campaign.status === 'completed' && (
                <>
                  <span className="flex items-center gap-1">
                    <CheckCircle className="h-4 w-4" />
                    {campaign.entregues} entregues
                  </span>
                  <span className="flex items-center gap-1">
                    <Send className="h-4 w-4" />
                    {campaign.respondidos} responderam
                  </span>
                </>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
```

---

### S12.3: Formulário de Campanha

**Arquivo:** `app/(dashboard)/campanhas/components/campaign-form.tsx`

```typescript
'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useToast } from '@/components/ui/use-toast'
import { api } from '@/lib/api/client'
import { AudienceSelector } from './audience-selector'

const campaignSchema = z.object({
  nome: z.string().min(1, 'Nome é obrigatório'),
  tipo: z.enum(['discovery', 'oferta', 'reativacao', 'followup', 'custom']),
  mensagem: z.string().min(1, 'Mensagem é obrigatória'),
  scheduled_at: z.string().optional(),
  audience_filters: z.object({
    status_funil: z.array(z.string()).optional(),
    especialidades: z.array(z.string()).optional(),
    cidades: z.array(z.string()).optional(),
    ultimo_contato_dias: z.number().optional()
  })
})

type CampaignFormData = z.infer<typeof campaignSchema>

const TIPOS = [
  { value: 'discovery', label: 'Discovery' },
  { value: 'oferta', label: 'Oferta de Vaga' },
  { value: 'reativacao', label: 'Reativação' },
  { value: 'followup', label: 'Follow-up' },
  { value: 'custom', label: 'Personalizada' }
]

export function CampaignForm() {
  const router = useRouter()
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const [audienceCount, setAudienceCount] = useState(0)

  const form = useForm<CampaignFormData>({
    resolver: zodResolver(campaignSchema),
    defaultValues: {
      tipo: 'discovery',
      audience_filters: {}
    }
  })

  const createMutation = useMutation({
    mutationFn: (data: CampaignFormData) =>
      api.post('/dashboard/campaigns', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] })
      toast({ title: 'Campanha criada' })
      router.push('/campanhas')
    },
    onError: () => {
      toast({
        title: 'Erro',
        description: 'Não foi possível criar a campanha',
        variant: 'destructive'
      })
    }
  })

  const onSubmit = (data: CampaignFormData) => {
    createMutation.mutate(data)
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
      {/* Info básica */}
      <Card>
        <CardHeader>
          <CardTitle>Informações da Campanha</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="nome">Nome</Label>
              <Input
                id="nome"
                placeholder="Ex: Campanha Cardiologistas SP"
                {...form.register('nome')}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="tipo">Tipo</Label>
              <Select
                value={form.watch('tipo')}
                onValueChange={(v) => form.setValue('tipo', v as any)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TIPOS.map((tipo) => (
                    <SelectItem key={tipo.value} value={tipo.value}>
                      {tipo.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="mensagem">Mensagem</Label>
            <Textarea
              id="mensagem"
              placeholder="Escreva a mensagem da campanha..."
              rows={5}
              {...form.register('mensagem')}
            />
            <p className="text-xs text-muted-foreground">
              Use {'{nome}'} para personalizar com o nome do médico
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="scheduled_at">Agendar para (opcional)</Label>
            <Input
              id="scheduled_at"
              type="datetime-local"
              {...form.register('scheduled_at')}
            />
          </div>
        </CardContent>
      </Card>

      {/* Audiência */}
      <Card>
        <CardHeader>
          <CardTitle>Audiência</CardTitle>
        </CardHeader>
        <CardContent>
          <AudienceSelector
            filters={form.watch('audience_filters')}
            onChange={(filters) => form.setValue('audience_filters', filters)}
            onCountChange={setAudienceCount}
          />
        </CardContent>
      </Card>

      {/* Preview */}
      <Card>
        <CardHeader>
          <CardTitle>Resumo</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-bold">{audienceCount}</p>
          <p className="text-muted-foreground">médicos serão contatados</p>
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex gap-2 justify-end">
        <Button
          type="button"
          variant="outline"
          onClick={() => router.back()}
        >
          Cancelar
        </Button>
        <Button
          type="submit"
          disabled={createMutation.isPending || audienceCount === 0}
        >
          {createMutation.isPending ? 'Criando...' : 'Criar Campanha'}
        </Button>
      </div>
    </form>
  )
}
```

---

### S12.4: Seletor de Audiência

**Arquivo:** `app/(dashboard)/campanhas/components/audience-selector.tsx`

```typescript
'use client'

import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { api } from '@/lib/api/client'

interface AudienceFilters {
  status_funil?: string[]
  especialidades?: string[]
  cidades?: string[]
  ultimo_contato_dias?: number
}

interface Props {
  filters: AudienceFilters
  onChange: (filters: AudienceFilters) => void
  onCountChange: (count: number) => void
}

const FUNNEL_STATUSES = [
  { value: 'prospecting', label: 'Prospecção' },
  { value: 'engaged', label: 'Engajado' },
  { value: 'negotiating', label: 'Negociando' }
]

export function AudienceSelector({ filters, onChange, onCountChange }: Props) {
  // Buscar contagem de audiência
  const { data: countData } = useQuery({
    queryKey: ['audience-count', filters],
    queryFn: () => api.post('/dashboard/campaigns/audience-count', filters)
  })

  useEffect(() => {
    onCountChange(countData?.count || 0)
  }, [countData, onCountChange])

  // Buscar opções
  const { data: options } = useQuery({
    queryKey: ['audience-options'],
    queryFn: () => api.get('/dashboard/campaigns/audience-options')
  })

  const toggleFunnel = (status: string) => {
    const current = filters.status_funil || []
    const updated = current.includes(status)
      ? current.filter(s => s !== status)
      : [...current, status]
    onChange({ ...filters, status_funil: updated })
  }

  return (
    <div className="space-y-6">
      {/* Status do funil */}
      <div className="space-y-3">
        <Label>Status no Funil</Label>
        <div className="flex flex-wrap gap-4">
          {FUNNEL_STATUSES.map((status) => (
            <div key={status.value} className="flex items-center gap-2">
              <Checkbox
                id={`funnel-${status.value}`}
                checked={filters.status_funil?.includes(status.value)}
                onCheckedChange={() => toggleFunnel(status.value)}
              />
              <label
                htmlFor={`funnel-${status.value}`}
                className="text-sm cursor-pointer"
              >
                {status.label}
              </label>
            </div>
          ))}
        </div>
      </div>

      {/* Último contato */}
      <div className="space-y-2">
        <Label>Último contato há mais de (dias)</Label>
        <Input
          type="number"
          placeholder="Ex: 30"
          value={filters.ultimo_contato_dias || ''}
          onChange={(e) => onChange({
            ...filters,
            ultimo_contato_dias: e.target.value ? parseInt(e.target.value) : undefined
          })}
        />
      </div>

      {/* Preview */}
      <div className="p-4 bg-muted rounded-lg">
        <p className="text-sm text-muted-foreground">
          Com os filtros atuais, <strong>{countData?.count || 0}</strong> médicos serão incluídos.
        </p>
      </div>
    </div>
  )
}
```

---

## Backend Endpoints

```python
# app/api/routes/dashboard/campaigns.py

@router.get("")
async def list_campaigns(
    user: CurrentUser,
    page: int = Query(1),
    per_page: int = Query(20),
    status: Optional[str] = None
):
    """Lista campanhas."""

@router.post("")
async def create_campaign(
    data: CampaignCreate,
    user: DashboardUser = Depends(require_operator())
):
    """Cria nova campanha."""

@router.get("/{campaign_id}")
async def get_campaign(campaign_id: str, user: CurrentUser):
    """Detalhes de uma campanha."""

@router.post("/{campaign_id}/start")
async def start_campaign(
    campaign_id: str,
    user: DashboardUser = Depends(require_operator())
):
    """Inicia execução da campanha."""

@router.post("/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: str,
    user: DashboardUser = Depends(require_operator())
):
    """Pausa campanha em execução."""

@router.post("/audience-count")
async def get_audience_count(
    filters: AudienceFilters,
    user: CurrentUser
):
    """Conta destinatários com filtros."""

@router.get("/audience-options")
async def get_audience_options(user: CurrentUser):
    """Retorna opções de filtro disponíveis."""
```

---

## Checklist Final

- [ ] Lista de campanhas com filtro de status
- [ ] Card de campanha com progresso
- [ ] Formulário de criação
- [ ] Seletor de audiência com contagem
- [ ] Agendamento de campanha
- [ ] Iniciar/pausar campanha
- [ ] Métricas de campanha
- [ ] Mobile responsivo
