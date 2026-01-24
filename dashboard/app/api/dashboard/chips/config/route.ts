/**
 * API: GET/PUT /api/dashboard/chips/config
 *
 * Configurações do pool de chips.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import type { PoolConfig } from '@/types/chips'

export const dynamic = 'force-dynamic'

interface PoolConfigRow {
  id: string
  producao_min: number | null
  producao_max: number | null
  warmup_buffer: number | null
  warmup_days: number | null
  ready_min: number | null
  trust_min_for_ready: number | null
  trust_degraded_threshold: number | null
  trust_critical_threshold: number | null
  auto_provision: boolean | null
  default_ddd: number | null
  limite_prospeccao_hora: number | null
  limite_followup_hora: number | null
  limite_resposta_hora: number | null
  updated_at: string | null
}

function rowToConfig(row: PoolConfigRow | null): PoolConfig {
  return {
    maxChipsActive: row?.producao_max || 10,
    maxChipsWarming: row?.warmup_buffer || 5,
    minChipsReady: row?.ready_min || 2,
    maxMsgsPerHour: row?.limite_prospeccao_hora || 20,
    maxMsgsPerDay: row?.limite_prospeccao_hora ? row.limite_prospeccao_hora * 10 : 100,
    minIntervalSeconds: 45,
    autoPromoteEnabled: row?.auto_provision || false,
    autoDemoteEnabled: true,
    minTrustForPromotion: row?.trust_min_for_ready || 70,
    alertThresholds: {
      trustDropWarning: row?.trust_degraded_threshold || 60,
      trustDropCritical: row?.trust_critical_threshold || 30,
      errorRateWarning: 10,
      errorRateCritical: 25,
    },
    operatingHours: {
      start: '08:00',
      end: '20:00',
    },
    operatingDays: [1, 2, 3, 4, 5], // Seg-Sex
  }
}

export async function GET() {
  try {
    const supabase = await createClient()

    const { data, error } = await supabase.from('pool_config').select('*').limit(1).single()

    if (error && error.code !== 'PGRST116') {
      // PGRST116 = no rows returned
      throw error
    }

    const config = rowToConfig(data as PoolConfigRow | null)
    return NextResponse.json(config)
  } catch (error) {
    console.error('Error fetching pool config:', error)
    // Return defaults on error
    return NextResponse.json(rowToConfig(null))
  }
}

export async function PUT(request: NextRequest) {
  try {
    const supabase = await createClient()
    const body: Partial<PoolConfig> = await request.json()

    // Map frontend config to database columns
    const updates: Record<string, unknown> = {
      updated_at: new Date().toISOString(),
      updated_by: 'dashboard_user',
    }

    if (body.maxChipsActive !== undefined) updates.producao_max = body.maxChipsActive
    if (body.maxChipsWarming !== undefined) updates.warmup_buffer = body.maxChipsWarming
    if (body.minChipsReady !== undefined) updates.ready_min = body.minChipsReady
    if (body.maxMsgsPerHour !== undefined) updates.limite_prospeccao_hora = body.maxMsgsPerHour
    if (body.autoPromoteEnabled !== undefined) updates.auto_provision = body.autoPromoteEnabled
    if (body.minTrustForPromotion !== undefined)
      updates.trust_min_for_ready = body.minTrustForPromotion
    if (body.alertThresholds?.trustDropWarning !== undefined)
      updates.trust_degraded_threshold = body.alertThresholds.trustDropWarning
    if (body.alertThresholds?.trustDropCritical !== undefined)
      updates.trust_critical_threshold = body.alertThresholds.trustDropCritical

    // Check if config exists
    const { data: existing } = await supabase.from('pool_config').select('id').limit(1).single()

    if (existing) {
      const { error } = await supabase.from('pool_config').update(updates).eq('id', existing.id)
      if (error) throw error
    } else {
      const { error } = await supabase.from('pool_config').insert(updates)
      if (error) throw error
    }

    // Return updated config
    const { data: updated } = await supabase.from('pool_config').select('*').limit(1).single()

    return NextResponse.json(rowToConfig(updated as PoolConfigRow | null))
  } catch (error) {
    console.error('Error updating pool config:', error)
    return NextResponse.json({ error: 'Failed to update config' }, { status: 500 })
  }
}
