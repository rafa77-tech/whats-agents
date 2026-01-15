"""
Tracing Module - Correlation ID para rastreamento de requisições.

Sprint 31 - S31.E3.1

Este módulo fornece um sistema de correlation ID que permite
rastrear uma requisição do webhook até a resposta final.

Uso:
    from app.core.tracing import get_trace_id, set_trace_id

    # No início do request (middleware faz isso automaticamente)
    set_trace_id(generate_trace_id())

    # Em qualquer lugar do código
    trace_id = get_trace_id()
    logger.info(f"[{trace_id}] Processando mensagem")

Como funciona:
    - Context vars propagam o trace_id automaticamente em async code
    - O middleware gera/extrai o trace_id no início de cada request
    - Todos os logs podem incluir o trace_id para correlação
"""
import uuid
from contextvars import ContextVar
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Context var para propagar trace_id através de código async
_trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)


def generate_trace_id() -> str:
    """
    Gera novo trace ID.

    Retorna os primeiros 8 caracteres de um UUID4,
    que é suficiente para identificação única em um período razoável.

    Returns:
        String de 8 caracteres hex
    """
    return str(uuid.uuid4())[:8]


def set_trace_id(trace_id: str) -> None:
    """
    Define trace ID para o contexto atual.

    O trace_id será propagado automaticamente para todas as
    coroutines chamadas a partir deste contexto.

    Args:
        trace_id: ID de trace a definir
    """
    _trace_id_var.set(trace_id)


def get_trace_id() -> Optional[str]:
    """
    Retorna trace ID do contexto atual.

    Returns:
        Trace ID ou None se não definido
    """
    return _trace_id_var.get()


def clear_trace_id() -> None:
    """
    Limpa trace ID do contexto.

    Deve ser chamado no final do processamento do request
    para evitar vazamento de contexto.
    """
    _trace_id_var.set(None)


class TraceContext:
    """
    Context manager para trace ID.

    Uso:
        with TraceContext() as trace_id:
            # trace_id disponível aqui e em chamadas aninhadas
            await processar_mensagem()

        # ou com ID específico
        with TraceContext("abc12345"):
            ...
    """

    def __init__(self, trace_id: Optional[str] = None):
        """
        Inicializa contexto.

        Args:
            trace_id: ID específico ou None para gerar automaticamente
        """
        self._trace_id = trace_id or generate_trace_id()
        self._token = None

    def __enter__(self) -> str:
        """Entra no contexto, define trace_id."""
        self._token = _trace_id_var.set(self._trace_id)
        return self._trace_id

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sai do contexto, restaura valor anterior."""
        if self._token is not None:
            _trace_id_var.reset(self._token)
        return False


def trace_log(message: str, level: int = logging.INFO, **extra) -> None:
    """
    Log com trace_id incluído automaticamente.

    Convenience function que adiciona trace_id aos extras do log.

    Args:
        message: Mensagem de log
        level: Nível do log (default INFO)
        **extra: Campos extras para o log
    """
    trace_id = get_trace_id()
    if trace_id:
        extra["trace_id"] = trace_id

    logger.log(level, message, extra=extra)


def get_trace_prefix() -> str:
    """
    Retorna prefixo formatado para logs.

    Returns:
        String no formato "[trace_id] " ou "" se não houver trace
    """
    trace_id = get_trace_id()
    if trace_id:
        return f"[{trace_id}] "
    return ""
