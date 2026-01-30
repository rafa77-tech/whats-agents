/**
 * API: GET /api/dashboard/funnel/[stage]
 *
 * Retorna lista de medicos em uma etapa especifica do funil.
 * Alinhado com a lógica do funil principal (baseado em interacoes).
 *
 * Query params:
 * - page: numero da pagina (default: 1)
 * - pageSize: itens por pagina (default: 10)
 * - search: filtro por nome
 * - period: periodo de dados (default: "7d")
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

const stageLabels: Record<string, string> = {
  enviadas: 'Enviadas',
  entregues: 'Entregues',
  respostas: 'Respostas',
  interesse: 'Interesse',
  fechadas: 'Fechadas',
}

interface ConversationRow {
  id: string
  cliente_id: string
  updated_at: string
  stage: string | null
  status: string | null
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
    const startDateISO = startDate.toISOString()

    let conversationIds: string[] = []
    let total = 0

    // Etapas baseadas em interacoes (enviadas, entregues, respostas)
    if (['enviadas', 'entregues', 'respostas'].includes(stage)) {
      // Buscar conversation_ids com mensagens de saída no período
      const { data: saidaData } = await supabase
        .from('interacoes')
        .select('conversation_id')
        .eq('tipo', 'saida')
        .not('conversation_id', 'is', null)
        .gte('created_at', startDateISO)

      const enviadasSet = new Set((saidaData || []).map((r) => r.conversation_id).filter(Boolean))

      if (stage === 'enviadas' || stage === 'entregues') {
        // Enviadas e Entregues: todas as conversas com saída
        conversationIds = Array.from(enviadasSet)
      } else if (stage === 'respostas') {
        // Respostas: conversas com saída que também tiveram entrada
        const { data: entradaData } = await supabase
          .from('interacoes')
          .select('conversation_id')
          .eq('tipo', 'entrada')
          .not('conversation_id', 'is', null)
          .gte('created_at', startDateISO)

        const entradaSet = new Set(
          (entradaData || []).map((r) => r.conversation_id).filter(Boolean)
        )

        // Interseção: conversas que enviaram E receberam
        conversationIds = Array.from(enviadasSet).filter((id) => entradaSet.has(id))
      }

      total = conversationIds.length
    }

    // Buscar detalhes das conversas
    let items: Array<{
      id: string
      medicoId: string
      nome: string
      telefone: string
      especialidade: string
      ultimoContato: string
      chipName: string
      conversaId: string
      chatwootUrl?: string
    }> = []

    if (['enviadas', 'entregues', 'respostas'].includes(stage) && conversationIds.length > 0) {
      // Paginar os IDs
      const paginatedIds = conversationIds.slice(offset, offset + pageSize)

      if (paginatedIds.length > 0) {
        const { data: conversas } = await supabase
          .from('conversations')
          .select(
            `
            id,
            cliente_id,
            updated_at,
            stage,
            status,
            clientes (
              primeiro_nome,
              sobrenome,
              telefone,
              especialidade
            )
          `
          )
          .in('id', paginatedIds)
          .order('updated_at', { ascending: false })

        const typedConversas = (conversas as unknown as ConversationRow[] | null) || []

        // Filtrar por nome se busca fornecida
        let filteredConversas = typedConversas
        if (search) {
          const searchLower = search.toLowerCase()
          filteredConversas = typedConversas.filter((c) => {
            const nome =
              `${c.clientes?.primeiro_nome || ''} ${c.clientes?.sobrenome || ''}`.toLowerCase()
            return nome.includes(searchLower)
          })
        }

        const chatwootBaseUrl = process.env.CHATWOOT_URL
        items = filteredConversas.map((c) => {
          const item: (typeof items)[number] = {
            id: c.id,
            medicoId: c.cliente_id || '',
            nome: c.clientes
              ? `${c.clientes.primeiro_nome || ''} ${c.clientes.sobrenome || ''}`.trim() ||
                'Desconhecido'
              : 'Desconhecido',
            telefone: c.clientes?.telefone || '',
            especialidade: c.clientes?.especialidade || 'Nao informada',
            ultimoContato: c.updated_at,
            chipName: 'Julia',
            conversaId: c.id,
          }
          if (chatwootBaseUrl) {
            item.chatwootUrl = `${chatwootBaseUrl}/conversations/${c.id}`
          }
          return item
        })
      }
    } else if (['interesse', 'fechadas'].includes(stage)) {
      // Etapas baseadas em conversations (interesse, fechadas)
      let query = supabase
        .from('conversations')
        .select(
          `
          id,
          cliente_id,
          updated_at,
          stage,
          status,
          clientes (
            primeiro_nome,
            sobrenome,
            telefone,
            especialidade
          )
        `,
          { count: 'exact' }
        )
        .order('updated_at', { ascending: false })

      if (stage === 'interesse') {
        query = query
          .in('stage', ['interesse', 'negociacao', 'qualificado', 'proposta'])
          .gte('updated_at', startDateISO)
      } else if (stage === 'fechadas') {
        query = query
          .in('status', ['fechado', 'completed', 'convertido'])
          .gte('completed_at', startDateISO)
      }

      query = query.range(offset, offset + pageSize - 1)

      const { data: conversas, count, error } = await query
      if (error) throw error

      total = count || 0
      const typedConversas = (conversas as unknown as ConversationRow[] | null) || []

      // Filtrar por nome se busca fornecida
      let filteredConversas = typedConversas
      if (search) {
        const searchLower = search.toLowerCase()
        filteredConversas = typedConversas.filter((c) => {
          const nome =
            `${c.clientes?.primeiro_nome || ''} ${c.clientes?.sobrenome || ''}`.toLowerCase()
          return nome.includes(searchLower)
        })
      }

      const chatwootBaseUrl = process.env.CHATWOOT_URL
      items = filteredConversas.map((c) => {
        const item: (typeof items)[number] = {
          id: c.id,
          medicoId: c.cliente_id || '',
          nome: c.clientes
            ? `${c.clientes.primeiro_nome || ''} ${c.clientes.sobrenome || ''}`.trim() ||
              'Desconhecido'
            : 'Desconhecido',
          telefone: c.clientes?.telefone || '',
          especialidade: c.clientes?.especialidade || 'Nao informada',
          ultimoContato: c.updated_at,
          chipName: 'Julia',
          conversaId: c.id,
        }
        if (chatwootBaseUrl) {
          item.chatwootUrl = `${chatwootBaseUrl}/conversations/${c.id}`
        }
        return item
      })
    }

    return NextResponse.json({
      stage,
      stageLabel: stageLabels[stage],
      items,
      total,
      page,
      pageSize,
    })
  } catch (error) {
    console.error('Error fetching funnel drilldown:', error)
    return NextResponse.json({ error: 'Failed to fetch drilldown data' }, { status: 500 })
  }
}
