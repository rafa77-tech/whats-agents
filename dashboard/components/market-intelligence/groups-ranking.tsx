/**
 * GroupsRanking - Sprint 46
 *
 * Tabela de ranking de grupos por qualidade e volume de vagas.
 */

'use client'

import { useState, useMemo } from 'react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Circle,
  CheckCircle2,
  Clock,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import type { GrupoRanking } from '@/types/market-intelligence'

// =============================================================================
// TYPES
// =============================================================================

export interface GroupsRankingProps {
  data: GrupoRanking[] | null
  isLoading?: boolean
  className?: string
  limit?: number
  onGroupClick?: (grupoId: string) => void
  title?: string
}

type SortKey = 'scoreQualidade' | 'vagasImportadas30d' | 'valorMedio30d' | 'ultimaVagaEm'
type SortOrder = 'asc' | 'desc'

// =============================================================================
// CONSTANTS
// =============================================================================

const ITEMS_PER_PAGE = 10

// =============================================================================
// HELPERS
// =============================================================================

function formatNumber(value: number | null): string {
  if (value === null) return '-'
  return value.toLocaleString('pt-BR')
}

function formatCurrency(reais: number | null): string {
  if (reais === null) return '-'
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 0,
  }).format(reais)
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return 'Nunca'
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays === 0) return 'Hoje'
  if (diffDays === 1) return 'Ontem'
  if (diffDays < 7) return `${diffDays} dias atras`
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} sem atras`
  return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
}

function getScoreBadgeVariant(score: number): 'default' | 'secondary' | 'destructive' | 'outline' {
  if (score >= 70) return 'default' // verde
  if (score >= 40) return 'secondary' // amarelo
  return 'destructive' // vermelho
}

// =============================================================================
// SUBCOMPONENTS
// =============================================================================

function GroupsRankingSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-48" />
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

interface SortButtonProps {
  label: string
  sortKey: SortKey
  currentSort: SortKey
  currentOrder: SortOrder
  onSort: (key: SortKey) => void
}

function SortButton({ label, sortKey, currentSort, currentOrder, onSort }: SortButtonProps) {
  const isActive = currentSort === sortKey

  return (
    <Button variant="ghost" size="sm" className="-ml-3 h-8" onClick={() => onSort(sortKey)}>
      {label}
      {isActive ? (
        currentOrder === 'desc' ? (
          <ArrowDown className="ml-1 h-4 w-4" />
        ) : (
          <ArrowUp className="ml-1 h-4 w-4" />
        )
      ) : (
        <ArrowUpDown className="ml-1 h-4 w-4 opacity-50" />
      )}
    </Button>
  )
}

interface ScoreBadgeProps {
  score: number
}

function ScoreBadge({ score }: ScoreBadgeProps) {
  return (
    <Badge variant={getScoreBadgeVariant(score)} className="font-mono">
      {score}
    </Badge>
  )
}

interface StatusIconProps {
  ativo: boolean
}

function StatusIcon({ ativo }: StatusIconProps) {
  if (ativo) {
    return <CheckCircle2 className="h-4 w-4 text-green-500" aria-label="Grupo ativo" />
  }
  return <Circle className="h-4 w-4 text-muted-foreground" aria-label="Grupo inativo" />
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export function GroupsRanking({
  data,
  isLoading = false,
  className,
  limit,
  onGroupClick,
  title = 'Ranking de Grupos',
}: GroupsRankingProps) {
  // Estado de ordenacao
  const [sortKey, setSortKey] = useState<SortKey>('scoreQualidade')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')
  const [currentPage, setCurrentPage] = useState(1)

  // Handler de ordenacao
  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortOrder((prev) => (prev === 'desc' ? 'asc' : 'desc'))
    } else {
      setSortKey(key)
      setSortOrder('desc')
    }
    setCurrentPage(1) // Reset para primeira pagina
  }

  // Ordenar e paginar dados
  const sortedData = useMemo(() => {
    if (!data) return []

    const sorted = [...data].sort((a, b) => {
      let aVal: number | string | null
      let bVal: number | string | null

      switch (sortKey) {
        case 'scoreQualidade':
          aVal = a.scoreQualidade
          bVal = b.scoreQualidade
          break
        case 'vagasImportadas30d':
          aVal = a.vagasImportadas30d
          bVal = b.vagasImportadas30d
          break
        case 'valorMedio30d':
          aVal = a.valorMedio30d ?? 0
          bVal = b.valorMedio30d ?? 0
          break
        case 'ultimaVagaEm':
          aVal = a.ultimaVagaEm ?? ''
          bVal = b.ultimaVagaEm ?? ''
          break
        default:
          return 0
      }

      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sortOrder === 'desc' ? bVal.localeCompare(aVal) : aVal.localeCompare(bVal)
      }

      return sortOrder === 'desc'
        ? (bVal as number) - (aVal as number)
        : (aVal as number) - (bVal as number)
    })

    // Aplicar limite se especificado
    if (limit) {
      return sorted.slice(0, limit)
    }

    return sorted
  }, [data, sortKey, sortOrder, limit])

  // Paginacao
  const paginatedData = useMemo(() => {
    if (limit) return sortedData // Se tem limite, nao pagina

    const start = (currentPage - 1) * ITEMS_PER_PAGE
    const end = start + ITEMS_PER_PAGE
    return sortedData.slice(start, end)
  }, [sortedData, currentPage, limit])

  const totalPages = limit ? 1 : Math.ceil(sortedData.length / ITEMS_PER_PAGE)

  // Loading state
  if (isLoading) {
    return <GroupsRankingSkeleton />
  }

  // Empty state
  if (!data || data.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex h-[200px] items-center justify-center text-muted-foreground">
            Nenhum grupo encontrado
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">#</TableHead>
                <TableHead>Grupo</TableHead>
                <TableHead className="w-24">
                  <SortButton
                    label="Score"
                    sortKey="scoreQualidade"
                    currentSort={sortKey}
                    currentOrder={sortOrder}
                    onSort={handleSort}
                  />
                </TableHead>
                <TableHead className="w-24">
                  <SortButton
                    label="Vagas"
                    sortKey="vagasImportadas30d"
                    currentSort={sortKey}
                    currentOrder={sortOrder}
                    onSort={handleSort}
                  />
                </TableHead>
                <TableHead className="w-28">
                  <SortButton
                    label="Valor Med."
                    sortKey="valorMedio30d"
                    currentSort={sortKey}
                    currentOrder={sortOrder}
                    onSort={handleSort}
                  />
                </TableHead>
                <TableHead className="w-28">
                  <SortButton
                    label="Ult. Vaga"
                    sortKey="ultimaVagaEm"
                    currentSort={sortKey}
                    currentOrder={sortOrder}
                    onSort={handleSort}
                  />
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedData.map((grupo, index) => {
                const position = limit ? index + 1 : (currentPage - 1) * ITEMS_PER_PAGE + index + 1

                return (
                  <TableRow
                    key={grupo.grupoId}
                    className={cn(onGroupClick && 'cursor-pointer hover:bg-muted/50')}
                    onClick={() => onGroupClick?.(grupo.grupoId)}
                  >
                    <TableCell className="font-medium text-muted-foreground">{position}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <StatusIcon ativo={grupo.grupoAtivo} />
                        <div>
                          <div className="line-clamp-1 font-medium">{grupo.grupoNome}</div>
                          {grupo.grupoRegiao && (
                            <div className="text-xs text-muted-foreground">{grupo.grupoRegiao}</div>
                          )}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <ScoreBadge score={grupo.scoreQualidade} />
                    </TableCell>
                    <TableCell className="font-medium">
                      {formatNumber(grupo.vagasImportadas30d)}
                    </TableCell>
                    <TableCell>{formatCurrency(grupo.valorMedio30d)}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1 text-sm text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        {formatDate(grupo.ultimaVagaEm)}
                      </div>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>

        {/* Paginacao */}
        {!limit && totalPages > 1 && (
          <div className="mt-4 flex items-center justify-between">
            <div className="text-sm text-muted-foreground">
              Mostrando {(currentPage - 1) * ITEMS_PER_PAGE + 1} -{' '}
              {Math.min(currentPage * ITEMS_PER_PAGE, sortedData.length)} de {sortedData.length}
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
              >
                <ChevronLeft className="h-4 w-4" />
                Anterior
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
              >
                Proximo
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default GroupsRanking
