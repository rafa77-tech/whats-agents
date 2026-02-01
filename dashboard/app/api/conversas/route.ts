/**
 * API: GET /api/conversas
 *
 * Lista conversas do banco de dados com informações do chip.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const page = parseInt(searchParams.get('page') || '1')
    const perPage = parseInt(searchParams.get('per_page') || '50')
    const status = searchParams.get('status')
    const controlledBy = searchParams.get('controlled_by')
    const chipId = searchParams.get('chip_id')
    const search = searchParams.get('search')

    const supabase = createAdminClient()

    // First, get conversation IDs filtered by chip if needed
    let conversationIds: string[] | null = null

    if (chipId) {
      const { data: chipConversations } = await supabase
        .from('conversation_chips')
        .select('conversa_id')
        .eq('chip_id', chipId)
        .eq('active', true)

      conversationIds = chipConversations?.map((cc) => cc.conversa_id) || []

      if (conversationIds.length === 0) {
        return NextResponse.json({ data: [], total: 0, pages: 0 })
      }
    }

    // Build main query with join to clientes
    let query = supabase.from('conversations').select(
      `
        id,
        status,
        controlled_by,
        message_count,
        last_message_at,
        created_at,
        cliente_id,
        clientes!inner(id, primeiro_nome, sobrenome, telefone)
      `,
      { count: 'exact' }
    )

    // Filter by chip's conversation IDs
    if (conversationIds) {
      query = query.in('id', conversationIds)
    }

    // Apply other filters
    if (status) {
      query = query.eq('status', status)
    }
    if (controlledBy) {
      query = query.eq('controlled_by', controlledBy)
    }
    if (search) {
      query = query.or(
        `clientes.primeiro_nome.ilike.%${search}%,clientes.sobrenome.ilike.%${search}%,clientes.telefone.ilike.%${search}%`
      )
    }

    // Pagination
    const from = (page - 1) * perPage
    const to = from + perPage - 1

    query = query.order('last_message_at', { ascending: false, nullsFirst: false }).range(from, to)

    const { data: conversations, error, count } = await query

    if (error) {
      console.error('Erro ao buscar conversas:', error)
      throw error
    }

    // Get chip info for all conversations
    const conversaIds = (conversations || []).map((c) => c.id)

    const { data: chipLinks } = await supabase
      .from('conversation_chips')
      .select(
        `
        conversa_id,
        chips!inner(id, telefone, instance_name, status, trust_level)
      `
      )
      .in('conversa_id', conversaIds)
      .eq('active', true)

    // Create a map of conversation to chip
    const chipMap = new Map<
      string,
      { id: string; telefone: string; instance_name: string; status: string; trust_level: string }
    >()

    chipLinks?.forEach((link) => {
      const chip = link.chips as unknown as {
        id: string
        telefone: string
        instance_name: string
        status: string
        trust_level: string
      }
      if (chip) {
        chipMap.set(link.conversa_id, chip)
      }
    })

    // Get last message for each conversation
    const { data: lastMessages } = await supabase
      .from('interacoes')
      .select('cliente_id, conteudo')
      .in(
        'cliente_id',
        (conversations || []).map((c) => c.cliente_id)
      )
      .order('created_at', { ascending: false })

    // Create a map of cliente_id to last message
    const lastMessageMap = new Map<string, string>()
    lastMessages?.forEach((msg) => {
      if (!lastMessageMap.has(msg.cliente_id)) {
        lastMessageMap.set(msg.cliente_id, msg.conteudo || '')
      }
    })

    // Transform data
    const data = (conversations || []).map((c) => {
      const cliente = c.clientes as unknown as {
        id: string
        primeiro_nome: string | null
        sobrenome: string | null
        telefone: string
      } | null

      const clienteNome = cliente
        ? [cliente.primeiro_nome, cliente.sobrenome].filter(Boolean).join(' ') || 'Sem nome'
        : 'Desconhecido'

      const chip = chipMap.get(c.id)

      return {
        id: c.id,
        cliente_nome: clienteNome,
        cliente_telefone: cliente?.telefone || '',
        status: c.status || 'active',
        controlled_by: c.controlled_by || 'julia',
        last_message: lastMessageMap.get(c.cliente_id) || undefined,
        last_message_at: c.last_message_at,
        unread_count: 0,
        chip: chip
          ? {
              id: chip.id,
              telefone: chip.telefone,
              instance_name: chip.instance_name,
              status: chip.status,
              trust_level: chip.trust_level,
            }
          : null,
      }
    })

    const total = count || 0
    const pages = Math.ceil(total / perPage)

    return NextResponse.json({
      data,
      total,
      pages,
    })
  } catch (error) {
    console.error('Erro ao buscar conversas:', error)
    return NextResponse.json({ data: [], total: 0, pages: 0 })
  }
}
