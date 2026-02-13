'use client'

/**
 * Create Instance Dialog - Sprint 40
 *
 * Dialog para criar nova instancia WhatsApp.
 * Fluxo em 3 etapas:
 * 1. Formulario com telefone e nome
 * 2. Exibicao do QR code com polling de conexao
 * 3. Confirmacao de sucesso
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'
import { Loader2, CheckCircle2, QrCode, Phone, AlertCircle } from 'lucide-react'
import { chipsApi } from '@/lib/api/chips'
import type { ConnectionStateResponse } from '@/types/chips'

type DialogStep = 'form' | 'qrcode' | 'success'

interface CreateInstanceDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}

export function CreateInstanceDialog({ open, onOpenChange, onSuccess }: CreateInstanceDialogProps) {
  // State
  const [step, setStep] = useState<DialogStep>('form')
  const [loading, setLoading] = useState(false)
  const [telefone, setTelefone] = useState('')
  const [instanceName, setInstanceName] = useState('')
  const [createdInstanceName, setCreatedInstanceName] = useState<string | null>(null)
  const [_createdChipId, setCreatedChipId] = useState<string | null>(null)
  const [qrCode, setQrCode] = useState<string | null>(null)
  const [qrRawCode, setQrRawCode] = useState<string | null>(null)
  const [qrState, setQrState] = useState<string>('close')
  const [pairingCode, setPairingCode] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Refs for polling
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const qrRefreshIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // Clean up intervals on unmount or dialog close
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
      }
      if (qrRefreshIntervalRef.current) {
        clearInterval(qrRefreshIntervalRef.current)
      }
    }
  }, [])

  // Reset state when dialog closes
  useEffect(() => {
    if (!open) {
      setTimeout(() => {
        setStep('form')
        setLoading(false)
        setTelefone('')
        setInstanceName('')
        setCreatedInstanceName(null)
        setCreatedChipId(null)
        setQrCode(null)
        setQrRawCode(null)
        setQrState('close')
        setPairingCode(null)
        setError(null)
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current)
          pollIntervalRef.current = null
        }
        if (qrRefreshIntervalRef.current) {
          clearInterval(qrRefreshIntervalRef.current)
          qrRefreshIntervalRef.current = null
        }
      }, 200)
    }
  }, [open])

  // Format phone number for display
  const formatPhoneDisplay = (value: string): string => {
    const digits = value.replace(/\D/g, '')
    if (digits.length <= 2) return digits
    if (digits.length <= 7) return `(${digits.slice(0, 2)}) ${digits.slice(2)}`
    if (digits.length <= 11)
      return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`
    return `+${digits.slice(0, 2)} (${digits.slice(2, 4)}) ${digits.slice(4, 9)}-${digits.slice(9, 13)}`
  }

  // Handle phone input
  const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/\D/g, '')
    if (value.length <= 13) {
      setTelefone(value)
    }
  }

  // Check connection state
  const checkConnectionState = useCallback(async (name: string) => {
    try {
      const result: ConnectionStateResponse = await chipsApi.getInstanceConnectionState(name)

      if (result.connected) {
        setStep('success')
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current)
          pollIntervalRef.current = null
        }
        if (qrRefreshIntervalRef.current) {
          clearInterval(qrRefreshIntervalRef.current)
          qrRefreshIntervalRef.current = null
        }
        toast.success('WhatsApp conectado com sucesso!')
      }
    } catch (err) {
      console.error('Error checking connection:', err)
    }
  }, [])

  // Handle form submit
  const handleSubmit = async () => {
    setLoading(true)
    setError(null)

    try {
      // Validate phone
      if (telefone.length < 10 || telefone.length > 13) {
        setError('Telefone invalido. Use formato: 5511999999999')
        setLoading(false)
        return
      }

      // Create instance
      const requestData: { telefone: string; instanceName?: string } = { telefone }
      if (instanceName) {
        requestData.instanceName = instanceName
      }
      const result = await chipsApi.createInstance(requestData)

      setCreatedInstanceName(result.instanceName)
      setCreatedChipId(result.chipId)

      // Use QR code from create response directly
      // IMPORTANT: Do NOT call /instance/connect - it triggers a new connection
      // attempt and puts the instance into "connecting" state prematurely
      if (result.code) {
        setQrRawCode(result.code)
      }
      if (result.qrCode) {
        setQrCode(result.qrCode)
      }
      if (result.pairingCode) {
        setPairingCode(result.pairingCode)
      }

      // Move to QR code step
      setStep('qrcode')

      // Poll connection state only (doesn't regenerate QR or trigger connect)
      pollIntervalRef.current = setInterval(() => {
        checkConnectionState(result.instanceName)
      }, 3000)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erro ao criar instancia'
      setError(errorMessage)
      toast.error('Erro ao criar instancia', { description: errorMessage })
    } finally {
      setLoading(false)
    }
  }

  // Handle success close
  const handleSuccessClose = () => {
    onSuccess()
    onOpenChange(false)
  }

  // Validate form
  const canSubmit = telefone.length >= 10 && telefone.length <= 13

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        {/* Step 1: Form */}
        {step === 'form' && (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Phone className="h-5 w-5" />
                Nova Instancia WhatsApp
              </DialogTitle>
              <DialogDescription>
                Crie uma nova instancia para conectar um numero ao sistema Julia.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="telefone">Telefone</Label>
                <Input
                  id="telefone"
                  placeholder="5511999999999"
                  value={formatPhoneDisplay(telefone)}
                  onChange={handlePhoneChange}
                  disabled={loading}
                />
                <p className="text-xs text-muted-foreground">
                  Inclua o codigo do pais (55) e DDD. Ex: 5511999999999
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="instanceName">Nome da Instancia (opcional)</Label>
                <Input
                  id="instanceName"
                  placeholder="Gerado automaticamente"
                  value={instanceName}
                  onChange={(e) => setInstanceName(e.target.value)}
                  disabled={loading}
                />
                <p className="text-xs text-muted-foreground">
                  Se vazio, sera gerado como julia_TELEFONE
                </p>
              </div>

              {error && (
                <div className="flex items-center gap-2 rounded-md bg-status-error/10 p-3 text-sm text-status-error-foreground">
                  <AlertCircle className="h-4 w-4" />
                  {error}
                </div>
              )}
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
                Cancelar
              </Button>
              <Button onClick={handleSubmit} disabled={!canSubmit || loading}>
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Criando...
                  </>
                ) : (
                  'Criar Instancia'
                )}
              </Button>
            </DialogFooter>
          </>
        )}

        {/* Step 2: QR Code */}
        {step === 'qrcode' && (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <QrCode className="h-5 w-5" />
                Escanear QR Code
              </DialogTitle>
              <DialogDescription>
                Abra o WhatsApp no celular e escaneie o QR code abaixo.
              </DialogDescription>
            </DialogHeader>

            <div className="flex flex-col items-center space-y-4 py-4">
              {qrRawCode || qrCode ? (
                <div className="rounded-lg border-2 border-border bg-card p-4">
                  {qrRawCode ? (
                    <QRCodeSVG value={qrRawCode} size={256} level="M" />
                  ) : (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img
                      src={
                        qrCode!.startsWith('data:') ? qrCode! : `data:image/png;base64,${qrCode}`
                      }
                      alt="QR Code"
                      className="h-64 w-64"
                    />
                  )}
                </div>
              ) : (
                <div className="flex h-64 w-64 items-center justify-center rounded-lg border-2 border-dashed border-muted">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              )}

              <div className="text-center">
                <p className="text-sm text-muted-foreground">
                  Instancia: <span className="font-medium">{createdInstanceName}</span>
                </p>
                <p className="mt-1 flex items-center justify-center gap-2 text-sm">
                  <span
                    className={`h-2 w-2 rounded-full ${
                      qrState === 'open'
                        ? 'bg-status-success-solid'
                        : qrState === 'connecting'
                          ? 'bg-status-warning-solid'
                          : 'bg-muted-foreground'
                    }`}
                  />
                  {qrState === 'open'
                    ? 'Conectado'
                    : qrState === 'connecting'
                      ? 'Conectando...'
                      : 'Aguardando scan'}
                </p>
              </div>

              {pairingCode && (
                <div className="rounded-lg bg-muted px-4 py-2 text-center">
                  <p className="text-xs text-muted-foreground">Codigo de pareamento</p>
                  <p className="font-mono text-lg font-bold">{pairingCode}</p>
                </div>
              )}

              <p className="text-center text-xs text-muted-foreground">
                Escaneie o QR code com o WhatsApp do celular
              </p>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancelar
              </Button>
            </DialogFooter>
          </>
        )}

        {/* Step 3: Success */}
        {step === 'success' && (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-status-success-foreground">
                <CheckCircle2 className="h-5 w-5" />
                Instancia Conectada
              </DialogTitle>
            </DialogHeader>

            <div className="flex flex-col items-center space-y-4 py-6">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-status-success">
                <CheckCircle2 className="h-8 w-8 text-status-success-foreground" />
              </div>

              <div className="text-center">
                <p className="text-lg font-medium">WhatsApp conectado com sucesso!</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  O chip esta pronto para entrar em fase de aquecimento.
                </p>
              </div>

              <div className="w-full rounded-lg bg-muted/50 p-4">
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Instancia:</span>
                    <span className="font-medium">{createdInstanceName}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Telefone:</span>
                    <span className="font-medium">{formatPhoneDisplay(telefone)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Status:</span>
                    <span className="font-medium text-status-success-foreground">Conectado</span>
                  </div>
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button onClick={handleSuccessClose} className="w-full">
                Concluir
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
