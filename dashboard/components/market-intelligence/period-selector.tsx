/**
 * PeriodSelector - Sprint 46
 *
 * Seletor de periodo para filtrar dados de Market Intelligence.
 */

'use client'

import { useState } from 'react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Calendar } from 'lucide-react'
import type { AnalyticsPeriod } from '@/types/market-intelligence'

// =============================================================================
// TYPES
// =============================================================================

export interface PeriodSelectorProps {
  value: AnalyticsPeriod
  onChange: (period: AnalyticsPeriod) => void
  onCustomChange?: (startDate: string, endDate: string) => void
}

// =============================================================================
// CONSTANTS
// =============================================================================

const PERIOD_OPTIONS = [
  { value: '24h', label: 'Ultimas 24 horas' },
  { value: '7d', label: 'Ultimos 7 dias' },
  { value: '30d', label: 'Ultimos 30 dias' },
  { value: '90d', label: 'Ultimos 90 dias' },
  { value: 'custom', label: 'Personalizado' },
] as const

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export function PeriodSelector({ value, onChange, onCustomChange }: PeriodSelectorProps) {
  const [customStart, setCustomStart] = useState('')
  const [customEnd, setCustomEnd] = useState('')
  const [isPopoverOpen, setIsPopoverOpen] = useState(false)

  const handlePeriodChange = (newValue: string) => {
    if (newValue === 'custom') {
      setIsPopoverOpen(true)
    } else {
      onChange(newValue as AnalyticsPeriod)
    }
  }

  const handleApplyCustom = () => {
    if (customStart && customEnd && onCustomChange) {
      onCustomChange(customStart, customEnd)
      setIsPopoverOpen(false)
    }
  }

  return (
    <div className="flex items-center gap-2">
      <Select value={value} onValueChange={handlePeriodChange}>
        <SelectTrigger className="w-[180px]">
          <SelectValue placeholder="Selecionar periodo" />
        </SelectTrigger>
        <SelectContent>
          {PERIOD_OPTIONS.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {value === 'custom' && (
        <Popover open={isPopoverOpen} onOpenChange={setIsPopoverOpen}>
          <PopoverTrigger asChild>
            <Button variant="outline" size="icon">
              <Calendar className="h-4 w-4" />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-80">
            <div className="grid gap-4">
              <div className="space-y-2">
                <h4 className="font-medium">Periodo Personalizado</h4>
                <p className="text-sm text-muted-foreground">Selecione o intervalo de datas</p>
              </div>
              <div className="grid gap-2">
                <div className="grid grid-cols-3 items-center gap-4">
                  <Label htmlFor="start">Inicio</Label>
                  <Input
                    id="start"
                    type="date"
                    className="col-span-2"
                    value={customStart}
                    onChange={(e) => setCustomStart(e.target.value)}
                  />
                </div>
                <div className="grid grid-cols-3 items-center gap-4">
                  <Label htmlFor="end">Fim</Label>
                  <Input
                    id="end"
                    type="date"
                    className="col-span-2"
                    value={customEnd}
                    onChange={(e) => setCustomEnd(e.target.value)}
                  />
                </div>
              </div>
              <Button onClick={handleApplyCustom} disabled={!customStart || !customEnd}>
                Aplicar
              </Button>
            </div>
          </PopoverContent>
        </Popover>
      )}
    </div>
  )
}

export default PeriodSelector
