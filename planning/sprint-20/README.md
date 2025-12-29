# Sprint 20: Ponte Automatica Medico-Divulgador (Marketplace Assistido)

**Status:** Em Planejamento
**Inicio:** A definir
**Duracao estimada:** 3-4 dias
**Dependencias:** Sprint 17 (Business Events), Sprint 19 (Valor Flexivel)

---

## Objetivo

Implementar **ponte automatica e auditavel** entre medico e divulgador externo quando um medico aceita uma vaga, transformando a Julia em **facilitadora de marketplace** (nao decisora).

### Por que agora?

O pipeline de scraping (Sprint 14) e oferta de vagas funciona, mas:
- Quando medico aceita, **nada acontece** alem de reservar internamente
- O divulgador da vaga **nao e notificado**
- Nao ha **follow-up** para saber se o plantao foi fechado
- Vagas ficam "reservadas" indefinidamente (vaga sequestrada)

**Sem isso, temos leads sem conversao real.**

### Premissas Fundamentais

| # | Premissa | Implicacao |
|---|----------|------------|
| 1 | **Dono da vaga = divulgador** | Somente ele confirma fechamento |
| 2 | **Canal = WhatsApp (mesmo numero Julia)** | Sem UI externa complexa |
| 3 | **Produto = marketplace assistido** | Julia intermedia, nao fecha |

---

## Arquitetura

```
                    PONTE AUTOMATICA

┌──────────────────────────────────────────────────────────────────┐
│                                                                   │
│   [Medico aceita]                                                │
│         │                                                         │
│         ▼                                                         │
│   ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐    │
│   │  reservar_  │───►│  external_   │───►│  Mensagens:     │    │
│   │  plantao    │    │  handoffs    │    │  - p/ medico    │    │
│   └─────────────┘    └──────────────┘    │  - p/ divulgador│    │
│                             │            └─────────────────┘    │
│                             │                    │               │
│                             ▼                    ▼               │
│                      ┌──────────────┐    ┌─────────────────┐    │
│                      │ Link Externo │    │ Keywords        │    │
│                      │ (JWT Token)  │    │ (Fallback)      │    │
│                      └──────────────┘    └─────────────────┘    │
│                             │                    │               │
│                             └────────┬───────────┘               │
│                                      ▼                           │
│                             ┌──────────────┐                     │
│                             │ Confirmacao  │                     │
│                             │ ou Expiracao │                     │
│                             └──────────────┘                     │
│                                      │                           │
│                                      ▼                           │
│                             ┌──────────────┐                     │
│                             │ business_    │                     │
│                             │ events       │                     │
│                             └──────────────┘                     │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Decisoes Tecnicas

### 1. Estrategia de Confirmacao

**Link externo com acao deterministica** (principal) + **Keywords como fallback** (devido ao Baileys nao suportar botoes).

| Metodo | Prioridade | Confiabilidade |
|--------|------------|----------------|
| Link JWT | Principal | Alta |
| Keywords | Fallback | Media |

### 2. Token JWT para Links

```python
# Payload do token
{
    "handoff_id": "uuid",
    "action": "confirmed" | "not_confirmed",
    "exp": timestamp_48h,
    "jti": "nonce_unico"  # single-use
}
```

**Caracteristicas:**
- Assinado com secret do backend
- Expira em 48h
- Single-use (nonce gravado em used_tokens)
- Idempotente (mesmo resultado se clicar 2x apos uso)

### 3. Maquina de Estados do Handoff

```
PENDING
  ├─ (link/keyword confirmado) ──► CONFIRMED ──► vaga.status = fechada
  ├─ (link/keyword nao fechou) ──► NOT_CONFIRMED ──► vaga.status = aberta
  └─ (48h sem resposta) ─────────► EXPIRED ──► vaga.status = aberta
```

**Source of truth:** Divulgador (unico que pode confirmar)

### 4. Mensagens de Ponte

**Para o medico:**
```
Perfeito! Reservei essa vaga pra voce.
Para confirmar na escala, fala direto com {NOME} ({EMPRESA}): {TELEFONE}
Me avisa aqui quando fechar!
```

**Para o divulgador:**
```
Oi {NOME}, tudo bem?
Tenho um medico interessado na vaga de {DATA} - {PERIODO} - {HOSPITAL}.
Contato: Dr(a). {NOME_MEDICO} - {TELEFONE_MEDICO}

Para eu registrar corretamente:
- Confirmar: {LINK_CONFIRMAR}
- Nao fechou: {LINK_NAO_FECHOU}

Ou responda CONFIRMADO / NAO FECHOU aqui.
```

### 5. Follow-up Automatico

| Tempo | Acao |
|-------|------|
| +2h | Lembrete para divulgador |
| +24h | Segundo follow-up + alerta Slack |
| +48h | Expira handoff, libera vaga |

---

## Modelo de Dados

### Nova Tabela: `external_handoffs`

```sql
CREATE TABLE external_handoffs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Relacionamentos
    vaga_id UUID NOT NULL REFERENCES vagas(id),
    cliente_id UUID NOT NULL REFERENCES clientes(id),

    -- Divulgador (snapshot no momento da ponte)
    divulgador_nome TEXT,
    divulgador_telefone TEXT NOT NULL,
    divulgador_empresa TEXT,

    -- Estado
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'contacted', 'confirmed', 'not_confirmed', 'expired')),

    -- Controle de tempo
    reserved_until TIMESTAMPTZ NOT NULL,
    last_followup_at TIMESTAMPTZ,
    followup_count INT DEFAULT 0,

    -- Auditoria
    confirmed_at TIMESTAMPTZ,
    confirmed_by TEXT,  -- 'link' ou 'keyword'
    expired_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    -- Previne duplicatas
    UNIQUE (vaga_id, cliente_id)
);

-- Indices
CREATE INDEX idx_eh_status ON external_handoffs(status);
CREATE INDEX idx_eh_reserved_until ON external_handoffs(reserved_until);
CREATE INDEX idx_eh_divulgador_tel ON external_handoffs(divulgador_telefone);
```

### Alteracao em `vagas`

```sql
ALTER TABLE vagas ADD COLUMN source TEXT;  -- 'grupo', 'manual', 'api'
ALTER TABLE vagas ADD COLUMN source_id UUID;  -- referencia a vagas_grupo

-- Novo status
ALTER TABLE vagas DROP CONSTRAINT IF EXISTS vagas_status_check;
ALTER TABLE vagas ADD CONSTRAINT vagas_status_check
    CHECK (status IN ('aberta', 'anunciada', 'reservada', 'aguardando_confirmacao', 'fechada', 'realizada', 'cancelada'));
```

### Tabela de Tokens Usados

```sql
CREATE TABLE handoff_used_tokens (
    jti TEXT PRIMARY KEY,
    handoff_id UUID NOT NULL REFERENCES external_handoffs(id),
    used_at TIMESTAMPTZ DEFAULT now()
);
```

---

## Eventos de Negocio (Novos)

| Evento | Trigger | Dados |
|--------|---------|-------|
| `HANDOFF_CREATED` | Ponte criada | vaga_id, cliente_id, divulgador_tel |
| `HANDOFF_CONTACTED` | Msg enviada ao divulgador | handoff_id, channel |
| `HANDOFF_CONFIRM_CLICKED` | Link clicado | handoff_id, action, token_jti |
| `HANDOFF_CONFIRMED` | Plantao confirmado | handoff_id, confirmed_by |
| `HANDOFF_NOT_CONFIRMED` | Plantao nao fechou | handoff_id, reason |
| `HANDOFF_EXPIRED` | 48h sem resposta | handoff_id, followup_count |
| `HANDOFF_FOLLOWUP_SENT` | Follow-up enviado | handoff_id, attempt |

---

## Epicos

| # | Epico | Descricao | Arquivos | Estimativa |
|---|-------|-----------|----------|------------|
| E01 | [Migrations](./epic-01-migrations.md) | external_handoffs + source em vagas + tokens | 3 migrations | 2h |
| E02 | [Eventos e Tokens](./epic-02-eventos-tokens.md) | EventTypes + geracao/validacao JWT | 3 arquivos | 3h |
| E03 | [Service de Ponte](./epic-03-service-ponte.md) | criar_ponte_externa + envio mensagens | 4 arquivos | 4h |
| E04 | [Integracao Tool](./epic-04-integracao-tool.md) | Modificar reservar_plantao | 2 arquivos | 2h |
| E05 | [Endpoint Confirmacao](./epic-05-endpoint-confirmacao.md) | GET /handoff/confirm + pagina resposta | 3 arquivos | 3h |
| E06 | [Detector Keywords](./epic-06-detector-keywords.md) | Fallback no webhook | 2 arquivos | 2h |
| E07 | [Job Follow-up](./epic-07-job-followup.md) | Processamento + expiracao | 2 arquivos | 3h |
| E08 | [Testes e Docs](./epic-08-testes-docs.md) | Cobertura + documentacao | 6+ arquivos | 4h |

**Total estimado:** ~23h (~3 dias)

---

## Dependencias entre Epicos

```
E01 (Migrations)
    └─► E02 (Eventos + Tokens)
            └─► E03 (Service de Ponte)
                    ├─► E04 (Integracao Tool)
                    ├─► E05 (Endpoint)
                    └─► E06 (Keywords)
                            └─► E07 (Job Follow-up)
                                    └─► E08 (Testes)
```

---

## Fluxo End-to-End

### 1. Medico Aceita Vaga

```
1. Tool reservar_plantao() chamada
2. Vaga.status = 'reservada'
3. Busca divulgador via vagas_grupo.mensagem_id.contato_id
4. Cria external_handoff (status=pending, reserved_until=now+48h)
5. Emite HANDOFF_CREATED
6. Envia msg para medico (contato do divulgador)
7. Envia msg para divulgador (contato do medico + links)
8. Emite HANDOFF_CONTACTED
9. Notifica Slack
```

### 2. Divulgador Confirma (Link)

```
1. Divulgador clica link: /handoff/confirm?t=JWT
2. Backend valida JWT (assinatura, expiracao, jti)
3. Verifica handoff ainda pendente
4. Grava jti em used_tokens
5. Atualiza handoff.status = 'confirmed'
6. Atualiza vaga.status = 'fechada'
7. Emite HANDOFF_CONFIRMED
8. Retorna pagina: "Registrado com sucesso!"
9. Notifica Slack
```

### 3. Divulgador Confirma (Keyword)

```
1. Webhook recebe msg do divulgador
2. Detecta telefone tem handoff pendente
3. Detecta keyword (CONFIRMADO/NAO FECHOU)
4. Atualiza handoff/vaga
5. Emite evento
6. Julia responde: "Anotado! Obrigada pela confirmacao."
```

### 4. Expiracao

```
1. Job roda a cada 10 min
2. Busca handoffs com reserved_until < now()
3. Para cada expirado:
   - handoff.status = 'expired'
   - vaga.status = 'aberta'
   - Emite HANDOFF_EXPIRED
   - Notifica Slack
   - Envia msg para medico: "A vaga nao avancou..."
```

---

## Guardrails

| Guardrail | Aplicacao |
|-----------|-----------|
| Opt-out | Verificar antes de enviar ao divulgador |
| Rate limit | Respeitar limite global |
| Horario comercial | 8h-20h seg-sex |
| Dedupe | Unique constraint + idempotencia |

---

## Invariantes

| # | Invariante | Validacao |
|---|------------|-----------|
| EH1 | Uma vaga so tem 1 handoff ativo | UNIQUE (vaga_id, cliente_id) |
| EH2 | Toda reserva externa tem reserved_until | NOT NULL constraint |
| EH3 | Expiracao libera a vaga | Job + trigger |
| EH4 | Toda acao emite evento | Codigo |
| EH5 | Ponte nunca bypassa guardrails | Usar send_outbound_message |
| EH6 | Token e single-use | Tabela handoff_used_tokens |

---

## Rollout

| Fase | Criterio | Acao |
|------|----------|------|
| Canary | Apenas source='grupo' e score>=95% | Ativar para vagas de alta confianca |
| 24h estavel | Sem erros, taxa confirmacao > 0 | Expandir para todas vagas de grupo |
| Opt-out | Feature flag handoff.enabled | Permitir desativar |

---

## Metricas de Sucesso

| Metrica | Meta |
|---------|------|
| Taxa de confirmacao | > 30% dos handoffs |
| Taxa de expiracao | < 50% |
| Tempo medio ate confirmacao | < 24h |
| Eventos auditaveis | 100% das acoes |
| Zero vagas sequestradas | 100% (expiracao funciona) |

---

## Riscos e Mitigacoes

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|---------------|---------|-----------|
| Divulgador nao tem telefone valido | Media | Medio | Fallback: notificar gestor |
| Link nao funciona (firewall) | Baixa | Medio | Keywords como fallback |
| Spam ao divulgador | Baixa | Alto | Max 3 followups, respeitar opt-out |
| Race condition (2 medicos) | Baixa | Medio | Unique constraint no handoff |

---

## Checklist Pre-Deploy

### Migrations
- [ ] external_handoffs criada
- [ ] source/source_id em vagas
- [ ] handoff_used_tokens criada
- [ ] Novo status 'aguardando_confirmacao'

### Codigo
- [ ] EventTypes novos em types.py
- [ ] Service criar_ponte_externa
- [ ] Endpoint /handoff/confirm
- [ ] Detector de keywords
- [ ] Job de follow-up/expiracao
- [ ] Integracao com reservar_plantao

### Testes
- [ ] Unitarios para service
- [ ] Unitarios para token
- [ ] Integracao end-to-end
- [ ] Teste de expiracao

### Observabilidade
- [ ] Eventos sendo emitidos
- [ ] Slack notificando
- [ ] Logs estruturados

---

## Queries de Validacao

```sql
-- Taxa de confirmacao (ultimos 7 dias)
SELECT
    COUNT(*) FILTER (WHERE status = 'confirmed') as confirmados,
    COUNT(*) FILTER (WHERE status = 'not_confirmed') as nao_fechou,
    COUNT(*) FILTER (WHERE status = 'expired') as expirados,
    COUNT(*) as total,
    ROUND(COUNT(*) FILTER (WHERE status = 'confirmed') * 100.0 / NULLIF(COUNT(*), 0), 2) as taxa_confirmacao
FROM external_handoffs
WHERE created_at >= now() - interval '7 days';

-- Handoffs pendentes (para monitoramento)
SELECT COUNT(*) as pendentes,
       MIN(reserved_until) as mais_antigo
FROM external_handoffs
WHERE status = 'pending';

-- Tempo medio ate confirmacao
SELECT AVG(EXTRACT(EPOCH FROM (confirmed_at - created_at)) / 3600) as horas_media
FROM external_handoffs
WHERE status = 'confirmed'
AND created_at >= now() - interval '30 days';
```

---

*Sprint criada em 29/12/2025*
