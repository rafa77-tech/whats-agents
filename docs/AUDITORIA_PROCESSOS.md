# Auditoria de Processos - Agente Júlia

Mapeamento completo de todos os processos, tools e fluxos do agente.

**Data:** 2025-12-29
**Versão:** 2.0 (Produção)

---

## Sumário

1. [Tools do WhatsApp](#1-tools-do-whatsapp)
2. [Tools do Slack](#2-tools-do-slack)
3. [Pipeline de Mensagens](#3-pipeline-de-mensagens)
4. [Conhecimento Dinâmico](#4-conhecimento-dinâmico-rag)
5. [Processos Principais](#5-processos-principais)
6. [Jobs Agendados](#6-jobs-agendados)
7. [Integrações Externas](#7-integrações-externas)
8. [Fluxo Completo](#8-fluxo-completo-mensagem-recebida-até-resposta)
9. [Contratos e Invariantes](#9-contratos-e-invariantes)
10. [Matriz de Risco - Tools Write](#10-matriz-de-risco---tools-write)
11. [Governança de Flags](#11-governança-de-flags)
12. [Source of Truth - Tabelas](#12-source-of-truth---tabelas)
13. [Apêndice: Decisões Arquiteturais](#13-apêndice-decisões-arquiteturais)

---

## 1. Tools do WhatsApp

Tools disponíveis para o agente durante conversas com médicos.

### 1.1 Tabela Resumo

| Tool | Arquivo | Trigger | Output |
|------|---------|---------|--------|
| `buscar_vagas` | `app/tools/vagas.py:75` | "tem vaga?", "quais plantões?" | Lista de vagas filtradas |
| `reservar_plantao` | `app/tools/vagas.py:443` | "pode reservar", "aceito" | Confirmação da reserva |
| `buscar_info_hospital` | `app/tools/vagas.py:648` | "onde fica?", "qual endereço?" | Endereço formatado |
| `salvar_memoria` | `app/tools/memoria.py:21` | Preferências mencionadas | Salva no RAG |
| `agendar_lembrete` | `app/tools/lembrete.py:13` | "me liga amanhã" | Agenda followup |

### 1.2 Detalhes dos Tools

#### `buscar_vagas`

**Arquivo:** `app/tools/vagas.py` (linhas 75-141)

**Descrição:** Lista vagas de plantão disponíveis (apenas MOSTRA, não reserva)

**Triggers:**
- "tem vaga?"
- "quais plantões?"
- "tem algo pra essa semana?"

**Input Schema:**
```json
{
  "especialidade": "string (opcional)",
  "regiao": "string (opcional)",
  "periodo": "enum: diurno/noturno/12h/24h/qualquer",
  "valor_minimo": "number (opcional)",
  "dias_semana": "array (opcional)",
  "limite": "integer (default: 5, max: 10)"
}
```

**Handler:** `handle_buscar_vagas()` (linhas 144-363)

**Fluxo:** Busca vagas compatíveis → Filtra por período/dias → Verifica conflitos → Formata resposta

---

#### `reservar_plantao`

**Arquivo:** `app/tools/vagas.py` (linhas 443-475)

**Descrição:** RESERVA um plantão/vaga quando médico ACEITA

**Triggers:**
- "Pode reservar"
- "Quero essa"
- "Fechado"
- "Aceito"
- "Pode ser"

**Input Schema:**
```json
{
  "data_plantao": "string OBRIGATÓRIO (YYYY-MM-DD)",
  "confirmacao": "string (descrição breve)"
}
```

**Handler:** `handle_reservar_plantao()` (linhas 517-641)

**Fluxo:** Valida data → Busca especialidade do médico → Busca vaga por data → Reserva no banco → Notifica gestor

---

#### `buscar_info_hospital`

**Arquivo:** `app/tools/vagas.py` (linhas 648-672)

**Descrição:** Busca informações sobre um hospital (endereço, bairro, cidade)

**Triggers:**
- "qual endereço?"
- "onde fica?"
- "como chego lá?"

**Input Schema:**
```json
{
  "nome_hospital": "string OBRIGATÓRIO"
}
```

**Handler:** `handle_buscar_info_hospital()` (linhas 675-743)

**Fluxo:** Busca hospital no banco (case insensitive) → Retorna dados completos

---

#### `salvar_memoria`

**Arquivo:** `app/tools/memoria.py` (linhas 21-84)

**Descrição:** Salva informações importantes sobre o médico para memória de longo prazo (RAG)

**Triggers:**
- "Prefiro plantão noturno"
- "Não trabalho aos domingos"
- "Mora em Santo André"
- Histórico com hospitais

**Input Schema:**
```json
{
  "informacao": "string OBRIGATÓRIO",
  "tipo": "enum: preferencia/restricao/info_pessoal/historico/comportamento",
  "confianca": "enum: alta/media/baixa (default: média)",
  "contexto": "string (opcional)"
}
```

**Handler:** `handle_salvar_memoria()` (linhas 87-195)

**Fluxo:** Gera embedding → Insere em doctor_context → Atualiza preferências_detectadas

---

#### `agendar_lembrete`

**Arquivo:** `app/tools/lembrete.py` (linhas 13-44)

**Descrição:** Agenda lembrete para contato futuro

**Triggers:**
- "me manda msg amanhã às 10h"
- "fala comigo à noite"
- "segunda-feira de manhã"

**Input Schema:**
```json
{
  "data_hora": "string OBRIGATÓRIO (ISO: YYYY-MM-DDTHH:MM)",
  "contexto": "string OBRIGATÓRIO",
  "mensagem_retorno": "string (opcional)"
}
```

**Handler:** `handle_agendar_lembrete()` (linhas 47-136)

**Fluxo:** Valida data/hora → Cria mensagem de retorno → Enfileira na fila

---

### 1.3 Agregação no Agente

**Arquivo:** `app/services/agente.py` (linhas 45-51)

```python
JULIA_TOOLS = [
    TOOL_BUSCAR_VAGAS,
    TOOL_RESERVAR_PLANTAO,
    TOOL_BUSCAR_INFO_HOSPITAL,
    TOOL_AGENDAR_LEMBRETE,
    TOOL_SALVAR_MEMORIA,
]
```

**Processor de Tools:** `processar_tool_call()` (linhas 54-89)

---

## 2. Tools do Slack

Tools disponíveis para gestão via Slack (comandos NLP).

**Arquivo:** `app/tools/slack/__init__.py`

### 2.1 Por Categoria

| Categoria | Tools | Descrição |
|-----------|-------|-----------|
| **Métricas** | `buscar_metricas`, `comparar_periodos` | Análise de performance |
| **Médicos** | `buscar_medico`, `listar_medicos`, `bloquear_medico`, `desbloquear_medico` | Gestão de médicos |
| **Mensagens** | `enviar_mensagem`, `buscar_historico` | Comunicação direta |
| **Vagas** | `buscar_vagas`, `reservar_vaga` | Gestão de plantões |
| **Sistema** | `status_sistema`, `buscar_handoffs`, `pausar_julia`, `retomar_julia`, `toggle_campanhas` | Controle operacional |
| **Briefing** | `processar_briefing` | Integração Google Docs |
| **Grupos** | `listar_vagas_revisao`, `aprovar_vaga_grupo`, `rejeitar_vaga_grupo`, `detalhes_vaga_grupo`, `estatisticas_grupos`, `metricas_pipeline`, `status_fila_grupos` | Pipeline de grupos WhatsApp |

### 2.2 Tools de Sistema (Kill Switches)

| Tool | Ação | Uso |
|------|------|-----|
| `pausar_julia` | Para TODO o envio de mensagens | Emergência |
| `retomar_julia` | Retoma envio de mensagens | Pós-emergência |
| `toggle_campanhas` | Ativa/desativa apenas campanhas | Controle granular |

---

## 3. Pipeline de Mensagens

Fluxo completo de processamento de mensagens recebidas.

### 3.1 Diagrama do Pipeline

```
WEBHOOK (Evolution API)
        ↓
┌─────────────────────────────────────────────────────────────┐
│ PRÉ-PROCESSADORES (12)                                      │
├─────────────────────────────────────────────────────────────┤
│  5  IngestaoGrupoProcessor    → Ingestão de grupos          │
│ 10  ParseMessageProcessor     → Parse da mensagem           │
│ 15  PresenceProcessor         → Presença/status             │
│ 20  LoadEntitiesProcessor     → Carrega médico/conversa     │
│ 22  BusinessEventInboundProcessor → Eventos de negócio      │
│ 25  ChatwootSyncProcessor     → Sincroniza Chatwoot         │
│ 30  OptOutProcessor           → Detecta opt-out        ⛔   │
│ 35  BotDetectionProcessor     → Detecta bot (37 padrões)⛔  │
│ 40  MediaProcessor            → Processa mídia         ⛔   │
│ 45  LongMessageProcessor      → Mensagens longas       ⛔   │
│ 50  HandoffTriggerProcessor   → Detecta handoff        ⛔   │
│ 60  HumanControlProcessor     → Controle humano        ⛔   │
└─────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────┐
│ CORE LLM (agente.py)                                        │
├─────────────────────────────────────────────────────────────┤
│ 1. Conhecimento Dinâmico (RAG)                              │
│    → Detecta objeção, perfil, objetivo                      │
│    → Busca conhecimento relevante                           │
│ 2. Policy Engine                                            │
│    → Extrai constraints                                     │
│ 3. Monta Prompt                                             │
│    → Contexto + vagas + memórias + diretrizes               │
│ 4. Claude Haiku + Tools                                     │
│    → Gera resposta                                          │
│ 5. Processa Tool Calls                                      │
│    → Executa tools e continua                               │
└─────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────┐
│ PÓS-PROCESSADORES (5)                                       │
├─────────────────────────────────────────────────────────────┤
│  5  ValidateOutputProcessor   → Valida resposta             │
│ 10  TimingProcessor           → Aplica delay (5-30s)        │
│ 20  SendMessageProcessor      → ⚠️ VIA WRAPPER (ver abaixo) │
│ 30  SaveInteractionProcessor  → Salva no banco              │
│ 40  MetricsProcessor          → Calcula métricas            │
└─────────────────────────────────────────────────────────────┘

⚠️ **CRÍTICO - SendMessageProcessor NÃO envia direto para Evolution!**
```
SendMessageProcessor
    → criar_contexto_reply(ctx)
    → enviar_resposta(telefone, texto, ctx)
        → send_outbound_message(telefone, texto, ctx)
            → check_outbound_guardrails(ctx)    [GUARDRAILS]
            → verificar_e_reservar(dedupe_key)  [DEDUPE]
            → evolution.enviar_mensagem()       [PROVIDER]
```
Este é o "one way out" - TODA mensagem passa pelo wrapper em `app/services/outbound.py`.

⛔ = Pode interromper pipeline e retornar resposta direta

### 3.2 Pré-Processadores

**Arquivo:** `app/pipeline/pre_processors.py`

| Processor | Prioridade | Função | Pode Parar Pipeline |
|-----------|-----------|--------|---------------------|
| IngestaoGrupoProcessor | 5 | Detecta entrada em grupo (não responde) | Sim |
| ParseMessageProcessor | 10 | Parse de mensagem, tipo de mídia | Não |
| PresenceProcessor | 15 | Detecta presença/read receipts | Não |
| LoadEntitiesProcessor | 20 | Carrega médico e conversa do banco | Não |
| BusinessEventInboundProcessor | 22 | E04: Eventos de negócio (offer_made) | Não |
| ChatwootSyncProcessor | 25 | Sincroniza com Chatwoot | Não |
| OptOutProcessor | 30 | Detecta pedido de opt-out | **Sim** |
| BotDetectionProcessor | 35 | Detecta se médico é bot (37 padrões) | **Sim** |
| MediaProcessor | 40 | Processa mídia (foto, áudio) | **Sim** |
| LongMessageProcessor | 45 | Detecta mensagens muito longas | **Sim** |
| HandoffTriggerProcessor | 50 | Detecta necessidade de handoff | **Sim** |
| HumanControlProcessor | 60 | Verifica se conversa sob controle humano | **Sim** |

### 3.3 Pós-Processadores

**Arquivo:** `app/pipeline/post_processors.py`

| Processor | Prioridade | Função | Sempre Executa |
|-----------|-----------|--------|----------------|
| ValidateOutputProcessor | 5 | Valida resposta gerada | Sim |
| TimingProcessor | 10 | Aplica delay humanizado | Não (early exit salta) |
| SendMessageProcessor | 20 | **Via wrapper** (guardrails + dedupe) | Sim |
| SaveInteractionProcessor | 30 | Salva em interacoes table | Sim |
| MetricsProcessor | 40 | Calcula métricas | Não (early exit salta) |

#### 3.3.1 TimingProcessor - Detalhes

**Arquivo:** `app/services/timing.py`

| Aspecto | Valor | Nota |
|---------|-------|------|
| Delay base | 5s | Mínimo garantido |
| Delay máximo | 30s | Limite superior |
| Aplica a | **Todos os tipos** | Reply E proativo (sem diferenciação) |
| Fórmula | base + leitura + complexidade × fator_hora × variação | |
| Variação | ±30% aleatório | Humanização |
| Fator hora | 1.0-1.4 | Mais lento almoço/início/fim do dia |

**Risco:** Delay de reply pode parecer lento para médico que espera resposta rápida. Considerar override para reply urgente.

#### 3.3.2 Semáforo de Concorrência

**Arquivo:** `app/api/routes/webhook.py:21`

```python
_semaforo_processamento = asyncio.Semaphore(2)  # Por instância
```

| Aspecto | Valor |
|---------|-------|
| Tipo | `asyncio.Semaphore` (in-memory) |
| Limite | 2 mensagens simultâneas |
| Escopo | **Por instância** (não global) |
| Comportamento overflow | Aguarda (enfileira) |
| Persistência | Não (reinício = reset) |

**Risco:** Em deploy multi-instância, cada instância tem seu próprio semáforo (total = 2 × N instâncias).

---

## 4. Conhecimento Dinâmico (RAG)

Sistema de conhecimento contextual implementado na Sprint 13.

**Arquivo Principal:** `app/services/conhecimento/orquestrador.py`

### 4.1 Componentes

| Componente | Arquivo | Função |
|------------|---------|--------|
| Orquestrador | `orquestrador.py` | Coordena 3 detectores, retorna contexto |
| Detector de Objeção | `detector_objecao.py` | Identifica objeções do médico |
| Detector de Perfil | `detector_perfil.py` | Classifica perfil comportamental |
| Detector de Objetivo | `detector_objetivo.py` | Identifica intenção da conversa |
| Buscador | `buscador.py` | Busca semântica em docs indexados |
| Indexador | `indexador.py` | Indexa documentos com embeddings |

### 4.2 Tipos de Objeção (10)

| Tipo | Descrição | Exemplo |
|------|-----------|---------|
| PRECO | Valor baixo, pagamento | "o valor tá baixo" |
| TEMPO | Agenda cheia, ocupado | "não tenho tempo" |
| CONFIANCA | Não conhece, desconfiança | "nunca ouvi falar" |
| PROCESSO | Burocracia, documentos | "muito documento" |
| DISPONIBILIDADE | Região, especialidade | "fica longe demais" |
| QUALIDADE | Hospital ruim | "esse hospital é ruim" |
| LEALDADE | Usa outra plataforma | "já trabalho com outro" |
| RISCO | Medo de não receber | "e se não pagar?" |
| MOTIVACAO | Não quer fazer plantão | "tô cansado de plantão" |
| COMUNICACAO | Não responde | Silêncio prolongado |

### 4.3 Perfis de Médico (7)

| Perfil | Características |
|--------|----------------|
| Eficiente | Rápido, objetivo, direto |
| Senior | Experiente, exigente |
| Junior | Iniciante, aprendendo |
| Conservador | Cauteloso, prefere segurança |
| Aventureiro | Aceita risco, flexível |
| Preço-sensível | Foca em valor monetário |
| Qualidade-focado | Quer o melhor hospital |

### 4.4 Objetivos da Conversa (8)

| Objetivo | Descrição |
|----------|-----------|
| Descoberta | Novo na plataforma |
| Oferta | Interessa em uma vaga |
| Negociação | Discute termos |
| Reclamação | Problema anterior |
| Feedback | Opinião sobre serviço |
| Informação | Quer saber mais |
| Interesse passivo | Pode interessar depois |
| Sem interesse | Recusa clara |

### 4.5 Base de Conhecimento

- **529 chunks** indexados de `docs/julia/`
- **Embeddings:** Voyage AI
- **Similaridade threshold:** 0.65
- **Cache:** 5 minutos

---

## 5. Processos Principais

### 5.1 Webhook de Mensagens

**Arquivo:** `app/api/routes/webhook.py`

**Endpoint:** `POST /webhook/evolution`

**Fluxo:**
1. Recebe webhook Evolution (event: messages.upsert)
2. Responde 200 imediatamente (não bloqueia Evolution)
3. Aguarda semáforo (`asyncio.Semaphore(2)`)
4. Agenda processamento em background via `processar_mensagem_pipeline()`
5. Pipeline executa pré → core → pós processadores
6. Mensagem é enviada em background

**Semáforo:** `asyncio.Semaphore(2)` - máximo 2 mensagens simultâneas **por instância**.
- Tipo: in-memory (não distribuído)
- Overflow: aguarda na fila
- Multi-instância: cada instância tem seu próprio limite

### 5.2 Geração de Resposta (LLM)

**Arquivo:** `app/services/agente.py`

**Função Principal:** `gerar_resposta_julia()` (linhas 92-250)

**Fluxo:**
1. **Conhecimento Dinâmico:** `OrquestradorConhecimento().analisar_situacao()`
2. **Policy Engine:** Extrai constraints da decisão
3. **Monta Prompt:** Contexto + vagas + histórico + memórias + diretrizes
4. **Gera com Tools:** Claude Haiku + JULIA_TOOLS
5. **Processa Tool Calls:** Executa e continua conversação
6. **Valida Output:** Não vazia, não bot, quebra se necessário

### 5.3 Campanhas

**Arquivo:** `app/services/jobs/campanhas.py`

**Tipos:**
- **Prospecção:** Contato frio com médico novo
- **Oferta:** Envio de vaga específica
- **Reativação:** Retorno com médico inativo
- **Followup:** Continuação de conversa
- **Custom:** Campanhas personalizadas

**Fluxo:**
1. Cria campanha com status "agendada"
2. Scheduler executa `processar_campanhas_agendadas()` a cada minuto
3. `criar_envios_campanha()` cria registros de envio
4. Worker enfileira mensagens para cada médico
5. Respeita rate limiting (20/hora, 100/dia)
6. Respeita horário comercial (08h-20h, seg-sex)

### 5.4 Handoff para Humano

**Arquivo:** `app/services/handoff.py`

**Triggers:**
1. Médico pede para falar com humano
2. Médico está irritado (sentimento negativo)
3. Situação complexa (jurídico, financeiro)
4. Confiança baixa na resposta do LLM

**Fluxo:**
1. `HandoffTriggerProcessor` detecta trigger
2. Júlia avisa: "Vou pedir pra minha supervisora te ajudar"
3. `UPDATE conversations SET controlled_by='human'`
4. Notifica gestor no Slack
5. Júlia para de responder
6. Humano assume via Chatwoot

### 5.5 Confirmação de Plantão

**Arquivo:** `app/services/confirmacao_plantao.py`

**Fluxo:**
1. Job detecta plantões que terminaram (shift_confirmation_due)
2. Envia mensagem perguntando se realizou
3. Médico confirma ou nega
4. Emite evento (shift_completed ou shift_not_completed)
5. Atualiza métricas

---

## 6. Jobs Agendados

**Arquivo:** `app/workers/scheduler.py`

| Job | Endpoint | Schedule | Descrição |
|-----|----------|----------|-----------|
| Mensagens Agendadas | `/jobs/processar-mensagens-agendadas` | 1 min | Envia lembretes, followups |
| Campanhas | `/jobs/processar-campanhas-agendadas` | 1 min | Inicia campanhas |
| Verificar Alertas | `/jobs/verificar-alertas` | 15 min | Status do sistema |
| Followups | `/jobs/processar-followups` | Diário 10h | Segue com inativos |
| Pausas Expiradas | `/jobs/processar-pausas-expiradas` | Diário 6h | Remove pausas vencidas |
| Avaliação de Conversas | `/jobs/avaliar-conversas-pendentes` | Diário 2h | Qualidade |
| Reports | `/jobs/report-periodo` | 4x/dia | Métricas |
| Doctor State | `/jobs/doctor-state-manutencao-diaria` | Diário 3h | Sync policy engine |
| Briefing Sync | `/jobs/sincronizar-briefing` | Diário | Google Docs |

---

## 7. Integrações Externas

### 7.1 Tabela Resumo

| Sistema | Uso | Arquivo |
|---------|-----|---------|
| **Evolution API** | WhatsApp (envio/recebimento) | `app/evolution.py` |
| **Chatwoot** | Supervisão, handoff | `app/services/chatwoot.py` |
| **Slack** | Comandos NLP, notificações | `app/services/slack/` |
| **Supabase** | PostgreSQL + pgvector | `app/services/supabase.py` |
| **Claude** | LLM (80% Haiku, 20% Sonnet) | `app/services/llm.py` |
| **Voyage AI** | Embeddings para RAG | `app/services/embeddings.py` |

### 7.2 Evolution API (WhatsApp)

**Arquivo:** `app/evolution.py`

- Webhook `POST /webhook/evolution` recebe mensagens
- Evolution envia: event, instance, data (message)
- Júlia processa e responde via Evolution API
- Multi-instância suportada (até 10 números WhatsApp)

### 7.3 Chatwoot (Supervisão)

**Arquivo:** `app/services/chatwoot.py`

**Métodos:**
- `buscar_contato_por_telefone()`: Busca médico
- `buscar_conversas_do_contato()`: Histórico
- `enviar_mensagem()`: Envia via Chatwoot
- `adicionar_label()`: Labels (handoff, oferta)
- `remover_label()`: Remove label

**Sincronização:**
- Chatwoot vê todas as conversas
- Gestor pode intervir (assume controle)
- Labels para classificação automática

### 7.4 Slack (Comandos e Notificações)

**Webhook:** `POST /webhook/slack`

**Agente Slack:** `app/services/slack/agent.py`

**Fluxo:**
1. Webhook recebe menção (@julia)
2. Verifica assinatura HMAC SHA256
3. Processa via `AgenteSlack`
4. Chama Claude para interpretar comando
5. Executa tools e responde

**Contexto de Sessão:**
- TTL de 30 minutos
- Histórico de commands
- Encadeamento de comandos

### 7.5 Claude LLM

**Arquivo:** `app/services/llm.py`

**Estratégia Híbrida:**
- **80% Haiku** ($0.25/1M input): Respostas simples
- **20% Sonnet**: Complexo (negociação, policy)

**Métodos:**
- `gerar_resposta()`: Sem tools
- `gerar_resposta_com_tools()`: Com tools
- `continuar_apos_tool()`: Continua após tool

---

## 8. Fluxo Completo: Mensagem Recebida até Resposta

```
1. RECEBIMENTO
   Evolution API → POST /webhook/evolution

2. ENFILEIRAMENTO
   Responde 200 imediatamente
   Agenda processar_mensagem_pipeline() em background

3. PRÉ-PROCESSAMENTO
   ParseMessage → LoadEntities → OptOut → BotDetection → Handoff
   [Se retorna resposta aqui, pula para envio]

4. CORE LLM
   Montar prompt (com conhecimento dinâmico + policy constraints)
   Chamar Claude Haiku com JULIA_TOOLS
   Processar tool calls se detectadas

5. VALIDAÇÃO
   ValidateOutput → Quebra em múltiplas mensagens se necessário

6. TIMING
   Aplica delay humanizado (5-30s)
   Fórmula: base + leitura + complexidade × fator_hora

7. ENVIO (VIA WRAPPER - CRÍTICO)
   SendMessage → criar_contexto_reply() → send_outbound_message()
       → check_outbound_guardrails() [Verifica regras R-1 a R4]
       → verificar_e_reservar()      [Dedupe por content_hash]
       → evolution.enviar_mensagem() [Provider]

8. SALVAR
   SaveInteraction → Insere em interacoes table

9. MÉTRICAS
   MetricsProcessor → Calcula e salva métricas

10. NOTIFICAÇÕES
    Notifica Chatwoot
    Notifica Slack (se handoff)
```

---

## Arquivos Principais

| Componente | Arquivo | Linhas |
|-----------|---------|--------|
| Agente Principal | `app/services/agente.py` | 656 |
| Webhook Evolution | `app/api/routes/webhook.py` | 350+ |
| Pipeline Processor | `app/pipeline/processor.py` | 150+ |
| Pré-processadores | `app/pipeline/pre_processors.py` | 500+ |
| Pós-processadores | `app/pipeline/post_processors.py` | 400+ |
| Conhecimento | `app/services/conhecimento/orquestrador.py` | 150+ |
| Slack Agent | `app/services/slack/agent.py` | 400+ |
| Chatwoot | `app/services/chatwoot.py` | 350+ |
| Tools Vagas | `app/tools/vagas.py` | 752 |
| Tools Memoria | `app/tools/memoria.py` | 268 |
| Campanhas | `app/services/jobs/campanhas.py` | 77 |
| Scheduler | `app/workers/scheduler.py` | 150+ |

---

## 9. Contratos e Invariantes

Regras invioláveis que devem ser garantidas pelo sistema. Quebrar qualquer invariante é bug crítico.

### 9.1 Invariantes de Eventos

| ID | Invariante | Verificação |
|----|------------|-------------|
| **I1** | Todo inbound persistido DEVE emitir `DOCTOR_INBOUND` (exatamente uma vez) | Query: inbounds sem evento correspondente |
| **I2** | Todo outbound DEVE resultar em exatamente um de: `DOCTOR_OUTBOUND`, `OUTBOUND_BLOCKED`, `OUTBOUND_BYPASS`, ou `OUTBOUND_DEDUPED` | Query: outbounds sem desfecho |
| **I3** | `method=reply` EXIGE `inbound_interaction_id` + `last_inbound_at` dentro da janela (30min) | Teste: `_has_valid_inbound_proof()` |
| **I4** | `opted_out` só pode receber outbound se: (a) `method=reply` válido, OU (b) bypass Slack COM `bypass_reason` | Guardrail R0 |
| **I5** | Nenhum evento pode carregar texto integral/PII em `event_props` | Regra R6 em `_validate_event_integrity()` |
| **I6** | Early-exit processors DEVEM emitir evento correspondente antes de retornar | Audit: opt-out emite evento antes de parar |

### 9.2 Invariantes de Outbound

| ID | Invariante | Implementação |
|----|------------|---------------|
| **O1** | TODO envio outbound passa por `send_outbound_message()` | CI gate: `test_architecture_guardrails.py` |
| **O2** | TODO envio proativo respeita rate limit (20/hora, 100/dia por telefone) | `RateLimitError` em `whatsapp.py` |
| **O3** | TODO envio proativo respeita horário comercial (08h-20h, seg-sex) | `esta_em_horario_comercial()` |
| **O4** | Dedupe por `content_hash` dentro de janela de 1 hora | `outbound_messages` table |

### 9.3 Contratos por Método (OutboundContext)

| Método | Campos Obrigatórios | is_proactive | Regras Aplicáveis |
|--------|---------------------|--------------|-------------------|
| `REPLY` | `inbound_interaction_id`, `last_inbound_at`, `conversation_id` | `false` | R-1 (proof) |
| `CAMPAIGN` | `campaign_id` | `true` | R0-R4 + campaigns.enabled |
| `FOLLOWUP` | `conversation_id` | `true` | R0-R4 |
| `REACTIVATION` | - | `true` | R0-R4 |
| `COMMAND` (Slack) | `actor_id` | `true` | R0-R4, bypass com `bypass_reason` |
| `MANUAL` | `actor_id`, `bypass_reason` (se opted_out) | `true` | R0-R4 |

### 9.4 Queries de Validação

```sql
-- I1: Inbounds sem evento DOCTOR_INBOUND
SELECT i.id, i.created_at
FROM interacoes i
LEFT JOIN business_events be ON be.interaction_id = i.id
  AND be.event_type = 'doctor_inbound'
WHERE i.tipo = 'entrada'
  AND i.created_at >= NOW() - INTERVAL '24 hours'
  AND be.id IS NULL;

-- I2: Outbounds sem desfecho (deve ser vazio)
SELECT i.id, i.created_at
FROM interacoes i
LEFT JOIN business_events be ON be.interaction_id = i.id
  AND be.event_type IN ('doctor_outbound', 'outbound_blocked', 'outbound_bypass')
WHERE i.tipo = 'saida'
  AND i.created_at >= NOW() - INTERVAL '24 hours'
  AND be.id IS NULL;
```

---

## 10. Matriz de Risco - Tools Write

Tools que modificam estado (write paths) e suas proteções.

### 10.1 Matriz Completa

| Tool | Read/Write | Dedupe Key | Concurrency Guard | Rate Limit | Failure Mode | Eventos Emitidos |
|------|------------|------------|-------------------|------------|--------------|------------------|
| `buscar_vagas` | Read | N/A | N/A | N/A | fail-open | Nenhum |
| `buscar_info_hospital` | Read | N/A | N/A | N/A | fail-open | Nenhum |
| `reservar_plantao` | **Write** | `vaga_id` | Optimistic lock (status=aberta) | N/A | fail-closed | `offer_accepted` |
| `salvar_memoria` | **Write** | `cliente_id + tipo + hash(info)` | Upsert | N/A | fail-open | Nenhum |
| `agendar_lembrete` | **Write** | `conversa_id + data_hora` | Unique constraint | N/A | fail-closed | Nenhum |
| `enviar_mensagem` (Slack) | **Write** | `cliente_id + content_hash` | Dedupe table | 20/hora | fail-closed | `doctor_outbound` ou `outbound_*` |
| `bloquear_medico` | **Write** | `cliente_id` | Idempotente | N/A | fail-closed | `permission_changed` |

### 10.2 Detalhes - reservar_plantao (Write Crítico)

**Arquivo:** `app/services/vagas/repository.py:88`

```python
# Optimistic locking - só reserva se ainda está aberta
.eq("id", vaga_id)
.eq("status", "aberta")  # ← Guard de concorrência
```

| Risco | Mitigação | Status |
|-------|-----------|--------|
| Concorrência (2 médicos reservam mesmo plantão) | `.eq("status", "aberta")` no UPDATE | ✅ Implementado |
| Tool chamada 2x pelo LLM | Vaga já muda para "reservada" no 1º call | ✅ Idempotente |
| Rollback após falha | Não implementado (reserva persiste) | ⚠️ Risco aceito |

### 10.3 Detalhes - salvar_memoria (Write)

| Risco | Mitigação | Status |
|-------|-----------|--------|
| Duplicação de memória | Embedding similarity check (>0.95 = mesmo) | ✅ Implementado |
| PII em memória | Não há sanitização automática | ⚠️ Risco aceito |

### 10.4 Dedupe de Inbound

**Risco identificado:** Dedupe de inbound depende do Evolution não duplicar.

| Situação | Mitigação Atual | Risco Residual |
|----------|-----------------|----------------|
| Evolution envia webhook 2x | `message_id` único por mensagem | Baixo (Evolution confiável) |
| Timeout + retry do lado Júlia | Não aplicável (Júlia não faz retry de recebimento) | N/A |

**Decisão:** Risco aceito. Se Evolution duplicar, processaremos 2x.

---

## 11. Governança de Flags

Sistema de feature flags para controle operacional.

### 11.1 Fonte de Verdade

```
┌─────────────────────────────────────────────────────┐
│                  SUPABASE                           │
│            feature_flags table                      │
│  ┌─────────────────────────────────────────────┐   │
│  │ key          │ value              │ updated │   │
│  │──────────────│────────────────────│─────────│   │
│  │ safe_mode    │ {enabled: false}   │ user_x  │   │
│  │ campaigns    │ {enabled: true}    │ system  │   │
│  │ policy_engine│ {enabled: true}    │ system  │   │
│  │ disabled_rules│{rules: []}        │ system  │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│                    REDIS                            │
│               Cache (TTL: 30s)                      │
│         feature_flag:{key} → value                  │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│                  APLICAÇÃO                          │
│          get_*_flags() → dataclass                  │
│                                                     │
│  Fallback chain:                                    │
│  1. Redis cache (30s TTL)                          │
│  2. Supabase query                                 │
│  3. Safe defaults (código)                         │
└─────────────────────────────────────────────────────┘
```

### 11.2 Flags Disponíveis

| Flag | Tipo | Default | Escopo | Quem Altera |
|------|------|---------|--------|-------------|
| `safe_mode` | `{enabled, mode}` | `{false, "wait"}` | Global | Slack: `pausar_julia` |
| `campaigns` | `{enabled}` | `{true}` | Global | Slack: `toggle_campanhas` |
| `policy_engine` | `{enabled}` | `{true}` | Global | Deploy/manual |
| `disabled_rules` | `{rules: []}` | `{rules: []}` | Global | Deploy/manual |

### 11.3 Precedência de Flags (Guardrails)

```
Ordem de verificação em check_outbound_guardrails():

1. R-1: inbound_proof (reply sem prova → vira proativo)
2. R0:  opted_out (absoluto, exceto reply válido ou bypass)
3. R1:  cooling_off
4. R2:  next_allowed_at
5. R3:  contact_cap_7d
6. R4a: campaigns.enabled (só para method=CAMPAIGN)
7. R4b: safe_mode (bloqueia TODO proativo)
```

**Regra de ouro:** `safe_mode` ganha de `campaigns.enabled`.
- `safe_mode=true` → bloqueia tudo proativo (incluindo campaigns)
- `campaigns.enabled=false` → bloqueia só campaigns (followup/reactivation continuam)

### 11.4 Escopo: Global vs Por Instância

| Flag | Escopo | Motivo |
|------|--------|--------|
| `safe_mode` | **Global** | Emergência afeta toda operação |
| `campaigns` | **Global** | Campanhas são centralizadas |
| Rate limit | **Por telefone** | Limite individual |
| Semáforo pipeline | **Por instância** | In-memory, não compartilhado |

### 11.5 Pontos de Leitura

| Flag | Lido em | Arquivo |
|------|---------|---------|
| `safe_mode` | `check_outbound_guardrails()` | `guardrails/check.py:407` |
| `campaigns` | `check_outbound_guardrails()` | `guardrails/check.py:394` |
| `policy_engine` | `decidir_proxima_acao()` | `policy/decide.py` |

---

## 12. Source of Truth - Tabelas

Definição de qual tabela é a fonte oficial para cada tipo de dado.

### 12.1 Mapa de Autoridade

| Domínio | Source of Truth | Tabela | Observação |
|---------|-----------------|--------|------------|
| **Status da conversa** | `conversations.controlled_by` | `conversations` | `julia` ou `human` |
| **Permissão do médico** | `doctor_state.permission_state` | `doctor_state` | `opted_in`, `opted_out`, `cooling_off` |
| **Histórico factual** | `interacoes` | `interacoes` | Imutável após criação |
| **Auditoria de eventos** | `business_events` | `business_events` | Append-only |
| **Decisões de policy** | `policy_events` | `policy_events` | Link com `doctor_state` |
| **Vagas disponíveis** | `vagas.status` | `vagas` | `aberta`, `reservada`, `fechada` |
| **Memória do médico** | `doctor_context` | `doctor_context` | RAG com embeddings |
| **Flags operacionais** | `feature_flags.value` | `feature_flags` | JSONB |
| **Campanhas** | `campanhas` | `campanhas` | Status + envios |

### 12.2 Relações Críticas

```
clientes (médico)
    │
    ├── conversations (1:N) ─── controlled_by: julia|human
    │       │
    │       └── interacoes (1:N) ─── tipo: entrada|saida
    │
    ├── doctor_state (1:1) ─── permission_state, cooling_off
    │
    ├── doctor_context (1:N) ─── memórias com embeddings
    │
    └── business_events (1:N) ─── auditoria
            │
            └── policy_events (0:1) ─── link opcional
```

### 12.3 Consistência

| Cenário | Fonte Primária | Secundária | Sync |
|---------|----------------|------------|------|
| Médico deu opt-out | `doctor_state` | `clientes.status`? | Manual (legado) |
| Conversa em handoff | `conversations.controlled_by` | Chatwoot label | Automático |
| Vaga reservada | `vagas.status` | Cache invalidado | Imediato |

---

## 13. Apêndice: Decisões Arquiteturais

Registro das decisões técnicas e seus motivos.

### 13.1 LLM: Haiku/Sonnet 80/20

| Decisão | Usar Claude Haiku para 80% das interações |
|---------|------------------------------------------|
| **Motivo** | Custo ($0.25/1M vs $3/1M) com qualidade suficiente |
| **Quando Sonnet** | Negociação complexa, policy decisions |
| **Economia** | ~73% vs Sonnet-only |
| **Risco** | Qualidade inferior em edge cases |

### 13.2 RAG: Similarity Threshold 0.65

| Decisão | Threshold de similaridade 0.65 |
|---------|-------------------------------|
| **Motivo** | Balanceia recall vs precisão |
| **Muito alto (0.8+)** | Perde conhecimento relevante |
| **Muito baixo (0.5-)** | Retorna muito ruído |
| **Ajuste** | Pode subir para 0.7 se muitos false positives |

### 13.3 Cache: 5 minutos para conhecimento

| Decisão | TTL de 5 minutos para buscas RAG |
|---------|----------------------------------|
| **Motivo** | Conhecimento muda raramente |
| **Trade-off** | Atualização de docs demora até 5min para refletir |
| **Alternativa** | Cache invalidation manual (não implementado) |

### 13.4 Timing: 5-30s (reduzido de 20-120s)

| Decisão | Delay de resposta 5-30 segundos |
|---------|--------------------------------|
| **Original** | 20-120s (muito lento para testes) |
| **Atual** | 5-30s (humanizado mas responsivo) |
| **Risco** | Pode parecer "bot" se muito rápido |
| **TODO** | Diferenciar reply (rápido) vs proativo (lento) |

### 13.5 Rate Limit: 20/hora, 100/dia

| Decisão | Limite de mensagens proativas |
|---------|------------------------------|
| **Por hora** | 20 mensagens |
| **Por dia** | 100 mensagens |
| **Escopo** | Por telefone (não global) |
| **Motivo** | Evitar ban do WhatsApp |
| **Base** | Políticas conhecidas do WhatsApp Business |

### 13.6 Semáforo: 2 mensagens simultâneas

| Decisão | Limite de 2 processamentos paralelos |
|---------|-------------------------------------|
| **Motivo** | Evitar sobrecarga do LLM/banco |
| **Tipo** | `asyncio.Semaphore` (in-memory) |
| **Risco** | Multi-instância = 2 × N total |
| **Alternativa** | Redis distributed lock (não implementado) |

### 13.7 Dedupe: Content hash + janela 1h

| Decisão | Deduplicação por hash de conteúdo |
|---------|----------------------------------|
| **Chave** | `sha256(texto)[:16]` |
| **Janela** | 1 hora |
| **Motivo** | Timeout + retry = duplicata |
| **Tabela** | `outbound_messages` |

---

## Histórico

| Data | Versão | Mudança |
|------|--------|---------|
| 2025-12-29 | 1.0 | Documento inicial com mapeamento completo |
| 2025-12-29 | 2.0 | Versão produção: contratos, matriz de risco, governança de flags, source of truth, decisões arquiteturais |
