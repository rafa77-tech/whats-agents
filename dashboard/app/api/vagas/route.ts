/**
 * API: GET /api/vagas
 *
 * Lista vagas do banco de dados.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const page = parseInt(searchParams.get('page') || '1')
    const perPage = parseInt(searchParams.get('per_page') || '20')
    const status = searchParams.get('status')
    const hospitalId = searchParams.get('hospital_id')
    const especialidadeId = searchParams.get('especialidade_id')
    const dateFrom = searchParams.get('date_from')
    const dateTo = searchParams.get('date_to')
    const search = searchParams.get('search')

    const supabase = createAdminClient()

    // Build query
    let query = supabase.from('vagas').select(
      `
        id,
        data,
        hora_inicio,
        hora_fim,
        valor,
        status,
        total_candidaturas,
        created_at,
        hospital_id,
        especialidade_id,
        hospitais!inner(id, nome),
        especialidades!inner(id, nome)
      `,
      { count: 'exact' }
    )

    // Apply filters
    if (status) {
      query = query.eq('status', status)
    }
    if (hospitalId) {
      query = query.eq('hospital_id', hospitalId)
    }
    if (especialidadeId) {
      query = query.eq('especialidade_id', especialidadeId)
    }
    if (dateFrom) {
      query = query.gte('data', dateFrom)
    }
    if (dateTo) {
      query = query.lte('data', dateTo)
    }
    if (search) {
      query = query.or(`hospitais.nome.ilike.%${search}%,especialidades.nome.ilike.%${search}%`)
    }

    // Pagination
    const from = (page - 1) * perPage
    const to = from + perPage - 1

    query = query.order('data', { ascending: false }).range(from, to)

    const { data: vagas, error, count } = await query

    if (error) {
      console.error('Erro ao buscar vagas:', error)
      throw error
    }

    // Transform data to match frontend interface
    const shifts = (vagas || []).map((v) => {
      const hospital = v.hospitais as unknown as { id: string; nome: string } | null
      const especialidade = v.especialidades as unknown as { id: string; nome: string } | null

      return {
        id: v.id,
        hospital: hospital?.nome || 'N/A',
        hospital_id: v.hospital_id || '',
        especialidade: especialidade?.nome || 'N/A',
        especialidade_id: v.especialidade_id || '',
        data: v.data,
        hora_inicio: v.hora_inicio,
        hora_fim: v.hora_fim,
        valor: v.valor || 0,
        status: v.status || 'aberta',
        reservas_count: v.total_candidaturas || 0,
        created_at: v.created_at,
      }
    })

    const total = count || 0
    const pages = Math.ceil(total / perPage)

    return NextResponse.json({
      data: shifts,
      total,
      pages,
    })
  } catch (error) {
    console.error('Erro ao buscar vagas:', error)
    return NextResponse.json({ data: [], total: 0, pages: 0 })
  }
}
