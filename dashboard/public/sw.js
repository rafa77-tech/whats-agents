// Service Worker for Web Push Notifications - Julia Dashboard

self.addEventListener('push', function (event) {
  if (!event.data) return

  const data = event.data.json()

  const options = {
    body: data.body,
    icon: '/icon-192.png',
    badge: '/badge-72.png',
    tag: data.tag || 'default',
    data: data.data || {},
    actions: data.actions || [],
    requireInteraction: data.priority === 'high' || data.priority === 'critical',
    vibrate: data.priority === 'critical' ? [200, 100, 200] : undefined,
  }

  event.waitUntil(self.registration.showNotification(data.title, options))
})

self.addEventListener('notificationclick', function (event) {
  event.notification.close()

  const data = event.notification.data
  let url = '/'

  // Redirect based on notification type
  if (data.type === 'handoff_request' && data.conversation_id) {
    url = `/conversas/${data.conversation_id}`
  } else if (data.type === 'rate_limit_warning') {
    url = '/sistema'
  } else if (data.type === 'circuit_open') {
    url = '/sistema'
  } else if (data.type === 'new_conversion' && data.doctor_id) {
    url = `/medicos/${data.doctor_id}`
  } else if (data.type === 'campaign_complete' && data.campaign_id) {
    url = `/campanhas/${data.campaign_id}`
  } else if (data.type === 'system_alert') {
    url = '/sistema'
  }

  event.waitUntil(
    clients.matchAll({ type: 'window' }).then(function (clientList) {
      // If there's already a window open, focus it
      for (const client of clientList) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          client.focus()
          client.navigate(url)
          return
        }
      }
      // Otherwise, open a new window
      if (clients.openWindow) {
        return clients.openWindow(url)
      }
    })
  )
})

// Handle service worker installation
self.addEventListener('install', function (event) {
  self.skipWaiting()
})

// Handle service worker activation
self.addEventListener('activate', function (event) {
  event.waitUntil(clients.claim())
})
