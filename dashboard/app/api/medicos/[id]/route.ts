/**
 * API: GET /api/medicos/[id]
 *
 * Retorna detalhes de um médico específico.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'

export const dynamic = 'force-dynamic'

export async function GET(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params
    const supabase = createAdminClient()

    // Fetch doctor details
    const { data: cliente, error } = await supabase
      .from('clientes')
      .select(
        `
        id,
        primeiro_nome,
        sobrenome,
        telefone,
        crm,
        especialidade,
        cidade,
        estado,
        email,
        stage_jornada,
        opt_out,
        opt_out_data,
        pressure_score_atual,
        contexto_consolidado,
        created_at,
        ultima_mensagem_data
      `
      )
      .eq('id', id)
      .is('deleted_at', null)
      .single()

    if (error) {
      if (error.code === 'PGRST116') {
        return NextResponse.json({ error: 'Medico nao encontrado' }, { status: 404 })
      }
      console.error('Erro ao buscar medico:', error)
      throw error
    }

    // Count conversations for this doctor
    const { count: conversationsCount } = await supabase
      .from('conversations')
      .select('id', { count: 'exact', head: true })
      .eq('cliente_id', id)

    const doctor = {
      id: cliente.id,
      nome: [cliente.primeiro_nome, cliente.sobrenome].filter(Boolean).join(' ') || 'Sem nome',
      telefone: cliente.telefone || '',
      crm: cliente.crm || undefined,
      especialidade: cliente.especialidade || undefined,
      cidade: cliente.cidade || undefined,
      estado: cliente.estado || undefined,
      email: cliente.email || undefined,
      stage_jornada: cliente.stage_jornada || undefined,
      opt_out: cliente.opt_out || false,
      opt_out_data: cliente.opt_out_data || undefined,
      pressure_score_atual: cliente.pressure_score_atual || undefined,
      contexto_consolidado: cliente.contexto_consolidado || undefined,
      created_at: cliente.created_at,
      conversations_count: conversationsCount || 0,
      last_interaction_at: cliente.ultima_mensagem_data || undefined,
    }

    return NextResponse.json(doctor)
  } catch (error) {
    console.error('Erro ao buscar medico:', error)
    return NextResponse.json({ error: 'Erro ao buscar medico' }, { status: 500 })
  }
}
