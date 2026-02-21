'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

export default function FlowsTab() {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">WhatsApp Flows</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Formularios nativos dentro do WhatsApp com criptografia end-to-end.
          </p>

          <div className="rounded-lg border border-dashed p-8 text-center">
            <p className="text-sm font-medium">Flow Builder</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Interface visual para construcao de flows em desenvolvimento.
            </p>
            <Badge variant="secondary" className="mt-3">
              Em breve
            </Badge>
          </div>

          <div className="text-xs text-muted-foreground">
            <p>Flows disponiveis via API:</p>
            <ul className="mt-1 list-inside list-disc space-y-1">
              <li>Onboarding de medicos</li>
              <li>Confirmacao de plantao</li>
              <li>Avaliacao pos-plantao</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
