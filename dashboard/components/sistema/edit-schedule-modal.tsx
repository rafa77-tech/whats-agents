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
import { Loader2 } from 'lucide-react'

interface ScheduleConfig {
  inicio: number
  fim: number
  dias: string[]
}

interface EditScheduleModalProps {
  currentConfig: {
    inicio: number
    fim: number
    dias: string
  }
  onClose: () => void
  onSave: () => void
}

const DIAS_SEMANA = [
  { key: 'seg', label: 'Seg' },
  { key: 'ter', label: 'Ter' },
  { key: 'qua', label: 'Qua' },
  { key: 'qui', label: 'Qui' },
  { key: 'sex', label: 'Sex' },
  { key: 'sab', label: 'Sab' },
  { key: 'dom', label: 'Dom' },
]

function parseDias(diasStr: string): string[] {
  const mapping: Record<string, string[]> = {
    'Seg-Sex': ['seg', 'ter', 'qua', 'qui', 'sex'],
    'Seg-Sab': ['seg', 'ter', 'qua', 'qui', 'sex', 'sab'],
    'Todos': ['seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom'],
  }
  return mapping[diasStr] || ['seg', 'ter', 'qua', 'qui', 'sex']
}

export function EditScheduleModal({ currentConfig, onClose, onSave }: EditScheduleModalProps) {
  const [config, setConfig] = useState<ScheduleConfig>({
    inicio: currentConfig.inicio,
    fim: currentConfig.fim,
    dias: parseDias(currentConfig.dias),
  })
  const [saving, setSaving] = useState(false)

  const toggleDia = (dia: string) => {
    setConfig((prev) => ({
      ...prev,
      dias: prev.dias.includes(dia)
        ? prev.dias.filter((d) => d !== dia)
        : [...prev.dias, dia],
    }))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await fetch('/api/sistema/config', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          horario: {
            inicio: config.inicio,
            fim: config.fim,
            dias: config.dias,
          },
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
          <DialogTitle>Editar Horario de Operacao</DialogTitle>
          <DialogDescription>Configure quando Julia pode enviar mensagens</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="inicio">Hora de inicio</Label>
              <Input
                id="inicio"
                type="number"
                min={0}
                max={23}
                value={config.inicio}
                onChange={(e) =>
                  setConfig((c) => ({ ...c, inicio: parseInt(e.target.value) || 8 }))
                }
              />
            </div>
            <div>
              <Label htmlFor="fim">Hora de fim</Label>
              <Input
                id="fim"
                type="number"
                min={0}
                max={23}
                value={config.fim}
                onChange={(e) =>
                  setConfig((c) => ({ ...c, fim: parseInt(e.target.value) || 20 }))
                }
              />
            </div>
          </div>

          <div>
            <Label>Dias de operacao</Label>
            <div className="mt-2 flex flex-wrap gap-2">
              {DIAS_SEMANA.map((dia) => (
                <Button
                  key={dia.key}
                  type="button"
                  variant={config.dias.includes(dia.key) ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => toggleDia(dia.key)}
                >
                  {dia.label}
                </Button>
              ))}
            </div>
          </div>

          <div className="rounded-lg bg-blue-50 p-3">
            <p className="text-xs text-blue-700">
              Julia so enviara mensagens proativas dentro deste horario. Respostas a medicos
              funcionam 24/7.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={handleSave} disabled={saving || config.dias.length === 0}>
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
