/**
 * API: POST /api/conversas/[id]/send
 *
 * Envia uma mensagem via WhatsApp através do backend Python.
 */

import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params
    const body = await request.json()
    const { message, media_url, media_type, caption } = body

    // Validate input
    if (!message && !media_url) {
      return NextResponse.json({ error: 'Mensagem ou mídia é obrigatória' }, { status: 400 })
    }

    // Determine which endpoint to call
    let endpoint: string
    let payload: Record<string, unknown>

    if (media_url) {
      // Send media
      endpoint = `${API_URL}/dashboard/conversations/send-media`
      payload = {
        conversation_id: id,
        media_url,
        media_type: media_type || 'document',
        caption: caption || message,
      }
    } else {
      // Send text
      endpoint = `${API_URL}/dashboard/conversations/send-text`
      payload = {
        conversation_id: id,
        message: message.trim(),
      }
    }

    // Call Python backend
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    const result = await response.json()

    if (!response.ok) {
      console.error('Backend error:', result)
      return NextResponse.json(
        { error: result.detail || 'Erro ao enviar mensagem' },
        { status: response.status }
      )
    }

    return NextResponse.json(result)
  } catch (error) {
    console.error('Erro ao enviar mensagem:', error)
    return NextResponse.json({ error: 'Erro ao enviar mensagem' }, { status: 500 })
  }
}
