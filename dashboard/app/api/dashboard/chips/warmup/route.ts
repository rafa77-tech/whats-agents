/**
 * API: GET /api/dashboard/chips/warmup
 *
 * Lista atividades de warmup do banco de dados.
 * Renomeado de /scheduler para /warmup (Sprint 42).
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import type { ScheduledActivity } from '@/types/chips'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    // Usar timezone de São Paulo para calcular "hoje"
    const todayInSP = new Date().toLocaleDateString('en-CA', { timeZone: 'America/Sao_Paulo' })
    const date = searchParams.get('date') || todayInSP
    const chipId = searchParams.get('chipId')
    const limit = parseInt(searchParams.get('limit') || '50', 10)

    const supabase = await createClient()

    // Calcular range do dia
    const startOfDay = `${date}T00:00:00-03:00`
    const endOfDay = `${date}T23:59:59-03:00`

    // Query base
    let query = supabase
      .from('warmup_schedule')
      .select(
        `
        id,
        chip_id,
        tipo,
        scheduled_for,
        status,
        executed_at,
        error_message,
        chips!inner(telefone)
      `
      )
      .gte('scheduled_for', startOfDay)
      .lte('scheduled_for', endOfDay)
      .order('scheduled_for', { ascending: true })
      .limit(limit)

    // Filtro por chip
    if (chipId) {
      query = query.eq('chip_id', chipId)
    }

    const { data, error } = await query

    if (error) {
      console.error('Error fetching warmup activities:', error)
      throw error
    }

    // Mapear para o formato esperado pelo frontend
    const activities: ScheduledActivity[] = (data || []).map((row) => {
      // chips vem como objeto do join
      const chips = row.chips as unknown as { telefone: string } | null
      return {
        id: row.id,
        chipId: row.chip_id,
        chipTelefone: chips?.telefone || '',
        type: row.tipo as ScheduledActivity['type'],
        scheduledAt: row.scheduled_for,
        executedAt: row.executed_at || undefined,
        status: row.status as ScheduledActivity['status'],
        errorMessage: row.error_message || undefined,
      }
    })

    return NextResponse.json(activities)
  } catch (error) {
    console.error('Error in warmup activities:', error)
    return NextResponse.json({ error: 'Failed to fetch warmup activities' }, { status: 500 })
  }
}
