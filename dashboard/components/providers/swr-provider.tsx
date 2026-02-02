'use client'

import { SWRConfig } from 'swr'
import { swrConfig } from '@/lib/swr'

interface SWRProviderProps {
  children: React.ReactNode
}

/**
 * Provider global de SWR para o dashboard.
 *
 * Sprint 44 T05.3: SWR para Data Fetching.
 *
 * Wrap the app with this provider in the root layout to enable
 * global SWR configuration and caching.
 */
export function SWRProvider({ children }: SWRProviderProps) {
  return <SWRConfig value={swrConfig}>{children}</SWRConfig>
}
