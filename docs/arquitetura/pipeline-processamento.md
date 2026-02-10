# Pipeline de Processamento

## Visão Geral

O pipeline de processamento é a arquitetura central que orquestra o processamento de mensagens WhatsApp desde o recebimento até o envio da resposta. Utiliza padrão Chain of Responsibility modular com pré-processadores, processamento core (LLM) e pós-processadores.

Cada processador tem responsabilidade única e pode:
- Modificar o contexto compartilhado
- Interromper o fluxo (ex: opt-out, handoff)
- Executar validações e controles
- Persistir dados e métricas

## Fluxo de Processamento

```
Webhook Evolution/Z-API
         |
         v
┌─────────────────────────────────────────┐
│ PRE-PROCESSADORES (13 processadores)    │
├─────────────────────────────────────────┤
│ 1. IngestaoGrupo (5)                    │  ← Grupos → stop
│ 2. ParseMessage (10)                    │  ← Parse + validação
│ 3. Presence (15)                        │  ← Marca lida, online
│ 4. LoadEntities (20)                    │  ← Busca médico/conversa
│ 5. ChipMapping (21)                     │  ← Multi-chip tracking
│ 6. BusinessEventInbound (22)            │  ← Emite events
│ 7. ChatwootSync (25)                    │  ← Sincroniza IDs
│ 8. OptOut (30)                          │  ← Detecta PARE → stop
│ 9. BotDetection (35)                    │  ← Detecta "você é bot?"
│10. Media (40)                           │  ← Audio/img → resposta
│11. LongMessage (45)                     │  ← Trunca/pede resumo
│12. HandoffTrigger (50)                  │  ← "Falar com humano"
│13. HandoffKeyword (55)                  │  ← Confirmações externas
│14. HumanControl (60)                    │  ← Conversa humana → stop
└─────────────────────────────────────────┘
         |
         v
┌─────────────────────────────────────────┐
│ CORE PROCESSOR                          │
│ LLMCoreProcessor                        │  ← Claude (Haiku/Sonnet)
│ - processar_mensagem_completo()         │
│ - Policy Engine integration             │
└─────────────────────────────────────────┘
         |
         v
┌─────────────────────────────────────────┐
│ POST-PROCESSADORES (6+ processadores)   │
├─────────────────────────────────────────┤
│ 1. ValidateOutput (5)                   │  ← Valida persona
│ 2. Timing (10)                          │  ← Delay humanizado
│ 3. SendMessage (20)                     │  ← Envia WhatsApp
│ 4. ChatwootResponse (25)                │  ← Sync Chatwoot
│ 5. SaveInteraction (30)                 │  ← Persiste BD
│ 6. Extraction (35)                      │  ← Extrai dados (Sprint 53)
│ 7. Metrics (40)                         │  ← Registra métricas
└─────────────────────────────────────────┘
         |
         v
   Resposta Enviada
```

## Estrutura de Arquivos

```
app/pipeline/
├── __init__.py              # Exports públicos
├── base.py                  # Classes base (ProcessorContext, ProcessorResult)
├── processor.py             # MessageProcessor (orquestrador)
├── core.py                  # LLMCoreProcessor
├── setup.py                 # criar_pipeline() - configuração
├── pre_processors.py        # Imports dos pre-processors
├── post_processors.py       # Post-processors principais (6 classes)
└── processors/              # Módulos especializados (16 arquivos)
    ├── __init__.py
    ├── ingestao_grupo.py
    ├── parse.py
    ├── presence.py
    ├── entities.py
    ├── chip_mapping.py
    ├── business_events.py
    ├── chatwoot.py
    ├── optout.py
    ├── fora_horario.py      # REMOVIDO do pipeline (31/12/2025)
    ├── bot_detection.py
    ├── media.py
    ├── long_message.py
    ├── handoff.py
    ├── human_control.py
    └── extraction.py
```

## Pré-Processadores

Executados **antes** do LLM processar a mensagem. Ordem definida por `priority` (menor executa primeiro).

### 1. IngestaoGrupoProcessor (priority: 5)

**Arquivo:** `processors/ingestao_grupo.py`

**Função:** Detecta mensagens de grupos WhatsApp e as ingere para processamento posterior.

**Comportamento:**
- Verifica se `remoteJid` termina com `@g.us` (grupo)
- Se for grupo: ingere no sistema de processamento de grupos e **para o pipeline**
- Se não for grupo: continua normalmente

**Stop Condition:** Sim (mensagens de grupo não geram resposta automática)

**Sprints:** 51, 52, 53 (Pipeline de Grupos)

---

### 2. ParseMessageProcessor (priority: 10)

**Arquivo:** `processors/parse.py`

**Função:** Parseia payload do webhook da Evolution API ou Z-API.

**Comportamento:**
- Extrai texto, telefone, message_id, tipo (texto/audio/imagem)
- Detecta formato LID (LinkedIn ID format do WhatsApp Business)
- Resolve telefone via Chatwoot se LID sem `remoteJidAlt`
- Valida se deve processar (ignora mensagens próprias, status)
- Popula `ProcessorContext` inicial

**Stop Condition:** Sim (mensagens inválidas ou próprias)

**Extrai:**
- `context.mensagem_texto`
- `context.telefone`
- `context.message_id`
- `context.tipo_mensagem`
- `context.metadata["nome_contato"]`
- `context.metadata["remote_jid"]`
- `context.metadata["chatwoot_conversation_id"]`

---

### 3. PresenceProcessor (priority: 15)

**Arquivo:** `processors/presence.py`

**Função:** Envia presença online e marca mensagem como lida.

**Comportamento:**
- Marca mensagem como lida via Evolution API
- Mostra status "online" para o remetente
- Pula se provider for Z-API (não usa Evolution)

**Stop Condition:** Não

**Tolerância:** Erros não param o pipeline

---

### 4. LoadEntitiesProcessor (priority: 20)

**Arquivo:** `processors/entities.py`

**Função:** Carrega ou cria médico e conversa no banco de dados.

**Comportamento:**
- Busca/cria registro de médico (`clientes`)
- Busca/cria conversa (`conversations`)
- Popula `context.medico` e `context.conversa`

**Stop Condition:** Sim (apenas se falhar buscar/criar)

**Extrai:**
- `context.medico` (dict completo do médico)
- `context.conversa` (dict completo da conversa)

---

### 5. ChipMappingProcessor (priority: 21)

**Arquivo:** `processors/chip_mapping.py`

**Função:** Registra qual chip (instância WhatsApp) recebeu a mensagem.

**Comportamento:**
- Extrai `_evolution_instance` do payload
- Cria/atualiza mapeamento `conversation_chips`
- Registra métrica de recebimento no chip
- **Executa em background** (não bloqueia)

**Stop Condition:** Não

**Sprints:** 26 (Multi-Julia Orchestration), 40, 41

**Feature Flag:** `MULTI_CHIP_ENABLED`

---

### 6. BusinessEventInboundProcessor (priority: 22)

**Arquivo:** `processors/business_events.py`

**Função:** Emite evento de mensagem recebida para tracking de funil.

**Comportamento:**
- Emite `doctor_inbound` event
- Detecta possíveis recusas de oferta (em background)
- **Executa em background** (não bloqueia)

**Stop Condition:** Não

**Sprints:** 17 (Business Events e Funil)

**Emite:**
- `EventType.DOCTOR_INBOUND`

---

### 7. ChatwootSyncProcessor (priority: 25)

**Arquivo:** `processors/chatwoot.py`

**Função:** Sincroniza IDs do Chatwoot se não existirem.

**Comportamento:**
- Verifica se `chatwoot_conversation_id` existe
- Se não: busca via API do Chatwoot e atualiza no banco
- Popula `context.conversa["chatwoot_conversation_id"]`

**Stop Condition:** Não

**Tolerância:** Erros não param o pipeline

---

### 8. OptOutProcessor (priority: 30)

**Arquivo:** `processors/optout.py`

**Função:** Detecta e processa pedidos de opt-out ("PARE", "não quero").

**Comportamento:**
- Detecta 37 padrões de opt-out
- Marca médico como `opt_out = true` no banco
- Retorna template de despedida dinâmico
- **Para o pipeline** (não processa LLM)

**Stop Condition:** Sim (retorna resposta de opt-out)

**Sprints:** 1, 3

**Resposta:** Template `mensagens_especiais.optout` (banco)

---

### 9. BotDetectionProcessor (priority: 35)

**Arquivo:** `processors/bot_detection.py`

**Função:** Detecta se médico menciona que Julia é um bot/robô.

**Comportamento:**
- Detecta 37 padrões ("você é bot?", "inteligência artificial", etc)
- Registra detecção na tabela `metricas_deteccao_bot`
- Marca `context.metadata["bot_detected"] = True`
- **NÃO para o pipeline** (apenas registra)

**Stop Condition:** Não

**Sprints:** 4 (Métricas & Feedback)

---

### 10. MediaProcessor (priority: 40)

**Arquivo:** `processors/media.py`

**Função:** Trata mensagens de mídia (audio, imagem, documento, vídeo).

**Comportamento:**
- Detecta tipo de mídia (`context.tipo_mensagem`)
- Retorna resposta especial conforme tipo:
  - Audio: "Oi! Tô numa reunião agora e não consigo ouvir áudio..."
  - Imagem: Processa caption se houver, senão resposta padrão
  - Documento: "Oi! Recebi o documento..."
  - Vídeo: "Oi! Recebi o vídeo..."
- **Para o pipeline** (não processa LLM)

**Stop Condition:** Sim (retorna resposta de mídia)

**Sprints:** 8 (Memória & Pipeline)

---

### 11. LongMessageProcessor (priority: 45)

**Arquivo:** `processors/long_message.py`

**Função:** Trata mensagens muito longas (>2000 chars).

**Comportamento:**
- Se >3000 chars: pede resumo e **para pipeline**
- Se >2000 chars: trunca e marca `context.metadata["message_truncated"] = True`
- Se ≤2000 chars: continua normalmente

**Stop Condition:** Sim (apenas se >3000 chars)

**Resposta:** "Nossa, mensagem bem longa! Pode resumir pra mim?"

---

### 12. HandoffTriggerProcessor (priority: 50)

**Arquivo:** `processors/handoff.py`

**Função:** Detecta triggers de handoff para atendimento humano.

**Comportamento:**
- Detecta padrões: "falar com humano", "reclamação", etc
- Cria registro de handoff
- Notifica gestor via Slack
- **Para o pipeline** (não gera resposta automática)

**Stop Condition:** Sim

**Sprints:** 2 (Vagas & Chatwoot)

**Triggers:**
- Pedido explícito de humano
- Sentimento muito negativo
- Situação complexa (jurídico, financeiro)

---

### 13. HandoffKeywordProcessor (priority: 55)

**Arquivo:** `processors/handoff.py` (classe `HandoffKeywordProcessor`)

**Função:** Processa confirmações de divulgadores via WhatsApp.

**Comportamento:**
- Detecta se remetente tem handoff pendente
- Reconhece keywords: "confirmado", "fechou", "não deu", etc
- Processa confirmação sem necessidade de clicar link
- Retorna agradecimento
- **Para o pipeline** (não processa LLM)

**Stop Condition:** Sim (se detectar keyword)

**Sprints:** 20 (Handoff Keywords), 44 (Otimização regex)

**Keywords:**
- Confirmado: "confirmado", "fechou", "fechado", "pode confirmar"
- Recusa: "não fechou", "não deu", "desistiu", "cancelou"

**Otimização:** Regex patterns pré-compilados (Sprint 44 T06.6)

---

### 14. HumanControlProcessor (priority: 60)

**Arquivo:** `processors/human_control.py`

**Função:** Verifica se conversa está sob controle humano.

**Comportamento:**
- Verifica `conversa.controlled_by`
- Se `"human"`: sincroniza com Chatwoot e **para pipeline**
- Se `"ai"`: continua normalmente

**Stop Condition:** Sim (se controle humano)

**Sprints:** 2 (Vagas & Chatwoot)

---

### REMOVIDO: ForaHorarioProcessor

**Arquivo:** `processors/fora_horario.py`

**Status:** REMOVIDO do pipeline em 31/12/2025

**Motivo:** Bug crítico - bloqueava TODAS as respostas fora do horário comercial, incluindo replies a mensagens do médico.

**Fix:** Julia responde 24/7 a mensagens inbound (médico mandou mensagem = Julia responde). Quiet hours aplicam APENAS a outbound proativo (campanhas, nudges, follow-ups).

**Código:** Arquivo mantido para referência histórica, mas não é registrado em `setup.py`.

---

## Core Processor

### LLMCoreProcessor

**Arquivo:** `core.py`

**Função:** Processa mensagem via agente Julia (Claude LLM).

**Comportamento:**
- Chama `processar_mensagem_completo()` do serviço agente
- Usa Haiku (80%) ou Sonnet (20%) conforme complexidade
- Integra com Policy Engine (Sprint 15)
- Propaga `policy_decision_id` para post-processors

**Input:**
- `context.mensagem_texto`
- `context.medico`
- `context.conversa`

**Output:**
- `ProcessorResult.response` (resposta do LLM)
- `context.metadata["policy_decision_id"]`
- `context.metadata["rule_matched"]`

**Sprints:** 1 (Core), 8 (Pipeline), 15 (Policy Engine), 16 (Policy Events)

---

## Pós-Processadores

Executados **após** o LLM gerar resposta. Ordem definida por `priority`.

### 1. ValidateOutputProcessor (priority: 5)

**Arquivo:** `post_processors.py`

**Função:** Valida resposta antes de enviar para garantir aderência à persona.

**Comportamento:**
- Detecta revelação de IA ("sou uma IA", "assistente virtual")
- Detecta formatos proibidos (bullets, markdown)
- Detecta linguagem corporativa/robotica
- **Tenta corrigir** automaticamente
- Se não conseguir corrigir: **bloqueia resposta** (retorna vazio)

**Stop Condition:** Sim (se resposta bloqueada)

**Sprints:** 3 (Persona & Timing), 4 (Métricas)

**Crítico:** Esta é a última linha de defesa contra quebra de persona.

---

### 2. TimingProcessor (priority: 10)

**Arquivo:** `post_processors.py`

**Função:** Aplica delay humanizado antes de enviar.

**Comportamento:**
- Usa `delay_engine` para calcular delay inteligente
- Contextos:
  - Reply direto/aceite: 0-3s (urgente)
  - Oferta/followup: 15-120s (proativo)
  - Campanha: 60-180s (frio)
- Mostra "digitando..." nos últimos 5 segundos

**Stop Condition:** Não

**Sprints:** 3 (Timing), 22 (Responsividade Inteligente)

**Delay Calculation:**
```python
delay = await get_delay_seconds(
    mensagem=mensagem,
    outbound_ctx=context,
    tempo_processamento_s=tempo_processamento
)
```

---

### 3. SendMessageProcessor (priority: 20)

**Arquivo:** `post_processors.py`

**Função:** Envia mensagem via WhatsApp (Evolution/Z-API).

**Comportamento:**
- Salva interação de entrada ANTES (para `inbound_proof`)
- Cria contexto de REPLY com prova de inbound
- Envia via `enviar_resposta()` com guardrails
- Captura `chip_id` usado no envio
- Marca ACK se for mensagem fora do horário
- Emite evento `doctor_outbound`

**Stop Condition:** Sim (se guardrail bloquear)

**Sprints:** 18 (Auditoria), 22 (Responsividade), 41 (Chips Health)

**Guardrails Integration:** Sprint 18.1 P0

**Metrics:**
- `context.metadata["message_sent"] = True`
- `context.metadata["sent_message_id"]`
- `context.metadata["chip_id"]`

---

### 4. ChatwootResponseProcessor (priority: 25)

**Arquivo:** `post_processors.py`

**Função:** Sincroniza mensagens com Chatwoot (workaround para LID).

**Comportamento:**
- Envia mensagem do médico como `incoming`
- Envia resposta da Julia como `outgoing`
- Necessário porque integração Evolution-Chatwoot tem bugs com LID format

**Stop Condition:** Não

**Tolerância:** Erros não param o pipeline

---

### 5. SaveInteractionProcessor (priority: 30)

**Arquivo:** `post_processors.py`

**Função:** Persiste interações no banco de dados.

**Comportamento:**
- Salva interação de entrada (`tipo="entrada"`)
- Salva interação de saída (`tipo="saida"`)
- Atribui reply a campanha (Sprint 23 E02)
- Atualiza `policy_event` com `interaction_id` (Sprint 16 E08)
- Captura `chip_id` para rastreamento

**Stop Condition:** Não

**Tabela:** `interacoes`

**Sprints:** 8, 16, 23, 41

**Relacionamentos:**
- `campaign_replies` (atribuição a campanhas)
- `policy_events` (decisões do Policy Engine)

---

### 6. ExtractionProcessor (priority: 35)

**Arquivo:** `processors/extraction.py`

**Função:** Extrai dados estruturados de cada turno de conversa via LLM.

**Comportamento:**
- Extrai interesse, especialidade, região, preferências
- Detecta próximo passo sugerido
- Salva em `conversation_insights`
- Salva memórias RAG em `doctor_context`
- Atualiza dados do médico se confiança ≥0.7
- **Executa em background** (não bloqueia resposta)

**Stop Condition:** Não

**Sprints:** 53 (Discovery Intelligence Pipeline)

**Feature Flag:** `EXTRACTION_ENABLED=true`

**Auto-Update Threshold:** `EXTRACTION_AUTO_UPDATE_THRESHOLD=0.7`

**Tabelas:**
- `conversation_insights`
- `doctor_context` (memórias RAG)
- `clientes` (atualização de dados)

**Fault-Tolerant:** Erros são logados mas não interrompem pipeline.

---

### 7. MetricsProcessor (priority: 40)

**Arquivo:** `post_processors.py`

**Função:** Registra métricas da conversa.

**Comportamento:**
- Registra mensagem do médico
- Registra resposta da Julia com tempo de resposta
- Atualiza contadores e timestamps

**Stop Condition:** Não

**Tabela:** `metricas_conversa`

**Métricas:**
- `total_mensagens_medico`
- `total_mensagens_ai`
- `tempo_resposta_segundos`
- `ultima_mensagem_medico_at`
- `ultima_mensagem_ai_at`

---

## ProcessorContext

Objeto compartilhado entre todos os processadores, passado por referência.

### Campos Principais

```python
@dataclass
class ProcessorContext:
    # Input obrigatório
    mensagem_raw: dict           # Payload original do webhook

    # Parseados por ParseMessageProcessor
    mensagem_texto: str = ""     # Texto da mensagem
    telefone: str = ""           # Telefone do remetente (normalizado)
    message_id: str = ""         # ID da mensagem WhatsApp
    tipo_mensagem: str = "texto" # texto, audio, imagem, documento, video

    # Carregados por LoadEntitiesProcessor
    medico: Optional[dict] = None     # Registro completo do médico
    conversa: Optional[dict] = None   # Registro completo da conversa

    # Gerado por LLMCoreProcessor
    resposta: Optional[str] = None    # Resposta do LLM

    # Metadata compartilhado (dict livre)
    metadata: dict = field(default_factory=dict)
```

### Metadata Comum

| Chave | Tipo | Quem Popula | Uso |
|-------|------|-------------|-----|
| `nome_contato` | str | ParseMessage | Nome do WhatsApp |
| `remote_jid` | str | ParseMessage | JID original (pode ser LID) |
| `chatwoot_conversation_id` | int | ParseMessage/ChatwootSync | ID da conversa Chatwoot |
| `chip_instance` | str | ChipMapping | Instância Evolution usada |
| `chip_id` | str | SendMessage | ID do chip no banco |
| `bot_detected` | bool | BotDetection | Médico mencionou bot |
| `message_truncated` | bool | LongMessage | Mensagem foi truncada |
| `optout` | bool | OptOut | Médico pediu opt-out |
| `handoff_trigger` | str | HandoffTrigger | Tipo de handoff |
| `human_control` | bool | HumanControl | Sob controle humano |
| `policy_decision_id` | str | LLMCore | ID da decisão do Policy Engine |
| `rule_matched` | str | LLMCore | Regra do Policy Engine aplicada |
| `message_sent` | bool | SendMessage | Mensagem foi enviada |
| `sent_message_id` | str | SendMessage | ID da msg enviada |
| `tempo_inicio` | float | MessageProcessor | Timestamp de início |
| `resposta_corrigida` | bool | ValidateOutput | Resposta foi corrigida |
| `resposta_bloqueada` | bool | ValidateOutput | Resposta foi bloqueada |
| `fora_horario` | bool | ForaHorario | Mensagem fora do horário |
| `inbound_interaction_id` | int | Extraction | ID da interação de entrada |
| `campanha_id` | str | (varies) | ID da campanha de origem |

### Métodos Imutáveis (Sprint 44 T03.2)

```python
# Atualizar campos (imutável)
new_context = context.with_updates(
    medico=medico,
    conversa=conversa
)

# Adicionar metadata (imutável)
new_context = context.add_metadata("tempo_inicio", time.time())

# Clonar
clone = context.clone()
```

**Nota:** Métodos mutáveis ainda funcionam (ex: `context.medico = medico`) mas estão deprecated para novos usos.

---

## ProcessorResult

Resultado retornado por cada processador.

```python
@dataclass
class ProcessorResult:
    success: bool = True              # Se processou com sucesso
    should_continue: bool = True      # Se deve continuar pipeline
    response: Optional[str] = None    # Resposta (se parar pipeline)
    error: Optional[str] = None       # Mensagem de erro
    metadata: dict = field(default_factory=dict)  # Metadata adicional
```

### Padrões de Uso

#### Continuar normalmente
```python
return ProcessorResult(success=True)
```

#### Parar pipeline sem resposta (silencioso)
```python
return ProcessorResult(
    success=True,
    should_continue=False,
    metadata={"motivo": "mensagem_grupo"}
)
```

#### Parar pipeline com resposta (ex: opt-out, media)
```python
return ProcessorResult(
    success=True,
    should_continue=False,
    response="Tudo bem! Pode me procurar quando quiser.",
    metadata={"optout": True}
)
```

#### Erro crítico (para pipeline)
```python
return ProcessorResult(
    success=False,
    should_continue=False,
    error="Erro ao buscar médico"
)
```

---

## Controle de Fluxo

### Early Exit

Quando um pré-processador retorna `should_continue=False` com `response`, o pipeline:

1. Pula o Core Processor (LLM)
2. Executa pós-processadores essenciais:
   - `SendMessage` (envia resposta)
   - `SaveInteraction` (persiste)
3. Pula pós-processadores não essenciais:
   - `Timing` (não precisa delay)
   - `Metrics` (já foi tratado)

### Fault Tolerance

Processadores podem ter diferentes níveis de tolerância a erro:

| Tipo | Comportamento | Exemplo |
|------|---------------|---------|
| Crítico | Erro para pipeline | `LoadEntitiesProcessor` |
| Não-crítico | Log warning, continua | `PresenceProcessor` |
| Background | Erro não afeta pipeline | `ChipMappingProcessor`, `ExtractionProcessor` |

### Background Tasks

Processadores que executam tarefas em background (usando `safe_create_task`):

- `ChipMappingProcessor` - Registro de chip
- `BusinessEventInboundProcessor` - Emissão de eventos
- `ExtractionProcessor` - Extração de dados

Vantagens:
- Não bloqueiam resposta ao médico
- Erros não afetam pipeline principal
- Melhor performance

---

## Orquestração (MessageProcessor)

**Arquivo:** `processor.py`

### Fluxo Completo

```python
async def process(self, mensagem_raw: dict) -> ProcessorResult:
    # 1. Criar contexto inicial
    context = ProcessorContext(mensagem_raw=mensagem_raw)

    # 2. FASE PRÉ-PROCESSADORES
    for processor in self.pre_processors:
        if not processor.should_run(context):
            continue

        result = await processor.process(context)

        if not result.success:
            return result  # Erro crítico

        if not result.should_continue:
            # Early exit - rodar pós-processadores essenciais
            if result.response:
                return await self._run_post_processors_on_early_exit(
                    context, result.response
                )
            return result

    # 3. FASE CORE (LLM)
    core_result = await self._core_processor.process(context)

    if not core_result.success:
        return core_result

    response = core_result.response or ""

    # 4. FASE PÓS-PROCESSADORES
    for processor in self.post_processors:
        if not processor.should_run(context):
            continue

        result = await processor.process(context, response)

        if not result.success:
            logger.warning(f"Post-processor {processor.name} falhou")
            continue  # Pós-processors não param pipeline

        if result.response:
            response = result.response

    return ProcessorResult(success=True, response=response)
```

### Adicionando Processadores

```python
from app.pipeline.setup import criar_pipeline

pipeline = criar_pipeline()

# Adicionar pré-processador
pipeline.add_pre_processor(MeuPreProcessor())

# Adicionar pós-processador
pipeline.add_post_processor(MeuPostProcessor())

# Processar mensagem
result = await pipeline.process(mensagem_raw)
```

---

## Configuração do Pipeline

**Arquivo:** `setup.py`

### criar_pipeline()

Função que configura o pipeline completo:

```python
def criar_pipeline() -> MessageProcessor:
    pipeline = MessageProcessor()

    # Pre-processadores (13 processadores)
    pipeline.add_pre_processor(IngestaoGrupoProcessor())       # 5
    pipeline.add_pre_processor(ParseMessageProcessor())        # 10
    pipeline.add_pre_processor(PresenceProcessor())            # 15
    pipeline.add_pre_processor(LoadEntitiesProcessor())        # 20
    pipeline.add_pre_processor(ChipMappingProcessor())         # 21
    pipeline.add_pre_processor(BusinessEventInboundProcessor())# 22
    pipeline.add_pre_processor(ChatwootSyncProcessor())        # 25
    pipeline.add_pre_processor(OptOutProcessor())              # 30
    # ForaHorarioProcessor REMOVIDO (31/12/2025)
    pipeline.add_pre_processor(BotDetectionProcessor())        # 35
    pipeline.add_pre_processor(MediaProcessor())               # 40
    pipeline.add_pre_processor(LongMessageProcessor())         # 45
    pipeline.add_pre_processor(HandoffTriggerProcessor())      # 50
    pipeline.add_pre_processor(HandoffKeywordProcessor())      # 55
    pipeline.add_pre_processor(HumanControlProcessor())        # 60

    # Core processor
    pipeline.set_core_processor(LLMCoreProcessor())

    # Pos-processadores (6+ processadores)
    pipeline.add_post_processor(ValidateOutputProcessor())     # 5
    pipeline.add_post_processor(TimingProcessor())             # 10
    pipeline.add_post_processor(SendMessageProcessor())        # 20
    pipeline.add_post_processor(ChatwootResponseProcessor())   # 25
    pipeline.add_post_processor(SaveInteractionProcessor())    # 30
    pipeline.add_post_processor(ExtractionProcessor())         # 35
    pipeline.add_post_processor(MetricsProcessor())            # 40

    return pipeline
```

### Instância Global

```python
# Importar instância já configurada
from app.pipeline.setup import message_pipeline

# Usar
result = await message_pipeline.process(mensagem_raw)
```

---

## Criando Novo Processador

### 1. Pré-Processador

```python
# app/pipeline/processors/meu_processor.py
import logging
from ..base import PreProcessor, ProcessorContext, ProcessorResult

logger = logging.getLogger(__name__)

class MeuProcessor(PreProcessor):
    """
    Descrição do que faz.

    Sprint X - Tarefa Y.

    Prioridade: XX (onde se encaixa)
    """

    name = "meu_processor"
    priority = 25  # Definir ordem

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        # Validação inicial
        if not context.mensagem_texto:
            return ProcessorResult(success=True)

        try:
            # Lógica do processador
            resultado = await processar_algo(context.mensagem_texto)

            # Modificar contexto
            context.metadata["meu_dado"] = resultado

            # Continuar normalmente
            return ProcessorResult(success=True)

        except Exception as e:
            logger.error(f"Erro no MeuProcessor: {e}")
            # Decidir: parar ou continuar?
            return ProcessorResult(success=False, error=str(e))

    def should_run(self, context: ProcessorContext) -> bool:
        """Condições para rodar este processador."""
        # Ex: só rodar se tiver médico identificado
        return context.medico is not None
```

### 2. Pós-Processador

```python
# app/pipeline/post_processors.py ou processors/meu_processor.py
from .base import PostProcessor, ProcessorContext, ProcessorResult

class MeuPostProcessor(PostProcessor):
    """
    Descrição do que faz.

    Prioridade: XX
    """

    name = "meu_post"
    priority = 25

    async def process(
        self,
        context: ProcessorContext,
        response: str
    ) -> ProcessorResult:
        if not response:
            return ProcessorResult(success=True, response=response)

        try:
            # Processar resposta
            nova_resposta = await processar_resposta(response)

            # Retornar com resposta modificada
            return ProcessorResult(success=True, response=nova_resposta)

        except Exception as e:
            logger.error(f"Erro no MeuPostProcessor: {e}")
            # Pós-processors geralmente não param pipeline
            return ProcessorResult(success=True, response=response)
```

### 3. Registrar no Pipeline

```python
# app/pipeline/setup.py
from .processors.meu_processor import MeuProcessor

def criar_pipeline() -> MessageProcessor:
    pipeline = MessageProcessor()

    # ... outros processadores ...
    pipeline.add_pre_processor(MeuProcessor())  # Ordem automática por priority
    # ... outros processadores ...

    return pipeline
```

### 4. Exportar (opcional)

```python
# app/pipeline/pre_processors.py
from .processors.meu_processor import MeuProcessor

__all__ = [
    # ... outros ...
    "MeuProcessor",
]
```

---

## Feature Flags e Configuração

### Variáveis de Ambiente

| Variável | Default | Onde Afeta | Uso |
|----------|---------|------------|-----|
| `MULTI_CHIP_ENABLED` | `false` | ChipMappingProcessor | Multi-chip tracking |
| `EXTRACTION_ENABLED` | `true` | ExtractionProcessor | Extração de dados |
| `EXTRACTION_AUTO_UPDATE_THRESHOLD` | `0.7` | ExtractionProcessor | Threshold para auto-update |

### Configuração Dinâmica (Banco)

Alguns processadores usam configuração do banco:

- **OptOutProcessor:** Template `mensagens_especiais.optout`
- **MediaProcessor:** Templates `mensagens_especiais.audio`, `imagem`, etc
- **HandoffKeywordProcessor:** Templates `confirmacao_aceite`, `confirmacao_recusa`

### Rollout de Features

Business Events usa rollout gradual:

```python
# Verificar se cliente está no rollout
should_emit = await should_emit_event(cliente_id, "doctor_inbound")

if should_emit:
    await emit_event(...)
```

---

## Error Handling

### Estratégias por Tipo

#### 1. Crítico (Para Pipeline)

Usado quando erro impede processamento:

```python
return ProcessorResult(
    success=False,
    should_continue=False,
    error="Erro ao buscar médico"
)
```

**Exemplos:**
- `ParseMessageProcessor` - Mensagem inválida
- `LoadEntitiesProcessor` - Falha ao buscar/criar médico

#### 2. Não-Crítico (Continua)

Usado quando erro não impede processamento:

```python
try:
    await fazer_algo()
except Exception as e:
    logger.warning(f"Erro não-crítico: {e}")
    # Continua normalmente

return ProcessorResult(success=True)
```

**Exemplos:**
- `PresenceProcessor` - Erro ao marcar como lida
- `ChatwootSyncProcessor` - Erro ao sincronizar IDs

#### 3. Background (Não Afeta)

Usado para tarefas que não devem bloquear:

```python
safe_create_task(
    self._processar_em_background(context),
    name="task_name"
)

return ProcessorResult(success=True)
```

**Exemplos:**
- `ChipMappingProcessor` - Registro de chip
- `BusinessEventInboundProcessor` - Emissão de eventos
- `ExtractionProcessor` - Extração de dados

### Logging Estruturado

```python
logger.info(
    f"Processador executado",
    extra={
        "processor": self.name,
        "cliente_id": context.medico.get("id"),
        "conversa_id": context.conversa.get("id"),
        "telefone_hash": context.telefone[-4:]
    }
)
```

---

## Performance

### Otimizações Implementadas

#### 1. Regex Pre-Compilation (Sprint 44 T06.6)

**HandoffKeywordProcessor:**

```python
# Padrões compilados no nível de classe (lazy init)
_PATTERNS_CONFIRMED = None

@classmethod
def _get_compiled_patterns(cls):
    if cls._PATTERNS_CONFIRMED is None:
        cls._PATTERNS_CONFIRMED = [
            re.compile(r"\bconfirmado\b", re.IGNORECASE),
            # ...
        ]
    return cls._PATTERNS_CONFIRMED
```

**Ganho:** ~40% mais rápido que compilar a cada chamada.

#### 2. Background Tasks

Processadores que não bloqueiam resposta:
- ChipMapping
- BusinessEvents
- Extraction

**Ganho:** Resposta 100-500ms mais rápida.

#### 3. Early Exit

Pipeline para antes do LLM quando possível:
- Opt-out → resposta template
- Mídia → resposta especial
- Handoff → sem resposta
- Controle humano → sem resposta

**Ganho:** Economia de chamada LLM (~$0.001/msg).

#### 4. Should Run Conditions

```python
def should_run(self, context: ProcessorContext) -> bool:
    # Pula se não tem dados necessários
    return bool(context.mensagem_texto and context.medico)
```

**Ganho:** Evita processamento desnecessário.

---

## Debugging

### Logs de Pipeline

```bash
# Ver fluxo completo
grep "Rodando pre:" logs/app.log
grep "Rodando pos:" logs/app.log

# Ver processadores que pararam pipeline
grep "Pipeline interrompido por" logs/app.log

# Ver early exits
grep "Rodando pos (early exit)" logs/app.log
```

### Metadata Tracking

Adicionar metadata para debugging:

```python
context.metadata["debug_info"] = {
    "processador": self.name,
    "timestamp": time.time(),
    "dados_extras": {...}
}
```

### Processar Mensagem Manualmente

```python
from app.pipeline.setup import message_pipeline
from app.pipeline.base import ProcessorContext

# Criar payload de teste
mensagem_raw = {
    "key": {"remoteJid": "5511999999999@s.whatsapp.net"},
    "message": {"conversation": "oi julia"},
    # ... outros campos
}

# Processar
result = await message_pipeline.process(mensagem_raw)

print(f"Success: {result.success}")
print(f"Response: {result.response}")
print(f"Metadata: {result.metadata}")
```

---

## Histórico de Mudanças

| Sprint | Mudança | Motivo |
|--------|---------|--------|
| 8 | Pipeline criado | Arquitetura modular |
| 15 | Policy Engine integration | Decisões baseadas em regras |
| 16 | Policy Events tracking | Auditoria de decisões |
| 17 | Business Events | Tracking de funil |
| 18 | Guardrails integration | Compliance e auditoria |
| 20 | HandoffKeywordProcessor | UX divulgadores |
| 22 | Delay inteligente | Timing humanizado |
| 23 | Campaign attribution | Tracking de campanhas |
| 26 | Multi-chip support | Escalabilidade WhatsApp |
| 41 | Chip health tracking | Observabilidade chips |
| 44 T03 | Módulos separados | Manutenibilidade |
| 44 T06.6 | Regex pre-compilation | Performance |
| 53 | ExtractionProcessor | Discovery intelligence |
| 31/12/2025 | REMOVIDO ForaHorarioProcessor | Bug crítico - bloqueava replies |

---

## Referências

### Código

- Pipeline: `app/pipeline/`
- Processadores: `app/pipeline/processors/`
- Setup: `app/pipeline/setup.py`
- Classes base: `app/pipeline/base.py`

### Documentação

- Agente Julia: `docs/julia/prompts/`
- Policy Engine: `planning/sprint-15/`
- Business Events: `planning/sprint-17/`
- Auditoria: `planning/sprint-18/`
- Extração: `planning/sprint-53/`

### Testes

- Testes de pipeline: `tests/pipeline/`
- Testes de processadores: `tests/pipeline/processors/`

---

## Próximos Passos

### Melhorias Planejadas

1. **Processador de Sentiment Analysis**
   - Detectar frustração antes de handoff
   - Priority: 48 (entre HandoffTrigger e HandoffKeyword)

2. **Processador de Rate Limiting**
   - Implementar rate limits por médico
   - Priority: 35 (junto com BotDetection)

3. **Processador de A/B Testing**
   - Testar variações de resposta
   - Post-processor priority: 8 (antes de ValidateOutput)

4. **Migration para Padrão Imutável**
   - Migrar todos processadores para usar `with_updates()`
   - Deprecar modificação direta de `context`

### Backlog Técnico

- [ ] Adicionar telemetria (OpenTelemetry)
- [ ] Melhorar error handling com retry policies
- [ ] Adicionar circuit breakers para serviços externos
- [ ] Implementar cache de resultados de processadores
- [ ] Adicionar testes de integração end-to-end
