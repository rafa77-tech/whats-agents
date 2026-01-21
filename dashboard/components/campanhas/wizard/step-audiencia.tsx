/**
 * Step 2 - Audiencia - Sprint 34 E03
 */

'use client'

import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { type CampanhaFormData, ESPECIALIDADES, REGIOES } from './types'

interface StepAudienciaProps {
  formData: CampanhaFormData
  updateField: <K extends keyof CampanhaFormData>(field: K, value: CampanhaFormData[K]) => void
  toggleArrayItem: (field: 'especialidades' | 'regioes' | 'status_cliente', item: string) => void
}

export function StepAudiencia({ formData, updateField, toggleArrayItem }: StepAudienciaProps) {
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
            <div className="flex flex-wrap gap-2">
              {ESPECIALIDADES.map((esp) => (
                <Badge
                  key={esp}
                  variant={formData.especialidades.includes(esp) ? 'default' : 'outline'}
                  className="cursor-pointer"
                  onClick={() => toggleArrayItem('especialidades', esp)}
                >
                  {esp}
                </Badge>
              ))}
            </div>
          </div>

          <div>
            <Label className="mb-2 block">Regioes</Label>
            <div className="flex flex-wrap gap-2">
              {REGIOES.map((reg) => (
                <Badge
                  key={reg}
                  variant={formData.regioes.includes(reg) ? 'default' : 'outline'}
                  className="cursor-pointer"
                  onClick={() => toggleArrayItem('regioes', reg)}
                >
                  {reg}
                </Badge>
              ))}
            </div>
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
                <span className="ml-1 font-medium">, {formData.regioes.length} regioes</span>
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
