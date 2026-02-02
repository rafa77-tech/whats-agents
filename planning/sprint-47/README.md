# Sprint 47: Helena - Agente de Gestão Slack

## Status: ✅ Completa

## Objetivo
Substituir Julia no Slack por Helena, agente de analytics com SQL dinâmico.

## Épicos Implementados

| ID | Nome | Status |
|----|------|--------|
| E01 | Remover Notificações Slack | ✅ Completo |
| E02 | Função SQL Readonly | ✅ Completo |
| E03 | Core Helena (Session + Agent) | ✅ Completo |
| E04 | Tools Pré-definidas | ✅ Completo |
| E05 | Tool SQL Dinâmico | ✅ Completo |
| E06 | Integração Webhook | ✅ Completo |
| E07 | Testes | ✅ Completo |

## Arquivos Criados

### Serviço Helena
- `app/services/helena/__init__.py`
- `app/services/helena/agent.py` - AgenteHelena
- `app/services/helena/session.py` - SessionManager
- `app/services/helena/prompts.py` - System prompt com schema

### Tools Helena
- `app/tools/helena/__init__.py` - Dispatcher + exports
- `app/tools/helena/metricas.py` - metricas_periodo, metricas_conversao, metricas_campanhas
- `app/tools/helena/sistema.py` - status_sistema, listar_handoffs
- `app/tools/helena/sql.py` - consulta_sql (SQL dinâmico)

### Testes
- `tests/services/helena/test_agent.py` - 13 testes
- `tests/tools/helena/test_sql.py` - 19 testes
- `tests/tools/helena/test_metricas.py` - 13 testes

## Arquivos Modificados

### Notificações Removidas
- `app/services/slack.py` - Funções de notificação removidas
- `app/services/slack/__init__.py` - Exports atualizados
- `app/services/alertas.py` - Alertas convertidos em logs
- `app/services/business_events/alerts.py` - send_alert_to_slack → log
- `app/services/chips/orchestrator.py` - notificar_slack → log
- `app/services/chips/health_monitor.py` - notificar_slack → log
- `app/services/handoff/flow.py` - Notificações removidas
- `app/services/vagas/service.py` - notificar_plantao_reservado → log
- `app/services/confirmacao_plantao.py` - notificar_confirmacao_plantao → log

### Webhook
- `app/api/routes/webhook.py` - Roteamento Helena adicionado

## Migrations Aplicadas

1. `create_readonly_query_function` - Função SQL segura
2. `create_helena_sessoes_table` - Tabela de sessões

## Como Usar Helena

No Slack, mencione "helena" junto com sua pergunta:

```
@bot helena como foi hoje?
@bot helena status sistema
@bot helena quantos cardiologistas responderam esta semana?
```

Helena detecta automaticamente qual tool usar ou monta SQL dinâmico quando necessário.

## Segurança

- Helena NÃO é acionável via WhatsApp
- Julia NÃO tem acesso a tools de analytics
- SQL dinâmico validado (apenas SELECT, LIMIT ≤ 100)
- Tabelas de sistema bloqueadas (pg_shadow, etc.)
- Timeout de 10 segundos nas queries
