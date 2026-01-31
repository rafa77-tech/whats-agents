'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { AlertTriangle, Loader2, ShieldAlert, ShieldCheck } from 'lucide-react'

interface SafeModeCardProps {
  isActive: boolean
  onActivate: () => void
}

export function SafeModeCard({ isActive, onActivate }: SafeModeCardProps) {
  const [showConfirm, setShowConfirm] = useState(false)
  const [motivo, setMotivo] = useState('')
  const [activating, setActivating] = useState(false)

  const handleConfirm = async () => {
    if (!motivo.trim()) return

    setActivating(true)
    try {
      // Activate pilot mode and disable all features
      await fetch('/api/sistema/pilot-mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pilot_mode: true, safe_mode: true, motivo }),
      })

      // Disable all autonomous features
      const features = [
        'discovery_automatico',
        'oferta_automatica',
        'reativacao_automatica',
        'feedback_automatico',
      ]
      await Promise.all(
        features.map((feature) =>
          fetch(`/api/sistema/features/${feature}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: false }),
          })
        )
      )

      setShowConfirm(false)
      setMotivo('')
      onActivate()
    } catch {
      // Ignore errors
    } finally {
      setActivating(false)
    }
  }

  return (
    <>
      <Card className={isActive ? 'border-green-300' : 'border-red-200'}>
        <CardHeader>
          <div className="flex items-center gap-3">
            {isActive ? (
              <ShieldCheck className="h-8 w-8 text-green-500" />
            ) : (
              <ShieldAlert className="h-8 w-8 text-red-500" />
            )}
            <div>
              <CardTitle>Safe Mode Emergencial</CardTitle>
              <CardDescription>Para imediatamente todas as operacoes</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div
            className={`rounded-lg p-4 ${isActive ? 'bg-green-50' : 'bg-red-50'}`}
          >
            {isActive ? (
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-green-800">
                  <ShieldCheck className="h-5 w-5" />
                  <span className="font-medium">Safe Mode ATIVO</span>
                </div>
                <p className="text-sm text-green-700">
                  Todas as operacoes autonomas estao paradas. Julia so responde mensagens de
                  medicos ja em conversa.
                </p>
                <Badge className="bg-green-100 text-green-800">Sistema Protegido</Badge>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-sm text-red-700">
                  Para imediatamente TODAS as operacoes da Julia:
                </p>
                <ul className="ml-4 list-disc text-sm text-red-600">
                  <li>Envio de mensagens</li>
                  <li>Processamento de fila</li>
                  <li>Jobs autonomos</li>
                  <li>Entrada em grupos</li>
                </ul>
                <div className="flex items-center justify-between pt-2">
                  <Badge className="bg-yellow-100 text-yellow-800">INATIVO</Badge>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => setShowConfirm(true)}
                  >
                    <AlertTriangle className="mr-2 h-4 w-4" />
                    ATIVAR
                  </Button>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <AlertDialog open={showConfirm} onOpenChange={setShowConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2 text-red-600">
              <AlertTriangle className="h-5 w-5" />
              ATIVAR SAFE MODE?
            </AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-4">
                <div className="rounded-lg bg-red-50 p-3">
                  <p className="font-medium text-red-800">ATENCAO: Acao critica</p>
                  <p className="mt-1 text-sm text-red-700">
                    Isso ira parar IMEDIATAMENTE todas as operacoes autonomas.
                  </p>
                </div>

                <div>
                  <Label htmlFor="motivo" className="text-sm font-medium">
                    Motivo (obrigatorio)
                  </Label>
                  <Textarea
                    id="motivo"
                    value={motivo}
                    onChange={(e) => setMotivo(e.target.value)}
                    placeholder="Descreva o motivo para ativar o Safe Mode..."
                    rows={3}
                    className="mt-1"
                  />
                </div>

                <p className="text-xs text-gray-500">
                  Julia continuara APENAS respondendo mensagens de medicos ja em conversa.
                </p>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <Button variant="outline" onClick={() => setShowConfirm(false)}>
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={handleConfirm}
              disabled={activating || !motivo.trim()}
            >
              {activating ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Ativando...
                </>
              ) : (
                'CONFIRMAR SAFE MODE'
              )}
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
