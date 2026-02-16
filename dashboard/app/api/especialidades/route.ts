import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'

export const dynamic = 'force-dynamic'

/**
 * GET /api/especialidades
 * Lista especialidades medicas
 */
export async function GET() {
  try {
    const supabase = createAdminClient()

    const { data, error } = await supabase.from('especialidades').select('id, nome').order('nome')

    if (error) {
      console.error('Erro ao buscar especialidades:', error)
      return NextResponse.json({ detail: 'Erro ao buscar especialidades' }, { status: 500 })
    }

    return NextResponse.json(data || [])
  } catch (error) {
    console.error('Erro ao buscar especialidades:', error)
    return NextResponse.json({ detail: 'Erro interno do servidor' }, { status: 500 })
  }
}

/**
 * POST /api/especialidades
 * Cria nova especialidade
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
      .from('especialidades')
      .insert({ nome })
      .select('id, nome')
      .single()

    if (error) {
      console.error('Erro ao criar especialidade:', error)
      return NextResponse.json({ detail: 'Erro ao criar especialidade' }, { status: 500 })
    }

    return NextResponse.json(data, { status: 201 })
  } catch (error) {
    console.error('Erro ao criar especialidade:', error)
    return NextResponse.json({ detail: 'Erro interno do servidor' }, { status: 500 })
  }
}
