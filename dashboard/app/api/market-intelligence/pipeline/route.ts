/**
 * API Market Intelligence Pipeline - Sprint 46
 *
 * Retorna metricas do funil de processamento do pipeline de grupos.
 */

import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'
import { createClient } from '@/lib/supabase/server'
import type {
  PipelineResponse,
  PipelineEtapa,
  PipelineConversoes,
  PipelinePerdas,
} from '@/types/market-intelligence'

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

function calcularPeriodo(
  period: string,
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

  if (period !== '24h') {
    inicio.setHours(0, 0, 0, 0)
  }
  const dias = Math.ceil((fim.getTime() - inicio.getTime()) / (1000 * 60 * 60 * 24)) || 1

  return { inicio, fim, dias }
}

function calcularPercentual(valor: number, base: number): number {
  if (base === 0) return 0
  const percentual = Math.round((valor / base) * 1000) / 10
  // Cap at 100% to prevent display issues
  return Math.min(percentual, 100)
}

function calcularTaxaConversao(valorFinal: number, valorInicial: number): number {
  if (valorInicial === 0) return 0
  return Math.round((valorFinal / valorInicial) * 1000) / 10
}

// =============================================================================
// QUERIES
// =============================================================================

interface MetricasPipeline {
  mensagensTotal: number
  mensagensPassouHeuristica: number
  mensagensEhOferta: number
  vagasExtraidas: number
  vagasDadosOk: number
  vagasImportadas: number
  vagasDuplicadas: number
  vagasDescartadas: number
  vagasRevisao: number
  confiancaClassificacaoMedia: number | null
  confiancaExtracaoMedia: number | null
}

type SupabaseClient = Awaited<ReturnType<typeof createClient>>

async function buscarMetricasPipeline(
  supabase: SupabaseClient,
  inicio: Date,
  fim: Date
): Promise<MetricasPipeline> {
  const inicioStr = inicio.toISOString().split('T')[0] as string
  const fimStr = fim.toISOString().split('T')[0] as string

  // Tentar buscar da view materializada primeiro
  const { data: mvData, error: mvError } = await supabase
    .from('mv_pipeline_metrics')
    .select('*')
    .gte('data', inicioStr)
    .lte('data', fimStr)

  if (!mvError && mvData && mvData.length > 0) {
    // Agregar dados da view materializada
    const agregado = mvData.reduce(
      (acc, row) => ({
        mensagensTotal: acc.mensagensTotal + (row.mensagens_total || 0),
        mensagensProcessadas: acc.mensagensProcessadas + (row.mensagens_processadas || 0),
        mensagensPassouHeuristica:
          acc.mensagensPassouHeuristica + (row.mensagens_passou_heuristica || 0),
        mensagensEhOferta: acc.mensagensEhOferta + (row.mensagens_eh_oferta || 0),
        vagasExtraidas: acc.vagasExtraidas + (row.vagas_extraidas || 0),
        vagasDadosOk: acc.vagasDadosOk + (row.vagas_dados_ok || 0),
        vagasDuplicadas: acc.vagasDuplicadas + (row.vagas_duplicadas || 0),
        vagasImportadas: acc.vagasImportadas + (row.vagas_importadas || 0),
        vagasRevisao: acc.vagasRevisao + (row.vagas_revisao || 0),
        vagasDescartadas: acc.vagasDescartadas + (row.vagas_descartadas || 0),
        somaConfiancaClass: acc.somaConfiancaClass + (row.confianca_classificacao_media || 0),
        somaConfiancaExtr: acc.somaConfiancaExtr + (row.confianca_extracao_media || 0),
        countConfianca: acc.countConfianca + (row.confianca_classificacao_media ? 1 : 0),
      }),
      {
        mensagensTotal: 0,
        mensagensProcessadas: 0,
        mensagensPassouHeuristica: 0,
        mensagensEhOferta: 0,
        vagasExtraidas: 0,
        vagasDadosOk: 0,
        vagasDuplicadas: 0,
        vagasImportadas: 0,
        vagasRevisao: 0,
        vagasDescartadas: 0,
        somaConfiancaClass: 0,
        somaConfiancaExtr: 0,
        countConfianca: 0,
      }
    )

    return {
      mensagensTotal: agregado.mensagensTotal,
      mensagensPassouHeuristica: agregado.mensagensPassouHeuristica,
      mensagensEhOferta: agregado.mensagensEhOferta,
      vagasExtraidas: agregado.vagasExtraidas,
      vagasDadosOk: agregado.vagasDadosOk,
      vagasImportadas: agregado.vagasImportadas,
      vagasDuplicadas: agregado.vagasDuplicadas,
      vagasDescartadas: agregado.vagasDescartadas,
      vagasRevisao: agregado.vagasRevisao,
      confiancaClassificacaoMedia:
        agregado.countConfianca > 0 ? agregado.somaConfiancaClass / agregado.countConfianca : null,
      confiancaExtracaoMedia:
        agregado.countConfianca > 0 ? agregado.somaConfiancaExtr / agregado.countConfianca : null,
    }
  }

  // Fallback: buscar diretamente das tabelas
  return await buscarMetricasDireto(supabase, inicio, fim)
}

async function buscarMetricasDireto(
  supabase: SupabaseClient,
  inicio: Date,
  fim: Date
): Promise<MetricasPipeline> {
  const inicioStr = inicio.toISOString()
  const fimStr = fim.toISOString()

  // Buscar mensagens
  const { data: mensagens, error: errMsg } = await supabase
    .from('mensagens_grupo')
    .select('id, passou_heuristica, eh_oferta, confianca_classificacao')
    .gte('created_at', inicioStr)
    .lte('created_at', fimStr)

  if (errMsg) {
    throw new Error(`Erro ao buscar mensagens: ${errMsg.message}`)
  }

  // Buscar vagas
  const { data: vagas, error: errVagas } = await supabase
    .from('vagas_grupo')
    .select('id, status, dados_minimos_ok, eh_duplicada, confianca_geral')
    .gte('created_at', inicioStr)
    .lte('created_at', fimStr)

  if (errVagas) {
    throw new Error(`Erro ao buscar vagas: ${errVagas.message}`)
  }

  const msgArray = mensagens || []
  const vagasArray = vagas || []

  const mensagensTotal = msgArray.length
  const mensagensPassouHeuristica = msgArray.filter((m) => m.passou_heuristica).length
  const mensagensEhOferta = msgArray.filter((m) => m.eh_oferta).length

  const vagasExtraidas = vagasArray.length
  const vagasDadosOk = vagasArray.filter((v) => v.dados_minimos_ok).length
  const vagasImportadas = vagasArray.filter((v) => v.status === 'importada').length
  const vagasDuplicadas = vagasArray.filter((v) => v.eh_duplicada).length
  const vagasDescartadas = vagasArray.filter((v) => v.status === 'descartada').length
  const vagasRevisao = vagasArray.filter((v) => v.status === 'revisao').length

  const confiancasClass = msgArray
    .filter((m) => m.confianca_classificacao != null)
    .map((m) => m.confianca_classificacao as number)
  const confiancasExtr = vagasArray
    .filter((v) => v.confianca_geral != null)
    .map((v) => v.confianca_geral as number)

  return {
    mensagensTotal,
    mensagensPassouHeuristica,
    mensagensEhOferta,
    vagasExtraidas,
    vagasDadosOk,
    vagasImportadas,
    vagasDuplicadas,
    vagasDescartadas,
    vagasRevisao,
    confiancaClassificacaoMedia:
      confiancasClass.length > 0
        ? confiancasClass.reduce((a: number, b: number) => a + b, 0) / confiancasClass.length
        : null,
    confiancaExtracaoMedia:
      confiancasExtr.length > 0
        ? confiancasExtr.reduce((a: number, b: number) => a + b, 0) / confiancasExtr.length
        : null,
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

    // 3. Buscar dados
    const supabase = await createClient()
    const metricas = await buscarMetricasPipeline(supabase, inicio, fim)

    // 4. Construir etapas do funil
    // O funil tem duas partes: mensagens e vagas
    // Mensagens: mensagensTotal -> passouHeuristica -> ehOferta
    // Vagas: vagasExtraidas -> dadosOk -> importadas
    // Cada parte usa sua própria base para percentuais
    const baseMensagens = metricas.mensagensTotal
    const baseVagas = metricas.vagasExtraidas

    const etapas: PipelineEtapa[] = [
      {
        id: 'mensagens',
        nome: 'Mensagens Recebidas',
        valor: metricas.mensagensTotal,
        percentual: 100,
      },
      {
        id: 'heuristica',
        nome: 'Passou Heuristica',
        valor: metricas.mensagensPassouHeuristica,
        percentual: calcularPercentual(metricas.mensagensPassouHeuristica, baseMensagens),
      },
      {
        id: 'ofertas',
        nome: 'Classificadas como Oferta',
        valor: metricas.mensagensEhOferta,
        percentual: calcularPercentual(metricas.mensagensEhOferta, baseMensagens),
      },
      {
        id: 'extraidas',
        nome: 'Vagas Extraidas',
        valor: metricas.vagasExtraidas,
        // Usa 100% como base própria (início da segunda parte do funil)
        percentual: baseVagas > 0 ? 100 : 0,
      },
      {
        id: 'validadas',
        nome: 'Dados Minimos OK',
        valor: metricas.vagasDadosOk,
        percentual: calcularPercentual(metricas.vagasDadosOk, baseVagas),
      },
      {
        id: 'importadas',
        nome: 'Vagas Importadas',
        valor: metricas.vagasImportadas,
        percentual: calcularPercentual(metricas.vagasImportadas, baseVagas),
      },
    ]

    // 5. Calcular taxas de conversao
    const conversoes: PipelineConversoes = {
      mensagemParaOferta: calcularTaxaConversao(
        metricas.mensagensEhOferta,
        metricas.mensagensTotal
      ),
      ofertaParaExtracao: calcularTaxaConversao(
        metricas.vagasExtraidas,
        metricas.mensagensEhOferta
      ),
      extracaoParaImportacao: calcularTaxaConversao(
        metricas.vagasImportadas,
        metricas.vagasExtraidas
      ),
      totalPipeline: calcularTaxaConversao(metricas.vagasImportadas, metricas.mensagensTotal),
    }

    // 6. Calcular perdas
    const perdas: PipelinePerdas = {
      duplicadas: metricas.vagasDuplicadas,
      descartadas: metricas.vagasDescartadas,
      revisao: metricas.vagasRevisao,
      semDadosMinimos: metricas.vagasExtraidas - metricas.vagasDadosOk,
    }

    // 7. Montar response
    const inicioStr = inicio.toISOString().split('T')[0] as string
    const fimStr = fim.toISOString().split('T')[0] as string

    const response: PipelineResponse = {
      periodo: {
        inicio: inicioStr,
        fim: fimStr,
        dias,
      },
      funil: {
        etapas,
        conversoes,
      },
      perdas,
      qualidade: {
        confiancaClassificacaoMedia: metricas.confiancaClassificacaoMedia
          ? Math.round(metricas.confiancaClassificacaoMedia * 100) / 100
          : null,
        confiancaExtracaoMedia: metricas.confiancaExtracaoMedia
          ? Math.round(metricas.confiancaExtracaoMedia * 100) / 100
          : null,
      },
      updatedAt: new Date().toISOString(),
    }

    return NextResponse.json(response)
  } catch (error) {
    console.error('[Market Intelligence Pipeline] Erro:', error)

    return NextResponse.json(
      {
        error: 'INTERNAL_ERROR',
        message: 'Erro interno ao processar requisicao',
      },
      { status: 500 }
    )
  }
}
