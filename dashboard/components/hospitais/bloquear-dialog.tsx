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
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { useToast } from '@/hooks/use-toast'
import { Check, ChevronsUpDown, AlertTriangle, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Hospital {
  id: string
  nome: string
  cidade: string
  vagas_abertas?: number
}

interface BloquearHospitalDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}

export function BloquearHospitalDialog({
  open,
  onOpenChange,
  onSuccess,
}: BloquearHospitalDialogProps) {
  const { toast } = useToast()
  const [hospitais, setHospitais] = useState<Hospital[]>([])
  const [selectedHospital, setSelectedHospital] = useState<Hospital | null>(null)
  const [motivo, setMotivo] = useState('')
  const [comboOpen, setComboOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [loadingHospitais, setLoadingHospitais] = useState(true)

  useEffect(() => {
    async function carregarHospitais() {
      try {
        const res = await fetch('/api/hospitais?excluir_bloqueados=true')
        const data = await res.json()
        setHospitais(data)
      } catch (error) {
        console.error('Erro ao carregar hospitais:', error)
      } finally {
        setLoadingHospitais(false)
      }
    }

    if (open) {
      setLoadingHospitais(true)
      carregarHospitais()
      setSelectedHospital(null)
      setMotivo('')
    }
  }, [open])

  const handleSubmit = async () => {
    if (!selectedHospital || !motivo.trim()) return

    setLoading(true)

    try {
      const res = await fetch('/api/hospitais/bloquear', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          hospital_id: selectedHospital.id,
          motivo: motivo.trim(),
        }),
      })

      if (!res.ok) {
        const error = await res.json()
        throw new Error(error.detail || 'Erro ao bloquear')
      }

      const data = await res.json()

      toast({
        title: 'Hospital bloqueado',
        description: `${selectedHospital.nome} foi bloqueado. ${data.vagas_movidas} vaga(s) movida(s).`,
      })

      onOpenChange(false)
      onSuccess()
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Erro',
        description: error instanceof Error ? error.message : 'Erro desconhecido',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Bloquear Hospital</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Seletor de hospital */}
          <div className="space-y-2">
            <Label>Hospital</Label>
            <Popover open={comboOpen} onOpenChange={setComboOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  role="combobox"
                  aria-expanded={comboOpen}
                  className="w-full justify-between"
                >
                  {selectedHospital ? selectedHospital.nome : 'Selecione um hospital...'}
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-full p-0" align="start">
                <Command>
                  <CommandInput placeholder="Buscar hospital..." />
                  <CommandList>
                    <CommandEmpty>
                      {loadingHospitais ? 'Carregando...' : 'Nenhum hospital encontrado'}
                    </CommandEmpty>
                    <CommandGroup className="max-h-[200px] overflow-auto">
                      {hospitais.map((hospital) => (
                        <CommandItem
                          key={hospital.id}
                          value={hospital.nome}
                          onSelect={() => {
                            setSelectedHospital(hospital)
                            setComboOpen(false)
                          }}
                        >
                          <Check
                            className={cn(
                              'mr-2 h-4 w-4',
                              selectedHospital?.id === hospital.id ? 'opacity-100' : 'opacity-0'
                            )}
                          />
                          <div className="flex flex-col">
                            <span>{hospital.nome}</span>
                            <span className="text-xs text-gray-500">
                              {hospital.cidade} • {hospital.vagas_abertas ?? 0} vagas
                            </span>
                          </div>
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>

          {/* Motivo */}
          <div className="space-y-2">
            <Label htmlFor="motivo">Motivo do bloqueio *</Label>
            <Textarea
              id="motivo"
              placeholder="Ex: Problemas de pagamento, reforma em andamento..."
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              rows={3}
            />
          </div>

          {/* Alerta de impacto */}
          {selectedHospital && (selectedHospital.vagas_abertas ?? 0) > 0 && (
            <div className="flex items-start gap-2 rounded-lg border border-yellow-200 bg-yellow-50 p-3">
              <AlertTriangle className="mt-0.5 h-4 w-4 text-yellow-600" />
              <p className="text-sm text-yellow-800">
                Este hospital tem{' '}
                <strong>{selectedHospital.vagas_abertas} vaga(s) aberta(s)</strong> que serao
                movidas para a tabela de bloqueados.
              </p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit} disabled={!selectedHospital || !motivo.trim() || loading}>
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Bloqueando...
              </>
            ) : (
              'Bloquear Hospital'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
