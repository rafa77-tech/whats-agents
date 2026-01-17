'use client'

import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { useApiError } from '@/hooks/use-api-error'
import { toast } from 'sonner'
import { Loader2 } from 'lucide-react'

type TipoDiretriz = 'margem_negociacao' | 'regra_especial' | 'info_adicional'
type Escopo = 'vaga' | 'medico' | 'hospital' | 'especialidade' | 'global'

interface NovaInstrucaoDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}

interface Hospital {
  id: string
  nome: string
}

interface Especialidade {
  id: string
  nome: string
}

export function NovaInstrucaoDialog({ open, onOpenChange, onSuccess }: NovaInstrucaoDialogProps) {
  const { handleError } = useApiError()
  const [loading, setLoading] = useState(false)
  const [tipo, setTipo] = useState<TipoDiretriz>('margem_negociacao')
  const [escopo, setEscopo] = useState<Escopo>('global')

  // Referencias do escopo
  const [hospitalId, setHospitalId] = useState<string>('')
  const [especialidadeId, setEspecialidadeId] = useState<string>('')

  // Listas para selecao
  const [hospitais, setHospitais] = useState<Hospital[]>([])
  const [especialidades, setEspecialidades] = useState<Especialidade[]>([])
  const [loadingListas, setLoadingListas] = useState(false)

  // Conteudo
  const [valorMaximo, setValorMaximo] = useState<string>('')
  const [percentualMaximo, setPercentualMaximo] = useState<string>('')
  const [regra, setRegra] = useState<string>('')
  const [info, setInfo] = useState<string>('')

  // Expiracao
  const [expiraEm, setExpiraEm] = useState<string>('')

  useEffect(() => {
    if (open) {
      setLoadingListas(true)
      Promise.all([
        fetch('/api/hospitais').then((r) => r.json()),
        fetch('/api/especialidades').then((r) => r.json()),
      ])
        .then(([h, e]) => {
          setHospitais(h)
          setEspecialidades(e)
        })
        .catch(console.error)
        .finally(() => setLoadingListas(false))
    }
  }, [open])

  const resetForm = () => {
    setTipo('margem_negociacao')
    setEscopo('global')
    setHospitalId('')
    setEspecialidadeId('')
    setValorMaximo('')
    setPercentualMaximo('')
    setRegra('')
    setInfo('')
    setExpiraEm('')
  }

  const handleSubmit = async () => {
    setLoading(true)

    try {
      const conteudo: Record<string, unknown> = {}

      if (tipo === 'margem_negociacao') {
        if (valorMaximo) conteudo.valor_maximo = Number(valorMaximo)
        if (percentualMaximo) conteudo.percentual_maximo = Number(percentualMaximo)
      } else if (tipo === 'regra_especial') {
        conteudo.regra = regra
      } else if (tipo === 'info_adicional') {
        conteudo.info = info
      }

      const payload: Record<string, unknown> = {
        tipo,
        escopo,
        conteudo,
      }

      if (escopo === 'hospital' && hospitalId) payload.hospital_id = hospitalId
      if (escopo === 'especialidade' && especialidadeId) payload.especialidade_id = especialidadeId
      if (expiraEm) payload.expira_em = new Date(expiraEm).toISOString()

      const res = await fetch('/api/diretrizes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!res.ok) {
        await handleError({ response: res })
        return
      }

      toast.success('Instrucao criada', {
        description: 'Julia seguira esta diretriz a partir de agora.',
      })

      resetForm()
      onOpenChange(false)
      onSuccess()
    } catch (error) {
      await handleError({ error: error instanceof Error ? error : undefined })
    } finally {
      setLoading(false)
    }
  }

  const canSubmit = (): boolean => {
    // Validar escopo
    if (escopo === 'hospital' && !hospitalId) return false
    if (escopo === 'especialidade' && !especialidadeId) return false

    // Validar conteudo
    if (tipo === 'margem_negociacao' && !valorMaximo && !percentualMaximo) return false
    if (tipo === 'regra_especial' && !regra.trim()) return false
    if (tipo === 'info_adicional' && !info.trim()) return false

    return true
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Nova Instrucao</DialogTitle>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Tipo de instrucao */}
          <div className="space-y-2">
            <Label>Tipo de instrucao</Label>
            <RadioGroup value={tipo} onValueChange={(v) => setTipo(v as TipoDiretriz)}>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="margem_negociacao" id="margem" />
                <Label htmlFor="margem" className="font-normal">
                  Margem de Negociacao
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="regra_especial" id="regra" />
                <Label htmlFor="regra" className="font-normal">
                  Regra Especial
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="info_adicional" id="info" />
                <Label htmlFor="info" className="font-normal">
                  Informacao Adicional
                </Label>
              </div>
            </RadioGroup>
          </div>

          {/* Escopo */}
          <div className="space-y-2">
            <Label>Aplica-se a</Label>
            <Select value={escopo} onValueChange={(v) => setEscopo(v as Escopo)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="global">Todas as conversas</SelectItem>
                <SelectItem value="hospital">Hospital especifico</SelectItem>
                <SelectItem value="especialidade">Especialidade</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Seletor baseado no escopo */}
          {escopo === 'hospital' && (
            <div className="space-y-2">
              <Label>Hospital</Label>
              <Select value={hospitalId} onValueChange={setHospitalId}>
                <SelectTrigger>
                  <SelectValue
                    placeholder={loadingListas ? 'Carregando...' : 'Selecione o hospital'}
                  />
                </SelectTrigger>
                <SelectContent>
                  {hospitais.map((h) => (
                    <SelectItem key={h.id} value={h.id}>
                      {h.nome}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {escopo === 'especialidade' && (
            <div className="space-y-2">
              <Label>Especialidade</Label>
              <Select value={especialidadeId} onValueChange={setEspecialidadeId}>
                <SelectTrigger>
                  <SelectValue
                    placeholder={loadingListas ? 'Carregando...' : 'Selecione a especialidade'}
                  />
                </SelectTrigger>
                <SelectContent>
                  {especialidades.map((e) => (
                    <SelectItem key={e.id} value={e.id}>
                      {e.nome}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Conteudo baseado no tipo */}
          {tipo === 'margem_negociacao' && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Valor maximo (R$)</Label>
                <Input
                  type="number"
                  placeholder="Ex: 3000"
                  value={valorMaximo}
                  onChange={(e) => setValorMaximo(e.target.value)}
                />
              </div>
              <div className="text-center text-gray-400">ou</div>
              <div className="space-y-2">
                <Label>Percentual maximo acima do base (%)</Label>
                <Input
                  type="number"
                  placeholder="Ex: 15"
                  value={percentualMaximo}
                  onChange={(e) => setPercentualMaximo(e.target.value)}
                />
              </div>
            </div>
          )}

          {tipo === 'regra_especial' && (
            <div className="space-y-2">
              <Label>Regra</Label>
              <Textarea
                placeholder="Ex: Pode flexibilizar horario de entrada em ate 1 hora"
                value={regra}
                onChange={(e) => setRegra(e.target.value)}
                rows={3}
              />
            </div>
          )}

          {tipo === 'info_adicional' && (
            <div className="space-y-2">
              <Label>Informacao</Label>
              <Textarea
                placeholder="Ex: Este hospital prefere medicos com experiencia em UTI"
                value={info}
                onChange={(e) => setInfo(e.target.value)}
                rows={3}
              />
            </div>
          )}

          {/* Expiracao */}
          <div className="space-y-2">
            <Label>Expira em (opcional)</Label>
            <Input
              type="datetime-local"
              value={expiraEm}
              onChange={(e) => setExpiraEm(e.target.value)}
            />
            <p className="text-xs text-gray-400">Deixe vazio para nao expirar automaticamente</p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit} disabled={!canSubmit() || loading}>
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Criando...
              </>
            ) : (
              'Criar Instrucao'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
