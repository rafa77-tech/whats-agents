# Auditoria de Processos - Agente Júlia

Mapeamento completo de todos os processos, tools e fluxos do agente.

**Data:** 2025-12-29
**Versão:** 1.0

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
│ 10  TimingProcessor           → Aplica delay (45-180s)      │
│ 20  SendMessageProcessor      → Envia via Evolution         │
│ 30  SaveInteractionProcessor  → Salva no banco              │
│ 40  MetricsProcessor          → Calcula métricas            │
└─────────────────────────────────────────────────────────────┘
```

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
| TimingProcessor | 10 | Aplica delay antes de envio | Não (early exit salta) |
| SendMessageProcessor | 20 | Envia via Evolution API | Sim |
| SaveInteractionProcessor | 30 | Salva em interacoes table | Sim |
| MetricsProcessor | 40 | Calcula métricas | Não (early exit salta) |

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
3. Agenda processamento em background via `processar_mensagem_pipeline()`
4. Pipeline executa pré → core → pós processadores
5. Mensagem é enviada em background

**Semáforo:** Máximo 2 mensagens simultâneas (evita overload)

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
   Aplica delay aleatório (45-180s)
   Respeita rate limiting

7. ENVIO
   SendMessage → Evolution API

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

## Histórico

| Data | Versão | Mudança |
|------|--------|---------|
| 2025-12-29 | 1.0 | Documento inicial com mapeamento completo |
