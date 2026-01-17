import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

/**
 * GET /api/ajuda
 * Lista pedidos de ajuda
 * Query params:
 *   - status: "pendente,timeout" | "" (todos)
 */
export async function GET(request: NextRequest) {
  try {
    const supabase = await createClient()
    const status = request.nextUrl.searchParams.get('status')

    let query = supabase
      .from('pedidos_ajuda')
      .select(
        `
        *,
        clientes (nome, telefone),
        hospitais (nome)
      `
      )
      .order('criado_em', { ascending: false })
      .limit(50)

    if (status) {
      const statusArray = status.split(',')
      query = query.in('status', statusArray)
    }

    const { data, error } = await query

    if (error) {
      console.error('Erro ao buscar pedidos de ajuda:', error)
      return NextResponse.json({ detail: 'Erro ao buscar pedidos' }, { status: 500 })
    }

    return NextResponse.json(data || [])
  } catch (error) {
    console.error('Erro ao buscar pedidos de ajuda:', error)
    return NextResponse.json({ detail: 'Erro interno do servidor' }, { status: 500 })
  }
}
