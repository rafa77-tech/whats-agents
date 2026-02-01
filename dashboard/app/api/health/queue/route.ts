/**
 * API: GET /api/health/queue
 * Sprint 43 - Health Center
 *
 * Retorna estatisticas da fila de mensagens.
 */

import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    const supabase = await createClient()

    // Use RPC function to get queue stats
    const { data, error } = await supabase.rpc('get_fila_stats')

    if (error) {
      console.error('Erro ao buscar stats da fila:', error)
      throw error
    }

    const stats = data as {
      pendentes: number
      processando: number
      travadas: number
      errosUltimaHora: number
      msgMaisAntiga: string | null
    } | null

    // Calculate messages per hour (from last hour)
    const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000).toISOString()
    const { count: processedLastHour } = await supabase
      .from('fila_mensagens')
      .select('*', { count: 'exact', head: true })
      .eq('status', 'enviada')
      .gte('updated_at', oneHourAgo)

    // Calculate average processing time
    const { data: avgData } = await supabase.rpc('get_avg_processing_time')

    return NextResponse.json({
      queue: {
        pendentes: stats?.pendentes || 0,
        processando: stats?.processando || 0,
        travadas: stats?.travadas || 0,
        errosUltimaHora: stats?.errosUltimaHora || 0,
        msgMaisAntiga: stats?.msgMaisAntiga,
        processadasPorHora: processedLastHour || 0,
        tempoMedioMs: (avgData as number) || null,
      },
      timestamp: new Date().toISOString(),
    })
  } catch (error) {
    console.error('Erro ao buscar stats da fila:', error)
    return NextResponse.json({
      queue: {
        pendentes: 0,
        processando: 0,
        travadas: 0,
        errosUltimaHora: 0,
        msgMaisAntiga: null,
        processadasPorHora: 0,
        tempoMedioMs: null,
      },
      error: true,
      timestamp: new Date().toISOString(),
    })
  }
}
