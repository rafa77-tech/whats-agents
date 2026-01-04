'use client'

import { useState, useRef, useEffect } from 'react'
import { Bell, MessageSquare, AlertTriangle, CheckCircle, X } from 'lucide-react'

interface Notification {
  id: string
  type: 'handoff' | 'alerta' | 'sucesso' | 'info'
  title: string
  message: string
  time: string
  read: boolean
}

// TODO: Replace with actual API data
const mockNotifications: Notification[] = [
  {
    id: '1',
    type: 'handoff',
    title: 'Handoff solicitado',
    message: 'Dr. Carlos Silva solicitou atendimento humano',
    time: '2 min',
    read: false,
  },
  {
    id: '2',
    type: 'alerta',
    title: 'Rate limit alto',
    message: 'Julia atingiu 18/20 mensagens nesta hora',
    time: '15 min',
    read: false,
  },
  {
    id: '3',
    type: 'sucesso',
    title: 'Plantao confirmado',
    message: 'Dr. Ana Oliveira confirmou plantao dia 15/01',
    time: '1h',
    read: true,
  },
]

const typeIcons = {
  handoff: MessageSquare,
  alerta: AlertTriangle,
  sucesso: CheckCircle,
  info: Bell,
}

const typeColors = {
  handoff: 'text-blue-500 bg-blue-100',
  alerta: 'text-yellow-500 bg-yellow-100',
  sucesso: 'text-green-500 bg-green-100',
  info: 'text-gray-500 bg-gray-100',
}

export function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false)
  const [notifications, setNotifications] = useState(mockNotifications)
  const menuRef = useRef<HTMLDivElement>(null)

  const unreadCount = notifications.filter((n) => !n.read).length

  // Close when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const markAsRead = (id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    )
  }

  const markAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))
  }

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 h-4 w-4 flex items-center justify-center text-[10px] font-bold text-white bg-red-500 rounded-full">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-lg bg-white shadow-lg border border-gray-200 z-50">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
            <h3 className="font-semibold text-gray-900">Notificacoes</h3>
            {unreadCount > 0 && (
              <button
                onClick={markAllAsRead}
                className="text-xs text-revoluna-600 hover:text-revoluna-700"
              >
                Marcar todas como lidas
              </button>
            )}
          </div>

          {/* Notifications list */}
          <div className="max-h-96 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="px-4 py-8 text-center text-gray-500">
                <Bell className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">Nenhuma notificacao</p>
              </div>
            ) : (
              notifications.map((notification) => {
                const Icon = typeIcons[notification.type]
                const colorClass = typeColors[notification.type]

                return (
                  <div
                    key={notification.id}
                    className={`flex gap-3 px-4 py-3 hover:bg-gray-50 border-b border-gray-50 last:border-0 ${
                      !notification.read ? 'bg-blue-50/50' : ''
                    }`}
                  >
                    <div
                      className={`flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center ${colorClass}`}
                    >
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900">
                        {notification.title}
                      </p>
                      <p className="text-xs text-gray-500 truncate">
                        {notification.message}
                      </p>
                      <p className="text-xs text-gray-400 mt-1">
                        {notification.time}
                      </p>
                    </div>
                    {!notification.read && (
                      <button
                        onClick={() => markAsRead(notification.id)}
                        className="flex-shrink-0 p-1 text-gray-400 hover:text-gray-600"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                )
              })
            )}
          </div>

          {/* Footer */}
          <div className="px-4 py-3 border-t border-gray-100 text-center">
            <button
              onClick={() => setIsOpen(false)}
              className="text-sm text-revoluna-600 hover:text-revoluna-700 font-medium"
            >
              Ver todas as notificacoes
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
