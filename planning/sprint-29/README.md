# Sprint 29: Conversation Mode (Modo de Conversa)

**Status:** Planejado
**Inicio:** A definir
**Estimativa:** 1-2 semanas
**Dependencias:** Sprint 15 (Policy Engine) - usa doctor_state como base
**Responsavel:** Dev

---

## Objetivo

Adicionar **conversation_mode** ao sistema Julia para controlar O QUE ela pode fazer em cada tipo de conversa.

**Princípio Central:** A LLM "brilha" propondo transições, mas quem decide e executa com segurança é o backend.

### Diferença para Sprint 15 (Policy Engine)

| Sprint 15 | Sprint 29 |
|-----------|-----------|
| Foco no **MÉDICO** (estado dele) | Foco na **CONVERSA** (modo atual) |
| `doctor_state.permission_state` | `conversations.conversation_mode` |
| "Posso contatar este médico?" | "O que posso fazer nesta conversa?" |
| Regras de bloqueio/handoff | Regras de capabilities por modo |

### O Que Este Sistema Resolve

Sem "mode" + "gate", qualquer campanha vira ruído e risco:
- Discovery virando oferta por impulso
- Oferta virando suporte sem fechamento
- Followup virando spam

**Uma conversa não pode estar em dois mundos ao mesmo tempo.**

### Conceito Central: Máquina de Estados

```
┌─────────────────────────────────────────────────────────────────┐
│                  MÁQUINA DE ESTADOS DE CONVERSA                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────┐      ┌──────────┐      ┌──────────┐             │
│   │ DISCOVERY│ ───► │  OFERTA  │ ───► │ FOLLOWUP │             │
│   └──────────┘      └──────────┘      └──────────┘             │
│        │ ▲               │ ▲               │                    │
│        │ │               │ │               │                    │
│        │ └───────────────┘ │               │                    │
│        │                   │               │                    │
│        │            ┌────────────┐         │                    │
│        └──────────► │ REATIVACAO │ ◄───────┘                   │
│                     └────────────┘                               │
│                           │                                      │
│                           └────► DISCOVERY (quase sempre)       │
│                                                                  │
│   Cada modo governa:                                            │
│   1. Tools PERMITIDAS/BLOQUEADAS                                │
│   2. Claims PROIBIDOS (atos de fala)                            │
│   3. Comportamento REQUERIDO                                    │
│   4. Transições PERMITIDAS                                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Três Camadas de Proteção

| Camada | O Que Protege | Como |
|--------|---------------|------|
| **Tools** | Ações no sistema | `forbidden_tools` - LLM não consegue chamar |
| **Claims** | Promessas verbais | `forbidden_claims` - proibido no prompt |
| **Transitions** | Mudança de modo | `ALLOWED_TRANSITIONS` - matriz determinística |

---

## Modos de Conversa

| Modo | Objetivo | Quando entra | Quando sai |
|------|----------|--------------|------------|
| `discovery` | Conhecer o médico | Primeiro contato / inbound frio | Médico confirma interesse |
| `oferta` | **Intermediar** (conectar com responsável) | Interesse confirmado | Ponte feita ou objeção |
| `followup` | Acompanhar desfecho da intermediação | Após ponte ser feita | Fechou/não fechou/silêncio > 7d |
| `reativacao` | Reativar inativo | Silêncio prolongado | Médico responde |

**Decisão de produto:** `oferta` = intermediação (sem reserva, sem preço).
**Evolução futura:** quando houver vagas próprias → criar `oferta_propria` (aí sim habilita reserva/negociação).

---

## Matriz de Transições Permitidas (AJUSTE 1)

**Regra:** Se a LLM propuser transição fora desta matriz → REJEITAR e registrar `blocked_transition`.

```python
ALLOWED_TRANSITIONS = {
    ConversationMode.DISCOVERY: {
        ConversationMode.OFERTA,      # Com evidência + micro-confirmação
        ConversationMode.REATIVACAO,  # Silêncio > 7d
    },
    ConversationMode.OFERTA: {
        ConversationMode.FOLLOWUP,    # Após reserva ou aguardando decisão
        ConversationMode.DISCOVERY,   # Objeção tratada, recuar para conhecer
        ConversationMode.REATIVACAO,  # Silêncio > 7d
    },
    ConversationMode.FOLLOWUP: {
        ConversationMode.OFERTA,      # Nova oportunidade
        ConversationMode.DISCOVERY,   # Mudança de contexto
        ConversationMode.REATIVACAO,  # Silêncio > 7d
    },
    ConversationMode.REATIVACAO: {
        ConversationMode.DISCOVERY,   # Quase sempre (reconquistar)
        ConversationMode.OFERTA,      # Interesse retomado direto
        ConversationMode.FOLLOWUP,    # Retomou conversa existente
    },
}
```

### Transições PROIBIDAS (Nunca Passam)

| De → Para | Motivo |
|-----------|--------|
| `discovery` → `followup` | Não há contexto para dar continuidade |
| `reativacao` → `reativacao` | Não faz sentido reativar quem está sendo reativado |

---

## Capabilities por Modo (Três Camadas)

### Camada 1: Tools (Ações no Sistema)

**IMPORTANTE:** Julia é INTERMEDIÁRIA. Ela conecta médico com responsável da vaga.

| Tool | discovery | oferta | followup | reativacao | Descrição |
|------|-----------|--------|----------|------------|-----------|
| `buscar_vagas` | ❌ | ✅ | ✅ | ✅ | Mostra vagas disponíveis (somente leitura) |
| `criar_handoff_externo` | ❌ | ✅ | ✅ | ❌ | Coloca em contato com dono da vaga |
| `registrar_status_intermediacao` | ❌ | ✅ | ✅ | ❌ | Status: interessado/contatado/fechado/sem_resposta |
| `salvar_memoria` | ✅ | ✅ | ✅ | ✅ | Salva informações do médico |
| `agendar_followup` | ❌ | ✅ | ✅ | ✅ | Agenda próximo contato |
| `perguntar_interesse` | ✅ | ❌ | ✅ | ✅ | Sonda interesse do médico |
| `perguntar_especialidade` | ✅ | ❌ | ❌ | ❌ | Conhece perfil do médico |

**Tools BLOQUEADAS EM TODOS OS MODOS (NUNCA usar):**

| Tool | Motivo |
|------|--------|
| ~~`reservar_plantao`~~ | Julia NÃO é dona da vaga |
| ~~`calcular_valor`~~ | Julia NÃO negocia valores |
| ~~`solicitar_documentos`~~ | Responsável da vaga pede docs |

### Camada 2: Claims Proibidos (AJUSTE 3)

**PROIBIÇÕES GLOBAIS (Aplicam a TODOS os modos):**

| Forbidden Claim | Descrição | Exemplos proibidos |
|-----------------|-----------|-------------------|
| `confirm_booking` | Confirmar reserva | "fechado", "confirmado", "tá reservado" |
| `quote_price` | Citar valores exatos | "paga X", "consigo X", "valor mínimo" |
| `promise_availability` | Garantir disponibilidade | "garanto que ainda tem" |
| `negotiate_terms` | Negociar condições | "consigo melhorar", "dá pra subir" |

**PROIBIÇÕES POR MODO (além das globais):**

| Modo | `forbidden_claims` adicionais |
|------|------------------------------|
| `discovery` | offer_specific_shift |
| `oferta` | (apenas globais - é modo de intermediação) |
| `followup` | pressure_decision, create_urgency |
| `reativacao` | offer_specific_shift, pressure_return |

### Camada 3: Comportamento Requerido

| Modo | `required_behavior` (DEVE fazer) |
|------|----------------------------------|
| `discovery` | "Conheça o médico. Pergunte 1 coisa de qualificação antes de propor transição." |
| `oferta` | "Apresente vagas. CONECTE com responsável. NÃO negocie valores." |
| `followup` | "Acompanhe se houve conversão. Pergunte se falou com responsável." |
| `reativacao` | "Seja gentil. Não cobre. Ofereça algo novo." |

---

## Mode Router (Transição de Modos)

### Arquitetura: 3 Camadas

```
┌─────────────────────────────────────────────────────────────────┐
│                         MODE ROUTER                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   MENSAGEM DO MÉDICO                                            │
│        │                                                         │
│        ▼                                                         │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ CAMADA 1: DETECÇÃO DE INTENÇÃO (AJUSTE 2)               │   │
│   │                                                          │   │
│   │  - Detecta detected_intent (o que o médico quer)        │   │
│   │  - Exemplos: ask_for_shift, pricing_question,           │   │
│   │    complaint, profile_update, smalltalk, optout         │   │
│   │  - Retorna: { detected_intent, confidence }             │   │
│   └─────────────────────────────────────────────────────────┘   │
│        │                                                         │
│        ▼                                                         │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ CAMADA 2: PROPOSTA DE TRANSIÇÃO                         │   │
│   │                                                          │   │
│   │  - Baseado em intent + modo_atual                       │   │
│   │  - Propõe: { proposed_mode, transition_evidence }       │   │
│   │  - SE transição não-trivial: propor MICRO-CONFIRMAÇÃO   │   │
│   └─────────────────────────────────────────────────────────┘   │
│        │                                                         │
│        ▼                                                         │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ CAMADA 3: VALIDAÇÃO (Backend Determinístico)            │   │
│   │                                                          │   │
│   │  - Verifica ALLOWED_TRANSITIONS[current] → proposed     │   │
│   │  - Verifica threshold de confiança                      │   │
│   │  - Verifica cooldown entre transições                   │   │
│   │  - Decide: ACEITAR, REJEITAR, ou PEDIR_CONFIRMAÇÃO      │   │
│   │  - Registra decisão + motivo para auditoria             │   │
│   └─────────────────────────────────────────────────────────┘   │
│        │                                                         │
│        ├── ACEITAR ──► atualizar conversation_mode              │
│        ├── PEDIR_CONFIRMAÇÃO ──► aguardar resposta (AJUSTE 4)   │
│        └── REJEITAR ──► manter modo + log blocked_transition    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Separação: Intent vs Mode (AJUSTE 2)

| Conceito | O Que É | Quem Define |
|----------|---------|-------------|
| `detected_intent` | O que o médico quer/sinaliza | Detector (regras + LLM) |
| `proposed_mode` | Modo sugerido para conversa | Router (baseado em intent) |
| `final_mode` | Modo efetivo da conversa | Backend (validação determinística) |

**Intents possíveis:**
- `ask_for_shift` - pergunta sobre vaga/plantão
- `pricing_question` - pergunta sobre valores
- `complaint` - reclamação
- `profile_update` - atualização de perfil
- `smalltalk` - conversa informal
- `optout` - pedido para não contatar
- `handoff_request` - pedido de humano
- `availability_check` - consulta de disponibilidade
- `confirmation` - confirmação de algo

**Vantagem:** Medir "quantas vezes LLM tentou transicionar e foi bloqueada" → ajustar prompt ou matriz.

### Transições Permitidas

```
discovery ──┬─► oferta      (interesse detectado)
            └─► reativacao  (silêncio > 7d)

oferta ─────┬─► followup    (pós-oferta, aguardando decisão)
            ├─► discovery   (objeção, recuar para conhecer melhor)
            └─► reativacao  (silêncio > 7d)

followup ───┬─► oferta      (nova oportunidade)
            ├─► discovery   (mudança de contexto)
            └─► reativacao  (silêncio > 7d)

reativacao ─┬─► oferta      (interesse retomado)
            ├─► discovery   (precisa reconquistar)
            └─► followup    (retomou conversa)
```

### Transições PROIBIDAS

| De | Para | Motivo |
|----|------|--------|
| `discovery` | `followup` | Não há contexto para dar continuidade |
| `reativacao` | `reativacao` | Não faz sentido reativar quem está sendo reativado |

---

## Micro-Confirmação de Transição (AJUSTE 4)

**Problema:** Julia não deve virar OFERTA no primeiro gatilho automaticamente.
**Solução:** Transições não-triviais passam por micro-confirmação.

### Exemplo Prático

```
Médico: "tem plantão essa semana?"

# Julia ainda em DISCOVERY (não transicionou)
Julia: "tenho sim! quer que eu te mande umas opções por aqui?"

Médico: "sim, manda aí"

# AGORA transiciona para OFERTA
# transition_reason = "user_requested_shift + confirmed_yes"
Julia: [busca vagas e apresenta]
```

### Quando Exigir Micro-Confirmação

| Transição | Exige Confirmação? | Motivo |
|-----------|-------------------|--------|
| discovery → oferta | ✅ SIM | Evitar falso positivo (curiosidade vs interesse real) |
| oferta → followup | ❌ NÃO | Natural após reserva |
| oferta → discovery | ❌ NÃO | Recuo por objeção é imediato |
| followup → oferta | ✅ SIM | Confirmar interesse em nova vaga |
| reativacao → * | ❌ NÃO | Qualquer resposta já é sinal |

### Fluxo Técnico

```python
class TransitionStatus(Enum):
    PENDING_CONFIRMATION = "pending_confirmation"  # Aguardando confirmação
    CONFIRMED = "confirmed"                        # Confirmado, pode transicionar
    REJECTED = "rejected"                          # Usuário rejeitou

# No banco
ALTER TABLE conversations
ADD COLUMN pending_transition conversation_mode_enum,
ADD COLUMN pending_transition_at TIMESTAMPTZ;
```

### Benefícios

1. **Reduz falso positivo:** "pergunta retórica", "curiosidade", "tô só vendo"
2. **Auditável:** `transition_reason = "user_requested_shift + confirmed_yes"`
3. **Natural:** Julia parece mais humana, não "pulando etapas"

---

## Épicos

| # | Épico | Descrição | Estimativa |
|---|-------|-----------|------------|
| E01 | Schema conversation_mode | Adicionar campo + enum + migração | 2h |
| E02 | Capabilities Gate | Mapa mode → tools permitidas | 4h |
| E03 | Mode Router | Detecção + validação de transição | 6h |
| E04 | Integração no agente | Plugar no fluxo existente | 4h |
| E05 | Testes e Validação | Unitários + integração | 4h |

**Total:** ~20h (1-2 semanas)

---

## Arquivos Detalhados

- [E01: Schema conversation_mode](./epic-01-schema.md)
- [E02: Capabilities Gate](./epic-02-capabilities.md)
- [E03: Mode Router](./epic-03-router.md)
- [E04: Integração](./epic-04-integracao.md)
- [E05: Testes](./epic-05-testes.md)

---

## Relação com Policy Engine (Sprint 15)

O conversation_mode **COMPLEMENTA** o Policy Engine:

```
┌─────────────────────────────────────────────────────────────────┐
│                    FLUXO DE DECISÃO                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   MENSAGEM RECEBIDA                                             │
│        │                                                         │
│        ▼                                                         │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ 1. POLICY ENGINE (Sprint 15)                            │   │
│   │    - Verificar doctor_state                             │   │
│   │    - Opt-out? Cooling off? Objeção grave?               │   │
│   │    - BLOQUEIA se necessário                             │   │
│   └─────────────────────────────────────────────────────────┘   │
│        │                                                         │
│        │ (passou)                                                │
│        ▼                                                         │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ 2. MODE ROUTER (Sprint 29)                              │   │
│   │    - Detectar modo atual                                │   │
│   │    - Verificar se precisa transição                     │   │
│   │    - Atualizar conversation_mode                        │   │
│   └─────────────────────────────────────────────────────────┘   │
│        │                                                         │
│        ▼                                                         │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ 3. CAPABILITIES GATE                                    │   │
│   │    - Verificar tools permitidas no modo atual           │   │
│   │    - Filtrar tools disponíveis para LLM                 │   │
│   └─────────────────────────────────────────────────────────┘   │
│        │                                                         │
│        ▼                                                         │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ 4. GERAR RESPOSTA (LLM)                                 │   │
│   │    - Apenas tools filtradas disponíveis                 │   │
│   │    - Constraints injetados no prompt                    │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Triggers de Transição

### Regras Determinísticas (sempre aplicam)

| Trigger | Transição | Condição |
|---------|-----------|----------|
| `interesse_explicito` | → `oferta` | Médico pergunta sobre vaga/valor/local |
| `silencio_prolongado` | → `reativacao` | 7+ dias sem resposta |
| `nova_oferta_aceita` | → `followup` | Após reservar plantão |
| `objecao_tratada` | → `discovery` | Objeção resolvida, recomeçar |

### Sinais Fracos (LLM como amplificador)

O LLM detecta sinais que as regras não pegam:

| Sinal | Exemplo | Transição sugerida |
|-------|---------|-------------------|
| Interesse implícito | "Interessante..." | → `oferta` |
| Mudança de contexto | "Mas antes de continuar..." | → `discovery` |
| Reabertura | "Oi, lembra de mim?" | → depende do histórico |

**Importante:** LLM sugere, backend valida.

---

## Métricas de Sucesso

| Métrica | Meta |
|---------|------|
| Transições corretas (audit) | > 95% |
| Tools bloqueadas respeitadas | 100% |
| Tempo de validação | < 5ms |
| Cobertura de testes | > 80% |

---

## Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Mode errado no início | Média | Baixo | Default conservador (discovery) |
| Transição prematura | Média | Médio | Threshold de confiança |
| LLM ignora capabilities | Baixa | Alto | Gate no backend, não só prompt |
| Complexidade excessiva | Média | Médio | Começar com 4 modos apenas |

---

## Backfill e Compatibilidade (AJUSTE 5)

### Regras para Conversas Existentes

| Situação | Modo Inicial | Motivo |
|----------|--------------|--------|
| Conversa com `vaga_id` ou `reserva` no histórico | `followup` | Já estava em contexto de vaga |
| Conversa ativa sem contexto de vaga | `discovery` | Conservador |
| Conversa inativa > 7 dias | `reativacao` | Precisa reativar |
| Inbound frio (novo) | `discovery` | Começar do zero |

### Conversas Iniciadas por Campanha

| Tipo da Campanha | Modo Inicial |
|------------------|--------------|
| discovery | `discovery` |
| oferta | `oferta` |
| followup | `followup` |
| reativacao | `reativacao` |

### SQL de Backfill

```sql
-- Conversas com vaga/reserva → followup
UPDATE conversations
SET conversation_mode = 'followup'::conversation_mode_enum
WHERE id IN (
    SELECT DISTINCT conversa_id FROM interacoes
    WHERE vaga_id IS NOT NULL OR reserva_id IS NOT NULL
)
AND conversation_mode = 'discovery';

-- Conversas inativas > 7 dias → reativacao
UPDATE conversations
SET conversation_mode = 'reativacao'::conversation_mode_enum
WHERE last_message_at < NOW() - INTERVAL '7 days'
AND status = 'active'
AND conversation_mode = 'discovery';
```

---

## Como Campanhas Funcionam com Modos

### Fluxo Completo

```
┌─────────────────────────────────────────────────────────────────┐
│                    FLUXO DE CAMPANHA                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   1. HUMANO CRIA CAMPANHA (via Slack)                           │
│      - tipo: discovery/oferta/followup/reativacao               │
│      - filtro/segmento                                          │
│      - limite (ex: 10 médicos)                                  │
│      - janela de execução                                       │
│      - copy/brief (pode ser gerado pela Julia)                  │
│                                                                  │
│   2. SCHEDULER PROCESSA                                         │
│      - Resolve alvos pelo filtro                                │
│      - Enfileira em fila_mensagens com acao_id                  │
│                                                                  │
│   3. MENSAGEM ENVIADA                                           │
│      - Quando médico responde, conversa nasce com:              │
│        • mode_source = "campaign:<acao_id>"                     │
│        • conversation_mode = <tipo_da_campanha>                 │
│        • capabilities_gate daquele modo                         │
│                                                                  │
│   4. JULIA OPERA DENTRO DO MODO                                 │
│      - Não "escolhe campanha"                                   │
│      - Escolhe transições DENTRO daquela conversa               │
│      - Backend valida cada transição                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Campos no Banco

```sql
ALTER TABLE conversations
ADD COLUMN mode_source TEXT;  -- "inbound", "campaign:<id>", "manual"

-- Exemplos:
-- mode_source = "inbound" → médico iniciou
-- mode_source = "campaign:abc-123" → campanha iniciou
-- mode_source = "manual" → gestor iniciou via Slack
```

### Implicação Chave

**Julia NÃO "escolhe campanha".**
- Quem escolhe é a operação (Slack/gestor)
- Julia escolhe transições dentro da conversa
- Isso dá controle e auditabilidade

---

## Guardrail Crítico: Julia é INTERMEDIÁRIA

**A Julia NÃO é dona das vagas.** Ela faz intermediação entre médicos e os responsáveis pelas vagas.

### Origem das Vagas

As vagas vêm de **scraping de grupos de WhatsApp**. O "dono" da vaga é quem postou no grupo.

### Fluxo Correto de Oferta

```
┌─────────────────────────────────────────────────────────────────┐
│                    FLUXO DE INTERMEDIAÇÃO                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   1. JULIA APRESENTA VAGA                                       │
│      - Mostra informações básicas (hospital, horário, região)   │
│      - NÃO confirma valores (pode informar faixa genérica)      │
│      - NÃO garante disponibilidade                              │
│                                                                  │
│   2. MÉDICO MOSTRA INTERESSE                                    │
│      - Julia qualifica o médico (CRM, especialidade)            │
│      - Julia NÃO negocia valores                                │
│                                                                  │
│   3. JULIA CONECTA COM RESPONSÁVEL                              │
│      - Passa contato do responsável pela vaga                   │
│      - OU passa dados do médico para o responsável              │
│      - A NEGOCIAÇÃO é entre médico e responsável                │
│                                                                  │
│   4. JULIA FAZ FOLLOW-UP                                        │
│      - Acompanha se houve conversão                             │
│      - Registra resultado (fechou, não fechou, motivo)          │
│      - NÃO interfere na negociação                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### O Que Julia NÃO Pode Fazer (NUNCA)

| Proibição | Motivo |
|-----------|--------|
| ❌ Confirmar reserva diretamente | Não é dona da vaga |
| ❌ Negociar valores | Não tem autoridade |
| ❌ Garantir disponibilidade | Pode ter mudado |
| ❌ Fechar plantão sem responsável | Risco de conflito |
| ❌ Prometer condições | Não controla a vaga |

### O Que Julia PODE Fazer

| Permissão | Contexto |
|-----------|----------|
| ✅ Informar faixa de valores | "Geralmente vai de X a Y" |
| ✅ Mostrar detalhes da vaga | Hospital, horário, região |
| ✅ Qualificar o médico | CRM, especialidade, disponibilidade |
| ✅ Conectar com responsável | Passar contato ou dados |
| ✅ Fazer follow-up | "Conseguiu falar com o responsável?" |

### Implicação no Código

```python
# ERRADO - Julia não pode fazer isso
async def reservar_plantao(vaga_id: str, medico_id: str):
    """Reserva plantão diretamente."""  # ❌ NÃO!
    ...

# CORRETO - Julia conecta
async def conectar_com_responsavel(vaga_id: str, medico_id: str):
    """Conecta médico interessado com responsável pela vaga."""  # ✅
    ...

async def registrar_interesse(vaga_id: str, medico_id: str):
    """Registra interesse do médico para follow-up."""  # ✅
    ...
```

---

## Refinamentos e Guardrails

### 1. Pricing Question no Discovery (Evitar Transição Prematura)

**Problema:** Médico pergunta "quanto paga?" → intent parece "interesse" → transição prematura para OFERTA.

**Solução:** Regra explícita no `required_behavior` do DISCOVERY:

```
Se perguntarem sobre valores no DISCOVERY:
- Explique de forma genérica (faixa/depende)
- NÃO mencione vaga específica
- Puxe 1 pergunta de qualificação
```

**Exemplo correto:**
```
Médico: "quanto paga um plantão de vocês?"
Julia: "depende bastante da região e especialidade!
       Em SP capital, a faixa vai de R$1.800 a R$3.500 por 12h.
       Vc é de qual especialidade mesmo?"
```

### 2. Structured Logging ("Black Box Recorder")

Todo processamento do Router salva:

```python
@dataclass
class ModeDecisionLog:
    timestamp: datetime
    conversa_id: str
    current_mode: str
    detected_intent: str
    proposed_mode: Optional[str]
    validator_decision: str  # APPLY, PENDING, CONFIRM, CANCEL, REJECT
    transition_reason: str
    capabilities_version: str  # Hash do CAPABILITIES_BY_MODE
```

**Benefício:** Quando der ruim, explica em 30 segundos.

### 3. Bootstrap de Modo (Regras Determinísticas)

**Problema:** Inbound que deveria começar em OFERTA entra como DISCOVERY.

**Exemplo perigoso:**
```
"Oi, sou o Dr João, vi uma vaga de anestesia com vocês"
# Se cair como DISCOVERY, Julia parece "lerda"
```

**Solução:** Regras de bootstrap ANTES da LLM:

| Origem | Regra | Modo Inicial |
|--------|-------|--------------|
| Campanha discovery | - | `discovery` |
| Campanha oferta | - | `oferta` |
| Inbound com "vaga"/"plantão" na 1ª msg | Detectado por regex | `oferta` |
| Inbound frio sem contexto | - | `discovery` |
| Resposta a campanha | mode_source=campaign | Modo da campanha |

```python
def bootstrap_mode(primeira_mensagem: str, origem: str) -> ConversationMode:
    """Determina modo inicial de forma determinística."""

    # Se veio de campanha, herda o modo
    if origem.startswith("campaign:"):
        return get_campaign_mode(origem)

    # Inbound com sinal claro de interesse
    interest_patterns = [
        r"\bvaga\b",
        r"\bplant[aã]o\b",
        r"\bescala\b",
        r"\btrabalhar\b.*\bvoc[eê]s\b",
    ]
    for pattern in interest_patterns:
        if re.search(pattern, primeira_mensagem.lower()):
            return ConversationMode.OFERTA

    # Default conservador
    return ConversationMode.DISCOVERY
```

### 4. Soft Interest Zone (Zona Cinza)

**Problema:** Transições "emocionais" que não são pedido explícito:
- "me manda mais detalhes"
- "depende do valor"
- "se for perto de casa, pode ser"

**Solução para V1:** Adicionar flag `soft_interest_detected`:

```python
# Quando soft_interest é detectado:
# - Libera buscar_vagas (mostrar opções)
# - BLOQUEIA reservar_plantao (não fechar ainda)
# - Próxima mensagem positiva confirma transição

class SoftInterestState:
    detected: bool = False
    detected_at: Optional[datetime] = None
    evidence: str = ""
```

### 5. Métrica de Violações

Além de bloquear, **medir** tentativas de violação:

```python
# Sempre que LLM tenta usar tool bloqueada ou fazer claim proibido
logger.warning(f"VIOLATION_ATTEMPT: mode={mode}, attempted={action}")

# Métrica agregada
violations_by_mode = {
    "discovery": {"buscar_vagas": 12, "quote_price": 3},
    "reativacao": {"reservar_plantao": 5}
}
```

**Uso:** Ajustar prompt ou matriz quando violação é frequente.

### 6. Escopo do Piloto

Para os primeiros 10 médicos, **não abrir todos os modos**:

| Modo | No Piloto? |
|------|------------|
| discovery | ✅ |
| oferta | ✅ |
| followup | ✅ |
| reativacao | ❌ Desabilitado |

**Motivo:** Menos superfície = menos ruído = aprendizado mais limpo.

### 7. Slack: Apenas Start/Stop

Slack pode:
- ✅ Criar ação ("iniciar discovery com 10 médicos")
- ✅ Pausar/cancelar campanha
- ✅ Consultar status

Slack NÃO pode:
- ❌ Mudar modo de conversa ativa
- ❌ Forçar transição
- ❌ Pular confirmação

**Motivo:** Evitar gambiarras e manter auditabilidade.

---

## Out of Scope (Sprint 29)

- Novos modos além dos 4 principais
- UI/Dashboard para gerenciar modos
- Machine learning para detectar transições
- Histórico detalhado de transições (log básico é suficiente)
- Criação de campanhas via Slack (Sprint futura)

---

## Próximos Passos

1. ✅ Documentação da Sprint
2. [ ] E01: Migração schema
3. [ ] E02: Capabilities Gate
4. [ ] E03: Mode Router
5. [ ] E04: Integração
6. [ ] E05: Testes

---

*Sprint criada em 02/01/2026*
