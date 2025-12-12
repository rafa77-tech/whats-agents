"""
DEPRECATED: Use app.services.slack.formatter

Este arquivo eh mantido para backward compatibility.
Novos codigos devem usar:

    from app.services.slack.formatter import bold, formatar_telefone
    from app.services.slack.formatter.templates import template_metricas

Sprint 10 - S10.E2.1
"""
import warnings

warnings.warn(
    "slack_formatter is deprecated. Use app.services.slack.formatter instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export tudo para backward compatibility
from app.services.slack.formatter import *
from app.services.slack.formatter.templates import *
