/**
 * Wizard Validation Schema - Sprint 34 E03
 */

import { z } from 'zod'
import { type CampanhaFormData } from './types'

export const campanhaSchema = z.object({
  // Step 1 - Configuracao
  nome_template: z.string().min(3, 'Nome deve ter pelo menos 3 caracteres'),
  tipo_campanha: z.enum(['oferta_plantao', 'reativacao', 'followup', 'descoberta']),
  categoria: z.enum(['marketing', 'operacional', 'relacionamento']),
  objetivo: z.string().optional(),

  // Step 2 - Audiencia
  audiencia_tipo: z.enum(['todos', 'filtrado']),
  especialidades: z.array(z.string()),
  regioes: z.array(z.string()),
  status_cliente: z.array(z.string()),

  // Step 3 - Mensagem
  corpo: z.string().min(10, 'Mensagem deve ter pelo menos 10 caracteres'),
  tom: z.enum(['amigavel', 'profissional', 'urgente', 'casual']),

  // Step 4 - Agendamento
  agendar: z.boolean(),
  agendar_para: z.string().optional(),
})

export type CampanhaSchemaType = z.infer<typeof campanhaSchema>

/**
 * Validates a specific step of the wizard.
 */
export function validateStep(step: number, data: CampanhaFormData): boolean {
  switch (step) {
    case 1:
      return data.nome_template.trim().length >= 3
    case 2:
      return true // Audiencia is always valid
    case 3:
      return data.corpo.trim().length >= 10
    case 4:
      return true // Review is always valid
    default:
      return false
  }
}
