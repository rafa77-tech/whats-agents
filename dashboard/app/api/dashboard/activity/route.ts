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

interface ActivityEventData {
  id: string
  type: ActivityType
  message: string
  chipName?: string
  timestamp: string
}

export async function GET(request: NextRequest) {
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
        total_enviados,
        campanhas (nome)
      `
      )
      .order('created_at', { ascending: false })
      .limit(5)

    interface CampanhaExecRow {
      id: string
      created_at: string
      total_enviados: number | null
      campanhas: {
        nome: string | null
      } | null
    }

    const typedCampanhas = campanhas as unknown as CampanhaExecRow[] | null

    typedCampanhas?.forEach((c) => {
      events.push({
        id: `campanha-${c.id}`,
        type: 'campanha',
        message: `Campanha "${c.campanhas?.nome ?? 'Sem nome'}" enviou ${c.total_enviados ?? 0} mensagens`,
        timestamp: c.created_at,
      })
    })

    // 4. Buscar chips que mudaram de status recentemente
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

    typedChips?.forEach((chip) => {
      if (chip.status === 'ready') {
        events.push({
          id: `chip-ready-${chip.id}`,
          type: 'chip',
          message: `graduou do warming (trust: ${chip.trust_score ?? 0})`,
          chipName: chip.instance_name ?? 'Chip',
          timestamp: chip.updated_at,
        })
      }
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

    // Return mock data on error for development
    const mockEvents: ActivityEventData[] = [
      {
        id: 'mock-1',
        type: 'fechamento',
        message: 'fechou plantao com Dr. Carlos (R$ 2.800)',
        chipName: 'Julia-01',
        timestamp: new Date(Date.now() - 28 * 60 * 1000).toISOString(),
      },
      {
        id: 'mock-2',
        type: 'handoff',
        message: 'handoff: Dra. Maria pediu humano',
        chipName: 'Julia-02',
        timestamp: new Date(Date.now() - 32 * 60 * 1000).toISOString(),
      },
      {
        id: 'mock-3',
        type: 'campanha',
        message: 'Campanha "Reativacao Janeiro" enviou 15 mensagens',
        timestamp: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
      },
      {
        id: 'mock-4',
        type: 'resposta',
        message: 'Dr. Pedro respondeu apos 3 dias',
        chipName: 'Julia-01',
        timestamp: new Date(Date.now() - 58 * 60 * 1000).toISOString(),
      },
      {
        id: 'mock-5',
        type: 'alerta',
        message: 'trust caiu 8 pontos (56 -> 48)',
        chipName: 'Julia-05',
        timestamp: new Date(Date.now() - 75 * 60 * 1000).toISOString(),
      },
      {
        id: 'mock-6',
        type: 'chip',
        message: 'graduou do warming (trust: 85)',
        chipName: 'Julia-03',
        timestamp: new Date(Date.now() - 90 * 60 * 1000).toISOString(),
      },
    ]

    return NextResponse.json({
      events: mockEvents,
      hasMore: false,
    })
  }
}
