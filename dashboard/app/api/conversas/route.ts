/**
 * API: GET /api/conversas
 *
 * Lista conversas do banco de dados.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const page = parseInt(searchParams.get('page') || '1')
    const perPage = parseInt(searchParams.get('per_page') || '20')
    const status = searchParams.get('status')
    const controlledBy = searchParams.get('controlled_by')
    const search = searchParams.get('search')

    const supabase = createAdminClient()

    // Build query with join to clientes
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

    // Apply filters
    if (status) {
      query = query.eq('status', status)
    }
    if (controlledBy) {
      query = query.eq('controlled_by', controlledBy)
    }
    if (search) {
      // Search by client name or phone
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

    // Transform data to match frontend interface
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

      return {
        id: c.id,
        cliente_nome: clienteNome,
        cliente_telefone: cliente?.telefone || '',
        status: c.status || 'active',
        controlled_by: c.controlled_by || 'julia',
        last_message_at: c.last_message_at,
        unread_count: 0, // TODO: Calculate from interacoes if needed
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
