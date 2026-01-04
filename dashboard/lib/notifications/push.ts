const VAPID_PUBLIC_KEY = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY || ''

export async function registerPushNotifications(): Promise<PushSubscription | null> {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    console.log('Push notifications not supported')
    return null
  }

  try {
    // Register service worker
    const registration = await navigator.serviceWorker.register('/sw.js')
    console.log('Service Worker registered')

    // Check permission
    const permission = await Notification.requestPermission()
    if (permission !== 'granted') {
      console.log('Notification permission denied')
      return null
    }

    // Get or create subscription
    let subscription = await registration.pushManager.getSubscription()

    if (!subscription && VAPID_PUBLIC_KEY) {
      subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY),
      })
    }

    return subscription
  } catch (error) {
    console.error('Failed to register push:', error)
    return null
  }
}

export async function unregisterPushNotifications(): Promise<boolean> {
  try {
    const registration = await navigator.serviceWorker.ready
    const subscription = await registration.pushManager.getSubscription()

    if (subscription) {
      await subscription.unsubscribe()
      return true
    }

    return false
  } catch (error) {
    console.error('Failed to unregister push:', error)
    return false
  }
}

export function isPushSupported(): boolean {
  return 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window
}

export function getPushPermissionState(): NotificationPermission | 'unsupported' {
  if (!('Notification' in window)) {
    return 'unsupported'
  }
  return Notification.permission
}

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')

  const rawData = window.atob(base64)
  const outputArray = new Uint8Array(rawData.length)

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i)
  }
  return outputArray
}
