/**
 * Step 2 - Audiencia - Sprint 34 E03
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
import { Loader2 } from 'lucide-react'
import { type CampanhaFormData } from './types'

interface FiltroOption {
  value: string
  label: string
  count: number
}

interface StepAudienciaProps {
  formData: CampanhaFormData
  updateField: <K extends keyof CampanhaFormData>(field: K, value: CampanhaFormData[K]) => void
  toggleArrayItem: (field: 'especialidades' | 'regioes' | 'status_cliente', item: string) => void
}

export function StepAudiencia({ formData, updateField, toggleArrayItem }: StepAudienciaProps) {
  const [especialidadesOptions, setEspecialidadesOptions] = useState<FiltroOption[]>([])
  const [estadosOptions, setEstadosOptions] = useState<FiltroOption[]>([])
  const [loading, setLoading] = useState(true)

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

    carregarFiltros()
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
    </div>
  )
}
