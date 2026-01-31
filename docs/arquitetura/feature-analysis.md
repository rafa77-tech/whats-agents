# Mapa de Features, Fluxos e Guardrails (Auditoria Técnica)

> Documento consolidado a partir de leitura de código + docs do repositório.

## 1) Visão Geral do Sistema (Resumo Executivo)

O sistema é um agente de IA para **staffing médico via WhatsApp**. Ele recebe mensagens (inbound), aplica um pipeline com validações e regras, decide a melhor ação via **Policy Engine**, gera resposta com **LLM + tools**, e envia outbound com **guardrails** rigorosos e auditoria por **business events**. Além disso, opera campanhas, follow-ups, reativações, handoffs para humanos, warmup de números (chips) e dashboards operacionais.

**Objetivo principal:** passar no teste de Turing e evitar bloqueios no WhatsApp.


## 2) Diagrama de Fluxo (End-to-End)

```text
WhatsApp (médico)
  │
  ▼
Evolution API / Z-API
  │  POST /webhook/evolution  (ou /webhooks/evolution/{instance} / /webhooks/zapi)
  ▼
Pipeline (pre → core → post)
  │  Parse + presence + load entities
  │  - cria/recupera médico e conversa
  │  - opt-out / bot / handoff / fora-horário
  │
  ├──> clientes (médicos)
  ├──> conversations (conversas)
  ├──> interacoes (inbound)
  └──> doctor_state (estado p/ policy)

  │  Policy Engine decide ação + constraints
  │  - rule order: opted_out → cooling_off → ...
  │  - gera policy_decision_id
  ▼
LLM + Tools (buscar_vagas, reservar_plantao, etc)
  │
  ▼
Post-processors
  │  - valida output
  │  - timing humanizado
  │  - envia via outbound
  │  - salva interação
  │  - métricas / eventos
  ▼
send_outbound_message (guardrails + dedupe + provider)
  │
  ├──> business_events: doctor_outbound, outbound_blocked/bypass/deduped
  ├──> policy_events (effect + interaction_id)
  ├──> doctor_state.last_touch_*
  └──> interacoes (outbound)
  ▼
Evolution API / Multi-chip
  ▼
WhatsApp (resposta)
```

### Fluxos Proativos (Campanhas/Follow-ups/Reativação)

```text
Campanhas / Followups / Reativação
  │
  ├── campanhas + segmentação → fila_mensagens
  └── jobs/workers processam fila → send_outbound_message
         │
         ├── guardrails + dedupe + allowlist DEV
         ├── business_events + attribution
         └── doctor_state.last_touch_*
```

### Handoff Humano

```text
Handoff trigger (pipeline/policy ou Chatwoot label)
  │
  ├── handoffs (registro)
  ├── conversations.controlled_by = 'human'
  └── business_events + Slack/Chatwoot
```

### Multi‑chip / Warmup

```text
Webhook Router (multi‑chip) / Warmup Orchestrator
  │
  ├── chips / chip_metrics / chip_interactions
  └── health + trust score + disponibilidade
```


## 3) Mapa de Features por Módulo

### 3.1 Entrada / API
- `app/api/routes/webhook.py`: webhook principal (Evolution + Slack), dedupe por Redis e processamento em background.
- `app/api/routes/webhook_router.py`: roteamento multi‑chip (instance_name) + métricas por chip.
- `app/api/routes/webhook_zapi.py`: suporte a Z‑API (multi‑provider).

### 3.2 Pipeline
- `app/pipeline/pre_processors.py`: parse, presence, load entities, opt‑out, handoff triggers, fora‑horário, bot detection, sync Chatwoot, etc.
- `app/pipeline/post_processors.py`: valida resposta, calcula timing, envia outbound, persiste interação, emite métricas/eventos.
- `app/pipeline/core.py` e `app/pipeline/setup.py`: orquestração e propagação de `policy_decision_id`.

### 3.3 Agente / LLM
- `app/services/agente.py`: orquestra contexto, tools, policy, envio.
- `app/services/llm.py`, `app/core/prompts.py`, `app/prompts/builder.py`: construção de prompt com `policy_constraints`.
- `app/tools/*`: ações do agente (vagas, lembretes, Slack ops).

### 3.4 Outbound + Guardrails
- `app/services/outbound.py`: ponto único de envio (allowlist DEV, dedupe, guardrails, multi‑chip, finalização).
- `app/services/guardrails/check.py`: regras e auditoria de bloqueios.
- `app/services/guardrails/types.py`: contrato de `OutboundContext` e outcomes.
- `app/services/outbound_dedupe.py`: deduplicação anti-spam.

### 3.5 Policy Engine
- `app/services/policy/decide.py`: motor determinístico com kill‑switch e safe‑mode.
- `app/services/policy/rules.py`: regras ordenadas por severidade.
- `app/services/policy/types.py`: `DoctorState`, `PrimaryAction`, `Tone`, etc.
- `app/services/policy/repository.py`: persistência e cache do `doctor_state`.

### 3.6 Negócio e CRM
- `app/services/vaga.py`: gestão de plantões.
- `app/services/campanhas/*`: segmentação e execução.
- `app/services/followup.py`: cadências de follow‑up.
- `app/services/handoff/*`: transferência IA↔humano.
- `app/services/segmentacao.py`: filtros e targeting.

### 3.7 Observabilidade
- `app/services/business_events/*`: eventos de negócio, métricas e auditoria.
- `app/api/routes/metricas.py`: funil de conversão e métricas.
- `app/api/routes/integridade.py`: auditoria e reconciliação.

### 3.8 Chips / Warmup
- `app/services/warmer/*`: warmup, trust score, alertas.
- `app/services/chips/*`: seleção, health, orchestrator.
- `app/api/routes/chips_dashboard.py`: dashboard e controle.

### 3.9 Group Entry Engine
- `app/services/group_entry/*` + `app/api/routes/group_entry.py`: importação de links, validação, agendamento e processamento de entradas.


## 4) Fluxo de Dados e Tabelas‑Chave

### Conversa e Mensagens
- `clientes`: médicos e preferências.
- `conversations`: sessão ativa (status, controlled_by).
- `interacoes`: mensagens inbound/outbound.
- `handoffs`: trocas IA↔humano.

### Estado do Médico (Policy)
- `doctor_state`: permission_state, temperature, objection, last_inbound/outbound, next_allowed_at, etc.

### Campanhas
- `campanhas`, `execucoes_campanhas`, `envios`, `metricas_campanhas`.

### Fila Outbound
- `fila_mensagens`: backlog de envios (campanha, followup, lembretes).
- `outbound_dedupe`: dedupe de mensagens.

### Auditoria / Eventos
- `business_events`: eventos de funil + guardrails.
- `policy_events`: decisões e efeitos de policy.

### Chips / Warmer
- `chips`, `chip_metrics_hourly`, `chip_interactions`, `chip_trust_history`.


## 5) Guardrails e Decisões (Matriz Regra → Comportamento → Impacto)

### 5.1 Policy Engine (o que Julia pode fazer)
- **opted_out** → WAIT terminal → evita contato indevido.
- **cooling_off** → resposta mínima, sem oferta → reduz atrito.
- **grave_objection** → HANDOFF imediato → protege reputação.
- **high_objection** → cautela extra → reduz pressão.
- **medium_objection** → trata objeção → melhora conversão.
- **new_doctor_first_contact** → discovery → evita venda precoce.
- **silence_reactivation** → reativação suave (7d + quente) → recupera conversas.
- **cold_temperature** → followup conservador → evita bloqueios.
- **hot_temperature** → oferta permitida → acelera fechamento.
- **default** → conservador, só oferta se médico pedir.

### 5.2 Guardrails Outbound (se a mensagem sai)
- **DEV allowlist** → bloqueio total fora da lista → evita envio acidental.
- **Deduplicação** → bloqueia duplicatas → anti‑spam.
- **Reply proof (R‑1)** → reply exige `inbound_interaction_id` + `last_inbound_at` recente.
- **Opt‑out absoluto (R0)** → só bypass humano via Slack com motivo.
- **Quiet hours (R0.5)** → proativo nunca fora do horário.
- **Cooling off / next_allowed / contact_cap (R1–R3)** → controle de cadência.
- **Kill switches / safe mode (R4)** → pausa geral.
- **Campaign cooldown (R5)** → 3 dias entre campanhas diferentes.

### 5.3 Outcomes Normalizados
- `SendOutcome`: SENT, BLOCKED_*, DEDUPED, FAILED_*, BYPASS.
- Eventos emitidos: `outbound_blocked`, `outbound_bypass`, `outbound_deduped`.


## 6) Mapa Endpoint → Serviço

### Webhooks
- `POST /webhook/evolution` → `message_pipeline.process` (pipeline completo)
- `POST /webhook/slack` → tools/handler Slack
- `POST /webhooks/evolution/{instance}` → multi-chip + métricas + pipeline
- `POST /webhooks/zapi` → roteamento Z‑API + métricas

### Health
- `GET /health` → liveness
- `GET /health/ready` → Redis + Supabase
- `GET /health/*` → checks de circuit, schema, prompts, chips, fila

### Campanhas
- `POST /campanhas` → `campanha_repository.criar`
- `POST /campanhas/{id}/iniciar` → `campanha_executor.executar`
- `POST /campanhas/segmento/preview` → `segmentacao_service`
- `GET /campanhas/{id}/relatorio` → Supabase (`fila_mensagens`) + repo

### Jobs
- `POST /jobs/primeira-mensagem` → `services.jobs.enviar_primeira_mensagem`
- `POST /jobs/processar-mensagens-agendadas` → `services.fila_mensagens.processar_mensagens_agendadas`
- `POST /jobs/processar-campanhas-agendadas` → `services.jobs.processar_campanhas_agendadas`
- `POST /jobs/processar-followups` → `services.followup.processar_followups_pendentes`
- `POST /jobs/sincronizar-briefing` → `services.briefing.sincronizar_briefing`
- `POST /jobs/processar-fila-mensagens` → `services.jobs.processar_fila`
- `POST /jobs/doctor-state-*` → `workers.temperature_decay.*`
- `POST /jobs/processar-grupos` → `workers.grupos_worker.processar_ciclo_grupos`

### Integridade
- `GET /integridade/auditoria` → `business_events.audit.run_full_audit`
- `GET /integridade/violacoes` → `business_events.audit.get_invariant_violations`
- `POST /integridade/reconciliacao` → `business_events.reconciliation.reconciliation_job`
- `GET /integridade/anomalias` → `business_events.reconciliation.listar_anomalias`
- `GET /integridade/kpis` → `business_events.kpis.*`

### Métricas
- `GET /metricas/resumo` → Supabase direto
- `GET /metricas/funil*` → `business_events.metrics.*`

### Admin
- `GET /admin/conversas` → Supabase
- `POST /admin/avaliacoes` → Supabase (`avaliacoes_qualidade`)

### Chatwoot / Handoff
- `POST /chatwoot/webhook` → `handoff.iniciar_handoff` / `finalizar_handoff`
- `GET /chatwoot/status` → `chatwoot_service`
- `GET /chatwoot/test-api` → chamada API Chatwoot
- `GET /handoff/confirm` → valida token + `processar_confirmacao`

### Sistema
- `GET /sistema/status` → Supabase (`system_config`) + settings
- `POST /sistema/pilot-mode` → Supabase + settings

### Warmer / Chips
- `/warmer/*` → `services.warmer.*`
- `/chips/*` → `services.chips.*` + Supabase

### Group Entry
- `/group-entry/*` → `services.group_entry.*`

## 8) Cobertura de Frontend (UI x Backend)

Legenda:
- View: visualização no dashboard
- Config: ações/edições/controles no dashboard
- Status: ✅ completo | 🟡 parcial | ❌ ausente | ⚠️ possível mismatch de API

| Feature / Domínio | UI (View/Config) | Backend / Serviço | Status |
|---|---|---|---|
| Campanhas | View + Config | `app/api/routes/campanhas.py` + `services/campanhas/*` | ✅ |
| Chips / Pool | View + Config | `app/api/routes/chips_dashboard.py` + `services/chips/*` | ✅ |
| Warmup chips | View + Config | `app/api/routes/warmer.py` + `services/warmer/*` | ✅ |
| Instâncias chips (QR/connection) | View + Config | `app/api/routes/chips_dashboard.py` | ✅ |
| Sistema (pilot + features autônomas) | View + Config | `app/api/routes/sistema.py` | ✅ |
| Rate limit (configuração) | View (read-only) | `app/api/routes/health.py` + `sistema/config` | 🟡 |
| Conversas (handoff manual) | View + Config | UI chama `/dashboard/conversations/*` | ⚠️ |
| Médicos (opt-out) | View + Config | UI chama `/dashboard/doctors/*` | ⚠️ |
| Vagas/Plantões | View | UI chama `/dashboard/shifts/*` | ⚠️ |
| Métricas gerais / Funil | View | UI chama `/dashboard/metrics/*` | ⚠️ |
| Monitor Jobs | View | `dashboard/app/api/dashboard/monitor/*` (Supabase) | 🟡 |
| Instruções / Diretrizes | View + Config | `dashboard/app/api/diretrizes/*` (Supabase) | ✅ |
| Hospitais bloqueados | View + Config | `dashboard/app/api/hospitais/*` (Supabase) | ✅ |
| Ajuda (Julia não soube responder) | View + Config | `dashboard/app/api/ajuda/*` + `/conversas/.../retomar` | 🟡 |
| Integridade (auditoria/anomalias) | Nenhuma | `app/api/routes/integridade.py` | ❌ |
| Guardrails avançados (desbloqueios, circuit reset, safe mode) | Nenhuma | `app/services/sistema_guardrails.py` | ❌ |
| Policy Engine (flags/regras) | Nenhuma | `app/services/policy/*` | ❌ |
| Group Entry Engine | Nenhuma | `app/api/routes/group_entry.py` | ❌ |
| Admin / Qualidade (avaliações) | Nenhuma | `app/api/routes/admin.py` | ❌ |
| Chatwoot status/test | Nenhuma | `app/api/routes/chatwoot.py` | ❌ |

### Priorização recomendada (impacto operacional)
1. Integridade / Auditoria
2. Guardrails avançados
3. Policy Engine
4. Group Entry Engine
5. Admin / Qualidade
6. Chatwoot status/test
7. Rate limit config completo (deixar de ser read-only)

### Possível mismatch de API (`/dashboard/*`)

Há páginas do frontend que chamam endpoints `.../dashboard/*` no backend via `NEXT_PUBLIC_API_URL`. **Essas rotas não existem no backend deste repositório**. Isso pode indicar:
- Backend separado/externo para endpoints de dashboard, ou
- Rotas ausentes neste código.

Se o backend externo não existir ou estiver desatualizado, a UI perde dados.

Páginas afetadas (exemplos principais):
- Dashboard executivo: `/dashboard/metrics`, `/dashboard/funnel`, `/dashboard/alerts`, `/dashboard/activity`, `/dashboard/status`
- Conversas: `/dashboard/conversations/*`
- Médicos: `/dashboard/doctors/*`
- Vagas/Plantões: `/dashboard/shifts/*`
- Métricas avançadas: `/dashboard/metrics/export`
- Auditoria (frontend): `/dashboard/audit`, `/dashboard/audit/export`


## 7) Observações Operacionais

- `send_outbound_message` é **único ponto permitido** para envio outbound.
- `policy_decision_id` é propagado ao longo do pipeline para auditoria.
- `business_events` é a trilha oficial para métricas e guardrails.
- `doctor_state` é o estado fonte para decisões comportamentais.


---

# Análise Crítica (Pontos Fortes e Riscos)

## Pontos Fortes

1) **Separação clara de responsabilidades**
- Pipeline modular (pre/core/post) e services isolados.
- `send_outbound_message` como gate único reduz bypass indevido.

2) **Governança operacional sólida**
- Guardrails rígidos (opt‑out, quiet hours, contact cap, cooldown).
- Auditoria estruturada por `business_events` e `policy_events`.

3) **Policy Engine determinístico**
- Regras ordenadas e previsíveis, com safe mode e kill switch.

4) **Multi‑chip e warmup**
- Operação escalável e resiliente com pool de chips e trust score.


## Riscos e Pontos de Atenção

1) **Complexidade operacional elevada**
- Muitos jobs e rotas; alta superfície de falhas silenciosas.
- Dependência forte de Supabase para estado e métricas.

2) **Guardrails distribuídos**
- Parte das regras está no policy engine, parte no guardrail de outbound.
- Risco de inconsistência: policy pode permitir, guardrail bloqueia (ou vice‑versa).

3) **Dependência de dados corretos no doctor_state**
- Se `doctor_state` estiver stale, decisões ficam erradas (ex: temperature ou permission_state).
- Cache Redis com TTL pode causar decisões baseadas em estado antigo.

4) **Deduplication + Retry**
- Deduplicação antes dos guardrails é correta, mas pode bloquear reenvio legítimo se o conteúdo for idêntico em um curto intervalo.

5) **Multi‑provider (Evolution + Z‑API)**
- Pode haver divergência de payload/semântica entre providers.
- Necessita testes rigorosos para equivalência de comportamento.

6) **Observabilidade**
- Muitos eventos e logs, mas sem painel consolidado mencionado no backend.
- Risco de “data overload” sem priorização clara.

7) **Governança de prompts**
- Regras de persona são críticas e estão dispersas entre docs e prompts; drift pode ocorrer.


## Recomendações

1) **Centralizar visibilidade de decisões**
- Criar painel único unificando: policy_decisions + guardrail outcomes + outbound results.

2) **Definir contratos de consistência**
- Testes automatizados comparando Policy vs Guardrails em cenários-chave.

3) **Monitorar saúde do doctor_state**
- Job periódico para detectar estados inconsistentes ou stale.

4) **Normalizar fluxos multi‑provider**
- Criar camada de normalização única antes do pipeline.

5) **Revisar dedup window**
- Ajustar janela ou incluir contexto (tipo/momento) para evitar bloqueios legítimos.

6) **Roadmap de observabilidade**
- Priorizar dashboards “operacionais” para alertas críticos.
