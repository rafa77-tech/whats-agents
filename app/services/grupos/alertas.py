"""
Alertas automáticos do pipeline de grupos.

Sprint 14 - E12 - Métricas e Monitoramento
"""

from datetime import datetime, timedelta, UTC
from typing import List, Dict

from app.core.logging import get_logger
from app.services.supabase import supabase
from app.services.slack import enviar_slack

logger = get_logger(__name__)


# =============================================================================
# Configuração de Alertas
# =============================================================================

ALERTAS_GRUPOS = {
    "fila_travada": {
        "descricao": "Muitos itens com erro na fila",
        "threshold": 10,  # > 10 itens com erro
        "severidade": "error"
    },
    "taxa_conversao_baixa": {
        "descricao": "Taxa de conversão abaixo do esperado",
        "threshold": 0.05,  # < 5% de conversão
        "janela_dias": 1,
        "severidade": "warning"
    },
    "custo_alto": {
        "descricao": "Custo diário acima do orçamento",
        "threshold_usd": 1.0,  # > $1/dia
        "severidade": "warning"
    },
    "itens_pendentes_antigos": {
        "descricao": "Itens pendentes sem processar há muito tempo",
        "threshold_horas": 4,  # > 4 horas pendente
        "threshold_quantidade": 5,  # > 5 itens
        "severidade": "warning"
    },
    "duplicacao_alta": {
        "descricao": "Taxa de duplicação muito alta",
        "threshold": 0.5,  # > 50% duplicados
        "janela_dias": 1,
        "severidade": "info"
    },
}

# Títulos amigáveis para exibição ao usuário (Slack, logs)
TITULOS_ALERTAS = {
    "fila_travada": "Fila com Muitos Erros",
    "taxa_conversao_baixa": "Taxa de Conversão Baixa",
    "custo_alto": "Custo Diário Elevado",
    "itens_pendentes_antigos": "Itens Pendentes Há Muito Tempo",
    "duplicacao_alta": "Alta Taxa de Duplicação",
}


# =============================================================================
# Verificadores de Alertas
# =============================================================================

async def verificar_fila_travada() -> List[Dict]:
    """Verifica se há muitos itens com erro na fila."""
    config = ALERTAS_GRUPOS["fila_travada"]

    try:
        result = supabase.table("fila_processamento_grupos") \
            .select("id", count="exact") \
            .eq("estagio", "erro") \
            .execute()

        total_erros = result.count or 0

        if total_erros > config["threshold"]:
            return [{
                "tipo": "fila_travada",
                "mensagem": f"Pipeline grupos: {total_erros} itens com erro (threshold: {config['threshold']})",
                "severidade": config["severidade"],
                "valor": total_erros
            }]

        return []
    except Exception as e:
        logger.error(f"Erro ao verificar fila travada: {e}")
        return []


async def verificar_taxa_conversao() -> List[Dict]:
    """Verifica se taxa de conversão está baixa."""
    config = ALERTAS_GRUPOS["taxa_conversao_baixa"]
    data_inicio = (datetime.now(UTC) - timedelta(days=config["janela_dias"])).isoformat()

    try:
        # Total de vagas criadas
        vagas_total = supabase.table("vagas_grupo") \
            .select("id", count="exact") \
            .gte("created_at", data_inicio) \
            .execute()

        # Vagas importadas
        vagas_importadas = supabase.table("vagas_grupo") \
            .select("id", count="exact") \
            .eq("status", "importada") \
            .gte("created_at", data_inicio) \
            .execute()

        total = vagas_total.count or 0
        importadas = vagas_importadas.count or 0

        if total > 0:
            taxa = importadas / total
            if taxa < config["threshold"]:
                return [{
                    "tipo": "taxa_conversao_baixa",
                    "mensagem": f"Taxa de conversão: {taxa*100:.1f}% (threshold: {config['threshold']*100}%)",
                    "severidade": config["severidade"],
                    "valor": taxa
                }]

        return []
    except Exception as e:
        logger.error(f"Erro ao verificar taxa de conversão: {e}")
        return []


async def verificar_custo_alto() -> List[Dict]:
    """Verifica se custo diário está acima do orçamento."""
    config = ALERTAS_GRUPOS["custo_alto"]
    hoje = datetime.now(UTC).date().isoformat()

    try:
        result = supabase.table("metricas_pipeline_diarias") \
            .select("custo_total_usd") \
            .eq("data", hoje) \
            .single() \
            .execute()

        if result.data:
            custo = float(result.data.get("custo_total_usd", 0) or 0)

            if custo > config["threshold_usd"]:
                return [{
                    "tipo": "custo_alto",
                    "mensagem": f"Custo hoje: ${custo:.4f} (orçamento: ${config['threshold_usd']:.2f})",
                    "severidade": config["severidade"],
                    "valor": custo
                }]

        return []
    except Exception as e:
        # Pode não existir registro para hoje ainda
        logger.debug(f"Erro ao verificar custo alto (pode ser normal): {e}")
        return []


async def verificar_itens_pendentes_antigos() -> List[Dict]:
    """Verifica se há itens pendentes há muito tempo."""
    config = ALERTAS_GRUPOS["itens_pendentes_antigos"]
    limite_tempo = (datetime.now(UTC) - timedelta(hours=config["threshold_horas"])).isoformat()

    try:
        result = supabase.table("fila_processamento_grupos") \
            .select("id", count="exact") \
            .eq("estagio", "pendente") \
            .lt("created_at", limite_tempo) \
            .execute()

        total_antigos = result.count or 0

        if total_antigos > config["threshold_quantidade"]:
            return [{
                "tipo": "itens_pendentes_antigos",
                "mensagem": f"{total_antigos} itens pendentes há mais de {config['threshold_horas']}h",
                "severidade": config["severidade"],
                "valor": total_antigos
            }]

        return []
    except Exception as e:
        logger.error(f"Erro ao verificar itens pendentes antigos: {e}")
        return []


async def verificar_duplicacao_alta() -> List[Dict]:
    """Verifica se taxa de duplicação está muito alta."""
    config = ALERTAS_GRUPOS["duplicacao_alta"]
    data_inicio = (datetime.now(UTC) - timedelta(days=config["janela_dias"])).isoformat()

    try:
        # Total de vagas
        vagas_total = supabase.table("vagas_grupo") \
            .select("id", count="exact") \
            .gte("created_at", data_inicio) \
            .execute()

        # Vagas duplicadas
        vagas_duplicadas = supabase.table("vagas_grupo") \
            .select("id", count="exact") \
            .eq("eh_duplicada", True) \
            .gte("created_at", data_inicio) \
            .execute()

        total = vagas_total.count or 0
        duplicadas = vagas_duplicadas.count or 0

        if total > 0:
            taxa = duplicadas / total
            if taxa > config["threshold"]:
                return [{
                    "tipo": "duplicacao_alta",
                    "mensagem": f"Taxa de duplicação: {taxa*100:.1f}% (threshold: {config['threshold']*100}%)",
                    "severidade": config["severidade"],
                    "valor": taxa
                }]

        return []
    except Exception as e:
        logger.error(f"Erro ao verificar taxa de duplicação: {e}")
        return []


# =============================================================================
# Executor de Alertas
# =============================================================================

async def verificar_alertas_grupos() -> List[Dict]:
    """
    Verifica todas as condições de alerta do pipeline de grupos.

    Returns:
        Lista de alertas ativos
    """
    alertas = []

    alertas.extend(await verificar_fila_travada())
    alertas.extend(await verificar_taxa_conversao())
    alertas.extend(await verificar_custo_alto())
    alertas.extend(await verificar_itens_pendentes_antigos())
    alertas.extend(await verificar_duplicacao_alta())

    return alertas


async def enviar_alerta_grupos_slack(alerta: Dict):
    """Envia alerta de grupos para Slack."""
    cores = {
        "info": "#2196F3",
        "warning": "#FF9800",
        "error": "#F44336",
        "critical": "#9C27B0",
    }
    cor = cores.get(alerta["severidade"], "#607D8B")

    emoji = {
        "info": "ℹ️",
        "warning": "⚠️",
        "error": "🚨",
        "critical": "🔴",
    }

    titulo = TITULOS_ALERTAS.get(alerta["tipo"], alerta["tipo"])

    mensagem = {
        "text": f"{emoji.get(alerta['severidade'], '⚠️')} Pipeline Grupos: {titulo}",
        "attachments": [{
            "color": cor,
            "fields": [
                {"title": "Descrição", "value": alerta["mensagem"], "short": False},
                {"title": "Severidade", "value": alerta["severidade"].upper(), "short": True},
                {"title": "Horário", "value": datetime.now(UTC).strftime("%H:%M"), "short": True},
            ]
        }]
    }

    await enviar_slack(mensagem)


async def executar_verificacao_alertas_grupos():
    """
    Job para verificar alertas do pipeline de grupos periodicamente.

    Deve ser executado a cada 15-30 minutos via scheduler.
    """
    try:
        alertas = await verificar_alertas_grupos()

        if alertas:
            logger.info(f"Encontrados {len(alertas)} alertas do pipeline de grupos")

            for alerta in alertas:
                await enviar_alerta_grupos_slack(alerta)

                # Registrar alerta no log
                titulo = TITULOS_ALERTAS.get(alerta['tipo'], alerta['tipo'])
                logger.warning(f"Alerta grupos: {titulo} - {alerta['mensagem']}")

        return alertas

    except Exception as e:
        logger.error(f"Erro ao executar verificação de alertas grupos: {e}")
        return []
