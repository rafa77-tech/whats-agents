import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

/**
 * GET /api/hospitais/bloqueados
 * Lista hospitais bloqueados
 * Query params:
 *   - historico: "true" para incluir desbloqueados (histórico completo)
 */
export async function GET(request: NextRequest) {
  try {
    const supabase = await createClient()
    const searchParams = request.nextUrl.searchParams
    const historico = searchParams.get('historico') === 'true'

    let query = supabase
      .from('hospitais_bloqueados')
      .select(
        `
        id,
        hospital_id,
        motivo,
        bloqueado_por,
        bloqueado_em,
        status,
        desbloqueado_em,
        desbloqueado_por,
        vagas_movidas,
        hospitais (
          nome,
          cidade
        )
      `
      )
      .order('bloqueado_em', { ascending: false })

    // Se não é histórico, filtrar apenas bloqueados ativos
    if (!historico) {
      query = query.eq('status', 'bloqueado')
    }

    const { data, error } = await query

    if (error) {
      console.error('Erro ao buscar hospitais bloqueados:', error)
      return NextResponse.json({ detail: 'Erro ao buscar hospitais bloqueados' }, { status: 500 })
    }

    return NextResponse.json(data || [])
  } catch (error) {
    console.error('Erro ao buscar hospitais bloqueados:', error)
    return NextResponse.json({ detail: 'Erro interno do servidor' }, { status: 500 })
  }
}
