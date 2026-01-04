'use client'

import { useCallback, useEffect, useState } from 'react'
import { Bell } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { NotificationItem } from './notification-item'
import { useAuth } from '@/hooks/use-auth'
import type { Notification } from '@/lib/notifications/types'

export function NotificationBell() {
  const [open, setOpen] = useState(false)
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [loading, setLoading] = useState(true)

  const { session } = useAuth()

  const fetchNotifications = useCallback(async () => {
    if (!session?.access_token) return

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/dashboard/notifications?limit=10`, {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      })

      if (response.ok) {
        const result = await response.json()
        setNotifications(result.notifications || [])
      }
    } catch (err) {
      console.error('Failed to fetch notifications:', err)
    } finally {
      setLoading(false)
    }
  }, [session?.access_token])

  useEffect(() => {
    fetchNotifications()
    // Refresh every minute
    const interval = setInterval(fetchNotifications, 60000)
    return () => clearInterval(interval)
  }, [fetchNotifications])

  const handleMarkAsRead = async (id: string) => {
    if (!session?.access_token) return

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      await fetch(`${apiUrl}/dashboard/notifications/${id}/read`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      })

      // Update local state
      setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)))
    } catch (err) {
      console.error('Failed to mark as read:', err)
    }
  }

  const handleMarkAllAsRead = async () => {
    if (!session?.access_token) return

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      await fetch(`${apiUrl}/dashboard/notifications/read-all`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      })

      // Update local state
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))
    } catch (err) {
      console.error('Failed to mark all as read:', err)
    }
  }

  const unreadCount = notifications.filter((n) => !n.read).length

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-xs text-white">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </Button>
      </PopoverTrigger>

      <PopoverContent className="w-80 p-0" align="end">
        <div className="flex items-center justify-between p-4">
          <h4 className="font-semibold">Notificacoes</h4>
          {unreadCount > 0 && (
            <Button variant="ghost" size="sm" onClick={handleMarkAllAsRead}>
              Marcar como lidas
            </Button>
          )}
        </div>

        <Separator />

        <ScrollArea className="h-[300px]">
          {loading ? (
            <div className="p-4 text-center text-muted-foreground">Carregando...</div>
          ) : notifications.length === 0 ? (
            <div className="p-4 text-center text-muted-foreground">Nenhuma notificacao</div>
          ) : (
            <div className="divide-y">
              {notifications.map((notification) => (
                <NotificationItem
                  key={notification.id}
                  notification={notification}
                  compact
                  onClose={() => setOpen(false)}
                  onMarkAsRead={handleMarkAsRead}
                />
              ))}
            </div>
          )}
        </ScrollArea>

        <Separator />

        <div className="p-2">
          <Button
            variant="ghost"
            className="w-full"
            onClick={() => {
              setOpen(false)
              window.location.href = '/notificacoes'
            }}
          >
            Ver todas
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  )
}
