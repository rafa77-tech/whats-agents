/**
 * API Market Intelligence Groups Ranking - Sprint 46
 *
 * Retorna ranking de grupos por performance (vagas importadas, score de qualidade).
 */

import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'
import { createClient } from '@/lib/supabase/server'
import type { GrupoRanking, GroupsRankingResponse } from '@/types/market-intelligence'

// =============================================================================
// VALIDACAO
// =============================================================================

const querySchema = z.object({
  limit: z.coerce.number().min(1).max(100).default(20),
  offset: z.coerce.number().min(0).default(0),
  sortBy: z.enum(['score', 'vagas', 'mensagens', 'valor']).default('vagas'),
  order: z.enum(['asc', 'desc']).default('desc'),
  apenasAtivos: z.coerce.boolean().default(true),
})

// =============================================================================
// QUERIES
// =============================================================================

type SupabaseClient = Awaited<ReturnType<typeof createClient>>

async function buscarGruposRanking(
  supabase: SupabaseClient,
  params: {
    limit: number
    offset: number
    sortBy: string
    order: 'asc' | 'desc'
    apenasAtivos: boolean
  }
): Promise<{ grupos: GrupoRanking[]; total: number }> {
  // Tentar buscar da view materializada primeiro
  const { data: mvData, error: mvError } = await supabase
    .from('mv_grupos_ranking')
    .select('*', { count: 'exact' })

  if (!mvError && mvData && mvData.length > 0) {
    // Filtrar e ordenar
    let grupos = mvData.map((row) => ({
      grupoId: row.grupo_id,
      grupoNome: row.grupo_nome || 'Grupo sem nome',
      grupoTipo: row.grupo_tipo,
      grupoRegiao: row.grupo_regiao,
      grupoAtivo: row.grupo_ativo ?? true,
      mensagens30d: row.mensagens_30d || 0,
      ofertas30d: row.ofertas_30d || 0,
      vagasExtraidas30d: row.vagas_extraidas_30d || 0,
      vagasImportadas30d: row.vagas_importadas_30d || 0,
      confiancaMedia30d: row.confianca_media_30d,
      valorMedio30d: row.valor_medio_30d,
      scoreQualidade: row.score_qualidade || 0,
      ultimaMensagemEm: row.ultima_mensagem_em,
      ultimaVagaEm: row.ultima_vaga_em,
      calculatedAt: row.calculated_at || new Date().toISOString(),
    })) as GrupoRanking[]

    if (params.apenasAtivos) {
      grupos = grupos.filter((g) => g.grupoAtivo)
    }

    // Ordenar
    grupos.sort((a, b) => {
      let aVal: number
      let bVal: number

      switch (params.sortBy) {
        case 'score':
          aVal = a.scoreQualidade
          bVal = b.scoreQualidade
          break
        case 'vagas':
          aVal = a.vagasImportadas30d
          bVal = b.vagasImportadas30d
          break
        case 'mensagens':
          aVal = a.mensagens30d
          bVal = b.mensagens30d
          break
        case 'valor':
          aVal = a.valorMedio30d || 0
          bVal = b.valorMedio30d || 0
          break
        default:
          aVal = a.vagasImportadas30d
          bVal = b.vagasImportadas30d
      }

      return params.order === 'desc' ? bVal - aVal : aVal - bVal
    })

    const total = grupos.length
    const paginados = grupos.slice(params.offset, params.offset + params.limit)

    return { grupos: paginados, total }
  }

  // Fallback: buscar diretamente das tabelas
  return await buscarGruposDireto(supabase, params)
}

async function buscarGruposDireto(
  supabase: SupabaseClient,
  params: {
    limit: number
    offset: number
    sortBy: string
    order: 'asc' | 'desc'
    apenasAtivos: boolean
  }
): Promise<{ grupos: GrupoRanking[]; total: number }> {
  // Calcular data de 30 dias atras
  const data30d = new Date()
  data30d.setDate(data30d.getDate() - 30)
  const data30dStr = data30d.toISOString()

  // Buscar grupos
  let gruposQuery = supabase.from('grupos_whatsapp').select('*', { count: 'exact' })

  if (params.apenasAtivos) {
    gruposQuery = gruposQuery.eq('ativo', true)
  }

  const { data: gruposData, error: gruposError } = await gruposQuery

  if (gruposError) {
    throw new Error(`Erro ao buscar grupos: ${gruposError.message}`)
  }

  if (!gruposData || gruposData.length === 0) {
    return { grupos: [], total: 0 }
  }

  // Buscar metricas de mensagens e vagas para os ultimos 30 dias
  const grupoIds = gruposData.map((g) => g.id)

  const [mensagensRes, vagasRes] = await Promise.all([
    supabase
      .from('mensagens_grupo')
      .select('grupo_id, eh_oferta, created_at')
      .in('grupo_id', grupoIds)
      .gte('created_at', data30dStr),
    supabase
      .from('vagas_grupo')
      .select('grupo_id, status, valor, created_at')
      .in('grupo_id', grupoIds)
      .gte('created_at', data30dStr),
  ])

  // Agregar metricas por grupo
  const metricasPorGrupo = new Map<
    string,
    {
      mensagens: number
      ofertas: number
      vagasExtraidas: number
      vagasImportadas: number
      valores: number[]
      ultimaMensagem: string | null
      ultimaVaga: string | null
    }
  >()

  grupoIds.forEach((id) =>
    metricasPorGrupo.set(id, {
      mensagens: 0,
      ofertas: 0,
      vagasExtraidas: 0,
      vagasImportadas: 0,
      valores: [],
      ultimaMensagem: null,
      ultimaVaga: null,
    })
  )

  // Processar mensagens
  ;(mensagensRes.data || []).forEach((m) => {
    const metricas = metricasPorGrupo.get(m.grupo_id)
    if (metricas) {
      metricas.mensagens++
      if (m.eh_oferta) metricas.ofertas++
      if (!metricas.ultimaMensagem || m.created_at > metricas.ultimaMensagem) {
        metricas.ultimaMensagem = m.created_at
      }
    }
  })

  // Processar vagas
  ;(vagasRes.data || []).forEach((v) => {
    const metricas = metricasPorGrupo.get(v.grupo_id)
    if (metricas) {
      metricas.vagasExtraidas++
      if (v.status === 'importada') {
        metricas.vagasImportadas++
        if (v.valor && v.valor > 0) metricas.valores.push(v.valor)
      }
      if (!metricas.ultimaVaga || v.created_at > metricas.ultimaVaga) {
        metricas.ultimaVaga = v.created_at
      }
    }
  })

  // Construir ranking
  let grupos: GrupoRanking[] = gruposData.map((g) => {
    const metricas = metricasPorGrupo.get(g.id) || {
      mensagens: 0,
      ofertas: 0,
      vagasExtraidas: 0,
      vagasImportadas: 0,
      valores: [],
      ultimaMensagem: null,
      ultimaVaga: null,
    }

    const valorMedio =
      metricas.valores.length > 0
        ? Math.round(metricas.valores.reduce((a, b) => a + b, 0) / metricas.valores.length)
        : null

    // Calcular score simplificado (0-100)
    // Score baseado em: vagas importadas (40%), taxa conversao (30%), recencia (30%)
    const taxaConversao =
      metricas.vagasExtraidas > 0 ? metricas.vagasImportadas / metricas.vagasExtraidas : 0
    const diasDesdeUltimaVaga = metricas.ultimaVaga
      ? Math.floor((Date.now() - new Date(metricas.ultimaVaga).getTime()) / (1000 * 60 * 60 * 24))
      : 999
    const recencia = Math.max(0, 100 - diasDesdeUltimaVaga * 3)

    const scoreVagas = Math.min(100, metricas.vagasImportadas * 2)
    const scoreConversao = Math.round(taxaConversao * 100)
    const score = Math.round(scoreVagas * 0.4 + scoreConversao * 0.3 + recencia * 0.3)

    return {
      grupoId: g.id,
      grupoNome: g.nome || 'Grupo sem nome',
      grupoTipo: g.tipo || null,
      grupoRegiao: g.regiao || null,
      grupoAtivo: g.ativo ?? true,
      mensagens30d: metricas.mensagens,
      ofertas30d: metricas.ofertas,
      vagasExtraidas30d: metricas.vagasExtraidas,
      vagasImportadas30d: metricas.vagasImportadas,
      confiancaMedia30d: null,
      valorMedio30d: valorMedio,
      scoreQualidade: score,
      ultimaMensagemEm: metricas.ultimaMensagem,
      ultimaVagaEm: metricas.ultimaVaga,
      calculatedAt: new Date().toISOString(),
    }
  })

  // Ordenar
  grupos.sort((a, b) => {
    let aVal: number
    let bVal: number

    switch (params.sortBy) {
      case 'score':
        aVal = a.scoreQualidade
        bVal = b.scoreQualidade
        break
      case 'vagas':
        aVal = a.vagasImportadas30d
        bVal = b.vagasImportadas30d
        break
      case 'mensagens':
        aVal = a.mensagens30d
        bVal = b.mensagens30d
        break
      case 'valor':
        aVal = a.valorMedio30d || 0
        bVal = b.valorMedio30d || 0
        break
      default:
        aVal = a.vagasImportadas30d
        bVal = b.vagasImportadas30d
    }

    return params.order === 'desc' ? bVal - aVal : aVal - bVal
  })

  const total = grupos.length
  const paginados = grupos.slice(params.offset, params.offset + params.limit)

  return { grupos: paginados, total }
}

// =============================================================================
// HANDLER
// =============================================================================

export async function GET(request: NextRequest) {
  try {
    // 1. Validar parametros
    const searchParams = Object.fromEntries(request.nextUrl.searchParams)
    const validacao = querySchema.safeParse(searchParams)

    if (!validacao.success) {
      return NextResponse.json(
        {
          error: 'VALIDATION_ERROR',
          message: 'Parametros invalidos',
          details: validacao.error.flatten().fieldErrors,
        },
        { status: 400 }
      )
    }

    const { limit, offset, sortBy, order, apenasAtivos } = validacao.data

    // 2. Buscar dados
    const supabase = await createClient()
    const { grupos, total } = await buscarGruposRanking(supabase, {
      limit,
      offset,
      sortBy,
      order,
      apenasAtivos,
    })

    // 3. Montar response
    const response: GroupsRankingResponse = {
      grupos,
      total,
      limit,
      offset,
      updatedAt: new Date().toISOString(),
    }

    return NextResponse.json(response)
  } catch (error) {
    console.error('[Market Intelligence Groups Ranking] Erro:', error)

    return NextResponse.json(
      {
        error: 'INTERNAL_ERROR',
        message: 'Erro interno ao processar requisicao',
      },
      { status: 500 }
    )
  }
}
