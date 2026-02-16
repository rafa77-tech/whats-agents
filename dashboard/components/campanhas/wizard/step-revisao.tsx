/**
 * Step 4 - Revisao - Sprint 34 E03
 * Sprint 58: Display linked vagas when escopo_vagas is present
 */

'use client'

import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { Sparkles, Briefcase } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { formatCurrency } from '@/lib/vagas/formatters'
import { type CampanhaFormData, TIPOS_CAMPANHA, CATEGORIAS, TONS } from './types'
import { requiresCustomMessage } from './schema'

interface StepRevisaoProps {
  formData: CampanhaFormData
  updateField: <K extends keyof CampanhaFormData>(field: K, value: CampanhaFormData[K]) => void
}

export function StepRevisao({ formData, updateField }: StepRevisaoProps) {
  return (
    <div className="space-y-4">
      <div className="space-y-3 rounded-lg bg-card p-4">
        <h3 className="font-medium">Resumo da Campanha</h3>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">Nome:</span>
            <p className="font-medium">{formData.nome_template}</p>
          </div>

          <div>
            <span className="text-muted-foreground">Tipo:</span>
            <p className="font-medium">
              {TIPOS_CAMPANHA.find((t) => t.value === formData.tipo_campanha)?.label}
            </p>
          </div>

          <div>
            <span className="text-muted-foreground">Categoria:</span>
            <p className="font-medium">
              {CATEGORIAS.find((c) => c.value === formData.categoria)?.label}
            </p>
          </div>

          <div>
            <span className="text-muted-foreground">Tom:</span>
            <p className="font-medium">{TONS.find((t) => t.value === formData.tom)?.label}</p>
          </div>
        </div>

        {formData.objetivo && (
          <div className="text-sm">
            <span className="text-muted-foreground">Objetivo:</span>
            <p>{formData.objetivo}</p>
          </div>
        )}

        <div className="text-sm">
          <span className="text-muted-foreground">Audiencia:</span>
          <p>
            {formData.audiencia_tipo === 'todos'
              ? 'Todos os medicos'
              : `Filtrada (${formData.especialidades.length} especialidades, ${formData.regioes.length} regioes)`}
          </p>
        </div>

        {formData.chips_excluidos.length > 0 && (
          <div className="text-sm">
            <span className="text-muted-foreground">Chips excluidos:</span>
            <p className="text-status-warning-foreground">
              {formData.chips_excluidos.length} chip
              {formData.chips_excluidos.length > 1 ? 's' : ''} nao sera
              {formData.chips_excluidos.length > 1 ? 'o' : ''} usado
              {formData.chips_excluidos.length > 1 ? 's' : ''}
            </p>
          </div>
        )}

        <div className="text-sm">
          <span className="text-muted-foreground">Mensagem:</span>
          {formData.corpo ? (
            <p className="mt-1 whitespace-pre-wrap rounded bg-muted p-2 text-xs">
              {formData.corpo.length > 100
                ? `${formData.corpo.substring(0, 100)}...`
                : formData.corpo}
            </p>
          ) : !requiresCustomMessage(formData.tipo_campanha) ? (
            <p className="flex items-center gap-1.5 text-status-info-solid">
              <Sparkles className="h-3.5 w-3.5" />
              Mensagem automatica do sistema
            </p>
          ) : (
            <p className="text-status-error-foreground">Nao definida</p>
          )}
        </div>
      </div>

      {/* Vagas vinculadas (Sprint 58) */}
      {formData.escopo_vagas && formData.escopo_vagas.vagas.length > 0 && (
        <div className="space-y-3 rounded-lg border border-status-info-border bg-status-info p-4">
          <h3 className="flex items-center gap-2 font-medium text-status-info-foreground">
            <Briefcase className="h-4 w-4" />
            {formData.escopo_vagas.vagas.length === 1
              ? '1 vaga vinculada'
              : `${formData.escopo_vagas.vagas.length} vagas vinculadas`}
          </h3>
          <div className="space-y-2">
            {formData.escopo_vagas.vagas.map((vaga) => (
              <div
                key={vaga.id}
                className="flex items-center justify-between rounded bg-background/60 px-3 py-2 text-sm"
              >
                <div>
                  <span className="font-medium">{vaga.hospital}</span>
                  <span className="mx-1 text-muted-foreground">-</span>
                  <span className="text-muted-foreground">{vaga.especialidade}</span>
                </div>
                <div className="flex items-center gap-3 text-muted-foreground">
                  <span>
                    {format(new Date(vaga.data + 'T00:00:00'), 'dd/MM', { locale: ptBR })}
                  </span>
                  <span>
                    {vaga.hora_inicio}-{vaga.hora_fim}
                  </span>
                  <span className="font-medium text-foreground">{formatCurrency(vaga.valor)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

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
          <p className="mt-2 text-sm text-muted-foreground">
            A campanha sera salva como rascunho. Voce podera iniciar o envio manualmente depois.
          </p>
        )}
      </div>
    </div>
  )
}
