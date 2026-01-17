/**
 * API: GET /api/dashboard/funnel/[stage]
 *
 * Retorna lista de medicos em uma etapa especifica do funil.
 *
 * Query params:
 * - page: numero da pagina (default: 1)
 * - pageSize: itens por pagina (default: 10)
 * - search: filtro por nome
 * - period: periodo de dados (default: "7d")
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

const stageLabels: Record<string, string> = {
  enviadas: 'Enviadas',
  entregues: 'Entregues',
  respostas: 'Respostas',
  interesse: 'Interesse',
  fechadas: 'Fechadas',
}

// Mapeia etapas do funil para filtros de status/stage
const stageFilters: Record<string, { status?: string[]; stage?: string[] }> = {
  enviadas: {}, // Todas as conversas do periodo
  entregues: {}, // Conversas com mensagem entregue
  respostas: {
    stage: ['respondido', 'interesse', 'negociacao', 'qualificado', 'proposta'],
  },
  interesse: {
    stage: ['interesse', 'negociacao', 'qualificado', 'proposta'],
  },
  fechadas: {
    status: ['fechado', 'completed', 'convertido'],
  },
}

interface ConversationRow {
  id: string
  cliente_id: string
  updated_at: string
  clientes: {
    primeiro_nome: string | null
    sobrenome: string | null
    telefone: string | null
    especialidade: string | null
  } | null
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ stage: string }> }
) {
  try {
    const supabase = await createClient()
    const { stage } = await params
    const searchParams = request.nextUrl.searchParams

    const page = parseInt(searchParams.get('page') || '1')
    const pageSize = parseInt(searchParams.get('pageSize') || '10')
    const search = searchParams.get('search') || ''
    const period = searchParams.get('period') || '7d'

    const offset = (page - 1) * pageSize

    // Validar etapa
    if (!stageLabels[stage]) {
      return NextResponse.json({ error: 'Invalid stage' }, { status: 400 })
    }

    // Calcular data inicio do periodo
    const periodMap: Record<string, number> = {
      '7d': 7,
      '14d': 14,
      '30d': 30,
    }
    const days = periodMap[period] || 7
    const startDate = new Date()
    startDate.setDate(startDate.getDate() - days)

    // Query principal com relacionamentos
    let query = supabase
      .from('conversations')
      .select(
        `
        id,
        cliente_id,
        updated_at,
        clientes (
          primeiro_nome,
          sobrenome,
          telefone,
          especialidade
        )
      `,
        { count: 'exact' }
      )
      .gte('updated_at', startDate.toISOString())
      .order('updated_at', { ascending: false })

    // Aplicar filtros de status/stage baseado na etapa
    const filters = stageFilters[stage]
    if (filters?.status) {
      query = query.in('status', filters.status)
    }
    if (filters?.stage) {
      query = query.in('stage', filters.stage)
    }

    // Paginacao
    query = query.range(offset, offset + pageSize - 1)

    const { data: conversas, count, error } = await query

    if (error) throw error

    const typedConversas = (conversas as unknown as ConversationRow[] | null) || []

    // Filtrar por nome se busca fornecida (client-side pois ilike em relacionamento e complexo)
    let filteredConversas = typedConversas
    if (search) {
      const searchLower = search.toLowerCase()
      filteredConversas = typedConversas.filter((c) => {
        const nome =
          `${c.clientes?.primeiro_nome || ''} ${c.clientes?.sobrenome || ''}`.toLowerCase()
        return nome.includes(searchLower)
      })
    }

    // Formatar resposta
    const chatwootUrl = process.env.CHATWOOT_URL
    const items = filteredConversas.map((c) => ({
      id: c.id,
      medicoId: c.cliente_id || '',
      nome: c.clientes
        ? `${c.clientes.primeiro_nome || ''} ${c.clientes.sobrenome || ''}`.trim() || 'Desconhecido'
        : 'Desconhecido',
      telefone: c.clientes?.telefone || '',
      especialidade: c.clientes?.especialidade || 'Nao informada',
      ultimoContato: c.updated_at,
      chipName: 'Julia', // Simplificado - poderia buscar do chip_id
      conversaId: c.id,
      chatwootUrl: chatwootUrl ? `${chatwootUrl}/conversations/${c.id}` : undefined,
    }))

    return NextResponse.json({
      stage,
      stageLabel: stageLabels[stage],
      items,
      total: count || 0,
      page,
      pageSize,
    })
  } catch (error) {
    console.error('Error fetching funnel drilldown:', error)
    return NextResponse.json({ error: 'Failed to fetch drilldown data' }, { status: 500 })
  }
}
