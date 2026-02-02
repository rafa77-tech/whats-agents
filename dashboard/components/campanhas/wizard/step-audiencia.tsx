/**
 * Step 2 - Audiencia - Sprint 34 E03
 * Updated: Chips exclusion support
 */

'use client'

import { useState, useEffect } from 'react'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Loader2, ChevronDown, Smartphone, Ban } from 'lucide-react'
import { type CampanhaFormData } from './types'

interface FiltroOption {
  value: string
  label: string
  count: number
}

interface ChipOption {
  id: string
  telefone: string
  instance_name: string
  status: string
  trust_level: string
  pode_prospectar: boolean
}

interface StepAudienciaProps {
  formData: CampanhaFormData
  updateField: <K extends keyof CampanhaFormData>(field: K, value: CampanhaFormData[K]) => void
  toggleArrayItem: (
    field: 'especialidades' | 'regioes' | 'status_cliente' | 'chips_excluidos',
    item: string
  ) => void
}

export function StepAudiencia({ formData, updateField, toggleArrayItem }: StepAudienciaProps) {
  const [especialidadesOptions, setEspecialidadesOptions] = useState<FiltroOption[]>([])
  const [estadosOptions, setEstadosOptions] = useState<FiltroOption[]>([])
  const [chipsOptions, setChipsOptions] = useState<ChipOption[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingChips, setLoadingChips] = useState(true)
  const [chipsOpen, setChipsOpen] = useState(false)

  useEffect(() => {
    const carregarFiltros = async () => {
      try {
        const res = await fetch('/api/filtros')
        const data = await res.json()

        if (res.ok) {
          setEspecialidadesOptions(data.especialidades || [])
          setEstadosOptions(data.estados || [])
        }
      } catch (err) {
        console.error('Erro ao carregar filtros:', err)
      } finally {
        setLoading(false)
      }
    }

    const carregarChips = async () => {
      try {
        const res = await fetch('/api/chips')
        const data = await res.json()

        if (res.ok && data.data) {
          setChipsOptions(data.data)
        }
      } catch (err) {
        console.error('Erro ao carregar chips:', err)
      } finally {
        setLoadingChips(false)
      }
    }

    carregarFiltros()
    carregarChips()
  }, [])

  return (
    <div className="space-y-4">
      <div>
        <Label>Audiencia</Label>
        <Select
          value={formData.audiencia_tipo}
          onValueChange={(v) => updateField('audiencia_tipo', v as 'todos' | 'filtrado')}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos os medicos</SelectItem>
            <SelectItem value="filtrado">Filtrar audiencia</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {formData.audiencia_tipo === 'filtrado' && (
        <>
          <div>
            <Label className="mb-2 block">Especialidades</Label>
            {loading ? (
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Loader2 className="h-4 w-4 animate-spin" />
                Carregando...
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                {especialidadesOptions.map((esp) => (
                  <Badge
                    key={esp.value}
                    variant={formData.especialidades.includes(esp.value) ? 'default' : 'outline'}
                    className="cursor-pointer"
                    onClick={() => toggleArrayItem('especialidades', esp.value)}
                  >
                    {esp.label} ({esp.count.toLocaleString()})
                  </Badge>
                ))}
              </div>
            )}
          </div>

          <div>
            <Label className="mb-2 block">Estados</Label>
            {loading ? (
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Loader2 className="h-4 w-4 animate-spin" />
                Carregando...
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                {estadosOptions.map((est) => (
                  <Badge
                    key={est.value}
                    variant={formData.regioes.includes(est.value) ? 'default' : 'outline'}
                    className="cursor-pointer"
                    onClick={() => toggleArrayItem('regioes', est.value)}
                  >
                    {est.value} ({est.count.toLocaleString()})
                  </Badge>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      <div className="rounded-lg bg-gray-50 p-4">
        <p className="text-sm text-gray-600">
          {formData.audiencia_tipo === 'todos' ? (
            <>A campanha sera enviada para todos os medicos cadastrados.</>
          ) : (
            <>
              Filtros selecionados:{' '}
              {formData.especialidades.length > 0 && (
                <span className="font-medium">{formData.especialidades.length} especialidades</span>
              )}
              {formData.regioes.length > 0 && (
                <span className="ml-1 font-medium">, {formData.regioes.length} estados</span>
              )}
              {formData.especialidades.length === 0 && formData.regioes.length === 0 && (
                <span className="text-gray-400">Nenhum filtro selecionado</span>
              )}
            </>
          )}
        </p>
      </div>

      {/* Chips Exclusion Section */}
      <div className="space-y-2">
        <button
          type="button"
          onClick={() => setChipsOpen(!chipsOpen)}
          className="flex w-full items-center justify-between rounded-lg border p-4 hover:bg-gray-50"
        >
          <div className="flex items-center gap-2">
            <Smartphone className="h-4 w-4 text-gray-500" />
            <span className="font-medium">Excluir chips da campanha</span>
            {formData.chips_excluidos.length > 0 && (
              <Badge variant="secondary" className="ml-2">
                {formData.chips_excluidos.length} excluido
                {formData.chips_excluidos.length > 1 ? 's' : ''}
              </Badge>
            )}
          </div>
          <ChevronDown
            className={`h-4 w-4 text-gray-500 transition-transform ${chipsOpen ? 'rotate-180' : ''}`}
          />
        </button>
        {chipsOpen && (
          <div className="rounded-lg border p-4">
            <p className="mb-3 text-sm text-gray-600">
              Selecione chips que <strong>NAO</strong> devem ser usados para enviar mensagens desta
              campanha.
            </p>
            {loadingChips ? (
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Loader2 className="h-4 w-4 animate-spin" />
                Carregando chips...
              </div>
            ) : chipsOptions.length === 0 ? (
              <p className="text-sm text-gray-400">Nenhum chip disponivel</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {chipsOptions.map((chip) => {
                  const isExcluded = formData.chips_excluidos.includes(chip.id)
                  const displayName = chip.instance_name || chip.telefone?.slice(-4) || chip.id
                  const trustColor =
                    chip.trust_level === 'verde'
                      ? 'bg-green-100 text-green-800'
                      : chip.trust_level === 'amarelo'
                        ? 'bg-yellow-100 text-yellow-800'
                        : chip.trust_level === 'laranja'
                          ? 'bg-orange-100 text-orange-800'
                          : 'bg-red-100 text-red-800'

                  return (
                    <Badge
                      key={chip.id}
                      variant={isExcluded ? 'destructive' : 'outline'}
                      className={`cursor-pointer ${isExcluded ? '' : 'hover:bg-gray-100'}`}
                      onClick={() => toggleArrayItem('chips_excluidos', chip.id)}
                    >
                      {isExcluded && <Ban className="mr-1 h-3 w-3" />}
                      {displayName}
                      <span className={`ml-1 rounded px-1 text-xs ${trustColor}`}>
                        {chip.trust_level}
                      </span>
                    </Badge>
                  )
                })}
              </div>
            )}
            {formData.chips_excluidos.length > 0 && (
              <p className="mt-3 text-xs text-orange-600">
                {formData.chips_excluidos.length} chip
                {formData.chips_excluidos.length > 1 ? 's' : ''} excluido
                {formData.chips_excluidos.length > 1 ? 's' : ''} - mensagens serao enviadas apenas
                pelos demais chips
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
