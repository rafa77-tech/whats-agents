/**
 * Step 3 - Mensagem - Sprint 34 E03
 */

'use client'

import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { type CampanhaFormData, type Tom, TONS } from './types'

interface StepMensagemProps {
  formData: CampanhaFormData
  updateField: <K extends keyof CampanhaFormData>(field: K, value: CampanhaFormData[K]) => void
}

export function StepMensagem({ formData, updateField }: StepMensagemProps) {
  return (
    <div className="space-y-4">
      <div>
        <Label>Tom da Mensagem</Label>
        <Select value={formData.tom} onValueChange={(v) => updateField('tom', v as Tom)}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {TONS.map((tom) => (
              <SelectItem key={tom.value} value={tom.value}>
                {tom.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div>
        <Label htmlFor="corpo">Mensagem *</Label>
        <Textarea
          id="corpo"
          placeholder={`Digite a mensagem que sera enviada aos medicos...

Use {{nome}} para inserir o nome do medico.
Use {{especialidade}} para a especialidade.
Use {{hospital}} para o hospital da vaga.`}
          value={formData.corpo}
          onChange={(e) => updateField('corpo', e.target.value)}
          rows={8}
          className="font-mono text-sm"
        />
        <p className="mt-1 text-xs text-gray-500">
          Variaveis disponiveis: {'{{nome}}'}, {'{{especialidade}}'}, {'{{hospital}}'},{' '}
          {'{{valor}}'}
        </p>
      </div>

      {formData.corpo && (
        <div className="rounded-lg border border-status-success-border bg-status-success p-4">
          <p className="mb-2 text-sm font-medium text-status-success-foreground">Preview:</p>
          <p className="whitespace-pre-wrap text-sm text-status-success-foreground">
            {formData.corpo
              .replace('{{nome}}', 'Dr. Carlos')
              .replace('{{especialidade}}', 'Cardiologia')
              .replace('{{hospital}}', 'Hospital Sao Luiz')
              .replace('{{valor}}', 'R$ 2.500')}
          </p>
        </div>
      )}
    </div>
  )
}
