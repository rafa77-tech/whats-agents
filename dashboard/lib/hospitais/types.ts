/**
 * Tipos centralizados para o módulo de hospitais
 */

// ============================================
// Entidades do banco
// ============================================

export interface Hospital {
  id: string
  nome: string
  cidade: string
  ativo?: boolean
  vagas_abertas?: number
}

export interface HospitalBloqueado {
  id: string
  hospital_id: string
  motivo: string
  bloqueado_por: string
  bloqueado_em: string
  status: 'bloqueado' | 'desbloqueado'
  desbloqueado_em?: string
  desbloqueado_por?: string
  vagas_movidas?: number
  hospitais?: {
    nome: string
    cidade: string
  }
}

// ============================================
// Requests da API
// ============================================

export interface BloquearHospitalRequest {
  hospital_id: string
  motivo: string
}

export interface DesbloquearHospitalRequest {
  hospital_id: string
}

// ============================================
// Responses da API
// ============================================

export interface BloquearHospitalResponse {
  success: boolean
  vagas_movidas: number
}

export interface DesbloquearHospitalResponse {
  success: boolean
  vagas_restauradas: number
}

// ============================================
// Parâmetros de consulta
// ============================================

export interface ListarBloqueadosParams {
  incluirHistorico?: boolean
}

export interface ListarHospitaisParams {
  excluirBloqueados?: boolean
  search?: string
  apenasRevisados?: boolean
  limit?: number
}

// ============================================
// Resultados do repository
// ============================================

export interface BloquearResult {
  success: boolean
  vagas_movidas: number
}

export interface DesbloquearResult {
  success: boolean
  vagas_restauradas: number
}

export interface VerificarHospitalResult {
  existe: boolean
  hospital?: {
    id: string
    nome: string
  }
}

export interface VerificarBloqueioResult {
  bloqueado: boolean
  bloqueio?: HospitalBloqueado
}

// ============================================
// Gestão de hospitais (Sprint 60 - Épico 5)
// ============================================

export interface HospitalDetalhado {
  id: string
  nome: string
  cidade: string
  estado: string
  criado_automaticamente: boolean
  precisa_revisao: boolean
  created_at: string
  vagas_count: number
  aliases: HospitalAlias[]
}

export interface HospitalAlias {
  id: string
  hospital_id: string
  alias: string
  alias_normalizado: string
  origem: string
  confianca: number
  confirmado: boolean
  created_at: string
}

export interface ListarHospitaisGestaoParams {
  page?: number
  perPage?: number
  search?: string
  status?: 'todos' | 'revisados' | 'pendentes'
  cidade?: string
}

export interface HospitaisGestaoResponse {
  data: HospitalGestaoItem[]
  total: number
  pages: number
  pendentes: number
  auto_criados: number
}

export interface HospitalGestaoItem {
  id: string
  nome: string
  cidade: string
  estado: string
  criado_automaticamente: boolean
  precisa_revisao: boolean
  created_at: string
  vagas_count: number
  aliases_count: number
}

export interface MergeResult {
  principal_id: string
  duplicado_id: string
  duplicado_nome: string
  vagas_migradas: number
  aliases_migrados: number
}
