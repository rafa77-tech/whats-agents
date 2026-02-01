/**
 * Formatadores para o modulo de Instrucoes (Diretrizes)
 */

import { format, formatDistanceToNow } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import type { Diretriz, TipoDiretriz, Escopo } from './types'
import { TIPO_LABELS, ESCOPO_ICONS, ESCOPO_LABELS } from './constants'

// =============================================================================
// Formatadores de data
// =============================================================================

/**
 * Formata data para exibicao relativa (ex: "ha 2 dias")
 */
export function formatRelativeDate(dateString: string): string {
  try {
    return formatDistanceToNow(new Date(dateString), {
      addSuffix: true,
      locale: ptBR,
    })
  } catch {
    return dateString
  }
}

/**
 * Formata data para exibicao (dd/MM HH:mm)
 */
export function formatExpirationDate(dateString: string): string {
  try {
    return format(new Date(dateString), 'dd/MM HH:mm')
  } catch {
    return dateString
  }
}

/**
 * Formata data de vaga (dd/MM)
 */
export function formatVagaDate(dateString: string): string {
  try {
    return format(new Date(dateString), 'dd/MM')
  } catch {
    return dateString
  }
}

/**
 * Verifica se uma data esta expirada
 */
export function isExpired(dateString: string): boolean {
  try {
    return new Date(dateString) < new Date()
  } catch {
    return false
  }
}

// =============================================================================
// Formatadores de labels
// =============================================================================

/**
 * Retorna o label para um tipo de diretriz
 */
export function getTipoLabel(tipo: TipoDiretriz): string {
  return TIPO_LABELS[tipo] ?? tipo
}

/**
 * Retorna o icone para um escopo
 */
export function getEscopoIcon(escopo: Escopo) {
  return ESCOPO_ICONS[escopo]
}

/**
 * Retorna o label para um escopo base
 */
export function getEscopoBaseLabel(escopo: Escopo): string {
  return ESCOPO_LABELS[escopo] ?? escopo
}

/**
 * Retorna o label contextual para um escopo de diretriz
 */
export function getEscopoLabel(diretriz: Diretriz): string {
  switch (diretriz.escopo) {
    case 'vaga':
      return diretriz.vagas?.data ? `Vaga ${formatVagaDate(diretriz.vagas.data)}` : 'Vaga'
    case 'medico':
      return diretriz.clientes
        ? `${diretriz.clientes.primeiro_nome} ${diretriz.clientes.sobrenome}`.trim()
        : 'Medico'
    case 'hospital':
      return diretriz.hospitais?.nome ?? 'Hospital'
    case 'especialidade':
      return diretriz.especialidades?.nome ?? 'Especialidade'
    case 'global':
      return 'Todas as conversas'
    default:
      return ''
  }
}

// =============================================================================
// Formatadores de conteudo
// =============================================================================

/**
 * Formata valor monetario
 */
export function formatCurrency(value: number): string {
  return value.toLocaleString('pt-BR')
}

/**
 * Retorna o label do conteudo de uma diretriz
 */
export function getConteudoLabel(diretriz: Diretriz): string {
  const { conteudo, tipo } = diretriz

  if (tipo === 'margem_negociacao') {
    if (conteudo.valor_maximo) {
      return `Ate R$ ${formatCurrency(conteudo.valor_maximo)}`
    }
    if (conteudo.percentual_maximo) {
      return `Ate ${conteudo.percentual_maximo}% acima`
    }
  }

  if (tipo === 'regra_especial') {
    return conteudo.regra ?? ''
  }

  if (tipo === 'info_adicional') {
    return conteudo.info ?? ''
  }

  return JSON.stringify(conteudo)
}

// =============================================================================
// Builders de URL
// =============================================================================

/**
 * Constroi URL para buscar diretrizes
 */
export function buildDiretrizesUrl(baseUrl: string, status: string): string {
  const params = new URLSearchParams({ status })
  return `${baseUrl}?${params}`
}

/**
 * Constroi URL para diretriz especifica
 */
export function buildDiretrizUrl(baseUrl: string, id: string): string {
  return `${baseUrl}/${id}`
}
