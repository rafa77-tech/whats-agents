/**
 * API: GET /api/medicos
 *
 * Lista medicos (clientes) do banco de dados.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const page = parseInt(searchParams.get('page') || '1')
    const perPage = parseInt(searchParams.get('per_page') || '20')
    const stageJornada = searchParams.get('stage_jornada')
    const especialidade = searchParams.get('especialidade')
    const optOut = searchParams.get('opt_out')
    const search = searchParams.get('search')

    const supabase = createAdminClient()

    // Build query
    let query = supabase
      .from('clientes')
      .select(
        `
        id,
        primeiro_nome,
        sobrenome,
        telefone,
        especialidade,
        cidade,
        stage_jornada,
        opt_out,
        created_at
      `,
        { count: 'exact' }
      )
      .is('deleted_at', null) // Exclude soft-deleted records

    // Apply filters
    if (stageJornada) {
      query = query.eq('stage_jornada', stageJornada)
    }
    if (especialidade) {
      query = query.ilike('especialidade', `%${especialidade}%`)
    }
    if (optOut !== null && optOut !== undefined) {
      query = query.eq('opt_out', optOut === 'true')
    }
    if (search) {
      // Search by name, phone, or CRM
      query = query.or(
        `primeiro_nome.ilike.%${search}%,sobrenome.ilike.%${search}%,telefone.ilike.%${search}%,crm.ilike.%${search}%`
      )
    }

    // Pagination
    const from = (page - 1) * perPage
    const to = from + perPage - 1

    query = query.order('created_at', { ascending: false }).range(from, to)

    const { data: clientes, error, count } = await query

    if (error) {
      console.error('Erro ao buscar medicos:', error)
      throw error
    }

    // Transform data to match frontend interface
    const data = (clientes || []).map((c) => ({
      id: c.id,
      nome: [c.primeiro_nome, c.sobrenome].filter(Boolean).join(' ') || 'Sem nome',
      telefone: c.telefone || '',
      especialidade: c.especialidade || undefined,
      cidade: c.cidade || undefined,
      stage_jornada: c.stage_jornada || undefined,
      opt_out: c.opt_out || false,
      created_at: c.created_at,
    }))

    const total = count || 0
    const pages = Math.ceil(total / perPage)

    return NextResponse.json({
      data,
      total,
      pages,
    })
  } catch (error) {
    console.error('Erro ao buscar medicos:', error)
    return NextResponse.json({ data: [], total: 0, pages: 0 })
  }
}
