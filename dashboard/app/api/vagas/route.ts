/**
 * API: GET /api/vagas | POST /api/vagas
 *
 * Lista vagas do banco de dados com validacao Zod.
 * Cria vagas manuais via POST.
 */

import { NextRequest, NextResponse } from 'next/server'
import { ZodError } from 'zod'
import { createAdminClient } from '@/lib/supabase/admin'
import { parseShiftListParams, parseShiftCreateBody } from '@/lib/vagas'

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
      criticidade,
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
        criticidade,
        total_candidaturas,
        created_at,
        hospital_id,
        especialidade_id,
        contato_nome,
        contato_whatsapp,
        hospitais!inner(id, nome),
        especialidades!inner(id, nome)
      `,
      { count: 'exact' }
    )

    // Apply filters
    if (status) {
      query = query.eq('status', status)
    }
    if (criticidade) {
      query = query.eq('criticidade', criticidade)
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
      // PostgREST does not support foreign table filters inside .or(),
      // so we resolve matching IDs first then filter by them.
      const [{ data: hMatch }, { data: eMatch }] = await Promise.all([
        supabase.from('hospitais').select('id').ilike('nome', `%${search}%`),
        supabase.from('especialidades').select('id').ilike('nome', `%${search}%`),
      ])

      const hIds = (hMatch || []).map((h) => h.id)
      const eIds = (eMatch || []).map((e) => e.id)

      if (hIds.length === 0 && eIds.length === 0) {
        return NextResponse.json({ data: [], total: 0, pages: 0 })
      }

      const conditions: string[] = []
      if (hIds.length > 0) conditions.push(`hospital_id.in.(${hIds.join(',')})`)
      if (eIds.length > 0) conditions.push(`especialidade_id.in.(${eIds.join(',')})`)
      query = query.or(conditions.join(','))
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
        criticidade: v.criticidade || 'normal',
        reservas_count: v.total_candidaturas || 0,
        created_at: v.created_at,
        contato_nome: v.contato_nome || null,
        contato_whatsapp: v.contato_whatsapp || null,
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

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()

    let parsed
    try {
      parsed = parseShiftCreateBody(body)
    } catch (error) {
      if (error instanceof ZodError) {
        return NextResponse.json(
          { detail: 'Dados invalidos', errors: error.errors },
          { status: 400 }
        )
      }
      throw error
    }

    const supabase = createAdminClient()
    const quantidade = parsed.quantidade ?? 1

    const insertData: Record<string, unknown> = {
      hospital_id: parsed.hospital_id,
      especialidade_id: parsed.especialidade_id,
      data: parsed.data,
      status: 'aberta',
      origem: 'manual',
      created_at: new Date().toISOString(),
      contato_nome: parsed.contato_nome,
      contato_whatsapp: parsed.contato_whatsapp,
      criticidade: parsed.criticidade ?? 'normal',
    }

    if (parsed.hora_inicio) insertData.hora_inicio = parsed.hora_inicio
    if (parsed.hora_fim) insertData.hora_fim = parsed.hora_fim
    if (parsed.observacoes) insertData.observacoes = parsed.observacoes

    if (parsed.valor != null) {
      insertData.valor = parsed.valor
      insertData.valor_tipo = 'fixo'
    } else {
      insertData.valor_tipo = 'a_combinar'
    }

    if (quantidade === 1) {
      const { data, error } = await supabase.from('vagas').insert(insertData).select('id').single()

      if (error) {
        console.error('Erro ao criar vaga:', error)
        return NextResponse.json({ detail: 'Erro ao criar vaga no banco' }, { status: 500 })
      }

      return NextResponse.json({ id: data.id, success: true, count: 1 }, { status: 201 })
    }

    // Batch insert: create N identical records
    const records = Array.from({ length: quantidade }, () => ({ ...insertData }))
    const { data, error } = await supabase.from('vagas').insert(records).select('id')

    if (error) {
      console.error('Erro ao criar vagas em lote:', error)
      return NextResponse.json({ detail: 'Erro ao criar vagas no banco' }, { status: 500 })
    }

    const ids = (data || []).map((r) => r.id)
    return NextResponse.json({ ids, success: true, count: ids.length }, { status: 201 })
  } catch (error) {
    console.error('Erro ao criar vaga:', error)
    return NextResponse.json({ detail: 'Erro interno do servidor' }, { status: 500 })
  }
}
