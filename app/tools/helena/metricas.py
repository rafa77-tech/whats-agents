"""
Tools de métricas para Helena.

Sprint 47: Métricas pré-definidas otimizadas.
"""
import logging
from datetime import datetime, timedelta, timezone

from app.services.supabase import supabase

logger = logging.getLogger(__name__)

# === TOOL: metricas_periodo ===

TOOL_METRICAS_PERIODO = {
    "name": "metricas_periodo",
    "description": """Retorna métricas gerais de um período.

QUANDO USAR:
- "Como foi hoje?"
- "Métricas da semana"
- "Resumo do mês"
- "Quantas conversas tivemos?"

RETORNA:
- Total de conversas
- Conversas com resposta
- Conversões (plantões reservados)
- Taxa de resposta
- Taxa de conversão
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "periodo": {
                "type": "string",
                "enum": ["hoje", "ontem", "semana", "mes"],
                "description": "Período para análise",
            },
        },
        "required": ["periodo"],
    },
}


async def handle_metricas_periodo(
    params: dict, user_id: str, channel_id: str
) -> dict:
    """Handler para metricas_periodo."""
    periodo = params.get("periodo", "hoje")

    # Calcular datas
    hoje = datetime.now(timezone.utc).date()
    if periodo == "hoje":
        inicio = hoje
        fim = hoje + timedelta(days=1)
    elif periodo == "ontem":
        inicio = hoje - timedelta(days=1)
        fim = hoje
    elif periodo == "semana":
        inicio = hoje - timedelta(days=7)
        fim = hoje + timedelta(days=1)
    elif periodo == "mes":
        inicio = hoje - timedelta(days=30)
        fim = hoje + timedelta(days=1)
    else:
        return {"success": False, "error": f"Período inválido: {periodo}"}

    try:
        # Query otimizada
        result = supabase.rpc(
            "execute_readonly_query",
            {
                "sql_query": f"""
                SELECT
                    COUNT(DISTINCT c.id) as total_conversas,
                    COUNT(DISTINCT c.id) FILTER (
                        WHERE EXISTS (
                            SELECT 1 FROM interacoes i
                            WHERE i.conversation_id = c.id AND i.tipo = 'entrada'
                        )
                    ) as com_resposta,
                    COUNT(DISTINCT c.id) FILTER (WHERE c.status = 'convertida') as conversoes
                FROM conversations c
                WHERE c.created_at >= '{inicio}'::date
                AND c.created_at < '{fim}'::date
                LIMIT 1
                """
            },
        ).execute()

        if not result.data or len(result.data) == 0:
            data = {"total_conversas": 0, "com_resposta": 0, "conversoes": 0}
        else:
            data = result.data[0]

        # Calcular taxas
        total = data.get("total_conversas", 0) or 0
        com_resposta = data.get("com_resposta", 0) or 0
        conversoes = data.get("conversoes", 0) or 0

        taxa_resposta = round(100 * com_resposta / total, 1) if total > 0 else 0
        taxa_conversao = round(100 * conversoes / com_resposta, 1) if com_resposta > 0 else 0

        return {
            "success": True,
            "periodo": periodo,
            "data_inicio": str(inicio),
            "data_fim": str(fim),
            "metricas": {
                "total_conversas": total,
                "com_resposta": com_resposta,
                "conversoes": conversoes,
                "taxa_resposta": taxa_resposta,
                "taxa_conversao": taxa_conversao,
            },
        }

    except Exception as e:
        logger.error(f"Erro em metricas_periodo: {e}")
        return {"success": False, "error": str(e)}


# === TOOL: metricas_conversao ===

TOOL_METRICAS_CONVERSAO = {
    "name": "metricas_conversao",
    "description": """Retorna funil de conversão detalhado.

QUANDO USAR:
- "Como está o funil?"
- "Taxa de conversão detalhada"
- "Onde estamos perdendo?"

RETORNA:
- Cada etapa do funil com quantidade e taxa
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "dias": {
                "type": "integer",
                "description": "Últimos N dias (default: 7)",
                "default": 7,
            },
        },
        "required": [],
    },
}


async def handle_metricas_conversao(
    params: dict, user_id: str, channel_id: str
) -> dict:
    """Handler para metricas_conversao."""
    dias = params.get("dias", 7)
    inicio = datetime.now(timezone.utc).date() - timedelta(days=dias)

    try:
        result = supabase.rpc(
            "execute_readonly_query",
            {
                "sql_query": f"""
                SELECT
                    COUNT(DISTINCT c.id) as total_abordados,
                    COUNT(DISTINCT c.id) FILTER (
                        WHERE EXISTS (SELECT 1 FROM interacoes i WHERE i.conversation_id = c.id AND i.tipo = 'entrada')
                    ) as responderam,
                    COUNT(DISTINCT c.id) FILTER (WHERE c.status = 'convertida') as converteram,
                    COUNT(DISTINCT c.id) FILTER (WHERE c.status = 'perdida') as perdidos
                FROM conversations c
                WHERE c.created_at >= '{inicio}'::date
                LIMIT 1
                """
            },
        ).execute()

        data = result.data[0] if result.data else {}

        total = data.get("total_abordados", 0) or 0
        responderam = data.get("responderam", 0) or 0
        converteram = data.get("converteram", 0) or 0
        perdidos = data.get("perdidos", 0) or 0

        return {
            "success": True,
            "dias": dias,
            "funil": {
                "abordados": {"quantidade": total, "taxa": 100},
                "responderam": {
                    "quantidade": responderam,
                    "taxa": round(100 * responderam / total, 1) if total > 0 else 0,
                },
                "converteram": {
                    "quantidade": converteram,
                    "taxa": round(100 * converteram / responderam, 1) if responderam > 0 else 0,
                },
                "perdidos": {
                    "quantidade": perdidos,
                    "taxa": round(100 * perdidos / total, 1) if total > 0 else 0,
                },
            },
        }

    except Exception as e:
        logger.error(f"Erro em metricas_conversao: {e}")
        return {"success": False, "error": str(e)}


# === TOOL: metricas_campanhas ===

TOOL_METRICAS_CAMPANHAS = {
    "name": "metricas_campanhas",
    "description": """Retorna métricas de campanhas.

QUANDO USAR:
- "Como estão as campanhas?"
- "Performance da campanha X"
- "Campanhas ativas"

RETORNA:
- Lista de campanhas com métricas
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["todas", "ativa", "concluida", "agendada"],
                "description": "Filtrar por status",
                "default": "todas",
            },
            "limite": {
                "type": "integer",
                "description": "Máximo de campanhas (default: 10)",
                "default": 10,
            },
        },
        "required": [],
    },
}


async def handle_metricas_campanhas(
    params: dict, user_id: str, channel_id: str
) -> dict:
    """Handler para metricas_campanhas."""
    status = params.get("status", "todas")
    limite = min(params.get("limite", 10), 50)

    try:
        status_filter = ""
        if status != "todas":
            status_filter = f"WHERE status = '{status}'"

        result = supabase.rpc(
            "execute_readonly_query",
            {
                "sql_query": f"""
                SELECT
                    id,
                    nome_template,
                    tipo_campanha,
                    status,
                    total_destinatarios,
                    enviados,
                    entregues,
                    respondidos,
                    CASE WHEN enviados > 0 THEN ROUND(100.0 * entregues / enviados, 1) ELSE 0 END as taxa_entrega,
                    CASE WHEN entregues > 0 THEN ROUND(100.0 * respondidos / entregues, 1) ELSE 0 END as taxa_resposta,
                    created_at
                FROM campanhas
                {status_filter}
                ORDER BY created_at DESC
                LIMIT {limite}
                """
            },
        ).execute()

        return {
            "success": True,
            "filtro_status": status,
            "campanhas": result.data or [],
            "total": len(result.data or []),
        }

    except Exception as e:
        logger.error(f"Erro em metricas_campanhas: {e}")
        return {"success": False, "error": str(e)}
