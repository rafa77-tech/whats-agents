/**
 * Wizard Container - Sprint 34 E03/E05
 *
 * Responsive container that uses Dialog on desktop and Sheet on mobile.
 * Includes draft state persistence and recovery.
 */

'use client'

import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { useMediaQuery } from '@/hooks/use-media-query'
import { useApiError } from '@/hooks/use-api-error'
import { ChevronLeft, ChevronRight, CheckCircle2, Loader2, Megaphone } from 'lucide-react'

import { WizardSteps } from './wizard-steps'
import { StepConfiguracao } from './step-configuracao'
import { StepAudiencia } from './step-audiencia'
import { StepMensagem } from './step-mensagem'
import { StepRevisao } from './step-revisao'
import { useCampanhaForm } from './use-campanha-form'
import { DraftRecoveryDialog } from './draft-recovery-dialog'

interface WizardContainerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}

export function WizardContainer({ open, onOpenChange, onSuccess }: WizardContainerProps) {
  const isDesktop = useMediaQuery('(min-width: 768px)')
  const { handleError } = useApiError()

  const {
    step,
    formData,
    updateField,
    toggleArrayItem,
    canProceed,
    nextStep,
    prevStep,
    reset,
    loading,
    setLoading,
    buildPayload,
    // Draft state
    hasDraft,
    draftStep,
    restoreFromDraft,
    dismissDraft,
  } = useCampanhaForm()

  // Show draft recovery dialog when modal opens and draft exists
  const showDraftDialog = open && hasDraft

  const handleSubmit = async () => {
    setLoading(true)

    try {
      const payload = buildPayload()

      const res = await fetch('/api/campanhas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!res.ok) {
        await handleError({ response: res })
        return
      }

      onSuccess()
      handleClose()
    } catch (error) {
      await handleError({ error: error instanceof Error ? error : undefined })
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    reset()
    onOpenChange(false)
  }

  const content = (
    <>
      <WizardSteps currentStep={step} />

      <div className="min-h-[300px]">
        {step === 1 && (
          <StepConfiguracao formData={formData} updateField={updateField} />
        )}
        {step === 2 && (
          <StepAudiencia
            formData={formData}
            updateField={updateField}
            toggleArrayItem={toggleArrayItem}
          />
        )}
        {step === 3 && (
          <StepMensagem formData={formData} updateField={updateField} />
        )}
        {step === 4 && (
          <StepRevisao formData={formData} updateField={updateField} />
        )}
      </div>

      <div className="mt-6 flex justify-between border-t pt-4">
        <Button variant="outline" onClick={prevStep} disabled={step === 1}>
          <ChevronLeft className="mr-2 h-4 w-4" />
          Voltar
        </Button>

        {step < 4 ? (
          <Button onClick={nextStep} disabled={!canProceed()}>
            Proximo
            <ChevronRight className="ml-2 h-4 w-4" />
          </Button>
        ) : (
          <Button onClick={handleSubmit} disabled={loading}>
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Criando...
              </>
            ) : (
              <>
                <CheckCircle2 className="mr-2 h-4 w-4" />
                Criar Campanha
              </>
            )}
          </Button>
        )}
      </div>
    </>
  )

  const draftDialog = (
    <DraftRecoveryDialog
      open={showDraftDialog}
      draftStep={draftStep}
      onRecover={restoreFromDraft}
      onDiscard={dismissDraft}
    />
  )

  if (isDesktop) {
    return (
      <>
        {draftDialog}
        <Dialog open={open} onOpenChange={handleClose}>
          <DialogContent className="max-h-[90vh] max-w-4xl overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Megaphone className="h-5 w-5" />
                Nova Campanha
              </DialogTitle>
            </DialogHeader>
            {content}
          </DialogContent>
        </Dialog>
      </>
    )
  }

  return (
    <>
      {draftDialog}
      <Sheet open={open} onOpenChange={handleClose}>
        <SheetContent side="bottom" className="h-[90vh] overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              <Megaphone className="h-5 w-5" />
              Nova Campanha
            </SheetTitle>
          </SheetHeader>
          <div className="mt-4">{content}</div>
        </SheetContent>
      </Sheet>
    </>
  )
}
