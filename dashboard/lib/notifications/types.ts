export type NotificationType =
  | 'handoff_request'
  | 'rate_limit_warning'
  | 'circuit_open'
  | 'new_conversion'
  | 'campaign_complete'
  | 'system_alert'

export type NotificationPriority = 'low' | 'medium' | 'high' | 'critical'

export interface Notification {
  id: string
  type: NotificationType
  title: string
  body: string
  priority: NotificationPriority
  read: boolean
  data?: Record<string, string | number | boolean>
  created_at: string
}

export interface NotificationTypeConfig {
  push: boolean
  toast: boolean
  sound: boolean
}

export interface NotificationConfig {
  push_enabled: boolean
  toast_enabled: boolean
  types: Partial<Record<NotificationType, NotificationTypeConfig>>
}

export const DEFAULT_CONFIG: NotificationConfig = {
  push_enabled: false,
  toast_enabled: true,
  types: {
    handoff_request: { push: true, toast: true, sound: true },
    rate_limit_warning: { push: true, toast: true, sound: false },
    circuit_open: { push: true, toast: true, sound: true },
    new_conversion: { push: true, toast: true, sound: false },
    campaign_complete: { push: false, toast: true, sound: false },
    system_alert: { push: true, toast: true, sound: true },
  },
}

export const NOTIFICATION_LABELS: Record<NotificationType, string> = {
  handoff_request: 'Handoff Solicitado',
  rate_limit_warning: 'Rate Limit',
  circuit_open: 'Circuito Aberto',
  new_conversion: 'Nova Conversao',
  campaign_complete: 'Campanha Finalizada',
  system_alert: 'Alerta de Sistema',
}
