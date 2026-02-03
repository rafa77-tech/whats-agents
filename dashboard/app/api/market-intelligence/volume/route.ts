/**
 * API Market Intelligence Volume - Sprint 46
 *
 * Retorna dados de volume ao longo do tempo para graficos de tendencia.
 */

import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'
import { createClient } from '@/lib/supabase/server'
import type { VolumeDataPoint, VolumeResponse } from '@/types/market-intelligence'

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
    granularity: z.enum(['day', 'week']).default('day'),
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

function agruparPorSemana(dados: VolumeDataPoint[]): VolumeDataPoint[] {
  const semanas: Map<string, VolumeDataPoint> = new Map()

  dados.forEach((d) => {
    const date = new Date(d.data)
    // Calcular inicio da semana (domingo)
    const dayOfWeek = date.getDay()
    const startOfWeek = new Date(date)
    startOfWeek.setDate(date.getDate() - dayOfWeek)
    const weekKey = startOfWeek.toISOString().split('T')[0] as string

    const existing = semanas.get(weekKey) || {
      data: weekKey,
      mensagens: 0,
      ofertas: 0,
      vagasExtraidas: 0,
      vagasImportadas: 0,
    }

    semanas.set(weekKey, {
      data: weekKey,
      mensagens: existing.mensagens + d.mensagens,
      ofertas: existing.ofertas + d.ofertas,
      vagasExtraidas: existing.vagasExtraidas + d.vagasExtraidas,
      vagasImportadas: existing.vagasImportadas + d.vagasImportadas,
    })
  })

  return Array.from(semanas.values()).sort((a, b) => a.data.localeCompare(b.data))
}

// =============================================================================
// QUERIES
// =============================================================================

type SupabaseClient = Awaited<ReturnType<typeof createClient>>

async function buscarDadosVolume(
  supabase: SupabaseClient,
  inicio: Date,
  fim: Date
): Promise<VolumeDataPoint[]> {
  const inicioStr = inicio.toISOString().split('T')[0] as string
  const fimStr = fim.toISOString().split('T')[0] as string

  // Tentar buscar da view materializada primeiro
  const { data: mvData, error: mvError } = await supabase
    .from('mv_pipeline_metrics')
    .select('*')
    .gte('data', inicioStr)
    .lte('data', fimStr)
    .order('data', { ascending: true })

  if (!mvError && mvData && mvData.length > 0) {
    return mvData.map((row) => ({
      data: row.data,
      mensagens: row.mensagens_total || 0,
      ofertas: row.mensagens_eh_oferta || 0,
      vagasExtraidas: row.vagas_extraidas || 0,
      vagasImportadas: row.vagas_importadas || 0,
    }))
  }

  // Fallback: buscar diretamente das tabelas
  return await buscarDadosDireto(supabase, inicio, fim)
}

async function buscarDadosDireto(
  supabase: SupabaseClient,
  inicio: Date,
  fim: Date
): Promise<VolumeDataPoint[]> {
  const inicioStr = inicio.toISOString()
  const fimStr = fim.toISOString()

  // Buscar mensagens agrupadas por dia
  const { data: mensagens, error: errMsg } = await supabase
    .from('mensagens_grupo')
    .select('created_at, eh_oferta')
    .gte('created_at', inicioStr)
    .lte('created_at', fimStr)

  if (errMsg) {
    throw new Error(`Erro ao buscar mensagens: ${errMsg.message}`)
  }

  // Buscar vagas agrupadas por dia
  const { data: vagas, error: errVagas } = await supabase
    .from('vagas_grupo')
    .select('created_at, status')
    .gte('created_at', inicioStr)
    .lte('created_at', fimStr)

  if (errVagas) {
    throw new Error(`Erro ao buscar vagas: ${errVagas.message}`)
  }

  // Agregar por dia
  const dadosPorDia: Map<string, VolumeDataPoint> = new Map()

  // Gerar todos os dias no range
  const current = new Date(inicio)
  while (current <= fim) {
    const dataStr = current.toISOString().split('T')[0] as string
    dadosPorDia.set(dataStr, {
      data: dataStr,
      mensagens: 0,
      ofertas: 0,
      vagasExtraidas: 0,
      vagasImportadas: 0,
    })
    current.setDate(current.getDate() + 1)
  }

  // Agregar mensagens
  ;(mensagens || []).forEach((m) => {
    const dataStr = new Date(m.created_at).toISOString().split('T')[0] as string
    const dia = dadosPorDia.get(dataStr)
    if (dia) {
      dia.mensagens++
      if (m.eh_oferta) {
        dia.ofertas++
      }
    }
  })

  // Agregar vagas
  ;(vagas || []).forEach((v) => {
    const dataStr = new Date(v.created_at).toISOString().split('T')[0] as string
    const dia = dadosPorDia.get(dataStr)
    if (dia) {
      dia.vagasExtraidas++
      if (v.status === 'importada') {
        dia.vagasImportadas++
      }
    }
  })

  return Array.from(dadosPorDia.values()).sort((a, b) => a.data.localeCompare(b.data))
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

    const { period, startDate, endDate, granularity } = validacao.data

    // 2. Calcular periodo
    const { inicio, fim, dias } = calcularPeriodo(period, startDate, endDate)

    // 3. Buscar dados
    const supabase = await createClient()
    let dados = await buscarDadosVolume(supabase, inicio, fim)

    // 4. Aplicar granularidade
    if (granularity === 'week') {
      dados = agruparPorSemana(dados)
    }

    // 5. Calcular totais e medias
    const totais = dados.reduce(
      (acc, d) => ({
        mensagens: acc.mensagens + d.mensagens,
        ofertas: acc.ofertas + d.ofertas,
        vagasExtraidas: acc.vagasExtraidas + d.vagasExtraidas,
        vagasImportadas: acc.vagasImportadas + d.vagasImportadas,
      }),
      { mensagens: 0, ofertas: 0, vagasExtraidas: 0, vagasImportadas: 0 }
    )

    const divisor = dados.length || 1
    const medias = {
      mensagensPorDia: Math.round((totais.mensagens / divisor) * 10) / 10,
      ofertasPorDia: Math.round((totais.ofertas / divisor) * 10) / 10,
      vagasExtraidasPorDia: Math.round((totais.vagasExtraidas / divisor) * 10) / 10,
      vagasImportadasPorDia: Math.round((totais.vagasImportadas / divisor) * 10) / 10,
    }

    // 6. Montar response
    const inicioStr = inicio.toISOString().split('T')[0] as string
    const fimStr = fim.toISOString().split('T')[0] as string

    const response: VolumeResponse = {
      periodo: {
        inicio: inicioStr,
        fim: fimStr,
        dias,
      },
      dados,
      totais,
      medias,
      updatedAt: new Date().toISOString(),
    }

    return NextResponse.json(response)
  } catch (error) {
    console.error('[Market Intelligence Volume] Erro:', error)

    return NextResponse.json(
      {
        error: 'INTERNAL_ERROR',
        message: 'Erro interno ao processar requisicao',
      },
      { status: 500 }
    )
  }
}
