/**
 * Step 3 - Mensagem - Sprint 34 E03
 */

'use client'

import { Info, Sparkles } from 'lucide-react'
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
import { requiresCustomMessage } from './schema'

interface StepMensagemProps {
  formData: CampanhaFormData
  updateField: <K extends keyof CampanhaFormData>(field: K, value: CampanhaFormData[K]) => void
}

const MENSAGENS_AUTOMATICAS: Record<string, string> = {
  descoberta:
    'A mensagem será gerada automaticamente usando aberturas dinâmicas personalizadas para cada médico.',
  reativacao:
    'Se não informar uma mensagem, será usado: "Oi Dr {nome}! Tudo bem? Faz tempo que a gente nao se fala..."',
  followup:
    'Se não informar uma mensagem, será usado: "Oi Dr {nome}! Lembrei de vc..."',
}

export function StepMensagem({ formData, updateField }: StepMensagemProps) {
  const isRequired = requiresCustomMessage(formData.tipo_campanha)
  const autoMessageInfo = MENSAGENS_AUTOMATICAS[formData.tipo_campanha]

  return (
    <div className="space-y-4">
      {/* Info card para mensagem automática */}
      {!isRequired && autoMessageInfo && (
        <div className="flex items-start gap-3 rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-950">
          <Sparkles className="mt-0.5 h-5 w-5 flex-shrink-0 text-blue-600 dark:text-blue-400" />
          <div>
            <p className="text-sm font-medium text-blue-900 dark:text-blue-100">
              Mensagem automática disponível
            </p>
            <p className="mt-1 text-sm text-blue-700 dark:text-blue-300">{autoMessageInfo}</p>
          </div>
        </div>
      )}

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
        <Label htmlFor="corpo">
          Mensagem {isRequired ? '*' : '(opcional)'}
        </Label>
        <Textarea
          id="corpo"
          placeholder={
            isRequired
              ? `Digite a mensagem que sera enviada aos medicos...

Use {{nome}} para inserir o nome do medico.
Use {{especialidade}} para a especialidade.
Use {{hospital}} para o hospital da vaga.`
              : 'Deixe em branco para usar a mensagem automática, ou digite uma mensagem customizada...'
          }
          value={formData.corpo}
          onChange={(e) => updateField('corpo', e.target.value)}
          rows={8}
          className="font-mono text-sm"
        />
        <p className="mt-1 text-xs text-muted-foreground">
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

      {/* Indicação visual quando usando mensagem automática */}
      {!isRequired && !formData.corpo && (
        <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/50 p-3">
          <Info className="h-4 w-4 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            Será usada a mensagem automática do sistema
          </p>
        </div>
      )}
    </div>
  )
}
