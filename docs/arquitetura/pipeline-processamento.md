# Pipeline de Processamento

> Implementado na Sprint 8 - Memória & Pipeline

## Visão Geral

O pipeline de processamento é a arquitetura central que processa mensagens de entrada e gera respostas. Utiliza padrão Chain of Responsibility com pré-processadores, processamento core e pós-processadores.

## Arquitetura

```
Mensagem Recebida
       │
       ▼
┌──────────────────┐
│ Pre-Processors   │  ← Validação, contexto, detecção
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Core Processor   │  ← Agente LLM (Julia)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Post-Processors  │  ← Formatação, persistência
└────────┬─────────┘
         │
         ▼
    Resposta
```

## Estrutura de Arquivos

```
app/pipeline/
├── __init__.py          # Exports
├── base.py              # Classes base (Processor, Context)
├── core.py              # Orquestração do pipeline
├── processor.py         # ProcessorChain
├── pre_processors.py    # Pré-processadores (~32k linhas)
├── post_processors.py   # Pós-processadores (~17k linhas)
└── setup.py             # Configuração do pipeline
```

## Pré-Processadores

Executados **antes** do LLM processar a mensagem:

| Processador | Função |
|-------------|--------|
| `ValidationProcessor` | Valida estrutura da mensagem |
| `ContextLoader` | Carrega contexto do médico |
| `RateLimitChecker` | Verifica rate limits |
| `BotDetector` | Detecta mensagens de bot |
| `OptOutDetector` | Detecta opt-out |
| `HandoffChecker` | Verifica se está em handoff |
| `KnowledgeInjector` | Injeta conhecimento RAG |
| `ObjectionDetector` | Detecta objeções |
| `ProfileDetector` | Detecta perfil do médico |

## Pós-Processadores

Executados **após** o LLM gerar resposta:

| Processador | Função |
|-------------|--------|
| `ResponseFormatter` | Formata resposta (quebra mensagens) |
| `PersonaValidator` | Valida aderência à persona |
| `MetricsCollector` | Coleta métricas da conversa |
| `EventEmitter` | Emite business events |
| `PersistenceHandler` | Salva interação no banco |
| `NotificationSender` | Envia notificações (Slack, etc) |

## Uso

### Processando Mensagem

```python
from app.pipeline.core import process_message
from app.pipeline.setup import create_default_pipeline

pipeline = create_default_pipeline()

result = await pipeline.process(
    message=message_content,
    cliente_id=cliente_id,
    conversation_id=conversation_id
)
```

### Adicionando Processador Customizado

```python
from app.pipeline.base import Processor, ProcessorContext

class MyProcessor(Processor):
    async def process(self, context: ProcessorContext) -> ProcessorContext:
        # Sua lógica aqui
        context.metadata["my_data"] = "value"
        return context

# Registrar no pipeline
pipeline.add_pre_processor(MyProcessor())
```

## ProcessorContext

Objeto compartilhado entre todos os processadores:

```python
@dataclass
class ProcessorContext:
    message: str                    # Mensagem original
    cliente_id: str                 # ID do médico
    conversation_id: str            # ID da conversa

    # Enriquecido pelos processadores
    doctor_context: dict = None     # Contexto do médico
    knowledge_chunks: list = None   # Conhecimento RAG
    detected_objection: str = None  # Objeção detectada
    detected_profile: str = None    # Perfil detectado

    # Resultado
    response: str = None            # Resposta do LLM
    tool_calls: list = None         # Tools chamadas

    # Controle de fluxo
    should_respond: bool = True     # Se deve responder
    skip_reason: str = None         # Motivo de pular
    metadata: dict = field(default_factory=dict)
```

## Controle de Fluxo

Um processador pode interromper o fluxo:

```python
class RateLimitProcessor(Processor):
    async def process(self, context: ProcessorContext) -> ProcessorContext:
        if await self.is_rate_limited(context.cliente_id):
            context.should_respond = False
            context.skip_reason = "rate_limit"
        return context
```

## Referências

- Sprint 8: `planning/sprint-8/`
- Sprint 15 (Policy Engine): `planning/sprint-15/`
- Código: `app/pipeline/`
