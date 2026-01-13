"""
Chip Management Services - Sprint 26.

Sistema de orquestracao multi-chip para Julia:
- Orchestrator: Pool manager, auto-replace, auto-provision
- Selector: Selecao inteligente de chip por tipo de mensagem
- Sender: Envio de mensagens via provider abstraction (E08)
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
from app.services.chips.sender import (
    enviar_via_chip,
    enviar_mensagem_inteligente,
    enviar_media_via_chip,
    verificar_conexao_chip,
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
    # E08 - Multi-Provider
    "enviar_via_chip",
    "enviar_mensagem_inteligente",
    "enviar_media_via_chip",
    "verificar_conexao_chip",
]
