/**
 * Nova Campanha Wizard - Sprint 34 E03
 *
 * Re-exports the refactored wizard container.
 * This file is kept for backwards compatibility with existing imports.
 */

'use client'

import { WizardContainer } from './wizard'

interface NovaCampanhaWizardProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}

export function NovaCampanhaWizard(props: NovaCampanhaWizardProps) {
  return <WizardContainer {...props} />
}
