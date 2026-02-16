import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'
import { listarHospitais } from '@/lib/hospitais'

export const dynamic = 'force-dynamic'

/**
 * GET /api/hospitais
 * Lista hospitais para seleção no combobox
 * Query params:
 *   - excluir_bloqueados: "true" para excluir hospitais bloqueados
 */
export async function GET(request: NextRequest) {
  try {
    const supabase = createAdminClient()
    const searchParams = request.nextUrl.searchParams
    const excluirBloqueados = searchParams.get('excluir_bloqueados') === 'true'

    const hospitais = await listarHospitais(supabase, { excluirBloqueados })

    return NextResponse.json(hospitais)
  } catch (error) {
    console.error('Erro ao buscar hospitais:', error)
    const message = error instanceof Error ? error.message : 'Erro interno do servidor'
    return NextResponse.json({ detail: message }, { status: 500 })
  }
}

/**
 * POST /api/hospitais
 * Cria novo hospital
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()

    const nome = typeof body.nome === 'string' ? body.nome.trim() : ''
    if (!nome) {
      return NextResponse.json({ detail: 'Nome e obrigatorio' }, { status: 400 })
    }

    const supabase = createAdminClient()

    const { data, error } = await supabase
      .from('hospitais')
      .insert({ nome })
      .select('id, nome')
      .single()

    if (error) {
      console.error('Erro ao criar hospital:', error)
      return NextResponse.json({ detail: 'Erro ao criar hospital' }, { status: 500 })
    }

    return NextResponse.json(data, { status: 201 })
  } catch (error) {
    console.error('Erro ao criar hospital:', error)
    return NextResponse.json({ detail: 'Erro interno do servidor' }, { status: 500 })
  }
}
