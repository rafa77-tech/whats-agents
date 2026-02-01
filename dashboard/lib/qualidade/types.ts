/**
 * Tipos para o modulo de Qualidade
 */

// =============================================================================
// Enums e tipos literais
// =============================================================================

/**
 * Status de uma sugestao de prompt
 */
export type SuggestionStatus = 'pending' | 'approved' | 'rejected' | 'implemented'

/**
 * Tipo de sugestao de prompt
 */
export type SuggestionType = 'tom' | 'resposta' | 'abertura' | 'objecao'

/**
 * Remetente de uma mensagem
 */
export type MessageSender = 'julia' | 'medico'

/**
 * Cores disponiveis para metric cards
 */
export type MetricCardColor = 'green' | 'yellow' | 'blue' | 'red'

/**
 * Filtro de conversas avaliadas
 */
export type ConversationFilter = 'all' | 'true' | 'false'

// =============================================================================
// Interfaces de dados
// =============================================================================

/**
 * Metricas de qualidade da pagina principal
 */
export interface QualityMetrics {
  avaliadas: number
  pendentes: number
  scoreMedio: number
  validacaoTaxa: number
  validacaoFalhas: number
  padroesViolados: PatternViolation[]
}

/**
 * Violacao de padrao detectada pelo validador
 */
export interface PatternViolation {
  padrao: string
  count: number
}

/**
 * Conversa para listagem
 */
export interface Conversation {
  id: string
  medicoNome: string
  mensagens: number
  status: string
  avaliada: boolean
  criadaEm: string
}

/**
 * Mensagem de uma conversa
 */
export interface Message {
  id: string
  remetente: MessageSender
  conteudo: string
  criadaEm: string
}

/**
 * Detalhes completos de uma conversa
 */
export interface ConversationDetail {
  id: string
  medicoNome: string
  mensagens: Message[]
}

/**
 * Sugestao de melhoria de prompt
 */
export interface Suggestion {
  id: string
  tipo: SuggestionType
  descricao: string
  status: SuggestionStatus
  exemplos?: string
  criadaEm: string
}

/**
 * Avaliacao de uma conversa
 */
export interface ConversationRatings {
  naturalidade: number
  persona: number
  objetivo: number
  satisfacao: number
}

/**
 * Payload para criar avaliacao
 */
export interface CreateEvaluationPayload {
  conversa_id: string
  naturalidade: number
  persona: number
  objetivo: number
  satisfacao: number
  observacoes: string
}

/**
 * Payload para criar sugestao
 */
export interface CreateSuggestionPayload {
  tipo: SuggestionType
  descricao: string
  exemplos?: string
}

/**
 * Payload para atualizar status de sugestao
 */
export interface UpdateSuggestionPayload {
  status: SuggestionStatus
}

// =============================================================================
// Interfaces de resposta da API (snake_case do backend)
// =============================================================================

/**
 * Resposta da API de metricas de performance
 */
export interface PerformanceMetricsResponse {
  avaliadas?: number
  pendentes?: number
  score_medio?: number
}

/**
 * Resposta da API de metricas de validacao
 */
export interface ValidationMetricsResponse {
  taxa_sucesso?: number
  falhas?: number
  padroes_violados?: Array<{ padrao: string; count: number }>
}

/**
 * Resposta da API de conversas
 */
export interface ConversationsResponse {
  conversas?: Array<{
    id: string
    medico_nome?: string | null
    total_mensagens?: number | null
    status: string
    avaliada: boolean
    criada_em: string
  }>
}

/**
 * Resposta da API de detalhes de conversa
 */
export interface ConversationDetailResponse {
  id: string
  medico_nome?: string
  interacoes?: Array<{
    id: string
    remetente: MessageSender
    conteudo: string
    criada_em: string
  }>
}

/**
 * Resposta da API de sugestoes
 */
export interface SuggestionsResponse {
  sugestoes?: Array<{
    id: string
    tipo: string
    descricao: string
    status: string
    exemplos?: string
    criada_em: string
  }>
}

// =============================================================================
// Interfaces de props de componentes
// =============================================================================

/**
 * Props do QualityMetricCard
 */
export interface QualityMetricCardProps {
  title: string
  value: number
  suffix?: string
  icon: React.ComponentType<{ className?: string | undefined }>
  color: MetricCardColor
}

/**
 * Props do EvaluateConversationModal
 */
export interface EvaluateConversationModalProps {
  conversationId: string
  onClose: () => void
}

/**
 * Props do NewSuggestionModal
 */
export interface NewSuggestionModalProps {
  onClose: () => void
  onCreated: () => void
}

/**
 * Props do RatingInput (componente interno)
 */
export interface RatingInputProps {
  label: string
  value: number
  onChange: (value: number) => void
}

// =============================================================================
// Interfaces de retorno de hooks
// =============================================================================

/**
 * Retorno do hook useQualidadeMetrics
 */
export interface UseQualidadeMetricsReturn {
  metrics: QualityMetrics | null
  loading: boolean
  error: string | null
  refresh: () => Promise<void>
}

/**
 * Retorno do hook useConversations
 */
export interface UseConversationsReturn {
  conversations: Conversation[]
  loading: boolean
  error: string | null
  refresh: () => Promise<void>
}

/**
 * Retorno do hook useSuggestions
 */
export interface UseSuggestionsReturn {
  suggestions: Suggestion[]
  loading: boolean
  error: string | null
  refresh: () => Promise<void>
  updateStatus: (id: string, status: SuggestionStatus) => Promise<void>
  create: (payload: CreateSuggestionPayload) => Promise<void>
  actionLoading: string | null
}

/**
 * Retorno do hook useConversationDetail
 */
export interface UseConversationDetailReturn {
  conversation: ConversationDetail | null
  loading: boolean
  error: string | null
  saveEvaluation: (ratings: ConversationRatings, observacoes: string) => Promise<void>
  saving: boolean
}
