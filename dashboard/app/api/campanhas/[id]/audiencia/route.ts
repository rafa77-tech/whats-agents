import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

interface RouteParams {
  params: Promise<{ id: string }>
}

// Nomes femininos comuns no Brasil (para deteccao de genero)
const NOMES_FEMININOS = new Set([
  // Terminados em A (mais comuns)
  'ana',
  'maria',
  'julia',
  'luiza',
  'paula',
  'carla',
  'fernanda',
  'amanda',
  'bruna',
  'camila',
  'daniela',
  'eduarda',
  'fabiana',
  'gabriela',
  'helena',
  'isabela',
  'isadora',
  'jessica',
  'juliana',
  'larissa',
  'leticia',
  'luana',
  'luciana',
  'mariana',
  'natalia',
  'patricia',
  'rafaela',
  'renata',
  'roberta',
  'sandra',
  'silvia',
  'tatiana',
  'vanessa',
  'victoria',
  'viviane',
  'adriana',
  'alessandra',
  'aline',
  'bianca',
  'carolina',
  'clara',
  'claudia',
  'cristina',
  'debora',
  'eliana',
  'erica',
  'flavia',
  'giovana',
  'giovanna',
  'graziela',
  'heloisa',
  'ingrid',
  'ivana',
  'janaina',
  'joana',
  'karen',
  'karina',
  'livia',
  'lorena',
  'lucia',
  'madalena',
  'marcela',
  'marina',
  'mayara',
  'michela',
  'milena',
  'nadia',
  'nathalia',
  'nicole',
  'paloma',
  'priscila',
  'raquel',
  'regina',
  'rosana',
  'sabrina',
  'samara',
  'simone',
  'sonia',
  'stella',
  'suzana',
  'talita',
  'tania',
  'tereza',
  'thais',
  'vera',
  'yara',
  'zelia',
  // Terminados em E
  'alice',
  'beatrice',
  'carine',
  'diane',
  'elaine',
  'fabiane',
  'gisele',
  'helene',
  'irene',
  'jacqueline',
  'michele',
  'monique',
  'nadine',
  'noelle',
  'rosane',
  'simone',
  'suzane',
  'viviane',
  'yasmine',
  'denise',
  'elise',
  'louise',
  'rose',
  // Terminados em outras letras
  'beatriz',
  'raquel',
  'mabel',
  'miriam',
  'deborah',
  'sarah',
  'ruth',
  'elizabeth',
  'carmen',
  'lilian',
  'suelen',
  'jaquelin',
  'ellen',
  'kelen',
  'maryellen',
  // Nomes compostos comuns (primeiro nome)
  'ana',
  'maria',
  'rosa',
  'santa',
  'flor',
])

// Nomes masculinos comuns (para casos ambiguos)
const NOMES_MASCULINOS = new Set([
  'joao',
  'jose',
  'carlos',
  'paulo',
  'pedro',
  'lucas',
  'marcos',
  'andre',
  'rafael',
  'fernando',
  'rodrigo',
  'bruno',
  'gustavo',
  'daniel',
  'ricardo',
  'marcelo',
  'fabio',
  'eduardo',
  'alexandre',
  'leonardo',
  'thiago',
  'tiago',
  'diego',
  'vitor',
  'victor',
  'gabriel',
  'henrique',
  'felipe',
  'matheus',
  'mateus',
  'guilherme',
  'antonio',
  'francisco',
  'sergio',
  'luiz',
  'luis',
  'claudio',
  'roberto',
  'mario',
  'jorge',
  'leandro',
  'anderson',
  'diego',
  'renato',
  'rogerio',
  'wagner',
  'wellington',
  'william',
  'wilson',
  'alex',
  'alan',
  'caio',
  'cesar',
  'danilo',
  'erick',
  'igor',
  'ivan',
  'junior',
  'julio',
  'luan',
  'murilo',
  'nelson',
  'otavio',
  'renan',
  'samuel',
  'vinicius',
  'yuri',
])

/**
 * Detecta genero baseado no primeiro nome
 * Retorna 'F' para feminino, 'M' para masculino
 */
function detectarGenero(nome: string): 'F' | 'M' {
  const nomeNormalizado = nome
    .toLowerCase()
    .trim()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')

  // Verificar lista de nomes femininos
  if (NOMES_FEMININOS.has(nomeNormalizado)) {
    return 'F'
  }

  // Verificar lista de nomes masculinos
  if (NOMES_MASCULINOS.has(nomeNormalizado)) {
    return 'M'
  }

  // Heuristicas baseadas na terminacao
  // Nomes terminados em A geralmente sao femininos (exceto algumas excecoes)
  const excecoesMasculinasA = ['joshua', 'issa', 'mustafa', 'luca', 'nicola']
  if (nomeNormalizado.endsWith('a') && !excecoesMasculinasA.includes(nomeNormalizado)) {
    return 'F'
  }

  // Nomes terminados em O, R, S geralmente sao masculinos
  if (nomeNormalizado.endsWith('o') || nomeNormalizado.endsWith('os')) {
    return 'M'
  }

  // Default para masculino (Dr) quando incerto
  return 'M'
}

/**
 * Retorna o titulo correto baseado no genero
 */
function getTitulo(nome: string): string {
  return detectarGenero(nome) === 'F' ? 'Dra' : 'Dr'
}

// Fragmentos de abertura (sincronizado com app/fragmentos/aberturas.py)
// Usam {titulo} para Dr/Dra dinamico
const SAUDACOES = [
  'Oi {titulo} {nome}! Tudo bem?',
  'E ai {titulo} {nome}, td certo?',
  'Opa {titulo} {nome}! Como vai?',
  '{titulo} {nome}, tudo tranquilo?',
  'Oi! Fala {titulo} {nome}',
  'Oi {titulo} {nome}!',
  'Bom dia {titulo} {nome}!',
  'Boa tarde {titulo} {nome}!',
  'Boa noite {titulo} {nome}!',
  'E ai {titulo} {nome}! Tudo joia?',
  'Oi {titulo} {nome}, td bem?',
  'Fala {titulo} {nome}! Blz?',
  '{titulo} {nome}! Tudo certo ai?',
  'Opa! {titulo} {nome}, tudo bem?',
  'Oi {titulo} {nome}, como vai?',
  'Hey {titulo} {nome}!',
  'Ola {titulo} {nome}, tudo bom?',
  'Bom dia, {titulo} {nome}! Como ta?',
  'Boa tarde, {titulo} {nome}! Td certo?',
  'Boa noite, {titulo} {nome}! Tudo bem?',
]

const APRESENTACOES = [
  'Sou a Julia da Revoluna',
  'Aqui e a Julia, da Revoluna',
  'Julia aqui, da Revoluna',
  'Meu nome e Julia, sou da Revoluna',
  'Sou Julia, escalista da Revoluna',
  'Aqui e Julia da equipe Revoluna',
  'Julia da Revoluna aqui',
  'Oi! Julia da Revoluna',
  'Sou a Julia, da Revoluna',
  'Aqui e a Julia da Revoluna',
]

const CONTEXTOS = [
  'Trabalho com escalas medicas aqui na regiao',
  'A gente trabalha com plantoes medicos',
  'Cuido das escalas medicas aqui',
  'Trabalho conectando medicos com plantoes',
  'Ajudo medicos a encontrar plantoes',
  'Trabalho com oportunidades de plantao',
  'Cuido da parte de escalas e plantoes',
  'A Revoluna trabalha com escalas medicas',
  'Trabalho com staffing medico aqui no ABC',
  'Cuido das vagas de plantao aqui na regiao',
]

// Ganchos especificos por tipo de campanha
const GANCHOS_POR_TIPO: Record<string, string[]> = {
  // Discovery: perguntar interesse geral, SEM mencionar vagas especificas
  descoberta: [
    'Vc ta fazendo plantoes?',
    'Ta aceitando plantao?',
    'Tem interesse em plantoes?',
    'Vc faz plantao avulso?',
    'Ta com disponibilidade pra plantao?',
    'Vc trabalha com plantao?',
    'Costuma pegar plantoes?',
    'Faz plantao na regiao?',
    'Ta trabalhando com plantoes?',
    'Trabalha com escalas medicas?',
  ],
  // Oferta de plantao: pode mencionar vagas disponiveis
  oferta_plantao: [
    'Surgiu umas vagas boas, tem interesse?',
    'Vi umas vagas que podem te interessar',
    'Posso te mostrar algumas oportunidades?',
    'Quer saber das vagas disponiveis?',
    'Tenho algumas vagas aqui, posso te mostrar?',
    'Apareceram plantoes na sua area',
    'Tem uns plantoes legais aqui, quer ver?',
    'Surgiu uma vaga que combina com seu perfil',
  ],
  // Reativacao: tom de reconexao
  reativacao: [
    'Faz tempo que a gente nao conversa ne?',
    'Sumiu! Ta tudo bem?',
    'E ai, voltou a fazer plantoes?',
    'Como ta a situacao dos plantoes?',
    'Ta precisando de plantao?',
    'Lembrei de vc! Ta trabalhando?',
  ],
  // Followup: continuacao de conversa
  followup: [
    'Conseguiu pensar sobre aquela proposta?',
    'E ai, o que achou?',
    'Alguma novidade?',
    'Deu pra avaliar?',
    'Pensou sobre os plantoes?',
  ],
}

// Default (fallback) - usar descoberta que sempre existe
const GANCHOS_DEFAULT: string[] = GANCHOS_POR_TIPO.descoberta!

function gerarMensagemExemplo(nome: string, tipoCampanha?: string): string {
  const titulo = getTitulo(nome)
  const saudacao = SAUDACOES[Math.floor(Math.random() * SAUDACOES.length)] ?? SAUDACOES[0]!
  const apresentacao =
    APRESENTACOES[Math.floor(Math.random() * APRESENTACOES.length)] ?? APRESENTACOES[0]!
  const incluirContexto = Math.random() < 0.7
  const contexto = incluirContexto
    ? (CONTEXTOS[Math.floor(Math.random() * CONTEXTOS.length)] ?? CONTEXTOS[0]!)
    : null

  // Selecionar ganchos baseado no tipo de campanha
  const ganchosArray: string[] = GANCHOS_POR_TIPO[tipoCampanha ?? ''] ?? GANCHOS_DEFAULT
  const gancho = ganchosArray[Math.floor(Math.random() * ganchosArray.length)] ?? ganchosArray[0]!

  const partes = [
    saudacao.replace('{titulo}', titulo).replace('{nome}', nome),
    apresentacao,
    ...(contexto ? [contexto] : []),
    gancho,
  ]

  return partes.join('\n\n')
}

/**
 * GET /api/campanhas/[id]/audiencia
 * Retorna a audiencia (medicos) da campanha baseado nos filtros
 */
export async function GET(_request: NextRequest, { params }: RouteParams) {
  try {
    const supabase = await createClient()
    const { id } = await params

    // Buscar campanha
    const { data: campanha, error: campanhaError } = await supabase
      .from('campanhas')
      .select('id, nome_template, tipo_campanha, audience_filters')
      .eq('id', id)
      .single()

    if (campanhaError || !campanha) {
      return NextResponse.json({ detail: 'Campanha nao encontrada' }, { status: 404 })
    }

    const filters = campanha.audience_filters || {}
    const quantidade = filters.quantidade_alvo || 50
    const selectedIds: string[] = filters.selected_cliente_ids || []
    const excludedIds: string[] = filters.excluded_cliente_ids || []

    let clientes: Array<{
      id: string
      primeiro_nome: string
      sobrenome?: string
      telefone: string
      especialidade?: string
      cidade?: string
      estado?: string
    }> = []

    // Se tem lista explicita de IDs, usar ela
    if (selectedIds.length > 0) {
      const { data, error } = await supabase
        .from('clientes')
        .select('id, primeiro_nome, sobrenome, telefone, especialidade, cidade, estado')
        .in('id', selectedIds)
        .is('deleted_at', null)

      if (error) {
        console.error('Erro ao buscar clientes selecionados:', error)
        return NextResponse.json({ detail: 'Erro ao buscar audiencia' }, { status: 500 })
      }

      clientes = data || []
    } else {
      // Construir query para clientes baseado em filtros
      let query = supabase
        .from('clientes')
        .select('id, primeiro_nome, sobrenome, telefone, especialidade, cidade, estado')
        .is('deleted_at', null)
        .eq('opt_out', false)
        .order('created_at', { ascending: false })

      // Aplicar filtros
      if (
        filters.especialidades &&
        Array.isArray(filters.especialidades) &&
        filters.especialidades.length > 0
      ) {
        query = query.in('especialidade', filters.especialidades)
      }

      if (filters.regioes && Array.isArray(filters.regioes) && filters.regioes.length > 0) {
        query = query.in('estado', filters.regioes)
      }

      // Excluir IDs removidos manualmente
      if (excludedIds.length > 0) {
        query = query.not('id', 'in', `(${excludedIds.join(',')})`)
      }

      // Limitar quantidade
      query = query.limit(quantidade)

      const { data, error } = await query

      if (error) {
        console.error('Erro ao buscar clientes:', error)
        return NextResponse.json({ detail: 'Erro ao buscar audiencia' }, { status: 500 })
      }

      clientes = data || []
    }

    // Gerar exemplos de mensagens (3 exemplos com nomes reais)
    const tipoCampanha = campanha.tipo_campanha || 'descoberta'
    const exemplos = clientes.slice(0, 3).map((cliente) => {
      const nome = cliente.primeiro_nome || 'Medico'
      return {
        destinatario: `${cliente.primeiro_nome} ${cliente.sobrenome || ''}`.trim(),
        mensagem: gerarMensagemExemplo(nome, tipoCampanha),
      }
    })

    // Se nao tem clientes suficientes, gerar com nome generico
    while (exemplos.length < 3) {
      exemplos.push({
        destinatario: 'Dr. Exemplo',
        mensagem: gerarMensagemExemplo('Exemplo', tipoCampanha),
      })
    }

    // Calcular variacoes possiveis baseado no tipo de campanha
    const ganchosTipo = GANCHOS_POR_TIPO[tipoCampanha] ?? GANCHOS_DEFAULT
    const variacoesPossiveis =
      SAUDACOES.length * APRESENTACOES.length * (CONTEXTOS.length + 1) * (ganchosTipo?.length ?? 10)

    return NextResponse.json({
      total: clientes.length,
      filters: filters,
      clientes: clientes,
      exemplos_mensagens: exemplos,
      variacoes_possiveis: variacoesPossiveis,
      tipo_campanha: tipoCampanha,
      modo: selectedIds.length > 0 ? 'manual' : 'filtros',
    })
  } catch (error) {
    console.error('Erro ao buscar audiencia:', error)
    return NextResponse.json({ detail: 'Erro interno do servidor' }, { status: 500 })
  }
}

/**
 * PATCH /api/campanhas/[id]/audiencia
 * Adiciona ou remove medicos da audiencia da campanha
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

    // Buscar campanha
    const { data: campanha, error: campanhaError } = await supabase
      .from('campanhas')
      .select('id, status, audience_filters')
      .eq('id', id)
      .single()

    if (campanhaError || !campanha) {
      return NextResponse.json({ detail: 'Campanha nao encontrada' }, { status: 404 })
    }

    if (campanha.status !== 'rascunho') {
      return NextResponse.json(
        { detail: 'Apenas campanhas em rascunho podem ter audiencia modificada' },
        { status: 400 }
      )
    }

    const body = await request.json()
    const { action, cliente_ids } = body as { action: 'add' | 'remove'; cliente_ids: string[] }

    if (!action || !cliente_ids || !Array.isArray(cliente_ids)) {
      return NextResponse.json(
        { detail: 'Parametros invalidos. Esperado: action (add/remove), cliente_ids (array)' },
        { status: 400 }
      )
    }

    const filters = campanha.audience_filters || {}
    let selectedIds: string[] = filters.selected_cliente_ids || []
    let excludedIds: string[] = filters.excluded_cliente_ids || []

    if (action === 'remove') {
      if (selectedIds.length > 0) {
        // Se estamos no modo manual, remover da lista de selecionados
        selectedIds = selectedIds.filter((id) => !cliente_ids.includes(id))
      } else {
        // Se estamos no modo filtros, adicionar a lista de excluidos
        excludedIds = Array.from(new Set([...excludedIds, ...cliente_ids]))
      }
    } else if (action === 'add') {
      // Ao adicionar, primeiro verificamos se os IDs existem
      const { data: clientesExistentes } = await supabase
        .from('clientes')
        .select('id')
        .in('id', cliente_ids)
        .is('deleted_at', null)

      const idsValidos = (clientesExistentes || []).map((c) => c.id)

      if (selectedIds.length > 0) {
        // Se estamos no modo manual, adicionar a lista
        selectedIds = Array.from(new Set([...selectedIds, ...idsValidos]))
      } else {
        // Se estamos no modo filtros, remover da lista de excluidos (se existir) e mudar para modo manual
        excludedIds = excludedIds.filter((id) => !idsValidos.includes(id))

        // Buscar todos os clientes atuais pelos filtros para montar lista manual
        let query = supabase
          .from('clientes')
          .select('id')
          .is('deleted_at', null)
          .eq('opt_out', false)

        if (
          filters.especialidades &&
          Array.isArray(filters.especialidades) &&
          filters.especialidades.length > 0
        ) {
          query = query.in('especialidade', filters.especialidades)
        }

        if (filters.regioes && Array.isArray(filters.regioes) && filters.regioes.length > 0) {
          query = query.in('estado', filters.regioes)
        }

        if (excludedIds.length > 0) {
          query = query.not('id', 'in', `(${excludedIds.join(',')})`)
        }

        query = query.limit(filters.quantidade_alvo || 50)

        const { data: clientesAtuais } = await query
        const idsAtuais = (clientesAtuais || []).map((c) => c.id)

        // Combinar lista atual com novos IDs
        selectedIds = Array.from(new Set([...idsAtuais, ...idsValidos]))
        excludedIds = [] // Limpar excluidos ao mudar para modo manual
      }
    }

    // Atualizar campanha
    const newFilters = {
      ...filters,
      selected_cliente_ids: selectedIds.length > 0 ? selectedIds : undefined,
      excluded_cliente_ids: excludedIds.length > 0 ? excludedIds : undefined,
    }

    // Limpar campos undefined
    if (!newFilters.selected_cliente_ids) delete newFilters.selected_cliente_ids
    if (!newFilters.excluded_cliente_ids) delete newFilters.excluded_cliente_ids

    const { error: updateError } = await supabase
      .from('campanhas')
      .update({
        audience_filters: newFilters,
        updated_at: new Date().toISOString(),
      })
      .eq('id', id)

    if (updateError) {
      console.error('Erro ao atualizar audiencia:', updateError)
      return NextResponse.json({ detail: 'Erro ao atualizar audiencia' }, { status: 500 })
    }

    return NextResponse.json({
      success: true,
      action,
      cliente_ids,
      modo: selectedIds.length > 0 ? 'manual' : 'filtros',
    })
  } catch (error) {
    console.error('Erro ao modificar audiencia:', error)
    return NextResponse.json({ detail: 'Erro interno do servidor' }, { status: 500 })
  }
}

/**
 * GET /api/campanhas/[id]/audiencia/buscar?q=termo
 * Busca medicos para adicionar a campanha
 */
export async function POST(request: NextRequest, { params }: RouteParams) {
  try {
    const supabase = await createClient()
    const { id } = await params

    // Verificar se campanha existe
    const { data: campanha, error: campanhaError } = await supabase
      .from('campanhas')
      .select('id, audience_filters')
      .eq('id', id)
      .single()

    if (campanhaError || !campanha) {
      return NextResponse.json({ detail: 'Campanha nao encontrada' }, { status: 404 })
    }

    const body = await request.json()
    const { query: searchQuery } = body as { query: string }

    if (!searchQuery || searchQuery.length < 2) {
      return NextResponse.json({ detail: 'Termo de busca muito curto' }, { status: 400 })
    }

    // Buscar clientes que correspondem ao termo
    const { data: clientes, error } = await supabase
      .from('clientes')
      .select('id, primeiro_nome, sobrenome, telefone, especialidade, cidade, estado')
      .is('deleted_at', null)
      .eq('opt_out', false)
      .or(
        `primeiro_nome.ilike.%${searchQuery}%,sobrenome.ilike.%${searchQuery}%,telefone.ilike.%${searchQuery}%`
      )
      .order('primeiro_nome')
      .limit(20)

    if (error) {
      console.error('Erro ao buscar clientes:', error)
      return NextResponse.json({ detail: 'Erro ao buscar medicos' }, { status: 500 })
    }

    // Marcar quais ja estao na campanha
    const filters = campanha.audience_filters || {}
    const selectedIds: string[] = filters.selected_cliente_ids || []
    const excludedIds: string[] = filters.excluded_cliente_ids || []

    const clientesComStatus = (clientes || []).map((cliente) => ({
      ...cliente,
      na_campanha:
        selectedIds.includes(cliente.id) ||
        (!selectedIds.length && !excludedIds.includes(cliente.id)),
    }))

    return NextResponse.json({
      clientes: clientesComStatus,
    })
  } catch (error) {
    console.error('Erro ao buscar medicos:', error)
    return NextResponse.json({ detail: 'Erro interno do servidor' }, { status: 500 })
  }
}
