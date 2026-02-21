/**
 * API: GET /api/dashboard/meta/budget
 * Sprint 71 — Budget status: spend vs limits (daily/weekly/monthly)
 */

import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

const DAILY_LIMIT = parseFloat(process.env.META_BUDGET_DIARIO_USD || '50')
const WEEKLY_LIMIT = parseFloat(process.env.META_BUDGET_SEMANAL_USD || '300')
const MONTHLY_LIMIT = parseFloat(process.env.META_BUDGET_MENSAL_USD || '1200')

function getStatus(percent: number): 'ok' | 'warning' | 'critical' | 'blocked' {
  if (percent >= 100) return 'blocked'
  if (percent >= 90) return 'critical'
  if (percent >= 80) return 'warning'
  return 'ok'
}

export async function GET() {
  try {
    const supabase = await createClient()
    const now = new Date()

    // Daily: today
    const dayStart = new Date(now)
    dayStart.setHours(0, 0, 0, 0)

    // Weekly: start of week (Monday)
    const weekStart = new Date(now)
    const dayOfWeek = weekStart.getDay()
    const diff = dayOfWeek === 0 ? 6 : dayOfWeek - 1
    weekStart.setDate(weekStart.getDate() - diff)
    weekStart.setHours(0, 0, 0, 0)

    // Monthly: start of month
    const monthStart = new Date(now.getFullYear(), now.getMonth(), 1)

    const [dailyRes, weeklyRes, monthlyRes] = await Promise.all([
      supabase
        .from('meta_conversation_costs')
        .select('cost_usd')
        .gte('created_at', dayStart.toISOString()),
      supabase
        .from('meta_conversation_costs')
        .select('cost_usd')
        .gte('created_at', weekStart.toISOString()),
      supabase
        .from('meta_conversation_costs')
        .select('cost_usd')
        .gte('created_at', monthStart.toISOString()),
    ])

    if (dailyRes.error) throw dailyRes.error
    if (weeklyRes.error) throw weeklyRes.error
    if (monthlyRes.error) throw monthlyRes.error

    const sumCosts = (rows: Array<{ cost_usd: unknown }>): number =>
      rows.reduce((sum, r) => sum + parseFloat(String(r.cost_usd || '0')), 0)

    const dailyUsed = sumCosts(dailyRes.data || [])
    const weeklyUsed = sumCosts(weeklyRes.data || [])
    const monthlyUsed = sumCosts(monthlyRes.data || [])

    const dailyPercent = DAILY_LIMIT > 0 ? (dailyUsed / DAILY_LIMIT) * 100 : 0
    const weeklyPercent = WEEKLY_LIMIT > 0 ? (weeklyUsed / WEEKLY_LIMIT) * 100 : 0
    const monthlyPercent = MONTHLY_LIMIT > 0 ? (monthlyUsed / MONTHLY_LIMIT) * 100 : 0

    const worstPercent = Math.max(dailyPercent, weeklyPercent, monthlyPercent)

    const budget = {
      daily_limit_usd: DAILY_LIMIT,
      daily_used_usd: Math.round(dailyUsed * 10000) / 10000,
      daily_percent: Math.round(dailyPercent * 10) / 10,
      weekly_limit_usd: WEEKLY_LIMIT,
      weekly_used_usd: Math.round(weeklyUsed * 10000) / 10000,
      weekly_percent: Math.round(weeklyPercent * 10) / 10,
      monthly_limit_usd: MONTHLY_LIMIT,
      monthly_used_usd: Math.round(monthlyUsed * 10000) / 10000,
      monthly_percent: Math.round(monthlyPercent * 10) / 10,
      status: getStatus(worstPercent),
    }

    return NextResponse.json({ status: 'ok', data: budget })
  } catch (error) {
    console.error('Error in /api/dashboard/meta/budget:', error)
    return NextResponse.json({ error: 'Failed to fetch budget status' }, { status: 500 })
  }
}
