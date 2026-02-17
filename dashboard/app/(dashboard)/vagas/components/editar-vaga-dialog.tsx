'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
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
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { toast } from 'sonner'
import { Check, ChevronsUpDown, Loader2, Plus, User } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ShiftDetail } from '@/lib/vagas/types'

interface EditarVagaDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  shift: ShiftDetail
  onSave: (data: Record<string, unknown>) => Promise<boolean>
  saving: boolean
}

interface Hospital {
  id: string
  nome: string
}

interface Especialidade {
  id: string
  nome: string
}

interface ContatoGrupo {
  id: string
  nome: string
  telefone: string | null
  empresa: string | null
}

export function EditarVagaDialog({
  open,
  onOpenChange,
  shift,
  onSave,
  saving,
}: EditarVagaDialogProps) {
  // Form fields - initialized from shift
  const [hospitalId, setHospitalId] = useState('')
  const [especialidadeId, setEspecialidadeId] = useState('')
  const [data, setData] = useState('')
  const [horaInicio, setHoraInicio] = useState('')
  const [horaFim, setHoraFim] = useState('')
  const [valor, setValor] = useState('')
  const [contatoNome, setContatoNome] = useState('')
  const [contatoWhatsapp, setContatoWhatsapp] = useState('')
  const [contatoManual, setContatoManual] = useState(false)

  // Combobox lists
  const [hospitais, setHospitais] = useState<Hospital[]>([])
  const [especialidades, setEspecialidades] = useState<Especialidade[]>([])
  const [contatos, setContatos] = useState<ContatoGrupo[]>([])
  const [selectedHospitalData, setSelectedHospitalData] = useState<Hospital | null>(null)
  const [loadingListas, setLoadingListas] = useState(false)
  const [loadingHospitais, setLoadingHospitais] = useState(false)
  const [loadingContatos, setLoadingContatos] = useState(false)

  // Combobox open state
  const [hospitalOpen, setHospitalOpen] = useState(false)
  const [especialidadeOpen, setEspecialidadeOpen] = useState(false)
  const [contatoOpen, setContatoOpen] = useState(false)

  // Search text
  const [hospitalSearch, setHospitalSearch] = useState('')
  const [especialidadeSearch, setEspecialidadeSearch] = useState('')
  const [contatoSearch, setContatoSearch] = useState('')

  // Creating state
  const [creatingHospital, setCreatingHospital] = useState(false)
  const [creatingEspecialidade, setCreatingEspecialidade] = useState(false)

  // Refs
  const hospitalSearchRef = useRef('')
  const especialidadeSearchRef = useRef('')
  const contatoSearchRef = useRef('')

  useEffect(() => {
    hospitalSearchRef.current = hospitalSearch
  }, [hospitalSearch])
  useEffect(() => {
    especialidadeSearchRef.current = especialidadeSearch
  }, [especialidadeSearch])
  useEffect(() => {
    contatoSearchRef.current = contatoSearch
  }, [contatoSearch])

  // Initialize form from shift when dialog opens
  useEffect(() => {
    if (open && shift) {
      setHospitalId(shift.hospital_id)
      setSelectedHospitalData({ id: shift.hospital_id, nome: shift.hospital })
      setEspecialidadeId(shift.especialidade_id)
      setData(shift.data)
      setHoraInicio(shift.hora_inicio?.slice(0, 5) || '')
      setHoraFim(shift.hora_fim?.slice(0, 5) || '')
      setValor(shift.valor ? String(shift.valor) : '')
      setContatoNome(shift.contato_nome || '')
      setContatoWhatsapp(shift.contato_whatsapp || '')
      setContatoManual(false)
      setHospitalSearch('')
      setEspecialidadeSearch('')
      setContatoSearch('')
    }
  }, [open, shift])

  // Debounced hospital search (server-side)
  const searchHospitais = useCallback(async (search: string) => {
    setLoadingHospitais(true)
    try {
      const params = new URLSearchParams({ limit: '50', apenas_revisados: 'true' })
      if (search.trim()) {
        params.set('search', search.trim())
      }
      const res = await fetch(`/api/hospitais?${params}`)
      const json = await res.json()
      setHospitais(Array.isArray(json) ? json : [])
    } catch {
      setHospitais([])
    } finally {
      setLoadingHospitais(false)
    }
  }, [])

  // Load initial data when dialog opens
  useEffect(() => {
    if (open) {
      searchHospitais('')
      setLoadingListas(true)
      fetch('/api/especialidades')
        .then((r) => r.json())
        .then((e) => setEspecialidades(Array.isArray(e) ? e : []))
        .catch(console.error)
        .finally(() => setLoadingListas(false))
    }
  }, [open, searchHospitais])

  // Debounced search when typing in hospital combobox
  useEffect(() => {
    if (!hospitalOpen) return
    const timer = setTimeout(() => {
      searchHospitais(hospitalSearch)
    }, 300)
    return () => clearTimeout(timer)
  }, [hospitalSearch, hospitalOpen, searchHospitais])

  // Debounced contato search
  const searchContatos = useCallback(async (search: string) => {
    setLoadingContatos(true)
    try {
      const params = search.trim() ? `?search=${encodeURIComponent(search.trim())}` : ''
      const res = await fetch(`/api/contatos-grupo${params}`)
      const json = await res.json()
      setContatos(Array.isArray(json.data) ? json.data : [])
    } catch {
      setContatos([])
    } finally {
      setLoadingContatos(false)
    }
  }, [])

  useEffect(() => {
    if (!contatoOpen) return
    const timer = setTimeout(() => {
      searchContatos(contatoSearch)
    }, 300)
    return () => clearTimeout(timer)
  }, [contatoSearch, contatoOpen, searchContatos])

  const canSubmit = (): boolean => {
    if (!hospitalId || !especialidadeId || !data) return false
    return true
  }

  const selectedHospital = selectedHospitalData
  const selectedEspecialidade = especialidades.find((e) => e.id === especialidadeId)

  const hospitalSearchTrimmed = hospitalSearch.trim().toLowerCase()
  const showCreateHospital =
    hospitalSearchTrimmed.length > 0 &&
    !loadingHospitais &&
    !hospitais.some((h) => h.nome.toLowerCase() === hospitalSearchTrimmed)

  const especialidadeSearchTrimmed = especialidadeSearch.trim().toLowerCase()
  const showCreateEspecialidade =
    especialidadeSearchTrimmed.length > 0 &&
    !especialidades.some((e) => e.nome.toLowerCase() === especialidadeSearchTrimmed)

  const contatoSearchTrimmed = contatoSearch.trim()
  const showCreateContato =
    contatoSearchTrimmed.length > 0 &&
    !contatos.some((c) => c.nome.toLowerCase() === contatoSearchTrimmed.toLowerCase())

  const handleCreateHospital = async () => {
    const nome = hospitalSearchRef.current.trim()
    if (!nome || creatingHospital) return

    setCreatingHospital(true)
    try {
      const res = await fetch('/api/hospitais', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nome }),
      })

      if (!res.ok) {
        toast.error('Erro ao criar hospital')
        return
      }

      const newHospital: Hospital = await res.json()
      setHospitais((prev) => [...prev, newHospital].sort((a, b) => a.nome.localeCompare(b.nome)))
      setHospitalId(newHospital.id)
      setSelectedHospitalData(newHospital)
      setHospitalOpen(false)
      setHospitalSearch('')
    } catch {
      toast.error('Erro ao criar hospital')
    } finally {
      setCreatingHospital(false)
    }
  }

  const handleCreateEspecialidade = async () => {
    const nome = especialidadeSearchRef.current.trim()
    if (!nome || creatingEspecialidade) return

    setCreatingEspecialidade(true)
    try {
      const res = await fetch('/api/especialidades', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nome }),
      })

      if (!res.ok) {
        toast.error('Erro ao criar especialidade')
        return
      }

      const newEspecialidade: Especialidade = await res.json()
      setEspecialidades((prev) =>
        [...prev, newEspecialidade].sort((a, b) => a.nome.localeCompare(b.nome))
      )
      setEspecialidadeId(newEspecialidade.id)
      setEspecialidadeOpen(false)
      setEspecialidadeSearch('')
    } catch {
      toast.error('Erro ao criar especialidade')
    } finally {
      setCreatingEspecialidade(false)
    }
  }

  const handleSelectContato = (contato: ContatoGrupo) => {
    setContatoNome(contato.nome)
    setContatoWhatsapp(contato.telefone || '')
    setContatoManual(false)
    setContatoOpen(false)
    setContatoSearch('')
  }

  const handleCreateContatoManual = () => {
    const nome = contatoSearchRef.current.trim()
    if (!nome) return
    setContatoNome(nome)
    setContatoWhatsapp('')
    setContatoManual(true)
    setContatoOpen(false)
    setContatoSearch('')
  }

  const handleSubmit = async () => {
    const payload: Record<string, unknown> = {
      hospital_id: hospitalId,
      especialidade_id: especialidadeId,
      data,
      hora_inicio: horaInicio || null,
      hora_fim: horaFim || null,
      valor: valor ? Number(valor) : null,
      contato_nome: contatoNome.trim() || null,
      contato_whatsapp: contatoWhatsapp.trim() || null,
    }

    try {
      const success = await onSave(payload)
      if (success) {
        toast.success('Vaga atualizada')
        onOpenChange(false)
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro ao atualizar vaga'
      toast.error(message)
    }
  }

  const contatoDisplayLabel = contatoNome
    ? contatoNome
    : loadingContatos
      ? 'Carregando...'
      : 'Buscar contato...'

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Editar Vaga</DialogTitle>
        </DialogHeader>

        <div className="max-h-[60vh] space-y-4 overflow-y-auto py-4 pr-1">
          {/* Hospital */}
          <div className="space-y-2">
            <Label>
              Hospital <span className="text-destructive">*</span>
            </Label>
            <Popover open={hospitalOpen} onOpenChange={setHospitalOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  role="combobox"
                  aria-expanded={hospitalOpen}
                  className="w-full justify-between"
                >
                  {selectedHospital
                    ? selectedHospital.nome
                    : loadingHospitais
                      ? 'Carregando...'
                      : 'Selecione o hospital'}
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
                <Command shouldFilter={false}>
                  <CommandInput
                    placeholder="Buscar hospital..."
                    value={hospitalSearch}
                    onValueChange={setHospitalSearch}
                  />
                  <CommandList>
                    <CommandEmpty>
                      {loadingHospitais ? 'Buscando...' : 'Nenhum hospital encontrado'}
                    </CommandEmpty>
                    <CommandGroup className="max-h-[200px] overflow-auto">
                      {hospitais.map((hospital) => (
                        <CommandItem
                          key={hospital.id}
                          value={hospital.nome}
                          onSelect={() => {
                            setHospitalId(hospital.id)
                            setSelectedHospitalData(hospital)
                            setHospitalOpen(false)
                            setHospitalSearch('')
                          }}
                        >
                          <Check
                            className={cn(
                              'mr-2 h-4 w-4',
                              hospitalId === hospital.id ? 'opacity-100' : 'opacity-0'
                            )}
                          />
                          {hospital.nome}
                        </CommandItem>
                      ))}
                    </CommandGroup>
                    {showCreateHospital && (
                      <CommandGroup>
                        <CommandItem
                          value={`__create__${hospitalSearch}`}
                          onSelect={handleCreateHospital}
                          disabled={creatingHospital}
                        >
                          {creatingHospital ? (
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          ) : (
                            <Plus className="mr-2 h-4 w-4" />
                          )}
                          Criar &quot;{hospitalSearch.trim()}&quot;
                        </CommandItem>
                      </CommandGroup>
                    )}
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>

          {/* Especialidade */}
          <div className="space-y-2">
            <Label>
              Especialidade <span className="text-destructive">*</span>
            </Label>
            <Popover open={especialidadeOpen} onOpenChange={setEspecialidadeOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  role="combobox"
                  aria-expanded={especialidadeOpen}
                  className="w-full justify-between"
                >
                  {selectedEspecialidade
                    ? selectedEspecialidade.nome
                    : loadingListas
                      ? 'Carregando...'
                      : 'Selecione a especialidade'}
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
                <Command shouldFilter={true}>
                  <CommandInput
                    placeholder="Buscar especialidade..."
                    value={especialidadeSearch}
                    onValueChange={setEspecialidadeSearch}
                  />
                  <CommandList>
                    <CommandEmpty>
                      {loadingListas ? 'Carregando...' : 'Nenhuma especialidade encontrada'}
                    </CommandEmpty>
                    <CommandGroup className="max-h-[200px] overflow-auto">
                      {especialidades.map((especialidade) => (
                        <CommandItem
                          key={especialidade.id}
                          value={especialidade.nome}
                          onSelect={() => {
                            setEspecialidadeId(especialidade.id)
                            setEspecialidadeOpen(false)
                            setEspecialidadeSearch('')
                          }}
                        >
                          <Check
                            className={cn(
                              'mr-2 h-4 w-4',
                              especialidadeId === especialidade.id ? 'opacity-100' : 'opacity-0'
                            )}
                          />
                          {especialidade.nome}
                        </CommandItem>
                      ))}
                    </CommandGroup>
                    {showCreateEspecialidade && (
                      <CommandGroup>
                        <CommandItem
                          value={`__create__${especialidadeSearch}`}
                          onSelect={handleCreateEspecialidade}
                          disabled={creatingEspecialidade}
                        >
                          {creatingEspecialidade ? (
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          ) : (
                            <Plus className="mr-2 h-4 w-4" />
                          )}
                          Criar &quot;{especialidadeSearch.trim()}&quot;
                        </CommandItem>
                      </CommandGroup>
                    )}
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>

          {/* Contato Responsavel */}
          <div className="space-y-2">
            <Label>Contato Responsavel</Label>
            <Popover open={contatoOpen} onOpenChange={setContatoOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  role="combobox"
                  aria-expanded={contatoOpen}
                  className="w-full justify-between"
                >
                  <span className="flex items-center gap-2 truncate">
                    <User className="h-4 w-4 shrink-0 opacity-50" />
                    {contatoDisplayLabel}
                  </span>
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
                <Command shouldFilter={false}>
                  <CommandInput
                    placeholder="Buscar contato por nome ou telefone..."
                    value={contatoSearch}
                    onValueChange={setContatoSearch}
                  />
                  <CommandList>
                    <CommandEmpty>
                      {loadingContatos ? 'Buscando...' : 'Nenhum contato encontrado'}
                    </CommandEmpty>
                    <CommandGroup className="max-h-[200px] overflow-auto">
                      {contatos.map((contato) => (
                        <CommandItem
                          key={contato.id}
                          value={`${contato.nome}-${contato.id}`}
                          onSelect={() => handleSelectContato(contato)}
                        >
                          <Check
                            className={cn(
                              'mr-2 h-4 w-4',
                              contatoNome === contato.nome && !contatoManual
                                ? 'opacity-100'
                                : 'opacity-0'
                            )}
                          />
                          <span>
                            {contato.nome}
                            {contato.telefone && (
                              <span className="ml-1 text-muted-foreground">
                                {' '}
                                — {contato.telefone}
                              </span>
                            )}
                            {contato.empresa && (
                              <span className="ml-1 text-muted-foreground">
                                {' '}
                                ({contato.empresa})
                              </span>
                            )}
                          </span>
                        </CommandItem>
                      ))}
                    </CommandGroup>
                    {showCreateContato && (
                      <CommandGroup>
                        <CommandItem
                          value={`__create__contato__${contatoSearch}`}
                          onSelect={handleCreateContatoManual}
                        >
                          <Plus className="mr-2 h-4 w-4" />
                          Usar &quot;{contatoSearchTrimmed}&quot;
                        </CommandItem>
                      </CommandGroup>
                    )}
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>

            {contatoNome && (contatoManual || !contatoWhatsapp) && (
              <div className="space-y-2 pt-1">
                <Label>WhatsApp do contato</Label>
                <Input
                  placeholder="5511999999999"
                  value={contatoWhatsapp}
                  onChange={(e) => setContatoWhatsapp(e.target.value.replace(/\D/g, ''))}
                  maxLength={13}
                />
                <p className="text-xs text-muted-foreground">
                  Apenas numeros, com DDD (10-13 digitos)
                </p>
              </div>
            )}

            {contatoNome && contatoWhatsapp && !contatoManual && (
              <p className="text-xs text-muted-foreground">
                {contatoNome} — {contatoWhatsapp}
              </p>
            )}
          </div>

          {/* Data */}
          <div className="space-y-2">
            <Label>
              Data <span className="text-destructive">*</span>
            </Label>
            <Input type="date" value={data} onChange={(e) => setData(e.target.value)} />
          </div>

          {/* Horarios */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Hora inicio</Label>
              <Input
                type="time"
                value={horaInicio}
                onChange={(e) => setHoraInicio(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Hora fim</Label>
              <Input type="time" value={horaFim} onChange={(e) => setHoraFim(e.target.value)} />
            </div>
          </div>

          {/* Valor */}
          <div className="space-y-2">
            <Label>Valor (R$)</Label>
            <Input
              type="number"
              placeholder="Ex: 2500"
              value={valor}
              onChange={(e) => setValor(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Deixe vazio para marcar como &quot;a combinar&quot;
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit} disabled={!canSubmit() || saving}>
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
