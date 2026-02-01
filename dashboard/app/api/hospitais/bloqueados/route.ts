import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { listarHospitaisBloqueados } from '@/lib/hospitais'

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
    const incluirHistorico = searchParams.get('historico') === 'true'

    const bloqueados = await listarHospitaisBloqueados(supabase, { incluirHistorico })

    return NextResponse.json(bloqueados)
  } catch (error) {
    console.error('Erro ao buscar hospitais bloqueados:', error)
    const message = error instanceof Error ? error.message : 'Erro interno do servidor'
    return NextResponse.json({ detail: message }, { status: 500 })
  }
}
