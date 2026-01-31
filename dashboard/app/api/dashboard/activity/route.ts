/**
 * API: GET /api/dashboard/activity
 *
 * Returns recent activity events from multiple sources:
 * - Closings (plantao fechado)
 * - Handoffs
 * - Campaign executions
 * - Chip transitions (warming graduation, trust changes)
 *
 * Query params:
 * - limit: number of events (default: 10)
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { type ActivityType } from '@/types/dashboard'
import { shouldUseMock, mockActivity } from '@/lib/mock'

export const dynamic = 'force-dynamic'

interface ActivityEventData {
  id: string
  type: ActivityType
  message: string
  chipName?: string
  timestamp: string
}

export async function GET(request: NextRequest) {
  // Return mock data for E2E tests
  if (shouldUseMock()) {
    return NextResponse.json(mockActivity)
  }

  try {
    const supabase = await createClient()
    const limit = parseInt(request.nextUrl.searchParams.get('limit') ?? '10')
    const events: ActivityEventData[] = []

    // 1. Buscar fechamentos recentes
    const { data: fechamentos } = await supabase
      .from('conversations')
      .select(
        `
        id,
        updated_at,
        clientes (primeiro_nome, sobrenome)
      `
      )
      .eq('status', 'fechado')
      .order('updated_at', { ascending: false })
      .limit(5)

    interface FechamentoRow {
      id: string
      updated_at: string
      clientes: {
        primeiro_nome: string | null
        sobrenome: string | null
      } | null
    }

    const typedFechamentos = fechamentos as unknown as FechamentoRow[] | null

    typedFechamentos?.forEach((f) => {
      const cliente = f.clientes
      const nome = cliente
        ? `${cliente.primeiro_nome ?? ''} ${cliente.sobrenome ?? ''}`.trim() || 'medico'
        : 'medico'

      events.push({
        id: `fechamento-${f.id}`,
        type: 'fechamento',
        message: `fechou plantao com ${nome}`,
        chipName: 'Julia',
        timestamp: f.updated_at,
      })
    })

    // 2. Buscar handoffs recentes
    const { data: handoffs } = await supabase
      .from('handoffs')
      .select(
        `
        id,
        created_at,
        motivo,
        conversations (
          clientes (primeiro_nome, sobrenome)
        )
      `
      )
      .order('created_at', { ascending: false })
      .limit(5)

    interface HandoffRow {
      id: string
      created_at: string
      motivo: string | null
      conversations: {
        clientes: {
          primeiro_nome: string | null
          sobrenome: string | null
        } | null
      } | null
    }

    const typedHandoffs = handoffs as unknown as HandoffRow[] | null

    typedHandoffs?.forEach((h) => {
      const cliente = h.conversations?.clientes
      const nome = cliente
        ? `${cliente.primeiro_nome ?? ''} ${cliente.sobrenome ?? ''}`.trim() || 'Medico'
        : 'Medico'

      events.push({
        id: `handoff-${h.id}`,
        type: 'handoff',
        message: `handoff: ${nome} ${h.motivo ?? 'pediu humano'}`,
        chipName: 'Julia',
        timestamp: h.created_at,
      })
    })

    // 3. Buscar execucoes de campanha
    const { data: campanhas } = await supabase
      .from('execucoes_campanhas')
      .select(
        `
        id,
        created_at,
        nome_execucao,
        quantidade_enviada,
        status
      `
      )
      .order('created_at', { ascending: false })
      .limit(5)

    interface CampanhaExecRow {
      id: string
      created_at: string
      nome_execucao: string | null
      quantidade_enviada: number | null
      status: string | null
    }

    const typedCampanhas = campanhas as unknown as CampanhaExecRow[] | null

    typedCampanhas?.forEach((c) => {
      const statusLabel = c.status === 'pendente' ? 'agendada' : c.status === 'concluida' ? 'concluída' : c.status
      events.push({
        id: `campanha-${c.id}`,
        type: 'campanha',
        message: `Campanha "${c.nome_execucao ?? 'Sem nome'}" ${statusLabel} (${c.quantidade_enviada ?? 0} msgs)`,
        timestamp: c.created_at,
      })
    })

    // 4. Buscar chips atualizados recentemente (qualquer mudança)
    const { data: chipsRecentes } = await supabase
      .from('chips')
      .select('id, instance_name, status, trust_score, updated_at')
      .order('updated_at', { ascending: false })
      .limit(5)

    interface ChipRow {
      id: string
      instance_name: string | null
      status: string | null
      trust_score: number | null
      updated_at: string
    }

    const typedChips = chipsRecentes as unknown as ChipRow[] | null

    const statusMessages: Record<string, string> = {
      ready: 'graduou do warming',
      active: 'está ativo',
      warming: 'em aquecimento',
      degraded: 'trust degradado',
      paused: 'foi pausado',
      banned: 'foi banido',
    }

    typedChips?.forEach((chip) => {
      const statusMsg = statusMessages[chip.status ?? ''] ?? `status: ${chip.status}`
      events.push({
        id: `chip-${chip.id}`,
        type: 'chip',
        message: `${statusMsg} (trust: ${chip.trust_score ?? 0})`,
        chipName: chip.instance_name ?? 'Chip',
        timestamp: chip.updated_at,
      })
    })

    // Ordenar por timestamp (mais recente primeiro) e limitar
    events.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    const limitedEvents = events.slice(0, limit)

    return NextResponse.json({
      events: limitedEvents,
      hasMore: events.length > limit,
    })
  } catch (error) {
    console.error('Error fetching activity:', error)
    return NextResponse.json({ error: 'Failed to fetch activity' }, { status: 500 })
  }
}
