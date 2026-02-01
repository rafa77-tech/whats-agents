'use client'

import { useState, useEffect } from 'react'
import { Bell, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { registerPushNotifications, isPushSupported } from '@/lib/notifications/push'
import { useAuth } from '@/hooks/use-auth'

export function PushPermissionBanner() {
  const [show, setShow] = useState(false)
  const [loading, setLoading] = useState(false)

  const { session } = useAuth()

  useEffect(() => {
    // Show banner if push is not active and was never denied
    const checkPermission = () => {
      if (!isPushSupported()) return

      const permission = Notification.permission
      const dismissed = localStorage.getItem('push-permission-dismissed')

      if (permission === 'default' && !dismissed) {
        setShow(true)
      }
    }

    checkPermission()
  }, [])

  const handleEnable = async () => {
    setLoading(true)

    const subscription = await registerPushNotifications()

    if (subscription && session?.access_token) {
      // Save subscription to backend
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        await fetch(`${apiUrl}/dashboard/notifications/push-subscription`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${session.access_token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ subscription: subscription.toJSON() }),
        })
      } catch (err) {
        console.error('Failed to save push subscription:', err)
      }

      setShow(false)
    }

    setLoading(false)
  }

  const handleDismiss = () => {
    localStorage.setItem('push-permission-dismissed', 'true')
    setShow(false)
  }

  if (!show) return null

  return (
    <Card className="fixed bottom-4 right-4 z-50 w-80 shadow-lg md:bottom-6 md:right-6">
      <CardContent className="p-4">
        <div className="flex gap-3">
          <div className="rounded-full bg-status-info p-2 dark:bg-status-info/30">
            <Bell className="h-5 w-5 text-status-info-foreground" />
          </div>
          <div className="flex-1">
            <p className="font-medium">Ativar notificacoes?</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Receba alertas importantes mesmo quando nao estiver no dashboard.
            </p>
            <div className="mt-3 flex gap-2">
              <Button size="sm" onClick={handleEnable} disabled={loading}>
                {loading ? 'Ativando...' : 'Ativar'}
              </Button>
              <Button size="sm" variant="ghost" onClick={handleDismiss}>
                Agora nao
              </Button>
            </div>
          </div>
          <Button variant="ghost" size="icon" className="h-6 w-6" onClick={handleDismiss}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
