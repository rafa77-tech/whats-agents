"""
Chip Management Services - Sprint 26 + Sprint 36 + Sprint 40.

Sistema de orquestracao multi-chip para Julia:
- Orchestrator: Pool manager, auto-replace, auto-provision
- Selector: Selecao inteligente de chip por tipo de mensagem
- Sender: Envio de mensagens via provider abstraction (E08)
- Health Monitor: Monitoramento proativo
- Migration: Migracao anunciada de conversas

Sprint 36 - Resiliência e Observabilidade:
- Circuit Breaker: Per-chip circuit breaker (E09)
- Cooldown: Cooldown automático por tipo de erro (E05)
- Affinity: Sistema de afinidade chip-médico (E11)

Sprint 40 - Instance Management UI:
- Instance Manager: Criacao/gerenciamento de instancias WhatsApp
"""

from app.services.chips.orchestrator import chip_orchestrator, ChipOrchestrator
from app.services.chips.selector import chip_selector, ChipSelector
from app.services.chips.health_monitor import health_monitor, HealthMonitor
from app.services.chips.migration import (
    migrar_conversa_anunciada,
    processar_migracoes_agendadas,
    # Sprint 36 - T11.4: Migração com contexto
    coletar_contexto_conversa,
    migrar_conversa_com_contexto,
    obter_contexto_conversa_atual,
    listar_migracoes_com_contexto,
)
from app.services.chips.sender import (
    enviar_via_chip,
    enviar_mensagem_inteligente,
    enviar_media_via_chip,
    verificar_conexao_chip,
)

# Sprint 36
from app.services.chips.circuit_breaker import (
    ChipCircuitBreaker,
    ChipCircuit,
    CircuitState,
    ChipCircuitOpenError,
    chip_circuit_breaker,
)
from app.services.chips.cooldown import (
    aplicar_cooldown,
    registrar_erro_whatsapp,
    limpar_cooldown,
    verificar_cooldown,
)
from app.services.chips.affinity import (
    registrar_interacao_chip_medico,
    buscar_chip_com_afinidade,
    registrar_conversa_bidirecional,
    calcular_taxa_resposta,
    calcular_taxa_delivery,
    atualizar_metricas_chip,
)

# Sprint 40 - Instance Manager
from app.services.chips.instance_manager import (
    InstanceManager,
    instance_manager,
    CreateInstanceResult,
    QRCodeResult,
    ConnectionStateResult,
    DeleteInstanceResult,
)

# Sync Evolution
from app.services.chips.sync_evolution import (
    sincronizar_chips_com_evolution,
    buscar_estado_instancia,
    listar_instancias_evolution,
)

__all__ = [
    # Orchestrator
    "chip_orchestrator",
    "ChipOrchestrator",
    # Selector
    "chip_selector",
    "ChipSelector",
    # Health Monitor
    "health_monitor",
    "HealthMonitor",
    # Migration
    "migrar_conversa_anunciada",
    "processar_migracoes_agendadas",
    # Sprint 36 - T11.4: Migração com contexto
    "coletar_contexto_conversa",
    "migrar_conversa_com_contexto",
    "obter_contexto_conversa_atual",
    "listar_migracoes_com_contexto",
    # E08 - Multi-Provider
    "enviar_via_chip",
    "enviar_mensagem_inteligente",
    "enviar_media_via_chip",
    "verificar_conexao_chip",
    # Sprint 36 - Circuit Breaker (E09)
    "ChipCircuitBreaker",
    "ChipCircuit",
    "CircuitState",
    "ChipCircuitOpenError",
    "chip_circuit_breaker",
    # Sprint 36 - Cooldown (E05)
    "aplicar_cooldown",
    "registrar_erro_whatsapp",
    "limpar_cooldown",
    "verificar_cooldown",
    # Sprint 36 - Affinity (E11)
    "registrar_interacao_chip_medico",
    "buscar_chip_com_afinidade",
    "registrar_conversa_bidirecional",
    "calcular_taxa_resposta",
    "calcular_taxa_delivery",
    "atualizar_metricas_chip",
    # Sprint 40 - Instance Manager
    "InstanceManager",
    "instance_manager",
    "CreateInstanceResult",
    "QRCodeResult",
    "ConnectionStateResult",
    "DeleteInstanceResult",
    # Sync Evolution
    "sincronizar_chips_com_evolution",
    "buscar_estado_instancia",
    "listar_instancias_evolution",
]
