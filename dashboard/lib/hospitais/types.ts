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
