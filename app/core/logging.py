"""
Configuração de logging estruturado.

Em produção: JSON para facilitar parsing por ferramentas de log
Em desenvolvimento: Formato legível para humanos

Sprint 44 T07.1-T07.3: Melhorias de observabilidade
- Adicionado trace_id via contextvars
- Função mask_phone para padronizar mascaramento
- Context manager para injetar contexto
"""

import logging
import sys
import os
import json
import uuid
from contextvars import ContextVar
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Optional

# Sprint 44 T07.3: Context vars para trace_id e outros contextos
_trace_id: ContextVar[str] = ContextVar("trace_id", default="")
_cliente_id: ContextVar[str] = ContextVar("cliente_id", default="")
_conversa_id: ContextVar[str] = ContextVar("conversa_id", default="")


class JSONFormatter(logging.Formatter):
    """Formatter que gera logs em formato JSON para produção."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Sprint 44 T07.3: Adicionar contexto via contextvars
        trace_id = _trace_id.get()
        if trace_id:
            log_data["trace_id"] = trace_id
        cliente_id = _cliente_id.get()
        if cliente_id:
            log_data["cliente_id"] = cliente_id
        conversa_id = _conversa_id.get()
        if conversa_id:
            log_data["conversa_id"] = conversa_id

        # Adicionar exception info se existir
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Adicionar campos extras se existirem
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """Formatter colorido para desenvolvimento."""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def get_logger(name: str, **extra_fields: Any) -> logging.Logger:
    """
    Retorna logger com campos extras opcionais.

    Usage:
        logger = get_logger(__name__, cliente_id="123", conversa_id="456")
        logger.info("Processando mensagem")
    """
    logger = logging.getLogger(name)

    if extra_fields:
        old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.extra_fields = extra_fields
            return record

        logging.setLogRecordFactory(record_factory)

    return logger


def setup_logging():
    """Configura logging da aplicação baseado no ambiente."""
    environment = os.getenv("ENVIRONMENT", "development").lower()
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    # Remover handlers existentes
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Criar handler para stdout
    handler = logging.StreamHandler(sys.stdout)

    if environment == "production":
        # Produção: JSON estruturado
        handler.setFormatter(JSONFormatter())
    else:
        # Desenvolvimento: formato legível colorido
        handler.setFormatter(
            ColoredFormatter(
                fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Reduzir verbosidade de libs externas
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


# Chamar no startup
setup_logging()


# =============================================================================
# Sprint 44 T07.2-T07.3: Funções de utilidade para logging
# =============================================================================


def mask_phone(telefone: str) -> str:
    """
    Mascara telefone para logs: 5511...1234

    Sprint 44 T07.2: Padronizar mascaramento de telefone.

    Args:
        telefone: Número de telefone

    Returns:
        Telefone mascarado para segurança
    """
    if not telefone:
        return "****"
    if len(telefone) >= 8:
        return f"{telefone[:4]}...{telefone[-4:]}"
    return "****"


def generate_trace_id() -> str:
    """Gera um novo trace_id único."""
    return str(uuid.uuid4())[:8]


def set_trace_id(trace_id: Optional[str] = None) -> str:
    """
    Define trace_id no contexto atual.

    Args:
        trace_id: ID a usar, ou None para gerar automaticamente

    Returns:
        O trace_id definido
    """
    tid = trace_id or generate_trace_id()
    _trace_id.set(tid)
    return tid


def get_trace_id() -> str:
    """Retorna o trace_id atual."""
    return _trace_id.get()


def set_log_context(
    cliente_id: Optional[str] = None,
    conversa_id: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> None:
    """
    Define contexto para todos os logs subsequentes.

    Sprint 44 T07.3: Injetar contexto via contextvars.

    Args:
        cliente_id: ID do cliente
        conversa_id: ID da conversa
        trace_id: ID de trace (opcional, gera se não fornecido)
    """
    if trace_id is not None or not _trace_id.get():
        _trace_id.set(trace_id or generate_trace_id())
    if cliente_id is not None:
        _cliente_id.set(cliente_id)
    if conversa_id is not None:
        _conversa_id.set(conversa_id)


@contextmanager
def log_context(
    cliente_id: Optional[str] = None,
    conversa_id: Optional[str] = None,
    trace_id: Optional[str] = None,
):
    """
    Context manager para definir contexto de logging temporário.

    Usage:
        with log_context(cliente_id="123", conversa_id="456"):
            logger.info("Esta mensagem terá cliente_id e conversa_id")

    Args:
        cliente_id: ID do cliente
        conversa_id: ID da conversa
        trace_id: ID de trace
    """
    # Salvar valores anteriores
    old_trace = _trace_id.get()
    old_cliente = _cliente_id.get()
    old_conversa = _conversa_id.get()

    try:
        # Definir novos valores
        set_log_context(cliente_id, conversa_id, trace_id)
        yield
    finally:
        # Restaurar valores anteriores
        _trace_id.set(old_trace)
        _cliente_id.set(old_cliente)
        _conversa_id.set(old_conversa)


def clear_log_context() -> None:
    """Limpa todo o contexto de logging."""
    _trace_id.set("")
    _cliente_id.set("")
    _conversa_id.set("")
