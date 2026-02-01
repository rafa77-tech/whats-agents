/**
 * API: GET /api/vagas/[id]
 *
 * Retorna detalhes de uma vaga específica.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'

export const dynamic = 'force-dynamic'

export async function GET(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params
    const supabase = createAdminClient()

    const { data: vaga, error } = await supabase
      .from('vagas')
      .select(
        `
        id,
        data,
        hora_inicio,
        hora_fim,
        valor,
        status,
        created_at,
        updated_at,
        hospital_id,
        especialidade_id,
        setor_id,
        hospitais!inner(id, nome),
        especialidades!inner(id, nome),
        setores(id, nome)
      `
      )
      .eq('id', id)
      .single()

    if (error) {
      if (error.code === 'PGRST116') {
        return NextResponse.json({ error: 'Vaga nao encontrada' }, { status: 404 })
      }
      console.error('Erro ao buscar vaga:', error)
      throw error
    }

    const hospital = vaga.hospitais as unknown as { id: string; nome: string } | null
    const especialidade = vaga.especialidades as unknown as { id: string; nome: string } | null
    const setor = vaga.setores as unknown as { id: string; nome: string } | null

    // Check if there's a reservation for this shift
    const { data: reserva } = await supabase
      .from('reservas')
      .select(
        `
        cliente_id,
        clientes(id, primeiro_nome, sobrenome)
      `
      )
      .eq('vaga_id', id)
      .eq('status', 'confirmada')
      .single()

    const cliente = reserva?.clientes as unknown as {
      id: string
      primeiro_nome: string | null
      sobrenome: string | null
    } | null

    const shift = {
      id: vaga.id,
      hospital: hospital?.nome || 'N/A',
      hospital_id: vaga.hospital_id || '',
      especialidade: especialidade?.nome || 'N/A',
      especialidade_id: vaga.especialidade_id || '',
      setor: setor?.nome || null,
      setor_id: vaga.setor_id || null,
      data: vaga.data,
      hora_inicio: vaga.hora_inicio,
      hora_fim: vaga.hora_fim,
      valor: vaga.valor || 0,
      status: vaga.status || 'aberta',
      cliente_id: reserva?.cliente_id || null,
      cliente_nome: cliente
        ? [cliente.primeiro_nome, cliente.sobrenome].filter(Boolean).join(' ')
        : null,
      created_at: vaga.created_at,
      updated_at: vaga.updated_at,
    }

    return NextResponse.json(shift)
  } catch (error) {
    console.error('Erro ao buscar vaga:', error)
    return NextResponse.json({ error: 'Erro ao buscar vaga' }, { status: 500 })
  }
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params
    const supabase = createAdminClient()

    const { error } = await supabase.from('vagas').delete().eq('id', id)

    if (error) {
      console.error('Erro ao deletar vaga:', error)
      throw error
    }

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Erro ao deletar vaga:', error)
    return NextResponse.json({ error: 'Erro ao deletar vaga' }, { status: 500 })
  }
}
