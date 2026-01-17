/**
 * Step 4 - Revisao - Sprint 34 E03
 */

'use client'

import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { type CampanhaFormData, TIPOS_CAMPANHA, CATEGORIAS, TONS } from './types'

interface StepRevisaoProps {
  formData: CampanhaFormData
  updateField: <K extends keyof CampanhaFormData>(field: K, value: CampanhaFormData[K]) => void
}

export function StepRevisao({ formData, updateField }: StepRevisaoProps) {
  return (
    <div className="space-y-4">
      <div className="space-y-3 rounded-lg bg-gray-50 p-4">
        <h3 className="font-medium">Resumo da Campanha</h3>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Nome:</span>
            <p className="font-medium">{formData.nome_template}</p>
          </div>

          <div>
            <span className="text-gray-500">Tipo:</span>
            <p className="font-medium">
              {TIPOS_CAMPANHA.find((t) => t.value === formData.tipo_campanha)?.label}
            </p>
          </div>

          <div>
            <span className="text-gray-500">Categoria:</span>
            <p className="font-medium">
              {CATEGORIAS.find((c) => c.value === formData.categoria)?.label}
            </p>
          </div>

          <div>
            <span className="text-gray-500">Tom:</span>
            <p className="font-medium">
              {TONS.find((t) => t.value === formData.tom)?.label}
            </p>
          </div>
        </div>

        {formData.objetivo && (
          <div className="text-sm">
            <span className="text-gray-500">Objetivo:</span>
            <p>{formData.objetivo}</p>
          </div>
        )}

        <div className="text-sm">
          <span className="text-gray-500">Audiencia:</span>
          <p>
            {formData.audiencia_tipo === 'todos'
              ? 'Todos os medicos'
              : `Filtrada (${formData.especialidades.length} especialidades, ${formData.regioes.length} regioes)`}
          </p>
        </div>
      </div>

      <div className="border-t pt-4">
        <div className="flex items-center space-x-2">
          <Checkbox
            id="agendar"
            checked={formData.agendar}
            onCheckedChange={(checked) => updateField('agendar', checked === true)}
          />
          <Label htmlFor="agendar">Agendar envio</Label>
        </div>

        {formData.agendar && (
          <div className="mt-4">
            <Label htmlFor="data">Data e Hora do Envio</Label>
            <Input
              id="data"
              type="datetime-local"
              value={formData.agendar_para}
              onChange={(e) => updateField('agendar_para', e.target.value)}
            />
          </div>
        )}

        {!formData.agendar && (
          <p className="mt-2 text-sm text-gray-500">
            A campanha sera salva como rascunho. Voce podera iniciar o envio manualmente depois.
          </p>
        )}
      </div>
    </div>
  )
}
