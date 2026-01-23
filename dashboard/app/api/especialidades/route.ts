import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

/**
 * GET /api/especialidades
 * Lista especialidades medicas
 */
export async function GET() {
  try {
    const supabase = await createClient()

    const { data, error } = await supabase
      .from('especialidades')
      .select('id, nome')
      .eq('ativo', true)
      .order('nome')

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
