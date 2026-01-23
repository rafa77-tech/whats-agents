/**
 * Mock data for Sistema E2E tests
 *
 * Used when running E2E tests without a backend
 */

export const mockSistemaStatus = {
  julia_ativa: true,
  modo_piloto: false,
  total_conversas: 1250,
  conversas_ativas: 89,
  rate_limit_atual: 45,
  rate_limit_maximo: 100,
  ultima_mensagem: '2026-01-23T11:55:00Z',
  uptime_horas: 168,
  erros_ultimo_dia: 3,
}

export const mockSistemaConfig = {
  rate_limit: {
    mensagens_por_hora: 20,
    mensagens_por_dia: 100,
    intervalo_minimo_segundos: 45,
  },
  horario_operacao: {
    inicio: '08:00',
    fim: '20:00',
    dias_semana: [1, 2, 3, 4, 5],
  },
  features: {
    campanhas_ativas: true,
    aquecimento_automatico: true,
    handoff_automatico: true,
  },
}

export const mockPilotMode = {
  enabled: false,
  medicos_piloto: [],
  max_medicos: 10,
}
