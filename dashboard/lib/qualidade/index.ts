/**
 * Modulo de Qualidade - Exports publicos
 */

// Types
export type {
  // Enums e literais
  SuggestionStatus,
  SuggestionType,
  MessageSender,
  MetricCardColor,
  ConversationFilter,
  // Interfaces de dados
  QualityMetrics,
  PatternViolation,
  Conversation,
  Message,
  ConversationDetail,
  Suggestion,
  ConversationRatings,
  CreateEvaluationPayload,
  CreateSuggestionPayload,
  UpdateSuggestionPayload,
  // Props de componentes
  QualityMetricCardProps,
  EvaluateConversationModalProps,
  NewSuggestionModalProps,
  RatingInputProps,
  // Retornos de hooks
  UseQualidadeMetricsReturn,
  UseConversationsReturn,
  UseSuggestionsReturn,
  UseConversationDetailReturn,
} from './types'

// Constants
export {
  // Limites
  CONVERSATIONS_FETCH_LIMIT,
  MAX_RATING_STARS,
  MAX_PATTERNS_DISPLAYED,
  // Opcoes
  SUGGESTION_TYPES,
  CONVERSATION_FILTER_OPTIONS,
  SUGGESTION_STATUS_FILTER_OPTIONS,
  EVALUATION_CRITERIA,
  // Cores
  METRIC_CARD_COLORS,
  SUGGESTION_STATUS_COLORS,
  SUGGESTION_STATUS_LABELS,
  SUGGESTION_TYPE_COLORS,
  // Defaults
  DEFAULT_METRICS,
  DEFAULT_RATINGS,
  // Endpoints
  API_ENDPOINTS,
} from './constants'

// Formatters
export {
  // Parsers
  parseMetricsResponse,
  parseConversationsResponse,
  parseConversationDetailResponse,
  parseMessagesResponse,
  parseSuggestionsResponse,
  // Formatadores de data
  formatDateBR,
  formatTimeBR,
  formatDateTimeBR,
  // Formatadores de ID
  formatShortId,
  // Validadores
  isRatingsComplete,
  canCreateSuggestion,
  // Builders de URL
  buildConversationsUrl,
  buildSuggestionsUrl,
  // Calculadores
  calculateFailureRate,
  calculateAverageRating,
} from './formatters'

// Hooks
export {
  useQualidadeMetrics,
  useConversations,
  useConversationDetail,
  useSuggestions,
} from './hooks'

// Schemas
export {
  // Schemas
  conversationsQuerySchema,
  suggestionsQuerySchema,
  createEvaluationSchema,
  createSuggestionSchema,
  updateSuggestionSchema,
  // Constants
  VALID_SUGGESTION_STATUSES,
  VALID_SUGGESTION_TYPES,
  VALID_CONVERSATION_FILTERS,
  // Parsers
  parseConversationsQuery,
  parseSuggestionsQuery,
  parseCreateEvaluationBody,
  parseCreateSuggestionBody,
  parseUpdateSuggestionBody,
  // Types
  type ConversationsQueryParams,
  type SuggestionsQueryParams,
  type CreateEvaluationBody,
  type CreateSuggestionBody,
  type UpdateSuggestionBody,
} from './schemas'
