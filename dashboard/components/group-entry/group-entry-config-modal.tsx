'use client'

import { useState, useEffect } from 'react'
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
import { Switch } from '@/components/ui/switch'
import { Loader2 } from 'lucide-react'

interface GroupEntryConfig {
  gruposPorDia: number
  intervaloMin: number
  intervaloMax: number
  horarioInicio: string
  horarioFim: string
  diasAtivos: string[]
  autoValidar: boolean
  autoAgendar: boolean
  notificarFalhas: boolean
}

interface GroupEntryConfigModalProps {
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

export function GroupEntryConfigModal({ onClose, onSave }: GroupEntryConfigModalProps) {
  const [config, setConfig] = useState<GroupEntryConfig>({
    gruposPorDia: 10,
    intervaloMin: 30,
    intervaloMax: 60,
    horarioInicio: '08:00',
    horarioFim: '20:00',
    diasAtivos: ['seg', 'ter', 'qua', 'qui', 'sex'],
    autoValidar: true,
    autoAgendar: false,
    notificarFalhas: true,
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const res = await fetch('/api/group-entry/config')
        if (res.ok) {
          const data = await res.json()
          setConfig({
            gruposPorDia: data.grupos_por_dia || 10,
            intervaloMin: data.intervalo_min || 30,
            intervaloMax: data.intervalo_max || 60,
            horarioInicio: data.horario_inicio || '08:00',
            horarioFim: data.horario_fim || '20:00',
            diasAtivos: data.dias_ativos || ['seg', 'ter', 'qua', 'qui', 'sex'],
            autoValidar: data.auto_validar ?? true,
            autoAgendar: data.auto_agendar ?? false,
            notificarFalhas: data.notificar_falhas ?? true,
          })
        }
      } catch {
        // Use defaults
      } finally {
        setLoading(false)
      }
    }

    fetchConfig()
  }, [])

  const handleSave = async () => {
    setSaving(true)
    try {
      await fetch('/api/group-entry/config', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          grupos_por_dia: config.gruposPorDia,
          intervalo_min: config.intervaloMin,
          intervalo_max: config.intervaloMax,
          horario_inicio: config.horarioInicio,
          horario_fim: config.horarioFim,
          dias_ativos: config.diasAtivos,
          auto_validar: config.autoValidar,
          auto_agendar: config.autoAgendar,
          notificar_falhas: config.notificarFalhas,
        }),
      })
      onSave()
    } catch {
      // Ignore errors
    } finally {
      setSaving(false)
    }
  }

  const toggleDia = (dia: string) => {
    setConfig((prev) => ({
      ...prev,
      diasAtivos: prev.diasAtivos.includes(dia)
        ? prev.diasAtivos.filter((d) => d !== dia)
        : [...prev.diasAtivos, dia],
    }))
  }

  if (loading) {
    return (
      <Dialog open onOpenChange={onClose}>
        <DialogContent>
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          </div>
        </DialogContent>
      </Dialog>
    )
  }

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Configuracao do Group Entry</DialogTitle>
          <DialogDescription>Configure limites e comportamento do sistema</DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Limites por Chip */}
          <div>
            <h4 className="mb-3 text-sm font-medium">Limites por Chip</h4>
            <div className="space-y-3">
              <div>
                <Label htmlFor="gruposPorDia">Grupos por dia (max 20)</Label>
                <Input
                  id="gruposPorDia"
                  type="number"
                  min={1}
                  max={20}
                  value={config.gruposPorDia}
                  onChange={(e) =>
                    setConfig((prev) => ({ ...prev, gruposPorDia: parseInt(e.target.value) || 10 }))
                  }
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="intervaloMin">Intervalo min (min)</Label>
                  <Input
                    id="intervaloMin"
                    type="number"
                    min={15}
                    value={config.intervaloMin}
                    onChange={(e) =>
                      setConfig((prev) => ({
                        ...prev,
                        intervaloMin: parseInt(e.target.value) || 30,
                      }))
                    }
                  />
                </div>
                <div>
                  <Label htmlFor="intervaloMax">Intervalo max (min)</Label>
                  <Input
                    id="intervaloMax"
                    type="number"
                    min={30}
                    value={config.intervaloMax}
                    onChange={(e) =>
                      setConfig((prev) => ({
                        ...prev,
                        intervaloMax: parseInt(e.target.value) || 60,
                      }))
                    }
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Horario de Operacao */}
          <div>
            <h4 className="mb-3 text-sm font-medium">Horario de Operacao</h4>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="horarioInicio">Inicio</Label>
                <Input
                  id="horarioInicio"
                  type="time"
                  value={config.horarioInicio}
                  onChange={(e) =>
                    setConfig((prev) => ({ ...prev, horarioInicio: e.target.value }))
                  }
                />
              </div>
              <div>
                <Label htmlFor="horarioFim">Fim</Label>
                <Input
                  id="horarioFim"
                  type="time"
                  value={config.horarioFim}
                  onChange={(e) => setConfig((prev) => ({ ...prev, horarioFim: e.target.value }))}
                />
              </div>
            </div>
            <div className="mt-3">
              <Label>Dias da semana</Label>
              <div className="mt-2 flex flex-wrap gap-2">
                {DIAS_SEMANA.map((dia) => (
                  <Button
                    key={dia.key}
                    type="button"
                    variant={config.diasAtivos.includes(dia.key) ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => toggleDia(dia.key)}
                  >
                    {dia.label}
                  </Button>
                ))}
              </div>
            </div>
          </div>

          {/* Comportamento */}
          <div>
            <h4 className="mb-3 text-sm font-medium">Comportamento</h4>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label htmlFor="autoValidar">Auto-validar links importados</Label>
                <Switch
                  id="autoValidar"
                  checked={config.autoValidar}
                  onCheckedChange={(checked) =>
                    setConfig((prev) => ({ ...prev, autoValidar: checked }))
                  }
                />
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="autoAgendar">Auto-agendar links validados</Label>
                <Switch
                  id="autoAgendar"
                  checked={config.autoAgendar}
                  onCheckedChange={(checked) =>
                    setConfig((prev) => ({ ...prev, autoAgendar: checked }))
                  }
                />
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="notificarFalhas">Notificar falhas no Slack</Label>
                <Switch
                  id="notificarFalhas"
                  checked={config.notificarFalhas}
                  onCheckedChange={(checked) =>
                    setConfig((prev) => ({ ...prev, notificarFalhas: checked }))
                  }
                />
              </div>
            </div>
          </div>
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
              'Salvar'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
