/**
 * API: GET /api/dashboard/chips/scheduler/stats
 *
 * Estatísticas do scheduler de warmup.
 * TODO: Implementar quando tabela de scheduling existir.
 */

import { NextRequest, NextResponse } from 'next/server'
import type { SchedulerStats } from '@/types/chips'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const dateParam = searchParams.get('date')
  const today = new Date().toISOString().split('T')[0] as string
  const date: string = dateParam ?? today

  // Mock data - será substituído por dados reais quando scheduler for implementado
  const stats: SchedulerStats = {
    date,
    totalPlanned: 24,
    totalExecuted: 18,
    totalFailed: 2,
    totalCancelled: 0,
    byType: {
      CONVERSA_PAR: { planned: 6, executed: 5, failed: 1 },
      MARCAR_LIDO: { planned: 8, executed: 7, failed: 0 },
      ENTRAR_GRUPO: { planned: 2, executed: 1, failed: 1 },
      ENVIAR_MIDIA: { planned: 4, executed: 3, failed: 0 },
      MENSAGEM_GRUPO: { planned: 3, executed: 2, failed: 0 },
      ATUALIZAR_PERFIL: { planned: 1, executed: 0, failed: 0 },
    },
  }

  return NextResponse.json(stats)
}
