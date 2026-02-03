'use client'

import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { AlertTriangle, Loader2 } from 'lucide-react'

interface RateLimitConfig {
  msgs_por_hora: number
  msgs_por_dia: number
  intervalo_min: number
  intervalo_max: number
}

interface EditRateLimitModalProps {
  currentConfig: RateLimitConfig
  onClose: () => void
  onSave: () => void
}

export function EditRateLimitModal({ currentConfig, onClose, onSave }: EditRateLimitModalProps) {
  const [config, setConfig] = useState<RateLimitConfig>({ ...currentConfig })
  const [saving, setSaving] = useState(false)

  const isHighRisk =
    config.msgs_por_hora > 25 || config.msgs_por_dia > 150 || config.intervalo_min < 30

  const handleSave = async () => {
    setSaving(true)
    try {
      await fetch('/api/sistema/config', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rate_limit: config,
        }),
      })
      onSave()
    } catch {
      // Ignore errors
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Editar Rate Limiting</DialogTitle>
          <DialogDescription>Configure os limites de envio de mensagens</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <Label htmlFor="msgs_por_hora">Mensagens por hora</Label>
            <Input
              id="msgs_por_hora"
              type="number"
              min={5}
              max={50}
              value={config.msgs_por_hora}
              onChange={(e) =>
                setConfig((c) => ({ ...c, msgs_por_hora: parseInt(e.target.value) || 20 }))
              }
            />
            <p className="mt-1 text-xs text-muted-foreground">Recomendado: 15-25</p>
          </div>

          <div>
            <Label htmlFor="msgs_por_dia">Mensagens por dia</Label>
            <Input
              id="msgs_por_dia"
              type="number"
              min={20}
              max={300}
              value={config.msgs_por_dia}
              onChange={(e) =>
                setConfig((c) => ({ ...c, msgs_por_dia: parseInt(e.target.value) || 100 }))
              }
            />
            <p className="mt-1 text-xs text-muted-foreground">Recomendado: 80-150</p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="intervalo_min">Intervalo min (s)</Label>
              <Input
                id="intervalo_min"
                type="number"
                min={30}
                max={180}
                value={config.intervalo_min}
                onChange={(e) =>
                  setConfig((c) => ({ ...c, intervalo_min: parseInt(e.target.value) || 45 }))
                }
              />
              <p className="mt-1 text-xs text-muted-foreground">Minimo: 30s</p>
            </div>
            <div>
              <Label htmlFor="intervalo_max">Intervalo max (s)</Label>
              <Input
                id="intervalo_max"
                type="number"
                min={60}
                max={300}
                value={config.intervalo_max}
                onChange={(e) =>
                  setConfig((c) => ({ ...c, intervalo_max: parseInt(e.target.value) || 180 }))
                }
              />
              <p className="mt-1 text-xs text-muted-foreground">Maximo: 300s</p>
            </div>
          </div>

          {isHighRisk && (
            <div className="rounded-lg border border-status-warning-border bg-status-warning p-3">
              <div className="flex items-center gap-2 text-status-warning-foreground">
                <AlertTriangle className="h-4 w-4" />
                <span className="text-sm font-medium">Atencao</span>
              </div>
              <p className="mt-1 text-xs text-status-warning-foreground">
                Limites muito altos ou intervalos muito curtos podem causar ban do WhatsApp.
              </p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Salvando...
              </>
            ) : (
              'Salvar Alteracoes'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
