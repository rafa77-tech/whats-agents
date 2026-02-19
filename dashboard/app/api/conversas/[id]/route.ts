/**
 * API: GET /api/conversas/[id]
 *
 * Retorna detalhes de uma conversa específica com mensagens e resumo.
 * Sprint 64: Added summary generation + metrics
 */

import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'

export const dynamic = 'force-dynamic'

interface InteracaoRow {
  id: number
  conteudo: string | null
  autor_tipo: string | null
  autor_nome: string | null
  created_at: string | null
  sentimento_score: number | null
  ai_confidence: number | null
}

function generateSummary(
  clienteNome: string,
  messages: { tipo: string; ai_confidence?: number | undefined }[],
  doctor?: {
    especialidade?: string | null
    stage_jornada?: string | null
  } | null
): { text: string; total_msg_medico: number; total_msg_julia: number; duracao_dias: number } {
  const totalMedico = messages.filter((m) => m.tipo === 'entrada').length
  const totalJulia = messages.filter((m) => m.tipo === 'saida').length

  const parts: string[] = []
  parts.push(clienteNome)
  if (doctor?.especialidade) {
    parts[0] = `${clienteNome}, ${doctor.especialidade}`
  }
  parts[0] += '.'

  const stageLabels: Record<string, string> = {
    novo: 'Primeiro contato',
    interessado: 'Demonstrou interesse',
    prospectado: 'Em prospeccao',
    negociando: 'Em negociacao',
    ativo: 'Ativo na plataforma',
    inativo: 'Sem resposta recente',
    perdido: 'Conversa perdida',
  }

  if (doctor?.stage_jornada && stageLabels[doctor.stage_jornada]) {
    parts.push(stageLabels[doctor.stage_jornada] + '.')
  }

  parts.push(
    `${totalMedico + totalJulia} mensagens trocadas (${totalMedico} medico, ${totalJulia} Julia).`
  )

  // Calculate duration
  let duracaoDias = 0
  if (messages.length >= 2) {
    // Messages are ordered by created_at ascending
    const firstMsg = messages[0]
    const lastMsg = messages[messages.length - 1]
    if (firstMsg && lastMsg) {
      // Duration approximated from message count / typical pace
      duracaoDias = Math.max(1, Math.ceil(messages.length / 10))
    }
  }

  return {
    text: parts.join(' '),
    total_msg_medico: totalMedico,
    total_msg_julia: totalJulia,
    duracao_dias: duracaoDias,
  }
}

export async function GET(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params
    const supabase = createAdminClient()

    // Fetch conversation with client info + pause state + doctor details
    const { data: conversation, error: convError } = await supabase
      .from('conversations')
      .select(
        `
        id,
        status,
        controlled_by,
        cliente_id,
        pausada_em,
        motivo_pausa,
        clientes!inner(id, primeiro_nome, sobrenome, telefone, especialidade, stage_jornada)
      `
      )
      .eq('id', id)
      .single()

    if (convError) {
      if (convError.code === 'PGRST116') {
        return NextResponse.json({ error: 'Conversa nao encontrada' }, { status: 404 })
      }
      console.error('Erro ao buscar conversa:', convError)
      throw convError
    }

    const cliente = conversation.clientes as unknown as {
      id: string
      primeiro_nome: string | null
      sobrenome: string | null
      telefone: string
      especialidade?: string | null
      stage_jornada?: string | null
    } | null

    const clienteNome = cliente
      ? [cliente.primeiro_nome, cliente.sobrenome].filter(Boolean).join(' ') || 'Sem nome'
      : 'Desconhecido'

    // Fetch messages (interacoes) for this conversation
    const { data: interacoes, error: msgError } = await supabase
      .from('interacoes')
      .select(
        `
        id,
        conteudo,
        autor_tipo,
        autor_nome,
        created_at,
        sentimento_score,
        ai_confidence
      `
      )
      .eq('conversation_id', id)
      .order('created_at', { ascending: true })
      .limit(100)

    if (msgError) {
      console.error('Erro ao buscar mensagens:', msgError)
    }

    // Transform messages
    const messages = ((interacoes as InteracaoRow[] | null) || []).map((msg) => ({
      id: String(msg.id),
      tipo: msg.autor_tipo === 'medico' ? 'entrada' : 'saida',
      conteudo: msg.conteudo || '',
      created_at: msg.created_at || new Date().toISOString(),
      sentimento_score: msg.sentimento_score ?? undefined,
      ai_confidence: msg.ai_confidence ?? undefined,
    }))

    // Generate summary
    const summary = generateSummary(clienteNome, messages, cliente)

    const result = {
      id: conversation.id,
      status: conversation.status || 'active',
      controlled_by: conversation.controlled_by || 'ai',
      pausada_em: (conversation as Record<string, unknown>).pausada_em ?? null,
      motivo_pausa: (conversation as Record<string, unknown>).motivo_pausa ?? null,
      cliente: {
        id: cliente?.id || '',
        nome: clienteNome,
        telefone: cliente?.telefone || '',
      },
      messages,
      summary: {
        text: summary.text,
        total_msg_medico: summary.total_msg_medico,
        total_msg_julia: summary.total_msg_julia,
        duracao_dias: summary.duracao_dias,
      },
    }

    return NextResponse.json(result)
  } catch (error) {
    console.error('Erro ao buscar conversa:', error)
    return NextResponse.json({ error: 'Erro ao buscar conversa' }, { status: 500 })
  }
}
