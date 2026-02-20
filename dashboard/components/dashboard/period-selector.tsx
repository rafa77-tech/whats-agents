'use client'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { type DashboardPeriod } from '@/types/dashboard'

interface PeriodSelectorProps {
  value: DashboardPeriod
  onChange: (value: DashboardPeriod) => void
}

const periodLabels: Record<DashboardPeriod, string> = {
  '24h': '24 horas',
  '7d': '7 dias',
  '14d': '14 dias',
  '30d': '30 dias',
}

export function PeriodSelector({ value, onChange }: PeriodSelectorProps) {
  return (
    <Select value={value} onValueChange={(v) => onChange(v as DashboardPeriod)}>
      <SelectTrigger className="w-[120px]">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="24h">{periodLabels['24h']}</SelectItem>
        <SelectItem value="7d">{periodLabels['7d']}</SelectItem>
        <SelectItem value="14d">{periodLabels['14d']}</SelectItem>
        <SelectItem value="30d">{periodLabels['30d']}</SelectItem>
      </SelectContent>
    </Select>
  )
}
