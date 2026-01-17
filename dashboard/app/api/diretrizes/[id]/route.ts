import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

interface PatchBody {
  status: 'cancelada'
}

/**
 * PATCH /api/diretrizes/[id]
 * Atualiza uma diretriz (usado para cancelar)
 */
export async function PATCH(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const supabase = await createClient()
    const { id } = await params

    // Verificar autenticacao
    const {
      data: { user },
    } = await supabase.auth.getUser()
    if (!user) {
      return NextResponse.json({ detail: 'Nao autorizado' }, { status: 401 })
    }

    const body = (await request.json()) as PatchBody

    // Buscar diretriz atual
    const { data: diretriz, error: fetchError } = await supabase
      .from('diretrizes_contextuais')
      .select('*')
      .eq('id', id)
      .single()

    if (fetchError || !diretriz) {
      return NextResponse.json({ detail: 'Diretriz nao encontrada' }, { status: 404 })
    }

    // Atualizar status
    const { data, error } = await supabase
      .from('diretrizes_contextuais')
      .update({
        status: body.status,
        cancelado_em: new Date().toISOString(),
        cancelado_por: user.email || user.id,
      })
      .eq('id', id)
      .select()
      .single()

    if (error) {
      console.error('Erro ao atualizar diretriz:', error)
      return NextResponse.json({ detail: 'Erro ao atualizar diretriz' }, { status: 500 })
    }

    // Registrar no audit_log
    await supabase.from('audit_log').insert({
      action: 'diretriz_cancelada',
      user_email: user.email,
      details: {
        diretriz_id: id,
        tipo: diretriz.tipo,
        escopo: diretriz.escopo,
      },
      created_at: new Date().toISOString(),
    })

    return NextResponse.json(data)
  } catch (error) {
    console.error('Erro ao atualizar diretriz:', error)
    return NextResponse.json({ detail: 'Erro interno do servidor' }, { status: 500 })
  }
}
