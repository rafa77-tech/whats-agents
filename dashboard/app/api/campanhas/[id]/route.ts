import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

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

    // Buscar envios da tabela envios (legado)
    const { data: enviosLegacy, error: enviosError } = await supabase
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
      console.error('Erro ao buscar envios legado:', enviosError)
    }

    // Buscar mensagens da fila_mensagens (novo sistema Sprint 35+)
    // Sem limite para ver todos os envios da campanha
    const { data: filaMensagens, error: filaError } = await supabase
      .from('fila_mensagens')
      .select(
        `
        id,
        cliente_id,
        conversa_id,
        status,
        conteudo,
        created_at,
        enviada_em,
        outcome,
        provider_message_id,
        clientes (
          id,
          primeiro_nome,
          sobrenome,
          telefone,
          especialidade
        )
      `
      )
      .contains('metadata', { campanha_id: id })
      .order('created_at', { ascending: false })

    if (filaError) {
      console.error('Erro ao buscar fila_mensagens:', filaError)
    }

    // Buscar delivery_status das interações para esta campanha
    // Interações de saída (tipo='saida') criadas para mensagens de campanha
    const conversaIds =
      filaMensagens?.map((m) => m.conversa_id).filter((id): id is string => id !== null) || []

    const deliveryStatusMap = new Map<string, { delivery_status: string; created_at: string }>()

    if (conversaIds.length > 0) {
      const { data: interacoes } = await supabase
        .from('interacoes')
        .select('conversation_id, delivery_status, created_at')
        .in('conversation_id', conversaIds)
        .eq('tipo', 'saida')
        .eq('autor_tipo', 'julia')
        .order('created_at', { ascending: false })

      // Mapear por conversation_id (pegar a mais recente)
      interacoes?.forEach((i) => {
        if (!deliveryStatusMap.has(i.conversation_id)) {
          deliveryStatusMap.set(i.conversation_id, {
            delivery_status: i.delivery_status || 'sent',
            created_at: i.created_at,
          })
        }
      })
    }

    // Mapear fila_mensagens para formato de envios
    // IMPORTANTE: Deduplicar por cliente_id - manter apenas o envio mais recente por cliente
    const clientesProcessados = new Set<string>()
    const enviosDaFila =
      filaMensagens
        ?.filter((msg) => {
          // Deduplicar por cliente_id (array já está ordenado por created_at DESC)
          if (clientesProcessados.has(msg.cliente_id)) {
            return false
          }
          clientesProcessados.add(msg.cliente_id)
          return true
        })
        .map((msg) => {
          // Mapear status/outcome da fila para status de envio
          // Outcomes: SENT, BLOCKED_*, FAILED_*, DEDUPED, BYPASS
          let envioStatus = 'pendente'
          let falhouEm: string | null = null

          const outcome = msg.outcome as string | null

          if (outcome === 'SENT') {
            envioStatus = 'enviado'
          } else if (outcome?.startsWith('BLOCKED_') || outcome?.startsWith('FAILED_')) {
            envioStatus = 'falhou'
            falhouEm = msg.enviada_em || msg.created_at
          } else if (outcome === 'DEDUPED') {
            envioStatus = 'falhou' // Deduplicado = não enviado
            falhouEm = msg.created_at
          } else if (msg.enviada_em) {
            envioStatus = 'enviado'
          } else if (msg.status === 'processando') {
            envioStatus = 'pendente'
          }

          // Buscar delivery_status da interação correspondente
          const conversaId = msg.conversa_id as string | null
          const deliveryInfo = conversaId ? deliveryStatusMap.get(conversaId) : null
          const deliveryStatus = deliveryInfo?.delivery_status || null

          // Mapear delivery_status para entregue_em e visualizado_em
          // delivery_status: 'pending' | 'sent' | 'delivered' | 'read' | 'failed'
          let entregueEm: string | null = null
          let visualizadoEm: string | null = null

          if (deliveryStatus === 'delivered' || deliveryStatus === 'read') {
            entregueEm = deliveryInfo?.created_at || msg.enviada_em
          }
          if (deliveryStatus === 'read') {
            visualizadoEm = deliveryInfo?.created_at || msg.enviada_em
          }
          if (deliveryStatus === 'failed') {
            envioStatus = 'falhou'
            falhouEm = falhouEm || deliveryInfo?.created_at || null
          }

          return {
            id: msg.id,
            cliente_id: msg.cliente_id,
            status: envioStatus,
            conteudo_enviado: msg.conteudo,
            created_at: msg.created_at,
            enviado_em: msg.enviada_em,
            entregue_em: entregueEm,
            visualizado_em: visualizadoEm,
            falhou_em: falhouEm,
            clientes: msg.clientes,
          }
        }) || []

    // Combinar envios (priorizar fila_mensagens se existir)
    const envios = enviosDaFila.length > 0 ? enviosDaFila : enviosLegacy || []

    // Calcular metricas dos envios
    const calculatedTotal = envios.length
    const calculatedEnviados = envios.filter((e) => e.enviado_em).length
    const calculatedEntregues = envios.filter((e) => e.entregue_em).length
    const visualizados = envios.filter((e) => e.visualizado_em).length
    const falhas = envios.filter((e) => e.status === 'falhou').length

    // Sprint 57: fila_mensagens/envios é a fonte de verdade para enviados/entregues
    // campanhas.enviados registra total ENFILEIRADO, não efetivamente enviado
    const storedTotal = campanha.total_destinatarios ?? 0

    const total = storedTotal > 0 ? storedTotal : calculatedTotal
    // Fonte de verdade: calculado da fila/envios, fallback: stored
    const enviados = calculatedEnviados > 0 ? calculatedEnviados : (campanha.enviados ?? 0)
    const entregues = calculatedEntregues > 0 ? calculatedEntregues : (campanha.entregues ?? 0)

    return NextResponse.json({
      ...campanha,
      envios: envios || [],
      metricas: {
        total,
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

    // Se ação é iniciar ou retomar, chamar o executor do backend para criar os envios
    if (action === 'iniciar' || action === 'retomar') {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      try {
        const execResponse = await fetch(`${apiUrl}/campanhas/${id}/iniciar`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        })

        if (!execResponse.ok) {
          console.error(
            `Erro ao executar campanha ${id}: ${execResponse.status} ${execResponse.statusText}`
          )
          // Não falha a requisição, apenas loga o erro
          // Os envios serão criados, mas pode haver delay
        } else {
          console.log(`Campanha ${id} executada com sucesso pelo backend`)
        }
      } catch (execError) {
        console.error(`Erro ao chamar executor para campanha ${id}:`, execError)
        // Não falha a requisição principal
      }
    }

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
/**
 * DELETE /api/campanhas/[id]
 * Exclui uma campanha em rascunho (hard delete)
 */
export async function DELETE(_request: NextRequest, { params }: RouteParams) {
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

    // Buscar campanha
    const { data: campanha, error: fetchError } = await supabase
      .from('campanhas')
      .select('id, status, nome_template')
      .eq('id', id)
      .single()

    if (fetchError || !campanha) {
      return NextResponse.json({ detail: 'Campanha nao encontrada' }, { status: 404 })
    }

    // Apenas rascunhos podem ser excluidos
    if (campanha.status !== 'rascunho') {
      return NextResponse.json(
        { detail: 'Apenas campanhas em rascunho podem ser excluidas' },
        { status: 409 }
      )
    }

    // Deletar registros filhos (FK sem CASCADE)
    await supabase.from('metricas_campanhas').delete().eq('campanha_id', id)
    await supabase.from('envios').delete().eq('campanha_id', id)
    await supabase.from('execucoes_campanhas').delete().eq('campanha_id', id)

    // Deletar campanha
    const { error: deleteError } = await supabase.from('campanhas').delete().eq('id', id)

    if (deleteError) {
      console.error('Erro ao excluir campanha:', deleteError)
      return NextResponse.json({ detail: 'Erro ao excluir campanha' }, { status: 500 })
    }

    // Registrar no audit_log
    await supabase.from('audit_log').insert({
      action: 'campanha_excluida',
      user_email: user.email,
      details: {
        campanha_id: id,
        nome: campanha.nome_template,
      },
      created_at: new Date().toISOString(),
    })

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Erro ao excluir campanha:', error)
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
