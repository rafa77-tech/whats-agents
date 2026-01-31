/**
 * Chips Table - Sprint 36
 *
 * Tabela principal de listagem de chips.
 */

'use client'

import Link from 'next/link'
import type { Route } from 'next'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { ChipListItem } from '@/types/chips'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { cn } from '@/lib/utils'
import { AlertTriangle, ChevronRight, Phone } from 'lucide-react'

interface ChipsTableProps {
  chips: ChipListItem[]
  selectedIds: string[]
  onSelectionChange: (ids: string[]) => void
  onRowClick?: (chip: ChipListItem) => void
}

const statusBadgeVariants: Record<string, string> = {
  active: 'bg-green-100 text-green-800 border-green-200',
  ready: 'bg-blue-100 text-blue-800 border-blue-200',
  warming: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  degraded: 'bg-orange-100 text-orange-800 border-orange-200',
  paused: 'bg-gray-100 text-gray-800 border-gray-200',
  banned: 'bg-red-100 text-red-800 border-red-200',
  provisioned: 'bg-purple-100 text-purple-800 border-purple-200',
  pending: 'bg-gray-100 text-gray-600 border-gray-200',
  cancelled: 'bg-gray-50 text-gray-500 border-gray-200',
  offline: 'bg-red-100 text-red-800 border-red-200',
}

const defaultBadgeVariant = 'bg-gray-100 text-gray-600 border-gray-200'

const trustLevelColors: Record<string, string> = {
  verde: 'text-green-600',
  amarelo: 'text-yellow-600',
  laranja: 'text-orange-600',
  vermelho: 'text-red-600',
  critico: 'text-gray-600',
}

const defaultTrustColor = 'text-gray-600'

const statusLabels: Record<string, string> = {
  active: 'Ativo',
  ready: 'Pronto',
  warming: 'Aquecendo',
  degraded: 'Degradado',
  paused: 'Pausado',
  banned: 'Banido',
  provisioned: 'Provisionado',
  pending: 'Pendente',
  cancelled: 'Cancelado',
  offline: 'Offline',
}

const defaultStatusLabel = 'Desconhecido'

export function ChipsTable({ chips, selectedIds, onSelectionChange, onRowClick }: ChipsTableProps) {
  const allSelected = chips.length > 0 && selectedIds.length === chips.length
  const someSelected = selectedIds.length > 0 && selectedIds.length < chips.length

  const handleSelectAll = () => {
    if (allSelected) {
      onSelectionChange([])
    } else {
      onSelectionChange(chips.map((c) => c.id))
    }
  }

  const handleSelectOne = (id: string) => {
    if (selectedIds.includes(id)) {
      onSelectionChange(selectedIds.filter((i) => i !== id))
    } else {
      onSelectionChange([...selectedIds, id])
    }
  }

  return (
    <div className="overflow-hidden rounded-lg border border-gray-200">
      <Table>
        <TableHeader>
          <TableRow className="bg-gray-50">
            <TableHead className="w-12">
              <Checkbox
                checked={allSelected}
                // @ts-expect-error - indeterminate is valid but not typed
                indeterminate={someSelected || undefined}
                onCheckedChange={handleSelectAll}
                aria-label="Selecionar todos"
              />
            </TableHead>
            <TableHead>Telefone</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Trust Score</TableHead>
            <TableHead>Fase</TableHead>
            <TableHead className="text-right">Msgs Hoje</TableHead>
            <TableHead className="text-right">Taxa Resp.</TableHead>
            <TableHead className="text-right">Erros 24h</TableHead>
            <TableHead className="w-8"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {chips.length === 0 ? (
            <TableRow>
              <TableCell colSpan={9} className="py-8 text-center text-gray-500">
                Nenhum chip encontrado
              </TableCell>
            </TableRow>
          ) : (
            chips.map((chip) => (
              <TableRow
                key={chip.id}
                className={cn(
                  'cursor-pointer hover:bg-gray-50',
                  selectedIds.includes(chip.id) && 'bg-blue-50'
                )}
                onClick={() => onRowClick?.(chip)}
              >
                <TableCell onClick={(e) => e.stopPropagation()}>
                  <Checkbox
                    checked={selectedIds.includes(chip.id)}
                    onCheckedChange={() => handleSelectOne(chip.id)}
                    aria-label={`Selecionar ${chip.telefone}`}
                  />
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Phone className="h-4 w-4 text-gray-400" />
                    <span className="font-mono text-sm">{chip.telefone}</span>
                    {chip.hasActiveAlert && <AlertTriangle className="h-4 w-4 text-orange-500" />}
                  </div>
                </TableCell>
                <TableCell>
                  <Badge
                    variant="outline"
                    className={cn(
                      'capitalize',
                      statusBadgeVariants[chip.status] || defaultBadgeVariant
                    )}
                  >
                    {statusLabels[chip.status] || defaultStatusLabel}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">
                  <span
                    className={cn(
                      'font-medium',
                      trustLevelColors[chip.trustLevel] || defaultTrustColor
                    )}
                  >
                    {chip.trustScore}
                  </span>
                </TableCell>
                <TableCell>
                  <span className="text-sm capitalize text-gray-600">
                    {chip.warmupPhase?.replace(/_/g, ' ') || '-'}
                  </span>
                </TableCell>
                <TableCell className="text-right">
                  <span className="text-sm">
                    {chip.messagesToday}/{chip.dailyLimit}
                  </span>
                </TableCell>
                <TableCell className="text-right">
                  <span
                    className={cn(
                      'text-sm',
                      chip.responseRate >= 30 ? 'text-green-600' : 'text-red-600'
                    )}
                  >
                    {chip.responseRate.toFixed(1)}%
                  </span>
                </TableCell>
                <TableCell className="text-right">
                  <span
                    className={cn(
                      'text-sm',
                      chip.errorsLast24h > 5 ? 'text-red-600' : 'text-gray-600'
                    )}
                  >
                    {chip.errorsLast24h}
                  </span>
                </TableCell>
                <TableCell>
                  <Link href={`/chips/${chip.id}` as Route} onClick={(e) => e.stopPropagation()}>
                    <ChevronRight className="h-4 w-4 text-gray-400 hover:text-gray-600" />
                  </Link>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  )
}
