'use client'

import { useCallback, useEffect, useState } from 'react'
import { format, startOfMonth, endOfMonth, addMonths, subMonths } from 'date-fns'
import { Calendar, List, Filter, Plus, Search } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { ShiftList } from './components/shift-list'
import { ShiftFilters } from './components/shift-filters'
import { ShiftCalendar } from './components/shift-calendar'
import type { Shift } from './components/shift-card'

interface Filters {
  status?: string | undefined
  hospital_id?: string | undefined
  especialidade_id?: string | undefined
  date_from?: string | undefined
  date_to?: string | undefined
}

type ViewMode = 'list' | 'calendar'

export default function VagasPage() {
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState<Filters>({})
  const [search, setSearch] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [loading, setLoading] = useState(true)
  const [viewMode, setViewMode] = useState<ViewMode>('list')
  const [selectedDate, setSelectedDate] = useState<Date | undefined>()
  const [calendarMonth, setCalendarMonth] = useState(new Date())
  const [data, setData] = useState<{
    data: Shift[]
    total: number
    pages: number
  } | null>(null)

  const fetchShifts = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()

      if (viewMode === 'calendar') {
        // For calendar, fetch all shifts for the visible month
        const monthStart = startOfMonth(calendarMonth)
        const monthEnd = endOfMonth(calendarMonth)
        params.set('date_from', format(monthStart, 'yyyy-MM-dd'))
        params.set('date_to', format(monthEnd, 'yyyy-MM-dd'))
        params.set('per_page', '500') // Get all shifts for the month
      } else {
        // For list view, use pagination
        params.set('page', String(page))
        params.set('per_page', '20')

        if (filters.date_from) params.set('date_from', filters.date_from)
        if (filters.date_to) params.set('date_to', filters.date_to)
      }

      if (filters.status) params.set('status', filters.status)
      if (filters.hospital_id) params.set('hospital_id', filters.hospital_id)
      if (filters.especialidade_id) params.set('especialidade_id', filters.especialidade_id)
      if (search) params.set('search', search)

      const response = await fetch(`/api/vagas?${params}`)

      if (response.ok) {
        const result = await response.json()
        setData(result)
      }
    } catch (err) {
      console.error('Failed to fetch shifts:', err)
    } finally {
      setLoading(false)
    }
  }, [page, filters, search, viewMode, calendarMonth])

  useEffect(() => {
    fetchShifts()
  }, [fetchShifts])

  const handleSearch = (value: string) => {
    setSearch(value)
    setPage(1)
  }

  const handleDateSelect = (date: Date) => {
    setSelectedDate(date)
    const dateStr = format(date, 'yyyy-MM-dd')
    setFilters((prev) => ({
      ...prev,
      date_from: dateStr,
      date_to: dateStr,
    }))
    setViewMode('list')
    setPage(1)
  }

  const handleCalendarMonthChange = (direction: 'prev' | 'next') => {
    setCalendarMonth((prev) => (direction === 'next' ? addMonths(prev, 1) : subMonths(prev, 1)))
  }

  const handleClearFilters = () => {
    setFilters({})
    setSelectedDate(undefined)
    setShowFilters(false)
    setPage(1)
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b p-4 md:p-6">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Vagas</h1>
            <p className="text-muted-foreground">{data?.total || 0} vagas cadastradas</p>
          </div>
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            <span className="hidden md:inline">Nova Vaga</span>
          </Button>
        </div>

        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Buscar por hospital ou especialidade..."
              value={search}
              onChange={(e) => handleSearch(e.target.value)}
              className="pl-10"
            />
          </div>

          {/* View toggle */}
          <div className="flex rounded-md border">
            <Button
              variant={viewMode === 'list' ? 'secondary' : 'ghost'}
              size="icon"
              onClick={() => setViewMode('list')}
              className="rounded-r-none"
            >
              <List className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === 'calendar' ? 'secondary' : 'ghost'}
              size="icon"
              onClick={() => setViewMode('calendar')}
              className="rounded-l-none"
            >
              <Calendar className="h-4 w-4" />
            </Button>
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
              <ShiftFilters
                filters={filters}
                onApply={(f) => {
                  setFilters(f)
                  setShowFilters(false)
                  setPage(1)
                }}
                onClear={handleClearFilters}
              />
            </SheetContent>
          </Sheet>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {loading ? (
          <div className="space-y-4 p-4">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-24" />
            ))}
          </div>
        ) : viewMode === 'calendar' ? (
          <div className="p-4">
            <ShiftCalendar
              shifts={data?.data || []}
              onDateSelect={handleDateSelect}
              selectedDate={selectedDate}
              currentMonth={calendarMonth}
              onMonthChange={handleCalendarMonthChange}
            />
          </div>
        ) : (
          <ShiftList
            shifts={data?.data || []}
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
