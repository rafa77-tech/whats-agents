'use client'

import { useState } from 'react'
import { format, subDays } from 'date-fns'
import { CalendarIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

interface DateRange {
  from: Date
  to: Date
}

interface Props {
  value: DateRange
  onChange: (range: DateRange) => void
}

const PRESETS = [
  { label: '7 dias', days: 7 },
  { label: '30 dias', days: 30 },
  { label: '90 dias', days: 90 },
]

export function DateRangePicker({ value, onChange }: Props) {
  const [open, setOpen] = useState(false)
  const [localFrom, setLocalFrom] = useState(format(value.from, 'yyyy-MM-dd'))
  const [localTo, setLocalTo] = useState(format(value.to, 'yyyy-MM-dd'))

  const handleApply = () => {
    onChange({
      from: new Date(localFrom),
      to: new Date(localTo),
    })
    setOpen(false)
  }

  const handlePreset = (days: number) => {
    const to = new Date()
    const from = subDays(to, days)
    setLocalFrom(format(from, 'yyyy-MM-dd'))
    setLocalTo(format(to, 'yyyy-MM-dd'))
    onChange({ from, to })
    setOpen(false)
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" className="min-w-[200px] justify-start text-left font-normal">
          <CalendarIcon className="mr-2 h-4 w-4" />
          <span>
            {format(value.from, 'dd/MM/yyyy')} - {format(value.to, 'dd/MM/yyyy')}
          </span>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-4" align="end">
        <div className="space-y-4">
          <div className="flex gap-2">
            {PRESETS.map((preset) => (
              <Button
                key={preset.days}
                variant="outline"
                size="sm"
                onClick={() => handlePreset(preset.days)}
              >
                {preset.label}
              </Button>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>De</Label>
              <Input type="date" value={localFrom} onChange={(e) => setLocalFrom(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Ate</Label>
              <Input type="date" value={localTo} onChange={(e) => setLocalTo(e.target.value)} />
            </div>
          </div>

          <Button onClick={handleApply} className="w-full">
            Aplicar
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  )
}
