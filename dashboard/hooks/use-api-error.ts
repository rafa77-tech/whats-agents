/**
 * useApiError Hook - Sprint 34 E01
 *
 * Handles API errors with user-friendly toast notifications.
 */

import { useCallback } from 'react'
import { toast } from 'sonner'
import {
  getErrorConfig,
  getErrorCodeFromStatus,
  extractErrorCode,
  type ErrorConfig,
  type ErrorAction,
} from '@/lib/errors'

interface ApiErrorOptions {
  onRetry?: () => void | Promise<void>
  onFocusFilters?: () => void
  fallbackMessage?: string
}

interface HandleErrorParams {
  response?: Response | undefined
  error?: Error | undefined
  errorCode?: string | undefined
}

export function useApiError(options: ApiErrorOptions = {}) {
  const { onRetry, onFocusFilters, fallbackMessage } = options

  const handleAction = useCallback(
    (action: ErrorAction | undefined) => {
      if (!action) return undefined

      if (action.href) {
        const href = action.href
        return {
          label: action.label,
          onClick: () => {
            window.location.href = href
          },
        }
      }

      if (action.onClick === 'retry' && onRetry) {
        return {
          label: action.label,
          onClick: () => void onRetry(),
        }
      }

      if (action.onClick === 'focus-filters' && onFocusFilters) {
        return {
          label: action.label,
          onClick: onFocusFilters,
        }
      }

      if (action.onClick === 'close') {
        return {
          label: action.label,
          onClick: () => toast.dismiss(),
        }
      }

      return undefined
    },
    [onRetry, onFocusFilters]
  )

  const showError = useCallback(
    (config: ErrorConfig) => {
      const action = handleAction(config.action)

      toast.error(config.message, {
        duration: config.duration ?? 4000,
        action,
      })
    },
    [handleAction]
  )

  const handleError = useCallback(
    async ({ response, error, errorCode }: HandleErrorParams) => {
      // If we have a direct error code, use it
      if (errorCode) {
        const config = getErrorConfig(errorCode)
        showError(config)
        return
      }

      // Handle network errors
      if (error && !response) {
        if (error.name === 'AbortError') {
          showError(getErrorConfig('timeout'))
        } else {
          showError(getErrorConfig('network_error'))
        }
        return
      }

      // Handle HTTP response errors
      if (response && !response.ok) {
        // Try to extract error code from response body
        try {
          const body = await response.json()
          const extractedCode = extractErrorCode(body)

          if (extractedCode) {
            const config = getErrorConfig(extractedCode)
            showError(config)
            return
          }

          // If body has a detail field, use it as the message
          if (typeof body.detail === 'string') {
            toast.error(body.detail, { duration: 4000 })
            return
          }
        } catch {
          // Could not parse body, fall through to status-based error
        }

        // Fall back to status-based error
        const statusCode = getErrorCodeFromStatus(response.status)
        const config = getErrorConfig(statusCode)
        showError(config)
        return
      }

      // Fallback error
      if (fallbackMessage) {
        toast.error(fallbackMessage)
      } else {
        showError(getErrorConfig('default'))
      }
    },
    [showError, fallbackMessage]
  )

  return {
    handleError,
    showError,
  }
}
