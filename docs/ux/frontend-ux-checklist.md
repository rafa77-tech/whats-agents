# Checklist UX por Tela (Dashboard Julia)

> Objetivo: revisar usabilidade e experiencia do usuario por modulo e identificar gaps.

## Dashboard (Visao Geral)
- [ ] Metricas principais claras e com meta vs atual
- [ ] Estado de carregamento e erro explicitos
- [ ] Alertas criticos visiveis sem scroll
- [ ] Atalhos para acoes relevantes (chips, campanhas, handoff)
- [ ] Funil com drilldown rapido e contexto por etapa
- [ ] Exportacao acessivel e com feedback

## Monitor (Jobs e Saude)
- [ ] Estado atual do sistema resumido (score, fila, chips, alertas)
- [ ] Filtros de jobs com busca e categorias
- [ ] Detalhe de job com ultima execucao e erro
- [ ] Acoes rapidas (reprocessar, reexecutar, abrir logs)
- [ ] Alertas criticos com destaque visual

## Campanhas
- [ ] Criacao guiada (wizard) com validacoes claras
- [ ] Preview de audiencia com contagem e amostra
- [ ] Status da campanha com linha do tempo
- [ ] Relatorio com taxa de entrega e resposta
- [ ] Cancelar/pausar com confirmacao

## Chips (Pool)
- [ ] Lista com status, trust, capacidade e erros recentes
- [ ] Filtros por status, trust, tipo
- [ ] Acoes em massa (pause/retomar/promover)
- [ ] Detalhe do chip com historico e interacoes
- [ ] Alertas com severidade e recomendacao

## Chips (Warmup)
- [ ] Agenda diaria clara por chip
- [ ] Erros de execucao visiveis
- [ ] Acoes de ajuste (replanejar, pausar)

## Chips (Configuracoes)
- [ ] Limites explicados com impacto
- [ ] Validacao de valores fora de faixa
- [ ] Salvamento com feedback

## Conversas
- [ ] Lista com filtros (status, tag, handoff, periodo)
- [ ] Conversa com timeline e contexto do medico
- [ ] Acoes rapidas: handoff, retomar, marcar resolvido
- [ ] Indicacao clara de quem controla (ai/humano)

## Medicos
- [ ] Lista com filtros por especialidade/regiao/status
- [ ] Perfil com preferencias e historico
- [ ] Opt-out com confirmacao e motivo
- [ ] Alertas de risco (bloqueio, reclamacao, bot detection)

## Vagas/Plantoes
- [ ] Lista com filtros por hospital/especialidade/data
- [ ] Status do plantao visivel (aberta, reservada, confirmada)
- [ ] Acoes rapidas (reservar, cancelar)

## Sistema
- [ ] Modo piloto explicado com impacto
- [ ] Toggling de features autonomas com confirmacao
- [ ] Configuracoes criticas (rate limit, horario) editaveis
- [ ] Historico de mudancas (audit trail)

## Instrucoes/Diretrizes
- [ ] Lista com status (ativa/expirada)
- [ ] Criacao com contexto (foco, prioridade)
- [ ] Historico de edicoes

## Hospitais Bloqueados
- [ ] Lista com motivo e data
- [ ] Desbloqueio com confirmacao e nota

## Ajuda (Perguntas sem resposta)
- [ ] Filtro por urgencia/status
- [ ] Contexto completo antes de responder
- [ ] Resposta com confirmacao de envio

## Auditoria / Integridade
- [ ] Visao unificada de eventos, bloqueios e bypass
- [ ] Filtros por periodo, canal, motivo
- [ ] Exportacao para investigacao
- [ ] Reconciliacao e anomalas visiveis

## Guardrails Avancados
- [ ] Toggle de safe mode
- [ ] Reset de circuit breaker
- [ ] Desbloqueio de cliente/chip com audit trail

## Policy Engine
- [ ] Exibir regra atual por conversa
- [ ] Toggle de regras (com auditoria)
- [ ] Ver historico de decisao e efeitos

## Group Entry
- [ ] Importacao CSV/Excel com validacao
- [ ] Fila e status de entradas
- [ ] Agendamento e cancelamento
- [ ] Capacidade de chips para grupos

## Chatwoot / Integracoes
- [ ] Status de integracao
- [ ] Teste de conexao e diagnostico

