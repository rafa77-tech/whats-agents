# Sprint 17 - Business Events, Funil e Alertas

**Início:** A definir
**Duração estimada:** 1-2 semanas
**Dependências:** Sprint 16 (Observability) completa

---

## Objetivo

Criar a camada de **eventos de negócio** que permite medir o funil real de conversão: contato → oferta → aceite → plantão realizado.

### Por que agora?

A Sprint 16 entregou observabilidade técnica (policy_events, flags, replay). Mas ainda não sabemos:
- Quantas ofertas viraram aceites?
- Qual hospital tem melhor conversão?
- Quando a operação está degradando?

**Sem isso, melhoramos "a conversa" mas não "vagas fechadas".**

### Benefícios

| Antes | Depois |
|-------|--------|
| Só sabemos decisões de policy | Sabemos conversões de negócio |
| Não há funil medido | Funil completo por hospital/médico |
| Problemas descobertos por reclamação | Alertas proativos |
| Status "fechada" ambíguo | Fluxo claro: reservada → realizada |

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    Business Events Layer                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   Emissores  │    │  business_   │    │   Funil &    │   │
│  │  de Eventos  │───►│   events     │───►│   Métricas   │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│         │                    │                    │          │
│         │                    │                    ▼          │
│  ┌──────┴───────┐           │           ┌──────────────┐   │
│  │ DB Triggers  │           │           │   Alertas    │   │
│  │ (status vaga)│           │           │   (Slack)    │   │
│  └──────────────┘           │           └──────────────┘   │
│                             │                               │
│  ┌──────────────────────────┴────────────────────────────┐  │
│  │                    policy_events                       │  │
│  │              (link via policy_decision_id)             │  │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## Decisões Técnicas

### 1. Detecção de Eventos Semânticos (Híbrido C)

| Evento | Fonte Primária | Fallback |
|--------|----------------|----------|
| `offer_accepted` | DB: `vagas.status` → `reservada` | - |
| `offer_made` | Backend: policy_action=OFFER + vaga_id | - |
| `offer_declined` | Heurística: mensagem de recusa | LLM (futuro) |
| `shift_completed` | DB: `vagas.status` → `realizada` | - |

**Regra de Ouro:** Só conta como `offer_made` se tiver `vaga_id`. Sem vaga_id = `offer_teaser_sent`.

### 2. Migração de Status da Vaga

```
ANTES:                    DEPOIS:
aberta                    aberta
anunciada                 anunciada
reservada                 reservada  ← offer_accepted
fechada (ambíguo)    →    realizada  ← shift_completed (NOVO)
cancelada                 cancelada
```

Migração: `UPDATE vagas SET status = 'reservada' WHERE status = 'fechada'`

### 3. Taxonomia de Eventos

8 eventos de negócio (sem LLM):

| # | Evento | Trigger |
|---|--------|---------|
| 1 | `doctor_inbound` | Mensagem recebida |
| 2 | `doctor_outbound` | Mensagem enviada |
| 3 | `offer_teaser_sent` | Menciona oportunidade (sem vaga_id) |
| 4 | `offer_made` | policy_action=OFFER + vaga_id |
| 5 | `offer_accepted` | `vagas.status` → `reservada` |
| 6 | `offer_declined` | Heurística de recusa |
| 7 | `handoff_created` | `criar_handoff()` |
| 8 | `shift_completed` | `vagas.status` → `realizada` |

---

## Épicos

| # | Épico | Descrição | Estimativa |
|---|-------|-----------|------------|
| E01 | Migração de Status | Adicionar `realizada`, migrar `fechada` | 0.5d |
| E02 | Tabela business_events | Schema + índices + repository | 0.5d |
| E03 | Emissores DB (Triggers) | offer_accepted, shift_completed | 1d |
| E04 | Emissores Backend | offer_made, offer_teaser, handoff | 1d |
| E05 | Detector de Recusa | Heurística para offer_declined | 0.5d |
| E06 | Queries de Funil | 5 métricas + segmentação | 1d |
| E07 | Sistema de Alertas | 3 alertas P0 + Slack | 1d |
| E08 | Canary Rollout | Flag 2% → 10% → 100% | 0.5d |
| E09 | Testes e Validação | Unitários + integração | 1d |

**Total estimado:** 7-8 dias

---

## Fluxo de Dados

### Aceite de Vaga (offer_accepted)

```
1. Julia oferece vaga (offer_made emitido pelo backend)
2. Médico responde "quero esse"
3. Sistema atualiza vagas.status = 'reservada'
4. Trigger DB emite business_event offer_accepted
5. Funil atualizado automaticamente
```

### Plantão Realizado (shift_completed)

```
1. Ops/gestor marca vaga como realizada
2. UPDATE vagas SET status = 'realizada'
3. Trigger DB emite business_event shift_completed
4. Funil fechado para esta vaga
```

---

## Alertas P0 (Críticos)

| Alerta | Trigger | Ação |
|--------|---------|------|
| Spike de handoff | +200% em 24h por hospital | Notifica Slack + pausa campanhas |
| Spike de objeção grave | +100% em 24h | Notifica gestor |
| Queda de conversão | offer_accepted/offer_made < 10% | Revisar ofertas/preços |

---

## Métricas de Funil

### Queries Principais

1. **Taxa de Resposta:** `doctor_inbound / doctor_outbound`
2. **Taxa de Oferta:** `offer_made / doctor_outbound`
3. **Taxa de Conversão:** `offer_accepted / offer_made`
4. **Taxa de Conclusão:** `shift_completed / offer_accepted`
5. **Tempo Médio entre Etapas**

### Segmentação

- Por `hospital_id`
- Por `especialidade`
- Por período (dia/semana/mês)
- Por origem do médico (campanha, inbound, referral)

---

## Checklist Final

### Pré-requisitos
- [ ] Sprint 16 completa e testada
- [ ] Acesso ao Supabase para migrações
- [ ] Slack webhook configurado

### Entregas
- [ ] E01 - Status `realizada` funcionando
- [ ] E02 - Tabela business_events criada
- [ ] E03 - Triggers de DB emitindo eventos
- [ ] E04 - Backend emitindo offer_made
- [ ] E05 - Detector de recusa funcionando
- [ ] E06 - Queries de funil implementadas
- [ ] E07 - Alertas notificando no Slack
- [ ] E08 - Canary em 2%
- [ ] E09 - Testes passando

### Validação
- [ ] offer_accepted registrado quando status → reservada
- [ ] shift_completed registrado quando status → realizada
- [ ] Funil mostra números corretos
- [ ] Alertas disparam em condições de teste
- [ ] policy_decision_id linkado quando aplicável

---

## Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Trigger DB com performance ruim | Baixa | Médio | Trigger leve, só INSERT |
| Falsos positivos em recusa | Média | Baixo | Começar conservador |
| Alertas demais (fadiga) | Média | Médio | Threshold alto inicial |
| Migração quebra código existente | Baixa | Alto | Testar em branch primeiro |

---

## Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Eventos capturados | > 95% das ações |
| Funil calculado corretamente | 100% |
| Alertas funcionando | 100% |
| Latência do trigger | < 100ms |
| Cobertura de testes | > 80% |
