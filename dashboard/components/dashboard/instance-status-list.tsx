'use client'

import { type WhatsAppInstance } from '@/types/dashboard'

interface InstanceStatusListProps {
  instances: WhatsAppInstance[]
}

export function InstanceStatusList({ instances }: InstanceStatusListProps) {
  return (
    <div className="space-y-2">
      <h4 className="text-sm font-medium text-foreground/80">Instancias WhatsApp</h4>
      <div className="space-y-1">
        {instances.map((instance) => (
          <div
            key={instance.name}
            className="flex items-center justify-between rounded bg-secondary px-2 py-1.5"
          >
            <div className="flex items-center gap-2">
              <span
                className={`h-2 w-2 rounded-full ${
                  instance.status === 'online'
                    ? 'bg-status-success-solid'
                    : instance.status === 'warming'
                      ? 'bg-status-warning-solid'
                      : 'bg-status-error-solid'
                }`}
              />
              <span className="text-sm font-medium">{instance.name}</span>
            </div>
            <span className="text-sm text-muted-foreground">{instance.messagesToday} msgs</span>
          </div>
        ))}
      </div>
    </div>
  )
}
