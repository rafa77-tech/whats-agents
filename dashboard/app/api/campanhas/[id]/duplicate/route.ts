import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

/**
 * POST /api/campanhas/[id]/duplicate
 * Duplica uma campanha existente como rascunho
 */
export async function POST(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const supabase = await createClient()

    const {
      data: { user },
    } = await supabase.auth.getUser()
    if (!user) {
      return NextResponse.json({ detail: 'Nao autorizado' }, { status: 401 })
    }

    const { id } = await params
    const campanhaId = parseInt(id, 10)
    if (isNaN(campanhaId)) {
      return NextResponse.json({ detail: 'ID invalido' }, { status: 400 })
    }

    const { data: original, error: fetchError } = await supabase
      .from('campanhas')
      .select('*')
      .eq('id', campanhaId)
      .single()

    if (fetchError || !original) {
      return NextResponse.json({ detail: 'Campanha nao encontrada' }, { status: 404 })
    }

    const { data: nova, error: insertError } = await supabase
      .from('campanhas')
      .insert({
        nome_template: `${original.nome_template} (copia)`,
        tipo_campanha: original.tipo_campanha,
        categoria: original.categoria,
        objetivo: original.objetivo,
        corpo: original.corpo,
        tom: original.tom,
        audience_filters: original.audience_filters,
        escopo_vagas: original.escopo_vagas,
        status: 'rascunho',
        created_by: user.email,
      })
      .select()
      .single()

    if (insertError) {
      console.error('Erro ao duplicar campanha:', insertError)
      return NextResponse.json({ detail: 'Erro ao duplicar campanha' }, { status: 500 })
    }

    await supabase.from('audit_log').insert({
      action: 'campanha_duplicada',
      user_email: user.email,
      details: {
        campanha_original_id: original.id,
        campanha_nova_id: nova.id,
        nome: nova.nome_template,
      },
      created_at: new Date().toISOString(),
    })

    return NextResponse.json(nova, { status: 201 })
  } catch (error) {
    console.error('Erro ao duplicar campanha:', error)
    return NextResponse.json({ detail: 'Erro interno do servidor' }, { status: 500 })
  }
}
