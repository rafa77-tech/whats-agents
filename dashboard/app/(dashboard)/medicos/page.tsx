'use client'

import { useCallback, useEffect, useState } from 'react'
import { Users, Filter, Download } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { useAuth } from '@/hooks/use-auth'
import { DoctorList } from './components/doctor-list'
import { DoctorFilters } from './components/doctor-filters'
import type { Doctor } from './components/doctor-card'

interface Filters {
  stage_jornada?: string | undefined
  especialidade?: string | undefined
  opt_out?: boolean | undefined
  search?: string | undefined
}

export default function MedicosPage() {
  const { session } = useAuth()
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState<Filters>({})
  const [search, setSearch] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<{
    data: Doctor[]
    total: number
    pages: number
  } | null>(null)

  const fetchDoctors = useCallback(async () => {
    if (!session?.access_token) return

    setLoading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const params = new URLSearchParams({
        page: String(page),
        per_page: '20',
      })

      if (filters.stage_jornada) params.set('stage_jornada', filters.stage_jornada)
      if (filters.especialidade) params.set('especialidade', filters.especialidade)
      if (filters.opt_out !== undefined) params.set('opt_out', String(filters.opt_out))
      if (filters.search) params.set('search', filters.search)

      const response = await fetch(`${apiUrl}/dashboard/doctors?${params}`, {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      })

      if (response.ok) {
        const result = await response.json()
        setData(result)
      }
    } catch (err) {
      console.error('Failed to fetch doctors:', err)
    } finally {
      setLoading(false)
    }
  }, [session?.access_token, page, filters])

  useEffect(() => {
    fetchDoctors()
  }, [fetchDoctors])

  const handleSearch = (value: string) => {
    setSearch(value)
    // Debounce search
    const timeout = setTimeout(() => {
      setFilters((prev) => ({ ...prev, search: value || undefined }))
      setPage(1)
    }, 300)
    return () => clearTimeout(timeout)
  }

  const handleExport = async () => {
    // TODO: Implement CSV export
    alert('Exportar CSV - Em desenvolvimento')
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b p-4 md:p-6">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Medicos</h1>
            <p className="text-muted-foreground">{data?.total || 0} medicos cadastrados</p>
          </div>
          <Button variant="outline" onClick={handleExport}>
            <Download className="mr-2 h-4 w-4" />
            <span className="hidden md:inline">Exportar</span>
          </Button>
        </div>

        <div className="flex gap-2">
          <div className="relative flex-1">
            <Users className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Buscar por nome, telefone ou CRM..."
              value={search}
              onChange={(e) => handleSearch(e.target.value)}
              className="pl-10"
            />
          </div>

          <Sheet open={showFilters} onOpenChange={setShowFilters}>
            <SheetTrigger asChild>
              <Button variant="outline">
                <Filter className="h-4 w-4 md:mr-2" />
                <span className="hidden md:inline">Filtros</span>
              </Button>
            </SheetTrigger>
            <SheetContent>
              <SheetHeader>
                <SheetTitle>Filtros</SheetTitle>
              </SheetHeader>
              <DoctorFilters
                filters={filters}
                onApply={(f) => {
                  setFilters(f)
                  setShowFilters(false)
                  setPage(1)
                }}
                onClear={() => {
                  setFilters({})
                  setShowFilters(false)
                  setPage(1)
                }}
              />
            </SheetContent>
          </Sheet>
        </div>
      </div>

      {/* Lista */}
      <div className="flex-1 overflow-auto">
        {loading ? (
          <div className="space-y-4 p-4">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-24" />
            ))}
          </div>
        ) : (
          <DoctorList
            doctors={data?.data || []}
            total={data?.total || 0}
            page={page}
            pages={data?.pages || 1}
            onPageChange={setPage}
          />
        )}
      </div>
    </div>
  )
}
