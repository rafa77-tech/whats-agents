"""
Tools de metricas para o agente Slack.

Sprint 10 - S10.E2.3
"""
from datetime import datetime, timezone, timedelta

from app.services.supabase import supabase


# =============================================================================
# DEFINICAO DAS TOOLS (formato Claude)
# =============================================================================

TOOL_BUSCAR_METRICAS = {
    "name": "buscar_metricas",
    "description": """Busca metricas de performance da Julia.

QUANDO USAR:
- Gestor pergunta como foi o dia/semana
- Gestor quer saber quantos responderam
- Gestor pergunta sobre taxa de resposta
- Gestor quer ver numeros/resultados

EXEMPLOS:
- "como foi hoje?"
- "quantos responderam?"
- "qual a taxa de resposta?"
- "como ta essa semana?"
- "me mostra os numeros"

NAO requer confirmacao - e apenas leitura de dados.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "periodo": {
                "type": "string",
                "enum": ["hoje", "ontem", "semana", "mes"],
                "description": "Periodo para buscar metricas"
            },
            "tipo": {
                "type": "string",
                "enum": ["geral", "respostas", "envios", "conversoes"],
                "description": "Tipo de metrica. Use 'geral' para visao completa."
            }
        },
        "required": ["periodo"]
    }
}

TOOL_COMPARAR_PERIODOS = {
    "name": "comparar_periodos",
    "description": """Compara metricas entre dois periodos.

QUANDO USAR:
- Gestor pergunta comparacao entre periodos
- Gestor quer ver evolucao/tendencia
- Gestor menciona "vs", "comparado com", "em relacao a"

EXEMPLOS:
- "como ta essa semana comparado com a anterior?"
- "hoje foi melhor que ontem?"
- "evoluiu do mes passado pra ca?"

NAO requer confirmacao - e apenas leitura de dados.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "periodo1": {
                "type": "string",
                "enum": ["hoje", "ontem", "semana", "semana_passada", "mes", "mes_passado"],
                "description": "Primeiro periodo (mais recente)"
            },
            "periodo2": {
                "type": "string",
                "enum": ["hoje", "ontem", "semana", "semana_passada", "mes", "mes_passado"],
                "description": "Segundo periodo (para comparacao)"
            }
        },
        "required": ["periodo1", "periodo2"]
    }
}


# =============================================================================
# FUNCOES AUXILIARES
# =============================================================================

def _calcular_datas_periodo(periodo: str) -> tuple[datetime, datetime]:
    """Calcula data inicio e fim para um periodo."""
    agora = datetime.now(timezone.utc)

    if periodo == "hoje":
        data_inicio = agora.replace(hour=0, minute=0, second=0, microsecond=0)
        data_fim = agora
    elif periodo == "ontem":
        data_inicio = (agora - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        data_fim = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    elif periodo == "semana":
        data_inicio = agora - timedelta(days=7)
        data_fim = agora
    elif periodo == "semana_passada":
        data_inicio = agora - timedelta(days=14)
        data_fim = agora - timedelta(days=7)
    elif periodo == "mes":
        data_inicio = agora - timedelta(days=30)
        data_fim = agora
    elif periodo == "mes_passado":
        data_inicio = agora - timedelta(days=60)
        data_fim = agora - timedelta(days=30)
    else:
        data_inicio = agora.replace(hour=0, minute=0, second=0, microsecond=0)
        data_fim = agora

    return data_inicio, data_fim


async def _buscar_metricas_periodo(data_inicio: datetime, data_fim: datetime) -> dict:
    """Busca metricas para um periodo especifico."""
    data_inicio_str = data_inicio.isoformat()
    data_fim_str = data_fim.isoformat()

    # Mensagens enviadas
    msgs_enviadas = supabase.table("fila_mensagens").select(
        "id", count="exact"
    ).eq("status", "enviada").gte("enviada_em", data_inicio_str).lte("enviada_em", data_fim_str).execute()

    # Respostas recebidas (interacoes de entrada)
    respostas = supabase.table("interacoes").select(
        "id", count="exact"
    ).eq("tipo", "entrada").gte("created_at", data_inicio_str).lte("created_at", data_fim_str).execute()

    # Conversas com sentimento positivo
    positivas = supabase.table("conversations").select(
        "id", count="exact"
    ).eq("sentimento", "positivo").gte("updated_at", data_inicio_str).lte("updated_at", data_fim_str).execute()

    # Conversas com sentimento negativo
    negativas = supabase.table("conversations").select(
        "id", count="exact"
    ).eq("sentimento", "negativo").gte("updated_at", data_inicio_str).lte("updated_at", data_fim_str).execute()

    # Opt-outs
    optouts = supabase.table("clientes").select(
        "id", count="exact"
    ).eq("opted_out", True).gte("opted_out_at", data_inicio_str).lte("opted_out_at", data_fim_str).execute()

    # Vagas reservadas
    vagas_reservadas = supabase.table("vagas").select(
        "id", count="exact"
    ).eq("status", "reservada").gte("updated_at", data_inicio_str).lte("updated_at", data_fim_str).execute()

    total_enviadas = msgs_enviadas.count or 0
    total_respostas = respostas.count or 0
    total_positivas = positivas.count or 0
    total_negativas = negativas.count or 0
    total_optouts = optouts.count or 0
    total_reservas = vagas_reservadas.count or 0

    taxa_resposta = round((total_respostas / total_enviadas * 100), 1) if total_enviadas > 0 else 0

    return {
        "enviadas": total_enviadas,
        "respostas": total_respostas,
        "taxa_resposta": taxa_resposta,
        "positivas": total_positivas,
        "negativas": total_negativas,
        "optouts": total_optouts,
        "vagas_reservadas": total_reservas
    }


# =============================================================================
# HANDLERS
# =============================================================================

async def handle_buscar_metricas(params: dict) -> dict:
    """Busca metricas de performance."""
    periodo = params.get("periodo", "hoje")

    try:
        data_inicio, data_fim = _calcular_datas_periodo(periodo)
        metricas = await _buscar_metricas_periodo(data_inicio, data_fim)

        return {
            "success": True,
            "periodo": periodo,
            "metricas": metricas
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_comparar_periodos(params: dict) -> dict:
    """Compara metricas entre dois periodos."""
    periodo1 = params.get("periodo1", "semana")
    periodo2 = params.get("periodo2", "semana_passada")

    try:
        # Buscar metricas dos dois periodos
        data_inicio1, data_fim1 = _calcular_datas_periodo(periodo1)
        data_inicio2, data_fim2 = _calcular_datas_periodo(periodo2)

        metricas1 = await _buscar_metricas_periodo(data_inicio1, data_fim1)
        metricas2 = await _buscar_metricas_periodo(data_inicio2, data_fim2)

        # Calcular variacoes
        def calcular_variacao(v1, v2):
            if v2 == 0:
                return "+100%" if v1 > 0 else "0%"
            diff = ((v1 - v2) / v2) * 100
            sinal = "+" if diff > 0 else ""
            return f"{sinal}{round(diff, 1)}%"

        variacao_taxa = metricas1["taxa_resposta"] - metricas2["taxa_resposta"]
        tendencia = "melhora" if variacao_taxa > 0 else "piora" if variacao_taxa < 0 else "estavel"

        return {
            "success": True,
            "periodo1": {
                "nome": periodo1,
                "metricas": metricas1
            },
            "periodo2": {
                "nome": periodo2,
                "metricas": metricas2
            },
            "variacao": {
                "taxa_resposta": f"{'+' if variacao_taxa > 0 else ''}{round(variacao_taxa, 1)} pontos",
                "enviadas": calcular_variacao(metricas1["enviadas"], metricas2["enviadas"]),
                "respostas": calcular_variacao(metricas1["respostas"], metricas2["respostas"]),
                "tendencia": tendencia
            }
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
