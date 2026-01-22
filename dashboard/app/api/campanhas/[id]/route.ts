import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

interface RouteParams {
  params: Promise<{ id: string }>
}

/**
 * GET /api/campanhas/[id]
 * Retorna detalhes de uma campanha com envios
 */
export async function GET(_request: NextRequest, { params }: RouteParams) {
  try {
    const supabase = await createClient()
    const { id } = await params

    // Buscar campanha
    const { data: campanha, error: campanhaError } = await supabase
      .from('campanhas')
      .select('*')
      .eq('id', id)
      .single()

    if (campanhaError || !campanha) {
      return NextResponse.json({ detail: 'Campanha nao encontrada' }, { status: 404 })
    }

    // Buscar envios da campanha com dados do cliente
    const { data: envios, error: enviosError } = await supabase
      .from('envios')
      .select(
        `
        id,
        cliente_id,
        status,
        conteudo_enviado,
        created_at,
        enviado_em,
        entregue_em,
        visualizado_em,
        falhou_em,
        clientes (
          id,
          primeiro_nome,
          sobrenome,
          telefone,
          especialidade
        )
      `
      )
      .eq('campanha_id', id)
      .order('created_at', { ascending: false })
      .limit(100)

    if (enviosError) {
      console.error('Erro ao buscar envios:', enviosError)
    }

    // Calcular metricas
    const totalEnvios = envios?.length || 0
    const enviados = envios?.filter((e) => e.enviado_em).length || 0
    const entregues = envios?.filter((e) => e.entregue_em).length || 0
    const visualizados = envios?.filter((e) => e.visualizado_em).length || 0
    const falhas = envios?.filter((e) => e.status === 'falhou').length || 0

    return NextResponse.json({
      ...campanha,
      envios: envios || [],
      metricas: {
        total: totalEnvios,
        enviados,
        entregues,
        visualizados,
        falhas,
        taxa_entrega: enviados > 0 ? Math.round((entregues / enviados) * 100) : 0,
        taxa_visualizacao: entregues > 0 ? Math.round((visualizados / entregues) * 100) : 0,
      },
    })
  } catch (error) {
    console.error('Erro ao buscar campanha:', error)
    return NextResponse.json({ detail: 'Erro interno do servidor' }, { status: 500 })
  }
}

/**
 * PATCH /api/campanhas/[id]
 * Atualiza status da campanha (iniciar, pausar, etc)
 */
export async function PATCH(request: NextRequest, { params }: RouteParams) {
  try {
    const supabase = await createClient()
    const { id } = await params

    // Verificar autenticacao
    const {
      data: { user },
    } = await supabase.auth.getUser()
    if (!user) {
      return NextResponse.json({ detail: 'Nao autorizado' }, { status: 401 })
    }

    const body = await request.json()
    const { action } = body

    // Buscar campanha atual
    const { data: campanha, error: fetchError } = await supabase
      .from('campanhas')
      .select('*')
      .eq('id', id)
      .single()

    if (fetchError || !campanha) {
      return NextResponse.json({ detail: 'Campanha nao encontrada' }, { status: 404 })
    }

    // Determinar novo status baseado na acao
    let newStatus: string
    let updateData: Record<string, unknown> = {}

    switch (action) {
      case 'iniciar':
        if (!['rascunho', 'agendada', 'pausada'].includes(campanha.status)) {
          return NextResponse.json(
            { detail: 'Campanha nao pode ser iniciada neste status' },
            { status: 400 }
          )
        }
        newStatus = 'ativa'
        updateData = { iniciada_em: new Date().toISOString() }
        break

      case 'pausar':
        if (campanha.status !== 'ativa') {
          return NextResponse.json(
            { detail: 'Apenas campanhas em execucao podem ser pausadas' },
            { status: 400 }
          )
        }
        newStatus = 'pausada'
        break

      case 'retomar':
        if (campanha.status !== 'pausada') {
          return NextResponse.json(
            { detail: 'Apenas campanhas pausadas podem ser retomadas' },
            { status: 400 }
          )
        }
        newStatus = 'ativa'
        break

      case 'cancelar':
        if (['concluida', 'cancelada'].includes(campanha.status)) {
          return NextResponse.json({ detail: 'Campanha ja esta finalizada' }, { status: 400 })
        }
        newStatus = 'cancelada'
        updateData = { concluida_em: new Date().toISOString() }
        break

      case 'concluir':
        if (campanha.status !== 'ativa') {
          return NextResponse.json(
            { detail: 'Apenas campanhas em execucao podem ser concluidas' },
            { status: 400 }
          )
        }
        newStatus = 'concluida'
        updateData = { concluida_em: new Date().toISOString() }
        break

      default:
        return NextResponse.json({ detail: 'Acao invalida' }, { status: 400 })
    }

    // Atualizar campanha
    const { data: updated, error: updateError } = await supabase
      .from('campanhas')
      .update({
        status: newStatus,
        updated_at: new Date().toISOString(),
        ...updateData,
      })
      .eq('id', id)
      .select()
      .single()

    if (updateError) {
      console.error('Erro ao atualizar campanha:', updateError)
      return NextResponse.json({ detail: 'Erro ao atualizar campanha' }, { status: 500 })
    }

    // Registrar no audit_log
    await supabase.from('audit_log').insert({
      action: `campanha_${action}`,
      user_email: user.email,
      details: {
        campanha_id: id,
        nome: campanha.nome_template,
        status_anterior: campanha.status,
        status_novo: newStatus,
      },
      created_at: new Date().toISOString(),
    })

    return NextResponse.json(updated)
  } catch (error) {
    console.error('Erro ao atualizar campanha:', error)
    return NextResponse.json({ detail: 'Erro interno do servidor' }, { status: 500 })
  }
}

/**
 * PUT /api/campanhas/[id]
 * Atualiza os dados de uma campanha em rascunho
 */
export async function PUT(request: NextRequest, { params }: RouteParams) {
  try {
    const supabase = await createClient()
    const { id } = await params

    // Verificar autenticacao
    const {
      data: { user },
    } = await supabase.auth.getUser()
    if (!user) {
      return NextResponse.json({ detail: 'Nao autorizado' }, { status: 401 })
    }

    // Buscar campanha atual
    const { data: campanha, error: fetchError } = await supabase
      .from('campanhas')
      .select('*')
      .eq('id', id)
      .single()

    if (fetchError || !campanha) {
      return NextResponse.json({ detail: 'Campanha nao encontrada' }, { status: 404 })
    }

    // Apenas campanhas em rascunho ou agendadas podem ser editadas
    if (!['rascunho', 'agendada'].includes(campanha.status)) {
      return NextResponse.json(
        { detail: 'Apenas campanhas em rascunho ou agendadas podem ser editadas' },
        { status: 400 }
      )
    }

    const body = await request.json()

    // Determinar status baseado no agendamento
    // Se tiver data de agendamento, muda para "agendada", senao mantem "rascunho"
    const novoStatus = body.agendar_para ? 'agendada' : 'rascunho'

    // Atualizar campanha
    const { data: updated, error: updateError } = await supabase
      .from('campanhas')
      .update({
        nome_template: body.nome_template,
        tipo_campanha: body.tipo_campanha,
        categoria: body.categoria,
        objetivo: body.objetivo,
        corpo: body.corpo,
        tom: body.tom,
        audience_filters: body.audience_filters,
        agendar_para: body.agendar_para || null,
        status: novoStatus,
        updated_at: new Date().toISOString(),
      })
      .eq('id', id)
      .select()
      .single()

    if (updateError) {
      console.error('Erro ao atualizar campanha:', updateError)
      return NextResponse.json({ detail: 'Erro ao atualizar campanha' }, { status: 500 })
    }

    // Registrar no audit_log
    await supabase.from('audit_log').insert({
      action: 'campanha_editada',
      user_email: user.email,
      details: {
        campanha_id: id,
        nome: body.nome_template,
        campos_alterados: Object.keys(body),
      },
      created_at: new Date().toISOString(),
    })

    return NextResponse.json(updated)
  } catch (error) {
    console.error('Erro ao editar campanha:', error)
    return NextResponse.json({ detail: 'Erro interno do servidor' }, { status: 500 })
  }
}
