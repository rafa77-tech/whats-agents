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

    // Buscar métricas de AMBAS as tabelas: envios (legado) e fila_mensagens (Sprint 35+)
    const campanhaIds = campanhas.map((c) => c.id)

    // 1. Buscar da tabela envios (sistema legado)
    const { data: envios } = await supabase
      .from('envios')
      .select('campanha_id, enviado_em, entregue_em, visualizado_em, status')
      .in('campanha_id', campanhaIds)

    // 2. Buscar da tabela fila_mensagens (Sprint 35+)
    // Campanhas usam metadata.campanha_id para identificar mensagens
    const { data: filaMensagens } = await supabase
      .from('fila_mensagens')
      .select('id, cliente_id, status, enviada_em, outcome, metadata')

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

    // Processar envios (legado)
    if (envios) {
      for (const envio of envios) {
        const metricas = metricasPorCampanha.get(envio.campanha_id)
        if (metricas) {
          metricas.total++
          if (envio.enviado_em) metricas.enviados++
          if (envio.entregue_em) metricas.entregues++
        }
      }
    }

    // Processar fila_mensagens (Sprint 35+)
    // IMPORTANTE: Deduplicar por cliente_id para evitar contar múltiplas execuções
    if (filaMensagens) {
      // Agrupar por campanha_id -> Set de cliente_ids processados
      const clientesProcessadosPorCampanha = new Map<number, Set<string>>()

      for (const msg of filaMensagens) {
        // Extrair campanha_id do metadata
        const metadata = msg.metadata as Record<string, unknown> | null
        const campanhaIdStr = metadata?.campanha_id as string | undefined
        if (!campanhaIdStr) continue

        const campanhaId = parseInt(campanhaIdStr, 10)
        if (isNaN(campanhaId)) continue

        const metricas = metricasPorCampanha.get(campanhaId)
        if (!metricas) continue

        // Deduplicar por cliente_id
        if (!clientesProcessadosPorCampanha.has(campanhaId)) {
          clientesProcessadosPorCampanha.set(campanhaId, new Set())
        }
        const clientesProcessados = clientesProcessadosPorCampanha.get(campanhaId)!

        // Se já processamos este cliente para esta campanha, pular
        if (clientesProcessados.has(msg.cliente_id)) continue
        clientesProcessados.add(msg.cliente_id)

        metricas.total++
        // Considerar enviada se status='enviada' ou outcome começando com SENT
        const isEnviada =
          msg.status === 'enviada' || (msg.outcome && String(msg.outcome).startsWith('SENT'))
        if (isEnviada || msg.enviada_em) {
          metricas.enviados++
          // Para fila_mensagens, considerar entregue se foi enviada
          // (não temos tracking de entrega nesse sistema)
          metricas.entregues++
        }
      }
    }

    // Mesclar métricas calculadas com valores armazenados na campanha
    // Prioridade: armazenado > calculado > 0
    // (valores armazenados são mais confiáveis pois são atualizados pelo executor)
    const campanhasComMetricas = campanhas.map((campanha) => {
      const metricas = metricasPorCampanha.get(campanha.id)
      const calculatedTotal = metricas?.total ?? 0
      const calculatedEnviados = metricas?.enviados ?? 0
      const calculatedEntregues = metricas?.entregues ?? 0

      // Usar valores armazenados se disponíveis, senão calcular da fila
      const storedTotal = campanha.total_destinatarios ?? 0
      const storedEnviados = campanha.enviados ?? 0
      const storedEntregues = campanha.entregues ?? 0

      return {
        ...campanha,
        total_destinatarios: storedTotal > 0 ? storedTotal : calculatedTotal,
        enviados: storedEnviados > 0 ? storedEnviados : calculatedEnviados,
        entregues: storedEntregues > 0 ? storedEntregues : calculatedEntregues,
        respondidos: campanha.respondidos ?? metricas?.respondidos ?? 0,
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
 * Tipos de campanha que têm mensagem automática gerada pelo sistema
 * - descoberta: usa aberturas dinâmicas
 * - reativacao: usa template "Faz tempo que a gente nao se fala"
 * - followup: usa template "Lembrei de vc"
 */
const TIPOS_COM_MENSAGEM_AUTOMATICA = ['descoberta', 'reativacao', 'followup']

function requiresCustomMessage(tipoCampanha: string): boolean {
  return !TIPOS_COM_MENSAGEM_AUTOMATICA.includes(tipoCampanha)
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

    // Corpo é obrigatório apenas para tipos que não têm mensagem automática
    const tipoCampanha = body.tipo_campanha || 'oferta_plantao'
    if (requiresCustomMessage(tipoCampanha) && !body.corpo?.trim()) {
      return NextResponse.json({ detail: 'Corpo da mensagem e obrigatorio' }, { status: 400 })
    }

    const { data, error } = await supabase
      .from('campanhas')
      .insert({
        nome_template: body.nome_template.trim(),
        tipo_campanha: tipoCampanha,
        categoria: body.categoria || 'marketing',
        objetivo: body.objetivo?.trim() || null,
        corpo: body.corpo?.trim() || null,
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
