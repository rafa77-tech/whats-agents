'use client'

import { useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { FlowScreen, FlowComponent } from '@/types/meta'

function FlowComponentPreview({ component }: { component: FlowComponent }) {
  switch (component.type) {
    case 'TextInput':
      return (
        <div className="space-y-1">
          <label className="text-xs font-medium text-foreground">
            {component.label}
            {component.required && <span className="text-destructive"> *</span>}
          </label>
          <div className="rounded border border-border bg-muted/30 px-2 py-1.5 text-xs text-muted-foreground">
            {component['helper-text'] ?? 'Digite aqui...'}
          </div>
        </div>
      )

    case 'Dropdown':
      return (
        <div className="space-y-1">
          <label className="text-xs font-medium text-foreground">
            {component.label}
            {component.required && <span className="text-destructive"> *</span>}
          </label>
          <div className="flex items-center justify-between rounded border border-border bg-muted/30 px-2 py-1.5 text-xs text-muted-foreground">
            <span>Selecione...</span>
            <ChevronRight className="h-3 w-3" />
          </div>
        </div>
      )

    case 'RadioButtonsGroup':
      return (
        <div className="space-y-1">
          <label className="text-xs font-medium text-foreground">{component.label}</label>
          <div className="space-y-1">
            {(component['data-source'] ?? []).slice(0, 3).map((opt) => (
              <div key={opt.id} className="flex items-center gap-1.5">
                <div className="h-3 w-3 rounded-full border border-border" />
                <span className="text-xs text-muted-foreground">{opt.title}</span>
              </div>
            ))}
          </div>
        </div>
      )

    case 'CheckboxGroup':
      return (
        <div className="space-y-1">
          <label className="text-xs font-medium text-foreground">{component.label}</label>
          <div className="space-y-1">
            {(component['data-source'] ?? []).slice(0, 3).map((opt) => (
              <div key={opt.id} className="flex items-center gap-1.5">
                <div className="h-3 w-3 rounded border border-border" />
                <span className="text-xs text-muted-foreground">{opt.title}</span>
              </div>
            ))}
          </div>
        </div>
      )

    case 'Footer':
      return (
        <div className="pt-2">
          <div className="rounded bg-primary px-3 py-1.5 text-center text-xs font-medium text-primary-foreground">
            {component.label ?? 'Enviar'}
          </div>
        </div>
      )

    case 'TextHeading':
    case 'TextSubheading':
    case 'TextBody':
      return (
        <p
          className={
            component.type === 'TextHeading'
              ? 'text-xs font-bold'
              : component.type === 'TextSubheading'
                ? 'text-xs font-medium'
                : 'text-xs text-muted-foreground'
          }
        >
          {component.label}
        </p>
      )

    default:
      return null
  }
}

interface FlowScreenPreviewProps {
  screens: FlowScreen[]
  className?: string
}

export function FlowScreenPreview({ screens, className = '' }: FlowScreenPreviewProps) {
  const [currentIndex, setCurrentIndex] = useState(0)

  if (screens.length === 0) {
    return (
      <div
        className={`flex items-center justify-center text-xs text-muted-foreground ${className}`}
      >
        Sem screens
      </div>
    )
  }

  const screen = screens[currentIndex] as FlowScreen | undefined
  if (!screen) return null
  const children = screen.layout?.children ?? []

  return (
    <div className={`flex flex-col ${className}`}>
      {/* Screen header */}
      <div className="flex items-center justify-between border-b px-3 py-2">
        <span className="text-xs font-medium">{screen.title}</span>
        {screens.length > 1 && (
          <span className="text-[10px] text-muted-foreground">
            {currentIndex + 1}/{screens.length}
          </span>
        )}
      </div>

      {/* Screen body */}
      <div className="flex-1 space-y-2.5 p-3">
        {children.map((comp, i) => (
          <FlowComponentPreview key={`${comp.type}-${comp.name ?? i}`} component={comp} />
        ))}
      </div>

      {/* Navigation */}
      {screens.length > 1 && (
        <div className="flex items-center justify-between border-t px-3 py-1.5">
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-1"
            disabled={currentIndex === 0}
            onClick={() => setCurrentIndex((i) => i - 1)}
          >
            <ChevronLeft className="h-3 w-3" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-1"
            disabled={currentIndex === screens.length - 1}
            onClick={() => setCurrentIndex((i) => i + 1)}
          >
            <ChevronRight className="h-3 w-3" />
          </Button>
        </div>
      )}
    </div>
  )
}
