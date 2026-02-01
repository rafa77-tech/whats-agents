/**
 * Modulo de Instrucoes (Diretrizes)
 *
 * Exports publicos para uso em componentes e paginas
 */

// Types
export type {
  TipoDiretriz,
  Escopo,
  DiretrizStatus,
  DiretrizConteudo,
  Diretriz,
  Hospital,
  Especialidade,
  DiretrizFilters,
  NovaInstrucaoDialogProps,
  DiretrizesTableProps,
  CriarDiretrizPayload,
  CancelarDiretrizPayload,
  UseInstrucoesReturn,
  UseNovaInstrucaoReturn,
  EscopoIconMap,
  TipoLabelMap,
  SelectOption,
} from './types'

// Constants
export {
  ESCOPO_ICONS,
  TIPO_LABELS,
  ESCOPO_LABELS,
  TIPO_OPTIONS,
  ESCOPO_OPTIONS,
  API_ENDPOINTS,
  DEFAULT_STATUS_ATIVAS,
  DEFAULT_STATUS_HISTORICO,
  DEFAULT_TIPO,
  DEFAULT_ESCOPO,
} from './constants'

// Schemas
export {
  tipoDiretrizSchema,
  escopoSchema,
  statusSchema,
  diretrizConteudoSchema,
  diretrizesQuerySchema,
  parseDiretrizesQuery,
  criarDiretrizSchema,
  cancelarDiretrizSchema,
  diretrizSchema,
} from './schemas'

export type {
  TipoDiretrizEnum,
  EscopoEnum,
  StatusEnum,
  CriarDiretrizInput,
  CancelarDiretrizInput,
  DiretrizFromSchema,
} from './schemas'

// Formatters
export {
  formatRelativeDate,
  formatExpirationDate,
  formatVagaDate,
  isExpired,
  getTipoLabel,
  getEscopoIcon,
  getEscopoBaseLabel,
  getEscopoLabel,
  formatCurrency,
  getConteudoLabel,
  buildDiretrizesUrl,
  buildDiretrizUrl,
} from './formatters'

// Hooks
export {
  useInstrucoes,
  useNovaInstrucao,
  useInstrucaoForm,
} from './hooks'

export type { InstrucaoFormState } from './hooks'
