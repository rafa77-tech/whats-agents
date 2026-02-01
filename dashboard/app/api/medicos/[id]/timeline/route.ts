/**
 * API: GET /api/medicos/[id]/timeline
 *
 * Retorna timeline de interações do médico.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'

export const dynamic = 'force-dynamic'

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params
    const supabase = createAdminClient()

    // Fetch interactions for this doctor
    const { data: interacoes, error } = await supabase
      .from('interacoes')
      .select(
        `
        id,
        tipo,
        conteudo,
        autor_tipo,
        created_at
      `
      )
      .eq('cliente_id', id)
      .order('created_at', { ascending: false })
      .limit(50)

    if (error) {
      console.error('Erro ao buscar timeline:', error)
      throw error
    }

    // Transform to timeline events
    const events = (interacoes || []).map((i) => {
      let type = 'message_received'
      let title = 'Mensagem recebida'

      if (i.autor_tipo === 'julia' || i.autor_tipo === 'agente') {
        type = 'message_sent'
        title = 'Mensagem enviada'
      } else if (i.autor_tipo === 'humano' || i.autor_tipo === 'operador') {
        type = 'handoff'
        title = 'Mensagem do operador'
      }

      return {
        id: String(i.id),
        type,
        title,
        description: i.conteudo?.substring(0, 100) || '',
        created_at: i.created_at,
      }
    })

    return NextResponse.json({ events })
  } catch (error) {
    console.error('Erro ao buscar timeline:', error)
    return NextResponse.json({ events: [] })
  }
}
