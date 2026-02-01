/**
 * API: GET /api/auditoria/export
 *
 * Exporta logs de auditoria em CSV.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const action = searchParams.get('action')
    const actorEmail = searchParams.get('actor_email')
    const fromDate = searchParams.get('from_date')
    const toDate = searchParams.get('to_date')

    const supabase = createAdminClient()

    // Build query - no pagination for export
    let query = supabase.from('audit_log').select(`
        id,
        action,
        user_email,
        details,
        created_at
      `)

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

    // Limit to last 10000 records for performance
    query = query.order('created_at', { ascending: false }).limit(10000)

    const { data: logs, error } = await query

    if (error) {
      console.error('Erro ao exportar logs de auditoria:', error)
      throw error
    }

    // Build CSV
    const headers = ['timestamp', 'action', 'actor_email', 'actor_role', 'details']
    const rows = (logs || []).map((log) => {
      const details = (log.details as Record<string, unknown>) || {}
      const role = (details.role as string) || 'unknown'
      const detailsStr = JSON.stringify(details).replace(/"/g, '""')

      return [
        log.created_at || '',
        log.action || '',
        log.user_email || 'system',
        role,
        `"${detailsStr}"`,
      ].join(',')
    })

    const csv = [headers.join(','), ...rows].join('\n')
    const today = new Date().toISOString().split('T')[0]

    return new NextResponse(csv, {
      headers: {
        'Content-Type': 'text/csv',
        'Content-Disposition': `attachment; filename="audit_logs_${today}.csv"`,
      },
    })
  } catch (error) {
    console.error('Erro ao exportar logs de auditoria:', error)
    const today = new Date().toISOString().split('T')[0]
    return new NextResponse('timestamp,action,actor_email,actor_role,details\n', {
      headers: {
        'Content-Type': 'text/csv',
        'Content-Disposition': `attachment; filename="audit_logs_${today}.csv"`,
      },
    })
  }
}
