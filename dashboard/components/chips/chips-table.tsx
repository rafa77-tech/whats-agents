/**
 * Chips Table - Sprint 36
 *
 * Tabela principal de listagem de chips.
 */

'use client'

import { useState } from 'react'
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
import { ChipErrorsDialog } from './chip-errors-dialog'

interface ChipsTableProps {
  chips: ChipListItem[]
  selectedIds: string[]
  onSelectionChange: (ids: string[]) => void
  onRowClick?: (chip: ChipListItem) => void
  onRefresh?: () => void
}

const statusBadgeVariants: Record<string, string> = {
  active: 'bg-status-success text-status-success-foreground border-status-success-border',
  ready: 'bg-status-info text-status-info-foreground border-status-info-border',
  warming: 'bg-status-warning text-status-warning-foreground border-status-warning-border',
  degraded: 'bg-status-warning text-status-warning-foreground border-status-warning-border',
  paused: 'bg-status-neutral text-status-neutral-foreground border-muted',
  banned: 'bg-status-error text-status-error-foreground border-status-error-border',
  provisioned: 'bg-status-info text-status-info-foreground border-status-info-border',
  pending: 'bg-status-neutral text-muted-foreground border-muted',
  cancelled: 'bg-muted/50 text-muted-foreground border-muted',
  offline: 'bg-status-error text-status-error-foreground border-status-error-border',
}

const defaultBadgeVariant = 'bg-status-neutral text-muted-foreground border-muted'

const trustLevelColors: Record<string, string> = {
  verde: 'text-trust-verde-foreground',
  amarelo: 'text-trust-amarelo-foreground',
  laranja: 'text-trust-laranja-foreground',
  vermelho: 'text-trust-vermelho-foreground',
  critico: 'text-trust-critico-foreground',
}

const defaultTrustColor = 'text-muted-foreground'

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

export function ChipsTable({
  chips,
  selectedIds,
  onSelectionChange,
  onRowClick,
  onRefresh,
}: ChipsTableProps) {
  const [errorDialogChip, setErrorDialogChip] = useState<ChipListItem | null>(null)

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
    <div className="overflow-hidden rounded-lg border border-border">
      <Table>
        <TableHeader>
          <TableRow className="bg-muted/50">
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
              <TableCell colSpan={9} className="py-8 text-center text-muted-foreground">
                Nenhum chip encontrado
              </TableCell>
            </TableRow>
          ) : (
            chips.map((chip) => (
              <TableRow
                key={chip.id}
                className={cn(
                  'cursor-pointer hover:bg-muted/50',
                  selectedIds.includes(chip.id) && 'bg-accent/50'
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
                    <Phone className="h-4 w-4 text-muted-foreground" />
                    <span className="font-mono text-sm">{chip.telefone}</span>
                    {chip.hasActiveAlert && (
                      <AlertTriangle className="h-4 w-4 text-status-warning-foreground" />
                    )}
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
                  <span className="text-sm capitalize text-muted-foreground">
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
                      chip.responseRate >= 30
                        ? 'text-status-success-foreground'
                        : 'text-status-error-foreground'
                    )}
                  >
                    {chip.responseRate.toFixed(1)}%
                  </span>
                </TableCell>
                <TableCell className="text-right" onClick={(e) => e.stopPropagation()}>
                  {chip.errorsLast24h > 0 ? (
                    <button
                      onClick={() => setErrorDialogChip(chip)}
                      className={cn(
                        'cursor-pointer rounded px-2 py-0.5 text-sm underline-offset-2 hover:underline',
                        chip.errorsLast24h > 5
                          ? 'text-status-error-foreground hover:bg-status-error/10'
                          : 'text-status-warning-foreground hover:bg-status-warning/10'
                      )}
                      title="Clique para ver detalhes dos erros"
                    >
                      {chip.errorsLast24h}
                    </button>
                  ) : (
                    <span className="text-sm text-muted-foreground">0</span>
                  )}
                </TableCell>
                <TableCell>
                  <Link href={`/chips/${chip.id}` as Route} onClick={(e) => e.stopPropagation()}>
                    <ChevronRight className="h-4 w-4 text-muted-foreground hover:text-foreground" />
                  </Link>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>

      {/* Errors Dialog */}
      {errorDialogChip && (
        <ChipErrorsDialog
          chipId={errorDialogChip.id}
          chipName={errorDialogChip.telefone}
          errorCount={errorDialogChip.errorsLast24h}
          open={!!errorDialogChip}
          onOpenChange={(open) => !open && setErrorDialogChip(null)}
          {...(onRefresh && { onErrorsCleared: onRefresh })}
        />
      )}
    </div>
  )
}
