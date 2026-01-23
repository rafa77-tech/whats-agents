/**
 * API: GET /api/dashboard/status
 *
 * Retorna status da Julia, ultimo heartbeat e uptime 30d.
 */

import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

interface JuliaStatusRow {
  status: string
  created_at: string
}

export async function GET() {
  try {
    const supabase = await createClient()

    // Buscar ultimo status
    const { data: statusData, error: statusError } = await supabase
      .from('julia_status')
      .select('status, created_at')
      .order('created_at', { ascending: false })
      .limit(1)
      .single()

    if (statusError && statusError.code !== 'PGRST116') {
      // PGRST116 = no rows returned
      console.error('Error fetching julia_status:', statusError)
    }

    // Calcular uptime 30d
    const thirtyDaysAgo = new Date()
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)

    const { count: totalChecks, error: totalError } = await supabase
      .from('julia_status')
      .select('*', { count: 'exact', head: true })
      .gte('created_at', thirtyDaysAgo.toISOString())

    if (totalError) {
      console.error('Error counting total checks:', totalError)
    }

    const { count: successfulChecks, error: successError } = await supabase
      .from('julia_status')
      .select('*', { count: 'exact', head: true })
      .gte('created_at', thirtyDaysAgo.toISOString())
      .in('status', ['online', 'ativo'])

    if (successError) {
      console.error('Error counting successful checks:', successError)
    }

    const uptime =
      totalChecks && totalChecks > 0 ? ((successfulChecks || 0) / totalChecks) * 100 : 100

    // Verificar se online (heartbeat < 5 min)
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000)
    const typedStatusData = statusData as JuliaStatusRow | null

    const isOnline = typedStatusData?.created_at
      ? new Date(typedStatusData.created_at) > fiveMinutesAgo
      : false

    return NextResponse.json({
      juliaStatus: isOnline ? 'online' : 'offline',
      lastHeartbeat: typedStatusData?.created_at || null,
      uptime30d: Number(uptime.toFixed(1)),
    })
  } catch (error) {
    console.error('Error fetching dashboard status:', error)
    return NextResponse.json({ error: 'Failed to fetch status' }, { status: 500 })
  }
}
