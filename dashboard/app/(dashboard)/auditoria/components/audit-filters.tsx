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
  action?: string | undefined
  actor_email?: string | undefined
  from_date?: string | undefined
  to_date?: string | undefined
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
  { value: 'circuit_reset', label: 'Reset Circuit' },
  { value: 'create_campaign', label: 'Criar Campanha' },
  { value: 'start_campaign', label: 'Iniciar Campanha' },
  { value: 'pause_campaign', label: 'Pausar Campanha' },
]

export function AuditFilters({ filters, onApply, onClear }: Props) {
  const [localFilters, setLocalFilters] = useState<Filters>(filters)

  return (
    <div className="space-y-6 py-4">
      <div className="space-y-2">
        <Label>Tipo de Acao</Label>
        <Select
          value={localFilters.action ?? 'all'}
          onValueChange={(v) =>
            setLocalFilters((prev) => ({
              ...prev,
              action: v === 'all' ? undefined : v,
            }))
          }
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
        <Label>Email do Usuario</Label>
        <Input
          placeholder="Ex: usuario@email.com"
          value={localFilters.actor_email ?? ''}
          onChange={(e) =>
            setLocalFilters((prev) => ({
              ...prev,
              actor_email: e.target.value || undefined,
            }))
          }
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>Data Inicio</Label>
          <Input
            type="date"
            value={localFilters.from_date ?? ''}
            onChange={(e) =>
              setLocalFilters((prev) => ({
                ...prev,
                from_date: e.target.value || undefined,
              }))
            }
          />
        </div>
        <div className="space-y-2">
          <Label>Data Fim</Label>
          <Input
            type="date"
            value={localFilters.to_date ?? ''}
            onChange={(e) =>
              setLocalFilters((prev) => ({
                ...prev,
                to_date: e.target.value || undefined,
              }))
            }
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
