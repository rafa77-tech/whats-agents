'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { useToast } from '@/hooks/use-toast'
import { Shield, Zap, AlertTriangle, CheckCircle2, Loader2, Edit2 } from 'lucide-react'
import { EditRateLimitModal, EditScheduleModal, SafeModeCard } from '@/components/sistema'

interface SystemStatus {
  pilot_mode: boolean
  autonomous_features: {
    discovery_automatico: boolean
    oferta_automatica: boolean
    reativacao_automatica: boolean
    feedback_automatico: boolean
  }
  last_changed_by?: string
  last_changed_at?: string
}

interface SystemConfig {
  rate_limit: {
    msgs_por_hora: number
    msgs_por_dia: number
    intervalo_min: number
    intervalo_max: number
  }
  horario: {
    inicio: number
    fim: number
    dias: string
  }
  uso_atual?: {
    msgs_hora: number
    msgs_dia: number
    horario_permitido: boolean
    hora_atual: string
  }
}

type FeatureKey =
  | 'discovery_automatico'
  | 'oferta_automatica'
  | 'reativacao_automatica'
  | 'feedback_automatico'

interface FeatureDialogState {
  feature: FeatureKey
  action: 'enable' | 'disable'
}

const FEATURE_INFO: Record<FeatureKey, { title: string; description: string }> = {
  discovery_automatico: {
    title: 'Discovery Automatico',
    description: 'Conhecer medicos nao-enriquecidos',
  },
  oferta_automatica: {
    title: 'Oferta Automatica',
    description: 'Ofertar vagas com furo de escala',
  },
  reativacao_automatica: {
    title: 'Reativacao Automatica',
    description: 'Retomar contato com inativos',
  },
  feedback_automatico: {
    title: 'Feedback Automatico',
    description: 'Pedir feedback pos-plantao',
  },
}

export default function SistemaPage() {
  const { toast } = useToast()
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [config, setConfig] = useState<SystemConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [confirmDialog, setConfirmDialog] = useState<'enable' | 'disable' | null>(null)
  const [featureDialog, setFeatureDialog] = useState<FeatureDialogState | null>(null)
  const [updating, setUpdating] = useState(false)
  const [editRateLimit, setEditRateLimit] = useState(false)
  const [editSchedule, setEditSchedule] = useState(false)

  const carregarStatus = async () => {
    try {
      const res = await fetch('/api/sistema/status')
      if (res.ok) {
        const data = await res.json()
        setStatus(data)
      }
    } catch (error) {
      console.error('Erro ao carregar status:', error)
    }
  }

  const carregarConfig = async () => {
    try {
      const res = await fetch('/api/sistema/config')
      if (res.ok) {
        const data = await res.json()
        setConfig(data)
      }
    } catch (error) {
      console.error('Erro ao carregar config:', error)
    }
  }

  useEffect(() => {
    const carregarDados = async () => {
      await Promise.all([carregarStatus(), carregarConfig()])
      setLoading(false)
    }
    carregarDados()
  }, [])

  const handleToggle = async (novoPilotMode: boolean) => {
    setUpdating(true)

    try {
      const res = await fetch('/api/sistema/pilot-mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pilot_mode: novoPilotMode }),
      })

      if (!res.ok) throw new Error('Erro ao atualizar')

      toast({
        title: novoPilotMode ? 'Modo Piloto ATIVADO' : 'Modo Piloto DESATIVADO',
        description: novoPilotMode
          ? 'Julia nao executara acoes autonomas.'
          : 'Julia agora age autonomamente!',
      })

      setConfirmDialog(null)
      carregarStatus()
    } catch {
      toast({
        variant: 'destructive',
        title: 'Erro',
        description: 'Nao foi possivel alterar o modo piloto.',
      })
    } finally {
      setUpdating(false)
    }
  }

  const handleFeatureToggle = async (feature: FeatureKey, enabled: boolean) => {
    setUpdating(true)

    try {
      const res = await fetch(`/api/sistema/features/${feature}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      })

      if (!res.ok) throw new Error('Erro ao atualizar')

      const featureTitle = FEATURE_INFO[feature].title
      toast({
        title: enabled ? `${featureTitle} HABILITADO` : `${featureTitle} DESABILITADO`,
        description: enabled
          ? 'A feature sera executada nos proximos ciclos.'
          : 'A feature nao sera mais executada automaticamente.',
      })

      setFeatureDialog(null)
      carregarStatus()
    } catch {
      toast({
        variant: 'destructive',
        title: 'Erro',
        description: `Nao foi possivel alterar ${FEATURE_INFO[feature].title}.`,
      })
    } finally {
      setUpdating(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Sistema</h1>
          <p className="text-gray-500">Configuracoes e controles do sistema Julia</p>
        </div>
        <div className="py-8 text-center">
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-gray-400" />
          <p className="mt-2 text-gray-500">Carregando...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Sistema</h1>
        <p className="text-gray-500">Configuracoes e controles do sistema Julia</p>
      </div>

      {/* Card principal do Modo Piloto */}
      <Card className={status?.pilot_mode ? 'border-status-warning-border' : 'border-status-success-border'}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Shield
                className={`h-8 w-8 ${status?.pilot_mode ? 'text-status-warning-foreground' : 'text-status-success-foreground'}`}
              />
              <div>
                <CardTitle className="text-xl">Modo Piloto</CardTitle>
                <CardDescription>Controla se Julia age autonomamente</CardDescription>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <Badge
                variant="outline"
                className={
                  status?.pilot_mode
                    ? 'border-status-warning-border bg-status-warning text-status-warning-foreground'
                    : 'border-status-success-border bg-status-success text-status-success-foreground'
                }
              >
                {status?.pilot_mode ? 'ATIVO' : 'DESATIVADO'}
              </Badge>

              <Switch
                checked={!status?.pilot_mode}
                onCheckedChange={(checked) => {
                  setConfirmDialog(checked ? 'disable' : 'enable')
                }}
              />
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {status?.pilot_mode ? (
            <div className="rounded-lg bg-status-warning p-4">
              <div className="mb-2 flex items-center gap-2 text-status-warning-foreground">
                <AlertTriangle className="h-5 w-5" />
                <span className="font-medium">Modo seguro ativo</span>
              </div>
              <p className="text-sm text-status-warning-foreground/90">
                Julia esta em modo piloto. Acoes autonomas estao desabilitadas. Ela so responde
                quando acionada por campanhas manuais ou mensagens de medicos.
              </p>
            </div>
          ) : (
            <div className="rounded-lg bg-status-success p-4">
              <div className="mb-2 flex items-center gap-2 text-status-success-foreground">
                <Zap className="h-5 w-5" />
                <span className="font-medium">Julia autonoma</span>
              </div>
              <p className="text-sm text-status-success-foreground/90">
                Julia esta operando de forma autonoma. Ela identifica oportunidades e age
                proativamente conforme as regras configuradas.
              </p>
            </div>
          )}

          {/* Status das features autonomas */}
          <div className="pt-4">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-medium text-gray-700">Features Autonomas</h3>
              {status?.pilot_mode && (
                <span className="text-xs text-status-warning-solid">
                  Desative o Modo Piloto para controlar individualmente
                </span>
              )}
            </div>
            <div className="grid grid-cols-2 gap-4">
              {(Object.keys(FEATURE_INFO) as FeatureKey[]).map((featureKey) => {
                const info = FEATURE_INFO[featureKey]
                const enabled = status?.autonomous_features[featureKey] ?? false
                const isPilotMode = status?.pilot_mode ?? true

                return (
                  <FeatureToggleCard
                    key={featureKey}
                    featureKey={featureKey}
                    title={info.title}
                    description={info.description}
                    enabled={enabled}
                    isPilotMode={isPilotMode}
                    onToggle={(action) => setFeatureDialog({ feature: featureKey, action })}
                  />
                )
              })}
            </div>
          </div>

          {/* Ultima alteracao */}
          {status?.last_changed_at && (
            <p className="pt-4 text-xs text-gray-500">
              Ultima alteracao: {new Date(status.last_changed_at).toLocaleString('pt-BR')}
              {status.last_changed_by && ` por ${status.last_changed_by}`}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Outros cards de configuracao */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Rate Limiting</CardTitle>
                <CardDescription>Limites de envio de mensagens</CardDescription>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setEditRateLimit(true)}
                disabled={!config}
              >
                <Edit2 className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {config ? (
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Mensagens por hora</span>
                  <span className="font-medium">{config.rate_limit.msgs_por_hora}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Mensagens por dia</span>
                  <span className="font-medium">{config.rate_limit.msgs_por_dia}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Intervalo entre mensagens</span>
                  <span className="font-medium">
                    {config.rate_limit.intervalo_min}-{config.rate_limit.intervalo_max}s
                  </span>
                </div>
                {config.uso_atual && (
                  <>
                    <div className="mt-4 border-t pt-4">
                      <p className="mb-2 text-xs font-medium text-gray-500">Uso atual</p>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Esta hora</span>
                        <span className="font-medium">
                          {config.uso_atual.msgs_hora}/{config.rate_limit.msgs_por_hora}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Hoje</span>
                        <span className="font-medium">
                          {config.uso_atual.msgs_dia}/{config.rate_limit.msgs_por_dia}
                        </span>
                      </div>
                    </div>
                  </>
                )}
              </div>
            ) : (
              <p className="text-sm text-gray-500">Carregando...</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Horario de Operacao</CardTitle>
                <CardDescription>Quando Julia pode enviar mensagens</CardDescription>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setEditSchedule(true)}
                disabled={!config}
              >
                <Edit2 className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {config ? (
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Horario</span>
                  <span className="font-medium">
                    {String(config.horario.inicio).padStart(2, '0')}h as{' '}
                    {String(config.horario.fim).padStart(2, '0')}h
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Dias</span>
                  <span className="font-medium">{config.horario.dias}</span>
                </div>
                {config.uso_atual && (
                  <div className="mt-4 border-t pt-4">
                    <div className="flex items-center justify-between">
                      <span className="text-gray-600">Status agora</span>
                      <Badge
                        variant="outline"
                        className={
                          config.uso_atual.horario_permitido
                            ? 'border-status-success-border bg-status-success text-status-success-foreground'
                            : 'border-status-warning-border bg-status-warning text-status-warning-foreground'
                        }
                      >
                        {config.uso_atual.horario_permitido
                          ? 'Dentro do horario'
                          : 'Fora do horario'}
                      </Badge>
                    </div>
                    <p className="mt-1 text-xs text-gray-400">
                      Hora atual no servidor: {config.uso_atual.hora_atual}
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-gray-500">Carregando...</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Safe Mode Card */}
      <SafeModeCard
        isActive={status?.pilot_mode ?? false}
        onActivate={() => {
          carregarStatus()
          carregarConfig()
        }}
      />

      {/* Edit Modals */}
      {editRateLimit && config && (
        <EditRateLimitModal
          currentConfig={config.rate_limit}
          onClose={() => setEditRateLimit(false)}
          onSave={() => {
            setEditRateLimit(false)
            carregarConfig()
            toast({
              title: 'Rate Limiting Atualizado',
              description: 'As novas configuracoes foram salvas.',
            })
          }}
        />
      )}

      {editSchedule && config && (
        <EditScheduleModal
          currentConfig={config.horario}
          onClose={() => setEditSchedule(false)}
          onSave={() => {
            setEditSchedule(false)
            carregarConfig()
            toast({
              title: 'Horario Atualizado',
              description: 'As novas configuracoes foram salvas.',
            })
          }}
        />
      )}

      {/* Dialogs de confirmacao */}
      <AlertDialog open={confirmDialog === 'enable'} onOpenChange={() => setConfirmDialog(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Ativar Modo Piloto?</AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div>
                Julia deixara de agir autonomamente. As seguintes funcionalidades serao
                desabilitadas:
                <ul className="mt-2 list-inside list-disc">
                  <li>Discovery automatico</li>
                  <li>Oferta automatica por furo de escala</li>
                  <li>Reativacao automatica</li>
                  <li>Feedback automatico</li>
                </ul>
                <p className="mt-4">
                  Julia ainda respondera mensagens de medicos e campanhas manuais.
                </p>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={() => handleToggle(true)} disabled={updating}>
              {updating ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Ativar Modo Piloto'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={confirmDialog === 'disable'} onOpenChange={() => setConfirmDialog(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Desativar Modo Piloto?</AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div>
                <div className="mb-4 flex items-center gap-2 text-status-warning-solid">
                  <AlertTriangle className="h-5 w-5" />
                  <span className="font-medium">Atencao: acao significativa</span>
                </div>
                Julia passara a agir autonomamente conforme as features habilitadas individualmente.
                <p className="mt-4">
                  Voce podera controlar cada feature (Discovery, Oferta, Reativacao, Feedback)
                  separadamente apos desativar o Modo Piloto.
                </p>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => handleToggle(false)}
              disabled={updating}
              className="bg-status-success-solid hover:bg-status-success-solid-hover"
            >
              {updating ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Desativar Modo Piloto'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Dialog de confirmacao para feature individual */}
      <AlertDialog open={featureDialog !== null} onOpenChange={() => setFeatureDialog(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {featureDialog?.action === 'enable' ? 'Habilitar' : 'Desabilitar'}{' '}
              {featureDialog && FEATURE_INFO[featureDialog.feature].title}?
            </AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div>
                {featureDialog?.action === 'enable' ? (
                  <p>
                    Esta feature passara a ser executada automaticamente nos proximos ciclos do
                    scheduler.
                  </p>
                ) : (
                  <p>
                    Esta feature sera desabilitada e nao executara mais automaticamente. Voce pode
                    reativar a qualquer momento.
                  </p>
                )}
                <p className="mt-4 text-xs text-gray-500">
                  {featureDialog && FEATURE_INFO[featureDialog.feature].description}
                </p>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={() =>
                featureDialog &&
                handleFeatureToggle(featureDialog.feature, featureDialog.action === 'enable')
              }
              disabled={updating}
              className={
                featureDialog?.action === 'enable' ? 'bg-status-success-solid hover:bg-status-success-solid-hover' : ''
              }
            >
              {updating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : featureDialog?.action === 'enable' ? (
                'Habilitar'
              ) : (
                'Desabilitar'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

interface FeatureToggleCardProps {
  featureKey: FeatureKey
  title: string
  description: string
  enabled: boolean
  isPilotMode: boolean
  onToggle: (action: 'enable' | 'disable') => void
}

function FeatureToggleCard({
  title,
  description,
  enabled,
  isPilotMode,
  onToggle,
}: FeatureToggleCardProps) {
  // Em modo piloto, features aparecem desabilitadas visualmente
  const isEffectivelyEnabled = !isPilotMode && enabled

  return (
    <div
      className={`rounded-lg border p-3 ${
        isEffectivelyEnabled
          ? 'border-status-success-border bg-status-success'
          : isPilotMode
            ? 'border-status-warning-border bg-status-warning/50'
            : 'border-muted bg-status-neutral'
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isEffectivelyEnabled ? (
            <CheckCircle2 className="h-4 w-4 text-status-success-foreground" />
          ) : isPilotMode ? (
            <AlertTriangle className="h-4 w-4 text-status-warning-foreground" />
          ) : (
            <div className="h-4 w-4 rounded-full border-2 border-muted-foreground" />
          )}
          <span
            className={`font-medium ${
              isEffectivelyEnabled
                ? 'text-status-success-foreground'
                : isPilotMode
                  ? 'text-status-warning-foreground'
                  : 'text-muted-foreground'
            }`}
          >
            {title}
          </span>
        </div>

        <Switch
          checked={enabled}
          disabled={isPilotMode}
          onCheckedChange={(checked) => {
            onToggle(checked ? 'enable' : 'disable')
          }}
        />
      </div>
      <p
        className={`mt-1 text-xs ${
          isEffectivelyEnabled
            ? 'text-status-success-foreground/80'
            : isPilotMode
              ? 'text-status-warning-foreground/80'
              : 'text-muted-foreground'
        }`}
      >
        {description}
        {isPilotMode && ' (bloqueado pelo Modo Piloto)'}
      </p>
    </div>
  )
}
