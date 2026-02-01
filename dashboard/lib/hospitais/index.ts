/**
 * Módulo de hospitais
 * Centraliza tipos e funções de acesso a dados
 */

// Types
export type {
  Hospital,
  HospitalBloqueado,
  BloquearHospitalRequest,
  DesbloquearHospitalRequest,
  BloquearHospitalResponse,
  DesbloquearHospitalResponse,
  ListarBloqueadosParams,
  ListarHospitaisParams,
  BloquearResult,
  DesbloquearResult,
  VerificarHospitalResult,
  VerificarBloqueioResult,
} from './types'

// Repository
export {
  listarHospitaisBloqueados,
  listarHospitais,
  verificarHospitalExiste,
  verificarHospitalBloqueado,
  contarVagasAbertas,
  contarVagasBloqueadas,
  bloquearHospital,
  desbloquearHospital,
  registrarAuditLog,
} from './repository'
