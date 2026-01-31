# Epic 02 - Guardrails & Safe Mode UI

## Objetivo
Criar controles operacionais para guardrails avancados, com audit trail e confirmacoes.

## Stories

### S43.E2.1 - Painel de Guardrails
**Objetivo:** Visualizar bloqueios, bypasses e deduped com filtros.

**Tarefas**
1. Tabela com event_type e reason_code.
2. Filtros por periodo, canal, metodo.

**DoD**
- [ ] Dados listados
- [ ] Filtros aplicados

### S43.E2.2 - Safe Mode Toggle
**Objetivo:** Permitir ativar/desativar safe mode com confirmacao e registro.

**Tarefas**
1. UI com switch e modal de confirmacao.
2. Registrar audit trail.

**DoD**
- [ ] Toggle funcional
- [ ] Historico registrado

### S43.E2.3 - Acoes de Emergencia
**Objetivo:** Reset de circuit breaker e desbloqueio de cliente/chip.

**Tarefas**
1. Botoes de acao com confirmacao.
2. Feedback de sucesso/erro.

