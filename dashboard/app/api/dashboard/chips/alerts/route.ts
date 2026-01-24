/**
 * API: GET /api/dashboard/chips/alerts
 *
 * Lista alertas do pool de chips com filtros e paginação.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import type { ChipAlertsListResponse, ChipAlert, ChipAlertSeverity } from '@/types/chips'

export const dynamic = 'force-dynamic'

interface AlertRow {
  id: string
  chip_id: string
  severity: string
  tipo: string
  message: string
  acao_tomada: string | null
  resolved: boolean | null
  resolved_at: string | null
  resolved_by: string | null
  created_at: string | null
  chips: {
    telefone: string
  } | null
}

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

export async function GET(request: NextRequest) {
  try {
    const supabase = await createClient()
    const searchParams = request.nextUrl.searchParams

    const page = parseInt(searchParams.get('page') || '1')
    const pageSize = parseInt(searchParams.get('pageSize') || '20')
    const severity = searchParams.get('severity')
    const type = searchParams.get('type')
    const chipId = searchParams.get('chipId')
    const resolved = searchParams.get('resolved')

    // Construir query
    let query = supabase
      .from('chip_alerts')
      .select('*, chips!inner(telefone)', { count: 'exact' })
      .order('created_at', { ascending: false })

    // Aplicar filtros
    if (severity) {
      query = query.eq('severity', severity)
    }
    if (type) {
      query = query.eq('tipo', type)
    }
    if (chipId) {
      query = query.eq('chip_id', chipId)
    }
    if (resolved !== null && resolved !== undefined) {
      query = query.eq('resolved', resolved === 'true')
    }

    // Paginação
    const from = (page - 1) * pageSize
    const to = from + pageSize - 1
    query = query.range(from, to)

    const { data: alerts, count, error } = await query

    if (error) throw error

    // Buscar contagem por severidade
    const { data: severityCounts } = await supabase
      .from('chip_alerts')
      .select('severity')
      .eq('resolved', false)

    const countBySeverity: Record<ChipAlertSeverity, number> = {
      critico: 0,
      alerta: 0,
      atencao: 0,
      info: 0,
    }

    severityCounts?.forEach((a) => {
      const sev = a.severity as ChipAlertSeverity
      if (sev in countBySeverity) {
        countBySeverity[sev]++
      }
    })

    // Mapear para formato do frontend
    const mappedAlerts: ChipAlert[] =
      (alerts as AlertRow[] | null)?.map((a) => {
        const alert: ChipAlert = {
          id: a.id,
          chipId: a.chip_id,
          chipTelefone: a.chips?.telefone || 'Desconhecido',
          type: a.tipo as ChipAlert['type'],
          severity: a.severity as ChipAlertSeverity,
          title: alertTitles[a.tipo] || a.tipo,
          message: a.message,
          createdAt: a.created_at || new Date().toISOString(),
        }
        if (a.acao_tomada) alert.recommendation = a.acao_tomada
        if (a.resolved_at) alert.resolvedAt = a.resolved_at
        if (a.resolved_by) alert.resolvedBy = a.resolved_by
        return alert
      }) || []

    const response: ChipAlertsListResponse = {
      alerts: mappedAlerts,
      total: count || 0,
      page,
      pageSize,
      hasMore: (count || 0) > page * pageSize,
      countBySeverity,
    }

    return NextResponse.json(response)
  } catch (error) {
    console.error('Error fetching alerts:', error)
    return NextResponse.json({ error: 'Failed to fetch alerts' }, { status: 500 })
  }
}
