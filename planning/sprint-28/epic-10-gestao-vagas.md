# E10: Gestão de Vagas

**Épico:** Lista + CRUD + Reservas
**Estimativa:** 6h
**Prioridade:** P1 (Core)
**Dependências:** E01, E02, E04

---

## Objetivo

Implementar gestão completa de vagas/plantões:
- Lista com filtros
- Criação/edição de vagas
- Visualização de reservas
- Status e disponibilidade
- Integração com médicos

---

## Estrutura de Arquivos

```
app/(dashboard)/vagas/
├── page.tsx                   # Lista de vagas
├── nova/
│   └── page.tsx               # Criar vaga
├── [id]/
│   ├── page.tsx               # Detalhe da vaga
│   └── editar/
│       └── page.tsx           # Editar vaga
├── components/
│   ├── shift-list.tsx
│   ├── shift-card.tsx
│   ├── shift-form.tsx
│   ├── shift-filters.tsx
│   ├── shift-reservations.tsx
│   └── shift-calendar.tsx
```

---

## Stories

### S10.1: Lista de Vagas

**Arquivo:** `app/(dashboard)/vagas/page.tsx`

```typescript
'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Calendar, Filter, Plus, LayoutGrid, List } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { api } from '@/lib/api/client'
import { useAuth } from '@/hooks/use-auth'
import { ShiftList } from './components/shift-list'
import { ShiftCalendar } from './components/shift-calendar'
import { ShiftFilters } from './components/shift-filters'

type ViewMode = 'list' | 'calendar'

interface Filters {
  status?: string
  hospital?: string
  especialidade?: string
  date_from?: string
  date_to?: string
}

export default function VagasPage() {
  const router = useRouter()
  const [viewMode, setViewMode] = useState<ViewMode>('list')
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState<Filters>({})
  const [showFilters, setShowFilters] = useState(false)

  const { hasPermission } = useAuth()
  const canCreate = hasPermission('operator')

  const { data, isLoading } = useQuery({
    queryKey: ['shifts', page, filters],
    queryFn: () => api.get('/dashboard/shifts', {
      params: { page, per_page: 20, ...filters }
    })
  })

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 md:p-6 border-b">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold">Vagas</h1>
            <p className="text-muted-foreground">
              {data?.total || 0} vagas cadastradas
            </p>
          </div>
          <div className="flex gap-2">
            <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as ViewMode)}>
              <TabsList>
                <TabsTrigger value="list">
                  <List className="h-4 w-4" />
                </TabsTrigger>
                <TabsTrigger value="calendar">
                  <Calendar className="h-4 w-4" />
                </TabsTrigger>
              </TabsList>
            </Tabs>
            {canCreate && (
              <Button onClick={() => router.push('/vagas/nova')}>
                <Plus className="h-4 w-4 mr-2" />
                <span className="hidden md:inline">Nova Vaga</span>
              </Button>
            )}
          </div>
        </div>

        <div className="flex gap-2">
          <Input
            placeholder="Buscar vagas..."
            className="flex-1"
          />
          <Button variant="outline" onClick={() => setShowFilters(!showFilters)}>
            <Filter className="h-4 w-4" />
          </Button>
        </div>

        {showFilters && (
          <ShiftFilters
            filters={filters}
            onApply={setFilters}
            className="mt-4"
          />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {isLoading ? (
          <div className="p-4 space-y-4">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-24" />
            ))}
          </div>
        ) : viewMode === 'list' ? (
          <ShiftList
            shifts={data?.data || []}
            total={data?.total || 0}
            page={page}
            pages={data?.pages || 1}
            onPageChange={setPage}
          />
        ) : (
          <ShiftCalendar shifts={data?.data || []} />
        )}
      </div>
    </div>
  )
}
```

---

### S10.2: Card de Vaga

**Arquivo:** `app/(dashboard)/vagas/components/shift-card.tsx`

```typescript
'use client'

import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { useRouter } from 'next/navigation'
import { Calendar, Clock, MapPin, DollarSign, Users } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

interface Shift {
  id: string
  hospital: string
  especialidade: string
  data: string
  hora_inicio: string
  hora_fim: string
  valor: number
  status: string
  reservas_count: number
  vagas_disponiveis: number
}

interface Props {
  shift: Shift
}

export function ShiftCard({ shift }: Props) {
  const router = useRouter()

  const getStatusBadge = () => {
    switch (shift.status) {
      case 'open':
        return <Badge className="bg-green-100 text-green-800">Aberta</Badge>
      case 'filled':
        return <Badge className="bg-blue-100 text-blue-800">Preenchida</Badge>
      case 'cancelled':
        return <Badge variant="destructive">Cancelada</Badge>
      case 'completed':
        return <Badge variant="secondary">Concluída</Badge>
      default:
        return <Badge variant="outline">{shift.status}</Badge>
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(value)
  }

  const shiftDate = new Date(shift.data)

  return (
    <Card
      className="cursor-pointer hover:bg-muted/50 transition-colors"
      onClick={() => router.push(`/vagas/${shift.id}`)}
    >
      <CardContent className="p-4">
        <div className="flex flex-col md:flex-row md:items-center gap-4">
          {/* Data */}
          <div className="flex-shrink-0 text-center p-3 bg-primary/10 rounded-lg w-16">
            <p className="text-2xl font-bold text-primary">
              {format(shiftDate, 'dd')}
            </p>
            <p className="text-xs text-muted-foreground uppercase">
              {format(shiftDate, 'MMM', { locale: ptBR })}
            </p>
          </div>

          {/* Info */}
          <div className="flex-1 space-y-2">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-semibold">{shift.hospital}</h3>
                <p className="text-sm text-muted-foreground">
                  {shift.especialidade}
                </p>
              </div>
              {getStatusBadge()}
            </div>

            <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                <Clock className="h-4 w-4" />
                {shift.hora_inicio} - {shift.hora_fim}
              </span>
              <span className="flex items-center gap-1">
                <DollarSign className="h-4 w-4" />
                {formatCurrency(shift.valor)}
              </span>
              <span className="flex items-center gap-1">
                <Users className="h-4 w-4" />
                {shift.reservas_count} / {shift.reservas_count + shift.vagas_disponiveis}
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
```

---

### S10.3: Formulário de Vaga

**Arquivo:** `app/(dashboard)/vagas/components/shift-form.tsx`

```typescript
'use client'

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useToast } from '@/components/ui/use-toast'
import { api } from '@/lib/api/client'

const shiftSchema = z.object({
  hospital_id: z.string().min(1, 'Selecione um hospital'),
  especialidade_id: z.string().min(1, 'Selecione uma especialidade'),
  data: z.string().min(1, 'Selecione uma data'),
  hora_inicio: z.string().min(1, 'Informe o horário de início'),
  hora_fim: z.string().min(1, 'Informe o horário de fim'),
  valor: z.number().min(0, 'Valor deve ser positivo'),
  quantidade: z.number().min(1, 'Mínimo 1 vaga'),
  descricao: z.string().optional()
})

type ShiftFormData = z.infer<typeof shiftSchema>

interface Props {
  shift?: ShiftFormData & { id: string }
  hospitals: { id: string; nome: string }[]
  especialidades: { id: string; nome: string }[]
}

export function ShiftForm({ shift, hospitals, especialidades }: Props) {
  const router = useRouter()
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const isEditing = !!shift

  const form = useForm<ShiftFormData>({
    resolver: zodResolver(shiftSchema),
    defaultValues: shift || {
      quantidade: 1
    }
  })

  const mutation = useMutation({
    mutationFn: (data: ShiftFormData) => {
      if (isEditing) {
        return api.put(`/dashboard/shifts/${shift.id}`, data)
      }
      return api.post('/dashboard/shifts', data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shifts'] })
      toast({
        title: isEditing ? 'Vaga atualizada' : 'Vaga criada',
        description: isEditing
          ? 'As alterações foram salvas'
          : 'A nova vaga foi criada com sucesso'
      })
      router.push('/vagas')
    },
    onError: () => {
      toast({
        title: 'Erro',
        description: 'Não foi possível salvar a vaga',
        variant: 'destructive'
      })
    }
  })

  const onSubmit = (data: ShiftFormData) => {
    mutation.mutate(data)
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="hospital">Hospital</Label>
          <Select
            value={form.watch('hospital_id')}
            onValueChange={(v) => form.setValue('hospital_id', v)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Selecione..." />
            </SelectTrigger>
            <SelectContent>
              {hospitals.map((h) => (
                <SelectItem key={h.id} value={h.id}>
                  {h.nome}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {form.formState.errors.hospital_id && (
            <p className="text-sm text-destructive">
              {form.formState.errors.hospital_id.message}
            </p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="especialidade">Especialidade</Label>
          <Select
            value={form.watch('especialidade_id')}
            onValueChange={(v) => form.setValue('especialidade_id', v)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Selecione..." />
            </SelectTrigger>
            <SelectContent>
              {especialidades.map((e) => (
                <SelectItem key={e.id} value={e.id}>
                  {e.nome}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="data">Data</Label>
          <Input
            type="date"
            {...form.register('data')}
          />
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-2">
            <Label htmlFor="hora_inicio">Início</Label>
            <Input
              type="time"
              {...form.register('hora_inicio')}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="hora_fim">Fim</Label>
            <Input
              type="time"
              {...form.register('hora_fim')}
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="valor">Valor (R$)</Label>
          <Input
            type="number"
            step="0.01"
            {...form.register('valor', { valueAsNumber: true })}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="quantidade">Quantidade de vagas</Label>
          <Input
            type="number"
            min="1"
            {...form.register('quantidade', { valueAsNumber: true })}
          />
        </div>
      </div>

      <div className="flex gap-2 justify-end">
        <Button
          type="button"
          variant="outline"
          onClick={() => router.back()}
        >
          Cancelar
        </Button>
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? 'Salvando...' : isEditing ? 'Salvar' : 'Criar Vaga'}
        </Button>
      </div>
    </form>
  )
}
```

---

### S10.4: Calendário de Vagas

**Arquivo:** `app/(dashboard)/vagas/components/shift-calendar.tsx`

```typescript
'use client'

import { useState } from 'react'
import { format, startOfMonth, endOfMonth, eachDayOfInterval, isSameDay } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface Shift {
  id: string
  data: string
  hospital: string
  status: string
}

interface Props {
  shifts: Shift[]
}

export function ShiftCalendar({ shifts }: Props) {
  const [currentMonth, setCurrentMonth] = useState(new Date())

  const monthStart = startOfMonth(currentMonth)
  const monthEnd = endOfMonth(currentMonth)
  const days = eachDayOfInterval({ start: monthStart, end: monthEnd })

  const getShiftsForDay = (day: Date) => {
    return shifts.filter((shift) => isSameDay(new Date(shift.data), day))
  }

  const prevMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1))
  }

  const nextMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1))
  }

  return (
    <div className="p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <Button variant="ghost" size="icon" onClick={prevMonth}>
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <h2 className="font-semibold">
          {format(currentMonth, 'MMMM yyyy', { locale: ptBR })}
        </h2>
        <Button variant="ghost" size="icon" onClick={nextMonth}>
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      {/* Days header */}
      <div className="grid grid-cols-7 gap-1 mb-2">
        {['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'].map((day) => (
          <div key={day} className="text-center text-sm font-medium text-muted-foreground py-2">
            {day}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div className="grid grid-cols-7 gap-1">
        {/* Empty cells for days before month start */}
        {[...Array(monthStart.getDay())].map((_, i) => (
          <div key={`empty-${i}`} className="h-24 md:h-32" />
        ))}

        {/* Days */}
        {days.map((day) => {
          const dayShifts = getShiftsForDay(day)
          const isToday = isSameDay(day, new Date())

          return (
            <div
              key={day.toISOString()}
              className={cn(
                'h-24 md:h-32 border rounded-lg p-1 overflow-hidden',
                isToday && 'border-primary'
              )}
            >
              <p className={cn(
                'text-sm font-medium mb-1',
                isToday && 'text-primary'
              )}>
                {format(day, 'd')}
              </p>

              <div className="space-y-1">
                {dayShifts.slice(0, 3).map((shift) => (
                  <div
                    key={shift.id}
                    className={cn(
                      'text-xs p-1 rounded truncate',
                      shift.status === 'open' && 'bg-green-100 text-green-800',
                      shift.status === 'filled' && 'bg-blue-100 text-blue-800',
                      shift.status === 'cancelled' && 'bg-red-100 text-red-800'
                    )}
                  >
                    {shift.hospital}
                  </div>
                ))}
                {dayShifts.length > 3 && (
                  <p className="text-xs text-muted-foreground">
                    +{dayShifts.length - 3} mais
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

## Backend Endpoints

```python
# app/api/routes/dashboard/shifts.py

@router.get("")
async def list_shifts(
    user: CurrentUser,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, le=100),
    status: Optional[str] = None,
    hospital: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    """Lista vagas com filtros."""

@router.post("")
async def create_shift(
    data: ShiftCreate,
    user: DashboardUser = Depends(require_operator())
):
    """Cria nova vaga."""

@router.get("/{shift_id}")
async def get_shift(shift_id: str, user: CurrentUser):
    """Detalhes de uma vaga."""

@router.put("/{shift_id}")
async def update_shift(
    shift_id: str,
    data: ShiftUpdate,
    user: DashboardUser = Depends(require_operator())
):
    """Atualiza vaga."""

@router.delete("/{shift_id}")
async def delete_shift(
    shift_id: str,
    user: DashboardUser = Depends(require_manager())
):
    """Remove vaga."""

@router.get("/{shift_id}/reservations")
async def get_shift_reservations(shift_id: str, user: CurrentUser):
    """Lista reservas de uma vaga."""
```

---

## Checklist Final

- [ ] Lista de vagas com paginação
- [ ] Vista em lista e calendário
- [ ] Filtros por status/hospital/data
- [ ] Card de vaga com info resumida
- [ ] Formulário de criação
- [ ] Formulário de edição
- [ ] Visualização de reservas
- [ ] CRUD completo
- [ ] Mobile responsivo
