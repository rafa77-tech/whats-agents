"""
Classes base para processadores.

Sprint 44 T03.2: ProcessorContext com métodos imutáveis (híbrido).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Any
import logging
import copy

logger = logging.getLogger(__name__)


@dataclass
class ProcessorContext:
    """
    Contexto compartilhado entre processadores.

    Sprint 44 T03.2: Adicionados métodos imutáveis (with_updates, add_metadata)
    para facilitar migração gradual para padrão imutável.

    Uso atual (mutável - deprecated para novos usos):
        context.medico = medico

    Uso novo (imutável - preferido):
        context = context.with_updates(medico=medico)
    """
    mensagem_raw: dict                    # Payload original
    mensagem_texto: str = ""              # Texto da mensagem
    telefone: str = ""                    # Telefone do remetente
    message_id: str = ""                  # ID da mensagem
    tipo_mensagem: str = "texto"          # texto, audio, imagem, etc
    medico: Optional[dict] = None         # Dados do medico
    conversa: Optional[dict] = None       # Dados da conversa
    resposta: Optional[str] = None        # Resposta gerada
    metadata: dict = field(default_factory=dict)  # Dados extras

    def with_updates(self, **kwargs) -> "ProcessorContext":
        """
        Sprint 44 T03.2: Retorna novo contexto com campos atualizados.

        Método imutável - não modifica o contexto atual.

        Args:
            **kwargs: Campos a atualizar

        Returns:
            Nova instância com campos atualizados

        Exemplo:
            new_ctx = context.with_updates(medico=medico, conversa=conversa)
        """
        new_context = copy.copy(self)
        new_context.metadata = self.metadata.copy()  # Deep copy do metadata

        for key, value in kwargs.items():
            if hasattr(new_context, key):
                setattr(new_context, key, value)
            else:
                logger.warning(f"ProcessorContext.with_updates: campo desconhecido '{key}'")

        return new_context

    def add_metadata(self, key: str, value: Any) -> "ProcessorContext":
        """
        Sprint 44 T03.2: Retorna novo contexto com metadata adicional.

        Método imutável - não modifica o contexto atual.

        Args:
            key: Chave do metadata
            value: Valor do metadata

        Returns:
            Nova instância com metadata adicional

        Exemplo:
            new_ctx = context.add_metadata("tempo_inicio", time.time())
        """
        new_context = copy.copy(self)
        new_context.metadata = self.metadata.copy()
        new_context.metadata[key] = value
        return new_context

    def clone(self) -> "ProcessorContext":
        """
        Sprint 44 T03.2: Cria cópia independente do contexto.

        Returns:
            Nova instância com mesmos valores
        """
        new_context = copy.copy(self)
        new_context.metadata = self.metadata.copy()
        return new_context


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
