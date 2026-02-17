import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'
import { buscarHospitalDetalhado, atualizarHospital, deletarHospitalSeguro } from '@/lib/hospitais'

export const dynamic = 'force-dynamic'

/**
 * GET /api/hospitais/[id]
 * Retorna detalhes de um hospital com aliases e contagens
 */
export async function GET(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params
    const supabase = createAdminClient()

    const hospital = await buscarHospitalDetalhado(supabase, id)

    if (!hospital) {
      return NextResponse.json({ detail: 'Hospital nao encontrado' }, { status: 404 })
    }

    return NextResponse.json(hospital)
  } catch (error) {
    console.error('Erro ao buscar hospital:', error)
    const message = error instanceof Error ? error.message : 'Erro interno do servidor'
    return NextResponse.json({ detail: message }, { status: 500 })
  }
}

/**
 * PATCH /api/hospitais/[id]
 * Atualiza dados de um hospital
 */
export async function PATCH(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params
    const body = await request.json()
    const supabase = createAdminClient()

    const updates: Record<string, unknown> = {}
    if (typeof body.nome === 'string' && body.nome.trim()) updates.nome = body.nome.trim()
    if (typeof body.cidade === 'string') updates.cidade = body.cidade.trim()
    if (typeof body.estado === 'string') updates.estado = body.estado.trim()
    if (typeof body.precisa_revisao === 'boolean') updates.precisa_revisao = body.precisa_revisao

    if (Object.keys(updates).length === 0) {
      return NextResponse.json({ detail: 'Nenhum campo para atualizar' }, { status: 400 })
    }

    await atualizarHospital(supabase, id, updates)

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Erro ao atualizar hospital:', error)
    const message = error instanceof Error ? error.message : 'Erro interno do servidor'
    return NextResponse.json({ detail: message }, { status: 500 })
  }
}

/**
 * DELETE /api/hospitais/[id]
 * Deleta hospital se não tem referências em nenhuma tabela FK
 */
export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params
    const supabase = createAdminClient()

    const deletado = await deletarHospitalSeguro(supabase, id)

    if (!deletado) {
      return NextResponse.json(
        { detail: 'Hospital tem referencias e nao pode ser deletado' },
        { status: 409 }
      )
    }

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Erro ao deletar hospital:', error)
    const message = error instanceof Error ? error.message : 'Erro interno do servidor'
    return NextResponse.json({ detail: message }, { status: 500 })
  }
}
