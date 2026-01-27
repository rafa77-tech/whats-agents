/**
 * API: GET /api/dashboard/chips/[id]/interactions
 *
 * Retorna interacoes recentes de um chip.
 * Sprint 39 - Chip Interactions
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import type { ChipInteractionsResponse, ChipInteraction, InteractionType } from '@/types/chips'

export const dynamic = 'force-dynamic'

interface InteractionRow {
  id: string
  tipo: string
  created_at: string
  metadata: Record<string, unknown> | null
  destinatario: string | null
}

function mapInteractionType(tipo: string): InteractionType {
  const typeMap: Record<string, InteractionType> = {
    msg_enviada: 'conversa_individual',
    msg_recebida: 'conversa_individual',
    warmup_msg: 'warmup_par',
    status_criado: 'midia_enviada',
    erro: 'erro',
    entrada_grupo: 'entrada_grupo',
    mensagem_grupo: 'mensagem_grupo',
  }
  return typeMap[tipo] || 'conversa_individual'
}

function getInteractionDescription(tipo: string, metadata: Record<string, unknown> | null): string {
  switch (tipo) {
    case 'msg_enviada':
      return 'Mensagem enviada'
    case 'msg_recebida':
      return 'Mensagem recebida'
    case 'warmup_msg':
      return 'Mensagem de warmup enviada'
    case 'status_criado':
      return 'Status/midia criado'
    case 'erro':
      return (metadata?.error as string) || 'Erro na operacao'
    case 'entrada_grupo':
      return 'Entrou em grupo'
    case 'mensagem_grupo':
      return 'Mensagem enviada em grupo'
    default:
      return `Interacao: ${tipo}`
  }
}

function isSuccessfulInteraction(tipo: string): boolean {
  return tipo !== 'erro'
}

export async function GET(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const supabase = await createClient()
    const { id: chipId } = await params
    const searchParams = request.nextUrl.searchParams

    const limit = parseInt(searchParams.get('limit') || '20', 10)
    const offset = parseInt(searchParams.get('offset') || '0', 10)
    const typeFilter = searchParams.get('type')

    // Verificar se chip existe
    const { data: chip, error: chipError } = await supabase
      .from('chips')
      .select('id')
      .eq('id', chipId)
      .single()

    if (chipError || !chip) {
      return NextResponse.json({ error: 'Chip not found' }, { status: 404 })
    }

    // Buscar total de interacoes
    let countQuery = supabase
      .from('chip_interactions')
      .select('id', { count: 'exact', head: true })
      .eq('chip_id', chipId)

    if (typeFilter) {
      countQuery = countQuery.eq('tipo', typeFilter)
    }

    const { count: totalCount } = await countQuery

    // Buscar interacoes com paginacao
    let query = supabase
      .from('chip_interactions')
      .select('id, tipo, created_at, metadata, destinatario')
      .eq('chip_id', chipId)
      .order('created_at', { ascending: false })
      .range(offset, offset + limit - 1)

    if (typeFilter) {
      query = query.eq('tipo', typeFilter)
    }

    const { data: interactions, error: interactionsError } = await query

    if (interactionsError) {
      console.error('Error fetching interactions:', interactionsError)
      return NextResponse.json({ error: 'Failed to fetch interactions' }, { status: 500 })
    }

    const rows = (interactions as InteractionRow[] | null) || []
    const total = totalCount ?? 0

    const formattedInteractions: ChipInteraction[] = rows.map((row) => {
      const interaction: ChipInteraction = {
        id: row.id,
        type: mapInteractionType(row.tipo),
        timestamp: row.created_at,
        description: getInteractionDescription(row.tipo, row.metadata),
        success: isSuccessfulInteraction(row.tipo),
      }
      if (row.metadata) {
        interaction.metadata = row.metadata
      }
      return interaction
    })

    const response: ChipInteractionsResponse = {
      interactions: formattedInteractions,
      total,
      hasMore: offset + limit < total,
    }

    return NextResponse.json(response)
  } catch (error) {
    console.error('Error fetching chip interactions:', error)
    return NextResponse.json({ error: 'Failed to fetch chip interactions' }, { status: 500 })
  }
}
