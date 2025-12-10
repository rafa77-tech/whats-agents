# Epic 03: Pipeline de Processamento

## Prioridade: P1 (Importante)

## Objetivo

> **Refatorar webhook monolitico em pipeline extensivel com pre e pos processadores.**

O `webhook.py` atual tem 436 linhas com toda a logica inline. Isso dificulta:
1. Adicionar novas funcionalidades
2. Testar componentes isolados
3. Entender o fluxo
4. Reutilizar logica

---

## Problema Atual

```python
# webhook.py - 436 linhas de:
async def processar_mensagem(data: dict):
    # 1. Parsear
    # 2. Marcar como lida
    # 3. Mostrar online
    # 4. Buscar medico
    # 5. Buscar conversa
    # 6. Salvar interacao
    # 7. Detectar bot
    # 8. Verificar opt-out
    # 8.5 Tratar audio/imagem/documento/video
    # 8.6 Tratar mensagem longa
    # 9. Verificar handoff
    # 10. Verificar controle IA
    # 11. Registrar metrica
    # 12. Calcular delay
    # 13. Gerar resposta
    # 14-18. Enviar e salvar...
```

Cada nova funcionalidade = mais `if` no meio do codigo.

---

## Arquitetura Proposta

```
┌─────────────────────────────────────────────────────────────────┐
│                        PIPELINE                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  MENSAGEM ENTRADA                                               │
│        │                                                         │
│        ▼                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              PRE-PROCESSADORES                           │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │   │
│  │  │ Parse   │→│ OptOut  │→│ Media   │→│ Handoff │→ ...  │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘       │   │
│  └─────────────────────────────────────────────────────────┘   │
│        │                                                         │
│        ▼ (se nao foi interrompido)                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              PROCESSADOR CORE (LLM)                      │   │
│  │  Monta contexto → Chama Claude → Processa tools          │   │
│  └─────────────────────────────────────────────────────────┘   │
│        │                                                         │
│        ▼                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              POS-PROCESSADORES                           │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │   │
│  │  │Validate │→│ Timing  │→│ Send    │→│ Save    │→ ...  │   │
│  │  │ Output  │ │         │ │         │ │         │       │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘       │   │
│  └─────────────────────────────────────────────────────────┘   │
│        │                                                         │
│        ▼                                                         │
│  MENSAGEM ENVIADA                                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Stories

---

# S8.E3.1 - Criar estrutura base do pipeline

## Objetivo

> **Criar classes base para processadores e pipeline.**

## Codigo Esperado

**Arquivo:** `app/pipeline/__init__.py`

```python
"""
Pipeline de processamento de mensagens.

Permite adicionar pre e pos processadores de forma modular.
"""
from .processor import MessageProcessor, ProcessorResult
from .base import PreProcessor, PostProcessor

__all__ = [
    "MessageProcessor",
    "ProcessorResult",
    "PreProcessor",
    "PostProcessor",
]
```

**Arquivo:** `app/pipeline/base.py`

```python
"""
Classes base para processadores.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProcessorContext:
    """Contexto compartilhado entre processadores."""
    mensagem_raw: dict                    # Payload original
    mensagem_texto: str = ""              # Texto da mensagem
    telefone: str = ""                    # Telefone do remetente
    message_id: str = ""                  # ID da mensagem
    tipo_mensagem: str = "texto"          # texto, audio, imagem, etc
    medico: Optional[dict] = None         # Dados do medico
    conversa: Optional[dict] = None       # Dados da conversa
    resposta: Optional[str] = None        # Resposta gerada
    metadata: dict = field(default_factory=dict)  # Dados extras


@dataclass
class ProcessorResult:
    """Resultado de um processador."""
    success: bool = True
    should_continue: bool = True          # Se deve continuar pipeline
    response: Optional[str] = None        # Resposta a enviar (se parar)
    error: Optional[str] = None           # Mensagem de erro
    metadata: dict = field(default_factory=dict)


class PreProcessor(ABC):
    """
    Base para pre-processadores.

    Pre-processadores rodam ANTES do LLM e podem:
    - Modificar a mensagem
    - Interromper o pipeline (retornando resposta)
    - Adicionar metadata ao contexto
    """

    name: str = "base_preprocessor"
    priority: int = 100  # Menor = roda primeiro

    @abstractmethod
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        """
        Processa o contexto.

        Args:
            context: Contexto atual do pipeline

        Returns:
            ProcessorResult indicando se deve continuar
        """
        pass

    def should_run(self, context: ProcessorContext) -> bool:
        """
        Verifica se este processador deve rodar.

        Override para adicionar condicoes.
        """
        return True


class PostProcessor(ABC):
    """
    Base para pos-processadores.

    Pos-processadores rodam DEPOIS do LLM e podem:
    - Modificar a resposta
    - Validar a resposta
    - Executar acoes (enviar, salvar)
    """

    name: str = "base_postprocessor"
    priority: int = 100

    @abstractmethod
    async def process(
        self,
        context: ProcessorContext,
        response: str
    ) -> ProcessorResult:
        """
        Processa a resposta.

        Args:
            context: Contexto do pipeline
            response: Resposta gerada pelo LLM

        Returns:
            ProcessorResult com resposta possivelmente modificada
        """
        pass

    def should_run(self, context: ProcessorContext) -> bool:
        """Verifica se este processador deve rodar."""
        return True
```

**Arquivo:** `app/pipeline/processor.py`

```python
"""
Processador principal de mensagens.
"""
import logging
from typing import Optional

from .base import (
    ProcessorContext,
    ProcessorResult,
    PreProcessor,
    PostProcessor
)

logger = logging.getLogger(__name__)


class MessageProcessor:
    """
    Orquestra o pipeline de processamento de mensagens.

    Uso:
        processor = MessageProcessor()
        processor.add_pre_processor(OptOutProcessor())
        processor.add_pre_processor(MediaProcessor())
        processor.add_post_processor(ValidateOutputProcessor())
        processor.add_post_processor(SendMessageProcessor())

        result = await processor.process(mensagem)
    """

    def __init__(self):
        self.pre_processors: list[PreProcessor] = []
        self.post_processors: list[PostProcessor] = []
        self._core_processor = None

    def add_pre_processor(self, processor: PreProcessor) -> "MessageProcessor":
        """Adiciona pre-processador e reordena por prioridade."""
        self.pre_processors.append(processor)
        self.pre_processors.sort(key=lambda p: p.priority)
        return self

    def add_post_processor(self, processor: PostProcessor) -> "MessageProcessor":
        """Adiciona pos-processador e reordena por prioridade."""
        self.post_processors.append(processor)
        self.post_processors.sort(key=lambda p: p.priority)
        return self

    def set_core_processor(self, processor) -> "MessageProcessor":
        """Define o processador core (LLM)."""
        self._core_processor = processor
        return self

    async def process(self, mensagem_raw: dict) -> ProcessorResult:
        """
        Processa mensagem pelo pipeline completo.

        Args:
            mensagem_raw: Payload da mensagem (webhook)

        Returns:
            ProcessorResult final
        """
        # Criar contexto inicial
        context = ProcessorContext(mensagem_raw=mensagem_raw)

        try:
            # FASE 1: Pre-processadores
            logger.debug(f"Iniciando {len(self.pre_processors)} pre-processadores")

            for processor in self.pre_processors:
                if not processor.should_run(context):
                    logger.debug(f"Pulando {processor.name}")
                    continue

                logger.debug(f"Rodando pre: {processor.name}")
                result = await processor.process(context)

                if not result.success:
                    logger.warning(f"Pre-processor {processor.name} falhou: {result.error}")
                    return result

                if not result.should_continue:
                    logger.info(f"Pipeline interrompido por {processor.name}")
                    return result

            # FASE 2: Processador core (LLM)
            if self._core_processor is None:
                logger.error("Core processor nao configurado")
                return ProcessorResult(
                    success=False,
                    error="Core processor nao configurado"
                )

            logger.debug("Rodando core processor")
            core_result = await self._core_processor.process(context)

            if not core_result.success:
                logger.error(f"Core processor falhou: {core_result.error}")
                return core_result

            response = core_result.response or ""

            # FASE 3: Pos-processadores
            logger.debug(f"Iniciando {len(self.post_processors)} pos-processadores")

            for processor in self.post_processors:
                if not processor.should_run(context):
                    logger.debug(f"Pulando {processor.name}")
                    continue

                logger.debug(f"Rodando pos: {processor.name}")
                result = await processor.process(context, response)

                if not result.success:
                    logger.warning(f"Pos-processor {processor.name} falhou: {result.error}")
                    # Pos-processors podem falhar sem parar tudo
                    continue

                # Atualizar resposta se modificada
                if result.response:
                    response = result.response

            # Sucesso
            return ProcessorResult(
                success=True,
                response=response
            )

        except Exception as e:
            logger.error(f"Erro no pipeline: {e}", exc_info=True)
            return ProcessorResult(
                success=False,
                error=str(e)
            )
```

## Criterios de Aceite

1. **Classes base funcionais:** PreProcessor e PostProcessor abstratas
2. **Contexto compartilhado:** ProcessorContext passa dados entre processadores
3. **Prioridade respeitada:** Processadores rodam em ordem de prioridade
4. **Interrupção funciona:** should_continue=False para o pipeline
5. **Fluent API:** add_pre_processor retorna self para encadeamento

## DoD

- [ ] Arquivo `app/pipeline/__init__.py` criado
- [ ] Arquivo `app/pipeline/base.py` criado
- [ ] Arquivo `app/pipeline/processor.py` criado
- [ ] Classes ProcessorContext e ProcessorResult funcionais
- [ ] Classes PreProcessor e PostProcessor abstratas
- [ ] MessageProcessor orquestra o pipeline
- [ ] Prioridade ordena processadores

---

# S8.E3.2 - Criar pre-processadores

## Objetivo

> **Extrair logica de pre-processamento do webhook para processadores modulares.**

## Codigo Esperado

**Arquivo:** `app/pipeline/pre_processors.py`

```python
"""
Pre-processadores do pipeline.
"""
import logging
from typing import Optional

from .base import PreProcessor, ProcessorContext, ProcessorResult
from app.services.parser import parsear_mensagem, deve_processar
from app.services.medico import buscar_ou_criar_medico
from app.services.conversa import buscar_ou_criar_conversa
from app.services.optout import detectar_optout, processar_optout, MENSAGEM_CONFIRMACAO_OPTOUT
from app.services.handoff_detector import detectar_trigger_handoff
from app.services.whatsapp import evolution, mostrar_online

logger = logging.getLogger(__name__)


class ParseMessageProcessor(PreProcessor):
    """
    Parseia mensagem do webhook da Evolution.

    Prioridade: 10 (roda primeiro)
    """
    name = "parse_message"
    priority = 10

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        mensagem = parsear_mensagem(context.mensagem_raw)

        if not mensagem:
            return ProcessorResult(
                success=False,
                should_continue=False,
                error="Mensagem nao pode ser parseada"
            )

        # Verificar se deve processar
        if not deve_processar(mensagem):
            return ProcessorResult(
                success=True,
                should_continue=False,  # Para silenciosamente
                metadata={"motivo": "mensagem ignorada (propria/grupo/status)"}
            )

        # Popular contexto
        context.mensagem_texto = mensagem.texto or ""
        context.telefone = mensagem.telefone
        context.message_id = mensagem.message_id
        context.tipo_mensagem = mensagem.tipo
        context.metadata["nome_contato"] = mensagem.nome_contato

        return ProcessorResult(success=True)


class LoadEntitiesProcessor(PreProcessor):
    """
    Carrega medico e conversa do banco.

    Prioridade: 20
    """
    name = "load_entities"
    priority = 20

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        # Buscar/criar medico
        medico = await buscar_ou_criar_medico(
            telefone=context.telefone,
            nome_whatsapp=context.metadata.get("nome_contato")
        )

        if not medico:
            return ProcessorResult(
                success=False,
                should_continue=False,
                error="Erro ao buscar/criar medico"
            )

        context.medico = medico

        # Buscar/criar conversa
        conversa = await buscar_ou_criar_conversa(cliente_id=medico["id"])

        if not conversa:
            return ProcessorResult(
                success=False,
                should_continue=False,
                error="Erro ao buscar/criar conversa"
            )

        context.conversa = conversa

        return ProcessorResult(success=True)


class OptOutProcessor(PreProcessor):
    """
    Detecta e processa pedidos de opt-out.

    Prioridade: 30
    """
    name = "optout"
    priority = 30

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        if not context.mensagem_texto:
            return ProcessorResult(success=True)

        is_optout, _ = detectar_optout(context.mensagem_texto)

        if not is_optout:
            return ProcessorResult(success=True)

        logger.info(f"Opt-out detectado para {context.telefone[:8]}...")

        # Processar opt-out
        sucesso = await processar_optout(
            cliente_id=context.medico["id"],
            telefone=context.telefone
        )

        if sucesso:
            return ProcessorResult(
                success=True,
                should_continue=False,  # Para o pipeline
                response=MENSAGEM_CONFIRMACAO_OPTOUT,
                metadata={"optout": True}
            )

        return ProcessorResult(success=True)


class MediaProcessor(PreProcessor):
    """
    Trata mensagens de midia (audio, imagem, documento, video).

    Prioridade: 40
    """
    name = "media"
    priority = 40

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        from app.services.respostas_especiais import (
            obter_resposta_audio,
            obter_resposta_imagem,
            obter_resposta_documento,
            obter_resposta_video
        )

        tipo = context.tipo_mensagem

        if tipo == "texto":
            return ProcessorResult(success=True)

        resposta = None

        if tipo == "audio":
            resposta = obter_resposta_audio()
        elif tipo == "imagem":
            resposta = obter_resposta_imagem(context.mensagem_texto)
        elif tipo == "documento":
            resposta = obter_resposta_documento()
        elif tipo == "video":
            resposta = obter_resposta_video()

        if resposta:
            return ProcessorResult(
                success=True,
                should_continue=False,
                response=resposta,
                metadata={"media_type": tipo}
            )

        return ProcessorResult(success=True)


class HandoffTriggerProcessor(PreProcessor):
    """
    Detecta triggers de handoff para humano.

    Prioridade: 50
    """
    name = "handoff_trigger"
    priority = 50

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        if not context.mensagem_texto:
            return ProcessorResult(success=True)

        trigger = detectar_trigger_handoff(context.mensagem_texto)

        if not trigger:
            return ProcessorResult(success=True)

        logger.info(f"Trigger de handoff detectado: {trigger['tipo']}")

        from app.services.handoff import iniciar_handoff

        await iniciar_handoff(
            conversa_id=context.conversa["id"],
            cliente_id=context.medico["id"],
            motivo=trigger["motivo"],
            trigger_type=trigger["tipo"]
        )

        return ProcessorResult(
            success=True,
            should_continue=False,  # Nao gera resposta automatica
            metadata={"handoff_trigger": trigger["tipo"]}
        )


class HumanControlProcessor(PreProcessor):
    """
    Verifica se conversa esta sob controle humano.

    Prioridade: 60
    """
    name = "human_control"
    priority = 60

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        if context.conversa.get("controlled_by") == "ai":
            return ProcessorResult(success=True)

        logger.info("Conversa sob controle humano, nao gerando resposta")

        # Sincronizar com Chatwoot para gestor ver
        from app.services.chatwoot import chatwoot_service

        if context.conversa.get("chatwoot_conversation_id") and chatwoot_service.configurado:
            try:
                await chatwoot_service.enviar_mensagem(
                    conversation_id=context.conversa["chatwoot_conversation_id"],
                    content=context.mensagem_texto or "[midia]",
                    message_type="incoming"
                )
            except Exception as e:
                logger.warning(f"Erro ao sincronizar com Chatwoot: {e}")

        return ProcessorResult(
            success=True,
            should_continue=False,
            metadata={"human_control": True}
        )


class PresenceProcessor(PreProcessor):
    """
    Envia presenca (online, digitando) e marca como lida.

    Prioridade: 15 (logo apos parse)
    """
    name = "presence"
    priority = 15

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        try:
            # Marcar como lida
            await evolution.marcar_como_lida(
                context.telefone,
                context.message_id
            )

            # Mostrar online
            await mostrar_online(context.telefone)

        except Exception as e:
            logger.warning(f"Erro ao enviar presenca: {e}")
            # Nao para o pipeline por isso

        return ProcessorResult(success=True)
```

## Criterios de Aceite

1. **ParseMessageProcessor:** Extrai dados da mensagem
2. **LoadEntitiesProcessor:** Carrega medico e conversa
3. **OptOutProcessor:** Detecta e processa opt-out
4. **MediaProcessor:** Trata audio/imagem/documento/video
5. **HandoffTriggerProcessor:** Detecta triggers de handoff
6. **HumanControlProcessor:** Verifica controle humano
7. **PresenceProcessor:** Marca lida e mostra online
8. **Prioridades corretas:** Ordem faz sentido

## DoD

- [ ] ParseMessageProcessor implementado
- [ ] LoadEntitiesProcessor implementado
- [ ] OptOutProcessor implementado
- [ ] MediaProcessor implementado
- [ ] HandoffTriggerProcessor implementado
- [ ] HumanControlProcessor implementado
- [ ] PresenceProcessor implementado
- [ ] Cada processador tem prioridade definida
- [ ] Cada processador pode interromper pipeline se necessario

---

# S8.E3.3 - Criar core processor (LLM)

## Objetivo

> **Extrair logica de geracao de resposta para core processor.**

## Codigo Esperado

**Arquivo:** `app/pipeline/core.py`

```python
"""
Core processor - geracao de resposta via LLM.
"""
import logging

from .base import ProcessorContext, ProcessorResult
from app.services.agente import processar_mensagem_completo

logger = logging.getLogger(__name__)


class LLMCoreProcessor:
    """
    Processador core que chama o LLM para gerar resposta.
    """

    name = "llm_core"

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        """
        Gera resposta usando o agente Julia.
        """
        try:
            resposta = await processar_mensagem_completo(
                mensagem_texto=context.mensagem_texto,
                medico=context.medico,
                conversa=context.conversa,
                vagas=None  # TODO: buscar vagas relevantes
            )

            if not resposta:
                logger.warning("Julia nao gerou resposta")
                return ProcessorResult(
                    success=True,
                    response=None,
                    metadata={"no_response": True}
                )

            return ProcessorResult(
                success=True,
                response=resposta
            )

        except Exception as e:
            logger.error(f"Erro no core processor: {e}", exc_info=True)
            return ProcessorResult(
                success=False,
                error=str(e)
            )
```

## DoD

- [ ] LLMCoreProcessor implementado
- [ ] Chama `processar_mensagem_completo` existente
- [ ] Trata caso de resposta vazia
- [ ] Trata excecoes graciosamente

---

# S8.E3.4 - Criar pos-processadores

## Objetivo

> **Criar processadores para validacao, timing, envio e salvamento.**

## Codigo Esperado

**Arquivo:** `app/pipeline/post_processors.py`

```python
"""
Pos-processadores do pipeline.
"""
import asyncio
import logging
import time

from .base import PostProcessor, ProcessorContext, ProcessorResult
from app.services.timing import calcular_delay_resposta
from app.services.agente import enviar_resposta
from app.services.interacao import salvar_interacao
from app.services.metricas import metricas_service
from app.services.whatsapp import mostrar_digitando

logger = logging.getLogger(__name__)


class TimingProcessor(PostProcessor):
    """
    Aplica delay humanizado antes de enviar.

    Prioridade: 10 (roda primeiro)
    """
    name = "timing"
    priority = 10

    async def process(
        self,
        context: ProcessorContext,
        response: str
    ) -> ProcessorResult:
        if not response:
            return ProcessorResult(success=True, response=response)

        # Calcular delay
        delay = calcular_delay_resposta(context.mensagem_texto)
        tempo_inicio = context.metadata.get("tempo_inicio", time.time())
        tempo_processamento = time.time() - tempo_inicio
        delay_restante = max(0, delay - tempo_processamento)

        logger.debug(f"Delay: {delay:.1f}s, processamento: {tempo_processamento:.1f}s, restante: {delay_restante:.1f}s")

        # Aguardar e mostrar digitando
        if delay_restante > 5:
            await asyncio.sleep(delay_restante - 5)
            await mostrar_digitando(context.telefone)
            await asyncio.sleep(5)
        elif delay_restante > 0:
            await asyncio.sleep(delay_restante)
            await mostrar_digitando(context.telefone)

        return ProcessorResult(success=True, response=response)


class SendMessageProcessor(PostProcessor):
    """
    Envia mensagem via WhatsApp.

    Prioridade: 20
    """
    name = "send_message"
    priority = 20

    async def process(
        self,
        context: ProcessorContext,
        response: str
    ) -> ProcessorResult:
        if not response:
            return ProcessorResult(success=True, response=response)

        resultado = await enviar_resposta(
            telefone=context.telefone,
            resposta=response
        )

        if resultado:
            context.metadata["message_sent"] = True
            context.metadata["sent_message_id"] = resultado.get("key", {}).get("id")
            logger.info(f"Mensagem enviada para {context.telefone[:8]}...")
        else:
            logger.error("Falha ao enviar mensagem")
            return ProcessorResult(
                success=False,
                error="Falha ao enviar mensagem"
            )

        return ProcessorResult(success=True, response=response)


class SaveInteractionProcessor(PostProcessor):
    """
    Salva interacoes no banco.

    Prioridade: 30
    """
    name = "save_interaction"
    priority = 30

    async def process(
        self,
        context: ProcessorContext,
        response: str
    ) -> ProcessorResult:
        try:
            # Salvar interacao de entrada (se ainda nao salvou)
            if not context.metadata.get("entrada_salva"):
                await salvar_interacao(
                    conversa_id=context.conversa["id"],
                    cliente_id=context.medico["id"],
                    tipo="entrada",
                    conteudo=context.mensagem_texto or "[midia]",
                    autor_tipo="medico",
                    message_id=context.message_id
                )
                context.metadata["entrada_salva"] = True

            # Salvar interacao de saida (se enviou)
            if response and context.metadata.get("message_sent"):
                await salvar_interacao(
                    conversa_id=context.conversa["id"],
                    cliente_id=context.medico["id"],
                    tipo="saida",
                    conteudo=response,
                    autor_tipo="julia",
                    message_id=context.metadata.get("sent_message_id")
                )

            logger.debug("Interacoes salvas")

        except Exception as e:
            logger.error(f"Erro ao salvar interacoes: {e}")
            # Nao para o pipeline por isso

        return ProcessorResult(success=True, response=response)


class MetricsProcessor(PostProcessor):
    """
    Registra metricas da conversa.

    Prioridade: 40
    """
    name = "metrics"
    priority = 40

    async def process(
        self,
        context: ProcessorContext,
        response: str
    ) -> ProcessorResult:
        try:
            tempo_inicio = context.metadata.get("tempo_inicio", time.time())
            tempo_resposta = time.time() - tempo_inicio

            # Registrar mensagem do medico
            await metricas_service.registrar_mensagem(
                conversa_id=context.conversa["id"],
                origem="medico"
            )

            # Registrar resposta da Julia
            if response:
                await metricas_service.registrar_mensagem(
                    conversa_id=context.conversa["id"],
                    origem="ai",
                    tempo_resposta_segundos=tempo_resposta
                )

        except Exception as e:
            logger.warning(f"Erro ao registrar metricas: {e}")

        return ProcessorResult(success=True, response=response)
```

## Criterios de Aceite

1. **TimingProcessor:** Aplica delay humanizado
2. **SendMessageProcessor:** Envia via Evolution API
3. **SaveInteractionProcessor:** Salva entrada e saida
4. **MetricsProcessor:** Registra metricas
5. **Prioridades corretas:** Timing → Send → Save → Metrics

## DoD

- [ ] TimingProcessor implementado
- [ ] SendMessageProcessor implementado
- [ ] SaveInteractionProcessor implementado
- [ ] MetricsProcessor implementado
- [ ] Erros nao quebram pipeline
- [ ] Logs adequados

---

# S8.E3.5 - Configurar pipeline no webhook

## Objetivo

> **Substituir logica inline do webhook pelo pipeline configurado.**

## Codigo Esperado

**Arquivo:** `app/pipeline/setup.py`

```python
"""
Configuracao do pipeline de mensagens.
"""
from .processor import MessageProcessor
from .core import LLMCoreProcessor
from .pre_processors import (
    ParseMessageProcessor,
    PresenceProcessor,
    LoadEntitiesProcessor,
    OptOutProcessor,
    MediaProcessor,
    HandoffTriggerProcessor,
    HumanControlProcessor,
)
from .post_processors import (
    TimingProcessor,
    SendMessageProcessor,
    SaveInteractionProcessor,
    MetricsProcessor,
)


def criar_pipeline() -> MessageProcessor:
    """
    Cria e configura o pipeline de mensagens.

    Returns:
        MessageProcessor configurado
    """
    pipeline = MessageProcessor()

    # Pre-processadores (ordem por prioridade)
    pipeline.add_pre_processor(ParseMessageProcessor())      # 10
    pipeline.add_pre_processor(PresenceProcessor())          # 15
    pipeline.add_pre_processor(LoadEntitiesProcessor())      # 20
    pipeline.add_pre_processor(OptOutProcessor())            # 30
    pipeline.add_pre_processor(MediaProcessor())             # 40
    pipeline.add_pre_processor(HandoffTriggerProcessor())    # 50
    pipeline.add_pre_processor(HumanControlProcessor())      # 60

    # Core processor
    pipeline.set_core_processor(LLMCoreProcessor())

    # Pos-processadores (ordem por prioridade)
    pipeline.add_post_processor(TimingProcessor())           # 10
    pipeline.add_post_processor(SendMessageProcessor())      # 20
    pipeline.add_post_processor(SaveInteractionProcessor())  # 30
    pipeline.add_post_processor(MetricsProcessor())          # 40

    return pipeline


# Instancia global do pipeline
message_pipeline = criar_pipeline()
```

**Arquivo:** `app/api/routes/webhook.py` (simplificado)

```python
"""
Endpoints de webhook para integracoes externas.
"""
import time
from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import JSONResponse
import logging

from app.pipeline.setup import message_pipeline
from app.pipeline.base import ProcessorContext

router = APIRouter(prefix="/webhook", tags=["Webhooks"])
logger = logging.getLogger(__name__)


@router.post("/evolution")
async def evolution_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Recebe webhooks da Evolution API.
    """
    try:
        payload = await request.json()
        logger.info(f"Webhook Evolution recebido: {payload.get('event')}")

        event = payload.get("event")

        if event == "messages.upsert":
            background_tasks.add_task(processar_mensagem_pipeline, payload.get("data", {}))
            logger.info("Mensagem agendada para processamento")

        elif event == "connection.update":
            logger.info(f"Status conexao: {payload.get('data')}")

        return JSONResponse({"status": "received"})

    except Exception as e:
        logger.error(f"Erro no webhook: {str(e)}")
        return JSONResponse({"status": "error", "message": str(e)})


async def processar_mensagem_pipeline(data: dict):
    """
    Processa mensagem usando o pipeline.
    """
    try:
        result = await message_pipeline.process(data)

        if not result.success:
            logger.error(f"Pipeline falhou: {result.error}")
        elif result.response:
            logger.info(f"Pipeline concluido com resposta")
        else:
            logger.info(f"Pipeline concluido sem resposta")

    except Exception as e:
        logger.error(f"Erro no pipeline: {e}", exc_info=True)
```

## Criterios de Aceite

1. **Pipeline configurado:** Todos os processadores registrados
2. **Webhook simplificado:** <50 linhas
3. **Funcionalidade mantida:** Tudo que funcionava continua funcionando
4. **Logs claros:** Mostra fluxo do pipeline

## DoD

- [ ] `criar_pipeline()` configura todos os processadores
- [ ] `message_pipeline` e instancia global
- [ ] `webhook.py` usa pipeline (< 50 linhas)
- [ ] Funcionalidade antiga funciona via pipeline
- [ ] Logs mostram qual processador esta rodando

---

# S8.E3.6 - Testes de regressao

## Objetivo

> **Garantir que refatoracao nao quebrou funcionalidades.**

## Codigo Esperado

**Arquivo:** `tests/test_pipeline.py`

```python
"""
Testes do pipeline de processamento.
"""
import pytest
from unittest.mock import AsyncMock, patch

from app.pipeline.setup import criar_pipeline, message_pipeline
from app.pipeline.base import ProcessorContext, ProcessorResult


class TestPipelineStructure:
    """Testes de estrutura do pipeline."""

    def test_pipeline_tem_preprocessors(self):
        pipeline = criar_pipeline()
        assert len(pipeline.pre_processors) >= 7

    def test_pipeline_tem_postprocessors(self):
        pipeline = criar_pipeline()
        assert len(pipeline.post_processors) >= 4

    def test_pipeline_tem_core(self):
        pipeline = criar_pipeline()
        assert pipeline._core_processor is not None

    def test_preprocessors_ordenados_por_prioridade(self):
        pipeline = criar_pipeline()
        prioridades = [p.priority for p in pipeline.pre_processors]
        assert prioridades == sorted(prioridades)


class TestPreProcessors:
    """Testes de pre-processadores."""

    @pytest.mark.asyncio
    async def test_optout_detecta_parar(self):
        from app.pipeline.pre_processors import OptOutProcessor

        processor = OptOutProcessor()
        context = ProcessorContext(
            mensagem_raw={},
            mensagem_texto="nao quero mais receber mensagens",
            telefone="5511999999999",
            medico={"id": "123"},
            conversa={"id": "456"}
        )

        with patch("app.services.optout.processar_optout", return_value=True):
            result = await processor.process(context)

        assert result.should_continue == False
        assert "optout" in result.response.lower() or result.metadata.get("optout")

    @pytest.mark.asyncio
    async def test_media_processor_audio(self):
        from app.pipeline.pre_processors import MediaProcessor

        processor = MediaProcessor()
        context = ProcessorContext(
            mensagem_raw={},
            tipo_mensagem="audio"
        )

        result = await processor.process(context)

        assert result.should_continue == False
        assert result.response is not None


class TestIntegration:
    """Testes de integracao do pipeline."""

    @pytest.mark.asyncio
    async def test_fluxo_completo_mensagem_texto():
        """
        Simula fluxo completo de mensagem de texto.
        """
        # Mock das dependencias
        with patch("app.pipeline.pre_processors.parsear_mensagem") as mock_parse, \
             patch("app.pipeline.pre_processors.deve_processar", return_value=True), \
             patch("app.pipeline.pre_processors.buscar_ou_criar_medico") as mock_medico, \
             patch("app.pipeline.pre_processors.buscar_ou_criar_conversa") as mock_conversa, \
             patch("app.pipeline.core.processar_mensagem_completo") as mock_llm, \
             patch("app.pipeline.post_processors.enviar_resposta") as mock_send:

            # Configurar mocks
            mock_parse.return_value = type("Msg", (), {
                "texto": "Oi Julia",
                "telefone": "5511999999999",
                "message_id": "abc123",
                "tipo": "texto",
                "nome_contato": "Dr Carlos"
            })()

            mock_medico.return_value = {"id": "med123", "primeiro_nome": "Carlos"}
            mock_conversa.return_value = {"id": "conv123", "controlled_by": "ai"}
            mock_llm.return_value = "Oi Dr Carlos! Tudo bem?"
            mock_send.return_value = {"key": {"id": "sent123"}}

            # Executar pipeline
            result = await message_pipeline.process({"data": {}})

            # Verificar
            assert result.success == True
            assert result.response == "Oi Dr Carlos! Tudo bem?"
            mock_send.assert_called_once()
```

## DoD

- [ ] Testes de estrutura do pipeline
- [ ] Testes unitarios de cada pre-processador
- [ ] Testes unitarios de cada pos-processador
- [ ] Teste de integracao end-to-end
- [ ] Testes de regressao (casos que funcionavam antes)
- [ ] Cobertura > 80%

---

## Resumo do Epic

| Story | Descricao | Complexidade |
|-------|-----------|--------------|
| S8.E3.1 | Estrutura base pipeline | Media |
| S8.E3.2 | Pre-processadores | Alta |
| S8.E3.3 | Core processor | Baixa |
| S8.E3.4 | Pos-processadores | Media |
| S8.E3.5 | Configurar webhook | Media |
| S8.E3.6 | Testes regressao | Media |

## Ordem de Implementacao

1. S8.E3.1 - Estrutura base (fundacao)
2. S8.E3.2 - Pre-processadores (extrair logica)
3. S8.E3.3 - Core processor (wrapper LLM)
4. S8.E3.4 - Pos-processadores (envio/save)
5. S8.E3.5 - Configurar webhook (integrar)
6. S8.E3.6 - Testes (validar)

## Arquivos Criados/Modificados

| Arquivo | Acao |
|---------|------|
| `app/pipeline/__init__.py` | Criar |
| `app/pipeline/base.py` | Criar |
| `app/pipeline/processor.py` | Criar |
| `app/pipeline/pre_processors.py` | Criar |
| `app/pipeline/post_processors.py` | Criar |
| `app/pipeline/core.py` | Criar |
| `app/pipeline/setup.py` | Criar |
| `app/api/routes/webhook.py` | Refatorar |
| `tests/test_pipeline.py` | Criar |
