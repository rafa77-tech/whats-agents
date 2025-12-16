"""
[DEPRECATED] Modulo de compatibilidade para relatorios.

Este arquivo foi reorganizado em:
- app/services/relatorios/periodo.py
- app/services/relatorios/semanal.py
- app/services/relatorios/diario.py

Use: from app.services.relatorios import gerar_relatorio_diario
Sprint 10 - S10.E3.3
"""
import warnings

warnings.warn(
    "relatorio.py is deprecated. Use app.services.relatorios instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-exportar tudo do novo modulo para manter compatibilidade
from app.services.relatorios import (
    # Periodico
    gerar_report_periodo,
    enviar_report_periodo_slack,
    # Semanal
    gerar_report_semanal,
    enviar_report_semanal_slack,
    # Diario
    gerar_relatorio_diario,
    enviar_relatorio_slack,
)

__all__ = [
    "gerar_report_periodo",
    "enviar_report_periodo_slack",
    "gerar_report_semanal",
    "enviar_report_semanal_slack",
    "gerar_relatorio_diario",
    "enviar_relatorio_slack",
]
