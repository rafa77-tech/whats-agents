"""
Tools de sistema para Helena.

Sprint 47: Status e operações.
"""
import logging
from datetime import datetime, timezone

from app.services.supabase import supabase

logger = logging.getLogger(__name__)

# === TOOL: status_sistema ===

TOOL_STATUS_SISTEMA = {
    "name": "status_sistema",
    "description": """Retorna status geral do sistema.

QUANDO USAR:
- "Como está o sistema?"
- "Status dos chips"
- "Tem algo errado?"

RETORNA:
- Status dos chips WhatsApp
- Fila de mensagens
- Handoffs pendentes
""",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}


async def handle_status_sistema(
    params: dict, user_id: str, channel_id: str
) -> dict:
    """Handler para status_sistema."""
    try:
        # Chips
        chips_result = supabase.rpc(
            "execute_readonly_query",
            {
                "sql_query": """
                SELECT
                    status,
                    COUNT(*) as quantidade,
                    ROUND(AVG(trust_score)::numeric, 2) as trust_medio
                FROM julia_chips
                GROUP BY status
                ORDER BY quantidade DESC
                LIMIT 20
                """
            },
        ).execute()

        # Fila
        fila_result = supabase.rpc(
            "execute_readonly_query",
            {
                "sql_query": """
                SELECT
                    status,
                    COUNT(*) as quantidade
                FROM fila_mensagens
                WHERE created_at >= NOW() - INTERVAL '24 hours'
                GROUP BY status
                LIMIT 10
                """
            },
        ).execute()

        # Handoffs pendentes
        handoffs_result = supabase.rpc(
            "execute_readonly_query",
            {
                "sql_query": """
                SELECT COUNT(*) as pendentes
                FROM handoffs
                WHERE status = 'pendente'
                LIMIT 1
                """
            },
        ).execute()

        return {
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "chips": chips_result.data or [],
            "fila_24h": fila_result.data or [],
            "handoffs_pendentes": (
                handoffs_result.data[0]["pendentes"]
                if handoffs_result.data
                else 0
            ),
        }

    except Exception as e:
        logger.error(f"Erro em status_sistema: {e}")
        return {"success": False, "error": str(e)}


# === TOOL: listar_handoffs ===

TOOL_LISTAR_HANDOFFS = {
    "name": "listar_handoffs",
    "description": """Lista handoffs (escalações para humano).

QUANDO USAR:
- "Tem handoff pendente?"
- "Listar escalações"
- "Quem precisa de atendimento?"

RETORNA:
- Lista de handoffs com detalhes
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["pendente", "em_atendimento", "resolvido", "todos"],
                "description": "Filtrar por status",
                "default": "pendente",
            },
            "limite": {
                "type": "integer",
                "description": "Máximo de resultados",
                "default": 10,
            },
        },
        "required": [],
    },
}


async def handle_listar_handoffs(
    params: dict, user_id: str, channel_id: str
) -> dict:
    """Handler para listar_handoffs."""
    status = params.get("status", "pendente")
    limite = min(params.get("limite", 10), 50)

    try:
        status_filter = ""
        if status != "todos":
            status_filter = f"AND h.status = '{status}'"

        result = supabase.rpc(
            "execute_readonly_query",
            {
                "sql_query": f"""
                SELECT
                    h.id,
                    h.motivo,
                    h.status,
                    h.created_at,
                    cl.primeiro_nome,
                    cl.sobrenome,
                    cl.telefone,
                    e.nome as especialidade
                FROM handoffs h
                JOIN conversations c ON c.id = h.conversation_id
                JOIN clientes cl ON cl.id = c.cliente_id
                LEFT JOIN especialidades e ON e.id = cl.especialidade_id
                WHERE 1=1 {status_filter}
                ORDER BY h.created_at DESC
                LIMIT {limite}
                """
            },
        ).execute()

        return {
            "success": True,
            "filtro_status": status,
            "handoffs": result.data or [],
            "total": len(result.data or []),
        }

    except Exception as e:
        logger.error(f"Erro em listar_handoffs: {e}")
        return {"success": False, "error": str(e)}
