/**
 * Abstração de logging para o Dashboard.
 *
 * Sprint 44 T05.6/T05.12: Remover console.logs e criar logging abstraction.
 *
 * Em desenvolvimento: logs são exibidos no console
 * Em produção: logs podem ser enviados para serviço de monitoramento
 */

interface LogContext {
  component?: string
  action?: string
  userId?: string
  chipId?: string
  conversaId?: string
  [key: string]: unknown
}

const isDevelopment = process.env.NODE_ENV === 'development'

/**
 * Logger centralizado para o dashboard.
 */
export const logger = {
  /**
   * Log de debug (apenas em desenvolvimento).
   */
  debug(message: string, context?: LogContext): void {
    if (isDevelopment) {
      console.debug(`[DEBUG] ${message}`, context ?? '')
    }
  },

  /**
   * Log de informação.
   */
  info(message: string, context?: LogContext): void {
    if (isDevelopment) {
      console.info(`[INFO] ${message}`, context ?? '')
    }
    // Em produção: enviar para serviço de monitoramento
    // sendToMonitoring('info', message, context)
  },

  /**
   * Log de aviso.
   */
  warn(message: string, context?: LogContext): void {
    if (isDevelopment) {
      console.warn(`[WARN] ${message}`, context ?? '')
    }
    // Em produção: enviar para serviço de monitoramento
    // sendToMonitoring('warn', message, context)
  },

  /**
   * Log de erro.
   */
  error(message: string, error?: Error, context?: LogContext): void {
    if (isDevelopment) {
      console.error(`[ERROR] ${message}`, error, context ?? '')
    }
    // Em produção: enviar para serviço de monitoramento (Sentry, etc)
    // sendToMonitoring('error', message, context, error)
  },

  /**
   * Log de ação do usuário (analytics).
   */
  track(action: string, properties?: Record<string, unknown>): void {
    if (isDevelopment) {
      console.info(`[TRACK] ${action}`, properties ?? '')
    }
    // Em produção: enviar para serviço de analytics
    // sendToAnalytics(action, properties)
  },

  /**
   * Log de performance.
   */
  perf(label: string, durationMs: number, context?: LogContext): void {
    if (isDevelopment) {
      console.info(`[PERF] ${label}: ${durationMs.toFixed(2)}ms`, context ?? '')
    }
    // Em produção: enviar para serviço de APM
    // sendToAPM(label, durationMs, context)
  },
}

/**
 * HOC para medir tempo de execução de funções async.
 */
export function withTiming<T extends (...args: unknown[]) => Promise<unknown>>(
  fn: T,
  label: string
): T {
  return (async (...args: Parameters<T>) => {
    const start = performance.now()
    try {
      return await fn(...args)
    } finally {
      const duration = performance.now() - start
      logger.perf(label, duration)
    }
  }) as T
}

/**
 * Hook-like para medir tempo (uso em componentes).
 */
export function measureTime(label: string): () => void {
  const start = performance.now()
  return () => {
    const duration = performance.now() - start
    logger.perf(label, duration)
  }
}
