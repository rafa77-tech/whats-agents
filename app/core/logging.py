"""
Configuração de logging estruturado.

Em produção: JSON para facilitar parsing por ferramentas de log
Em desenvolvimento: Formato legível para humanos
"""
import logging
import sys
import os
import json
from datetime import datetime, timezone
from typing import Any


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
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
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
        handler.setFormatter(ColoredFormatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))

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
