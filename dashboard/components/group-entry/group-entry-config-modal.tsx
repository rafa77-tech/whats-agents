'use client'

import { useEffect } from 'react'
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
import { toast } from '@/hooks/use-toast'
import { useGroupEntryConfig, validateConfig, DIAS_SEMANA, CONFIG_LIMITS } from '@/lib/group-entry'
import type { GroupEntryConfigUI } from '@/lib/group-entry'

interface GroupEntryConfigModalProps {
  onClose: () => void
  onSave: () => void
}

export function GroupEntryConfigModal({ onClose, onSave }: GroupEntryConfigModalProps) {
  const { config, setConfig, loading, saving, error, saveConfig } = useGroupEntryConfig()

  // Show error toast
  useEffect(() => {
    if (error) {
      toast({
        title: 'Erro',
        description: error,
        variant: 'destructive',
      })
    }
  }, [error])

  const handleSave = async () => {
    // Validate config
    const validationErrors = validateConfig(config)
    if (validationErrors.length > 0) {
      toast({
        title: 'Configuracao invalida',
        description: validationErrors.join('. '),
        variant: 'destructive',
      })
      return
    }

    const success = await saveConfig(config)
    if (success) {
      toast({
        title: 'Sucesso',
        description: 'Configuracao salva com sucesso',
      })
      onSave()
    }
  }

  const updateConfig = <K extends keyof GroupEntryConfigUI>(
    key: K,
    value: GroupEntryConfigUI[K]
  ) => {
    setConfig((prev) => ({ ...prev, [key]: value }))
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
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground/70" />
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
                <Label htmlFor="gruposPorDia">
                  Grupos por dia (max {CONFIG_LIMITS.gruposPorDia.max})
                </Label>
                <Input
                  id="gruposPorDia"
                  type="number"
                  min={CONFIG_LIMITS.gruposPorDia.min}
                  max={CONFIG_LIMITS.gruposPorDia.max}
                  value={config.gruposPorDia}
                  onChange={(e) => updateConfig('gruposPorDia', parseInt(e.target.value) || 10)}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="intervaloMin">Intervalo min (min)</Label>
                  <Input
                    id="intervaloMin"
                    type="number"
                    min={CONFIG_LIMITS.intervaloMin.min}
                    value={config.intervaloMin}
                    onChange={(e) => updateConfig('intervaloMin', parseInt(e.target.value) || 30)}
                  />
                </div>
                <div>
                  <Label htmlFor="intervaloMax">Intervalo max (min)</Label>
                  <Input
                    id="intervaloMax"
                    type="number"
                    min={CONFIG_LIMITS.intervaloMax.min}
                    value={config.intervaloMax}
                    onChange={(e) => updateConfig('intervaloMax', parseInt(e.target.value) || 60)}
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
                  onChange={(e) => updateConfig('horarioInicio', e.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="horarioFim">Fim</Label>
                <Input
                  id="horarioFim"
                  type="time"
                  value={config.horarioFim}
                  onChange={(e) => updateConfig('horarioFim', e.target.value)}
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
                  onCheckedChange={(checked) => updateConfig('autoValidar', checked)}
                />
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="autoAgendar">Auto-agendar links validados</Label>
                <Switch
                  id="autoAgendar"
                  checked={config.autoAgendar}
                  onCheckedChange={(checked) => updateConfig('autoAgendar', checked)}
                />
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="notificarFalhas">Notificar falhas no Slack</Label>
                <Switch
                  id="notificarFalhas"
                  checked={config.notificarFalhas}
                  onCheckedChange={(checked) => updateConfig('notificarFalhas', checked)}
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
