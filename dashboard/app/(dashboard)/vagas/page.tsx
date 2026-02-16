'use client'

import dynamic from 'next/dynamic'
import { Calendar, List, Filter, Plus, Search, CheckSquare, X, Megaphone } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { ShiftList } from './components/shift-list'
import { ShiftFilters } from './components/shift-filters'
import { ShiftCalendar } from './components/shift-calendar'
import { NovaVagaDialog } from './components/nova-vaga-dialog'
import { useShifts, buildCampaignInitialData } from '@/lib/vagas'
import type { Shift, WizardInitialData } from '@/lib/vagas'
import { useCallback, useMemo, useState } from 'react'

const NovaCampanhaWizard = dynamic(
  () =>
    import('@/components/campanhas/nova-campanha-wizard').then((mod) => ({
      default: mod.NovaCampanhaWizard,
    })),
  { ssr: false }
)

export default function VagasPage() {
  const [showFilters, setShowFilters] = useState(false)
  const [novaVagaOpen, setNovaVagaOpen] = useState(false)

  // Selection mode (Sprint 58)
  const [selectionMode, setSelectionMode] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [wizardOpen, setWizardOpen] = useState(false)
  const [wizardInitialData, setWizardInitialData] = useState<WizardInitialData | null>(null)

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

  const handleSelectChange = useCallback((shiftId: string, selected: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (selected) {
        next.add(shiftId)
      } else {
        next.delete(shiftId)
      }
      return next
    })
  }, [])

  const toggleSelectionMode = useCallback(() => {
    setSelectionMode((prev) => {
      if (prev) {
        // Exiting selection mode: clear selection
        setSelectedIds(new Set())
      }
      return !prev
    })
  }, [])

  const selectedShifts = useMemo((): Shift[] => {
    if (!data?.data || selectedIds.size === 0) return []
    return data.data.filter((s) => selectedIds.has(s.id))
  }, [data?.data, selectedIds])

  const handleCreateCampaign = useCallback(() => {
    if (selectedShifts.length === 0) return
    const initialData = buildCampaignInitialData(selectedShifts)
    setWizardInitialData(initialData)
    setWizardOpen(true)
  }, [selectedShifts])

  const handleWizardSuccess = useCallback(() => {
    setWizardOpen(false)
    setWizardInitialData(null)
    setSelectionMode(false)
    setSelectedIds(new Set())
    actions.refresh()
  }, [actions])

  const handleWizardClose = useCallback((open: boolean) => {
    if (!open) {
      setWizardOpen(false)
      setWizardInitialData(null)
    }
  }, [])

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b p-4 md:p-6">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Vagas</h1>
            <p className="text-muted-foreground">{data?.total || 0} vagas cadastradas</p>
          </div>
          <div className="flex gap-2">
            <Button
              variant={selectionMode ? 'secondary' : 'outline'}
              onClick={toggleSelectionMode}
              size="sm"
            >
              {selectionMode ? (
                <>
                  <X className="mr-2 h-4 w-4" />
                  Cancelar
                </>
              ) : (
                <>
                  <CheckSquare className="mr-2 h-4 w-4" />
                  <span className="hidden md:inline">Selecionar</span>
                </>
              )}
            </Button>
            <Button onClick={() => setNovaVagaOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              <span className="hidden md:inline">Nova Vaga</span>
            </Button>
          </div>
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
            selectable={selectionMode}
            selectedIds={selectedIds}
            onSelectChange={handleSelectChange}
          />
        )}
      </div>

      {/* Floating action bar when vagas are selected (Sprint 58) */}
      {selectionMode && selectedIds.size > 0 && (
        <div className="sticky bottom-0 border-t bg-background p-4 shadow-lg">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium">
              {selectedIds.size} vaga{selectedIds.size > 1 ? 's' : ''} selecionada
              {selectedIds.size > 1 ? 's' : ''}
            </p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => setSelectedIds(new Set())}>
                Limpar
              </Button>
              <Button size="sm" onClick={handleCreateCampaign}>
                <Megaphone className="mr-2 h-4 w-4" />
                Criar Campanha
              </Button>
            </div>
          </div>
        </div>
      )}

      <NovaVagaDialog
        open={novaVagaOpen}
        onOpenChange={setNovaVagaOpen}
        onSuccess={actions.refresh}
      />

      {/* Campaign wizard (dynamic import for bundle optimization) */}
      {wizardOpen && (
        <NovaCampanhaWizard
          open={wizardOpen}
          onOpenChange={handleWizardClose}
          onSuccess={handleWizardSuccess}
          initialData={wizardInitialData}
        />
      )}
    </div>
  )
}
