/**
 * API: GET /api/vagas
 *
 * Lista vagas do banco de dados com validacao Zod.
 */

import { NextRequest, NextResponse } from 'next/server'
import { ZodError } from 'zod'
import { createAdminClient } from '@/lib/supabase/admin'
import { parseShiftListParams } from '@/lib/vagas'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams

    // Validate query params with Zod
    let params
    try {
      params = parseShiftListParams(searchParams)
    } catch (error) {
      if (error instanceof ZodError) {
        return NextResponse.json(
          { error: 'Parametros de busca invalidos', details: error.errors },
          { status: 400 }
        )
      }
      throw error
    }

    const {
      page,
      per_page: perPage,
      status,
      hospital_id,
      especialidade_id,
      date_from,
      date_to,
      search,
    } = params

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
    if (hospital_id) {
      query = query.eq('hospital_id', hospital_id)
    }
    if (especialidade_id) {
      query = query.eq('especialidade_id', especialidade_id)
    }
    if (date_from) {
      query = query.gte('data', date_from)
    }
    if (date_to) {
      query = query.lte('data', date_to)
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
