/**
 * Config Tab Content - Sprint 45
 *
 * Conteudo da tab Configuracoes (sem header, mas com botao Save).
 * Refatorado de config-page-content.tsx para uso com tabs.
 */

'use client'

import { useState, useEffect } from 'react'
import { Save, Loader2, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { cn } from '@/lib/utils'
import { chipsApi } from '@/lib/api/chips'
import { PoolConfig } from '@/types/chips'

export function ConfigTabContent() {
  const [config, setConfig] = useState<PoolConfig | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const data = await chipsApi.getPoolConfig()
        setConfig(data)
      } catch (err) {
        console.error('Error fetching config:', err)
        setError('Nao foi possivel carregar as configuracoes')
      } finally {
        setIsLoading(false)
      }
    }
    fetchConfig()
  }, [])

  const handleSave = async () => {
    if (!config) return

    setIsSaving(true)
    setError(null)
    setSuccess(false)

    try {
      await chipsApi.updatePoolConfig(config)
      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
    } catch (err) {
      console.error('Error saving config:', err)
      setError('Nao foi possivel salvar as configuracoes')
    } finally {
      setIsSaving(false)
    }
  }

  const updateConfig = (updates: Partial<PoolConfig>) => {
    if (config) {
      setConfig({ ...config, ...updates })
    }
  }

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="h-8 w-48 rounded bg-muted" />
        <div className="space-y-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-32 rounded bg-muted" />
          ))}
        </div>
      </div>
    )
  }

  if (!config) {
    return (
      <div className="py-12 text-center">
        <AlertTriangle className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
        <p className="text-muted-foreground">{error || 'Configuracoes nao disponiveis'}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Save button */}
      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={isSaving}>
          {isSaving ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Salvando...
            </>
          ) : (
            <>
              <Save className="mr-2 h-4 w-4" />
              Salvar Alteracoes
            </>
          )}
        </Button>
      </div>

      {/* Status messages */}
      {error && (
        <div className="rounded-lg border border-status-error-border bg-status-error/10 p-4 text-status-error-foreground">
          {error}
        </div>
      )}
      {success && (
        <div className="rounded-lg border border-status-success-border bg-status-success/10 p-4 text-status-success-foreground">
          Configuracoes salvas com sucesso!
        </div>
      )}

      {/* Limites Gerais */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Limites do Pool</CardTitle>
          <CardDescription>Configure os limites de chips do pool</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div>
              <Label htmlFor="maxChipsActive">Maximo de Chips Ativos</Label>
              <Input
                id="maxChipsActive"
                type="number"
                value={config.maxChipsActive}
                onChange={(e) => updateConfig({ maxChipsActive: parseInt(e.target.value) })}
              />
            </div>
            <div>
              <Label htmlFor="maxChipsWarming">Maximo em Warmup</Label>
              <Input
                id="maxChipsWarming"
                type="number"
                value={config.maxChipsWarming}
                onChange={(e) => updateConfig({ maxChipsWarming: parseInt(e.target.value) })}
              />
            </div>
            <div>
              <Label htmlFor="minChipsReady">Minimo Prontos</Label>
              <Input
                id="minChipsReady"
                type="number"
                value={config.minChipsReady}
                onChange={(e) => updateConfig({ minChipsReady: parseInt(e.target.value) })}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Limites de Mensagem */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Limites de Mensagens</CardTitle>
          <CardDescription>Configure os limites de envio de mensagens</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div>
              <Label htmlFor="maxMsgsPerHour">Mensagens por Hora</Label>
              <Input
                id="maxMsgsPerHour"
                type="number"
                value={config.maxMsgsPerHour}
                onChange={(e) => updateConfig({ maxMsgsPerHour: parseInt(e.target.value) })}
              />
            </div>
            <div>
              <Label htmlFor="maxMsgsPerDay">Mensagens por Dia</Label>
              <Input
                id="maxMsgsPerDay"
                type="number"
                value={config.maxMsgsPerDay}
                onChange={(e) => updateConfig({ maxMsgsPerDay: parseInt(e.target.value) })}
              />
            </div>
            <div>
              <Label htmlFor="minIntervalSeconds">Intervalo Minimo (seg)</Label>
              <Input
                id="minIntervalSeconds"
                type="number"
                value={config.minIntervalSeconds}
                onChange={(e) => updateConfig({ minIntervalSeconds: parseInt(e.target.value) })}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Warmup */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Configuracoes de Warmup</CardTitle>
          <CardDescription>Configure o processo de aquecimento de chips</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <Label>Promocao Automatica</Label>
              <p className="text-sm text-muted-foreground">
                Promover chips automaticamente quando atingirem criterios
              </p>
            </div>
            <Switch
              checked={config.autoPromoteEnabled}
              onCheckedChange={(checked) => updateConfig({ autoPromoteEnabled: checked })}
            />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <Label>Rebaixamento Automatico</Label>
              <p className="text-sm text-muted-foreground">
                Rebaixar chips automaticamente quando trust cair
              </p>
            </div>
            <Switch
              checked={config.autoDemoteEnabled}
              onCheckedChange={(checked) => updateConfig({ autoDemoteEnabled: checked })}
            />
          </div>
          <div>
            <Label htmlFor="minTrustForPromotion">Trust Minimo para Promocao</Label>
            <Input
              id="minTrustForPromotion"
              type="number"
              value={config.minTrustForPromotion}
              onChange={(e) => updateConfig({ minTrustForPromotion: parseInt(e.target.value) })}
              className="max-w-[200px]"
            />
          </div>
        </CardContent>
      </Card>

      {/* Horarios */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Horarios de Operacao</CardTitle>
          <CardDescription>Configure os horarios em que o sistema opera</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid max-w-md grid-cols-2 gap-4">
            <div>
              <Label htmlFor="startTime">Inicio</Label>
              <Input
                id="startTime"
                type="time"
                value={config.operatingHours.start}
                onChange={(e) =>
                  updateConfig({
                    operatingHours: { ...config.operatingHours, start: e.target.value },
                  })
                }
              />
            </div>
            <div>
              <Label htmlFor="endTime">Fim</Label>
              <Input
                id="endTime"
                type="time"
                value={config.operatingHours.end}
                onChange={(e) =>
                  updateConfig({
                    operatingHours: { ...config.operatingHours, end: e.target.value },
                  })
                }
              />
            </div>
          </div>
          <div>
            <Label>Dias de Operacao</Label>
            <div className="mt-2 flex gap-2">
              {['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab'].map((day, index) => (
                <button
                  key={day}
                  type="button"
                  onClick={() => {
                    const days = config.operatingDays.includes(index)
                      ? config.operatingDays.filter((d) => d !== index)
                      : [...config.operatingDays, index].sort()
                    updateConfig({ operatingDays: days })
                  }}
                  className={cn(
                    'rounded-md px-3 py-1 text-sm font-medium transition-colors',
                    config.operatingDays.includes(index)
                      ? 'bg-status-info text-status-info-foreground'
                      : 'bg-muted text-muted-foreground hover:bg-muted/80'
                  )}
                >
                  {day}
                </button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Alert Thresholds */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Limiares de Alerta</CardTitle>
          <CardDescription>Configure quando alertas devem ser disparados</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <div>
              <Label htmlFor="trustDropWarning">Trust Drop (Alerta)</Label>
              <Input
                id="trustDropWarning"
                type="number"
                value={config.alertThresholds.trustDropWarning}
                onChange={(e) =>
                  updateConfig({
                    alertThresholds: {
                      ...config.alertThresholds,
                      trustDropWarning: parseInt(e.target.value),
                    },
                  })
                }
              />
            </div>
            <div>
              <Label htmlFor="trustDropCritical">Trust Drop (Critico)</Label>
              <Input
                id="trustDropCritical"
                type="number"
                value={config.alertThresholds.trustDropCritical}
                onChange={(e) =>
                  updateConfig({
                    alertThresholds: {
                      ...config.alertThresholds,
                      trustDropCritical: parseInt(e.target.value),
                    },
                  })
                }
              />
            </div>
            <div>
              <Label htmlFor="errorRateWarning">Error Rate (Alerta) %</Label>
              <Input
                id="errorRateWarning"
                type="number"
                value={config.alertThresholds.errorRateWarning}
                onChange={(e) =>
                  updateConfig({
                    alertThresholds: {
                      ...config.alertThresholds,
                      errorRateWarning: parseInt(e.target.value),
                    },
                  })
                }
              />
            </div>
            <div>
              <Label htmlFor="errorRateCritical">Error Rate (Critico) %</Label>
              <Input
                id="errorRateCritical"
                type="number"
                value={config.alertThresholds.errorRateCritical}
                onChange={(e) =>
                  updateConfig({
                    alertThresholds: {
                      ...config.alertThresholds,
                      errorRateCritical: parseInt(e.target.value),
                    },
                  })
                }
              />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
