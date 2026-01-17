/**
 * Wizard Steps Progress Indicator - Sprint 34 E03
 */

'use client'

import { CheckCircle2, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import { WIZARD_STEPS } from './types'

interface WizardStepsProps {
  currentStep: number
}

export function WizardSteps({ currentStep }: WizardStepsProps) {
  return (
    <div className="mb-6 flex items-center justify-between">
      {WIZARD_STEPS.map((s, index) => {
        const StepIcon = s.icon
        const isActive = currentStep === s.id
        const isCompleted = currentStep > s.id

        return (
          <div key={s.id} className="flex items-center">
            <div
              className={cn(
                'flex h-10 w-10 items-center justify-center rounded-full border-2 transition-colors',
                isActive && 'border-primary bg-primary text-white',
                isCompleted && 'border-green-500 bg-green-500 text-white',
                !isActive && !isCompleted && 'border-gray-300 text-gray-400'
              )}
            >
              {isCompleted ? (
                <CheckCircle2 className="h-5 w-5" />
              ) : (
                <StepIcon className="h-5 w-5" />
              )}
            </div>
            <span
              className={cn(
                'ml-2 text-sm font-medium',
                isActive && 'text-primary',
                !isActive && 'text-gray-500'
              )}
            >
              {s.title}
            </span>
            {index < WIZARD_STEPS.length - 1 && (
              <ChevronRight className="mx-4 h-5 w-5 text-gray-300" />
            )}
          </div>
        )
      })}
    </div>
  )
}
