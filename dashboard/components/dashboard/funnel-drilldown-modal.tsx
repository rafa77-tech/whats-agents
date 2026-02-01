/**
 * Funnel Drilldown Modal - Sprint 34 E04
 *
 * Modal showing list of doctors at each funnel stage.
 * Improved: skeleton loading, overlay pagination, range indicator, message preview.
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { TableSkeleton } from '@/components/ui/table-skeleton'
import { type FunnelDrilldownData } from '@/types/dashboard'
import {
  Search,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  X,
  ChevronDown,
  ChevronUp,
  MessageCircle,
} from 'lucide-react'
import { formatDistanceToNow, format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { cn } from '@/lib/utils'

interface ConversationMessage {
  id: string
  tipo: 'entrada' | 'saida'
  conteudo: string
  timestamp: string
  deliveryStatus: string | null
  isFromJulia: boolean
}

interface FunnelDrilldownModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  stage: string | null
  period: string
}

export function FunnelDrilldownModal({
  open,
  onOpenChange,
  stage,
  period,
}: FunnelDrilldownModalProps) {
  const [data, setData] = useState<FunnelDrilldownData | null>(null)
  const [loading, setLoading] = useState(false)
  const [isInitialLoad, setIsInitialLoad] = useState(true)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [expandedRow, setExpandedRow] = useState<string | null>(null)
  const [messages, setMessages] = useState<Record<string, ConversationMessage[]>>({})
  const [loadingMessages, setLoadingMessages] = useState<string | null>(null)

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search)
    }, 300)
    return () => clearTimeout(timer)
  }, [search])

  const fetchData = useCallback(async () => {
    if (!stage) return

    setLoading(true)
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        pageSize: '10',
        search: debouncedSearch,
        period,
      })

      const res = await fetch(`/api/dashboard/funnel/${stage}?${params}`)
      const json = await res.json()

      if (res.ok) {
        setData(json)
        setIsInitialLoad(false)
      }
    } catch (error) {
      console.error('Error fetching drilldown:', error)
    } finally {
      setLoading(false)
    }
  }, [stage, page, debouncedSearch, period])

  useEffect(() => {
    if (open && stage) {
      fetchData()
    }
  }, [open, stage, fetchData])

  // Fetch messages for a conversation
  const fetchMessages = useCallback(
    async (conversationId: string) => {
      if (messages[conversationId]) {
        // Already cached
        return
      }

      setLoadingMessages(conversationId)
      try {
        const res = await fetch(`/api/dashboard/conversations/${conversationId}/messages?limit=30`)
        const json = await res.json()

        if (res.ok) {
          setMessages((prev) => ({
            ...prev,
            [conversationId]: json.messages || [],
          }))
        }
      } catch (error) {
        console.error('Error fetching messages:', error)
      } finally {
        setLoadingMessages(null)
      }
    },
    [messages]
  )

  // Toggle row expansion
  const toggleExpand = useCallback(
    (conversationId: string) => {
      if (expandedRow === conversationId) {
        setExpandedRow(null)
      } else {
        setExpandedRow(conversationId)
        fetchMessages(conversationId)
      }
    },
    [expandedRow, fetchMessages]
  )

  // Reset state when closing
  useEffect(() => {
    if (!open) {
      setSearch('')
      setDebouncedSearch('')
      setPage(1)
      setData(null)
      setIsInitialLoad(true)
      setExpandedRow(null)
      setMessages({})
      setLoadingMessages(null)
    }
  }, [open])

  const handleSearchChange = (value: string) => {
    setSearch(value)
    setPage(1) // Reset page on search
  }

  const clearSearch = () => {
    setSearch('')
    setDebouncedSearch('')
    setPage(1)
  }

  const totalPages = data ? Math.ceil(data.total / data.pageSize) : 0
  const pageSize = data?.pageSize || 10
  const startItem = data ? (page - 1) * pageSize + 1 : 0
  const endItem = data ? Math.min(page * pageSize, data.total) : 0
  const hasSearchFilter = debouncedSearch.length > 0
  const isEmptySearchResult = !loading && data?.items.length === 0 && hasSearchFilter

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[80vh] max-w-4xl flex-col overflow-hidden">
        <DialogHeader>
          <DialogTitle>
            Medicos em &quot;{data?.stageLabel || stage}&quot; ({data?.total || 0})
          </DialogTitle>
        </DialogHeader>

        {/* Busca */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground/70" />
          <Input
            placeholder="Buscar por nome..."
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="pl-10 pr-10"
          />
          {search && (
            <button
              onClick={clearSearch}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground/70 hover:text-muted-foreground"
              aria-label="Limpar busca"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Tabela */}
        <div className="relative flex-1 overflow-auto rounded-lg border">
          {/* Overlay de loading durante paginacao */}
          {loading && !isInitialLoad && (
            <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/60">
              <div className="rounded-lg bg-card px-4 py-2 shadow-lg">
                <span className="text-sm text-muted-foreground">Carregando...</span>
              </div>
            </div>
          )}

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                <TableHead>Telefone</TableHead>
                <TableHead>Especialidade</TableHead>
                <TableHead>Ultimo Contato</TableHead>
                <TableHead>Chip</TableHead>
                <TableHead className="w-[80px]">Acao</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody className={cn(loading && !isInitialLoad && 'opacity-50')}>
              {loading && isInitialLoad ? (
                <TableSkeleton rows={5} columns={6} />
              ) : isEmptySearchResult ? (
                <TableRow>
                  <TableCell colSpan={6} className="py-8 text-center">
                    <div className="space-y-2">
                      <p className="text-muted-foreground">
                        Nenhum medico encontrado para &quot;{debouncedSearch}&quot;
                      </p>
                      <Button variant="outline" size="sm" onClick={clearSearch}>
                        Limpar busca
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ) : data?.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="py-8 text-center text-muted-foreground">
                    Nenhum medico neste estagio
                  </TableCell>
                </TableRow>
              ) : (
                data?.items.map((item) => (
                  <>
                    <TableRow
                      key={item.id}
                      className={cn(
                        'cursor-pointer hover:bg-muted/50',
                        expandedRow === (item.conversaId || item.id) && 'bg-status-info/10'
                      )}
                      onClick={() => toggleExpand(item.conversaId || item.id)}
                    >
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-2">
                          {expandedRow === (item.conversaId || item.id) ? (
                            <ChevronUp className="h-4 w-4 text-muted-foreground/70" />
                          ) : (
                            <ChevronDown className="h-4 w-4 text-muted-foreground/70" />
                          )}
                          {item.nome}
                        </div>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{item.telefone || '-'}</TableCell>
                      <TableCell className="text-muted-foreground">{item.especialidade}</TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatDistanceToNow(new Date(item.ultimoContato), {
                          addSuffix: true,
                          locale: ptBR,
                        })}
                      </TableCell>
                      <TableCell className="text-muted-foreground">{item.chipName}</TableCell>
                      <TableCell onClick={(e) => e.stopPropagation()}>
                        {item.chatwootUrl ? (
                          <Button variant="ghost" size="sm" asChild>
                            <a href={item.chatwootUrl} target="_blank" rel="noopener noreferrer">
                              <ExternalLink className="h-4 w-4" />
                            </a>
                          </Button>
                        ) : (
                          <span className="text-muted-foreground/70">-</span>
                        )}
                      </TableCell>
                    </TableRow>
                    {/* Mensagens expandidas */}
                    {expandedRow === (item.conversaId || item.id) && (
                      <TableRow key={`${item.id}-messages`}>
                        <TableCell colSpan={6} className="bg-muted/50 p-0">
                          <div className="max-h-80 overflow-y-auto p-4">
                            {loadingMessages === (item.conversaId || item.id) ? (
                              <div className="flex items-center justify-center py-4">
                                <div className="h-5 w-5 animate-spin rounded-full border-2 border-status-info-solid border-t-transparent" />
                                <span className="ml-2 text-sm text-muted-foreground">
                                  Carregando mensagens...
                                </span>
                              </div>
                            ) : messages[item.conversaId || item.id]?.length === 0 ? (
                              <div className="py-4 text-center text-sm text-muted-foreground">
                                Nenhuma mensagem encontrada
                              </div>
                            ) : (
                              <div className="space-y-3">
                                {messages[item.conversaId || item.id]?.map((msg) => (
                                  <div
                                    key={msg.id}
                                    className={cn(
                                      'flex',
                                      msg.isFromJulia ? 'justify-end' : 'justify-start'
                                    )}
                                  >
                                    <div
                                      className={cn(
                                        'max-w-[80%] rounded-lg px-3 py-2',
                                        msg.isFromJulia
                                          ? 'bg-status-info-solid text-white'
                                          : 'border bg-card text-foreground shadow-sm'
                                      )}
                                    >
                                      <div className="mb-1 flex items-center gap-2">
                                        <MessageCircle className="h-3 w-3" />
                                        <span className="text-xs font-medium">
                                          {msg.isFromJulia ? 'Julia' : item.nome}
                                        </span>
                                      </div>
                                      <p className="whitespace-pre-wrap text-sm">{msg.conteudo}</p>
                                      <div
                                        className={cn(
                                          'mt-1 text-xs',
                                          msg.isFromJulia ? 'text-blue-100' : 'text-muted-foreground/70'
                                        )}
                                      >
                                        {format(new Date(msg.timestamp), "dd/MM 'às' HH:mm", {
                                          locale: ptBR,
                                        })}
                                      </div>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                  </>
                ))
              )}
            </TableBody>
          </Table>
        </div>

        {/* Paginacao */}
        {data && data.total > 0 && (
          <div className="flex items-center justify-between border-t pt-4">
            <div className="text-sm text-muted-foreground">
              Mostrando {startItem}-{endItem} de {data.total} medicos
            </div>
            {totalPages > 1 && (
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1 || loading}
                >
                  <ChevronLeft className="mr-1 h-4 w-4" />
                  Anterior
                </Button>
                <span className="text-sm text-muted-foreground">
                  {page} / {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages || loading}
                >
                  Proximo
                  <ChevronRight className="ml-1 h-4 w-4" />
                </Button>
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
