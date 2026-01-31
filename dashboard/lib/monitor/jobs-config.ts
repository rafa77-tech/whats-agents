/**
 * Jobs Configuration - Sprint 42
 *
 * Definicoes estaticas dos jobs do sistema.
 * Baseado em app/workers/scheduler.py.
 */

import type { JobDefinition, JobCategory } from '@/types/monitor'

/**
 * SLA por categoria de job (em segundos).
 */
export const JOB_SLA_BY_CATEGORY: Record<JobCategory, number> = {
  critical: 180, // 3 minutos
  frequent: 900, // 15 minutos
  hourly: 7200, // 2 horas
  daily: 90000, // 25 horas
  weekly: 691200, // 8 dias
}

/**
 * Lista completa de jobs do sistema.
 */
export const JOBS: JobDefinition[] = [
  // Critical (every minute)
  {
    name: 'heartbeat',
    displayName: 'Heartbeat',
    category: 'critical',
    schedule: '* * * * *',
    description: 'Heartbeat para monitoramento',
    slaSeconds: 180,
    isCritical: true,
  },
  {
    name: 'processar_mensagens_agendadas',
    displayName: 'Processar Mensagens',
    category: 'critical',
    schedule: '* * * * *',
    description: 'Processa mensagens da fila',
    slaSeconds: 180,
    isCritical: true,
  },
  {
    name: 'processar_campanhas_agendadas',
    displayName: 'Processar Campanhas',
    category: 'critical',
    schedule: '* * * * *',
    description: 'Processa campanhas agendadas',
    slaSeconds: 180,
    isCritical: true,
  },
  {
    name: 'processar_grupos',
    displayName: 'Processar Grupos',
    category: 'critical',
    schedule: '* * * * *',
    description: 'Processa mensagens de grupos',
    slaSeconds: 180,
    isCritical: true,
  },

  // Frequent (every 5-15 min)
  {
    name: 'verificar_whatsapp',
    displayName: 'Verificar WhatsApp',
    category: 'frequent',
    schedule: '*/5 * * * *',
    description: 'Verifica conexao WhatsApp',
    slaSeconds: 900,
    isCritical: false,
  },
  {
    name: 'sincronizar_chips',
    displayName: 'Sincronizar Chips',
    category: 'frequent',
    schedule: '*/5 * * * *',
    description: 'Sincroniza chips com Evolution API',
    slaSeconds: 900,
    isCritical: false,
  },
  {
    name: 'validar_telefones',
    displayName: 'Validar Telefones',
    category: 'frequent',
    schedule: '*/5 8-19 * * *',
    description: 'Valida telefones via checkNumberStatus',
    slaSeconds: 900,
    isCritical: false,
  },
  {
    name: 'atualizar_trust_scores',
    displayName: 'Atualizar Trust Scores',
    category: 'frequent',
    schedule: '*/15 * * * *',
    description: 'Atualiza trust scores dos chips',
    slaSeconds: 2700,
    isCritical: false,
  },
  {
    name: 'verificar_alertas',
    displayName: 'Verificar Alertas',
    category: 'frequent',
    schedule: '*/15 * * * *',
    description: 'Verifica alertas do sistema',
    slaSeconds: 2700,
    isCritical: false,
  },
  {
    name: 'verificar_alertas_grupos',
    displayName: 'Alertas de Grupos',
    category: 'frequent',
    schedule: '*/15 * * * *',
    description: 'Verifica alertas de grupos',
    slaSeconds: 2700,
    isCritical: false,
  },
  {
    name: 'processar_handoffs',
    displayName: 'Processar Handoffs',
    category: 'frequent',
    schedule: '*/10 * * * *',
    description: 'Processa follow-ups de handoff',
    slaSeconds: 1800,
    isCritical: false,
  },

  // Hourly
  {
    name: 'sincronizar_briefing',
    displayName: 'Sincronizar Briefing',
    category: 'hourly',
    schedule: '0 * * * *',
    description: 'Sincroniza briefing do Google Docs',
    slaSeconds: 7200,
    isCritical: false,
  },
  {
    name: 'processar_confirmacao_plantao',
    displayName: 'Confirmar Plantões',
    category: 'hourly',
    schedule: '0 * * * *',
    description: 'Processa confirmacoes de plantao',
    slaSeconds: 7200,
    isCritical: false,
  },
  {
    name: 'oferta_autonoma',
    displayName: 'Oferta Autônoma',
    category: 'hourly',
    schedule: '0 * * * *',
    description: 'Executa ofertas autonomas',
    slaSeconds: 7200,
    isCritical: false,
  },

  // Daily
  {
    name: 'processar_followups',
    displayName: 'Follow-ups Diários',
    category: 'daily',
    schedule: '0 10 * * *',
    description: 'Processa follow-ups diarios',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'processar_pausas_expiradas',
    displayName: 'Pausas Expiradas',
    category: 'daily',
    schedule: '0 6 * * *',
    description: 'Processa pausas expiradas',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'avaliar_conversas_pendentes',
    displayName: 'Avaliar Conversas',
    category: 'daily',
    schedule: '0 2 * * *',
    description: 'Avalia conversas pendentes',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'report_manha',
    displayName: 'Report da Manhã',
    category: 'daily',
    schedule: '0 10 * * *',
    description: 'Report da manha',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'report_fim_dia',
    displayName: 'Report Fim do Dia',
    category: 'daily',
    schedule: '0 20 * * *',
    description: 'Report de fim do dia',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'doctor_state_manutencao_diaria',
    displayName: 'Manutenção Médicos',
    category: 'daily',
    schedule: '0 3 * * *',
    description: 'Manutencao diaria do doctor_state',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'sincronizar_templates',
    displayName: 'Sincronizar Templates',
    category: 'daily',
    schedule: '0 6 * * *',
    description: 'Sincroniza templates de campanha',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'limpar_grupos_finalizados',
    displayName: 'Limpar Grupos',
    category: 'daily',
    schedule: '0 3 * * *',
    description: 'Limpa grupos finalizados',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'consolidar_metricas_grupos',
    displayName: 'Métricas de Grupos',
    category: 'daily',
    schedule: '0 1 * * *',
    description: 'Consolida metricas de grupos',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'processar_retomadas',
    displayName: 'Retomadas',
    category: 'daily',
    schedule: '0 8 * * 1-5',
    description: 'Processa retomadas (seg-sex)',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'discovery_autonomo',
    displayName: 'Discovery Autônomo',
    category: 'daily',
    schedule: '0 9,14 * * 1-5',
    description: 'Discovery autonomo (9h e 14h)',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'feedback_autonomo',
    displayName: 'Feedback Autônomo',
    category: 'daily',
    schedule: '0 11 * * *',
    description: 'Feedback autonomo',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'snapshot_chips_diario',
    displayName: 'Snapshot de Chips',
    category: 'daily',
    schedule: '55 23 * * *',
    description: 'Snapshot diario de chips',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'resetar_contadores_chips',
    displayName: 'Reset Contadores',
    category: 'daily',
    schedule: '5 0 * * *',
    description: 'Reset de contadores de chips',
    slaSeconds: 90000,
    isCritical: false,
  },

  // Weekly
  {
    name: 'report_semanal',
    displayName: 'Report Semanal',
    category: 'weekly',
    schedule: '0 9 * * 1',
    description: 'Report semanal (segunda)',
    slaSeconds: 691200,
    isCritical: false,
  },
  {
    name: 'atualizar_prompt_feedback',
    displayName: 'Atualizar Prompts',
    category: 'weekly',
    schedule: '0 2 * * 0',
    description: 'Atualiza prompt de feedback',
    slaSeconds: 691200,
    isCritical: false,
  },
  {
    name: 'doctor_state_manutencao_semanal',
    displayName: 'Manutenção Semanal',
    category: 'weekly',
    schedule: '0 4 * * 1',
    description: 'Manutencao semanal doctor_state',
    slaSeconds: 691200,
    isCritical: false,
  },
  {
    name: 'reativacao_autonoma',
    displayName: 'Reativação Autônoma',
    category: 'weekly',
    schedule: '0 10 * * 1',
    description: 'Reativacao autonoma (segunda)',
    slaSeconds: 691200,
    isCritical: false,
  },
]

/**
 * Mapa de jobs por nome para lookup rapido.
 */
export const JOBS_BY_NAME: Record<string, JobDefinition> = Object.fromEntries(
  JOBS.map((job) => [job.name, job])
)

/**
 * Jobs criticos que devem estar sempre rodando.
 */
export const CRITICAL_JOBS = JOBS.filter((job) => job.isCritical).map((job) => job.name)

/**
 * Total de jobs configurados.
 */
export const TOTAL_JOBS = JOBS.length
