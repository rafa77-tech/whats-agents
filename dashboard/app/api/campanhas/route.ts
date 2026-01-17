import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

/**
 * GET /api/campanhas
 * Lista campanhas com filtro por status
 */
export async function GET(request: NextRequest) {
  try {
    const supabase = await createClient()
    const status = request.nextUrl.searchParams.get('status')

    let query = supabase
      .from('campanhas')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(50)

    if (status) {
      const statusArray = status.split(',')
      query = query.in('status', statusArray)
    }

    const { data, error } = await query

    if (error) {
      console.error('Erro ao buscar campanhas:', error)
      return NextResponse.json({ detail: 'Erro ao buscar campanhas' }, { status: 500 })
    }

    return NextResponse.json(data || [])
  } catch (error) {
    console.error('Erro ao buscar campanhas:', error)
    return NextResponse.json({ detail: 'Erro interno do servidor' }, { status: 500 })
  }
}

interface CampanhaBody {
  nome_template: string
  tipo_campanha: string
  categoria: string
  objetivo?: string
  corpo: string
  tom: string
  audience_filters?: Record<string, unknown>
  agendar_para?: string
  status?: string
}

/**
 * POST /api/campanhas
 * Cria uma nova campanha
 */
export async function POST(request: NextRequest) {
  try {
    const supabase = await createClient()

    // Verificar autenticacao
    const {
      data: { user },
    } = await supabase.auth.getUser()
    if (!user) {
      return NextResponse.json({ detail: 'Nao autorizado' }, { status: 401 })
    }

    const body = (await request.json()) as CampanhaBody

    if (!body.nome_template?.trim()) {
      return NextResponse.json({ detail: 'Nome da campanha e obrigatorio' }, { status: 400 })
    }

    if (!body.corpo?.trim()) {
      return NextResponse.json({ detail: 'Corpo da mensagem e obrigatorio' }, { status: 400 })
    }

    const { data, error } = await supabase
      .from('campanhas')
      .insert({
        nome_template: body.nome_template.trim(),
        tipo_campanha: body.tipo_campanha || 'oferta_plantao',
        categoria: body.categoria || 'marketing',
        objetivo: body.objetivo?.trim() || null,
        corpo: body.corpo.trim(),
        tom: body.tom || 'amigavel',
        audience_filters: body.audience_filters || {},
        agendar_para: body.agendar_para || null,
        status: body.status || 'rascunho',
        created_by: user.email,
      })
      .select()
      .single()

    if (error) {
      console.error('Erro ao criar campanha:', error)
      return NextResponse.json({ detail: 'Erro ao criar campanha' }, { status: 500 })
    }

    // Registrar no audit_log
    await supabase.from('audit_log').insert({
      action: 'campanha_criada',
      user_email: user.email,
      details: {
        campanha_id: data.id,
        nome: data.nome_template,
        tipo: data.tipo_campanha,
      },
      created_at: new Date().toISOString(),
    })

    return NextResponse.json(data, { status: 201 })
  } catch (error) {
    console.error('Erro ao criar campanha:', error)
    return NextResponse.json({ detail: 'Erro interno do servidor' }, { status: 500 })
  }
}
