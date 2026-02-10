/**
 * API: GET /api/dashboard/message-flow
 *
 * Retorna chips ativos com métricas recentes e mensagens dos últimos 5 minutos
 * para o widget de visualização de fluxo de mensagens. Otimizado para polling 5s.
 */

import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import type {
  ChipNode,
  ChipNodeStatus,
  MessageFlowData,
  RecentMessage,
} from '@/types/dashboard'

export const dynamic = 'force-dynamic'

/** Mapeia status do banco para status visual do widget */
function mapChipStatus(dbStatus: string): ChipNodeStatus {
  switch (dbStatus) {
    case 'active':
      return 'active'
    case 'warming':
    case 'ready':
      return 'warming'
    case 'degraded':
      return 'degraded'
    case 'paused':
      return 'paused'
    default:
      return 'offline'
  }
}

interface ChipRow {
  id: string
  instance_name: string
  status: string
  trust_score: number | null
  msgs_enviadas_hoje: number | null
  msgs_recebidas_hoje: number | null
}

interface InteracaoRow {
  id: number
  chip_id: string
  tipo: string
  created_at: string
}

export async function GET(): Promise<NextResponse> {
  try {
    const supabase = await createClient()
    const now = new Date()

    // 1. Buscar chips com status relevante (limit 15, ordenado por trust_score)
    const { data: chipsData, error: chipsError } = await supabase
      .from('chips')
      .select('id, instance_name, status, trust_score, msgs_enviadas_hoje, msgs_recebidas_hoje')
      .in('status', ['active', 'warming', 'ready', 'degraded', 'paused'])
      .order('trust_score', { ascending: false, nullsFirst: false })
      .limit(15)

    if (chipsError) {
      console.error('[message-flow] chips query error:', chipsError)
      throw chipsError
    }

    const chips = (chipsData as ChipRow[] | null) ?? []
    const chipIds = chips.map((c) => c.id)

    // 2. Buscar mensagens dos últimos 5 minutos (para animação de partículas)
    const fiveMinAgo = new Date(now.getTime() - 5 * 60 * 1000)
    let recentInteracoes: InteracaoRow[] = []

    if (chipIds.length > 0) {
      const { data: msgData, error: msgError } = await supabase
        .from('interacoes')
        .select('id, chip_id, tipo, created_at')
        .in('chip_id', chipIds)
        .gte('created_at', fiveMinAgo.toISOString())
        .order('created_at', { ascending: false })
        .limit(50)

      if (msgError) {
        console.error('[message-flow] messages query error:', msgError)
      } else {
        recentInteracoes = (msgData as InteracaoRow[] | null) ?? []
      }
    }

    // 3. Contar mensagens/minuto (último minuto, todas as interações)
    const oneMinAgo = new Date(now.getTime() - 60 * 1000)
    const { count: msgsLastMinute } = await supabase
      .from('interacoes')
      .select('*', { count: 'exact', head: true })
      .gte('created_at', oneMinAgo.toISOString())

    // 4. Calcular atividade recente por chip (últimos 2 min = "ativo")
    const twoMinAgo = new Date(now.getTime() - 2 * 60 * 1000)
    const activeChipIds = new Set(
      recentInteracoes
        .filter((m) => new Date(m.created_at) >= twoMinAgo)
        .map((m) => m.chip_id)
    )

    // Contadores de mensagens recentes por chip
    const chipOutbound = new Map<string, number>()
    const chipInbound = new Map<string, number>()
    for (const msg of recentInteracoes) {
      if (msg.tipo === 'saida') {
        chipOutbound.set(msg.chip_id, (chipOutbound.get(msg.chip_id) ?? 0) + 1)
      } else {
        chipInbound.set(msg.chip_id, (chipInbound.get(msg.chip_id) ?? 0) + 1)
      }
    }

    // 5. Montar ChipNode[]
    const chipNodes: ChipNode[] = chips.map((chip) => ({
      id: chip.id,
      name: chip.instance_name || 'Unknown',
      status: mapChipStatus(chip.status),
      trustScore: chip.trust_score ?? 0,
      recentOutbound: chipOutbound.get(chip.id) ?? 0,
      recentInbound: chipInbound.get(chip.id) ?? 0,
      isActive: activeChipIds.has(chip.id),
    }))

    // 6. Montar RecentMessage[]
    const recentMessages: RecentMessage[] = recentInteracoes.map((msg) => ({
      id: String(msg.id),
      chipId: msg.chip_id,
      direction: msg.tipo === 'saida' ? 'outbound' : 'inbound',
      timestamp: msg.created_at,
    }))

    const result: MessageFlowData = {
      chips: chipNodes,
      recentMessages,
      messagesPerMinute: msgsLastMinute ?? 0,
      updatedAt: now.toISOString(),
    }

    return NextResponse.json(result)
  } catch (error) {
    console.error('[message-flow] Error:', error)
    return NextResponse.json({ error: 'Failed to fetch message flow data' }, { status: 500 })
  }
}
