/**
 * Step 1 - Configuracao - Sprint 34 E03
 */

'use client'

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
import {
  type CampanhaFormData,
  type TipoCampanha,
  type Categoria,
  TIPOS_CAMPANHA,
  CATEGORIAS,
} from './types'

interface StepConfiguracaoProps {
  formData: CampanhaFormData
  updateField: <K extends keyof CampanhaFormData>(field: K, value: CampanhaFormData[K]) => void
}

export function StepConfiguracao({ formData, updateField }: StepConfiguracaoProps) {
  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="nome">Nome da Campanha *</Label>
        <Input
          id="nome"
          placeholder="Ex: Oferta Cardio ABC - Janeiro"
          value={formData.nome_template}
          onChange={(e) => updateField('nome_template', e.target.value)}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label>Tipo de Campanha</Label>
          <Select
            value={formData.tipo_campanha}
            onValueChange={(v) => updateField('tipo_campanha', v as TipoCampanha)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TIPOS_CAMPANHA.map((tipo) => (
                <SelectItem key={tipo.value} value={tipo.value}>
                  {tipo.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <Label>Categoria</Label>
          <Select
            value={formData.categoria}
            onValueChange={(v) => updateField('categoria', v as Categoria)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {CATEGORIAS.map((cat) => (
                <SelectItem key={cat.value} value={cat.value}>
                  {cat.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div>
        <Label htmlFor="objetivo">Objetivo (opcional)</Label>
        <Textarea
          id="objetivo"
          placeholder="Descreva o objetivo desta campanha..."
          value={formData.objetivo}
          onChange={(e) => updateField('objetivo', e.target.value)}
          rows={3}
        />
      </div>
    </div>
  )
}
