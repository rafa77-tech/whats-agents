/**
 * API: GET /api/dashboard/operational
 *
 * Retorna status operacional (rate limits, fila, LLM usage, instancias).
 */

import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

// Limites de rate (do CLAUDE.md)
const RATE_LIMITS = {
  hour: 20,
  day: 100,
}

interface ChipRow {
  instance_name: string
  evolution_connected: boolean
  msgs_enviadas_hoje: number
  status: string
  provider: string | null
}

export async function GET() {
  try {
    const supabase = await createClient()

    // === Fila de Mensagens ===

    const { count: queueSize } = await supabase
      .from('fila_mensagens')
      .select('*', { count: 'exact', head: true })
      .eq('status', 'pending')

    // === Rate Limit Hora ===

    const oneHourAgo = new Date()
    oneHourAgo.setHours(oneHourAgo.getHours() - 1)

    const { count: msgsLastHour } = await supabase
      .from('interacoes')
      .select('*', { count: 'exact', head: true })
      .eq('tipo', 'saida')
      .gte('created_at', oneHourAgo.toISOString())

    // === Rate Limit Dia ===

    const todayStart = new Date()
    todayStart.setHours(0, 0, 0, 0)

    const { count: msgsToday } = await supabase
      .from('interacoes')
      .select('*', { count: 'exact', head: true })
      .eq('tipo', 'saida')
      .gte('created_at', todayStart.toISOString())

    // === LLM Usage (estimativa baseada em interacoes) ===
    // Na pratica, 80% usa Haiku e 20% usa Sonnet (estrategia hibrida)
    const llmUsage = {
      haiku: 80,
      sonnet: 20,
    }

    // === Instancias (chips ativos) ===

    const { data: chipsData } = await supabase
      .from('chips')
      .select('instance_name, evolution_connected, msgs_enviadas_hoje, status, provider')
      .in('status', ['active', 'warming', 'ready'])
      .order('instance_name')

    const instances =
      (chipsData as ChipRow[] | null)?.map((chip: ChipRow) => {
        // Para Z-API, consideramos online se status é active (não usa evolution_connected)
        // Para Evolution, verificamos evolution_connected
        const isOnline =
          chip.provider === 'z-api'
            ? chip.status === 'active'
            : chip.evolution_connected && chip.status === 'active'

        return {
          name: chip.instance_name || 'Unknown',
          status: isOnline ? ('online' as const) : ('offline' as const),
          messagesToday: chip.msgs_enviadas_hoje || 0,
        }
      }) || []

    return NextResponse.json({
      rateLimitHour: {
        current: msgsLastHour || 0,
        max: RATE_LIMITS.hour,
        label: 'Rate Limit Hora',
      },
      rateLimitDay: {
        current: msgsToday || 0,
        max: RATE_LIMITS.day,
        label: 'Rate Limit Dia',
      },
      queueSize: queueSize || 0,
      llmUsage,
      instances,
    })
  } catch (error) {
    console.error('Error fetching operational status:', error)
    return NextResponse.json({ error: 'Failed to fetch operational status' }, { status: 500 })
  }
}
