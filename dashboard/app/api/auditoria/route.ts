/**
 * API: GET /api/auditoria
 *
 * Lista logs de auditoria do banco de dados.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const page = parseInt(searchParams.get('page') || '1')
    const perPage = parseInt(searchParams.get('per_page') || '50')
    const action = searchParams.get('action')
    const actorEmail = searchParams.get('actor_email')
    const fromDate = searchParams.get('from_date')
    const toDate = searchParams.get('to_date')

    const supabase = createAdminClient()

    // Build query
    let query = supabase
      .from('audit_log')
      .select(
        `
        id,
        action,
        user_email,
        details,
        created_at
      `,
        { count: 'exact' }
      )

    // Apply filters
    if (action) {
      query = query.eq('action', action)
    }
    if (actorEmail) {
      query = query.ilike('user_email', `%${actorEmail}%`)
    }
    if (fromDate) {
      query = query.gte('created_at', fromDate)
    }
    if (toDate) {
      query = query.lte('created_at', toDate)
    }

    // Pagination
    const from = (page - 1) * perPage
    const to = from + perPage - 1

    query = query.order('created_at', { ascending: false }).range(from, to)

    const { data: logs, error, count } = await query

    if (error) {
      console.error('Erro ao buscar logs de auditoria:', error)
      throw error
    }

    // Transform data to match frontend interface
    const data = (logs || []).map((log) => {
      const details = (log.details as Record<string, unknown>) || {}
      return {
        id: log.id,
        action: log.action,
        actor_email: log.user_email || 'system',
        actor_role: (details.role as string) || 'unknown',
        details: details,
        created_at: log.created_at,
      }
    })

    const total = count || 0
    const pages = Math.ceil(total / perPage)

    return NextResponse.json({
      data,
      total,
      page,
      per_page: perPage,
      pages,
    })
  } catch (error) {
    console.error('Erro ao buscar logs de auditoria:', error)
    return NextResponse.json({ data: [], total: 0, page: 1, per_page: 50, pages: 0 })
  }
}
