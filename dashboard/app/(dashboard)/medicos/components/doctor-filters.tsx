'use client'

import { useState } from 'react'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { STAGE_OPTIONS, ESPECIALIDADE_OPTIONS } from '@/lib/medicos'
import type { DoctorFilters as Filters } from '@/lib/medicos'

interface Props {
  filters: Filters
  onApply: (filters: Filters) => void
  onClear: () => void
}

export function DoctorFilters({ filters, onApply, onClear }: Props) {
  const [localFilters, setLocalFilters] = useState<Filters>(filters)

  const handleApply = () => {
    onApply(localFilters)
  }

  return (
    <div className="space-y-6 py-4">
      <div className="space-y-2">
        <Label>Etapa do Funil</Label>
        <Select
          value={localFilters.stage_jornada || 'all'}
          onValueChange={(value) =>
            setLocalFilters((prev) => ({
              ...prev,
              stage_jornada: value === 'all' ? undefined : value,
            }))
          }
        >
          <SelectTrigger>
            <SelectValue placeholder="Todas" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas</SelectItem>
            {STAGE_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>Especialidade</Label>
        <Select
          value={localFilters.especialidade || 'all'}
          onValueChange={(value) =>
            setLocalFilters((prev) => ({
              ...prev,
              especialidade: value === 'all' ? undefined : value,
            }))
          }
        >
          <SelectTrigger>
            <SelectValue placeholder="Todas" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas</SelectItem>
            {ESPECIALIDADE_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex items-center justify-between">
        <Label htmlFor="opt-out-filter">Apenas Opt-out</Label>
        <Switch
          id="opt-out-filter"
          checked={localFilters.opt_out || false}
          onCheckedChange={(checked) =>
            setLocalFilters((prev) => ({
              ...prev,
              opt_out: checked || undefined,
            }))
          }
        />
      </div>

      <div className="flex gap-2 pt-4">
        <Button variant="outline" className="flex-1" onClick={onClear}>
          Limpar
        </Button>
        <Button className="flex-1" onClick={handleApply}>
          Aplicar
        </Button>
      </div>
    </div>
  )
}
