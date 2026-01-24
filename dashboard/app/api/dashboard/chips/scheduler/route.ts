/**
 * API: GET /api/dashboard/chips/scheduler
 *
 * Lista atividades agendadas do warmup.
 * TODO: Implementar quando tabela de scheduling existir.
 */

import { NextRequest, NextResponse } from 'next/server'
import type { ScheduledActivity } from '@/types/chips'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const date = searchParams.get('date') || new Date().toISOString().split('T')[0]

  // Mock data - será substituído por dados reais quando scheduler for implementado
  const activities: ScheduledActivity[] = [
    {
      id: '1',
      chipId: 'chip-1',
      chipTelefone: '5511999999901',
      type: 'CONVERSA_PAR',
      scheduledAt: `${date}T09:00:00Z`,
      executedAt: `${date}T09:02:00Z`,
      status: 'executada',
    },
    {
      id: '2',
      chipId: 'chip-1',
      chipTelefone: '5511999999901',
      type: 'MARCAR_LIDO',
      scheduledAt: `${date}T10:00:00Z`,
      executedAt: `${date}T10:01:00Z`,
      status: 'executada',
    },
    {
      id: '3',
      chipId: 'chip-2',
      chipTelefone: '5511999999902',
      type: 'ENVIAR_MIDIA',
      scheduledAt: `${date}T11:00:00Z`,
      status: 'planejada',
    },
    {
      id: '4',
      chipId: 'chip-2',
      chipTelefone: '5511999999902',
      type: 'MENSAGEM_GRUPO',
      scheduledAt: `${date}T12:00:00Z`,
      status: 'planejada',
    },
  ]

  return NextResponse.json(activities)
}
