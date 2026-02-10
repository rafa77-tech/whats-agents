# API e Endpoints

> Referencia completa de todos os endpoints da API

---

## Base URL

```
Desenvolvimento: http://localhost:8000
Producao: https://whats-agents-production.up.railway.app
```

---

## Sumario

A API possui 28 routers organizados em 7 categorias:

| Categoria | Routers | Descricao |
|-----------|---------|-----------|
| **Health & Monitoramento** | health | Health checks e status do sistema |
| **Webhooks** | webhook, webhook_router, webhook_zapi, chatwoot | Recebimento de eventos externos |
| **Dashboard** | dashboard_conversations, chips_dashboard, metricas, metricas_grupos, admin, campanhas, piloto | Interface de gerenciamento |
| **Admin & Config** | sistema, guardrails, policy, integridade | Configuracao e controle do sistema |
| **Jobs** | jobs | Tarefas agendadas e workers |
| **Integrations** | extraction, incidents, supervisor_channel, sse, group_entry, warmer, handoff | Features especializadas |
| **Debug** | test_db, debug_llm, debug_whatsapp | Ferramentas de teste (remover em producao) |

---

## 1. Health & Monitoramento

### GET /health

Health check basico (liveness probe).

**Resposta:**
```json
{
    "status": "healthy",
    "timestamp": "2025-12-07T10:30:00Z",
    "service": "julia-api"
}
```

### GET /health/ready

Readiness probe - verifica dependencias criticas.

**Resposta:**
```json
{
    "status": "ready",
    "checks": {
        "redis": "ok",
        "database": "ok",
        "evolution": "ok"
    },
    "timestamp": "2025-12-07T10:30:00Z"
}
```

### GET /health/deep

Deep health check para CI/CD. Verifica environment markers, schema, prompts, localhost URLs.

**Retorna 503** se encontrar problemas criticos.

**Resposta:**
```json
{
    "status": "healthy",
    "version": {
        "git_sha": "abc123",
        "deployment_id": "20251207_103000",
        "railway_environment": "production"
    },
    "checks": {
        "environment": {"status": "ok", "app_env": "production", "db_env": "production"},
        "project_ref": {"status": "ok"},
        "localhost_check": {"status": "ok"},
        "redis": {"status": "ok"},
        "supabase": {"status": "ok"},
        "prompts": {"status": "ok"}
    },
    "deploy_safe": true
}
```

### GET /health/rate-limit

Status do rate limiting.

### GET /health/circuits

Status dos circuit breakers (claude, evolution, supabase).

### GET /health/whatsapp

Verifica status da conexao WhatsApp com Evolution API.

### GET /health/grupos

Health check do worker de processamento de grupos WhatsApp.

### GET /health/jobs

Status das execucoes dos jobs do scheduler. Mostra jobs stale (que nao rodaram dentro do SLA).

### GET /health/telefones

Estatisticas de validacao de telefones (pendentes, validos, invalidos).

### GET /health/pilot

Status do modo piloto.

### GET /health/chips

Dashboard de saude dos chips (trust score, permissoes, circuit breaker).

### GET /health/fila

Metricas da fila de mensagens (pendentes, travadas, erros).

### GET /health/alerts

Alertas consolidados do sistema.

### GET /health/score

Health score consolidado do sistema (0-100).

### GET /health/circuits/history

Historico de transicoes dos circuit breakers.

---

## 2. Webhooks

### POST /webhook/evolution

Recebe webhooks da Evolution API (mensagens WhatsApp).

**Headers:**
```
Content-Type: application/json
```

**Payload (exemplo):**
```json
{
    "event": "messages.upsert",
    "instance": "julia",
    "data": {
        "key": {
            "remoteJid": "5511999999999@s.whatsapp.net",
            "fromMe": false,
            "id": "ABC123"
        },
        "message": {
            "conversation": "Oi, tudo bem?"
        },
        "messageTimestamp": "1701950400"
    }
}
```

**Resposta:**
```json
{"status": "received"}
```

**Processamento:**
1. Retorna 200 imediatamente
2. Processa em background via message pipeline
3. Envia resposta via Evolution API

### POST /webhook/slack

Recebe eventos do Slack (mencoes, comandos).

Eventos suportados:
- `url_verification`: Verificacao inicial do Slack
- `event_callback`: Eventos de mensagens/mencoes

Roteia para Helena (analytics) ou Julia (operacional) baseado no texto.

### POST /webhook/slack/interactivity

Recebe interacoes do Slack (cliques em botoes). Usado para confirmacao de plantoes.

### POST /webhooks/evolution/{instance_name}

Webhook router multi-chip. Recebe webhooks de multiplas instancias Evolution e roteia por chip.

### POST /webhooks/zapi

Webhook para integracao Z-API. Processa eventos de mensagens, conexao, status e presenca.

### POST /chatwoot/webhook

Recebe webhooks do Chatwoot para logica de handoff via labels.

**Eventos:**
- `conversation_updated`: Detecta label "humano" para handoff

---

## 3. Dashboard - Conversas & Mensagens

### POST /dashboard/conversations/send-text

Envia mensagem de texto via WhatsApp do dashboard.

**Auth:** Requer `controlled_by='human'`

**Request:**
```json
{
    "conversation_id": "uuid",
    "message": "Texto da mensagem"
}
```

**Resposta:**
```json
{
    "success": true,
    "message_id": "ABC123",
    "interacao_id": 456,
    "chip_id": "uuid"
}
```

### POST /dashboard/conversations/send-media

Envia midia via WhatsApp (image, audio, document, video).

### POST /dashboard/conversations/{conversation_id}/control

Altera controle da conversa entre AI e humano.

**Request:**
```json
{
    "controlled_by": "ai"
}
```

### POST /dashboard/conversations/{conversation_id}/pause

Pausa Julia na conversa.

### POST /dashboard/conversations/{conversation_id}/resume

Retoma Julia na conversa.

### GET /dashboard/conversations/{conversation_id}/notes

Lista notas do supervisor para a conversa.

### POST /dashboard/conversations/{conversation_id}/notes

Cria nota do supervisor.

### POST /dashboard/conversations/{conversation_id}/feedback

Registra feedback em mensagem da Julia (positive/negative).

---

## 4. Dashboard - Chips

### GET /chips/pool/status

Status completo do pool de chips.

### GET /chips/pool/health

Relatorio de saude do pool com alertas ativos.

### GET /chips

Lista chips com filtros (status, trust_min, tipo, limit).

### GET /chips/{chip_id}

Detalhes de um chip especifico.

### GET /chips/{chip_id}/metrics

Metricas detalhadas de um chip (periodo: 1h, 6h, 24h, 7d).

### GET /chips/{chip_id}/history

Historico de operacoes e Trust Score de um chip.

### POST /chips/{chip_id}/pause

Pausa um chip (move para status degraded).

### POST /chips/{chip_id}/resume

Resume um chip pausado/degradado.

### POST /chips/{chip_id}/reactivate

Reativa um chip banido ou cancelado.

**Request:**
```json
{
    "motivo": "Recurso aprovado",
    "para_status": "pending"
}
```

### GET /chips/diagnostico

Diagnostico completo do sistema multi-chip. Testa cada etapa do fluxo.

**Query params:**
- `tipo_mensagem`: prospeccao, followup, ou resposta
- `telefone_teste`: Telefone para teste de envio (opcional)
- `enviar_teste`: Se True, envia mensagem de teste

### POST /chips/instances

Cria uma nova instancia WhatsApp.

### GET /chips/instances/{instance_name}/qr-code

Obtem QR code para pareamento da instancia.

### DELETE /chips/instances/{instance_name}

Deleta uma instancia WhatsApp.

---

## 5. Dashboard - Metricas

### GET /metricas/resumo

Resumo de metricas dos ultimos N dias.

**Query params:**
- `dias`: default 7

**Resposta:**
```json
{
    "periodo_dias": 7,
    "conversas": {
        "total": 150,
        "ativas": 23
    },
    "mensagens": {
        "recebidas": 380,
        "enviadas": 450
    },
    "handoffs": {
        "total": 5,
        "por_tipo": {"manual": 2, "auto": 3}
    },
    "taxas": {
        "resposta": 0.844,
        "handoff": 0.033
    }
}
```

### GET /metricas/funil

Metricas de funil de conversao (outbound → inbound → offer → accepted → completed).

### GET /metricas/funil/hospitais

Metricas de funil segmentadas por hospital.

### GET /metricas/funil/tendencia

Tendencia do funil nos ultimos dias.

### GET /metricas/funil/top-medicos

Medicos mais ativos (temperatura operacional).

### GET /metricas/funil/tempo-conversao

Tempo medio de conversao entre etapas do funil.

### GET /metricas/app-downloads

Metricas de envio de links do app.

### GET /metricas/app-downloads/medicos

Lista medicos que receberam links do app.

---

## 6. Dashboard - Grupos

### GET /metricas/grupos/resumo

Resumo de metricas do pipeline de grupos.

**Query params:**
- `dias`: default 7

### GET /metricas/grupos/hoje

Metricas do dia atual.

### GET /metricas/grupos/top-grupos

Grupos com mais vagas importadas.

### GET /metricas/grupos/fila

Status atual da fila de processamento.

### GET /metricas/grupos/custos

Detalhamento de custos LLM do periodo.

### POST /metricas/grupos/consolidar

Consolida metricas de grupos para metricas de pipeline.

---

## 7. Dashboard - Admin

### GET /admin/clientes/telefone/{telefone}

Busca cliente pelo telefone.

### GET /admin/conversas

Lista conversas para revisao.

**Query params:**
- `status`: active, completed, escalated
- `controlled_by`: ai, human
- `limit`: default 20
- `offset`: default 0

### GET /admin/conversas/{conversa_id}

Retorna conversa com todas as interacoes.

### POST /admin/avaliacoes

Salva avaliacao do gestor.

### GET /admin/conversas/por-tag/{tag}

Busca conversas que tem determinada tag.

### GET /admin/validacao/metricas

Metricas do validador de output.

### POST /admin/validacao/testar

Testa um texto contra o validador de output.

---

## 8. Dashboard - Campanhas

### POST /campanhas

Cria nova campanha de outreach.

**Request:**
```json
{
    "nome_template": "Anestesistas ABC",
    "tipo_campanha": "oferta",
    "especialidades": ["anestesiologia"],
    "quantidade_alvo": 50,
    "modo_selecao": "deterministico"
}
```

### POST /campanhas/{campanha_id}/iniciar

Inicia execucao de campanha.

### GET /campanhas/{campanha_id}/relatorio

Relatorio completo da campanha.

### GET /campanhas

Lista campanhas com filtros.

### PATCH /campanhas/{campanha_id}/status

Atualiza status de uma campanha.

---

## 9. Extraction Pipeline (Sprint 53)

### GET /extraction/insights/conversation/{conversation_id}

Busca insights de uma conversa especifica.

### GET /extraction/insights/cliente/{cliente_id}

Busca historico de insights de um cliente/medico.

### GET /extraction/insights/campaign/{campaign_id}

Busca insights de uma campanha especifica.

### GET /extraction/campaign/{campaign_id}/report

Gera relatorio Julia para uma campanha (analise qualitativa com LLM).

### GET /extraction/campaign-summary

Resumo agregado de todas as campanhas com insights.

### GET /extraction/stats

Estatisticas gerais do sistema de extracao.

### POST /extraction/backfill

Dispara backfill de extracoes em background.

**Request:**
```json
{
    "dias": 30,
    "campanha_id": 123,
    "dry_run": false,
    "max_interacoes": 1000
}
```

### GET /extraction/opportunities

Retorna oportunidades agrupadas por proximo_passo (enviar_vagas, agendar_followup, escalar_humano).

---

## 10. Supervisor Channel (Sprint 54)

### GET /supervisor/channel/{conversation_id}/history

Retorna historico do supervisor channel.

### POST /supervisor/channel/{conversation_id}/message

Envia pergunta do supervisor e recebe resposta da Julia sobre a conversa.

**Request:**
```json
{
    "content": "Como esta indo essa conversa?"
}
```

### POST /supervisor/channel/{conversation_id}/instruct

Cria instrucao com preview. Supervisor escreve instrucao, Julia gera preview da mensagem.

**Request:**
```json
{
    "instruction": "Envie os links do app para o medico"
}
```

### POST /supervisor/channel/{conversation_id}/instruct/{id}/confirm

Confirma envio da mensagem gerada pela instrucao.

### POST /supervisor/channel/{conversation_id}/instruct/{id}/reject

Rejeita instrucao - nenhuma mensagem e enviada ao medico.

---

## 11. SSE - Real-Time Updates (Sprint 54)

### GET /dashboard/sse/conversations/{conversation_id}

Stream SSE de eventos para uma conversa.

**Eventos emitidos:**
- `new_message`: Nova mensagem na conversa
- `control_change`: Mudanca de controle (ai/human)
- `pause_change`: Conversa pausada/retomada
- `channel_message`: Nova mensagem no supervisor channel

**Uso:**
```javascript
const eventSource = new EventSource(`/dashboard/sse/conversations/${id}`);
eventSource.addEventListener('new_message', (e) => {
    const data = JSON.parse(e.data);
    console.log('Nova mensagem:', data);
});
```

---

## 12. Incidents (Sprint 55)

### POST /incidents

Registra uma mudanca de status (health score).

### GET /incidents

Lista historico de incidentes.

**Query params:**
- `limit`: default 20
- `status`: filtrar por status
- `since`: data inicial

### GET /incidents/stats

Estatisticas de incidentes (MTTR, uptime, etc).

---

## 13. Jobs (Tarefas Agendadas)

Endpoints chamados pelo scheduler ou manualmente.

### POST /jobs/heartbeat

Registra heartbeat da Julia (cada minuto).

### POST /jobs/primeira-mensagem

Envia primeira mensagem de prospeccao para um medico.

### POST /jobs/processar-mensagens-agendadas

Processa fila de mensagens agendadas (cada minuto).

### POST /jobs/processar-campanhas-agendadas

Inicia campanhas que atingiram horario agendado (cada minuto).

### POST /jobs/verificar-alertas

Verifica condicoes de alerta e notifica (cada 15 minutos).

### POST /jobs/processar-followups

Processa follow-ups pendentes (48h, 5d, 15d) - diario as 10h.

### POST /jobs/processar-pausas-expiradas

Reativa conversas pausadas ha mais de 60 dias - diario as 6h.

### POST /jobs/avaliar-conversas-pendentes

Avalia qualidade de conversas encerradas - diario as 2h.

### POST /jobs/relatorio-diario

Gera e envia relatorio diario para Slack - diario as 8h.

### POST /jobs/report-periodo

Gera report de periodo especifico (manha, almoco, tarde, fim_dia).

### POST /jobs/report-semanal

Gera report semanal consolidado - segunda as 9h.

### POST /jobs/sincronizar-briefing

Sincroniza briefing do Google Docs - cada hora.

### POST /jobs/processar-grupos

Processa mensagens de grupos WhatsApp (batch_size, max_workers).

### POST /jobs/processar-confirmacao-plantao

Transiciona vagas vencidas (reservada → pendente_confirmacao) - horario.

### POST /jobs/processar-handoffs

Processa handoffs pendentes (follow-up e expiracao) - cada 10 minutos.

### POST /jobs/processar-retomadas

Processa mensagens fora do horario pendentes - diario as 08:00.

### POST /jobs/reconcile-touches

Job de reconciliacao de doctor_state.last_touch_* - cada 10-15 minutos.

### POST /jobs/validar-telefones

Valida telefones via checkNumberStatus - cada 5 minutos, das 8h as 20h.

### POST /jobs/executar-gatilhos-autonomos

Executa todos os gatilhos automaticos da Julia (Discovery, Oferta, Reativacao, Feedback).

**IMPORTANTE:** So executa se PILOT_MODE=False.

### POST /jobs/atualizar-trust-scores

Recalcula Trust Score de todos os chips ativos - cada 15 minutos.

### POST /jobs/sincronizar-chips

Sincroniza chips com Evolution API - cada 5 minutos.

### POST /jobs/monitorar-fila

Monitora saude da fila de mensagens - cada 10 minutos.

### POST /jobs/snapshot-chips-diario

Cria snapshots diarios das metricas de chips - 23:55 todos os dias.

### POST /jobs/resetar-contadores-chips

Reseta contadores diarios dos chips - 00:05 todos os dias.

---

## 14. Group Entry Engine (Sprint 25)

### POST /group-entry/import/csv

Importa links de grupos de um arquivo CSV.

### POST /group-entry/import/excel

Importa links de grupos de um arquivo Excel (.xlsx).

### GET /group-entry/links

Lista links de grupos com filtros.

### GET /group-entry/links/stats

Estatisticas de links por status.

### POST /group-entry/validate/{link_id}

Valida um link especifico.

### POST /group-entry/validate/batch

Valida lote de links pendentes.

### POST /group-entry/schedule

Agenda entrada em um grupo especifico.

### GET /group-entry/queue

Lista proximas entradas na fila.

### POST /group-entry/process

Processa entradas pendentes na fila.

### GET /group-entry/chips

Lista chips disponiveis para entrada em grupos.

### GET /group-entry/config

Retorna configuracao atual.

### PATCH /group-entry/config

Atualiza configuracao de limites.

---

## 15. Warmer (Sprint 25)

### POST /warmer/iniciar

Inicia processo de warmup para um chip.

### POST /warmer/pausar

Pausa processo de warmup de um chip.

### POST /warmer/transicao

Forca transicao de fase de um chip.

### GET /warmer/trust/{chip_id}

Obtem trust score de um chip.

### GET /warmer/permissoes/{chip_id}

Obtem permissoes atuais de um chip.

### GET /warmer/alertas

Lista alertas ativos.

### GET /warmer/alertas/{chip_id}/analisar

Analisa um chip e retorna alertas encontrados.

### GET /warmer/status

Status geral do pool de chips.

### GET /warmer/politicas

Consulta politicas Meta/WhatsApp via RAG.

### POST /warmer/politicas/verificar

Verifica se uma acao esta em conformidade com politicas.

---

## 16. Guardrails (Sprint 43)

### GET /guardrails/flags

Lista todas as feature flags e seus estados.

### GET /guardrails/flags/{flag_name}

Obtem valor de uma feature flag especifica.

### POST /guardrails/flags/{flag_name}

Atualiza valor de uma feature flag.

**Request:**
```json
{
    "enabled": true,
    "motivo": "Ativar envio de prospeccao",
    "usuario": "admin"
}
```

### POST /guardrails/desbloquear/chip/{chip_id}

Desbloqueia um chip manualmente (reseta circuit breaker, cooldown, contadores).

### POST /guardrails/desbloquear/cliente/{cliente_id}

Desbloqueia um cliente manualmente (reseta rate limit, flags de bloqueio).

### GET /guardrails/circuits

Lista todos os circuit breakers e seus estados.

### POST /guardrails/circuits/{circuit_name}/reset

Reseta um circuit breaker manualmente.

### GET /guardrails/emergencia/status

Verifica status do modo emergencia.

### POST /guardrails/emergencia/ativar

Ativa modo de emergencia (desabilita todas as flags de envio).

### POST /guardrails/emergencia/desativar

Desativa modo de emergencia (reabilita flags de envio).

### GET /guardrails/audit

Busca registros no audit trail.

**Query params:**
- `acao`: Tipo de acao
- `entidade`: Tipo de entidade
- `usuario`: Quem executou
- `horas`: Periodo (default 24h)
- `limite`: Max registros (default 100)

---

## 17. Policy Engine (Sprint 43)

### GET /policy/status

Status geral do Policy Engine (enabled, safe_mode, rules disabled).

### POST /policy/enable

Habilita o Policy Engine.

### POST /policy/disable

Desabilita o Policy Engine.

### GET /policy/safe-mode

Status do modo seguro.

### POST /policy/safe-mode/enable

Ativa modo seguro (wait ou handoff).

### POST /policy/safe-mode/disable

Desativa modo seguro.

### GET /policy/rules

Lista todas as regras do Policy Engine.

### POST /policy/rules/{rule_id}/enable

Habilita uma regra especifica.

### POST /policy/rules/{rule_id}/disable

Desabilita uma regra especifica.

### GET /policy/metrics

Resumo de metricas do Policy Engine.

### GET /policy/metrics/decisions

Conta total de decisoes no periodo.

### GET /policy/metrics/rules

Agrupa decisoes por regra.

### GET /policy/metrics/actions

Agrupa decisoes por acao primaria.

### GET /policy/metrics/hourly

Decisoes agrupadas por hora.

### GET /policy/metrics/orphans

Encontra decisoes orfas (sem efeitos correspondentes).

### GET /policy/decisions/cliente/{cliente_id}

Lista decisoes de um cliente especifico.

---

## 18. Integridade (Sprint 18)

### GET /integridade/auditoria

Executa auditoria completa de cobertura de eventos.

**Query params:**
- `hours`: Janela de tempo (default 24h)

### GET /integridade/violacoes

Lista violacoes de invariantes do funil.

### POST /integridade/reconciliacao

Executa reconciliacao bidirecional DB vs Eventos.

### GET /integridade/anomalias

Lista anomalias de dados detectadas.

### GET /integridade/anomalias/recorrentes

Lista anomalias recorrentes (detectadas multiplas vezes).

### POST /integridade/anomalias/{anomaly_id}/resolver

Marca uma anomalia como resolvida.

### GET /integridade/kpis

Resumo dos 3 KPIs principais (Conversion Rate, Time-to-Fill, Health Score).

### GET /integridade/kpis/conversion

Taxas de conversao segmentadas.

### GET /integridade/kpis/time-to-fill

Breakdown de tempos do funil.

### GET /integridade/kpis/health

Health Score composto (pressao, friccao, qualidade, spam).

---

## 19. Sistema (Sprint 32)

### GET /sistema/status

Status atual do sistema (pilot_mode, autonomous_features).

### POST /sistema/pilot-mode

Altera modo piloto.

**Request:**
```json
{
    "pilot_mode": true,
    "changed_by": "admin"
}
```

### POST /sistema/features/{feature}

Altera status de uma feature autonoma individual.

**Features disponiveis:**
- `discovery_automatico`
- `oferta_automatica`
- `reativacao_automatica`
- `feedback_automatico`

---

## 20. Handoff (Sprint 20)

### GET /handoff/confirm

Processa confirmacao de handoff via link externo.

**Query params:**
- `t`: Token JWT de confirmacao

Retorna pagina HTML de feedback.

---

## 21. Piloto (Sprint 35)

### GET /piloto/status

Status atual do piloto.

Retorna contadores de campanha discovery, envios na fila, e metricas de resposta.

---

## 22. Debug - Test DB

**IMPORTANTE:** Remover em producao.

### GET /test/db/connection

Testa conexao com Supabase.

### GET /test/db/medicos/count

Conta medicos na base.

### GET /test/db/medicos/piloto

Lista medicos do grupo piloto.

### GET /test/db/vagas/count

Conta vagas na base.

---

## 23. Debug - Test LLM

**IMPORTANTE:** Remover em producao.

### POST /test/llm/resposta

Testa geracao de resposta.

### POST /test/llm/julia

Testa resposta da Julia com contexto completo.

### GET /test/llm/health

Testa se LLM esta respondendo.

---

## 24. Debug - Test WhatsApp

**IMPORTANTE:** Remover em producao.

### GET /test/whatsapp/status

Verifica status da conexao WhatsApp.

### POST /test/whatsapp/enviar

Envia mensagem de teste (CUIDADO: envia mensagem real!).

---

## Codigos de Erro

| Codigo | Descricao |
|--------|-----------|
| 200 | Sucesso |
| 400 | Request invalido |
| 401 | Nao autorizado |
| 403 | Proibido (ex: conversa nao esta em handoff) |
| 404 | Recurso nao encontrado |
| 429 | Rate limit excedido |
| 500 | Erro interno |
| 503 | Servico indisponivel (circuit open ou health check falhou) |

---

## Rate Limits da API

| Endpoint | Limite |
|----------|--------|
| /webhook/* | Sem limite (Evolution controla) |
| /jobs/* | 1 req/min por job |
| /admin/* | 100 req/min |
| /metricas/* | 10 req/min |
| /test/* | 10 req/min |
| /handoff/confirm | 30/min, 200/hora (por IP) |

---

## Autenticacao

**Desenvolvimento:** Sem autenticacao (localhost).

**Producao:** Railway nao expoe endpoints publicamente (apenas via proxy interno). Endpoints sensiveis (admin, sistema, guardrails) devem ser protegidos por API key no futuro.

---

## Exemplos de Uso

### Health Check

```bash
curl http://localhost:8000/health
```

### Enviar Mensagem do Dashboard

```bash
curl -X POST http://localhost:8000/dashboard/conversations/send-text \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "uuid-da-conversa",
    "message": "Ola, como posso ajudar?"
  }'
```

### Criar Campanha

```bash
curl -X POST http://localhost:8000/campanhas \
  -H "Content-Type: application/json" \
  -d '{
    "nome_template": "Anestesistas ABC",
    "tipo_campanha": "oferta",
    "especialidades": ["anestesiologia"],
    "quantidade_alvo": 50,
    "modo_selecao": "deterministico"
  }'
```

### Desbloquear Chip

```bash
curl -X POST http://localhost:8000/guardrails/desbloquear/chip/uuid-do-chip \
  -H "Content-Type: application/json" \
  -d '{
    "motivo": "Falso positivo",
    "usuario": "admin"
  }'
```

### Ativar Modo Emergencia

```bash
curl -X POST http://localhost:8000/guardrails/emergencia/ativar \
  -H "Content-Type: application/json" \
  -d '{
    "motivo": "Problema detectado",
    "usuario": "admin"
  }'
```

### Consultar Metricas de Funil

```bash
curl "http://localhost:8000/metricas/funil?hours=168"
```

### SSE - Acompanhar Conversa em Tempo Real

```javascript
const eventSource = new EventSource(
  'http://localhost:8000/dashboard/sse/conversations/uuid-da-conversa'
);

eventSource.addEventListener('new_message', (e) => {
  console.log('Nova mensagem:', JSON.parse(e.data));
});

eventSource.addEventListener('control_change', (e) => {
  console.log('Controle mudou:', JSON.parse(e.data));
});
```

---

## Versionamento

**Versao atual:** 0.1.0

A API nao possui versionamento no path (sem `/v1`). Mudancas breaking serao comunicadas e terao periodo de migracao.

---

## Recursos Adicionais

- **API Docs (Swagger):** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json
