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

  // Step 3 - Mensagem (corpo é opcional para tipos com mensagem automática)
  corpo: z.string().optional().default(''),
  tom: z.enum(['amigavel', 'profissional', 'urgente', 'casual']),

  // Step 4 - Agendamento
  agendar: z.boolean(),
  agendar_para: z.string().optional(),
})

export type CampanhaSchemaType = z.infer<typeof campanhaSchema>

/**
 * Tipos de campanha que têm geração automática de mensagem.
 * - discovery: usa obter_abertura_texto()
 * - reativacao: template padrão "Oi Dr {nome}! Tudo bem? Faz tempo..."
 * - followup: template padrão "Oi Dr {nome}! Lembrei de vc..."
 */
const TIPOS_COM_MENSAGEM_AUTOMATICA = ['descoberta', 'reativacao', 'followup']

/**
 * Verifica se o tipo de campanha requer mensagem customizada.
 */
export function requiresCustomMessage(tipoCampanha: string): boolean {
  return !TIPOS_COM_MENSAGEM_AUTOMATICA.includes(tipoCampanha)
}

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
      // Mensagem só é obrigatória para oferta_plantao
      if (requiresCustomMessage(data.tipo_campanha)) {
        return data.corpo.trim().length >= 10
      }
      return true // Outros tipos têm geração automática
    case 4:
      return true // Review is always valid
    default:
      return false
  }
}
