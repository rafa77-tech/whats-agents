import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

/**
 * GET /api/hospitais
 * Lista hospitais para seleção no combobox
 * Query params:
 *   - excluir_bloqueados: "true" para excluir hospitais bloqueados
 */
export async function GET(request: NextRequest) {
  try {
    const supabase = await createClient()
    const searchParams = request.nextUrl.searchParams
    const excluirBloqueados = searchParams.get('excluir_bloqueados') === 'true'

    // Buscar hospitais
    const query = supabase
      .from('hospitais')
      .select('id, nome, cidade')
      .eq('ativo', true)
      .order('nome')

    const { data: hospitais, error } = await query

    if (error) {
      console.error('Erro ao buscar hospitais:', error)
      return NextResponse.json({ detail: 'Erro ao buscar hospitais' }, { status: 500 })
    }

    let resultado = hospitais || []

    // Se excluir bloqueados, filtrar hospitais que estão bloqueados
    if (excluirBloqueados) {
      const { data: bloqueados } = await supabase
        .from('hospitais_bloqueados')
        .select('hospital_id')
        .eq('status', 'bloqueado')

      const idsBloqueados = new Set((bloqueados || []).map((b) => b.hospital_id))
      resultado = resultado.filter((h) => !idsBloqueados.has(h.id))
    }

    // Buscar contagem de vagas abertas para cada hospital
    const { data: vagasCount } = await supabase
      .from('vagas')
      .select('hospital_id')
      .eq('status', 'aberta')

    const vagasPorHospital = new Map<string, number>()
    ;(vagasCount || []).forEach((v) => {
      const count = vagasPorHospital.get(v.hospital_id) || 0
      vagasPorHospital.set(v.hospital_id, count + 1)
    })

    const hospitaisComVagas = resultado.map((h) => ({
      ...h,
      vagas_abertas: vagasPorHospital.get(h.id) || 0,
    }))

    return NextResponse.json(hospitaisComVagas)
  } catch (error) {
    console.error('Erro ao buscar hospitais:', error)
    return NextResponse.json({ detail: 'Erro interno do servidor' }, { status: 500 })
  }
}
