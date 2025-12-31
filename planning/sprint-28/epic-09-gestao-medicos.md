# E09: Gestão de Médicos

**Épico:** Lista + Perfil + Ações
**Estimativa:** 6h
**Prioridade:** P1 (Core)
**Dependências:** E01, E02, E04

---

## Objetivo

Implementar gestão completa de médicos:
- Lista com filtros e busca
- Perfil detalhado
- Histórico de interações
- Ações (opt-out, status funil)
- Métricas individuais

---

## Estrutura de Arquivos

```
app/(dashboard)/medicos/
├── page.tsx                   # Lista de médicos
├── [id]/
│   └── page.tsx               # Perfil do médico
├── components/
│   ├── doctor-list.tsx
│   ├── doctor-card.tsx
│   ├── doctor-filters.tsx
│   ├── doctor-profile.tsx
│   ├── doctor-timeline.tsx
│   ├── doctor-stats.tsx
│   └── doctor-actions.tsx
```

---

## Stories

### S09.1: Lista de Médicos

**Arquivo:** `app/(dashboard)/medicos/page.tsx`

```typescript
'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Users, Filter, Download, Plus } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import { api } from '@/lib/api/client'
import { DoctorList } from './components/doctor-list'
import { DoctorFilters } from './components/doctor-filters'

interface Filters {
  status_funil?: string
  especialidade?: string
  opt_out?: boolean
  search?: string
}

export default function MedicosPage() {
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState<Filters>({})
  const [search, setSearch] = useState('')
  const [showFilters, setShowFilters] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['doctors', page, filters],
    queryFn: () => api.get('/dashboard/doctors', {
      params: { page, per_page: 20, ...filters }
    })
  })

  const handleSearch = (value: string) => {
    setSearch(value)
    setFilters(prev => ({ ...prev, search: value || undefined }))
    setPage(1)
  }

  const handleExport = async () => {
    // Exportar CSV
    const response = await api.get('/dashboard/doctors/export', {
      params: filters
    })
    // Download logic
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 md:p-6 border-b">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold">Médicos</h1>
            <p className="text-muted-foreground">
              {data?.total || 0} médicos cadastrados
            </p>
          </div>
          <Button variant="outline" onClick={handleExport}>
            <Download className="h-4 w-4 mr-2" />
            <span className="hidden md:inline">Exportar</span>
          </Button>
        </div>

        <div className="flex gap-2">
          <div className="flex-1 relative">
            <Users className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Buscar por nome, telefone ou CRM..."
              value={search}
              onChange={(e) => handleSearch(e.target.value)}
              className="pl-10"
            />
          </div>

          <Sheet open={showFilters} onOpenChange={setShowFilters}>
            <SheetTrigger asChild>
              <Button variant="outline">
                <Filter className="h-4 w-4 md:mr-2" />
                <span className="hidden md:inline">Filtros</span>
              </Button>
            </SheetTrigger>
            <SheetContent>
              <SheetHeader>
                <SheetTitle>Filtros</SheetTitle>
              </SheetHeader>
              <DoctorFilters
                filters={filters}
                onApply={(f) => { setFilters(f); setShowFilters(false) }}
                onClear={() => { setFilters({}); setShowFilters(false) }}
              />
            </SheetContent>
          </Sheet>
        </div>
      </div>

      {/* Lista */}
      <div className="flex-1 overflow-auto">
        {isLoading ? (
          <div className="p-4 space-y-4">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-24" />
            ))}
          </div>
        ) : (
          <DoctorList
            doctors={data?.data || []}
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

### S09.2: Perfil do Médico

**Arquivo:** `app/(dashboard)/medicos/[id]/page.tsx`

```typescript
'use client'

import { useQuery } from '@tanstack/react-query'
import { useParams, useRouter } from 'next/navigation'
import { ArrowLeft, Phone, Mail, MapPin, Stethoscope } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api/client'
import { DoctorTimeline } from '../components/doctor-timeline'
import { DoctorStats } from '../components/doctor-stats'
import { DoctorActions } from '../components/doctor-actions'

export default function DoctorProfilePage() {
  const params = useParams()
  const router = useRouter()
  const doctorId = params.id as string

  const { data: doctor, isLoading } = useQuery({
    queryKey: ['doctor', doctorId],
    queryFn: () => api.get(`/dashboard/doctors/${doctorId}`)
  })

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton className="h-32" />
        <Skeleton className="h-64" />
      </div>
    )
  }

  const initials = doctor?.nome
    ?.split(' ')
    .slice(0, 2)
    .map((n: string) => n[0])
    .join('')
    .toUpperCase()

  const getFunnelBadge = (status: string) => {
    const colors: Record<string, string> = {
      prospecting: 'bg-gray-100 text-gray-800',
      engaged: 'bg-blue-100 text-blue-800',
      negotiating: 'bg-yellow-100 text-yellow-800',
      converted: 'bg-green-100 text-green-800',
      lost: 'bg-red-100 text-red-800'
    }
    return <Badge className={colors[status] || 'bg-gray-100'}>{status}</Badge>
  }

  return (
    <div className="flex flex-col h-full overflow-auto">
      {/* Header */}
      <div className="p-4 md:p-6 border-b bg-background sticky top-0 z-10">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.back()}
          className="mb-4"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Voltar
        </Button>

        <div className="flex gap-4">
          <Avatar className="h-16 w-16 md:h-20 md:w-20">
            <AvatarFallback className="text-xl bg-primary/10 text-primary">
              {initials}
            </AvatarFallback>
          </Avatar>

          <div className="flex-1">
            <div className="flex items-start justify-between">
              <div>
                <h1 className="text-xl md:text-2xl font-bold">{doctor?.nome}</h1>
                <div className="flex flex-wrap gap-2 mt-1">
                  {getFunnelBadge(doctor?.status_funil)}
                  {doctor?.opt_out && (
                    <Badge variant="destructive">Opt-out</Badge>
                  )}
                </div>
              </div>
            </div>

            <div className="flex flex-wrap gap-4 mt-3 text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                <Phone className="h-4 w-4" />
                {doctor?.telefone}
              </span>
              {doctor?.especialidade && (
                <span className="flex items-center gap-1">
                  <Stethoscope className="h-4 w-4" />
                  {doctor?.especialidade}
                </span>
              )}
              {doctor?.cidade && (
                <span className="flex items-center gap-1">
                  <MapPin className="h-4 w-4" />
                  {doctor?.cidade}
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
              Histórico
            </TabsTrigger>
            <TabsTrigger value="stats" className="flex-1 md:flex-none">
              Métricas
            </TabsTrigger>
            <TabsTrigger value="actions" className="flex-1 md:flex-none">
              Ações
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
              <DoctorActions doctor={doctor} />
            </TabsContent>
          </div>
        </Tabs>
      </div>
    </div>
  )
}
```

---

### S09.3: Timeline de Interações

**Arquivo:** `app/(dashboard)/medicos/components/doctor-timeline.tsx`

```typescript
'use client'

import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import {
  MessageCircle,
  Phone,
  Calendar,
  CheckCircle,
  XCircle,
  Send,
  UserCheck
} from 'lucide-react'
import { api } from '@/lib/api/client'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

interface TimelineEvent {
  id: string
  type: string
  title: string
  description?: string
  created_at: string
  metadata?: Record<string, any>
}

const EVENT_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  message_sent: Send,
  message_received: MessageCircle,
  call: Phone,
  shift_reserved: Calendar,
  shift_confirmed: CheckCircle,
  shift_cancelled: XCircle,
  handoff: UserCheck,
  campaign: Send
}

const EVENT_COLORS: Record<string, string> = {
  message_sent: 'bg-blue-100 text-blue-600',
  message_received: 'bg-green-100 text-green-600',
  call: 'bg-purple-100 text-purple-600',
  shift_reserved: 'bg-yellow-100 text-yellow-600',
  shift_confirmed: 'bg-green-100 text-green-600',
  shift_cancelled: 'bg-red-100 text-red-600',
  handoff: 'bg-orange-100 text-orange-600',
  campaign: 'bg-indigo-100 text-indigo-600'
}

interface Props {
  doctorId: string
}

export function DoctorTimeline({ doctorId }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: ['doctor-timeline', doctorId],
    queryFn: () => api.get(`/dashboard/doctors/${doctorId}/timeline`)
  })

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="h-16" />
        ))}
      </div>
    )
  }

  const events: TimelineEvent[] = data?.events || []

  if (events.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        Nenhuma interação registrada
      </div>
    )
  }

  return (
    <div className="relative">
      {/* Linha vertical */}
      <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-border" />

      <div className="space-y-6">
        {events.map((event, index) => {
          const Icon = EVENT_ICONS[event.type] || MessageCircle
          const colorClass = EVENT_COLORS[event.type] || 'bg-gray-100 text-gray-600'

          return (
            <div key={event.id} className="relative pl-10">
              {/* Ícone */}
              <div
                className={cn(
                  'absolute left-0 w-8 h-8 rounded-full flex items-center justify-center',
                  colorClass
                )}
              >
                <Icon className="h-4 w-4" />
              </div>

              {/* Conteúdo */}
              <div className="bg-muted rounded-lg p-4">
                <div className="flex items-start justify-between gap-2">
                  <p className="font-medium">{event.title}</p>
                  <span className="text-xs text-muted-foreground whitespace-nowrap">
                    {format(new Date(event.created_at), "dd/MM 'às' HH:mm", {
                      locale: ptBR
                    })}
                  </span>
                </div>
                {event.description && (
                  <p className="text-sm text-muted-foreground mt-1">
                    {event.description}
                  </p>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

---

### S09.4: Ações do Médico

**Arquivo:** `app/(dashboard)/medicos/components/doctor-actions.tsx`

```typescript
'use client'

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Ban, MessageCircle, RefreshCw } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { useToast } from '@/components/ui/use-toast'
import { api } from '@/lib/api/client'
import { useAuth } from '@/hooks/use-auth'

interface Doctor {
  id: string
  nome: string
  status_funil: string
  opt_out: boolean
}

interface Props {
  doctor: Doctor
}

const FUNNEL_STATUSES = [
  { value: 'prospecting', label: 'Prospecção' },
  { value: 'engaged', label: 'Engajado' },
  { value: 'negotiating', label: 'Negociando' },
  { value: 'converted', label: 'Convertido' },
  { value: 'lost', label: 'Perdido' }
]

export function DoctorActions({ doctor }: Props) {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { hasPermission } = useAuth()

  const canEdit = hasPermission('operator')

  const updateFunnelMutation = useMutation({
    mutationFn: (status: string) =>
      api.put(`/dashboard/doctors/${doctor.id}/funnel`, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['doctor', doctor.id] })
      toast({ title: 'Status atualizado' })
    }
  })

  const toggleOptOutMutation = useMutation({
    mutationFn: () =>
      api.post(`/dashboard/doctors/${doctor.id}/opt-out`, {
        opt_out: !doctor.opt_out
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['doctor', doctor.id] })
      toast({
        title: doctor.opt_out ? 'Opt-out removido' : 'Opt-out registrado'
      })
    }
  })

  if (!canEdit) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          Você precisa de permissão de Operador para realizar ações
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Status do Funil */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Status do Funil</CardTitle>
          <CardDescription>
            Posição do médico no pipeline de vendas
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Select
            value={doctor.status_funil}
            onValueChange={(value) => updateFunnelMutation.mutate(value)}
            disabled={updateFunnelMutation.isPending}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {FUNNEL_STATUSES.map((status) => (
                <SelectItem key={status.value} value={status.value}>
                  {status.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {/* Opt-out */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Preferências de Contato</CardTitle>
          <CardDescription>
            Gerenciar preferências de comunicação
          </CardDescription>
        </CardHeader>
        <CardContent>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant={doctor.opt_out ? 'default' : 'destructive'}
                className="w-full"
              >
                {doctor.opt_out ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Reativar Contato
                  </>
                ) : (
                  <>
                    <Ban className="h-4 w-4 mr-2" />
                    Marcar Opt-out
                  </>
                )}
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>
                  {doctor.opt_out ? 'Reativar contato?' : 'Marcar como opt-out?'}
                </AlertDialogTitle>
                <AlertDialogDescription>
                  {doctor.opt_out
                    ? 'O médico voltará a receber mensagens da Julia.'
                    : 'O médico não receberá mais mensagens automáticas da Julia.'}
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancelar</AlertDialogCancel>
                <AlertDialogAction onClick={() => toggleOptOutMutation.mutate()}>
                  Confirmar
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </CardContent>
      </Card>

      {/* Iniciar Conversa */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Conversa</CardTitle>
        </CardHeader>
        <CardContent>
          <Button
            variant="outline"
            className="w-full"
            onClick={() => {
              // Navegar para conversa ativa ou criar nova
            }}
          >
            <MessageCircle className="h-4 w-4 mr-2" />
            Ver Conversa
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
```

---

## Backend Endpoints

```python
# app/api/routes/dashboard/doctors.py

@router.get("")
async def list_doctors(
    user: CurrentUser,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_funil: Optional[str] = None,
    especialidade: Optional[str] = None,
    opt_out: Optional[bool] = None,
    search: Optional[str] = None
):
    """Lista médicos com filtros."""
    # Implementação similar a conversations

@router.get("/{doctor_id}")
async def get_doctor(doctor_id: str, user: CurrentUser):
    """Detalhes de um médico."""

@router.get("/{doctor_id}/timeline")
async def get_doctor_timeline(doctor_id: str, user: CurrentUser):
    """Timeline de interações do médico."""

@router.put("/{doctor_id}/funnel")
async def update_funnel_status(
    doctor_id: str,
    data: FunnelUpdate,
    user: DashboardUser = Depends(require_operator())
):
    """Atualiza status do funil."""

@router.post("/{doctor_id}/opt-out")
async def toggle_opt_out(
    doctor_id: str,
    data: OptOutToggle,
    user: DashboardUser = Depends(require_operator())
):
    """Toggle opt-out do médico."""
```

---

## Checklist Final

- [ ] Lista de médicos com paginação
- [ ] Busca por nome/telefone/CRM
- [ ] Filtros por funil/especialidade/opt-out
- [ ] Card de médico com info resumida
- [ ] Perfil completo do médico
- [ ] Timeline de interações
- [ ] Métricas individuais
- [ ] Ações (funil, opt-out)
- [ ] Exportar CSV
- [ ] Mobile responsivo
