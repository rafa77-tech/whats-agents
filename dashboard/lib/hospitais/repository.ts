/**
 * Repository para acesso a dados de hospitais no Supabase
 */

import type { SupabaseClient } from '@supabase/supabase-js'
import type {
  Hospital,
  HospitalBloqueado,
  HospitalDetalhado,
  HospitalAlias,
  HospitalSetor,
  HospitalVaga,
  HospitalGestaoItem,
  HospitaisGestaoResponse,
  ListarBloqueadosParams,
  ListarHospitaisParams,
  ListarHospitaisGestaoParams,
  BloquearResult,
  DesbloquearResult,
  VerificarHospitalResult,
  VerificarBloqueioResult,
  MergeResult,
} from './types'

// ============================================
// Consultas de leitura
// ============================================

/**
 * Lista hospitais bloqueados
 * @param incluirHistorico - Se true, inclui registros desbloqueados
 */
export async function listarHospitaisBloqueados(
  supabase: SupabaseClient,
  params: ListarBloqueadosParams = {}
): Promise<HospitalBloqueado[]> {
  const { incluirHistorico = false } = params

  let query = supabase
    .from('hospitais_bloqueados')
    .select(
      `
      id,
      hospital_id,
      motivo,
      bloqueado_por,
      bloqueado_em,
      status,
      desbloqueado_em,
      desbloqueado_por,
      vagas_movidas,
      hospitais (
        nome,
        cidade
      )
    `
    )
    .order('bloqueado_em', { ascending: false })

  if (!incluirHistorico) {
    query = query.eq('status', 'bloqueado')
  }

  const { data, error } = await query

  if (error) {
    throw new Error(`Erro ao buscar hospitais bloqueados: ${error.message}`)
  }

  return (data || []) as unknown as HospitalBloqueado[]
}

/**
 * Lista hospitais para seleção com busca server-side
 * @param params.excluirBloqueados - Exclui hospitais atualmente bloqueados
 * @param params.search - Busca por nome (ilike)
 * @param params.apenasRevisados - Filtra apenas hospitais revisados (default: false)
 * @param params.limit - Limita resultados (default: sem limite)
 */
export async function listarHospitais(
  supabase: SupabaseClient,
  params: ListarHospitaisParams = {}
): Promise<Hospital[]> {
  const { excluirBloqueados = false, search, apenasRevisados = false, limit = 0 } = params

  let query = supabase.from('hospitais').select('id, nome, cidade').order('nome')

  if (apenasRevisados) {
    query = query.eq('precisa_revisao', false)
  }

  if (search) {
    query = query.ilike('nome', `%${search}%`)
  }

  if (limit > 0) {
    query = query.limit(limit)
  }

  const { data: hospitais, error } = await query

  if (error) {
    throw new Error(`Erro ao buscar hospitais: ${error.message}`)
  }

  let resultado = hospitais || []

  if (excluirBloqueados) {
    const { data: bloqueados } = await supabase
      .from('hospitais_bloqueados')
      .select('hospital_id')
      .eq('status', 'bloqueado')

    const idsBloqueados = new Set((bloqueados || []).map((b) => b.hospital_id))
    resultado = resultado.filter((h) => !idsBloqueados.has(h.id))
  }

  // Skip vagas count when doing server-side search (not needed for dropdown)
  if (search || limit > 0) {
    return resultado
  }

  // Buscar contagem de vagas abertas (full list mode)
  const { data: vagasCount } = await supabase
    .from('vagas')
    .select('hospital_id')
    .eq('status', 'aberta')

  const vagasPorHospital = new Map<string, number>()
  ;(vagasCount || []).forEach((v) => {
    const count = vagasPorHospital.get(v.hospital_id) || 0
    vagasPorHospital.set(v.hospital_id, count + 1)
  })

  return resultado.map((h) => ({
    ...h,
    vagas_abertas: vagasPorHospital.get(h.id) || 0,
  }))
}

// ============================================
// Verificações
// ============================================

/**
 * Verifica se um hospital existe
 */
export async function verificarHospitalExiste(
  supabase: SupabaseClient,
  hospitalId: string
): Promise<VerificarHospitalResult> {
  const { data: hospital, error } = await supabase
    .from('hospitais')
    .select('id, nome')
    .eq('id', hospitalId)
    .single()

  if (error || !hospital) {
    return { existe: false }
  }

  return { existe: true, hospital }
}

/**
 * Verifica se um hospital está bloqueado
 */
export async function verificarHospitalBloqueado(
  supabase: SupabaseClient,
  hospitalId: string
): Promise<VerificarBloqueioResult> {
  const { data: bloqueio } = await supabase
    .from('hospitais_bloqueados')
    .select('*')
    .eq('hospital_id', hospitalId)
    .eq('status', 'bloqueado')
    .single()

  if (!bloqueio) {
    return { bloqueado: false }
  }

  return { bloqueado: true, bloqueio: bloqueio as HospitalBloqueado }
}

/**
 * Conta vagas abertas de um hospital
 */
export async function contarVagasAbertas(
  supabase: SupabaseClient,
  hospitalId: string
): Promise<number> {
  const { count } = await supabase
    .from('vagas')
    .select('id', { count: 'exact', head: true })
    .eq('hospital_id', hospitalId)
    .eq('status', 'aberta')

  return count || 0
}

/**
 * Conta vagas bloqueadas de um hospital
 */
export async function contarVagasBloqueadas(
  supabase: SupabaseClient,
  hospitalId: string
): Promise<number> {
  const { count } = await supabase
    .from('vagas')
    .select('id', { count: 'exact', head: true })
    .eq('hospital_id', hospitalId)
    .eq('status', 'bloqueada')

  return count || 0
}

// ============================================
// Operações de escrita
// ============================================

/**
 * Bloqueia um hospital
 * - Cria registro de bloqueio
 * - Atualiza status das vagas abertas para 'bloqueada'
 * - Registra no audit_log
 */
export async function bloquearHospital(
  supabase: SupabaseClient,
  hospitalId: string,
  motivo: string,
  userEmail: string
): Promise<BloquearResult> {
  // Contar vagas que serão afetadas
  const vagasMovidas = await contarVagasAbertas(supabase, hospitalId)

  // Criar registro de bloqueio
  const { error: insertError } = await supabase.from('hospitais_bloqueados').insert({
    hospital_id: hospitalId,
    motivo,
    bloqueado_por: userEmail,
    bloqueado_em: new Date().toISOString(),
    status: 'bloqueado',
    vagas_movidas: vagasMovidas,
  })

  if (insertError) {
    throw new Error(`Erro ao bloquear hospital: ${insertError.message}`)
  }

  // Mover vagas para status "bloqueada"
  if (vagasMovidas > 0) {
    const { error: updateError } = await supabase
      .from('vagas')
      .update({ status: 'bloqueada' })
      .eq('hospital_id', hospitalId)
      .eq('status', 'aberta')

    if (updateError) {
      throw new Error(`Erro ao atualizar vagas: ${updateError.message}`)
    }
  }

  return { success: true, vagas_movidas: vagasMovidas }
}

/**
 * Desbloqueia um hospital
 * - Atualiza registro de bloqueio para 'desbloqueado'
 * - Restaura vagas bloqueadas para 'aberta'
 * - Registra no audit_log
 */
export async function desbloquearHospital(
  supabase: SupabaseClient,
  hospitalId: string,
  bloqueioId: string,
  userEmail: string
): Promise<DesbloquearResult> {
  // Atualizar status para desbloqueado
  const { error: updateError } = await supabase
    .from('hospitais_bloqueados')
    .update({
      status: 'desbloqueado',
      desbloqueado_em: new Date().toISOString(),
      desbloqueado_por: userEmail,
    })
    .eq('id', bloqueioId)

  if (updateError) {
    throw new Error(`Erro ao desbloquear hospital: ${updateError.message}`)
  }

  // Contar vagas que serão restauradas
  const vagasRestauradas = await contarVagasBloqueadas(supabase, hospitalId)

  // Restaurar vagas bloqueadas para "aberta"
  if (vagasRestauradas > 0) {
    const { error: vagasError } = await supabase
      .from('vagas')
      .update({ status: 'aberta' })
      .eq('hospital_id', hospitalId)
      .eq('status', 'bloqueada')

    if (vagasError) {
      throw new Error(`Erro ao restaurar vagas: ${vagasError.message}`)
    }
  }

  return { success: true, vagas_restauradas: vagasRestauradas }
}

// ============================================
// Auditoria
// ============================================

/**
 * Registra ação no audit_log
 */
export async function registrarAuditLog(
  supabase: SupabaseClient,
  action: string,
  userEmail: string,
  details: Record<string, unknown>
): Promise<void> {
  await supabase.from('audit_log').insert({
    action,
    user_email: userEmail,
    details,
    created_at: new Date().toISOString(),
  })
}

// ============================================
// Gestão de Hospitais (Sprint 60 - Épico 5)
// ============================================

/**
 * Lista hospitais para a página de gestão com paginação e filtros
 */
export async function listarHospitaisGestao(
  supabase: SupabaseClient,
  params: ListarHospitaisGestaoParams = {}
): Promise<HospitaisGestaoResponse> {
  const {
    page = 1,
    perPage = 20,
    search,
    status = 'todos',
    cidade,
    criadoAutomaticamente,
  } = params

  const from = (page - 1) * perPage
  const to = from + perPage - 1

  let query = supabase
    .from('hospitais')
    .select('id, nome, cidade, estado, criado_automaticamente, precisa_revisao, created_at', {
      count: 'exact',
    })
    .order('created_at', { ascending: false })

  if (search) {
    query = query.ilike('nome', `%${search}%`)
  }

  if (status === 'revisados') {
    query = query.eq('precisa_revisao', false)
  } else if (status === 'pendentes') {
    query = query.eq('precisa_revisao', true)
  }

  if (cidade) {
    query = query.ilike('cidade', `%${cidade}%`)
  }

  if (criadoAutomaticamente !== undefined) {
    query = query.eq('criado_automaticamente', criadoAutomaticamente)
  }

  query = query.range(from, to)

  const { data: hospitais, error, count } = await query

  if (error) {
    throw new Error(`Erro ao buscar hospitais: ${error.message}`)
  }

  const total = count || 0
  const ids = (hospitais || []).map((h) => h.id)

  // Fetch vagas count and aliases count for these hospitals
  const vagasPorHospital = new Map<string, number>()
  const aliasesPorHospital = new Map<string, number>()

  if (ids.length > 0) {
    const { data: vagasData } = await supabase
      .from('vagas')
      .select('hospital_id')
      .in('hospital_id', ids)

    ;(vagasData || []).forEach((v) => {
      vagasPorHospital.set(v.hospital_id, (vagasPorHospital.get(v.hospital_id) || 0) + 1)
    })

    const { data: aliasesData } = await supabase
      .from('hospitais_alias')
      .select('hospital_id')
      .in('hospital_id', ids)

    ;(aliasesData || []).forEach((a) => {
      aliasesPorHospital.set(a.hospital_id, (aliasesPorHospital.get(a.hospital_id) || 0) + 1)
    })
  }

  const data: HospitalGestaoItem[] = (hospitais || []).map((h) => ({
    ...h,
    vagas_count: vagasPorHospital.get(h.id) || 0,
    aliases_count: aliasesPorHospital.get(h.id) || 0,
  }))

  // Global counts (independent of current filters/page)
  const { count: pendentesCount } = await supabase
    .from('hospitais')
    .select('id', { count: 'exact', head: true })
    .eq('precisa_revisao', true)

  const { count: autoCriadosCount } = await supabase
    .from('hospitais')
    .select('id', { count: 'exact', head: true })
    .eq('criado_automaticamente', true)

  return {
    data,
    total,
    pages: Math.ceil(total / perPage),
    pendentes: pendentesCount || 0,
    auto_criados: autoCriadosCount || 0,
  }
}

/**
 * Busca hospital por ID com aliases e contagens
 */
export async function buscarHospitalDetalhado(
  supabase: SupabaseClient,
  hospitalId: string
): Promise<HospitalDetalhado | null> {
  const { data: hospital, error } = await supabase
    .from('hospitais')
    .select(
      'id, nome, cidade, estado, logradouro, numero, bairro, cep, latitude, longitude, endereco_formatado, criado_automaticamente, precisa_revisao, created_at'
    )
    .eq('id', hospitalId)
    .single()

  if (error || !hospital) {
    return null
  }

  const { data: aliases } = await supabase
    .from('hospitais_alias')
    .select('id, hospital_id, alias, alias_normalizado, origem, confianca, confirmado, created_at')
    .eq('hospital_id', hospitalId)
    .order('created_at', { ascending: false })

  // Fetch last 50 vagas with joins
  const { data: vagasData } = await supabase
    .from('vagas')
    .select(
      `
      id, data, hora_inicio, hora_fim, valor, status,
      especialidades (nome),
      setores (id, nome),
      periodos (nome)
    `
    )
    .eq('hospital_id', hospitalId)
    .order('data', { ascending: false })
    .limit(50)

  type VagaRow = {
    id: string
    data: string
    hora_inicio: string | null
    hora_fim: string | null
    valor: number | null
    status: string
    especialidades: { nome: string } | null
    setores: { id: string; nome: string } | null
    periodos: { nome: string } | null
  }

  const vagasRaw = (vagasData || []) as unknown as VagaRow[]

  const vagas: HospitalVaga[] = vagasRaw.map((v) => ({
    id: v.id,
    data: v.data,
    hora_inicio: v.hora_inicio,
    hora_fim: v.hora_fim,
    valor: v.valor,
    status: v.status,
    especialidade_nome: v.especialidades?.nome || null,
    setor_nome: v.setores?.nome || null,
    periodo_nome: v.periodos?.nome || null,
  }))

  // Derive setores from vagas
  const setorMap = new Map<string, { id: string; nome: string; count: number }>()
  for (const v of vagasRaw) {
    if (v.setores?.id && v.setores?.nome) {
      const existing = setorMap.get(v.setores.id)
      if (existing) {
        existing.count++
      } else {
        setorMap.set(v.setores.id, { id: v.setores.id, nome: v.setores.nome, count: 1 })
      }
    }
  }
  const setores: HospitalSetor[] = Array.from(setorMap.values()).map((s) => ({
    id: s.id,
    nome: s.nome,
    vagas_count: s.count,
  }))

  const { count: vagasCount } = await supabase
    .from('vagas')
    .select('id', { count: 'exact', head: true })
    .eq('hospital_id', hospitalId)

  return {
    ...hospital,
    vagas_count: vagasCount || 0,
    aliases: (aliases || []) as HospitalAlias[],
    setores,
    vagas,
  }
}

/**
 * Atualiza dados de um hospital
 */
export async function atualizarHospital(
  supabase: SupabaseClient,
  hospitalId: string,
  dados: {
    nome?: string
    cidade?: string
    estado?: string
    precisa_revisao?: boolean
    logradouro?: string
    numero?: string
    bairro?: string
    cep?: string
  }
): Promise<void> {
  const { error } = await supabase.from('hospitais').update(dados).eq('id', hospitalId)

  if (error) {
    throw new Error(`Erro ao atualizar hospital: ${error.message}`)
  }
}

/**
 * Adiciona alias a um hospital
 */
export async function adicionarAlias(
  supabase: SupabaseClient,
  hospitalId: string,
  alias: string,
  aliasNormalizado: string
): Promise<HospitalAlias> {
  const { data, error } = await supabase
    .from('hospitais_alias')
    .insert({
      hospital_id: hospitalId,
      alias,
      alias_normalizado: aliasNormalizado,
      origem: 'manual_dashboard',
      confianca: 1.0,
      confirmado: true,
      criado_por: 'dashboard',
    })
    .select('id, hospital_id, alias, alias_normalizado, origem, confianca, confirmado, created_at')
    .single()

  if (error) {
    throw new Error(`Erro ao adicionar alias: ${error.message}`)
  }

  return data as HospitalAlias
}

/**
 * Remove alias de um hospital
 */
export async function removerAlias(supabase: SupabaseClient, aliasId: string): Promise<void> {
  const { error } = await supabase.from('hospitais_alias').delete().eq('id', aliasId)

  if (error) {
    throw new Error(`Erro ao remover alias: ${error.message}`)
  }
}

/**
 * Mescla hospital duplicado no principal via RPC atômica
 */
export async function mesclarHospitais(
  supabase: SupabaseClient,
  principalId: string,
  duplicadoId: string,
  executadoPor: string
): Promise<MergeResult> {
  const { data, error } = await supabase.rpc('mesclar_hospitais', {
    p_principal_id: principalId,
    p_duplicado_id: duplicadoId,
    p_executado_por: executadoPor,
  })

  if (error) {
    throw new Error(`Erro ao mesclar hospitais: ${error.message}`)
  }

  return data as MergeResult
}

/**
 * Deleta hospital se não tem referências em nenhuma tabela FK
 */
export async function deletarHospitalSeguro(
  supabase: SupabaseClient,
  hospitalId: string
): Promise<boolean> {
  const { data, error } = await supabase.rpc('deletar_hospital_sem_referencias', {
    p_hospital_id: hospitalId,
  })

  if (error) {
    throw new Error(`Erro ao deletar hospital: ${error.message}`)
  }

  return data === true
}

/**
 * Busca hospitais duplicados por similaridade para um hospital
 */
export async function buscarDuplicados(
  supabase: SupabaseClient,
  hospitalId: string,
  hospitalNome: string,
  limite: number = 10
): Promise<Array<{ id: string; nome: string; cidade: string; similarity: number }>> {
  // Use pg_trgm similarity via RPC or manual query
  const { data, error } = await supabase
    .from('hospitais')
    .select('id, nome, cidade')
    .neq('id', hospitalId)
    .ilike('nome', `%${hospitalNome.split(' ').slice(0, 2).join('%')}%`)
    .limit(limite)

  if (error) {
    throw new Error(`Erro ao buscar duplicados: ${error.message}`)
  }

  return (data || []).map((h) => ({
    ...h,
    similarity: 0, // Client-side similarity would need pg_trgm RPC
  }))
}
