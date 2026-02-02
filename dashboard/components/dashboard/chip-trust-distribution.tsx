'use client'

import { type TrustDistribution } from '@/types/dashboard'

interface ChipTrustDistributionProps {
  distribution: TrustDistribution[]
}

const trustConfig: Record<string, { label: string; range: string; color: string }> = {
  verde: { label: 'Verde', range: '75+', color: 'bg-status-success-solid' },
  amarelo: { label: 'Amarelo', range: '50-74', color: 'bg-status-warning-solid' },
  laranja: { label: 'Laranja', range: '35-49', color: 'bg-trust-laranja-solid' },
  vermelho: { label: 'Vermelho', range: '<35', color: 'bg-trust-vermelho-solid' },
  critico: { label: 'Critico', range: '<20', color: 'bg-trust-critico-solid' },
}

const defaultConfig = { label: 'Desconhecido', range: '-', color: 'bg-muted-foreground' }

export function ChipTrustDistribution({ distribution = [] }: ChipTrustDistributionProps) {
  const maxCount = Math.max(...distribution.map((d) => d.count), 1)

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-medium text-foreground/80">Trust Level</h4>
      <div className="space-y-2">
        {distribution.map((item) => {
          const config = trustConfig[item.level] || defaultConfig
          const barWidth = (item.count / maxCount) * 100

          return (
            <div key={item.level} className="flex items-center gap-3">
              <div className="w-24 text-sm text-muted-foreground">
                {config.label} ({config.range})
              </div>
              <div className="h-4 flex-1 overflow-hidden rounded-full bg-muted">
                <div
                  className={`h-full ${config.color} rounded-full transition-all`}
                  style={{ width: `${barWidth}%` }}
                />
              </div>
              <div className="w-8 text-right text-sm font-medium">{item.count}</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
