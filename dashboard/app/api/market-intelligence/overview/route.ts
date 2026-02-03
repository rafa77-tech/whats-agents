/**
 * API Market Intelligence Overview - Sprint 46
 *
 * Retorna KPIs e metricas de overview do modulo de Market Intelligence.
 */

import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'
import { createClient } from '@/lib/supabase/server'
import { type MarketOverviewResponse, type AnalyticsPeriod } from '@/types/market-intelligence'

// =============================================================================
// VALIDACAO
// =============================================================================

const querySchema = z
  .object({
    period: z.enum(['24h', '7d', '30d', '90d', 'custom']).default('24h'),
    startDate: z
      .string()
      .regex(/^\d{4}-\d{2}-\d{2}$/)
      .optional(),
    endDate: z
      .string()
      .regex(/^\d{4}-\d{2}-\d{2}$/)
      .optional(),
  })
  .refine(
    (data) => {
      if (data.period === 'custom') {
        return data.startDate && data.endDate
      }
      return true
    },
    {
      message: 'startDate e endDate sao obrigatorios quando period=custom',
    }
  )

// =============================================================================
// HELPERS
// =============================================================================

/**
 * Calcula as datas de inicio e fim baseado no periodo
 */
function calcularPeriodo(
  period: AnalyticsPeriod,
  startDate?: string,
  endDate?: string
): { inicio: Date; fim: Date; dias: number } {
  const fim = endDate ? new Date(endDate) : new Date()
  fim.setHours(23, 59, 59, 999)

  let inicio: Date

  switch (period) {
    case '24h':
      inicio = new Date()
      inicio.setHours(inicio.getHours() - 24)
      break
    case '7d':
      inicio = new Date(fim)
      inicio.setDate(inicio.getDate() - 6)
      break
    case '30d':
      inicio = new Date(fim)
      inicio.setDate(inicio.getDate() - 29)
      break
    case '90d':
      inicio = new Date(fim)
      inicio.setDate(inicio.getDate() - 89)
      break
    case 'custom':
      inicio = new Date(startDate!)
      break
    default:
      inicio = new Date()
      inicio.setHours(inicio.getHours() - 24)
  }

  // Para 24h, não resetar horas
  if (period !== '24h') {
    inicio.setHours(0, 0, 0, 0)
  }

  const dias = Math.ceil((fim.getTime() - inicio.getTime()) / (1000 * 60 * 60 * 24)) || 1

  return { inicio, fim, dias }
}

/**
 * Calcula variacao percentual entre dois valores
 */
function calcularVariacao(
  atual: number,
  anterior: number
): {
  variacao: number | null
  variacaoTipo: 'up' | 'down' | 'stable' | null
} {
  if (anterior === 0) {
    return { variacao: null, variacaoTipo: null }
  }

  const variacao = ((atual - anterior) / anterior) * 100

  let variacaoTipo: 'up' | 'down' | 'stable'
  if (variacao > 1) {
    variacaoTipo = 'up'
  } else if (variacao < -1) {
    variacaoTipo = 'down'
  } else {
    variacaoTipo = 'stable'
  }

  return { variacao: Math.round(variacao * 10) / 10, variacaoTipo }
}

/**
 * Formata valor monetario (centavos para reais)
 */
function formatarValor(centavos: number): string {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 0,
  }).format(centavos / 100)
}

// =============================================================================
// QUERIES
// =============================================================================

interface MetricasPeriodo {
  gruposAtivos: number
  mensagensTotal: number
  mensagensComOferta: number
  vagasExtraidas: number
  vagasImportadas: number
  valorMedio: number | null
  tendenciaGrupos: number[]
  tendenciaVagas: number[]
  tendenciaTaxa: number[]
  tendenciaValor: number[]
}

type SupabaseClient = Awaited<ReturnType<typeof createClient>>

async function buscarMetricasPeriodo(
  supabase: SupabaseClient,
  inicio: Date,
  fim: Date
): Promise<MetricasPeriodo> {
  // Query principal - metricas agregadas
  const { data: metricas, error: erroMetricas } = await supabase
    .from('market_intelligence_daily')
    .select('*')
    .gte('data', inicio.toISOString().split('T')[0])
    .lte('data', fim.toISOString().split('T')[0])
    .order('data', { ascending: true })

  if (erroMetricas) {
    throw new Error(`Erro ao buscar metricas: ${erroMetricas.message}`)
  }

  // Se nao houver dados na tabela de snapshots, buscar diretamente
  if (!metricas || metricas.length === 0) {
    return await buscarMetricasDireto(supabase, inicio, fim)
  }

  // Agregar metricas
  const totais = metricas.reduce(
    (acc, m) => ({
      gruposAtivos: Math.max(acc.gruposAtivos, m.grupos_ativos || 0),
      mensagensTotal: acc.mensagensTotal + (m.mensagens_total || 0),
      mensagensComOferta: acc.mensagensComOferta + (m.mensagens_com_oferta || 0),
      vagasExtraidas: acc.vagasExtraidas + (m.vagas_extraidas || 0),
      vagasImportadas: acc.vagasImportadas + (m.vagas_importadas || 0),
      valoresPlantao: [...acc.valoresPlantao, m.valor_medio_plantao].filter(Boolean),
    }),
    {
      gruposAtivos: 0,
      mensagensTotal: 0,
      mensagensComOferta: 0,
      vagasExtraidas: 0,
      vagasImportadas: 0,
      valoresPlantao: [] as number[],
    }
  )

  // Calcular valor medio
  const valorMedio =
    totais.valoresPlantao.length > 0
      ? Math.round(
          totais.valoresPlantao.reduce((a: number, b: number) => a + b, 0) /
            totais.valoresPlantao.length
        )
      : null

  // Extrair tendencias (ultimos 5 pontos)
  const ultimosN = metricas.slice(-5)
  const tendenciaGrupos = ultimosN.map((m) => m.grupos_ativos || 0)
  const tendenciaVagas = ultimosN.map((m) => m.vagas_importadas || 0)
  const tendenciaTaxa = ultimosN.map((m) =>
    m.taxa_importacao ? Math.round(m.taxa_importacao * 100) : 0
  )
  const tendenciaValor = ultimosN.map((m) => m.valor_medio_plantao || 0)

  return {
    gruposAtivos: totais.gruposAtivos,
    mensagensTotal: totais.mensagensTotal,
    mensagensComOferta: totais.mensagensComOferta,
    vagasExtraidas: totais.vagasExtraidas,
    vagasImportadas: totais.vagasImportadas,
    valorMedio,
    tendenciaGrupos,
    tendenciaVagas,
    tendenciaTaxa,
    tendenciaValor,
  }
}

async function buscarMetricasDireto(
  supabase: SupabaseClient,
  inicio: Date,
  fim: Date
): Promise<MetricasPeriodo> {
  const inicioStr = inicio.toISOString()
  const fimStr = fim.toISOString()

  // Buscar de tabelas originais
  const [gruposRes, mensagensRes, vagasRes] = await Promise.all([
    // Grupos ativos
    supabase.from('grupos_whatsapp').select('id').eq('ativo', true),

    // Mensagens
    supabase
      .from('mensagens_grupo')
      .select('id, eh_oferta')
      .gte('created_at', inicioStr)
      .lte('created_at', fimStr),

    // Vagas
    supabase
      .from('vagas_grupo')
      .select('id, status, valor')
      .gte('created_at', inicioStr)
      .lte('created_at', fimStr),
  ])

  const gruposAtivos = gruposRes.data?.length || 0
  const mensagens = mensagensRes.data || []
  const vagas = vagasRes.data || []

  const mensagensTotal = mensagens.length
  const mensagensComOferta = mensagens.filter((m) => m.eh_oferta).length
  const vagasExtraidas = vagas.length
  const vagasImportadas = vagas.filter((v) => v.status === 'importada').length

  const valoresValidos = vagas.filter((v) => v.valor && v.valor > 0).map((v) => v.valor as number)
  const valorMedio =
    valoresValidos.length > 0
      ? Math.round(valoresValidos.reduce((a, b) => a + b, 0) / valoresValidos.length)
      : null

  return {
    gruposAtivos,
    mensagensTotal,
    mensagensComOferta,
    vagasExtraidas,
    vagasImportadas,
    valorMedio,
    tendenciaGrupos: [gruposAtivos],
    tendenciaVagas: [vagasImportadas],
    tendenciaTaxa: [vagasExtraidas > 0 ? Math.round((vagasImportadas / vagasExtraidas) * 100) : 0],
    tendenciaValor: [valorMedio || 0],
  }
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

    const { period, startDate, endDate } = validacao.data

    // 2. Calcular periodo
    const { inicio, fim, dias } = calcularPeriodo(period, startDate, endDate)

    // 3. Calcular periodo anterior (para variacao)
    const diasPeriodo = dias
    const inicioAnterior = new Date(inicio)
    inicioAnterior.setDate(inicioAnterior.getDate() - diasPeriodo)
    const fimAnterior = new Date(inicio)
    fimAnterior.setDate(fimAnterior.getDate() - 1)

    // 4. Buscar dados
    const supabase = await createClient()

    const [metricasAtuais, metricasAnteriores] = await Promise.all([
      buscarMetricasPeriodo(supabase, inicio, fim),
      buscarMetricasPeriodo(supabase, inicioAnterior, fimAnterior),
    ])

    // 5. Calcular KPIs
    const vagasPorDia = dias > 0 ? metricasAtuais.vagasImportadas / dias : 0
    const vagasPorDiaAnterior =
      diasPeriodo > 0 ? metricasAnteriores.vagasImportadas / diasPeriodo : 0

    const taxaConversao =
      metricasAtuais.vagasExtraidas > 0
        ? metricasAtuais.vagasImportadas / metricasAtuais.vagasExtraidas
        : 0
    const taxaConversaoAnterior =
      metricasAnteriores.vagasExtraidas > 0
        ? metricasAnteriores.vagasImportadas / metricasAnteriores.vagasExtraidas
        : 0

    // 6. Montar response
    const inicioStr = inicio.toISOString().split('T')[0] as string
    const fimStr = fim.toISOString().split('T')[0] as string

    const response: MarketOverviewResponse = {
      periodo: {
        inicio: inicioStr,
        fim: fimStr,
        dias,
      },
      kpis: {
        gruposAtivos: {
          valor: metricasAtuais.gruposAtivos,
          valorFormatado: String(metricasAtuais.gruposAtivos),
          ...calcularVariacao(metricasAtuais.gruposAtivos, metricasAnteriores.gruposAtivos),
          tendencia: metricasAtuais.tendenciaGrupos,
        },
        vagasPorDia: {
          valor: Math.round(vagasPorDia * 10) / 10,
          valorFormatado: `${(Math.round(vagasPorDia * 10) / 10).toFixed(1)}/dia`,
          ...calcularVariacao(vagasPorDia, vagasPorDiaAnterior),
          tendencia: metricasAtuais.tendenciaVagas,
        },
        taxaConversao: {
          valor: Math.round(taxaConversao * 1000) / 10,
          valorFormatado: `${(Math.round(taxaConversao * 1000) / 10).toFixed(1)}%`,
          ...calcularVariacao(taxaConversao, taxaConversaoAnterior),
          tendencia: metricasAtuais.tendenciaTaxa,
        },
        valorMedio: {
          valor: metricasAtuais.valorMedio || 0,
          valorFormatado: metricasAtuais.valorMedio
            ? formatarValor(metricasAtuais.valorMedio)
            : 'N/A',
          ...calcularVariacao(metricasAtuais.valorMedio || 0, metricasAnteriores.valorMedio || 0),
          tendencia: metricasAtuais.tendenciaValor,
        },
      },
      resumo: {
        totalMensagens: metricasAtuais.mensagensTotal,
        totalOfertas: metricasAtuais.mensagensComOferta,
        totalVagasExtraidas: metricasAtuais.vagasExtraidas,
        totalVagasImportadas: metricasAtuais.vagasImportadas,
      },
      updatedAt: new Date().toISOString(),
    }

    return NextResponse.json(response)
  } catch (error) {
    console.error('[Market Intelligence Overview] Erro:', error)

    return NextResponse.json(
      {
        error: 'INTERNAL_ERROR',
        message: 'Erro interno ao processar requisicao',
      },
      { status: 500 }
    )
  }
}
