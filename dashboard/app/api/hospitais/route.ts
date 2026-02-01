import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
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
    const supabase = await createClient()
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
