/**
 * API: GET /api/conversas/[id]/context
 *
 * Retorna contexto do medico para o painel lateral.
 * Sprint 54: Supervision Dashboard - Phase 2
 */

import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'
import type { DoctorContextData } from '@/types/conversas'

export const dynamic = 'force-dynamic'

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
): Promise<NextResponse> {
  try {
    const { id } = await params
    const supabase = createAdminClient()

    // Get conversation to find cliente_id
    const { data: conversation, error: convError } = await supabase
      .from('conversations')
      .select('cliente_id')
      .eq('id', id)
      .single()

    if (convError || !conversation) {
      return NextResponse.json({ error: 'Conversa nao encontrada' }, { status: 404 })
    }

    const clienteId = conversation.cliente_id

    // Parallel queries for all context data
    const [
      clienteResult,
      memoryResult,
      metricsResult,
      handoffsResult,
      eventsResult,
      conversationCountResult,
    ] = await Promise.all([
      // Doctor profile
      supabase
        .from('clientes')
        .select(
          'primeiro_nome, sobrenome, telefone, crm, especialidade, stage_jornada, pressure_score_atual, tags, opt_out, cidade, estado, created_at'
        )
        .eq('id', clienteId)
        .single(),

      // Doctor memory (valid entries, latest 20)
      supabase
        .from('doctor_context')
        .select('content, tipo, created_at')
        .eq('cliente_id', clienteId)
        .eq('valido', true)
        .order('created_at', { ascending: false })
        .limit(20),

      // Conversation metrics
      supabase
        .from('metricas_conversa')
        .select(
          'total_mensagens_medico, total_mensagens_julia, tempo_medio_resposta_segundos, duracao_conversa_minutos, houve_handoff'
        )
        .eq('conversa_id', id)
        .single(),

      // Handoff history (latest 5)
      supabase
        .from('handoffs')
        .select('motivo, trigger_type, status, created_at, notas')
        .eq('conversation_id', id)
        .order('created_at', { ascending: false })
        .limit(5),

      // Business events (latest 15)
      supabase
        .from('business_events')
        .select('event_type, event_props, ts')
        .eq('cliente_id', clienteId)
        .order('ts', { ascending: false })
        .limit(15),

      // Total conversations for this client
      supabase
        .from('conversations')
        .select('id', { count: 'exact', head: true })
        .eq('cliente_id', clienteId),
    ])

    const cliente = clienteResult.data
    const nome = cliente
      ? [cliente.primeiro_nome, cliente.sobrenome].filter(Boolean).join(' ') || 'Sem nome'
      : 'Desconhecido'

    const metrics = metricsResult.data

    const result: DoctorContextData = {
      doctor: {
        nome,
        telefone: cliente?.telefone || '',
        crm: cliente?.crm || undefined,
        especialidade: cliente?.especialidade || undefined,
        stage_jornada: cliente?.stage_jornada || undefined,
        pressure_score: cliente?.pressure_score_atual ?? undefined,
        tags: Array.isArray(cliente?.tags) ? (cliente.tags as string[]) : undefined,
        opt_out: cliente?.opt_out ?? false,
        cidade: cliente?.cidade || undefined,
        estado: cliente?.estado || undefined,
      },
      memory: (memoryResult.data || []).map((m) => ({
        content: m.content || '',
        tipo: m.tipo || 'geral',
        created_at: m.created_at || '',
      })),
      metrics: {
        total_msg_medico: metrics?.total_mensagens_medico ?? 0,
        total_msg_julia: metrics?.total_mensagens_julia ?? 0,
        tempo_medio_resposta: metrics?.tempo_medio_resposta_segundos
          ? Number(metrics.tempo_medio_resposta_segundos)
          : 0,
        duracao_minutos: metrics?.duracao_conversa_minutos
          ? Number(metrics.duracao_conversa_minutos)
          : 0,
        houve_handoff: metrics?.houve_handoff ?? false,
      },
      handoff_history: (handoffsResult.data || []).map((h) => ({
        motivo: h.motivo || '',
        trigger_type: h.trigger_type || '',
        status: h.status || '',
        created_at: h.created_at || '',
        notas: h.notas || undefined,
      })),
      recent_events: (eventsResult.data || []).map((e) => ({
        event_type: e.event_type || '',
        event_props: (e.event_props || {}) as Record<string, unknown>,
        ts: e.ts || '',
      })),
      conversation_count: conversationCountResult.count || 0,
      first_contact_at: cliente?.created_at || undefined,
    }

    return NextResponse.json(result)
  } catch (error) {
    console.error('Erro ao buscar contexto:', error)
    return NextResponse.json({ error: 'Erro ao buscar contexto' }, { status: 500 })
  }
}
