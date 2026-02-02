'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Loader2, Plus, Check, X, XCircle } from 'lucide-react'
import {
  useSuggestions,
  formatDateBR,
  SUGGESTION_STATUS_FILTER_OPTIONS,
  SUGGESTION_STATUS_COLORS,
  SUGGESTION_STATUS_LABELS,
  SUGGESTION_TYPE_COLORS,
} from '@/lib/qualidade'
import type { SuggestionStatus, SuggestionType } from '@/lib/qualidade'
import { NewSuggestionModal } from './new-suggestion-modal'

export function SuggestionsList() {
  const [filterStatus, setFilterStatus] = useState<string>('pending')
  const [isNewOpen, setIsNewOpen] = useState(false)

  const { suggestions, loading, refresh, updateStatus, actionLoading } =
    useSuggestions(filterStatus)

  const getStatusBadge = (status: SuggestionStatus) => {
    const colorClass = SUGGESTION_STATUS_COLORS[status] || 'bg-gray-100 text-gray-800'
    const label = SUGGESTION_STATUS_LABELS[status] || status
    return <Badge className={colorClass}>{label}</Badge>
  }

  const getTipoBadge = (tipo: SuggestionType) => {
    const colorClass = SUGGESTION_TYPE_COLORS[tipo] || 'bg-gray-100 text-gray-800'
    return <Badge className={colorClass}>{tipo}</Badge>
  }

  const handleApprove = async (id: string) => {
    try {
      await updateStatus(id, 'approved')
    } catch {
      // Error handled by hook
    }
  }

  const handleReject = async (id: string) => {
    try {
      await updateStatus(id, 'rejected')
    } catch {
      // Error handled by hook
    }
  }

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base">Sugestoes de Prompt</CardTitle>
              <CardDescription>{suggestions.length} sugestoes encontradas</CardDescription>
            </div>
            <Button size="sm" onClick={() => setIsNewOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Nova Sugestao
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {/* Filters */}
          <div className="mb-4">
            <Select value={filterStatus} onValueChange={setFilterStatus}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                {SUGGESTION_STATUS_FILTER_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
            </div>
          ) : suggestions.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Descricao</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Data</TableHead>
                  <TableHead className="text-right">Acoes</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {suggestions.map((sug) => (
                  <TableRow key={sug.id}>
                    <TableCell>{getTipoBadge(sug.tipo)}</TableCell>
                    <TableCell className="max-w-xs truncate">{sug.descricao}</TableCell>
                    <TableCell>{getStatusBadge(sug.status)}</TableCell>
                    <TableCell className="text-sm text-gray-500">
                      {formatDateBR(sug.criadaEm)}
                    </TableCell>
                    <TableCell className="text-right">
                      {sug.status === 'pending' && (
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleReject(sug.id)}
                            disabled={actionLoading === sug.id}
                          >
                            {actionLoading === sug.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <X className="h-4 w-4 text-status-error-solid" />
                            )}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleApprove(sug.id)}
                            disabled={actionLoading === sug.id}
                          >
                            {actionLoading === sug.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Check className="h-4 w-4 text-status-success-solid" />
                            )}
                          </Button>
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="py-8 text-center text-gray-500">
              <XCircle className="mx-auto h-8 w-8 text-gray-300" />
              <p className="mt-2">Nenhuma sugestao encontrada</p>
            </div>
          )}
        </CardContent>
      </Card>

      {isNewOpen && (
        <NewSuggestionModal
          onClose={() => setIsNewOpen(false)}
          onCreated={() => {
            setIsNewOpen(false)
            refresh()
          }}
        />
      )}
    </>
  )
}
