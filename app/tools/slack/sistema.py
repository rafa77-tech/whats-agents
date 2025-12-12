"""
Tools de sistema para o agente Slack.

Sprint 10 - S10.E2.3
"""
from datetime import datetime, timezone

from app.services.supabase import supabase


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
