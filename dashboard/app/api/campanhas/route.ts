import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

/**
 * GET /api/campanhas
 * Lista campanhas com filtro por status
 * Calcula métricas em tempo real a partir da tabela envios
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

    const { data: campanhas, error } = await query

    if (error) {
      console.error('Erro ao buscar campanhas:', error)
      return NextResponse.json({ detail: 'Erro ao buscar campanhas' }, { status: 500 })
    }

    if (!campanhas || campanhas.length === 0) {
      return NextResponse.json([])
    }

    // Buscar métricas reais da tabela envios para cada campanha
    const campanhaIds = campanhas.map((c) => c.id)
    const { data: envios } = await supabase
      .from('envios')
      .select('campanha_id, enviado_em, entregue_em, visualizado_em, status')
      .in('campanha_id', campanhaIds)

    // Calcular métricas por campanha
    const metricasPorCampanha = new Map<
      number,
      { total: number; enviados: number; entregues: number; respondidos: number }
    >()

    for (const campanha of campanhas) {
      metricasPorCampanha.set(campanha.id, {
        total: 0,
        enviados: 0,
        entregues: 0,
        respondidos: 0,
      })
    }

    if (envios) {
      for (const envio of envios) {
        const metricas = metricasPorCampanha.get(envio.campanha_id)
        if (metricas) {
          metricas.total++
          if (envio.enviado_em) metricas.enviados++
          if (envio.entregue_em) metricas.entregues++
          // respondidos seria baseado em outra lógica (ex: conversa iniciada)
        }
      }
    }

    // Sobrescrever os campos armazenados com os valores calculados
    const campanhasComMetricas = campanhas.map((campanha) => {
      const metricas = metricasPorCampanha.get(campanha.id)
      return {
        ...campanha,
        total_destinatarios: metricas?.total ?? campanha.total_destinatarios ?? 0,
        enviados: metricas?.enviados ?? campanha.enviados ?? 0,
        entregues: metricas?.entregues ?? campanha.entregues ?? 0,
        respondidos: metricas?.respondidos ?? campanha.respondidos ?? 0,
      }
    })

    return NextResponse.json(campanhasComMetricas)
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
