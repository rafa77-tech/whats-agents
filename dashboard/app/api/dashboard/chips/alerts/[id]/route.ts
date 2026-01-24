/**
 * API: GET /api/dashboard/chips/alerts/[id]
 *
 * Retorna detalhes de um alerta específico.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import type { ChipAlert, ChipAlertSeverity } from '@/types/chips'

export const dynamic = 'force-dynamic'

const alertTitles: Record<string, string> = {
  TRUST_CAINDO: 'Trust Score em queda',
  TAXA_BLOCK_ALTA: 'Taxa de bloqueio elevada',
  ERROS_FREQUENTES: 'Erros frequentes detectados',
  DELIVERY_BAIXO: 'Taxa de delivery baixa',
  RESPOSTA_BAIXA: 'Taxa de resposta baixa',
  DESCONEXAO: 'Chip desconectado',
  LIMITE_PROXIMO: 'Próximo do limite diário',
  FASE_ESTAGNADA: 'Fase de warmup estagnada',
  QUALIDADE_META: 'Qualidade abaixo da meta',
  COMPORTAMENTO_ANOMALO: 'Comportamento anômalo detectado',
}

export async function GET(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const supabase = await createClient()
    const { id } = await params

    const { data: alert, error } = await supabase
      .from('chip_alerts')
      .select('*, chips!inner(telefone)')
      .eq('id', id)
      .single()

    if (error || !alert) {
      return NextResponse.json({ error: 'Alert not found' }, { status: 404 })
    }

    const mapped: ChipAlert = {
      id: alert.id,
      chipId: alert.chip_id,
      chipTelefone: alert.chips?.telefone || 'Desconhecido',
      type: alert.tipo as ChipAlert['type'],
      severity: alert.severity as ChipAlertSeverity,
      title: alertTitles[alert.tipo] || alert.tipo,
      message: alert.message,
      recommendation: alert.acao_tomada || undefined,
      createdAt: alert.created_at,
      resolvedAt: alert.resolved_at || undefined,
      resolvedBy: alert.resolved_by || undefined,
    }

    return NextResponse.json(mapped)
  } catch (error) {
    console.error('Error fetching alert:', error)
    return NextResponse.json({ error: 'Failed to fetch alert' }, { status: 500 })
  }
}
