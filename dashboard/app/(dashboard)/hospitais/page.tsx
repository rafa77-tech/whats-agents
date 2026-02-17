'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Building2, Search, ChevronLeft, ChevronRight, AlertTriangle } from 'lucide-react'
import type { HospitalGestaoItem } from '@/lib/hospitais/types'

type StatusFilter = 'todos' | 'revisados' | 'pendentes'

export default function HospitaisPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<HospitalGestaoItem[]>([])
  const [total, setTotal] = useState(0)
  const [pages, setPages] = useState(0)
  const [pendentes, setPendentes] = useState(0)
  const [autoCriados, setAutoCriados] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<StatusFilter>('todos')

  const fetchHospitais = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        page: String(page),
        per_page: '20',
        status,
      })
      if (search.trim()) {
        params.set('search', search.trim())
      }

      const res = await fetch(`/api/hospitais/gestao?${params}`)
      const json = await res.json()
      setData(json.data || [])
      setTotal(json.total || 0)
      setPages(json.pages || 0)
      setPendentes(json.pendentes || 0)
      setAutoCriados(json.auto_criados || 0)
    } catch {
      setData([])
    } finally {
      setLoading(false)
    }
  }, [page, search, status])

  useEffect(() => {
    fetchHospitais()
  }, [fetchHospitais])

  // Debounced search
  const [searchInput, setSearchInput] = useState('')
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput)
      setPage(1)
    }, 400)
    return () => clearTimeout(timer)
  }, [searchInput])

  // pendentes and autoCriados are global counts from the API

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold">
            <Building2 className="h-6 w-6" />
            Hospitais
          </h1>
          <p className="text-sm text-muted-foreground">{total} hospitais cadastrados</p>
        </div>
        <Button variant="outline" onClick={() => router.push('/hospitais/bloqueados')}>
          Ver Bloqueados
        </Button>
      </div>

      {/* Stats banner */}
      {!loading && total > 0 && (
        <div className="flex flex-wrap gap-4">
          <div className="rounded-lg border bg-card px-4 py-2">
            <p className="text-xs text-muted-foreground">Total</p>
            <p className="text-lg font-semibold">{total}</p>
          </div>
          {status === 'todos' && pendentes > 0 && (
            <div className="rounded-lg border border-status-warning-border bg-status-warning px-4 py-2">
              <p className="flex items-center gap-1 text-xs text-status-warning-foreground">
                <AlertTriangle className="h-3 w-3" />
                Pendentes de revisao
              </p>
              <p className="text-lg font-semibold text-status-warning-foreground">{pendentes}</p>
            </div>
          )}
          {status === 'todos' && autoCriados > 0 && (
            <div className="rounded-lg border bg-card px-4 py-2">
              <p className="text-xs text-muted-foreground">Auto-criados</p>
              <p className="text-lg font-semibold">{autoCriados}</p>
            </div>
          )}
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Buscar por nome..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select
          value={status}
          onValueChange={(v) => {
            setStatus(v as StatusFilter)
            setPage(1)
          }}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos</SelectItem>
            <SelectItem value="revisados">Revisados</SelectItem>
            <SelectItem value="pendentes">Pendentes</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nome</TableHead>
              <TableHead>Cidade</TableHead>
              <TableHead className="text-center">Vagas</TableHead>
              <TableHead className="text-center">Aliases</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              Array.from({ length: 10 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell>
                    <Skeleton className="h-4 w-48" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-4 w-24" />
                  </TableCell>
                  <TableCell className="text-center">
                    <Skeleton className="mx-auto h-4 w-8" />
                  </TableCell>
                  <TableCell className="text-center">
                    <Skeleton className="mx-auto h-4 w-8" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-5 w-20" />
                  </TableCell>
                </TableRow>
              ))
            ) : data.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="py-8 text-center text-muted-foreground">
                  Nenhum hospital encontrado
                </TableCell>
              </TableRow>
            ) : (
              data.map((hospital) => (
                <TableRow
                  key={hospital.id}
                  className="cursor-pointer"
                  onClick={() => router.push(`/hospitais/${hospital.id}`)}
                >
                  <TableCell className="font-medium">{hospital.nome}</TableCell>
                  <TableCell className="text-muted-foreground">{hospital.cidade || '—'}</TableCell>
                  <TableCell className="text-center">{hospital.vagas_count}</TableCell>
                  <TableCell className="text-center">{hospital.aliases_count}</TableCell>
                  <TableCell>
                    {hospital.precisa_revisao ? (
                      <Badge
                        variant="outline"
                        className="border-status-warning-border text-status-warning-foreground"
                      >
                        Pendente
                      </Badge>
                    ) : (
                      <Badge
                        variant="outline"
                        className="border-status-success-border text-status-success-foreground"
                      >
                        Revisado
                      </Badge>
                    )}
                    {hospital.criado_automaticamente && (
                      <Badge variant="secondary" className="ml-1">
                        Auto
                      </Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Pagina {page} de {pages}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.min(pages, p + 1))}
              disabled={page >= pages}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
