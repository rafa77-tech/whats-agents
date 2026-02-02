import type { SWRConfiguration } from 'swr'

/**
 * Erro customizado para SWR com informações adicionais.
 *
 * Sprint 44 T05.3: SWR para Data Fetching.
 */
export class FetchError extends Error {
  info: unknown
  status: number | undefined

  constructor(message: string, status?: number, info?: unknown) {
    super(message)
    this.name = 'FetchError'
    this.status = status
    this.info = info
  }
}

/**
 * Fetcher padrão para SWR.
 * Inclui tratamento de erros e parsing automático de JSON.
 */
export async function fetcher<T>(url: string): Promise<T> {
  const res = await fetch(url)

  if (!res.ok) {
    let info: unknown
    try {
      info = await res.json()
    } catch {
      info = { message: res.statusText }
    }

    throw new FetchError('Erro ao carregar dados', res.status, info)
  }

  return res.json() as Promise<T>
}

/**
 * Fetcher com POST para SWR.
 * Útil para endpoints que precisam de body.
 */
export async function postFetcher<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    let info: unknown
    try {
      info = await res.json()
    } catch {
      info = { message: res.statusText }
    }

    throw new FetchError('Erro ao enviar dados', res.status, info)
  }

  return res.json() as Promise<T>
}

/**
 * Configuração global padrão do SWR.
 */
export const swrConfig: SWRConfiguration = {
  fetcher,
  revalidateOnFocus: false,
  dedupingInterval: 5000,
  errorRetryCount: 3,
  errorRetryInterval: 5000,
  onError: (error: FetchError) => {
    // Log de erros para monitoramento
    if (process.env.NODE_ENV === 'development') {
      console.error('[SWR Error]', error.message, error.status, error.info)
    }
  },
}

/**
 * Configuração para dados que mudam frequentemente.
 */
export const realtimeConfig: SWRConfiguration = {
  ...swrConfig,
  refreshInterval: 30000, // 30 segundos
  revalidateOnFocus: true,
}

/**
 * Configuração para dados estáticos ou que mudam raramente.
 */
export const staticConfig: SWRConfiguration = {
  ...swrConfig,
  revalidateOnFocus: false,
  revalidateIfStale: false,
  dedupingInterval: 60000, // 1 minuto
}
