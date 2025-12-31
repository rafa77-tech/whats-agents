# E13: Auditoria e Logs

**Épico:** Logs de Ações + Filtros + Exportação
**Estimativa:** 4h
**Prioridade:** P2 (Importante)
**Dependências:** E01, E02, E04

---

## Objetivo

Implementar sistema de auditoria:
- Log de todas as ações no dashboard
- Filtros por usuário, ação, data
- Visualização detalhada
- Exportação de relatórios
- Retenção configurável

---

## Estrutura de Arquivos

```
app/(dashboard)/auditoria/
├── page.tsx                   # Lista de logs
├── components/
│   ├── audit-list.tsx
│   ├── audit-item.tsx
│   ├── audit-filters.tsx
│   └── audit-detail-dialog.tsx
```

---

## Stories

### S13.1: Lista de Auditoria

**Arquivo:** `app/(dashboard)/auditoria/page.tsx`

```typescript
'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Shield, Filter, Download } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import { api } from '@/lib/api/client'
import { useAuth } from '@/hooks/use-auth'
import { RequireRole } from '@/components/providers/auth-provider'
import { AuditList } from './components/audit-list'
import { AuditFilters } from './components/audit-filters'

interface Filters {
  action?: string
  actor_email?: string
  from_date?: string
  to_date?: string
}

export default function AuditoriaPage() {
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState<Filters>({})
  const [showFilters, setShowFilters] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['audit-logs', page, filters],
    queryFn: () => api.get('/dashboard/audit', {
      params: { page, per_page: 50, ...filters }
    })
  })

  const handleExport = async () => {
    const response = await api.get('/dashboard/audit/export', {
      params: filters
    })
    // Download CSV
  }

  return (
    <RequireRole role="manager">
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="p-4 md:p-6 border-b">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <Shield className="h-6 w-6 text-primary" />
              <div>
                <h1 className="text-2xl font-bold">Auditoria</h1>
                <p className="text-muted-foreground">
                  Histórico de ações no sistema
                </p>
              </div>
            </div>
            <Button variant="outline" onClick={handleExport}>
              <Download className="h-4 w-4 mr-2" />
              <span className="hidden md:inline">Exportar</span>
            </Button>
          </div>

          <div className="flex gap-2">
            <Input
              placeholder="Buscar por email ou ação..."
              className="flex-1"
              onChange={(e) => setFilters(prev => ({
                ...prev,
                actor_email: e.target.value || undefined
              }))}
            />

            <Sheet open={showFilters} onOpenChange={setShowFilters}>
              <SheetTrigger asChild>
                <Button variant="outline">
                  <Filter className="h-4 w-4" />
                </Button>
              </SheetTrigger>
              <SheetContent>
                <SheetHeader>
                  <SheetTitle>Filtros</SheetTitle>
                </SheetHeader>
                <AuditFilters
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
            <div className="p-4 space-y-2">
              {[...Array(10)].map((_, i) => (
                <Skeleton key={i} className="h-16" />
              ))}
            </div>
          ) : (
            <AuditList
              logs={data?.data || []}
              total={data?.total || 0}
              page={page}
              pages={data?.pages || 1}
              onPageChange={setPage}
            />
          )}
        </div>
      </div>
    </RequireRole>
  )
}
```

---

### S13.2: Item de Auditoria

**Arquivo:** `app/(dashboard)/auditoria/components/audit-item.tsx`

```typescript
'use client'

import { useState } from 'react'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import {
  Power,
  Flag,
  User,
  Settings,
  MessageCircle,
  RefreshCw,
  ChevronDown,
  ChevronUp
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface AuditLog {
  id: string
  action: string
  actor_email: string
  actor_role: string
  details: Record<string, any>
  created_at: string
}

interface Props {
  log: AuditLog
}

const ACTION_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  julia_toggle: Power,
  julia_pause: Power,
  feature_flag_update: Flag,
  rate_limit_update: Settings,
  manual_handoff: User,
  return_to_julia: RefreshCw,
  circuit_reset: RefreshCw
}

const ACTION_LABELS: Record<string, string> = {
  julia_toggle: 'Toggle Julia',
  julia_pause: 'Pausar Julia',
  feature_flag_update: 'Atualizar Feature Flag',
  rate_limit_update: 'Atualizar Rate Limit',
  manual_handoff: 'Handoff Manual',
  return_to_julia: 'Retornar para Julia',
  circuit_reset: 'Reset Circuit Breaker'
}

export function AuditItem({ log }: Props) {
  const [expanded, setExpanded] = useState(false)

  const Icon = ACTION_ICONS[log.action] || Settings
  const actionLabel = ACTION_LABELS[log.action] || log.action

  return (
    <div className="border-b last:border-b-0">
      <button
        className="w-full p-4 text-left hover:bg-muted/50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-full bg-muted">
            <Icon className="h-4 w-4" />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <p className="font-medium">{actionLabel}</p>
              <Badge variant="outline" className="text-xs">
                {log.actor_role}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              {log.actor_email}
            </p>
          </div>

          <div className="text-right">
            <p className="text-sm text-muted-foreground">
              {format(new Date(log.created_at), "dd/MM HH:mm", { locale: ptBR })}
            </p>
          </div>

          {expanded ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4">
          <div className="p-3 bg-muted rounded-lg">
            <p className="text-xs font-medium mb-2">Detalhes</p>
            <pre className="text-xs overflow-x-auto">
              {JSON.stringify(log.details, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}
```

---

### S13.3: Filtros de Auditoria

**Arquivo:** `app/(dashboard)/auditoria/components/audit-filters.tsx`

```typescript
'use client'

import { useState } from 'react'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

interface Filters {
  action?: string
  actor_email?: string
  from_date?: string
  to_date?: string
}

interface Props {
  filters: Filters
  onApply: (filters: Filters) => void
  onClear: () => void
}

const ACTIONS = [
  { value: 'julia_toggle', label: 'Toggle Julia' },
  { value: 'julia_pause', label: 'Pausar Julia' },
  { value: 'feature_flag_update', label: 'Feature Flag' },
  { value: 'rate_limit_update', label: 'Rate Limit' },
  { value: 'manual_handoff', label: 'Handoff Manual' },
  { value: 'return_to_julia', label: 'Retornar Julia' },
  { value: 'circuit_reset', label: 'Reset Circuit' }
]

export function AuditFilters({ filters, onApply, onClear }: Props) {
  const [localFilters, setLocalFilters] = useState(filters)

  return (
    <div className="space-y-6 py-4">
      <div className="space-y-2">
        <Label>Tipo de Ação</Label>
        <Select
          value={localFilters.action || 'all'}
          onValueChange={(v) => setLocalFilters(prev => ({
            ...prev,
            action: v === 'all' ? undefined : v
          }))}
        >
          <SelectTrigger>
            <SelectValue placeholder="Todas" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas</SelectItem>
            {ACTIONS.map((action) => (
              <SelectItem key={action.value} value={action.value}>
                {action.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>Email do Usuário</Label>
        <Input
          placeholder="Ex: usuario@email.com"
          value={localFilters.actor_email || ''}
          onChange={(e) => setLocalFilters(prev => ({
            ...prev,
            actor_email: e.target.value || undefined
          }))}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>Data Início</Label>
          <Input
            type="date"
            value={localFilters.from_date || ''}
            onChange={(e) => setLocalFilters(prev => ({
              ...prev,
              from_date: e.target.value || undefined
            }))}
          />
        </div>
        <div className="space-y-2">
          <Label>Data Fim</Label>
          <Input
            type="date"
            value={localFilters.to_date || ''}
            onChange={(e) => setLocalFilters(prev => ({
              ...prev,
              to_date: e.target.value || undefined
            }))}
          />
        </div>
      </div>

      <div className="flex gap-2 pt-4">
        <Button variant="outline" className="flex-1" onClick={onClear}>
          Limpar
        </Button>
        <Button className="flex-1" onClick={() => onApply(localFilters)}>
          Aplicar
        </Button>
      </div>
    </div>
  )
}
```

---

## Backend Endpoints

```python
# app/api/routes/dashboard/audit.py

@router.get("")
async def list_audit_logs(
    user: DashboardUser = Depends(require_manager()),
    page: int = Query(1),
    per_page: int = Query(50, le=100),
    action: Optional[str] = None,
    actor_email: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
):
    """Lista logs de auditoria."""

    query = supabase.table("audit_logs").select("*")

    if action:
        query = query.eq("action", action)
    if actor_email:
        query = query.ilike("actor_email", f"%{actor_email}%")
    if from_date:
        query = query.gte("created_at", from_date)
    if to_date:
        query = query.lte("created_at", to_date)

    # Contar total
    count_result = query.execute()
    total = len(count_result.data)

    # Paginar
    offset = (page - 1) * per_page
    result = query.order("created_at", desc=True).range(
        offset, offset + per_page - 1
    ).execute()

    return {
        "data": result.data,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page
    }

@router.get("/export")
async def export_audit_logs(
    user: DashboardUser = Depends(require_admin()),
    action: Optional[str] = None,
    actor_email: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
):
    """Exporta logs em CSV. Requer admin."""
    # Gera CSV
```

---

## Checklist Final

- [ ] Lista de logs paginada
- [ ] Filtros por ação, usuário, data
- [ ] Detalhes expandíveis
- [ ] Exportação CSV (admin only)
- [ ] Acesso restrito a manager+
- [ ] Mobile responsivo
