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

const statusConfig: Record<ChipStatus, { label: string; className: string }> = {
  active: {
    label: 'Active',
    className: 'bg-green-100 text-green-700 border-green-200',
  },
  ready: {
    label: 'Ready',
    className: 'bg-blue-100 text-blue-700 border-blue-200',
  },
  warming: {
    label: 'Warming',
    className: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  },
  degraded: {
    label: 'Degraded',
    className: 'bg-orange-100 text-orange-700 border-orange-200',
  },
  paused: {
    label: 'Paused',
    className: 'bg-gray-100 text-gray-700 border-gray-200',
  },
  banned: {
    label: 'Banned',
    className: 'bg-red-100 text-red-700 border-red-200',
  },
  provisioned: {
    label: 'Prov.',
    className: 'bg-gray-100 text-gray-600 border-gray-200',
  },
  pending: {
    label: 'Pending',
    className: 'bg-gray-100 text-gray-600 border-gray-200',
  },
  cancelled: {
    label: 'Cancelled',
    className: 'bg-gray-100 text-gray-400 border-gray-200',
  },
}

const trustColors: Record<TrustLevel, string> = {
  verde: 'text-green-600 bg-green-100',
  amarelo: 'text-yellow-600 bg-yellow-100',
  laranja: 'text-orange-600 bg-orange-100',
  vermelho: 'text-red-600 bg-red-100',
}

function TrustBadge({ score, level }: { score: number; level: TrustLevel }) {
  return (
    <span
      className={`inline-flex items-center rounded px-2 py-0.5 text-sm font-medium ${trustColors[level]}`}
    >
      {score}
    </span>
  )
}

function StatusBadge({ status }: { status: ChipStatus }) {
  const config = statusConfig[status]
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
        <h4 className="text-sm font-medium text-gray-700">Chips Detalhados</h4>
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
            <TableRow className="bg-gray-50">
              <TableHead className="w-[120px]">Numero</TableHead>
              <TableHead className="w-[90px]">Status</TableHead>
              <TableHead className="w-[70px]">Trust</TableHead>
              <TableHead className="w-[90px]">Msgs Hoje</TableHead>
              <TableHead className="w-[80px]">Tx Resp</TableHead>
              <TableHead className="w-[60px]">Erros</TableHead>
              <TableHead>Alertas</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {displayedChips.map((chip) => (
              <TableRow key={chip.id} className={chip.hasActiveAlert ? 'bg-red-50' : ''}>
                <TableCell className="font-medium">{chip.name}</TableCell>
                <TableCell>
                  <StatusBadge status={chip.status} />
                </TableCell>
                <TableCell>
                  <TrustBadge score={chip.trustScore} level={chip.trustLevel} />
                </TableCell>
                <TableCell>
                  {chip.status === 'active' || chip.status === 'warming' ? (
                    <span className="text-gray-600">
                      {chip.messagesToday}/{chip.dailyLimit}
                    </span>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </TableCell>
                <TableCell>
                  {chip.responseRate > 0 ? (
                    <span
                      className={
                        chip.responseRate >= 90
                          ? 'text-green-600'
                          : chip.responseRate >= 80
                            ? 'text-yellow-600'
                            : 'text-red-600'
                      }
                    >
                      {chip.responseRate.toFixed(1)}%
                    </span>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </TableCell>
                <TableCell>
                  <span
                    className={
                      chip.errorsLast24h > 0 ? 'font-medium text-red-600' : 'text-gray-400'
                    }
                  >
                    {chip.errorsLast24h}
                  </span>
                </TableCell>
                <TableCell>
                  {chip.hasActiveAlert ? (
                    <div className="flex items-center gap-1 text-orange-600">
                      <AlertTriangle className="h-4 w-4" />
                      <span className="text-xs">{chip.alertMessage}</span>
                    </div>
                  ) : chip.warmingDay ? (
                    <span className="text-xs text-blue-600">Dia {chip.warmingDay}/21</span>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
