/**
 * Chips Filters - Sprint 36
 *
 * Barra de filtros para a lista de chips.
 */

'use client'

import { useState } from 'react'
import { ChipStatus } from '@/types/dashboard'
import { TrustLevelExtended, ChipsListParams } from '@/types/chips'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Search, X, SlidersHorizontal } from 'lucide-react'

interface ChipsFiltersProps {
  filters: Partial<ChipsListParams>
  onFiltersChange: (filters: Partial<ChipsListParams>) => void
}

const statusOptions: { value: ChipStatus; label: string }[] = [
  { value: 'active', label: 'Ativo' },
  { value: 'ready', label: 'Pronto' },
  { value: 'warming', label: 'Aquecendo' },
  { value: 'degraded', label: 'Degradado' },
  { value: 'paused', label: 'Pausado' },
  { value: 'banned', label: 'Banido' },
]

const trustLevelOptions: { value: TrustLevelExtended; label: string }[] = [
  { value: 'verde', label: 'Verde (80-100)' },
  { value: 'amarelo', label: 'Amarelo (60-79)' },
  { value: 'laranja', label: 'Laranja (40-59)' },
  { value: 'vermelho', label: 'Vermelho (20-39)' },
  { value: 'critico', label: 'Critico (0-19)' },
]

const sortOptions: { value: NonNullable<ChipsListParams['sortBy']>; label: string }[] = [
  { value: 'trust', label: 'Trust Score' },
  { value: 'status', label: 'Status' },
  { value: 'messages', label: 'Mensagens' },
  { value: 'errors', label: 'Erros' },
  { value: 'createdAt', label: 'Data Criacao' },
  { value: 'responseRate', label: 'Taxa Resposta' },
]

export function ChipsFilters({ filters, onFiltersChange }: ChipsFiltersProps) {
  const [searchValue, setSearchValue] = useState(filters.search || '')

  const handleSearchSubmit = () => {
    const { search: _search, ...rest } = filters
    if (searchValue) {
      onFiltersChange({ ...rest, search: searchValue })
    } else {
      onFiltersChange(rest)
    }
  }

  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearchSubmit()
    }
  }

  const handleStatusChange = (status: string) => {
    const { status: _status, ...rest } = filters
    if (status === 'all') {
      onFiltersChange(rest)
    } else {
      onFiltersChange({ ...rest, status: status as ChipStatus })
    }
  }

  const handleTrustLevelChange = (level: string) => {
    const { trustLevel: _trustLevel, ...rest } = filters
    if (level === 'all') {
      onFiltersChange(rest)
    } else {
      onFiltersChange({ ...rest, trustLevel: level as TrustLevelExtended })
    }
  }

  const handleAlertFilterChange = (value: string) => {
    const { hasAlert: _hasAlert, ...rest } = filters
    if (value === 'with') {
      onFiltersChange({ ...rest, hasAlert: true })
    } else if (value === 'without') {
      onFiltersChange({ ...rest, hasAlert: false })
    } else {
      onFiltersChange(rest)
    }
  }

  const handleSortChange = (sortBy: string) => {
    onFiltersChange({ ...filters, sortBy: sortBy as NonNullable<ChipsListParams['sortBy']> })
  }

  const handleOrderChange = (order: string) => {
    onFiltersChange({ ...filters, order: order as NonNullable<ChipsListParams['order']> })
  }

  const clearFilters = () => {
    setSearchValue('')
    onFiltersChange({})
  }

  const activeFilterCount = [
    filters.status,
    filters.trustLevel,
    filters.hasAlert,
    filters.search,
  ].filter((f) => f !== undefined).length

  return (
    <div className="space-y-4">
      {/* Search bar */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <Input
            placeholder="Buscar por telefone..."
            value={searchValue}
            onChange={(e) => setSearchValue(e.target.value)}
            onKeyDown={handleSearchKeyDown}
            className="pl-10"
          />
        </div>
        <Button onClick={handleSearchSubmit}>Buscar</Button>
      </div>

      {/* Filter row */}
      <div className="flex flex-wrap items-center gap-2">
        {/* Status filter */}
        <Select value={(filters.status as string) || 'all'} onValueChange={handleStatusChange}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos os status</SelectItem>
            {statusOptions.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Trust level filter */}
        <Select
          value={(filters.trustLevel as string) || 'all'}
          onValueChange={handleTrustLevelChange}
        >
          <SelectTrigger className="w-44">
            <SelectValue placeholder="Trust Level" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos os niveis</SelectItem>
            {trustLevelOptions.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Alert filter */}
        <Select
          value={
            filters.hasAlert === true ? 'with' : filters.hasAlert === false ? 'without' : 'all'
          }
          onValueChange={handleAlertFilterChange}
        >
          <SelectTrigger className="w-36">
            <SelectValue placeholder="Alertas" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="with">Com alertas</SelectItem>
            <SelectItem value="without">Sem alertas</SelectItem>
          </SelectContent>
        </Select>

        {/* Sort */}
        <div className="ml-auto flex items-center gap-1">
          <Select value={filters.sortBy || 'trust'} onValueChange={handleSortChange}>
            <SelectTrigger className="w-36">
              <SlidersHorizontal className="mr-2 h-4 w-4" />
              <SelectValue placeholder="Ordenar" />
            </SelectTrigger>
            <SelectContent>
              {sortOptions.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={filters.order || 'desc'} onValueChange={handleOrderChange}>
            <SelectTrigger className="w-28">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="asc">Crescente</SelectItem>
              <SelectItem value="desc">Decrescente</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Clear filters */}
        {activeFilterCount > 0 && (
          <Button variant="ghost" size="sm" onClick={clearFilters}>
            <X className="mr-1 h-4 w-4" />
            Limpar ({activeFilterCount})
          </Button>
        )}
      </div>
    </div>
  )
}
