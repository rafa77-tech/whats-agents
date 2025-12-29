# Sprint 22: Responsividade Inteligente

**Status:** Planejamento
**Inicio:** A definir
**Duracao estimada:** 4-5 dias
**Dependencias:** Sprint 18 (Guardrails), Sprint 20 (Handoff Externo)

---

## Objetivo

Transformar a Julia de um **sistema batch com delay artificial** em uma **assistente genuinamente responsiva**, ajustando timing e prioridades para maximizar encantamento, confianca e taxa de fechamento.

### Problema Central

Hoje a Julia funciona tecnicamente bem, mas:

| Sintoma | Percepcao do Medico |
|---------|---------------------|
| Delay 5-30s para tudo | "Ela responde quando da" |
| Fora do horario = silencio | "Nao sei se estou sendo atendido" |
| Jobs concorrendo o dia todo | Julia parece "ocupada, nunca focada" |
| Sem visibilidade de estado | Gestor nao sabe o que ela esta fazendo |

**Resultado:** Alta eficiencia tecnica, baixo encantamento humano.

### Por que agora?

- Sistema estavel (18 sprints de robustez)
- Guardrails consolidados (Sprint 18)
- Handoff externo funcionando (Sprint 20)
- **Gargalo atual nao e tecnico, e de experiencia**

---

## Principios

| # | Principio | Aplicacao |
|---|-----------|-----------|
| 1 | **Resposta > Acao** | Fora do horario: reconhecer, nao executar |
| 2 | **Contexto define delay** | Reply direta = 0-3s, Campanha fria = 60-180s |
| 3 | **Atendimento e prioridade maxima** | Nunca compete com jobs batch |
| 4 | **Menos ruido, mesma entrega** | Consolidar jobs, criar janelas |
| 5 | **Visibilidade gera confianca** | Gestor sabe o que Julia esta fazendo |

---

## Arquitetura

```
                    MODOS OPERACIONAIS

┌────────────────────────────────────────────────────────────────────┐
│                                                                     │
│   ┌─────────────────┐                                              │
│   │  Mensagem       │                                              │
│   │  Recebida       │                                              │
│   └────────┬────────┘                                              │
│            │                                                        │
│            ▼                                                        │
│   ┌─────────────────┐                                              │
│   │  Classificador  │                                              │
│   │  de Contexto    │                                              │
│   └────────┬────────┘                                              │
│            │                                                        │
│   ┌────────┼────────┬────────────────┐                             │
│   │        │        │                │                              │
│   ▼        ▼        ▼                ▼                              │
│ ┌────┐  ┌────┐  ┌────────┐    ┌──────────┐                         │
│ │REPLY│  │ACEITE│ │OFERTA  │    │CAMPANHA  │                        │
│ │0-3s │  │0-2s │ │15-45s  │    │60-180s   │                        │
│ └──┬──┘  └──┬──┘ └───┬────┘    └────┬─────┘                        │
│    │        │        │              │                               │
│    └────────┴────────┴──────────────┘                               │
│                      │                                              │
│                      ▼                                              │
│            ┌─────────────────┐                                      │
│            │  Delay Engine   │                                      │
│            │  (por contexto) │                                      │
│            └────────┬────────┘                                      │
│                     │                                               │
│                     ▼                                               │
│            ┌─────────────────┐                                      │
│            │  Envio Final    │                                      │
│            └─────────────────┘                                      │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘


                    JANELAS DE EXECUCAO

┌────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  06h    08h    10h    12h    14h    16h    18h    20h    22h       │
│   │      │      │      │      │      │      │      │      │        │
│   │      │      │      │      │      │      │      │      │        │
│   ▼      ▼      ▼      ▼      ▼      ▼      ▼      ▼      ▼        │
│  ┌──┐   ┌──────────────────────────────────────────┐   ┌──┐        │
│  │B │   │           HORARIO COMERCIAL              │   │B │        │
│  │A │   │      Atendimento + Comercial             │   │A │        │
│  │T │   └──────────────────────────────────────────┘   │T │        │
│  │C │         ▲      ▲             ▲      ▲            │C │        │
│  │H │         │      │             │      │            │H │        │
│  └──┘       10:00  14:00         16:00  17:00          └──┘        │
│              │      │             │      │                          │
│            Follow  Campa-       Follow  Campa-                      │
│            ups     nhas         ups     nhas                        │
│                                                                     │
│  ATENDIMENTO: 24/7 (responde, nao age fora do horario)             │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

---

## Decisoes Tecnicas

### 1. Classificacao de Contexto

Toda mensagem recebida e classificada em um dos tipos:

| Tipo | Criterios | Delay |
|------|-----------|-------|
| `reply_direta` | Resposta a pergunta da Julia | 0-3s |
| `aceite_vaga` | Palavras: "ok", "quero", "reserva", "fechado" | 0-2s |
| `confirmacao` | Resposta a confirmacao operacional | 2-5s |
| `oferta_ativa` | Julia esta oferecendo vaga | 15-45s |
| `followup` | Retomando conversa inativa | 30-120s |
| `campanha_fria` | Primeiro contato de campanha | 60-180s |

### 2. Delay Engine

```python
@dataclass
class DelayConfig:
    tipo: str
    min_delay_ms: int
    max_delay_ms: int
    fora_horario_permitido: bool
    prioridade: int  # 1 = maxima

DELAY_CONFIGS = {
    "reply_direta": DelayConfig("reply_direta", 0, 3000, True, 1),
    "aceite_vaga": DelayConfig("aceite_vaga", 0, 2000, True, 1),
    "confirmacao": DelayConfig("confirmacao", 2000, 5000, True, 2),
    "oferta_ativa": DelayConfig("oferta_ativa", 15000, 45000, False, 3),
    "followup": DelayConfig("followup", 30000, 120000, False, 4),
    "campanha_fria": DelayConfig("campanha_fria", 60000, 180000, False, 5),
}
```

### 3. Modo Fora do Horario

**Comportamento atual:** Silencio total, tudo enfileira.

**Novo comportamento:**

```
Medico 21h: "Tem vaga amanha?"

Julia (imediato, 0-3s):
"Oi Dr! Recebi sua mensagem.
Vou verificar as vagas e te retorno assim que
o horario operacional abrir, tudo bem?
Qualquer urgencia, me avisa!"

[Acao de buscar vaga fica pendente para 08h]
```

**Regras:**
- Reconhece a mensagem (delay 0-3s)
- NAO executa tools de acao (buscar_vagas, reservar)
- Armazena contexto para retomar as 08h
- Excecoes: handoff urgente, confirmacao de plantao

### 4. Racionalizacao de Jobs

| Job | Frequencia Atual | Frequencia Nova | Justificativa |
|-----|------------------|-----------------|---------------|
| processar_mensagens_agendadas | 1 min | 1 min | Critico, manter |
| processar_campanhas_agendadas | 1 min | Janelas | Nao precisa ser continuo |
| processar_grupos | 5 min | 15 min | Grupos sao lentos mesmo |
| verificar_whatsapp | 1 min | 5 min | Status nao muda rapido |
| verificar_alertas | 15 min | 30 min | Alertas nao sao urgentes |
| verificar_alertas_grupos | 15 min | 30 min | Idem |
| processar_followups | 10h | 10h, 16h | 2x/dia suficiente |
| processar_handoffs | 10 min | 15 min | Pode ser menos frequente |

**Janelas de Campanhas:**
- 10:00 - Manha (abertura)
- 14:00 - Pos-almoco
- 17:00 - Fim de tarde

### 5. Painel de Estado no Slack

Mensagem automatica a cada 5 minutos (se houver atividade):

```
📊 Julia Status

Estado: 🟢 Atendimento
Conversas ativas: 5
Replies pendentes: 2
Handoffs abertos: 1

Ultimas acoes:
• 14:32 - Reply para Dr. Carlos (aceite)
• 14:28 - Oferta enviada para Dr. Maria
• 14:15 - Follow-up Dr. Paulo

Proxima acao agendada:
• 14:45 - Campanha Reativacao (12 medicos)
```

---

## Modelo de Dados

### Nova Tabela: `julia_estado`

```sql
CREATE TABLE julia_estado (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Estado atual
    modo TEXT NOT NULL DEFAULT 'atendimento'
        CHECK (modo IN ('atendimento', 'comercial', 'batch', 'pausada')),

    -- Metricas em tempo real
    conversas_ativas INT DEFAULT 0,
    replies_pendentes INT DEFAULT 0,
    handoffs_abertos INT DEFAULT 0,

    -- Ultima atividade
    ultima_acao TEXT,
    ultima_acao_at TIMESTAMPTZ,

    -- Proxima acao agendada
    proxima_acao TEXT,
    proxima_acao_at TIMESTAMPTZ,

    -- Controle
    atualizado_em TIMESTAMPTZ DEFAULT now(),

    -- Singleton (apenas 1 registro)
    CONSTRAINT julia_estado_singleton CHECK (id = '00000000-0000-0000-0000-000000000001'::uuid)
);

-- Inserir registro inicial
INSERT INTO julia_estado (id, modo)
VALUES ('00000000-0000-0000-0000-000000000001', 'atendimento')
ON CONFLICT DO NOTHING;
```

### Nova Tabela: `mensagens_fora_horario`

```sql
CREATE TABLE mensagens_fora_horario (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Referencia
    cliente_id UUID NOT NULL REFERENCES clientes(id),
    conversa_id UUID REFERENCES conversations(id),

    -- Mensagem original
    mensagem TEXT NOT NULL,
    recebida_em TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Processamento
    ack_enviado BOOLEAN DEFAULT FALSE,
    ack_enviado_em TIMESTAMPTZ,
    processada BOOLEAN DEFAULT FALSE,
    processada_em TIMESTAMPTZ,

    -- Contexto para retomada
    contexto JSONB,

    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_mfh_pendentes ON mensagens_fora_horario(processada, recebida_em)
WHERE processada = FALSE;
```

### Alteracao em `fila_mensagens`

```sql
-- Adicionar campo de tipo de contexto
ALTER TABLE fila_mensagens ADD COLUMN IF NOT EXISTS tipo_contexto TEXT
    DEFAULT 'campanha_fria'
    CHECK (tipo_contexto IN (
        'reply_direta',
        'aceite_vaga',
        'confirmacao',
        'oferta_ativa',
        'followup',
        'campanha_fria'
    ));

-- Adicionar prioridade explicita
ALTER TABLE fila_mensagens ADD COLUMN IF NOT EXISTS prioridade INT DEFAULT 5;
```

---

## Epicos

| # | Epico | Descricao | Arquivos | Estimativa |
|---|-------|-----------|----------|------------|
| E01 | [Migrations](./epic-01-migrations.md) | julia_estado + mensagens_fora_horario + alteracoes | 3 migrations | 2h |
| E02 | [Classificador de Contexto](./epic-02-classificador.md) | Detectar tipo de mensagem para delay | 2 arquivos | 3h |
| E03 | [Delay Engine](./epic-03-delay-engine.md) | Motor de delay por contexto | 3 arquivos | 4h |
| E04 | [Modo Fora do Horario](./epic-04-fora-horario.md) | Ack imediato + processamento diferido | 4 arquivos | 5h |
| E05 | [Racionalizacao de Jobs](./epic-05-jobs.md) | Ajustar frequencias e janelas | 2 arquivos | 2h |
| E06 | [Estado da Julia](./epic-06-estado.md) | Singleton + atualizacao em tempo real | 3 arquivos | 3h |
| E07 | [Painel Slack](./epic-07-painel-slack.md) | Mensagem de status periodica | 2 arquivos | 3h |
| E08 | [Testes e Docs](./epic-08-testes-docs.md) | Cobertura + documentacao | 6+ arquivos | 4h |

**Total estimado:** ~26h (~4 dias)

---

## Dependencias entre Epicos

```
E01 (Migrations)
    └─► E02 (Classificador)
            └─► E03 (Delay Engine)
                    └─► E04 (Fora Horario)
    └─► E05 (Jobs) ─────────────────────┐
    └─► E06 (Estado) ───────────────────┤
                                        ▼
                                E07 (Painel Slack)
                                        │
                                        ▼
                                E08 (Testes)
```

**Paralelizaveis:** E05, E06 podem rodar em paralelo apos E01.

---

## Fluxo End-to-End

### 1. Mensagem Durante Horario Comercial

```
1. Webhook recebe mensagem
2. Classificador detecta tipo: "aceite_vaga"
3. Delay Engine calcula: 0-2s
4. Aguarda delay
5. Agente processa e responde
6. Atualiza julia_estado
7. Log estruturado
```

### 2. Mensagem Fora do Horario

```
1. Webhook recebe mensagem (21:30)
2. Detecta: fora do horario comercial
3. Classifica: "reply_direta"
4. Verifica: fora_horario_permitido = True para ack
5. Envia ack imediato (0-3s):
   "Oi Dr! Recebi sua mensagem..."
6. Salva em mensagens_fora_horario com contexto
7. Proximo dia 08:00:
   - Job processa mensagens_fora_horario
   - Retoma conversa com contexto
   - "Bom dia Dr! Sobre sua mensagem de ontem..."
```

### 3. Campanha Fria

```
1. Job processar_campanhas_agendadas (janela 10:00)
2. Para cada envio pendente:
   - Classifica: "campanha_fria"
   - Delay Engine: 60-180s
   - Respeita rate limit
3. Atualiza julia_estado.proxima_acao
4. Apos janela: pausa ate proxima janela (14:00)
```

### 4. Painel Slack

```
1. Job a cada 5 minutos
2. Busca julia_estado
3. Busca metricas:
   - COUNT(*) FROM conversations WHERE status='ativa' AND updated_at > now() - '1h'
   - COUNT(*) FROM fila_mensagens WHERE status='pendente'
   - COUNT(*) FROM external_handoffs WHERE status='pending'
4. Formata mensagem
5. Envia para canal #julia-status
6. Atualiza ultima_notificacao
```

---

## Invariantes

| # | Invariante | Validacao |
|---|------------|-----------|
| R1 | Reply direta sempre < 5s | Monitorar p99 latencia |
| R2 | Aceite de vaga sempre < 3s | Metrica de aceite |
| R3 | Ack fora do horario sempre enviado | Log + metrica |
| R4 | Mensagem fora horario nunca perdida | Tabela + processamento |
| R5 | Jobs batch nao competem com atendimento | Prioridade explicita |
| R6 | Estado da Julia sempre atualizado | Singleton + trigger |
| R7 | Painel Slack reflete realidade | Queries em tempo real |

---

## Metricas de Sucesso

| Metrica | Baseline | Meta | Medicao |
|---------|----------|------|---------|
| Latencia reply direta (p50) | ~15s | < 3s | Logs |
| Latencia aceite vaga (p50) | ~15s | < 2s | Logs |
| Taxa ack fora horario | 0% | 100% | Tabela |
| Mensagens fora horario processadas | 0% | 100% | Job |
| Jobs batch em janela | 0% | 100% | Scheduler |
| Visibilidade estado (Slack) | Nenhuma | A cada 5min | Canal |

---

## Riscos e Mitigacoes

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|---------------|---------|-----------|
| Delay muito baixo parece bot | Media | Alto | A/B test, ajustar minimos |
| Ack fora horario sem retomada | Baixa | Alto | Job obrigatorio + alerta |
| Jobs em janela perdendo mensagens | Baixa | Medio | Manter criticos a cada 1min |
| Painel Slack muito verboso | Media | Baixo | Sumarizar, canal dedicado |

---

## Rollout

| Fase | Criterio | Acao |
|------|----------|------|
| 1. Delay Engine | 10% das mensagens | Medir latencia |
| 2. Fora Horario | Todos os clientes | Monitorar ack rate |
| 3. Jobs | Ambiente staging | Validar janelas |
| 4. Painel | Canal teste | Ajustar formato |
| 5. Full | 100% | Monitorar metricas |

---

## Checklist Pre-Deploy

### Migrations
- [ ] julia_estado criada com singleton
- [ ] mensagens_fora_horario criada
- [ ] fila_mensagens alterada (tipo_contexto, prioridade)

### Codigo
- [ ] Classificador de contexto implementado
- [ ] Delay Engine funcionando
- [ ] Ack fora do horario enviando
- [ ] Job de retomada (08h)
- [ ] Scheduler com novas frequencias
- [ ] Estado da Julia atualizando
- [ ] Painel Slack enviando

### Testes
- [ ] Unitarios para classificador
- [ ] Unitarios para delay engine
- [ ] Integracao fora do horario
- [ ] Teste de janelas de jobs

### Observabilidade
- [ ] Logs com tipo_contexto
- [ ] Metricas de latencia por tipo
- [ ] Alerta se ack > 5s
- [ ] Alerta se retomada falhar

---

## Queries de Validacao

```sql
-- Latencia por tipo de contexto (ultimas 24h)
SELECT
    tipo_contexto,
    COUNT(*) as total,
    ROUND(AVG(EXTRACT(EPOCH FROM (enviado_em - criado_em)) * 1000)) as latencia_media_ms,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (enviado_em - criado_em)) * 1000)) as p50_ms,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (enviado_em - criado_em)) * 1000)) as p95_ms
FROM fila_mensagens
WHERE criado_em >= now() - interval '24 hours'
AND enviado_em IS NOT NULL
GROUP BY tipo_contexto
ORDER BY latencia_media_ms;

-- Mensagens fora do horario pendentes
SELECT
    COUNT(*) as pendentes,
    MIN(recebida_em) as mais_antiga
FROM mensagens_fora_horario
WHERE processada = FALSE;

-- Taxa de ack fora do horario
SELECT
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE ack_enviado) as com_ack,
    ROUND(COUNT(*) FILTER (WHERE ack_enviado) * 100.0 / NULLIF(COUNT(*), 0), 2) as taxa_ack
FROM mensagens_fora_horario
WHERE recebida_em >= now() - interval '7 days';

-- Estado atual da Julia
SELECT * FROM julia_estado;

-- Jobs executados por janela (hoje)
SELECT
    DATE_TRUNC('hour', executed_at) as hora,
    job_name,
    COUNT(*) as execucoes
FROM job_executions
WHERE executed_at >= CURRENT_DATE
GROUP BY DATE_TRUNC('hour', executed_at), job_name
ORDER BY hora, job_name;
```

---

*Sprint criada em 29/12/2025*
