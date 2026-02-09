/**
 * API: GET /api/conversas/[id]/stream
 *
 * SSE proxy para atualizacoes em tempo real.
 * Sprint 54: Real-Time Updates
 */

import { NextRequest } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
): Promise<Response> {
  const { id } = await params

  try {
    const upstream = await fetch(`${API_URL}/dashboard/sse/conversations/${id}`, {
      headers: { Accept: 'text/event-stream' },
    })

    if (!upstream.ok || !upstream.body) {
      return new Response(JSON.stringify({ error: 'SSE connection failed' }), {
        status: upstream.status,
        headers: { 'Content-Type': 'application/json' },
      })
    }

    return new Response(upstream.body, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
        'X-Accel-Buffering': 'no',
      },
    })
  } catch (error) {
    console.error('SSE proxy error:', error)
    return new Response(JSON.stringify({ error: 'SSE connection error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    })
  }
}
