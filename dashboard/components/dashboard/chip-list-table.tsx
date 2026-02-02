'use client'

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { type ChipDetail, type ChipStatus, type TrustLevel } from '@/types/dashboard'
import { AlertTriangle, ChevronRight } from 'lucide-react'
import Link from 'next/link'
import type { Route } from 'next'

interface ChipListTableProps {
  chips: ChipDetail[]
  maxItems?: number
  showViewAll?: boolean
}

const statusConfig: Record<string, { label: string; className: string }> = {
  active: {
    label: 'Active',
    className: 'bg-status-success text-status-success-foreground border-status-success-border',
  },
  ready: {
    label: 'Ready',
    className: 'bg-status-info text-status-info-foreground border-status-info-border',
  },
  warming: {
    label: 'Warming',
    className: 'bg-status-warning text-status-warning-foreground border-status-warning-border',
  },
  degraded: {
    label: 'Degraded',
    className: 'bg-trust-laranja text-trust-laranja-foreground border-trust-laranja',
  },
  paused: {
    label: 'Paused',
    className: 'bg-status-neutral text-status-neutral-foreground border-border',
  },
  banned: {
    label: 'Banned',
    className: 'bg-status-error text-status-error-foreground border-status-error-border',
  },
  provisioned: {
    label: 'Prov.',
    className: 'bg-status-neutral text-muted-foreground border-border',
  },
  pending: {
    label: 'Pending',
    className: 'bg-status-neutral text-muted-foreground border-border',
  },
  cancelled: {
    label: 'Cancelled',
    className: 'bg-status-neutral text-muted-foreground/70 border-border',
  },
  offline: {
    label: 'Offline',
    className: 'bg-status-error text-status-error-foreground border-status-error-border',
  },
}

const defaultStatusConfig = {
  label: 'Unknown',
  className: 'bg-status-neutral text-muted-foreground border-border',
}

const trustColors: Record<string, string> = {
  verde: 'text-status-success-foreground bg-status-success',
  amarelo: 'text-status-warning-foreground bg-status-warning',
  laranja: 'text-trust-laranja-foreground bg-trust-laranja',
  vermelho: 'text-trust-vermelho-foreground bg-trust-vermelho',
  critico: 'text-trust-critico-foreground bg-trust-critico',
}

const defaultTrustColor = 'text-muted-foreground bg-status-neutral'

function TrustBadge({ score, level }: { score: number; level: TrustLevel }) {
  const colorClass = trustColors[level] || defaultTrustColor
  return (
    <span
      className={`inline-flex items-center rounded px-2 py-0.5 text-sm font-medium ${colorClass}`}
    >
      {score}
    </span>
  )
}

function StatusBadge({ status }: { status: ChipStatus }) {
  const config = statusConfig[status] || defaultStatusConfig
  return (
    <Badge variant="outline" className={config.className}>
      {config.label}
    </Badge>
  )
}

export function ChipListTable({ chips, maxItems = 5, showViewAll = true }: ChipListTableProps) {
  // Ordenar: alertas primeiro, depois por trust (menor primeiro)
  const sortedChips = [...chips].sort((a, b) => {
    if (a.hasActiveAlert && !b.hasActiveAlert) return -1
    if (!a.hasActiveAlert && b.hasActiveAlert) return 1
    return a.trustScore - b.trustScore
  })

  const displayedChips = sortedChips.slice(0, maxItems)

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-foreground/80">Chips Detalhados</h4>
        {showViewAll && (
          <Link href={'/chips' as Route}>
            <Button variant="ghost" size="sm" className="text-sm">
              Ver todos
              <ChevronRight className="ml-1 h-4 w-4" />
            </Button>
          </Link>
        )}
      </div>

      <div className="overflow-hidden rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/50">
              <TableHead className="w-[120px]">Numero</TableHead>
              <TableHead className="w-[90px]">Status</TableHead>
              <TableHead className="w-[70px]">Trust</TableHead>
              <TableHead className="w-[90px]">Msgs Hoje</TableHead>
              <TableHead className="w-[80px]">Tx Resp</TableHead>
              <TableHead className="w-[60px]">Erros</TableHead>
              <TableHead>Alertas</TableHead>
              <TableHead className="w-8"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {displayedChips.map((chip) => (
              <TableRow
                key={chip.id}
                className={`cursor-pointer hover:bg-muted/50 ${chip.hasActiveAlert ? 'bg-status-error/10 hover:bg-status-error/20' : ''}`}
              >
                <TableCell className="font-medium">
                  <Link href={`/chips/${chip.id}` as Route} className="block">
                    {chip.name}
                  </Link>
                </TableCell>
                <TableCell>
                  <Link href={`/chips/${chip.id}` as Route} className="block">
                    <StatusBadge status={chip.status} />
                  </Link>
                </TableCell>
                <TableCell>
                  <Link href={`/chips/${chip.id}` as Route} className="block">
                    <TrustBadge score={chip.trustScore} level={chip.trustLevel} />
                  </Link>
                </TableCell>
                <TableCell>
                  <Link href={`/chips/${chip.id}` as Route} className="block">
                    <span className="text-muted-foreground">
                      {chip.messagesToday}/{chip.dailyLimit}
                    </span>
                  </Link>
                </TableCell>
                <TableCell>
                  <Link href={`/chips/${chip.id}` as Route} className="block">
                    {chip.responseRate > 0 ? (
                      <span
                        className={
                          chip.responseRate >= 90
                            ? 'text-status-success-foreground'
                            : chip.responseRate >= 80
                              ? 'text-status-warning-foreground'
                              : 'text-status-error-foreground'
                        }
                      >
                        {chip.responseRate.toFixed(1)}%
                      </span>
                    ) : (
                      <span className="text-muted-foreground/70">-</span>
                    )}
                  </Link>
                </TableCell>
                <TableCell>
                  <Link href={`/chips/${chip.id}` as Route} className="block">
                    <span
                      className={
                        chip.errorsLast24h > 0
                          ? 'font-medium text-status-error-foreground'
                          : 'text-muted-foreground/70'
                      }
                    >
                      {chip.errorsLast24h}
                    </span>
                  </Link>
                </TableCell>
                <TableCell>
                  <Link href={`/chips/${chip.id}` as Route} className="block">
                    {chip.hasActiveAlert ? (
                      <div className="flex items-center gap-1 text-trust-laranja-foreground">
                        <AlertTriangle className="h-4 w-4" />
                        <span className="text-xs">{chip.alertMessage}</span>
                      </div>
                    ) : chip.warmingDay ? (
                      <span className="text-xs text-status-info-foreground">
                        Dia {chip.warmingDay}/21
                      </span>
                    ) : (
                      <span className="text-muted-foreground/70">-</span>
                    )}
                  </Link>
                </TableCell>
                <TableCell>
                  <Link href={`/chips/${chip.id}` as Route}>
                    <ChevronRight className="h-4 w-4 text-muted-foreground/70 hover:text-muted-foreground" />
                  </Link>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
