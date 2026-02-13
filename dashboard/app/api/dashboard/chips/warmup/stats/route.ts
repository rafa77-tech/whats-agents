/**
 * API: GET /api/dashboard/chips/warmup/stats
 *
 * Estatísticas de warmup do banco de dados.
 * Renomeado de /scheduler/stats para /warmup/stats (Sprint 42).
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import type { SchedulerStats, ScheduledActivityType } from '@/types/chips'

export const dynamic = 'force-dynamic'

// Tipos de atividade conhecidos
const ACTIVITY_TYPES: ScheduledActivityType[] = [
  'CONVERSA_PAR',
  'MARCAR_LIDO',
  'ENTRAR_GRUPO',
  'ENVIAR_MIDIA',
  'MENSAGEM_GRUPO',
  'ATUALIZAR_PERFIL',
]

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const dateParam = searchParams.get('date')
    // Usar timezone de São Paulo para calcular "hoje"
    const today = new Date().toLocaleDateString('en-CA', { timeZone: 'America/Sao_Paulo' })
    const date: string = dateParam ?? today

    const supabase = await createClient()

    // Calcular range do dia
    const startOfDay = `${date}T00:00:00-03:00`
    const endOfDay = `${date}T23:59:59-03:00`

    // Query todas as atividades do dia
    const { data, error } = await supabase
      .from('warmup_schedule')
      .select('tipo, status')
      .gte('scheduled_for', startOfDay)
      .lte('scheduled_for', endOfDay)

    if (error) {
      console.error('Error fetching warmup stats:', error)
      throw error
    }

    // Inicializar contadores por tipo
    const byType: SchedulerStats['byType'] = {} as SchedulerStats['byType']
    ACTIVITY_TYPES.forEach((type) => {
      byType[type] = { planned: 0, executed: 0, failed: 0 }
    })

    // Contadores globais
    let totalPlanned = 0
    let totalExecuted = 0
    let totalFailed = 0
    let totalCancelled = 0

    // Processar dados
    ;(data || []).forEach((row) => {
      const tipo = (row.tipo as string).toUpperCase() as ScheduledActivityType
      const status = row.status as string

      // Incrementar por tipo (se conhecido)
      if (byType[tipo]) {
        byType[tipo].planned++
        if (status === 'executada') {
          byType[tipo].executed++
        } else if (status === 'falhou') {
          byType[tipo].failed++
        }
      }

      // Incrementar totais
      totalPlanned++
      if (status === 'executada') {
        totalExecuted++
      } else if (status === 'falhou') {
        totalFailed++
      } else if (status === 'cancelada') {
        totalCancelled++
      }
    })

    const stats: SchedulerStats = {
      date,
      totalPlanned,
      totalExecuted,
      totalFailed,
      totalCancelled,
      byType,
    }

    return NextResponse.json(stats)
  } catch (error) {
    console.error('Error in warmup stats:', error)
    return NextResponse.json({ error: 'Failed to fetch warmup stats' }, { status: 500 })
  }
}
