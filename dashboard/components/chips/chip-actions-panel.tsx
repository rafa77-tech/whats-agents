/**
 * Chip Actions Panel - Sprint 36 + Sprint 41 (Reactivate & QR Code)
 *
 * Painel de ações disponíveis para o chip.
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { chipsApi } from '@/lib/api/chips'
import { ChipFullDetail } from '@/types/chips'
import {
  Pause,
  Play,
  TrendingUp,
  AlertTriangle,
  Loader2,
  RotateCcw,
  QrCode,
  CheckCircle2,
  RefreshCw,
  Wifi,
} from 'lucide-react'

interface ChipActionsPanelProps {
  chip: ChipFullDetail
  onActionComplete: () => void
}

type ActionType = 'pause' | 'resume' | 'promote' | 'reactivate' | 'qrcode'

interface ActionConfig {
  label: string
  description: string
  confirmLabel: string
  icon: typeof Pause
  variant: 'default' | 'outline' | 'destructive'
  condition: (chip: ChipFullDetail) => boolean
  requiresInput?: boolean
}

const actionsConfig: Record<Exclude<ActionType, 'qrcode'>, ActionConfig> = {
  pause: {
    label: 'Pausar Chip',
    description:
      'Ao pausar o chip, ele deixará de enviar e receber mensagens até ser retomado manualmente.',
    confirmLabel: 'Pausar',
    icon: Pause,
    variant: 'outline',
    condition: (chip) =>
      !['paused', 'banned', 'cancelled', 'pending', 'provisioned'].includes(chip.status),
  },
  resume: {
    label: 'Retomar Chip',
    description: 'Ao retomar o chip, ele voltará a enviar e receber mensagens normalmente.',
    confirmLabel: 'Retomar',
    icon: Play,
    variant: 'default',
    condition: (chip) => chip.status === 'paused',
  },
  promote: {
    label: 'Promover Fase',
    description:
      'Promover o chip para a próxima fase de warmup. Isso aumentará os limites de mensagens.',
    confirmLabel: 'Promover',
    icon: TrendingUp,
    variant: 'default',
    condition: (chip) =>
      chip.status === 'warming' && chip.warmupPhase !== 'operacao' && chip.trustScore >= 70,
  },
  reactivate: {
    label: 'Reativar Chip',
    description:
      'Reativar um chip banido ou cancelado. Informe o motivo da reativação (ex: "Recurso aprovado pelo WhatsApp").',
    confirmLabel: 'Reativar',
    icon: RotateCcw,
    variant: 'default',
    condition: (chip) => chip.status === 'banned' || chip.status === 'cancelled',
    requiresInput: true,
  },
}

export function ChipActionsPanel({ chip, onActionComplete }: ChipActionsPanelProps) {
  const [confirmAction, setConfirmAction] = useState<ActionType | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [reactivateMotivo, setReactivateMotivo] = useState('')

  // QR Code state
  const [showQRCode, setShowQRCode] = useState(false)
  const [qrCodeData, setQRCodeData] = useState<string | null>(null)
  const [pairingCode, setPairingCode] = useState<string | null>(null)
  const [connectionState, setConnectionState] = useState<string>('close')
  const [isLoadingQR, setIsLoadingQR] = useState(false)
  const [qrError, setQrError] = useState<string | null>(null)

  // Connection check state
  const [isCheckingConnection, setIsCheckingConnection] = useState(false)
  const [connectionResult, setConnectionResult] = useState<string | null>(null)

  // Fetch QR code
  const fetchQRCode = useCallback(async () => {
    if (!chip.instanceName) {
      setQrError('Instância não configurada')
      return
    }

    setIsLoadingQR(true)
    setQrError(null)

    try {
      const result = await chipsApi.getInstanceQRCode(chip.instanceName)
      setQRCodeData(result.qrCode)
      setPairingCode(result.pairingCode || null)
      setConnectionState(result.state)

      if (result.state === 'open') {
        // Connected! Refresh chip data
        onActionComplete()
      }
    } catch (err) {
      console.error('Error fetching QR code:', err)
      setQrError('Erro ao obter QR code')
    } finally {
      setIsLoadingQR(false)
    }
  }, [chip.instanceName, onActionComplete])

  // Auto-refresh QR code when dialog is open
  useEffect(() => {
    if (!showQRCode) return

    fetchQRCode()

    // Refresh every 10 seconds while dialog is open
    const interval = setInterval(() => {
      if (connectionState !== 'open') {
        fetchQRCode()
      }
    }, 10000)

    return () => clearInterval(interval)
  }, [showQRCode, connectionState, fetchQRCode])

  const handleAction = async (action: Exclude<ActionType, 'qrcode'>) => {
    setIsProcessing(true)
    setError(null)

    try {
      let result

      if (action === 'reactivate') {
        if (!reactivateMotivo.trim()) {
          setError('Informe o motivo da reativação')
          setIsProcessing(false)
          return
        }
        result = await chipsApi.reactivateChip(chip.id, reactivateMotivo.trim())
      } else {
        const actionFn = {
          pause: chipsApi.pauseChip,
          resume: chipsApi.resumeChip,
          promote: chipsApi.promoteChip,
        }[action]

        result = await actionFn(chip.id)
      }

      if (result.success) {
        setReactivateMotivo('')
        onActionComplete()
      } else {
        setError(result.message || 'Ação falhou')
      }
    } catch (err) {
      console.error('Action failed:', err)
      setError('Erro ao executar ação')
    } finally {
      setIsProcessing(false)
      setConfirmAction(null)
    }
  }

  const handleOpenQRCode = () => {
    setShowQRCode(true)
    setQRCodeData(null)
    setConnectionState('close')
    setQrError(null)
  }

  const handleCheckConnection = async () => {
    setIsCheckingConnection(true)
    setConnectionResult(null)
    setError(null)

    try {
      const result = await chipsApi.checkChipConnection(chip.id)

      if (result.connected) {
        if (result.status_atualizado) {
          setConnectionResult(`Conectado! Status atualizado para ${result.novo_status}.`)
          onActionComplete() // Refresh chip data
        } else {
          setConnectionResult(`Conectado (${result.state})`)
        }
      } else {
        setConnectionResult(`Desconectado: ${result.message}`)
      }
    } catch (err) {
      console.error('Check connection failed:', err)
      setError('Erro ao verificar conexão')
    } finally {
      setIsCheckingConnection(false)
    }
  }

  const availableActions = (Object.keys(actionsConfig) as Exclude<ActionType, 'qrcode'>[]).filter(
    (action) => actionsConfig[action].condition(chip)
  )

  // Show QR Code button for pending/offline chips
  const canShowQRCode =
    chip.instanceName && ['pending', 'offline', 'provisioned'].includes(chip.status)

  const config = confirmAction && confirmAction !== 'qrcode' ? actionsConfig[confirmAction] : null

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Ações</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {error && (
            <div className="mb-2 rounded-md border border-status-error-border bg-status-error/10 p-3">
              <div className="flex items-center gap-2 text-status-error-foreground">
                <AlertTriangle className="h-4 w-4" />
                <span className="text-sm">{error}</span>
              </div>
            </div>
          )}

          {/* Check Connection button - for pending chips */}
          {chip.instanceName && chip.status === 'pending' && (
            <Button
              variant="default"
              className="w-full justify-start"
              onClick={handleCheckConnection}
              disabled={isCheckingConnection || isProcessing}
            >
              {isCheckingConnection ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Wifi className="mr-2 h-4 w-4" />
              )}
              Verificar Conexão
            </Button>
          )}

          {/* Connection result feedback */}
          {connectionResult && (
            <div
              className={`rounded-md border p-3 ${
                connectionResult.includes('Conectado!')
                  ? 'border-status-success-border bg-status-success/10 text-status-success-foreground'
                  : connectionResult.includes('Conectado')
                    ? 'border-status-info-border bg-status-info/10 text-status-info-foreground'
                    : 'border-status-warning-border bg-status-warning/10 text-status-warning-foreground'
              }`}
            >
              <p className="text-sm">{connectionResult}</p>
            </div>
          )}

          {/* QR Code button - special action */}
          {canShowQRCode && (
            <Button
              variant="outline"
              className="w-full justify-start"
              onClick={handleOpenQRCode}
              disabled={isProcessing}
            >
              <QrCode className="mr-2 h-4 w-4" />
              Gerar QR Code
            </Button>
          )}

          {/* Standard actions */}
          {availableActions.length === 0 && !canShowQRCode ? (
            <p className="py-2 text-sm text-muted-foreground">
              Nenhuma ação disponível para este chip no momento.
            </p>
          ) : (
            availableActions.map((action) => {
              const actionConfig = actionsConfig[action]
              const Icon = actionConfig.icon

              return (
                <Button
                  key={action}
                  variant={actionConfig.variant}
                  className="w-full justify-start"
                  onClick={() => setConfirmAction(action)}
                  disabled={isProcessing}
                >
                  <Icon className="mr-2 h-4 w-4" />
                  {actionConfig.label}
                </Button>
              )
            })
          )}

          {/* Status info for banned chips */}
          {chip.status === 'banned' && (
            <div className="mt-4 rounded-md border border-status-warning-border bg-status-warning/10 p-3">
              <div className="flex items-start gap-2 text-status-warning-foreground">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <div>
                  <span className="text-sm font-medium">Chip Banido</span>
                  <p className="mt-1 text-xs opacity-80">
                    Se o chip voltou a funcionar após recurso, use &quot;Reativar Chip&quot; acima.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Status info for cancelled chips */}
          {chip.status === 'cancelled' && (
            <div className="mt-4 rounded-md border border-border bg-muted/50 p-3">
              <div className="flex items-start gap-2 text-muted-foreground">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <div>
                  <span className="text-sm font-medium">Chip Cancelado</span>
                  <p className="mt-1 text-xs opacity-80">
                    Use &quot;Reativar Chip&quot; para voltar a usar este número.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Status info for pending chips */}
          {chip.status === 'pending' && (
            <div className="mt-4 rounded-md border border-status-info-border bg-status-info/10 p-3">
              <div className="flex items-start gap-2 text-status-info-foreground">
                <QrCode className="mt-0.5 h-4 w-4 shrink-0" />
                <div>
                  <span className="text-sm font-medium">Aguardando Conexão</span>
                  <p className="mt-1 text-xs opacity-80">
                    Clique em &quot;Gerar QR Code&quot; para conectar o WhatsApp.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Warmup info */}
          {chip.status === 'warming' && chip.warmupPhase && (
            <div className="mt-4 rounded-md border border-status-info-border bg-status-info/10 p-3">
              <span className="text-sm text-status-info-foreground">
                Em aquecimento - Dia {chip.warmingDay}
              </span>
              {chip.trustScore < 70 && (
                <p className="mt-1 text-xs text-status-info-foreground opacity-80">
                  Trust score precisa ser &ge; 70 para promoção
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Confirmation dialog for standard actions */}
      <AlertDialog
        open={!!confirmAction && confirmAction !== 'qrcode'}
        onOpenChange={() => {
          setConfirmAction(null)
          setReactivateMotivo('')
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{config?.label}</AlertDialogTitle>
            <AlertDialogDescription>{config?.description}</AlertDialogDescription>
          </AlertDialogHeader>

          {/* Motivo input for reactivate */}
          {confirmAction === 'reactivate' && (
            <div className="space-y-2 py-2">
              <Label htmlFor="reactivate-motivo">Motivo da reativação *</Label>
              <Textarea
                id="reactivate-motivo"
                placeholder="Ex: Recurso aprovado pelo WhatsApp, Número reconectado..."
                value={reactivateMotivo}
                onChange={(e) => setReactivateMotivo(e.target.value)}
                rows={3}
              />
            </div>
          )}

          <AlertDialogFooter>
            <AlertDialogCancel disabled={isProcessing}>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={() =>
                confirmAction && confirmAction !== 'qrcode' && handleAction(confirmAction)
              }
              disabled={
                isProcessing || (confirmAction === 'reactivate' && !reactivateMotivo.trim())
              }
            >
              {isProcessing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Processando...
                </>
              ) : (
                config?.confirmLabel
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* QR Code Dialog */}
      <Dialog open={showQRCode} onOpenChange={setShowQRCode}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Conectar WhatsApp</DialogTitle>
            <DialogDescription>
              Escaneie o QR Code com o WhatsApp do número {chip.telefone}
            </DialogDescription>
          </DialogHeader>

          <div className="flex flex-col items-center gap-4 py-4">
            {isLoadingQR && !qrCodeData && (
              <div className="flex h-64 w-64 items-center justify-center rounded-lg border bg-muted/50">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            )}

            {qrError && (
              <div className="flex h-64 w-64 flex-col items-center justify-center rounded-lg border border-status-error-border bg-status-error/10 p-4 text-center">
                <AlertTriangle className="mb-2 h-8 w-8 text-status-error-foreground" />
                <p className="text-sm text-status-error-foreground">{qrError}</p>
                <Button variant="outline" size="sm" className="mt-4" onClick={fetchQRCode}>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Tentar novamente
                </Button>
              </div>
            )}

            {connectionState === 'open' && (
              <div className="flex h-64 w-64 flex-col items-center justify-center rounded-lg border border-status-success-border bg-status-success/10 p-4 text-center">
                <CheckCircle2 className="mb-2 h-12 w-12 text-status-success-solid" />
                <p className="font-medium text-status-success-foreground">Conectado!</p>
                <p className="mt-1 text-sm text-status-success-foreground opacity-80">
                  WhatsApp pareado com sucesso.
                </p>
              </div>
            )}

            {qrCodeData && connectionState !== 'open' && (
              <>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={
                    qrCodeData.startsWith('data:')
                      ? qrCodeData
                      : `data:image/png;base64,${qrCodeData}`
                  }
                  alt="QR Code WhatsApp"
                  className="h-64 w-64 rounded-lg border"
                />
                {pairingCode && (
                  <div className="rounded-md bg-muted px-4 py-2 text-center">
                    <p className="text-xs text-muted-foreground">Código de pareamento</p>
                    <p className="font-mono text-lg font-bold tracking-wider">{pairingCode}</p>
                  </div>
                )}
                <p className="text-center text-xs text-muted-foreground">
                  O QR Code será atualizado automaticamente a cada 10 segundos.
                </p>
              </>
            )}

            {!qrCodeData && !qrError && !isLoadingQR && connectionState !== 'open' && (
              <div className="flex h-64 w-64 flex-col items-center justify-center rounded-lg border bg-muted/50 p-4 text-center">
                <QrCode className="mb-2 h-8 w-8 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">Aguardando QR Code...</p>
                <Button variant="outline" size="sm" className="mt-4" onClick={fetchQRCode}>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Gerar QR Code
                </Button>
              </div>
            )}
          </div>

          {connectionState !== 'open' && (
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowQRCode(false)}>
                Fechar
              </Button>
              <Button onClick={fetchQRCode} disabled={isLoadingQR}>
                {isLoadingQR ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Carregando...
                  </>
                ) : (
                  <>
                    <RefreshCw className="mr-2 h-4 w-4" />
                    Atualizar
                  </>
                )}
              </Button>
            </div>
          )}

          {connectionState === 'open' && (
            <div className="flex justify-end">
              <Button onClick={() => setShowQRCode(false)}>Fechar</Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}
