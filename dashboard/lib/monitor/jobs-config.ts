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
    description: 'Verificacao de saude do sistema',
    helpText:
      'Envia um sinal periodico para confirmar que o sistema esta funcionando. Se este job parar, indica que o scheduler travou ou o sistema caiu. Essencial para monitoramento.',
    slaSeconds: 180,
    isCritical: true,
  },
  {
    name: 'processar_fila_mensagens',
    displayName: 'Processar Mensagens',
    category: 'critical',
    schedule: '* * * * *',
    description: 'Envia mensagens da fila para WhatsApp',
    helpText:
      'Processa a fila de mensagens agendadas e envia para os medicos via WhatsApp. Respeita os limites de rate limiting e horario comercial. Critico para a operacao da Julia.',
    slaSeconds: 180,
    isCritical: true,
  },
  {
    name: 'processar_campanhas_agendadas',
    displayName: 'Processar Campanhas',
    category: 'critical',
    schedule: '* * * * *',
    description: 'Executa campanhas de prospecção',
    helpText:
      'Identifica campanhas que devem iniciar e cria os envios individuais para cada medico da lista. Controla o fluxo de prospecção automatizada da Julia.',
    slaSeconds: 180,
    isCritical: true,
  },
  {
    name: 'processar_grupos',
    displayName: 'Processar Grupos',
    category: 'critical',
    schedule: '* * * * *',
    description: 'Monitora mensagens de grupos WhatsApp',
    helpText:
      'Processa mensagens recebidas de grupos de WhatsApp para identificar oportunidades de prospecção. Monitora grupos de plantao e comunidades medicas.',
    slaSeconds: 180,
    isCritical: true,
  },

  // Frequent (every 5-15 min)
  {
    name: 'verificar_whatsapp',
    displayName: 'Verificar WhatsApp',
    category: 'frequent',
    schedule: '*/5 * * * *',
    description: 'Monitora conexoes WhatsApp',
    helpText:
      'Verifica se todas as instancias do WhatsApp estao conectadas e funcionando. Se detectar desconexao, tenta reconectar automaticamente e notifica a equipe.',
    slaSeconds: 900,
    isCritical: false,
  },
  {
    name: 'sincronizar_chips',
    displayName: 'Sincronizar Chips',
    category: 'frequent',
    schedule: '*/5 * * * *',
    description: 'Atualiza status dos chips',
    helpText:
      'Sincroniza o estado dos chips de WhatsApp com a Evolution API. Atualiza informacoes de conexao, bateria, e status de cada numero virtual.',
    slaSeconds: 900,
    isCritical: false,
  },
  {
    name: 'validar_telefones',
    displayName: 'Validar Telefones',
    category: 'frequent',
    schedule: '*/5 8-19 * * *',
    description: 'Valida numeros de medicos',
    helpText:
      'Verifica se os numeros de telefone dos medicos ainda estao ativos no WhatsApp. Remove numeros invalidos e atualiza o status no banco de dados. Executa apenas em horario comercial.',
    slaSeconds: 900,
    isCritical: false,
  },
  {
    name: 'atualizar_trust_scores',
    displayName: 'Atualizar Trust Scores',
    category: 'frequent',
    schedule: '*/15 * * * *',
    description: 'Calcula reputacao dos chips',
    helpText:
      'Recalcula o score de confianca de cada chip baseado em metricas como taxa de entrega, bloqueios, e tempo de uso. Chips com score baixo sao colocados em quarentena.',
    slaSeconds: 2700,
    isCritical: false,
  },
  {
    name: 'verificar_alertas',
    displayName: 'Verificar Alertas',
    category: 'frequent',
    schedule: '*/15 * * * *',
    description: 'Processa alertas do sistema',
    helpText:
      'Analisa metricas do sistema e gera alertas quando detecta anomalias. Monitora taxa de erros, latencia, e outros indicadores de saude.',
    slaSeconds: 2700,
    isCritical: false,
  },
  {
    name: 'verificar_alertas_grupos',
    displayName: 'Alertas de Grupos',
    category: 'frequent',
    schedule: '*/15 * * * *',
    description: 'Monitora atividade em grupos',
    helpText:
      'Detecta atividade incomum em grupos de WhatsApp monitorados. Alerta sobre grupos silenciosos ou com volume anormal de mensagens.',
    slaSeconds: 2700,
    isCritical: false,
  },
  {
    name: 'processar_handoffs',
    displayName: 'Processar Handoffs',
    category: 'frequent',
    schedule: '*/10 * * * *',
    description: 'Gerencia transicoes para humano',
    helpText:
      'Monitora conversas que foram transferidas para atendimento humano. Envia lembretes para a equipe e verifica se o medico foi atendido.',
    slaSeconds: 1800,
    isCritical: false,
  },

  // Hourly
  {
    name: 'sincronizar_briefing',
    displayName: 'Sincronizar Briefing',
    category: 'hourly',
    schedule: '0 * * * *',
    description: 'Atualiza briefing da Julia',
    helpText:
      'Busca o briefing atualizado do Google Docs e sincroniza com o sistema. O briefing contem informacoes sobre vagas, hospitais, e instrucoes diarias para a Julia.',
    slaSeconds: 7200,
    isCritical: false,
  },
  {
    name: 'processar_confirmacao_plantao',
    displayName: 'Confirmar Plantões',
    category: 'hourly',
    schedule: '0 * * * *',
    description: 'Envia confirmacoes de plantao',
    helpText:
      'Identifica plantoes realizados nas ultimas horas e envia mensagem de confirmacao para o medico. Coleta feedback sobre a experiencia no hospital.',
    slaSeconds: 7200,
    isCritical: false,
  },
  {
    name: 'oferta_autonoma',
    displayName: 'Oferta Autônoma',
    category: 'hourly',
    schedule: '0 * * * *',
    description: 'Oferta vagas automaticamente',
    helpText:
      'Identifica medicos qualificados para vagas disponiveis e envia ofertas personalizadas. Usa o historico de preferencias para fazer matching inteligente.',
    slaSeconds: 7200,
    isCritical: false,
  },

  // Daily
  {
    name: 'processar_followups',
    displayName: 'Follow-ups Diários',
    category: 'daily',
    schedule: '0 10 * * *',
    description: 'Envia follow-ups pendentes',
    helpText:
      'Processa a lista de follow-ups agendados e envia mensagens de acompanhamento para medicos que nao responderam. Respeita os intervalos minimos entre contatos.',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'processar_pausas_expiradas',
    displayName: 'Pausas Expiradas',
    category: 'daily',
    schedule: '0 6 * * *',
    description: 'Reativa medicos pausados',
    helpText:
      'Identifica medicos cujo periodo de pausa expirou e os reativa para receber novas ofertas. Medicos podem pausar temporariamente o contato via Julia.',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'avaliar_conversas_pendentes',
    displayName: 'Avaliar Conversas',
    category: 'daily',
    schedule: '0 2 * * *',
    description: 'Analisa qualidade das conversas',
    helpText:
      'Executa avaliacao automatica das conversas do dia anterior usando IA. Identifica conversas problematicas e oportunidades de melhoria na abordagem.',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'report_manha',
    displayName: 'Report da Manhã',
    category: 'daily',
    schedule: '0 10 * * *',
    description: 'Envia resumo matinal no Slack',
    helpText:
      'Gera e envia o report matinal com metricas do dia anterior, conversas ativas, e prioridades do dia. Enviado no canal #julia-reports do Slack.',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'report_fim_dia',
    displayName: 'Report Fim do Dia',
    category: 'daily',
    schedule: '0 20 * * *',
    description: 'Envia resumo noturno no Slack',
    helpText:
      'Gera o report de fim de dia com resultados das conversas, plantoes fechados, e pendencias para o dia seguinte. Enviado no canal #julia-reports do Slack.',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'doctor_state_manutencao_diaria',
    displayName: 'Manutenção Médicos',
    category: 'daily',
    schedule: '0 3 * * *',
    description: 'Atualiza estados dos medicos',
    helpText:
      'Executa manutencao diaria na maquina de estados dos medicos. Transiciona estados expirados, limpa flags temporarias, e atualiza scores de engajamento.',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'sincronizar_templates',
    displayName: 'Sincronizar Templates',
    category: 'daily',
    schedule: '0 6 * * *',
    description: 'Atualiza templates de campanha',
    helpText:
      'Busca templates de mensagens atualizados do Google Drive. Os templates sao usados para criar mensagens personalizadas em campanhas de prospecção.',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'limpar_grupos_finalizados',
    displayName: 'Limpar Grupos',
    category: 'daily',
    schedule: '0 3 * * *',
    description: 'Remove grupos antigos',
    helpText:
      'Remove da base de dados grupos de WhatsApp que foram finalizados ou que nao tem mais atividade. Libera recursos e mantem o banco limpo.',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'consolidar_metricas_grupos',
    displayName: 'Métricas de Grupos',
    category: 'daily',
    schedule: '0 1 * * *',
    description: 'Consolida estatisticas de grupos',
    helpText:
      'Agrega metricas diarias dos grupos de WhatsApp monitorados. Calcula volume de mensagens, membros ativos, e taxa de engajamento por grupo.',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'processar_retomadas',
    displayName: 'Retomadas',
    category: 'daily',
    schedule: '0 8 * * 1-5',
    description: 'Retoma conversas pausadas',
    helpText:
      'Identifica conversas que foram interrompidas e podem ser retomadas. Envia mensagem de reengajamento para medicos que pararam de responder ha alguns dias.',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'discovery_autonomo',
    displayName: 'Discovery Autônomo',
    category: 'daily',
    schedule: '0 9,14 * * 1-5',
    description: 'Prospecta novos medicos',
    helpText:
      'Executa prospecção autonoma de novos medicos. Seleciona medicos da base que ainda nao foram contatados e inicia abordagem inicial. Executa 9h e 14h em dias uteis.',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'feedback_autonomo',
    displayName: 'Feedback Autônomo',
    category: 'daily',
    schedule: '0 11 * * *',
    description: 'Coleta feedback de plantoes',
    helpText:
      'Envia mensagens pedindo feedback para medicos que realizaram plantoes recentemente. As avaliacoes ajudam a melhorar o matching de vagas.',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'snapshot_chips_diario',
    displayName: 'Snapshot de Chips',
    category: 'daily',
    schedule: '55 23 * * *',
    description: 'Registra estado dos chips',
    helpText:
      'Salva um snapshot do estado de todos os chips no fim do dia. Usado para historico e analise de tendencias de saude dos numeros virtuais.',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'resetar_contadores_chips',
    displayName: 'Reset Contadores',
    category: 'daily',
    schedule: '5 0 * * *',
    description: 'Zera contadores diarios',
    helpText:
      'Reseta os contadores diarios de mensagens enviadas por cada chip. Executado apos a meia-noite para iniciar novo ciclo de rate limiting.',
    slaSeconds: 90000,
    isCritical: false,
  },

  // Weekly
  {
    name: 'report_semanal',
    displayName: 'Report Semanal',
    category: 'weekly',
    schedule: '0 9 * * 1',
    description: 'Envia resumo semanal no Slack',
    helpText:
      'Gera report consolidado da semana com metricas de conversao, plantoes fechados, e analise de tendencias. Enviado toda segunda-feira as 9h.',
    slaSeconds: 691200,
    isCritical: false,
  },
  {
    name: 'atualizar_prompt_feedback',
    displayName: 'Atualizar Prompts',
    category: 'weekly',
    schedule: '0 2 * * 0',
    description: 'Otimiza prompts da Julia',
    helpText:
      'Analisa conversas da semana e ajusta automaticamente os prompts da Julia para melhorar a qualidade das respostas. Usa aprendizado baseado em feedback.',
    slaSeconds: 691200,
    isCritical: false,
  },
  {
    name: 'doctor_state_manutencao_semanal',
    displayName: 'Manutenção Semanal',
    category: 'weekly',
    schedule: '0 4 * * 1',
    description: 'Manutencao profunda de estados',
    helpText:
      'Executa manutencao semanal mais profunda na maquina de estados. Recalcula scores, limpa dados obsoletos, e otimiza registros de medicos.',
    slaSeconds: 691200,
    isCritical: false,
  },
  {
    name: 'reativacao_autonoma',
    displayName: 'Reativação Autônoma',
    category: 'weekly',
    schedule: '0 10 * * 1',
    description: 'Reativa medicos inativos',
    helpText:
      'Identifica medicos que nao interagem ha muito tempo e envia mensagem de reativacao. Tenta reengajar medicos que ja demonstraram interesse anteriormente.',
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
