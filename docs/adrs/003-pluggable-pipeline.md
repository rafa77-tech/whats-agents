# ADR-003: Pipeline de Processamento Plugavel

- Status: Aceita
- Data: Janeiro 2026
- Sprint: Sprint 10 (Refatoracao e Divida Tecnica)
- Decisores: Equipe de Engenharia

## Contexto

O processamento de mensagens do Agente Julia cresceu organicamente durante as primeiras 9 sprints, acumulando complexidade:

**Estado original (Sprint 1-9):**
- Logica monolitica em `webhook.py` (500+ linhas)
- Todas as validacoes, deteccoes e processamentos em um unico arquivo
- Dificil de testar componentes isoladamente
- Dificil de adicionar novos detectors sem modificar codigo existente
- Duplicacao de logica entre webhook Evolution e Z-API

**Processamentos necessarios:**
1. Pre-processamento:
   - Deteccao de opt-out
   - Deteccao de bot (37 padroes)
   - Deteccao de handoff
   - Rate limiting
   - Validacao de horario comercial

2. Processamento core:
   - Chamada LLM com tools
   - Execucao de tools

3. Pos-processamento:
   - Humanizacao de resposta (delay, chunks)
   - Emissao de business events
   - Calculo de metricas
   - Sincronizacao com Chatwoot

**Problema**: Como adicionar novos processadores sem aumentar complexidade e acoplamento?

## Decisao

Implementar **pipeline de processamento plugavel** com arquitetura modular:

### Estrutura

```
app/pipeline/
├── base.py              # Classes abstratas
├── core.py              # Orquestrador principal
├── processor.py         # Interface base
├── setup.py             # Bootstrap do pipeline
├── pre_processors.py    # Pre-processadores
├── post_processors.py   # Pos-processadores
└── processors/          # Implementacoes concretas
    ├── opt_out_detector.py
    ├── bot_detector.py
    ├── handoff_detector.py
    ├── rate_limiter.py
    ├── business_hours_validator.py
    ├── humanizer.py
    └── event_emitter.py
```

### Interface Base

```python
class MessageProcessor(ABC):
    @abstractmethod
    async def process(self, context: ProcessingContext) -> ProcessingResult:
        """Processa mensagem e retorna resultado."""
        pass

    @abstractmethod
    def should_stop_pipeline(self, result: ProcessingResult) -> bool:
        """Determina se pipeline deve parar."""
        pass
```

### Pipeline Orchestrator

```python
class MessagePipeline:
    def __init__(self):
        self.pre_processors: List[MessageProcessor] = []
        self.core_processor: MessageProcessor = None
        self.post_processors: List[MessageProcessor] = []

    async def process(self, message: Message) -> Response:
        context = ProcessingContext(message)

        # Pre-processing
        for processor in self.pre_processors:
            result = await processor.process(context)
            if processor.should_stop_pipeline(result):
                return result

        # Core processing
        result = await self.core_processor.process(context)

        # Post-processing
        for processor in self.post_processors:
            await processor.process(context)

        return result
```

### Configuracao Plugavel

```python
# app/pipeline/setup.py
def setup_pipeline() -> MessagePipeline:
    pipeline = MessagePipeline()

    # Pre-processors (ordem importa)
    pipeline.add_pre_processor(OptOutDetector())
    pipeline.add_pre_processor(BotDetector())
    pipeline.add_pre_processor(HandoffDetector())
    pipeline.add_pre_processor(RateLimiter())
    pipeline.add_pre_processor(BusinessHoursValidator())

    # Core
    pipeline.set_core_processor(LLMProcessor())

    # Post-processors
    pipeline.add_post_processor(ResponseHumanizer())
    pipeline.add_post_processor(BusinessEventEmitter())
    pipeline.add_post_processor(MetricsCollector())

    return pipeline
```

**Beneficios:**
- Adicionar novo processor = criar classe + adicionar em `setup.py`
- Testar processor isoladamente
- Reordenar processors facilmente
- Desabilitar processor via feature flag
- Composicao > heranca

## Alternativas Consideradas

### 1. Chain of Responsibility Pattern (puro)
- **Pros**: Padrao classico, cada handler decide proximo
- **Cons**: Acoplamento entre handlers, dificil de testar
- **Rejeicao**: Pipeline com orquestrador central eh mais explicito

### 2. Event-Driven Architecture (pubsub)
- **Pros**: Desacoplamento total, facil adicionar listeners
- **Cons**: Complexidade alta, dificil rastrear fluxo, overhead de mensageria
- **Rejeicao**: Overkill para processamento sincrono

### 3. Decorator Pattern
- **Pros**: Composicao em runtime, flexivel
- **Cons**: Stack de decorators dificil de debugar, ordem implicita
- **Rejeicao**: Pipeline explicita ordem e dependencias

### 4. Manter monolitico com refactoring
- **Pros**: Simplicidade, sem overhead de abstrações
- **Cons**: Nao resolve problema de acoplamento e testabilidade
- **Rejeicao**: Nao escala com crescimento de features

## Consequencias

### Positivas

1. **Testabilidade**
   - Testar cada processor isoladamente
   - Mockar dependencies facilmente
   - Unit tests < 100 linhas por processor

2. **Extensibilidade**
   - Adicionar detector de objecao: criar classe + registrar
   - Adicionar policy engine: novo post-processor
   - Feature flags para ativar/desativar processors

3. **Reusabilidade**
   - Processors compartilhados entre webhooks (Evolution, Z-API, Slack)
   - Mesmo BotDetector usado em diferentes contextos

4. **Manutencao**
   - Bug em rate limiting? Isolado em `rate_limiter.py`
   - Melhorar humanizacao? Apenas `humanizer.py`
   - Cada arquivo < 200 linhas

5. **Visibilidade**
   - Logging estruturado por processor
   - Metricas por etapa (latencia de cada processor)
   - Debugging simplificado

### Negativas

1. **Complexidade inicial**
   - Mais arquivos para entender
   - Abstractions overhead (interfaces, base classes)
   - Curva de aprendizado para novos desenvolvedores
   - Mitigacao: Documentacao clara, exemplos

2. **Performance overhead**
   - Loop sobre lista de processors
   - Context object copying
   - Estimativa: +50ms por mensagem (negligivel vs 2s de LLM)
   - Mitigacao: Async/await, evitar I/O desnecessario

3. **Debugging multi-camada**
   - Stack trace mais longo
   - Precisa rastrear por varios processors
   - Mitigacao: Logging estruturado com trace_id

### Mitigacoes

1. **Documentacao**
   - Diagrama de pipeline em `docs/arquitetura/pipeline.md`
   - Exemplo de novo processor em docstring

2. **Logging estruturado**
   - Cada processor loga entrada/saida
   - Trace ID para rastrear mensagem end-to-end

3. **Metricas**
   - Latencia por processor
   - Taxa de stop (quantos processors param pipeline)

## Implementacao

### Exemplo: BotDetector

```python
class BotDetector(MessageProcessor):
    def __init__(self):
        self.patterns = load_bot_patterns()

    async def process(self, context: ProcessingContext) -> ProcessingResult:
        texto = context.message.texto
        for pattern in self.patterns:
            if pattern.matches(texto):
                logger.warning("Bot detectado", extra={
                    "pattern": pattern.name,
                    "medico_id": context.medico_id
                })
                return ProcessingResult(
                    should_stop=True,
                    reason="bot_detected",
                    metadata={"pattern": pattern.name}
                )
        return ProcessingResult(should_stop=False)

    def should_stop_pipeline(self, result: ProcessingResult) -> bool:
        return result.should_stop
```

### Exemplo: Adicionar novo processor

```python
# 1. Criar processor
class ObjecaoDetector(MessageProcessor):
    async def process(self, context: ProcessingContext) -> ProcessingResult:
        objecao = detectar_objecao(context.message.texto)
        if objecao:
            context.metadata["objecao_tipo"] = objecao.tipo
        return ProcessingResult(should_stop=False)

    def should_stop_pipeline(self, result: ProcessingResult) -> bool:
        return False

# 2. Registrar em setup.py
pipeline.add_pre_processor(ObjecaoDetector())
```

## Metricas de Sucesso

1. **Reducao de 80% em linhas de `webhook.py`** (500 -> 100 linhas)
2. **Cobertura de testes > 85%** para cada processor
3. **Latencia adicional < 100ms** (overhead do pipeline)
4. **Novos processors adicionados em < 2h** (time to implement)

## Referencias

- Codigo: `app/pipeline/` (toda estrutura)
- Base classes: `app/pipeline/base.py`, `app/pipeline/processor.py`
- Setup: `app/pipeline/setup.py`
- Docs: `docs/arquitetura/pipeline.md` (se existir)
- Tests: `tests/unit/pipeline/`

## Historico de Mudancas

- **2026-01**: Sprint 10 - Implementacao inicial
- **2026-01**: Sprint 13 - Adicao de conhecimento dinamico processor
- **2026-01**: Sprint 17 - Adicao de business events processor
- **2026-02**: Atual - 12+ processors ativos, arquitetura estavel
