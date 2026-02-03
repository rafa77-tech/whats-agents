'use client'

import { LucideIcon, CheckCircle2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  description?: string
  action?: {
    label: string
    onClick: () => void
  }
}

export function EmptyState({
  icon: Icon = CheckCircle2,
  title,
  description,
  action,
}: EmptyStateProps) {
  return (
    <div className="flex min-h-[200px] items-center justify-center">
      <div className="text-center">
        <Icon className="mx-auto h-8 w-8 text-muted-foreground/50" />
        <p className="mt-2 text-sm font-medium text-foreground/80">{title}</p>
        {description && <p className="mt-1 text-xs text-muted-foreground/70">{description}</p>}
        {action && (
          <Button onClick={action.onClick} variant="outline" size="sm" className="mt-4">
            {action.label}
          </Button>
        )}
      </div>
    </div>
  )
}
