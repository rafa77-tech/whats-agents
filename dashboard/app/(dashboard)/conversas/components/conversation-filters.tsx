'use client'

import { useState } from 'react'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

interface Filters {
  status?: string | undefined
  controlled_by?: string | undefined
}

interface Props {
  filters: Filters
  onApply: (filters: Filters) => void
  onClear: () => void
}

export function ConversationFilters({ filters, onApply, onClear }: Props) {
  const [localFilters, setLocalFilters] = useState(filters)

  const handleApply = () => {
    onApply(localFilters)
  }

  return (
    <div className="space-y-6 py-4">
      <div className="space-y-2">
        <Label>Status</Label>
        <Select
          value={localFilters.status || 'all'}
          onValueChange={(value) =>
            setLocalFilters((prev) => ({
              ...prev,
              status: value === 'all' ? undefined : value,
            }))
          }
        >
          <SelectTrigger>
            <SelectValue placeholder="Todos" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="active">Ativas</SelectItem>
            <SelectItem value="closed">Fechadas</SelectItem>
            <SelectItem value="waiting">Aguardando</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>Controle</Label>
        <Select
          value={localFilters.controlled_by || 'all'}
          onValueChange={(value) =>
            setLocalFilters((prev) => ({
              ...prev,
              controlled_by: value === 'all' ? undefined : value,
            }))
          }
        >
          <SelectTrigger>
            <SelectValue placeholder="Todos" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="julia">Julia (IA)</SelectItem>
            <SelectItem value="human">Humano (Handoff)</SelectItem>
          </SelectContent>
        </Select>
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
