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
