# Sprint 18 - Auditoria e Integridade

**Status:** ENCERRADA
**Inicio:** 2025-12-29
**Fim:** 2025-12-31
**Duracao:** 3 dias
**Dependencias:** Sprint 17 (Business Events Layer) completa

> **Nota:** Sprint re-escopada durante execucao com base em auditoria de seguranca.
> Escopo original (E10-E13) movido para sprints futuras.
> Foco redirecionado para fundamentos de integridade operacional.

---

## Objetivo

Transformar o funil de "bonito no paper" para **confiavel em producao**, com medidas que voce pode apostar dinheiro em cima.

### Por que agora?

A Sprint 17 entregou a camada de eventos de negocio (business_events) e alertas. Mas ainda falta:
- **Provar** com numeros que os eventos cobrem o que deveriam cobrir
- **Encontrar** buracos (silencios e efeitos que nao viram evento)
- **Criar** metricas-pilar que governam decisoes
- **Colocar guardrails** de outbound alinhados com opted_out / cooling_off / pressao

**Sem isso, temos eventos mas nao temos confianca nos dados.**

### Beneficios

| Antes | Depois |
|-------|--------|
| Eventos sem validacao de cobertura | Auditoria diaria de integridade |
| Divergencias silenciosas | Alertas automaticos de anomalias |
| Metricas cruas (contagens) | 3 KPIs que governam operacao |
| Campanhas podem violar opt-out | Guardrails impossiveis de burlar |

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Data Integrity Layer                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────┐    ┌──────────────────────┐                       │
│  │  E10: Event Coverage │    │  E11: Reconciliacao  │                       │
│  │  (Auditoria diaria)  │───►│   DB vs Eventos      │                       │
│  └──────────────────────┘    └──────────────────────┘                       │
│           │                            │                                     │
│           ▼                            ▼                                     │
│  ┌──────────────────────────────────────────────────┐                       │
│  │             data_anomalies (historico)           │                       │
│  └──────────────────────────────────────────────────┘                       │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                         KPIs Layer                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     E12: 3 KPIs Operacionais                         │   │
│  │                                                                      │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐   │   │
│  │  │ Conversion  │  │ Time-to-    │  │ Health Score                │   │   │
│  │  │ Rate        │  │ Fill        │  │ (pressao/churn)             │   │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                       Guardrails Layer                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                   E13: Guardrails de Campanha                        │   │
│  │                                                                      │   │
│  │  permission_state ∈ {opted_out, cooling_off} → BLOQUEIA              │   │
│  │  next_allowed_at > now() → BLOQUEIA                                  │   │
│  │  contact_count_7d > TETO → BLOQUEIA                                  │   │
│  │                                                                      │   │
│  │  Todos emitem: business_event "campaign_blocked"                     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Decisoes Tecnicas

### 1. Auditoria de Cobertura de Eventos

Perguntas que precisamos responder diariamente:
- Toda mensagem inbound gera `doctor_inbound`?
- Toda mensagem outbound gera `doctor_outbound`?
- Toda mudanca de status gera evento correspondente?
- Existe `offer_accepted` sem `offer_made` previo? (bug de instrumentacao)
- Existe `offer_made` sem `vaga_id`? (bug ou prompt drift)

### 2. Reconciliacao DB vs Eventos

Daily job que compara:
- `vagas.status` nas ultimas 24h
- `business_events` do mesmo periodo

Divergencias geram:
- Alerta Slack (para o time)
- Registro em `data_anomalies` (para historico)

### 3. Tres KPIs Operacionais

| KPI | Formula | Segmentacao |
|-----|---------|-------------|
| **Conversion Rate** | `offer_accepted / offer_made` | hospital, origem, risco |
| **Time-to-Fill** | `vaga anunciada → reservada → realizada` | hospital, especialidade |
| **Health Score** | `f(contact_count_7d, opted_out_rate, cooling_off_rate)` | global, por cohort |

### 4. Guardrails de Campanha

**Regra:** E impossivel o sistema violar opt-out, mesmo com bug.

| Condicao | Acao |
|----------|------|
| `permission_state = opted_out` | BLOQUEIA outbound |
| `permission_state = cooling_off` | BLOQUEIA outbound |
| `next_allowed_at > now()` | BLOQUEIA outbound |
| `contact_count_7d > TETO` | BLOQUEIA outbound |

Todos emitem `business_event campaign_blocked` para visibilidade.

---

## Epicos

| # | Epico | Descricao | Estimativa |
|---|-------|-----------|------------|
| E10 | Auditoria de Integridade | Queries de cobertura + painel | 1d |
| E11 | Reconciliacao DB vs Eventos | Daily job + data_anomalies | 1d |
| E12 | Metricas que Importam | 3 KPIs + endpoints + dashboard | 1.5d |
| E13 | Guardrails de Campanha | Bloqueios + campaign_blocked event | 1d |

**Total estimado:** 4-5 dias

---

## Metricas de Sucesso

| Metrica | Meta | Como Medir |
|---------|------|------------|
| Event Coverage | > 98% | Auditoria diaria E10 |
| Divergencias detectadas | 100% | Reconciliacao E11 |
| KPIs calculados | 100% | Endpoints E12 funcionando |
| Guardrails funcionando | 100% | Zero outbound para opted_out |
| Alertas de anomalia | < 24h delay | Job diario E11 |

---

## Riscos e Mitigacoes

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|---------------|---------|-----------|
| Queries de auditoria pesadas | Media | Medio | Indices otimizados, rodar off-peak |
| Falsos positivos em reconciliacao | Media | Baixo | Threshold de tolerancia |
| KPIs complexos demais | Baixa | Medio | Comecar simples, iterar |
| Guardrail bloqueia indevidamente | Baixa | Alto | Logs detalhados, bypass de emergencia |

---

## Checklist Final

### Pre-requisitos
- [ ] Sprint 17 completa (business_events funcionando)
- [ ] Acesso ao Supabase para novas tabelas
- [ ] Slack webhook configurado

### Entregas
- [ ] E10 - Queries de cobertura funcionando
- [ ] E10 - Painel de auditoria disponivel
- [ ] E11 - Job diario de reconciliacao
- [ ] E11 - Tabela data_anomalies criada
- [ ] E12 - 3 KPIs implementados
- [ ] E12 - Endpoints de dashboard
- [ ] E13 - Guardrails bloqueando corretamente
- [ ] E13 - Evento campaign_blocked emitido

### Validacao
- [ ] Auditoria detecta buracos conhecidos
- [ ] Reconciliacao encontra divergencias de teste
- [ ] KPIs mostram valores coerentes
- [ ] Guardrail bloqueia opted_out em campanha
- [ ] Evento campaign_blocked registrado

---

## RESULTADO FINAL (Re-escopo)

### Contexto da Mudanca

Durante a Sprint 18, uma auditoria de seguranca identificou riscos criticos no pipeline de outbound.
O escopo foi redirecionado para enderacar esses riscos antes de prosseguir com features.

**Documento de auditoria:** `planning/sprint-18/relatorio-auditoria-outbound-v2.md`

### Entregas Reais

| Entrega | Status | Evidencia |
|---------|--------|-----------|
| Versionamento operacional (GIT_SHA, BUILD_TIME) | DONE | `/health/deep` |
| Schema version tracking | DONE | `app_settings` |
| Schema fingerprint | DONE | Fallback mode funcionando |
| DEV guardrails (OUTBOUND_ALLOWLIST) | DONE | Fail-closed implementado |
| Marcadores de ambiente | DONE | Validacao cruzada APP_ENV vs DB |
| Deteccao de environment mismatch | DONE | Status CRITICAL no /health/deep |
| ENV-CONTRACT.md | DONE | `docs/operacao/` |
| TEST-PLAYBOOK.md | DONE | `docs/operacao/` |

### Itens Diferidos

| Item | Motivo | Destino |
|------|--------|---------|
| E10 - Auditoria de cobertura | Re-escopo | Sprint futura |
| E11 - Reconciliacao DB vs Eventos | Re-escopo | Sprint futura |
| E12 - 3 KPIs operacionais | Re-escopo | Sprint futura |
| E13 - Guardrails de campanha | Parcialmente feito | Sprint futura |
| Evolution DEV separado | Requer numero virtual | Sprint 25 |

### Evidencias de Encerramento

```
docs/auditorias/sprint-18/
├── SPRINT-18-CLOSE.md                    # Declaracao formal
└── health-snapshots/
    ├── prod-health-deep-2025-12-31.json
    ├── dev-health-deep-2025-12-31.json
    ├── guardrail-test-output-2025-12-31.txt
    └── version-comparison-2025-12-31.md
```

### Metricas Finais

| Metrica | Resultado |
|---------|-----------|
| DEV /health/deep | `status: healthy`, `deploy_safe: true` |
| PROD /health/deep | `status: healthy`, `deploy_safe: true` |
| Testes guardrail | 4/4 passaram |
| Prompts sincronizados | DEV = PROD (v2) |

---

**Sprint 18 encerrada em 2025-12-31.**
