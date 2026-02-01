/**
 * API: GET /api/health/services
 * Sprint 43 - Health Center
 *
 * Verifica status de todos os servicos externos.
 */

import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface ServiceStatus {
  name: string
  status: 'ok' | 'warn' | 'error'
  latency: number | undefined
  details: string | undefined
}

export async function GET() {
  const services: ServiceStatus[] = []
  const startTime = Date.now()

  // Check WhatsApp (via backend)
  try {
    const whatsappStart = Date.now()
    const res = await fetch(`${API_URL}/health/whatsapp`, {
      headers: { Authorization: `Bearer ${process.env.API_SECRET ?? ''}` },
      cache: 'no-store',
    })
    const latency = Date.now() - whatsappStart

    if (res.ok) {
      const data = (await res.json()) as { connected?: boolean; state?: string }
      services.push({
        name: 'WhatsApp',
        status: data.connected ? 'ok' : 'error',
        latency,
        details: data.state,
      })
    } else {
      services.push({
        name: 'WhatsApp',
        status: 'error',
        latency: undefined,
        details: 'Backend error',
      })
    }
  } catch {
    services.push({ name: 'WhatsApp', status: 'error', latency: undefined, details: 'Unreachable' })
  }

  // Check Redis, Supabase, and LLM via single backend health call
  try {
    const healthStart = Date.now()
    const res = await fetch(`${API_URL}/health/ready`, {
      headers: { Authorization: `Bearer ${process.env.API_SECRET ?? ''}` },
      cache: 'no-store',
    })
    const latency = Date.now() - healthStart

    if (res.ok) {
      const data = (await res.json()) as { checks?: { redis?: string; database?: string } }

      // Redis status (returns string like "ok", "error", "degraded")
      const redisStatus = data.checks?.redis
      services.push({
        name: 'Redis',
        status: redisStatus === 'ok' ? 'ok' : redisStatus === 'degraded' ? 'warn' : 'error',
        latency,
        details: redisStatus,
      })

      // Supabase/Database status
      const dbStatus = data.checks?.database
      services.push({
        name: 'Supabase',
        status: dbStatus === 'ok' ? 'ok' : dbStatus === 'degraded' ? 'warn' : 'error',
        latency,
        details: dbStatus,
      })

      // LLM is considered ok if backend is up
      services.push({
        name: 'LLM',
        status: 'ok',
        latency,
        details: 'Available',
      })
    } else {
      services.push({ name: 'Redis', status: 'warn', latency: undefined, details: 'Check failed' })
      services.push({
        name: 'Supabase',
        status: 'warn',
        latency: undefined,
        details: 'Check failed',
      })
      services.push({ name: 'LLM', status: 'warn', latency: undefined, details: 'Check failed' })
    }
  } catch {
    services.push({ name: 'Redis', status: 'error', latency: undefined, details: 'Unreachable' })
    services.push({ name: 'Supabase', status: 'error', latency: undefined, details: 'Unreachable' })
    services.push({ name: 'LLM', status: 'error', latency: undefined, details: 'Unreachable' })
  }

  return NextResponse.json({
    services,
    totalLatency: Date.now() - startTime,
    timestamp: new Date().toISOString(),
  })
}
