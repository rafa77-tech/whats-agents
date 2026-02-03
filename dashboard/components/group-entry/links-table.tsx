'use client'

import { useState, useEffect, useMemo } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
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
import {
  CheckCircle2,
  Clock,
  XCircle,
  Loader2,
  Search,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { toast } from '@/hooks/use-toast'
import {
  useLinksList,
  useLinkActions,
  useDebounce,
  getLinkStatusBadgeColor,
  getLinkStatusLabel,
  formatLinkUrl,
  formatDate,
} from '@/lib/group-entry'

interface LinksTableProps {
  onUpdate: () => void
}

export function LinksTable({ onUpdate }: LinksTableProps) {
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [searchInput, setSearchInput] = useState('')

  // Debounce search input by 300ms
  const debouncedSearch = useDebounce(searchInput, 300)

  const filters = useMemo(
    () => ({
      status: statusFilter,
      search: debouncedSearch,
    }),
    [statusFilter, debouncedSearch]
  )

  const { links, loading, error, total, page, totalPages, setPage, refresh } = useLinksList(filters)

  const handleSuccess = () => {
    refresh()
    onUpdate()
  }

  const {
    actionLoading,
    error: actionError,
    validateLink,
    scheduleLink,
  } = useLinkActions(handleSuccess)

  // Show toast on errors
  useEffect(() => {
    if (error) {
      toast({
        title: 'Erro',
        description: error,
        variant: 'destructive',
      })
    }
  }, [error])

  useEffect(() => {
    if (actionError) {
      toast({
        title: 'Erro na acao',
        description: actionError,
        variant: 'destructive',
      })
    }
  }, [actionError])

  const handleValidate = async (id: string) => {
    const success = await validateLink(id)
    if (success) {
      toast({
        title: 'Sucesso',
        description: 'Link validado com sucesso',
      })
    }
  }

  const handleSchedule = async (id: string) => {
    const success = await scheduleLink(id)
    if (success) {
      toast({
        title: 'Sucesso',
        description: 'Link agendado com sucesso',
      })
    }
  }

  const renderStatusBadge = (status: string) => {
    const colorClass = getLinkStatusBadgeColor(status)
    const label = getLinkStatusLabel(status)
    return <Badge className={colorClass}>{label}</Badge>
  }

  const canValidate = (status: string) => status === 'pending'
  const canSchedule = (status: string) => status === 'pending' || status === 'validated'

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base">Links de Grupos</CardTitle>
            <CardDescription>{total} links encontrados</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Filters */}
        <div className="mb-4 flex gap-4">
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos</SelectItem>
              <SelectItem value="pending">Pendentes</SelectItem>
              <SelectItem value="validated">Validados</SelectItem>
              <SelectItem value="scheduled">Agendados</SelectItem>
              <SelectItem value="processed">Processados</SelectItem>
              <SelectItem value="failed">Falharam</SelectItem>
            </SelectContent>
          </Select>
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground/70" />
            <Input
              placeholder="Buscar por URL..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        {loading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground/70" />
          </div>
        ) : links.length > 0 ? (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Link</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Categoria</TableHead>
                  <TableHead>Criado</TableHead>
                  <TableHead className="text-right">Acoes</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {links.map((link) => (
                  <TableRow key={link.id}>
                    <TableCell>
                      <code className="text-xs">{formatLinkUrl(link.url)}</code>
                    </TableCell>
                    <TableCell>{renderStatusBadge(link.status)}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {link.categoria || '-'}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDate(link.criado_em)}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        {canValidate(link.status) && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleValidate(link.id)}
                            disabled={actionLoading === link.id}
                            title="Validar link"
                          >
                            {actionLoading === link.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <CheckCircle2 className="h-4 w-4" />
                            )}
                          </Button>
                        )}
                        {canSchedule(link.status) && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleSchedule(link.id)}
                            disabled={actionLoading === link.id}
                            title="Agendar link"
                          >
                            {actionLoading === link.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Clock className="h-4 w-4" />
                            )}
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="mt-4 flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                  Pagina {page} de {totalPages}
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage(page - 1)}
                    disabled={page <= 1}
                  >
                    <ChevronLeft className="h-4 w-4" />
                    Anterior
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage(page + 1)}
                    disabled={page >= totalPages}
                  >
                    Proximo
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="py-8 text-center text-muted-foreground">
            <XCircle className="mx-auto h-8 w-8 text-muted-foreground/50" />
            <p className="mt-2">Nenhum link encontrado</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
