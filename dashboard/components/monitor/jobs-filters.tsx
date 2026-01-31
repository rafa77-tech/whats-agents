/**
 * Jobs Filters - Sprint 42
 *
 * Filtros para a lista de jobs.
 */

'use client'

import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Search } from 'lucide-react'
import type { MonitorFilters, JobStatusFilter, TimeRangeFilter, JobCategory } from '@/types/monitor'

interface JobsFiltersProps {
  filters: MonitorFilters
  onFiltersChange: (filters: MonitorFilters) => void
}

const STATUS_OPTIONS: { value: JobStatusFilter; label: string }[] = [
  { value: 'all', label: 'Todos os Status' },
  { value: 'running', label: 'Executando' },
  { value: 'success', label: 'Sucesso' },
  { value: 'error', label: 'Erro' },
  { value: 'timeout', label: 'Timeout' },
  { value: 'stale', label: 'Atrasados' },
]

const TIME_OPTIONS: { value: TimeRangeFilter; label: string }[] = [
  { value: '1h', label: 'Ultima hora' },
  { value: '6h', label: 'Ultimas 6h' },
  { value: '24h', label: 'Ultimas 24h' },
]

const CATEGORY_OPTIONS: { value: JobCategory | 'all'; label: string }[] = [
  { value: 'all', label: 'Todas Categorias' },
  { value: 'critical', label: 'Criticos' },
  { value: 'frequent', label: 'Frequentes' },
  { value: 'hourly', label: 'Horarios' },
  { value: 'daily', label: 'Diarios' },
  { value: 'weekly', label: 'Semanais' },
]

export function JobsFilters({ filters, onFiltersChange }: JobsFiltersProps) {
  const updateFilter = <K extends keyof MonitorFilters>(key: K, value: MonitorFilters[K]) => {
    onFiltersChange({ ...filters, [key]: value })
  }

  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
      {/* Search */}
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <Input
          placeholder="Buscar por nome..."
          value={filters.search}
          onChange={(e) => updateFilter('search', e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Status filter */}
      <Select
        value={filters.status}
        onValueChange={(v) => updateFilter('status', v as JobStatusFilter)}
      >
        <SelectTrigger className="w-full sm:w-[160px]">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {STATUS_OPTIONS.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Category filter */}
      <Select
        value={filters.category}
        onValueChange={(v) => updateFilter('category', v as JobCategory | 'all')}
      >
        <SelectTrigger className="w-full sm:w-[160px]">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {CATEGORY_OPTIONS.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Time range buttons */}
      <div className="flex gap-1 rounded-lg bg-gray-100 p-1">
        {TIME_OPTIONS.map((opt) => (
          <Button
            key={opt.value}
            variant={filters.timeRange === opt.value ? 'default' : 'ghost'}
            size="sm"
            onClick={() => updateFilter('timeRange', opt.value)}
            className="px-3"
          >
            {opt.label}
          </Button>
        ))}
      </div>
    </div>
  )
}
