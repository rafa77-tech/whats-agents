'use client'

import { useMemo } from 'react'
import {
  format,
  startOfMonth,
  endOfMonth,
  eachDayOfInterval,
  isSameMonth,
  isSameDay,
  startOfWeek,
  endOfWeek,
} from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { Shift } from './shift-card'

interface Props {
  shifts: Shift[]
  onDateSelect: (date: Date) => void
  selectedDate?: Date | undefined
  currentMonth: Date
  onMonthChange: (direction: 'prev' | 'next') => void
}

const STATUS_COLORS: Record<string, string> = {
  aberta: 'bg-green-500',
  reservada: 'bg-yellow-500',
  confirmada: 'bg-blue-500',
  cancelada: 'bg-red-500',
  realizada: 'bg-gray-500',
  fechada: 'bg-gray-500',
}

export function ShiftCalendar({
  shifts,
  onDateSelect,
  selectedDate,
  currentMonth,
  onMonthChange,
}: Props) {
  const days = useMemo(() => {
    const start = startOfWeek(startOfMonth(currentMonth), { locale: ptBR })
    const end = endOfWeek(endOfMonth(currentMonth), { locale: ptBR })
    return eachDayOfInterval({ start, end })
  }, [currentMonth])

  const shiftsByDate = useMemo(() => {
    const map = new Map<string, Shift[]>()
    shifts.forEach((shift) => {
      const dateKey = shift.data
      if (!map.has(dateKey)) {
        map.set(dateKey, [])
      }
      map.get(dateKey)!.push(shift)
    })
    return map
  }, [shifts])

  const weekDays = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab']

  return (
    <div className="rounded-lg border bg-card p-4">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold capitalize">
          {format(currentMonth, 'MMMM yyyy', { locale: ptBR })}
        </h2>
        <div className="flex gap-1">
          <Button variant="outline" size="icon" onClick={() => onMonthChange('prev')}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="icon" onClick={() => onMonthChange('next')}>
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Week days header */}
      <div className="mb-2 grid grid-cols-7 gap-1">
        {weekDays.map((day) => (
          <div key={day} className="py-2 text-center text-xs font-medium text-muted-foreground">
            {day}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div className="grid grid-cols-7 gap-1">
        {days.map((day) => {
          const dateKey = format(day, 'yyyy-MM-dd')
          const dayShifts = shiftsByDate.get(dateKey) || []
          const isCurrentMonth = isSameMonth(day, currentMonth)
          const isSelected = selectedDate && isSameDay(day, selectedDate)
          const isToday = isSameDay(day, new Date())

          return (
            <button
              key={dateKey}
              onClick={() => onDateSelect(day)}
              className={cn(
                'relative flex h-20 flex-col items-start rounded-md border p-1 text-left transition-colors hover:bg-muted/50',
                !isCurrentMonth && 'bg-muted/30 text-muted-foreground',
                isSelected && 'ring-2 ring-primary',
                isToday && 'border-primary'
              )}
            >
              <span className={cn('text-sm', isToday && 'font-bold text-primary')}>
                {format(day, 'd')}
              </span>

              {/* Shift indicators */}
              <div className="mt-1 flex flex-wrap gap-0.5">
                {dayShifts.slice(0, 3).map((shift) => (
                  <div
                    key={shift.id}
                    className={cn(
                      'h-1.5 w-1.5 rounded-full',
                      STATUS_COLORS[shift.status] || 'bg-gray-500'
                    )}
                    title={`${shift.hospital} - ${shift.especialidade}`}
                  />
                ))}
                {dayShifts.length > 3 && (
                  <span className="text-[10px] text-muted-foreground">+{dayShifts.length - 3}</span>
                )}
              </div>

              {/* Shift count badge */}
              {dayShifts.length > 0 && (
                <span className="absolute bottom-1 right-1 text-[10px] font-medium text-muted-foreground">
                  {dayShifts.length}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* Legend */}
      <div className="mt-4 flex flex-wrap gap-4 border-t pt-4 text-xs">
        <div className="flex items-center gap-1">
          <div className="h-2 w-2 rounded-full bg-green-500" />
          <span>Aberta</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="h-2 w-2 rounded-full bg-yellow-500" />
          <span>Reservada</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="h-2 w-2 rounded-full bg-blue-500" />
          <span>Confirmada</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="h-2 w-2 rounded-full bg-red-500" />
          <span>Cancelada</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="h-2 w-2 rounded-full bg-gray-500" />
          <span>Realizada</span>
        </div>
      </div>
    </div>
  )
}
