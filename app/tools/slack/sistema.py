"""
Tools de sistema para o agente Slack.

Sprint 10 - S10.E2.3
Sprint 18.1 - B1: Toggle campanhas via Slack
Sprint 21 - E02: Kill switch ponte externa
"""
import logging
from datetime import datetime, timezone

from app.services.supabase import supabase
from app.services.policy.flags import (
    get_campaigns_flags,
    set_flag,
    is_safe_mode_active,
    get_external_handoff_flags,
    enable_external_handoff,
    disable_external_handoff,
    set_external_handoff_canary,
)

logger = logging.getLogger(__name__)


# =============================================================================
# DEFINICAO DAS TOOLS (formato Claude)
# =============================================================================

TOOL_STATUS_SISTEMA = {
    "name": "status_sistema",
    "description": """Retorna status geral do sistema.

QUANDO USAR:
- Gestor pergunta como ta a Julia
- Gestor quer ver status geral
- Gestor pergunta se ta tudo funcionando

EXEMPLOS:
- "como ta a Julia?"
- "status"
- "ta tudo ok?"

NAO requer confirmacao - e apenas leitura de dados.""",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}

TOOL_BUSCAR_HANDOFFS = {
    "name": "buscar_handoffs",
    "description": """Lista handoffs pendentes ou recentes.

QUANDO USAR:
- Gestor pergunta sobre handoffs
- Gestor quer ver conversas que precisam de atencao

EXEMPLOS:
- "tem handoff pendente?"
- "quem precisa de atencao?"

NAO requer confirmacao - e apenas leitura de dados.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["pendente", "resolvido", "todos"],
                "description": "Status do handoff"
            }
        },
        "required": []
    }
}

TOOL_PAUSAR_JULIA = {
    "name": "pausar_julia",
    "description": """Pausa envios automaticos da Julia.

QUANDO USAR:
- Gestor pede para pausar
- Gestor quer parar os envios

EXEMPLOS:
- "pausa a Julia"
- "para de enviar"

ACAO CRITICA: Peca confirmacao antes de pausar.""",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}

TOOL_RETOMAR_JULIA = {
    "name": "retomar_julia",
    "description": """Retoma envios automaticos da Julia.

QUANDO USAR:
- Gestor pede para retomar
- Gestor quer voltar os envios

EXEMPLOS:
- "retoma a Julia"
- "volta a enviar"

ACAO CRITICA: Peca confirmacao antes de retomar.""",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}

TOOL_TOGGLE_CAMPANHAS = {
    "name": "toggle_campanhas",
    "description": """Ativa ou desativa campanhas proativas.

QUANDO USAR:
- Gestor quer parar/iniciar campanhas
- Gestor quer desativar envios proativos
- Gestor pergunta status das campanhas

EXEMPLOS:
- "desativa campanhas"
- "para as campanhas"
- "liga campanhas"
- "ativa campanhas"
- "campanhas status"
- "campanhas estao ativas?"

DIFERENCA DE pausar_julia:
- pausar_julia: para TUDO (inclusive replies)
- toggle_campanhas: para so proativos (campanhas, followups)

ACAO CRITICA para on/off: Peca confirmacao antes de mudar.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "acao": {
                "type": "string",
                "enum": ["on", "off", "status"],
                "description": "Acao: 'on' para ativar, 'off' para desativar, 'status' para ver estado atual"
            }
        },
        "required": ["acao"]
    }
}

TOOL_TOGGLE_PONTE_EXTERNA = {
    "name": "toggle_ponte_externa",
    "description": """Controla a ponte externa (handoff medico-divulgador).

QUANDO USAR:
- Gestor quer ativar/desativar ponte externa
- Gestor quer ver status da ponte externa
- Gestor quer ajustar canary (rollout gradual)

EXEMPLOS:
- "toggle_ponte_externa off" - desliga todas as pontes
- "toggle_ponte_externa on" - liga ponte (100%)
- "toggle_ponte_externa on 50" - liga com canary 50%
- "toggle_ponte_externa status" - mostra estado atual
- "desliga ponte externa"
- "para as pontes"
- "status ponte"

ACAO CRITICA para on/off: Peca confirmacao antes de mudar.
Status nao requer confirmacao.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "acao": {
                "type": "string",
                "enum": ["on", "off", "status"],
                "description": "Acao: 'on' para ativar, 'off' para desativar, 'status' para ver estado atual"
            },
            "canary_pct": {
                "type": "integer",
                "description": "Percentual do canary (0-100). Apenas para acao 'on'. Default: 100",
                "minimum": 0,
                "maximum": 100
            }
        },
        "required": ["acao"]
    }
}


# =============================================================================
# HANDLERS
# =============================================================================

async def handle_status_sistema(params: dict) -> dict:
    """Retorna status geral do sistema."""
    try:
        # Status Julia
        status_result = supabase.table("julia_status").select("status").order(
            "created_at", desc=True
        ).limit(1).execute()
        status = status_result.data[0].get("status") if status_result.data else "ativo"

        # Conversas ativas
        conversas = supabase.table("conversations").select(
            "id", count="exact"
        ).eq("status", "active").execute()

        # Handoffs pendentes
        handoffs = supabase.table("handoffs").select(
            "id", count="exact"
        ).eq("status", "pendente").execute()

        # Vagas abertas
        vagas = supabase.table("vagas").select(
            "id", count="exact"
        ).eq("status", "aberta").execute()

        # Mensagens hoje
        hoje = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        msgs = supabase.table("fila_mensagens").select(
            "id", count="exact"
        ).eq("status", "enviada").gte("enviada_em", hoje).execute()

        return {
            "success": True,
            "status": status,
            "conversas_ativas": conversas.count or 0,
            "handoffs_pendentes": handoffs.count or 0,
            "vagas_abertas": vagas.count or 0,
            "mensagens_hoje": msgs.count or 0
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_buscar_handoffs(params: dict) -> dict:
    """Lista handoffs."""
    status = params.get("status", "pendente")

    try:
        query = supabase.table("handoffs").select(
            "*, conversations(clientes(primeiro_nome, telefone))"
        ).order("created_at", desc=True).limit(10)

        if status != "todos":
            query = query.eq("status", status)

        result = query.execute()

        handoffs = []
        for h in result.data or []:
            conv = h.get("conversations", {})
            cliente = conv.get("clientes", {}) if conv else {}
            handoffs.append({
                "id": h.get("id"),
                "medico": cliente.get("primeiro_nome"),
                "telefone": cliente.get("telefone"),
                "motivo": h.get("trigger_type"),
                "criado_em": h.get("created_at"),
                "status": h.get("status")
            })

        return {"success": True, "handoffs": handoffs, "total": len(handoffs)}

    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_pausar_julia(params: dict, user_id: str) -> dict:
    """Pausa a Julia."""
    try:
        supabase.table("julia_status").insert({
            "status": "pausado",
            "motivo": "Pausado via Slack",
            "alterado_por": user_id,
            "alterado_via": "slack",
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        return {"success": True, "status": "pausado"}

    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_retomar_julia(params: dict, user_id: str) -> dict:
    """Retoma a Julia."""
    try:
        supabase.table("julia_status").insert({
            "status": "ativo",
            "motivo": "Retomado via Slack",
            "alterado_por": user_id,
            "alterado_via": "slack",
            "created_at": datetime.now(timezone.utc).isoformat()
        }).execute()

        return {"success": True, "status": "ativo"}

    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_toggle_campanhas(params: dict, user_id: str) -> dict:
    """
    Toggle campanhas on/off ou retorna status.

    Sprint 18.1 - B1: Kill switch granular para campanhas.
    """
    acao = params.get("acao", "status")

    try:
        # Status atual
        campaigns_flags = await get_campaigns_flags()
        safe_mode = await is_safe_mode_active()

        if acao == "status":
            return {
                "success": True,
                "campanhas_ativas": campaigns_flags.enabled,
                "safe_mode": safe_mode,
                "mensagem": (
                    f"Campanhas: {'ativadas' if campaigns_flags.enabled else 'desativadas'}\n"
                    f"Safe mode: {'ativo' if safe_mode else 'inativo'}"
                )
            }

        # Toggle on/off
        new_enabled = acao == "on"

        # Atualizar flag
        success = await set_flag(
            key="campaigns",
            value={"enabled": new_enabled},
            updated_by=user_id
        )

        if not success:
            return {"success": False, "error": "Falha ao atualizar flag"}

        # Emitir evento de auditoria
        await _emitir_evento_toggle_campanhas(
            enabled=new_enabled,
            actor_id=user_id,
        )

        acao_realizada = "ativadas" if new_enabled else "desativadas"
        logger.info(
            f"Campanhas {acao_realizada} por {user_id}",
            extra={
                "event": "campaigns_toggled",
                "enabled": new_enabled,
                "actor_id": user_id,
                "channel": "slack",
            }
        )

        return {
            "success": True,
            "campanhas_ativas": new_enabled,
            "mensagem": f"Campanhas {acao_realizada} com sucesso!"
        }

    except Exception as e:
        logger.error(f"Erro ao toggle campanhas: {e}")
        return {"success": False, "error": str(e)}


async def _emitir_evento_toggle_campanhas(enabled: bool, actor_id: str) -> None:
    """Emite business_event para auditoria de toggle."""
    from app.services.business_events import (
        emit_event,
        BusinessEvent,
        EventType,
        EventSource,
    )

    # Usar OUTBOUND_BYPASS como carrier (ou criar tipo específico)
    # Por enquanto, logamos estruturado e usamos dedupe_key para auditoria
    dedupe_key = f"campaigns_toggle:{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"

    await emit_event(BusinessEvent(
        event_type=EventType.OUTBOUND_BYPASS,  # Reusa tipo existente
        source=EventSource.OPS,
        cliente_id=None,
        dedupe_key=dedupe_key,
        event_props={
            "action": "campaigns_toggled",
            "enabled": enabled,
            "actor_id": actor_id,
            "channel": "slack",
            "method": "command",
        },
    ))


async def handle_toggle_ponte_externa(params: dict, user_id: str) -> dict:
    """
    Toggle ponte externa on/off ou retorna status.

    Sprint 21 - E02: Kill switch para ponte externa.

    Args:
        params: {acao: on|off|status, canary_pct?: int}
        user_id: ID do usuario Slack

    Returns:
        Dict com resultado da operacao
    """
    acao = params.get("acao", "status")
    canary_pct = params.get("canary_pct", 100)

    try:
        # Status atual
        flags = await get_external_handoff_flags()

        if acao == "status":
            # Contar handoffs pendentes
            handoffs_pendentes = 0
            try:
                from app.services.supabase import supabase
                result = supabase.table("external_handoffs") \
                    .select("id", count="exact") \
                    .in_("status", ["pending", "contacted"]) \
                    .execute()
                handoffs_pendentes = result.count or 0
            except Exception:
                pass

            status_texto = (
                f"*Ponte Externa*\n"
                f"• Status: {'ativa' if flags.enabled else 'desativada'}\n"
                f"• Canary: {flags.canary_pct}%\n"
                f"• Handoffs pendentes: {handoffs_pendentes}"
            )

            return {
                "success": True,
                "enabled": flags.enabled,
                "canary_pct": flags.canary_pct,
                "handoffs_pendentes": handoffs_pendentes,
                "mensagem": status_texto
            }

        # Toggle on
        if acao == "on":
            success = await enable_external_handoff(
                canary_pct=canary_pct,
                updated_by=user_id
            )

            if not success:
                return {"success": False, "error": "Falha ao ativar ponte externa"}

            # Emitir evento de auditoria
            await _emitir_evento_ponte_externa(
                enabled=True,
                canary_pct=canary_pct,
                actor_id=user_id,
            )

            logger.info(
                f"Ponte externa ativada por {user_id} (canary: {canary_pct}%)",
                extra={
                    "event": "ponte_externa_enabled",
                    "canary_pct": canary_pct,
                    "actor_id": user_id,
                    "channel": "slack",
                }
            )

            return {
                "success": True,
                "enabled": True,
                "canary_pct": canary_pct,
                "mensagem": f"Ponte externa ativada com canary {canary_pct}%!"
            }

        # Toggle off
        if acao == "off":
            success = await disable_external_handoff(updated_by=user_id)

            if not success:
                return {"success": False, "error": "Falha ao desativar ponte externa"}

            # Emitir evento de auditoria
            await _emitir_evento_ponte_externa(
                enabled=False,
                canary_pct=flags.canary_pct,  # Manter valor anterior
                actor_id=user_id,
            )

            logger.info(
                f"Ponte externa desativada por {user_id}",
                extra={
                    "event": "ponte_externa_disabled",
                    "actor_id": user_id,
                    "channel": "slack",
                }
            )

            return {
                "success": True,
                "enabled": False,
                "canary_pct": flags.canary_pct,
                "mensagem": (
                    "Ponte externa desativada!\n"
                    "• Novas pontes: bloqueadas\n"
                    "• Follow-ups: pausados\n"
                    "• Confirmacoes existentes: ainda funcionam"
                )
            }

        return {"success": False, "error": f"Acao desconhecida: {acao}"}

    except Exception as e:
        logger.error(f"Erro ao toggle ponte externa: {e}")
        return {"success": False, "error": str(e)}


async def _emitir_evento_ponte_externa(
    enabled: bool,
    canary_pct: int,
    actor_id: str
) -> None:
    """Emite business_event para auditoria de toggle ponte externa."""
    from app.services.business_events import (
        emit_event,
        BusinessEvent,
        EventType,
        EventSource,
    )

    dedupe_key = f"ponte_externa_toggle:{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"

    await emit_event(BusinessEvent(
        event_type=EventType.OUTBOUND_BYPASS,  # Reusa tipo existente
        source=EventSource.OPS,
        cliente_id=None,
        dedupe_key=dedupe_key,
        event_props={
            "action": "ponte_externa_toggled",
            "enabled": enabled,
            "canary_pct": canary_pct,
            "actor_id": actor_id,
            "channel": "slack",
            "method": "command",
        },
    ))
