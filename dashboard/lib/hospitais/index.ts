/**
 * Módulo de hospitais
 * Centraliza tipos e funções de acesso a dados
 */

// Types
export type {
  Hospital,
  HospitalBloqueado,
  HospitalDetalhado,
  HospitalAlias,
  HospitalSetor,
  HospitalVaga,
  HospitalGestaoItem,
  HospitaisGestaoResponse,
  BloquearHospitalRequest,
  DesbloquearHospitalRequest,
  BloquearHospitalResponse,
  DesbloquearHospitalResponse,
  ListarBloqueadosParams,
  ListarHospitaisParams,
  ListarHospitaisGestaoParams,
  BloquearResult,
  DesbloquearResult,
  VerificarHospitalResult,
  VerificarBloqueioResult,
  MergeResult,
} from './types'

// Repository
export {
  listarHospitaisBloqueados,
  listarHospitais,
  listarHospitaisGestao,
  buscarHospitalDetalhado,
  atualizarHospital,
  adicionarAlias,
  removerAlias,
  mesclarHospitais,
  deletarHospitalSeguro,
  buscarDuplicados,
  verificarHospitalExiste,
  verificarHospitalBloqueado,
  contarVagasAbertas,
  contarVagasBloqueadas,
  bloquearHospital,
  desbloquearHospital,
  registrarAuditLog,
} from './repository'
