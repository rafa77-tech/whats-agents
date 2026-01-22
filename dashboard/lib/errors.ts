/**
 * API Error Messages - Sprint 34 E01
 *
 * Centralized error message mapping for user-friendly feedback.
 */

export interface ErrorAction {
  label: string
  href?: string
  onClick?: 'retry' | 'focus-filters' | 'close'
}

export interface ErrorConfig {
  message: string
  action?: ErrorAction
  duration?: number
}

/**
 * Maps API error codes to user-friendly messages and actions.
 */
export const API_ERROR_MESSAGES: Record<string, ErrorConfig> = {
  // Campanhas
  campanha_nome_duplicado: {
    message: 'Ja existe uma campanha com esse nome.',
    action: { label: 'Ver campanhas', href: '/campanhas' },
  },
  campanha_sem_destinatarios: {
    message: 'Nenhum medico corresponde aos filtros selecionados.',
    action: { label: 'Ajustar filtros', onClick: 'focus-filters' },
  },
  campanha_corpo_invalido: {
    message: 'A mensagem contem variaveis invalidas.',
  },
  campanha_ativa: {
    message: 'Esta campanha ja esta ativa.',
  },

  // Diretrizes
  diretriz_conflito: {
    message: 'Ja existe uma instrucao ativa com esse escopo.',
  },
  diretriz_vaga_nao_encontrada: {
    message: 'A vaga selecionada nao foi encontrada.',
  },
  diretriz_medico_nao_encontrado: {
    message: 'O medico selecionado nao foi encontrado.',
  },

  // Sistema
  pilot_mode_active: {
    message: 'O modo piloto ja esta ativo.',
  },
  pilot_mode_inactive: {
    message: 'O modo piloto ja esta desativado.',
  },

  // HTTP Status Errors
  rate_limit: {
    message: 'Muitas requisicoes. Aguarde alguns segundos.',
    duration: 5000,
  },
  unauthorized: {
    message: 'Sessao expirada. Faca login novamente.',
    action: { label: 'Fazer login', href: '/login' },
  },
  forbidden: {
    message: 'Voce nao tem permissao para esta acao.',
  },
  not_found: {
    message: 'Recurso nao encontrado.',
  },
  server_error: {
    message: 'Erro interno. Nossa equipe foi notificada.',
  },
  bad_gateway: {
    message: 'Servico temporariamente indisponivel.',
    action: { label: 'Tentar novamente', onClick: 'retry' },
  },
  service_unavailable: {
    message: 'Servico em manutencao. Tente novamente em alguns minutos.',
  },

  // Network Errors
  network_error: {
    message: 'Erro de conexao. Verifique sua internet.',
    action: { label: 'Tentar novamente', onClick: 'retry' },
  },
  timeout: {
    message: 'A requisicao demorou demais. Tente novamente.',
    action: { label: 'Tentar novamente', onClick: 'retry' },
  },

  // Validation Errors
  validation_error: {
    message: 'Dados invalidos. Verifique os campos.',
  },

  // Fallback
  default: {
    message: 'Ocorreu um erro inesperado. Tente novamente.',
    action: { label: 'Tentar novamente', onClick: 'retry' },
  },
}

/**
 * Maps HTTP status codes to error codes.
 */
export function getErrorCodeFromStatus(status: number): string {
  switch (status) {
    case 400:
      return 'validation_error'
    case 401:
      return 'unauthorized'
    case 403:
      return 'forbidden'
    case 404:
      return 'not_found'
    case 429:
      return 'rate_limit'
    case 500:
      return 'server_error'
    case 502:
      return 'bad_gateway'
    case 503:
      return 'service_unavailable'
    default:
      return 'default'
  }
}

/**
 * Gets error config for a given error code or API response.
 */
export function getErrorConfig(errorCode: string): ErrorConfig {
  const config = API_ERROR_MESSAGES[errorCode]
  if (config) return config

  const defaultConfig = API_ERROR_MESSAGES['default']
  // default is always defined, but TypeScript doesn't know that
  return defaultConfig ?? { message: 'Erro inesperado.' }
}

/**
 * Extracts error code from API response body.
 * Expects format: { error: "error_code", detail?: "..." } or { code: "error_code" }
 */
export function extractErrorCode(body: unknown): string | null {
  if (typeof body === 'object' && body !== null) {
    const obj = body as Record<string, unknown>
    if (typeof obj.error === 'string') return obj.error
    if (typeof obj.code === 'string') return obj.code
  }
  return null
}
