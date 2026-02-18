import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'
import { listarHospitais } from '@/lib/hospitais'

export const dynamic = 'force-dynamic'

/**
 * GET /api/hospitais
 * Lista hospitais para seleção no combobox
 * Query params:
 *   - excluir_bloqueados: "true" para excluir hospitais bloqueados
 *   - search: busca por nome (ilike)
 *   - apenas_revisados: "true" para filtrar apenas revisados (default: true)
 *   - limit: limite de resultados (default: 50)
 */
export async function GET(request: NextRequest) {
  try {
    const supabase = createAdminClient()
    const searchParams = request.nextUrl.searchParams
    const excluirBloqueados = searchParams.get('excluir_bloqueados') === 'true'
    const search = searchParams.get('search') || ''
    const apenasRevisados = searchParams.get('apenas_revisados') !== 'false'
    const limitParam = searchParams.get('limit')
    const limit = limitParam ? parseInt(limitParam, 10) : 50

    const params: Parameters<typeof listarHospitais>[1] = {
      excluirBloqueados,
      apenasRevisados,
      limit: limit > 0 ? limit : 50,
    }
    if (search) {
      params.search = search
    }

    const hospitais = await listarHospitais(supabase, params)

    return NextResponse.json(hospitais)
  } catch (error) {
    console.error('Erro ao buscar hospitais:', error)
    const message = error instanceof Error ? error.message : 'Erro interno do servidor'
    return NextResponse.json({ detail: message }, { status: 500 })
  }
}

/**
 * POST /api/hospitais
 * Cria novo hospital
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()

    const nome = typeof body.nome === 'string' ? body.nome.trim() : ''
    if (!nome) {
      return NextResponse.json({ detail: 'Nome e obrigatorio' }, { status: 400 })
    }

    const cidade = typeof body.cidade === 'string' ? body.cidade.trim() : ''
    if (!cidade) {
      return NextResponse.json({ detail: 'Cidade e obrigatoria' }, { status: 400 })
    }

    const estado = typeof body.estado === 'string' ? body.estado.trim() : ''
    if (!estado) {
      return NextResponse.json({ detail: 'Estado e obrigatorio' }, { status: 400 })
    }

    const latitude =
      typeof body.latitude === 'number' && !Number.isNaN(body.latitude) ? body.latitude : null
    const longitude =
      typeof body.longitude === 'number' && !Number.isNaN(body.longitude) ? body.longitude : null
    const logradouro = typeof body.logradouro === 'string' ? body.logradouro.trim() : null
    const bairro = typeof body.bairro === 'string' ? body.bairro.trim() : null
    const cep = typeof body.cep === 'string' ? body.cep.trim() : null

    const hasLatLong = latitude !== null && longitude !== null

    const insertData: Record<string, unknown> = {
      nome,
      cidade,
      estado,
      endereco_verificado: hasLatLong,
      precisa_revisao: !hasLatLong,
    }
    if (latitude !== null) insertData.latitude = latitude
    if (longitude !== null) insertData.longitude = longitude
    if (logradouro) insertData.logradouro = logradouro
    if (bairro) insertData.bairro = bairro
    if (cep) insertData.cep = cep

    const supabase = createAdminClient()

    const { data, error } = await supabase
      .from('hospitais')
      .insert(insertData)
      .select('id, nome')
      .single()

    if (error) {
      console.error('Erro ao criar hospital:', error)
      return NextResponse.json({ detail: 'Erro ao criar hospital' }, { status: 500 })
    }

    return NextResponse.json(data, { status: 201 })
  } catch (error) {
    console.error('Erro ao criar hospital:', error)
    return NextResponse.json({ detail: 'Erro interno do servidor' }, { status: 500 })
  }
}
