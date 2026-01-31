'use client'

import { useState, useEffect, useCallback } from 'react'
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
import { NewSuggestionModal } from './new-suggestion-modal'

interface Suggestion {
  id: string
  tipo: string
  descricao: string
  status: 'pending' | 'approved' | 'rejected' | 'implemented'
  criadaEm: string
}

export function SuggestionsList() {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [filterStatus, setFilterStatus] = useState<string>('pending')
  const [isNewOpen, setIsNewOpen] = useState(false)

  const fetchSuggestions = useCallback(async () => {
    try {
      const params = new URLSearchParams()
      if (filterStatus !== 'all') {
        params.append('status', filterStatus)
      }

      const res = await fetch(`/api/admin/sugestoes?${params.toString()}`)
      if (res.ok) {
        const data = await res.json()
        setSuggestions(
          data.sugestoes?.map((s: Record<string, unknown>) => ({
            id: s.id,
            tipo: s.tipo,
            descricao: s.descricao,
            status: s.status,
            criadaEm: s.criada_em,
          })) || []
        )
      }
    } catch {
      // Ignore errors
    } finally {
      setLoading(false)
    }
  }, [filterStatus])

  useEffect(() => {
    fetchSuggestions()
  }, [fetchSuggestions])

  const handleUpdateStatus = async (id: string, status: string) => {
    setActionLoading(id)
    try {
      await fetch(`/api/admin/sugestoes/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      })
      await fetchSuggestions()
    } catch {
      // Ignore errors
    } finally {
      setActionLoading(null)
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pending':
        return <Badge className="bg-yellow-100 text-yellow-800">Pendente</Badge>
      case 'approved':
        return <Badge className="bg-blue-100 text-blue-800">Aprovada</Badge>
      case 'rejected':
        return <Badge className="bg-red-100 text-red-800">Rejeitada</Badge>
      case 'implemented':
        return <Badge className="bg-green-100 text-green-800">Implementada</Badge>
      default:
        return <Badge>{status}</Badge>
    }
  }

  const getTipoBadge = (tipo: string) => {
    const colors: Record<string, string> = {
      tom: 'bg-purple-100 text-purple-800',
      resposta: 'bg-blue-100 text-blue-800',
      abertura: 'bg-green-100 text-green-800',
      objecao: 'bg-orange-100 text-orange-800',
    }
    return <Badge className={colors[tipo] || 'bg-gray-100 text-gray-800'}>{tipo}</Badge>
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
                <SelectItem value="all">Todas</SelectItem>
                <SelectItem value="pending">Pendentes</SelectItem>
                <SelectItem value="approved">Aprovadas</SelectItem>
                <SelectItem value="rejected">Rejeitadas</SelectItem>
                <SelectItem value="implemented">Implementadas</SelectItem>
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
                      {new Date(sug.criadaEm).toLocaleDateString('pt-BR')}
                    </TableCell>
                    <TableCell className="text-right">
                      {sug.status === 'pending' && (
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleUpdateStatus(sug.id, 'rejected')}
                            disabled={actionLoading === sug.id}
                          >
                            {actionLoading === sug.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <X className="h-4 w-4 text-red-500" />
                            )}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleUpdateStatus(sug.id, 'approved')}
                            disabled={actionLoading === sug.id}
                          >
                            {actionLoading === sug.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Check className="h-4 w-4 text-green-500" />
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
            fetchSuggestions()
          }}
        />
      )}
    </>
  )
}
