/**
 * API: GET /api/contatos-grupo
 *
 * Lista contatos conhecidos de grupos para combobox de contato responsavel.
 * Usa createAdminClient() pois contatos_grupo tem RLS service_role only.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  try {
    const search = request.nextUrl.searchParams.get('search') || ''
    const supabase = createAdminClient()

    let query = supabase
      .from('contatos_grupo')
      .select('id, nome, telefone, empresa')
      .not('nome', 'is', null)
      .order('total_vagas_postadas', { ascending: false, nullsFirst: false })
      .limit(50)

    if (search.trim()) {
      query = query.or(`nome.ilike.%${search.trim()}%,telefone.ilike.%${search.trim()}%`)
    }

    const { data, error } = await query

    if (error) {
      console.error('Erro ao buscar contatos grupo:', error)
      return NextResponse.json({ data: [] })
    }

    return NextResponse.json({ data: data || [] })
  } catch (error) {
    console.error('Erro ao buscar contatos grupo:', error)
    return NextResponse.json({ data: [] })
  }
}
