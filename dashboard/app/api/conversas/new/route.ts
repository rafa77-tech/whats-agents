/**
 * API: POST /api/conversas/new
 *
 * Inicia ou retoma uma conversa com um contato.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'

export const dynamic = 'force-dynamic'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { phone, doctor_id } = body

    if (!phone || typeof phone !== 'string') {
      return NextResponse.json({ error: 'Telefone é obrigatório' }, { status: 400 })
    }

    // Clean phone number
    const cleanPhone = phone.replace(/\D/g, '')
    if (cleanPhone.length < 10) {
      return NextResponse.json({ error: 'Telefone inválido' }, { status: 400 })
    }

    const supabase = createAdminClient()

    // Try to find existing client by phone
    let cliente_id = doctor_id

    if (!cliente_id) {
      const { data: existingClient } = await supabase
        .from('clientes')
        .select('id')
        .or(`telefone.eq.${cleanPhone},telefone.eq.55${cleanPhone}`)
        .limit(1)
        .single()

      if (existingClient) {
        cliente_id = existingClient.id
      } else {
        // Create new client
        const { data: newClient, error: createError } = await supabase
          .from('clientes')
          .insert({
            telefone: cleanPhone.startsWith('55') ? cleanPhone : `55${cleanPhone}`,
            nome: `Contato ${cleanPhone.slice(-4)}`,
            origem: 'dashboard',
          })
          .select('id')
          .single()

        if (createError) {
          console.error('Erro ao criar cliente:', createError)
          throw createError
        }

        cliente_id = newClient?.id
      }
    }

    if (!cliente_id) {
      return NextResponse.json(
        { error: 'Não foi possível encontrar ou criar o contato' },
        { status: 500 }
      )
    }

    // Find or create conversation
    const { data: existingConv } = await supabase
      .from('conversations')
      .select('id')
      .eq('cliente_id', cliente_id)
      .limit(1)
      .single()

    let conversationId = existingConv?.id

    if (!conversationId) {
      // Create new conversation
      const { data: newConv, error: convError } = await supabase
        .from('conversations')
        .insert({
          cliente_id,
          status: 'active',
          controlled_by: 'human', // Start in handoff mode so operator can send message
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        })
        .select('id')
        .single()

      if (convError) {
        console.error('Erro ao criar conversa:', convError)
        throw convError
      }

      conversationId = newConv?.id
    } else {
      // Set existing conversation to handoff mode
      await supabase
        .from('conversations')
        .update({
          controlled_by: 'human',
          updated_at: new Date().toISOString(),
        })
        .eq('id', conversationId)
    }

    return NextResponse.json({
      success: true,
      conversation_id: conversationId,
      cliente_id,
    })
  } catch (error) {
    console.error('Erro ao criar conversa:', error)
    return NextResponse.json({ error: 'Erro ao criar conversa' }, { status: 500 })
  }
}
