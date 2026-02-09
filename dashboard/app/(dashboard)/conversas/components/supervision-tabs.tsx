'use client'

import { AlertTriangle, Bot, Clock, CheckCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { SupervisionTab, TabCounts } from '@/types/conversas'

interface Props {
  activeTab: SupervisionTab
  counts: TabCounts
  onTabChange: (tab: SupervisionTab) => void
}

interface TabConfig {
  id: SupervisionTab
  label: string
  icon: React.ReactNode
  badgeColor: string
}

const TABS: TabConfig[] = [
  {
    id: 'atencao',
    label: 'Atencao',
    icon: <AlertTriangle className="h-3.5 w-3.5" />,
    badgeColor: 'bg-destructive text-destructive-foreground',
  },
  {
    id: 'julia_ativa',
    label: 'Julia Ativa',
    icon: <Bot className="h-3.5 w-3.5" />,
    badgeColor: 'bg-state-ai text-state-ai-foreground',
  },
  {
    id: 'aguardando',
    label: 'Aguardando',
    icon: <Clock className="h-3.5 w-3.5" />,
    badgeColor: 'bg-status-warning text-status-warning-foreground',
  },
  {
    id: 'encerradas',
    label: 'Encerradas',
    icon: <CheckCircle className="h-3.5 w-3.5" />,
    badgeColor: 'bg-status-neutral text-status-neutral-foreground',
  },
]

export function SupervisionTabs({ activeTab, counts, onTabChange }: Props) {
  return (
    <div className="flex border-b">
      {TABS.map((tab) => {
        const isActive = activeTab === tab.id
        const count = counts[tab.id]

        return (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={cn(
              'flex flex-1 items-center justify-center gap-1.5 px-2 py-2 text-xs font-medium transition-colors',
              isActive
                ? 'border-b-2 border-primary text-primary'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            {tab.icon}
            <span className="hidden sm:inline">{tab.label}</span>
            <span
              className={cn(
                'inline-flex min-w-[18px] items-center justify-center rounded-full px-1 py-0.5 text-[10px] font-semibold leading-none',
                isActive ? tab.badgeColor : 'bg-muted text-muted-foreground',
                tab.id === 'atencao' && count > 0 && 'bg-destructive text-destructive-foreground'
              )}
            >
              {count}
            </span>
          </button>
        )
      })}
    </div>
  )
}
