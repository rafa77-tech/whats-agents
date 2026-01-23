import { NextResponse } from 'next/server'
import { shouldUseMock, mockSistemaConfig } from '@/lib/mock'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface RateLimitStats {
  msgs_hora: number
  limite_hora: number
  msgs_dia: number
  limite_dia: number
  horario_permitido: boolean
  hora_atual: string
  dia_semana: string
}

interface RateLimitResponse {
  rate_limit: RateLimitStats
  timestamp: string
}

/**
 * GET /api/sistema/config
 * Retorna configuracoes do sistema (rate limiting, horarios, etc)
 */
export async function GET() {
  // Return mock data for E2E tests
  if (shouldUseMock()) {
    return NextResponse.json({
      rate_limit: {
        msgs_por_hora: mockSistemaConfig.rate_limit.mensagens_por_hora,
        msgs_por_dia: mockSistemaConfig.rate_limit.mensagens_por_dia,
        intervalo_min: mockSistemaConfig.rate_limit.intervalo_minimo_segundos,
        intervalo_max: 180,
      },
      horario: {
        inicio: 8,
        fim: 20,
        dias: 'Segunda a Sexta',
      },
      uso_atual: {
        msgs_hora: 12,
        msgs_dia: 45,
        horario_permitido: true,
        hora_atual: new Date().toLocaleTimeString('pt-BR'),
      },
    })
  }

  try {
    // Buscar estatisticas de rate limit do backend (inclui limites configurados)
    const res = await fetch(`${API_URL}/health/rate-limit`, {
      headers: {
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
      cache: 'no-store',
    })

    if (!res.ok) {
      throw new Error(`Backend retornou ${res.status}`)
    }

    const data = (await res.json()) as RateLimitResponse
    const stats = data.rate_limit

    // Retornar config formatada para o frontend
    // Nota: intervalo e horarios sao config estatica do backend (config.py)
    // Se precisar mudar, alterar DatabaseConfig em app/core/config.py
    return NextResponse.json({
      rate_limit: {
        msgs_por_hora: stats.limite_hora,
        msgs_por_dia: stats.limite_dia,
        intervalo_min: 45, // DatabaseConfig.INTERVALO_MIN_SEGUNDOS
        intervalo_max: 180, // DatabaseConfig.INTERVALO_MAX_SEGUNDOS
      },
      horario: {
        inicio: 8, // DatabaseConfig.HORA_INICIO
        fim: 20, // DatabaseConfig.HORA_FIM
        dias: 'Segunda a Sexta',
      },
      uso_atual: {
        msgs_hora: stats.msgs_hora,
        msgs_dia: stats.msgs_dia,
        horario_permitido: stats.horario_permitido,
        hora_atual: stats.hora_atual,
      },
    })
  } catch (error) {
    console.error('Erro ao buscar config do sistema:', error)
    return NextResponse.json(
      { error: 'Erro ao buscar configuracoes. Backend indisponivel.' },
      { status: 503 }
    )
  }
}
