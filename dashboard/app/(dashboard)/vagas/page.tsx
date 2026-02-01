'use client'

import { Calendar, List, Filter, Plus, Search } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { ShiftList } from './components/shift-list'
import { ShiftFilters } from './components/shift-filters'
import { ShiftCalendar } from './components/shift-calendar'
import { useShifts } from '@/lib/vagas'
import { useState } from 'react'

export default function VagasPage() {
  const [showFilters, setShowFilters] = useState(false)

  const { data, loading, filters, search, page, viewMode, calendarMonth, selectedDate, actions } =
    useShifts()

  const handleApplyFilters = (f: typeof filters) => {
    actions.setFilters(f)
    setShowFilters(false)
  }

  const handleClearFilters = () => {
    actions.clearFilters()
    setShowFilters(false)
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
              onChange={(e) => actions.setSearch(e.target.value)}
              className="pl-10"
            />
          </div>

          {/* View toggle */}
          <div className="flex rounded-md border">
            <Button
              variant={viewMode === 'list' ? 'secondary' : 'ghost'}
              size="icon"
              onClick={() => actions.setViewMode('list')}
              className="rounded-r-none"
            >
              <List className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === 'calendar' ? 'secondary' : 'ghost'}
              size="icon"
              onClick={() => actions.setViewMode('calendar')}
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
                onApply={handleApplyFilters}
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
              onDateSelect={actions.handleDateSelect}
              selectedDate={selectedDate}
              currentMonth={calendarMonth}
              onMonthChange={actions.handleCalendarMonthChange}
            />
          </div>
        ) : (
          <ShiftList
            shifts={data?.data || []}
            total={data?.total || 0}
            page={page}
            pages={data?.pages || 1}
            onPageChange={actions.setPage}
          />
        )}
      </div>
    </div>
  )
}
