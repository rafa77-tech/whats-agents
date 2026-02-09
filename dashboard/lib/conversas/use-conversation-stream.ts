/**
 * SSE Hook for real-time conversation updates.
 * Sprint 54: Phase 4 - Real-Time Updates
 *
 * Tries SSE first, falls back to SWR polling if SSE fails.
 */

import { useEffect, useRef, useCallback, useState } from 'react'
import { mutate } from 'swr'

type SSEEventType = 'new_message' | 'control_change' | 'pause_change' | 'channel_message'

interface SSEEvent {
  type: SSEEventType
  data: Record<string, unknown>
}

interface UseConversationStreamOptions {
  /** Called when any event is received */
  onEvent?: (event: SSEEvent) => void
  /** Whether to connect (default true) */
  enabled?: boolean
}

interface UseConversationStreamReturn {
  /** Whether SSE is connected */
  isConnected: boolean
  /** Whether using fallback polling */
  isFallback: boolean
}

export function useConversationStream(
  conversationId: string | null,
  options: UseConversationStreamOptions = {}
): UseConversationStreamReturn {
  const { onEvent, enabled = true } = options
  const [isConnected, setIsConnected] = useState(false)
  const [isFallback, setIsFallback] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)
  const fallbackIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const onEventRef = useRef(onEvent)

  // Keep callback ref up to date
  onEventRef.current = onEvent

  const invalidateConversation = useCallback(() => {
    if (!conversationId) return
    // Invalidate SWR caches for this conversation
    void mutate(`/api/conversas/${conversationId}`)
    void mutate((key: string) => typeof key === 'string' && key.startsWith('/api/conversas'), undefined, { revalidate: true })
  }, [conversationId])

  const startFallbackPolling = useCallback(() => {
    if (fallbackIntervalRef.current) return
    setIsFallback(true)

    fallbackIntervalRef.current = setInterval(() => {
      invalidateConversation()
    }, 10000) // 10s polling
  }, [invalidateConversation])

  const stopFallbackPolling = useCallback(() => {
    if (fallbackIntervalRef.current) {
      clearInterval(fallbackIntervalRef.current)
      fallbackIntervalRef.current = null
    }
    setIsFallback(false)
  }, [])

  useEffect(() => {
    if (!conversationId || !enabled) {
      setIsConnected(false)
      return
    }

    // Try SSE connection
    const url = `/api/conversas/${conversationId}/stream`
    let es: EventSource

    try {
      es = new EventSource(url)
      eventSourceRef.current = es

      es.addEventListener('connected', () => {
        setIsConnected(true)
        stopFallbackPolling()
      })

      const handleEvent = (type: SSEEventType) => (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data as string) as Record<string, unknown>
          onEventRef.current?.({ type, data })

          // Invalidate relevant SWR cache on events
          invalidateConversation()
        } catch {
          // Ignore parse errors
        }
      }

      es.addEventListener('new_message', handleEvent('new_message'))
      es.addEventListener('control_change', handleEvent('control_change'))
      es.addEventListener('pause_change', handleEvent('pause_change'))
      es.addEventListener('channel_message', handleEvent('channel_message'))

      es.addEventListener('error', () => {
        setIsConnected(false)
        // If SSE fails, fall back to polling
        if (es.readyState === EventSource.CLOSED) {
          startFallbackPolling()
        }
      })
    } catch {
      // SSE not supported or failed to connect - use polling
      startFallbackPolling()
    }

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
        eventSourceRef.current = null
      }
      setIsConnected(false)
      stopFallbackPolling()
    }
  }, [conversationId, enabled, invalidateConversation, startFallbackPolling, stopFallbackPolling])

  return { isConnected, isFallback }
}
