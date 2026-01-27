/**
 * API: GET /api/dashboard/chips/[id]/detail
 *
 * Retorna detalhes completos de um chip.
 * Sprint 39 - Chip Detail
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import type { ChipFullDetail, WarmupPhase, TrustLevelExtended } from '@/types/chips'
import type { ChipStatus } from '@/types/dashboard'

export const dynamic = 'force-dynamic'

interface ChipRow {
  id: string
  telefone: string
  instance_name: string | null
  status: string
  trust_score: number | null
  trust_level: string | null
  fase_warmup: string | null
  warming_day: number | null
  msgs_enviadas_hoje: number | null
  limite_dia: number | null
  taxa_resposta: number | null
  taxa_block: number | null
  taxa_delivery: number | null
  erros_ultimas_24h: number | null
  created_at: string
  updated_at: string | null
  last_activity_start: string | null
  msgs_enviadas_total: number | null
}

function getTrustLevel(score: number): TrustLevelExtended {
  if (score >= 80) return 'verde'
  if (score >= 60) return 'amarelo'
  if (score >= 40) return 'laranja'
  if (score >= 20) return 'vermelho'
  return 'critico'
}

function extractDDD(telefone: string): string {
  const cleaned = telefone.replace(/\D/g, '')
  if (cleaned.startsWith('55') && cleaned.length >= 4) {
    return cleaned.substring(2, 4)
  }
  return cleaned.substring(0, 2)
}

function getRegionByDDD(ddd: string): string {
  const regions: Record<string, string> = {
    '11': 'São Paulo - SP',
    '12': 'Vale do Paraíba - SP',
    '13': 'Baixada Santista - SP',
    '14': 'Bauru - SP',
    '15': 'Sorocaba - SP',
    '16': 'Ribeirão Preto - SP',
    '17': 'São José do Rio Preto - SP',
    '18': 'Presidente Prudente - SP',
    '19': 'Campinas - SP',
    '21': 'Rio de Janeiro - RJ',
    '22': 'Campos dos Goytacazes - RJ',
    '24': 'Volta Redonda - RJ',
    '27': 'Vitória - ES',
    '28': 'Cachoeiro de Itapemirim - ES',
    '31': 'Belo Horizonte - MG',
    '32': 'Juiz de Fora - MG',
    '33': 'Governador Valadares - MG',
    '34': 'Uberlândia - MG',
    '35': 'Poços de Caldas - MG',
    '37': 'Divinópolis - MG',
    '38': 'Montes Claros - MG',
  }
  return regions[ddd] || `DDD ${ddd}`
}

export async function GET(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const supabase = await createClient()
    const { id: chipId } = await params

    // Buscar chip
    const { data: chip, error: chipError } = await supabase
      .from('chips')
      .select('*')
      .eq('id', chipId)
      .single()

    if (chipError || !chip) {
      return NextResponse.json({ error: 'Chip not found' }, { status: 404 })
    }

    const typedChip = chip as ChipRow

    // Buscar contagem de alertas ativos
    const { count: alertCount } = await supabase
      .from('chip_alerts')
      .select('id', { count: 'exact', head: true })
      .eq('chip_id', chipId)
      .eq('resolved', false)

    // Buscar contagem de conversas
    const { count: conversationCount } = await supabase
      .from('conversations')
      .select('id', { count: 'exact', head: true })
      .eq('chip_id', chipId)

    // Buscar interacoes bidirecionais (chip_interactions com tipo msg_recebida)
    const { count: bidirectionalCount } = await supabase
      .from('chip_interactions')
      .select('id', { count: 'exact', head: true })
      .eq('chip_id', chipId)
      .eq('tipo', 'msg_recebida')

    const ddd = extractDDD(typedChip.telefone)
    const trustScore = typedChip.trust_score ?? 50
    const trustLevel = (typedChip.trust_level as TrustLevelExtended) || getTrustLevel(trustScore)

    const detail: ChipFullDetail = {
      id: typedChip.id,
      telefone: typedChip.telefone,
      status: (typedChip.status || 'inactive') as ChipStatus,
      trustScore,
      trustLevel,
      warmupPhase: (typedChip.fase_warmup as WarmupPhase) || null,
      messagesToday: typedChip.msgs_enviadas_hoje ?? 0,
      dailyLimit: typedChip.limite_dia ?? 100,
      responseRate: Number(((typedChip.taxa_resposta ?? 0) * 100).toFixed(1)),
      errorsLast24h: typedChip.erros_ultimas_24h ?? 0,
      hasActiveAlert: (alertCount ?? 0) > 0,
      createdAt: typedChip.created_at,
      updatedAt: typedChip.updated_at ?? typedChip.created_at,
      // Extended fields
      ddd,
      region: getRegionByDDD(ddd),
      instanceName: typedChip.instance_name ?? `Chip-${typedChip.id.slice(0, 4)}`,
      deliveryRate: Number(((typedChip.taxa_delivery ?? 0.95) * 100).toFixed(1)),
      blockRate: Number(((typedChip.taxa_block ?? 0) * 100).toFixed(1)),
      lastActivityAt: typedChip.last_activity_start,
      totalMessagesSent: typedChip.msgs_enviadas_total ?? 0,
      totalConversations: conversationCount ?? 0,
      totalBidirectional: bidirectionalCount ?? 0,
      groupsJoined: 0, // TODO: implementar quando houver tabela de grupos
      mediaTypesSent: ['text'], // TODO: implementar contagem real
    }

    // Add optional fields only when they have values
    if (typedChip.warming_day !== null && typedChip.warming_day !== undefined) {
      detail.warmingDay = typedChip.warming_day
    }

    return NextResponse.json(detail)
  } catch (error) {
    console.error('Error fetching chip detail:', error)
    return NextResponse.json({ error: 'Failed to fetch chip detail' }, { status: 500 })
  }
}
