'use client'

import { useState, useEffect, useCallback } from 'react'
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
import { CheckCircle2, Clock, XCircle, Loader2, Search } from 'lucide-react'

interface Link {
  id: string
  url: string
  status: 'pending' | 'validated' | 'scheduled' | 'processed' | 'failed'
  categoria: string | null
  criadoEm: string
}

interface LinksTableProps {
  onUpdate: () => void
}

export function LinksTable({ onUpdate }: LinksTableProps) {
  const [links, setLinks] = useState<Link[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [search, setSearch] = useState('')
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const fetchLinks = useCallback(async () => {
    try {
      const params = new URLSearchParams()
      if (statusFilter !== 'all') params.append('status', statusFilter)
      if (search) params.append('search', search)
      params.append('limit', '20')

      const res = await fetch(`/api/group-entry/links?${params.toString()}`)
      if (res.ok) {
        const data = await res.json()
        setLinks(
          data.links?.map((l: Record<string, unknown>) => ({
            id: l.id,
            url: l.url,
            status: l.status,
            categoria: l.categoria,
            criadoEm: l.criado_em,
          })) || []
        )
      }
    } catch {
      // Ignore errors
    } finally {
      setLoading(false)
    }
  }, [statusFilter, search])

  useEffect(() => {
    fetchLinks()
  }, [fetchLinks])

  const handleValidate = async (id: string) => {
    setActionLoading(id)
    try {
      await fetch(`/api/group-entry/validate/${id}`, { method: 'POST' })
      await fetchLinks()
      onUpdate()
    } catch {
      // Ignore errors
    } finally {
      setActionLoading(null)
    }
  }

  const handleSchedule = async (id: string) => {
    setActionLoading(id)
    try {
      await fetch('/api/group-entry/schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ link_id: id }),
      })
      await fetchLinks()
      onUpdate()
    } catch {
      // Ignore errors
    } finally {
      setActionLoading(null)
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pending':
        return <Badge className="bg-gray-100 text-gray-800">Pendente</Badge>
      case 'validated':
        return <Badge className="bg-blue-100 text-blue-800">Validado</Badge>
      case 'scheduled':
        return <Badge className="bg-yellow-100 text-yellow-800">Agendado</Badge>
      case 'processed':
        return <Badge className="bg-green-100 text-green-800">Processado</Badge>
      case 'failed':
        return <Badge className="bg-red-100 text-red-800">Falhou</Badge>
      default:
        return <Badge>{status}</Badge>
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base">Links de Grupos</CardTitle>
            <CardDescription>{links.length} links encontrados</CardDescription>
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
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <Input
              placeholder="Buscar por URL..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        {loading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          </div>
        ) : links.length > 0 ? (
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
                    <code className="text-xs">
                      {link.url.replace('https://chat.whatsapp.com/', '...')}
                    </code>
                  </TableCell>
                  <TableCell>{getStatusBadge(link.status)}</TableCell>
                  <TableCell className="text-sm text-gray-500">{link.categoria || '-'}</TableCell>
                  <TableCell className="text-sm text-gray-500">
                    {new Date(link.criadoEm).toLocaleDateString('pt-BR')}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      {link.status === 'pending' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleValidate(link.id)}
                          disabled={actionLoading === link.id}
                        >
                          {actionLoading === link.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <CheckCircle2 className="h-4 w-4" />
                          )}
                        </Button>
                      )}
                      {(link.status === 'pending' || link.status === 'validated') && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleSchedule(link.id)}
                          disabled={actionLoading === link.id}
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
        ) : (
          <div className="py-8 text-center text-gray-500">
            <XCircle className="mx-auto h-8 w-8 text-gray-300" />
            <p className="mt-2">Nenhum link encontrado</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
