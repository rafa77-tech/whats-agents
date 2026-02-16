/**
 * Repository para acesso a dados de hospitais no Supabase
 */

import type { SupabaseClient } from '@supabase/supabase-js'
import type {
  Hospital,
  HospitalBloqueado,
  ListarBloqueadosParams,
  ListarHospitaisParams,
  BloquearResult,
  DesbloquearResult,
  VerificarHospitalResult,
  VerificarBloqueioResult,
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
 * Lista hospitais ativos para seleção
 * @param excluirBloqueados - Se true, exclui hospitais atualmente bloqueados
 */
export async function listarHospitais(
  supabase: SupabaseClient,
  params: ListarHospitaisParams = {}
): Promise<Hospital[]> {
  const { excluirBloqueados = false } = params

  const { data: hospitais, error } = await supabase
    .from('hospitais')
    .select('id, nome, cidade')
    .order('nome')

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

  // Buscar contagem de vagas abertas
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
