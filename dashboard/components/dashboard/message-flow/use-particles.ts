'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import type { RecentMessage, MessageDirection } from '@/types/dashboard'

export interface Particle {
  id: string
  chipId: string
  direction: MessageDirection
  /** Timestamp de criação para TTL */
  createdAt: number
}

interface UseParticlesOptions {
  messages: RecentMessage[]
  maxParticles?: number
  animationDuration?: number
}

/**
 * Gerencia o ciclo de vida das partículas: cria novas quando mensagens chegam,
 * remove após TTL expirar. Não anima — usa CSS puro para isso.
 */
export function useParticles({
  messages,
  maxParticles = 20,
  animationDuration = 1500,
}: UseParticlesOptions): Particle[] {
  const [particles, setParticles] = useState<Particle[]>([])
  const seenIdsRef = useRef(new Set<string>())
  const cleanupTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const cleanup = useCallback(() => {
    const now = Date.now()
    setParticles((prev) => {
      const alive = prev.filter(
        (p) => now - p.createdAt < animationDuration + 100
      )
      // Clean up seenIds for removed particles
      const aliveIds = new Set(alive.map((p) => p.id))
      seenIdsRef.current.forEach((id) => {
        if (!aliveIds.has(id)) {
          seenIdsRef.current.delete(id)
        }
      })
      return alive
    })
  }, [animationDuration])

  // Schedule periodic cleanup
  useEffect(() => {
    cleanupTimerRef.current = setInterval(cleanup, animationDuration / 2)
    return () => {
      if (cleanupTimerRef.current) {
        clearInterval(cleanupTimerRef.current)
      }
    }
  }, [cleanup, animationDuration])

  // Create particles for new messages
  useEffect(() => {
    const now = Date.now()
    const newParticles: Particle[] = []

    for (const msg of messages) {
      if (seenIdsRef.current.has(msg.id)) continue

      seenIdsRef.current.add(msg.id)
      newParticles.push({
        id: msg.id,
        chipId: msg.chipId,
        direction: msg.direction,
        createdAt: now,
      })
    }

    if (newParticles.length === 0) return

    setParticles((prev) => {
      const combined = [...prev, ...newParticles]
      // Enforce max: drop oldest if over limit
      if (combined.length > maxParticles) {
        const sorted = combined.sort((a, b) => a.createdAt - b.createdAt)
        const dropped = sorted.slice(combined.length - maxParticles)
        // Clean seenIds for dropped particles
        const keptIds = new Set(dropped.map((p) => p.id))
        sorted
          .slice(0, combined.length - maxParticles)
          .forEach((p) => {
            if (!keptIds.has(p.id)) {
              seenIdsRef.current.delete(p.id)
            }
          })
        return dropped
      }
      return combined
    })
  }, [messages, maxParticles])

  return particles
}
