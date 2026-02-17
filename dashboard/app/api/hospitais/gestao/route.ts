import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'
import { listarHospitaisGestao } from '@/lib/hospitais'

export const dynamic = 'force-dynamic'

/**
 * GET /api/hospitais/gestao
 * Lista hospitais para página de gestão com paginação e filtros
 */
export async function GET(request: NextRequest) {
  try {
    const supabase = createAdminClient()
    const searchParams = request.nextUrl.searchParams

    const page = parseInt(searchParams.get('page') || '1', 10)
    const perPage = parseInt(searchParams.get('per_page') || '20', 10)
    const search = searchParams.get('search') || undefined
    const status = (searchParams.get('status') as 'todos' | 'revisados' | 'pendentes') || 'todos'
    const cidade = searchParams.get('cidade') || undefined

    const params: Parameters<typeof listarHospitaisGestao>[1] = {
      page,
      perPage: Math.min(perPage, 100),
      status,
    }
    if (search) params.search = search
    if (cidade) params.cidade = cidade

    const result = await listarHospitaisGestao(supabase, params)

    return NextResponse.json(result)
  } catch (error) {
    console.error('Erro ao buscar hospitais (gestão):', error)
    const message = error instanceof Error ? error.message : 'Erro interno do servidor'
    return NextResponse.json({ detail: message }, { status: 500 })
  }
}
