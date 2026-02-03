/**
 * Market Intelligence Types - Sprint 46
 *
 * Tipos TypeScript para o modulo de Market Intelligence.
 * Refletem as estruturas do banco de dados e contratos de API.
 */

// =============================================================================
// ENUMS
// =============================================================================

/**
 * Periodos disponiveis para filtros de analytics
 */
export type AnalyticsPeriod = '24h' | '7d' | '30d' | '90d' | 'custom'

/**
 * Status de uma vaga no pipeline
 */
export type VagaGroupStatus =
  | 'pendente'
  | 'processando'
  | 'importada'
  | 'revisao'
  | 'descartada'
  | 'duplicada'

/**
 * Niveis de confianca para classificacao
 */
export type ConfidenceLevel = 'alta' | 'media' | 'baixa'

// =============================================================================
// ENTIDADES DO BANCO
// =============================================================================

/**
 * Snapshot diario de market intelligence
 * Tabela: market_intelligence_daily
 */
export interface MarketIntelligenceDaily {
  id: string
  data: string // ISO date string YYYY-MM-DD

  // Metricas de Volume
  gruposAtivos: number
  mensagensTotal: number
  mensagensComOferta: number
  vagasExtraidas: number
  vagasImportadas: number
  vagasDuplicadas: number
  vagasDescartadas: number

  // Taxas (0-1)
  taxaDeteccaoOferta: number | null
  taxaExtracao: number | null
  taxaImportacao: number | null
  taxaDuplicatas: number | null

  // Qualidade (0-1)
  confiancaMediaExtracao: number | null
  confiancaMediaMatch: number | null

  // Valor (em centavos)
  valorMedioPlantao: number | null
  valorMedianoPlantao: number | null
  valorMinimoPlantao: number | null
  valorMaximoPlantao: number | null

  // Metadata
  createdAt: string
  updatedAt: string
}

/**
 * Ranking de grupo
 * View: mv_grupos_ranking
 */
export interface GrupoRanking {
  grupoId: string
  grupoNome: string
  grupoTipo: string | null
  grupoRegiao: string | null
  grupoAtivo: boolean

  // Metricas 30 dias
  mensagens30d: number
  ofertas30d: number
  vagasExtraidas30d: number
  vagasImportadas30d: number

  // Qualidade
  confiancaMedia30d: number | null
  valorMedio30d: number | null
  scoreQualidade: number // 0-100

  // Timestamps
  ultimaMensagemEm: string | null
  ultimaVagaEm: string | null
  calculatedAt: string
}

/**
 * Metricas do pipeline por dia
 * View: mv_pipeline_metrics
 */
export interface PipelineMetrics {
  data: string // ISO date string YYYY-MM-DD

  // Etapa 1: Mensagens
  mensagensTotal: number
  mensagensProcessadas: number
  mensagensPassouHeuristica: number
  mensagensEhOferta: number

  // Etapa 2: Vagas Extraidas
  vagasExtraidas: number
  vagasDadosOk: number
  vagasDuplicadas: number

  // Etapa 3: Vagas Importadas
  vagasImportadas: number
  vagasRevisao: number
  vagasDescartadas: number

  // Confianca
  confiancaClassificacaoMedia: number | null
  confiancaExtracaoMedia: number | null

  calculatedAt: string
}

// =============================================================================
// API REQUESTS
// =============================================================================

/**
 * Parametros para API de overview
 */
export interface MarketOverviewParams {
  period: AnalyticsPeriod
  startDate?: string // ISO date, requerido se period === 'custom'
  endDate?: string // ISO date, requerido se period === 'custom'
}

/**
 * Parametros para API de volume
 */
export interface MarketVolumeParams {
  period: AnalyticsPeriod
  startDate?: string
  endDate?: string
  groupBy?: 'day' | 'week' | 'month'
}

/**
 * Parametros para API de pipeline
 */
export interface MarketPipelineParams {
  period: AnalyticsPeriod
  startDate?: string
  endDate?: string
}

/**
 * Parametros para API de ranking de grupos
 */
export interface GroupsRankingParams {
  limit?: number // default: 20, max: 100
  offset?: number // default: 0
  sortBy?: 'score' | 'vagas' | 'mensagens' | 'valor'
  order?: 'asc' | 'desc'
  apenasAtivos?: boolean
}

// =============================================================================
// API RESPONSES
// =============================================================================

/**
 * Response da API de overview
 */
export interface MarketOverviewResponse {
  periodo: {
    inicio: string
    fim: string
    dias: number
  }

  kpis: {
    gruposAtivos: KPIMetric
    vagasPorDia: KPIMetric
    taxaConversao: KPIMetric
    valorMedio: KPIMetric
  }

  resumo: {
    totalMensagens: number
    totalOfertas: number
    totalVagasExtraidas: number
    totalVagasImportadas: number
  }

  updatedAt: string
}

/**
 * Metrica de KPI com variacao
 */
export interface KPIMetric {
  valor: number
  valorFormatado: string
  variacao: number | null // percentual vs periodo anterior
  variacaoTipo: 'up' | 'down' | 'stable' | null
  tendencia: number[] // ultimos N valores para sparkline
}

/**
 * Response da API de volume
 */
export interface MarketVolumeResponse {
  periodo: {
    inicio: string
    fim: string
  }

  series: VolumeSeries[]

  totais: {
    mensagens: number
    ofertas: number
    vagasExtraidas: number
    vagasImportadas: number
  }

  updatedAt: string
}

/**
 * Serie temporal de volume
 */
export interface VolumeSeries {
  data: string
  mensagens: number
  ofertas: number
  vagasExtraidas: number
  vagasImportadas: number
}

/**
 * Ponto de dados de volume (alias para VolumeSeries)
 */
export type VolumeDataPoint = VolumeSeries

/**
 * Response completa da API de volume (com medias e dias)
 */
export interface VolumeResponse {
  periodo: {
    inicio: string
    fim: string
    dias: number
  }

  dados: VolumeDataPoint[]

  totais: {
    mensagens: number
    ofertas: number
    vagasExtraidas: number
    vagasImportadas: number
  }

  medias: {
    mensagensPorDia: number
    ofertasPorDia: number
    vagasExtraidasPorDia: number
    vagasImportadasPorDia: number
  }

  updatedAt: string
}

/**
 * Response da API de pipeline
 */
export interface MarketPipelineResponse {
  periodo: {
    inicio: string
    fim: string
  }

  funil: PipelineFunnelStep[]

  taxas: {
    deteccaoOferta: number
    extracao: number
    importacao: number
    descarte: number
    duplicatas: number
  }

  qualidade: {
    confiancaClassificacao: number
    confiancaExtracao: number
  }

  updatedAt: string
}

/**
 * Etapa do funil do pipeline
 */
export interface PipelineFunnelStep {
  id: string
  nome: string
  valor: number
  percentual: number // em relacao ao total inicial
  percentualAnterior: number // em relacao a etapa anterior
  cor: string // cor para visualizacao
}

/**
 * Etapa do funil simplificada (sem cor e percentualAnterior)
 */
export interface PipelineEtapa {
  id: string
  nome: string
  valor: number
  percentual: number
}

/**
 * Taxas de conversao do pipeline
 */
export interface PipelineConversoes {
  mensagemParaOferta: number
  ofertaParaExtracao: number
  extracaoParaImportacao: number
  totalPipeline: number
}

/**
 * Perdas do pipeline
 */
export interface PipelinePerdas {
  duplicadas: number
  descartadas: number
  revisao: number
  semDadosMinimos: number
}

/**
 * Estrutura do funil do pipeline (extraida da response)
 */
export interface PipelineFunil {
  etapas: PipelineEtapa[]
  conversoes: PipelineConversoes
}

/**
 * Response completa da API de pipeline
 */
export interface PipelineResponse {
  periodo: {
    inicio: string
    fim: string
    dias: number
  }

  funil: {
    etapas: PipelineEtapa[]
    conversoes: PipelineConversoes
  }

  perdas: PipelinePerdas

  qualidade: {
    confiancaClassificacaoMedia: number | null
    confiancaExtracaoMedia: number | null
  }

  updatedAt: string
}

/**
 * Response da API de ranking de grupos
 */
export interface GroupsRankingResponse {
  grupos: GrupoRanking[]
  total: number
  limit: number
  offset: number
  updatedAt: string
}

// =============================================================================
// COMPONENTES
// =============================================================================

/**
 * Props para KPICard
 */
export interface KPICardProps {
  titulo: string
  valor: string | number
  valorFormatado?: string
  subtitulo?: string
  icone: React.ReactNode
  variacao?: number | null
  variacaoTipo?: 'up' | 'down' | 'stable' | null
  tendencia?: number[]
  status?: 'success' | 'warning' | 'danger' | 'neutral'
  loading?: boolean
  className?: string
}

/**
 * Props para VolumeChart
 */
export interface VolumeChartProps {
  dados: VolumeSeries[]
  periodo: AnalyticsPeriod
  loading?: boolean
  altura?: number
  mostrarLegenda?: boolean
  seriesVisiveis?: ('mensagens' | 'ofertas' | 'vagasExtraidas' | 'vagasImportadas')[]
  className?: string
}

/**
 * Props para PipelineFunnel
 */
export interface PipelineFunnelProps {
  etapas: PipelineFunnelStep[]
  loading?: boolean
  orientacao?: 'horizontal' | 'vertical'
  mostrarPercentuais?: boolean
  className?: string
}

/**
 * Props para GroupsRanking
 */
export interface GroupsRankingProps {
  grupos: GrupoRanking[]
  total: number
  loading?: boolean
  onLoadMore?: () => void
  onGroupClick?: (grupo: GrupoRanking) => void
  className?: string
}

// =============================================================================
// TYPE GUARDS
// =============================================================================

/**
 * Verifica se o valor e um AnalyticsPeriod valido
 */
export function isAnalyticsPeriod(value: unknown): value is AnalyticsPeriod {
  return typeof value === 'string' && ['24h', '7d', '30d', '90d', 'custom'].includes(value)
}

/**
 * Verifica se o valor e um VagaGroupStatus valido
 */
export function isVagaGroupStatus(value: unknown): value is VagaGroupStatus {
  return (
    typeof value === 'string' &&
    ['pendente', 'processando', 'importada', 'revisao', 'descartada', 'duplicada'].includes(value)
  )
}

/**
 * Verifica se o objeto e uma KPIMetric valida
 */
export function isKPIMetric(obj: unknown): obj is KPIMetric {
  if (typeof obj !== 'object' || obj === null) return false
  const metric = obj as Record<string, unknown>
  return (
    typeof metric.valor === 'number' &&
    typeof metric.valorFormatado === 'string' &&
    Array.isArray(metric.tendencia)
  )
}

// =============================================================================
// UTILITARIOS
// =============================================================================

/**
 * Converte snake_case do banco para camelCase
 */
export type SnakeToCamelCase<S extends string> = S extends `${infer T}_${infer U}`
  ? `${T}${Capitalize<SnakeToCamelCase<U>>}`
  : S

/**
 * Converte todas as keys de um objeto de snake_case para camelCase
 */
export type KeysToCamelCase<T> = {
  [K in keyof T as SnakeToCamelCase<string & K>]: T[K] extends object ? KeysToCamelCase<T[K]> : T[K]
}

/**
 * Tipo para resposta de API com erro
 */
export interface APIError {
  error: string
  message: string
  details?: Record<string, unknown>
}

/**
 * Tipo para resposta de API generica
 */
export type APIResponse<T> = T | APIError

/**
 * Type guard para verificar se e um erro de API
 */
export function isAPIError(response: unknown): response is APIError {
  if (typeof response !== 'object' || response === null) return false
  const obj = response as Record<string, unknown>
  return typeof obj.error === 'string' && typeof obj.message === 'string'
}
