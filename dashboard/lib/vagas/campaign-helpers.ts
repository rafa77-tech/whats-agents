/**
 * Helper functions for vagas -> campanhas integration
 * Sprint 58: Campanhas de Oferta a partir de Vagas
 */

import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import type { Shift } from './types'
import { formatCurrency } from './formatters'
import type { CampanhaFormData } from '@/components/campanhas/wizard/types'

/**
 * Resumo de uma vaga para persistir no escopo_vagas da campanha.
 * Contém apenas os campos relevantes para a Julia formatar ofertas.
 */
export interface VagaResumo {
  id: string
  hospital: string
  especialidade: string
  data: string
  hora_inicio: string
  hora_fim: string
  valor: number
}

/**
 * Estrutura JSONB persistida no campo escopo_vagas da tabela campanhas.
 * O backend (builder.py / contexto.py) já lê este formato.
 */
export interface EscopoVagas {
  vaga_ids: string[]
  vagas: VagaResumo[]
}

/**
 * Dados iniciais para pré-preencher o wizard de campanha
 * quando criada a partir de vagas selecionadas.
 */
export interface WizardInitialData {
  nome_template: string
  tipo_campanha: CampanhaFormData['tipo_campanha']
  categoria: CampanhaFormData['categoria']
  corpo: string
  escopo_vagas: EscopoVagas
}

/**
 * Gera um nome automático para a campanha baseado nas vagas.
 */
function buildCampaignName(vagas: Shift[]): string {
  if (vagas.length === 1) {
    const v = vagas[0]!
    const dataFormatada = format(new Date(v.data + 'T00:00:00'), 'dd/MM', { locale: ptBR })
    return `Oferta ${v.hospital} - ${v.especialidade} ${dataFormatada}`
  }

  // Múltiplas vagas: agrupar por hospital
  const hospitais = Array.from(new Set(vagas.map((v) => v.hospital)))
  if (hospitais.length === 1) {
    return `Oferta ${hospitais[0]} - ${vagas.length} vagas`
  }
  return `Oferta ${vagas.length} vagas - ${hospitais.length} hospitais`
}

/**
 * Gera o corpo da mensagem template a partir das vagas.
 * Usa variáveis {{nome}} para personalização pela Julia.
 */
function buildMessageBody(vagas: Shift[]): string {
  if (vagas.length === 1) {
    const v = vagas[0]!
    const dataFormatada = format(new Date(v.data + 'T00:00:00'), 'dd/MM (EEEE)', { locale: ptBR })
    return [
      `Oi {{nome}}! Tudo bem?`,
      ``,
      `Surgiu uma vaga de ${v.especialidade.toLowerCase()} no ${v.hospital}`,
      ``,
      `${dataFormatada}, das ${v.hora_inicio} as ${v.hora_fim}`,
      `Valor: ${formatCurrency(v.valor)}`,
      ``,
      `Tem interesse?`,
    ].join('\n')
  }

  // Múltiplas vagas
  const linhas = [`Oi {{nome}}! Tudo bem?`, ``, `Tenho ${vagas.length} vagas disponiveis pra vc:`]
  for (const v of vagas) {
    const dataFormatada = format(new Date(v.data + 'T00:00:00'), 'dd/MM', { locale: ptBR })
    linhas.push(
      ``,
      `- ${v.hospital} (${v.especialidade.toLowerCase()})`,
      `  ${dataFormatada}, ${v.hora_inicio}-${v.hora_fim} | ${formatCurrency(v.valor)}`
    )
  }
  linhas.push(``, `Alguma te interessa?`)
  return linhas.join('\n')
}

/**
 * Converte um array de Shift para um resumo persistível.
 */
function toVagaResumo(shift: Shift): VagaResumo {
  return {
    id: shift.id,
    hospital: shift.hospital,
    especialidade: shift.especialidade,
    data: shift.data,
    hora_inicio: shift.hora_inicio,
    hora_fim: shift.hora_fim,
    valor: shift.valor,
  }
}

/**
 * Constrói os dados iniciais para o wizard de campanha
 * a partir de vagas selecionadas.
 *
 * @param vagas - Array de vagas selecionadas (mínimo 1)
 * @returns WizardInitialData pronto para passar ao wizard
 */
export function buildCampaignInitialData(vagas: Shift[]): WizardInitialData {
  if (vagas.length === 0) {
    throw new Error('Pelo menos uma vaga deve ser selecionada')
  }

  return {
    nome_template: buildCampaignName(vagas),
    tipo_campanha: 'oferta_plantao',
    categoria: 'operacional',
    corpo: buildMessageBody(vagas),
    escopo_vagas: {
      vaga_ids: vagas.map((v) => v.id),
      vagas: vagas.map(toVagaResumo),
    },
  }
}
