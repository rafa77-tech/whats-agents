/**
 * Nova Campanha Wizard - Sprint 34 E03
 *
 * Re-exports the refactored wizard container.
 * This file is kept for backwards compatibility with existing imports.
 * Sprint 58: Added initialData support for vagas→campanhas flow.
 */

'use client'

import { WizardContainer } from './wizard'
import type { WizardInitialData } from '@/lib/vagas/campaign-helpers'

interface NovaCampanhaWizardProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
  initialData?: WizardInitialData | null
}

export function NovaCampanhaWizard(props: NovaCampanhaWizardProps) {
  return <WizardContainer {...props} />
}
