"""
Services de relatorios.

Sprint 10 - S10.E3.3
"""
from .periodo import (
    gerar_report_periodo,
    enviar_report_periodo_slack,
)

from .semanal import (
    gerar_report_semanal,
    enviar_report_semanal_slack,
)

from .diario import (
    gerar_relatorio_diario,
    enviar_relatorio_slack,
)


__all__ = [
    # Periodico
    "gerar_report_periodo",
    "enviar_report_periodo_slack",
    # Semanal
    "gerar_report_semanal",
    "enviar_report_semanal_slack",
    # Diario
    "gerar_relatorio_diario",
    "enviar_relatorio_slack",
]
