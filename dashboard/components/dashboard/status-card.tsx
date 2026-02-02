import { LucideIcon, TrendingUp, TrendingDown } from 'lucide-react'
import { cn } from '@/lib/utils'

interface StatusCardProps {
  title: string
  value: string
  icon: LucideIcon
  trend?: {
    value: number
    positive: boolean
  }
}

export function StatusCard({ title, value, icon: Icon, trend }: StatusCardProps) {
  return (
    <div className="rounded-xl border border-border bg-card p-4 lg:p-6">
      <div className="flex items-start justify-between">
        <div className="rounded-lg bg-revoluna-50 p-2">
          <Icon className="h-5 w-5 text-revoluna-400" />
        </div>
        {trend && (
          <div
            className={cn(
              'flex items-center gap-1 text-sm font-medium',
              trend.positive ? 'text-status-success-foreground' : 'text-status-error-foreground'
            )}
          >
            {trend.positive ? (
              <TrendingUp className="h-4 w-4" />
            ) : (
              <TrendingDown className="h-4 w-4" />
            )}
            {trend.value}%
          </div>
        )}
      </div>
      <div className="mt-4">
        <p className="text-2xl font-bold text-foreground lg:text-3xl">{value}</p>
        <p className="mt-1 text-sm text-muted-foreground">{title}</p>
      </div>
    </div>
  )
}
