'use client'

import { MessageCircle, Users, TrendingUp, Clock, ArrowUp, ArrowDown } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface KPIValue {
  label: string
  value: string
  change: number
  changeLabel: string
}

interface Props {
  data?:
    | {
        total_messages: KPIValue
        active_doctors: KPIValue
        conversion_rate: KPIValue
        avg_response_time: KPIValue
      }
    | undefined
}

const ICONS = {
  messages: MessageCircle,
  users: Users,
  conversion: TrendingUp,
  time: Clock,
}

export function KPICards({ data }: Props) {
  if (!data) return null

  const kpis = [
    { ...data.total_messages, icon: 'messages' as const },
    { ...data.active_doctors, icon: 'users' as const },
    { ...data.conversion_rate, icon: 'conversion' as const },
    { ...data.avg_response_time, icon: 'time' as const },
  ]

  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
      {kpis.map((kpi, index) => {
        const Icon = ICONS[kpi.icon]
        const isPositive = kpi.change >= 0
        const ChangeIcon = isPositive ? ArrowUp : ArrowDown

        return (
          <Card key={index}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {kpi.label}
              </CardTitle>
              <Icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{kpi.value}</div>
              <div
                className={cn(
                  'mt-1 flex items-center text-xs',
                  isPositive ? 'text-status-success-foreground' : 'text-status-error-foreground'
                )}
              >
                <ChangeIcon className="mr-1 h-3 w-3" />
                <span>{Math.abs(kpi.change)}%</span>
                <span className="ml-1 text-muted-foreground">{kpi.changeLabel}</span>
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
