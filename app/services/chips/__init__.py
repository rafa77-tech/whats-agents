"""
Chip Management Services - Sprint 26.

Sistema de orquestracao multi-chip para Julia:
- Orchestrator: Pool manager, auto-replace, auto-provision
- Selector: Selecao inteligente de chip por tipo de mensagem
- Health Monitor: Monitoramento proativo
- Migration: Migracao anunciada de conversas
"""

from app.services.chips.orchestrator import chip_orchestrator, ChipOrchestrator
from app.services.chips.selector import chip_selector, ChipSelector
from app.services.chips.health_monitor import health_monitor, HealthMonitor
from app.services.chips.migration import (
    migrar_conversa_anunciada,
    processar_migracoes_agendadas,
)

__all__ = [
    "chip_orchestrator",
    "ChipOrchestrator",
    "chip_selector",
    "ChipSelector",
    "health_monitor",
    "HealthMonitor",
    "migrar_conversa_anunciada",
    "processar_migracoes_agendadas",
]
