"""
Coleta e armazenamento de métricas do pipeline de grupos.

Sprint 14 - E12 - Métricas e Monitoramento
"""

import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional, List
from uuid import UUID

from app.core.logging import get_logger
from app.services.supabase import supabase

logger = get_logger(__name__)


# =============================================================================
# S12.2 - Estruturas de Métricas
# =============================================================================


@dataclass
class MetricasProcessamento:
    """Métricas coletadas durante processamento de uma mensagem."""

    inicio: float = field(default_factory=time.time)
    fim: Optional[float] = None

    # Contadores
    mensagens_processadas: int = 0
    vagas_extraidas: int = 0

    # Tempos (ms)
    tempo_heuristica_ms: int = 0
    tempo_llm_ms: int = 0
    tempo_extracao_ms: int = 0
    tempo_normalizacao_ms: int = 0

    # LLM
    tokens_input: int = 0
    tokens_output: int = 0

    # Resultado
    resultado: Optional[str] = None  # "importado", "revisao", "descartado", "duplicado"
    confianca: Optional[float] = None

    # Contexto
    grupo_id: Optional[UUID] = None

    def finalizar(self):
        """Marca fim do processamento."""
        self.fim = time.time()

    @property
    def tempo_total_ms(self) -> int:
        """Tempo total de processamento em ms."""
        if self.fim:
            return int((self.fim - self.inicio) * 1000)
        return 0

    @property
    def custo_estimado(self) -> float:
        """Custo estimado em USD (baseado em preços Claude Haiku)."""
        # Claude Haiku: $0.25/1M input, $1.25/1M output
        custo_input = self.tokens_input * 0.25 / 1_000_000
        custo_output = self.tokens_output * 1.25 / 1_000_000
        return custo_input + custo_output


# =============================================================================
# S12.2 - Coletor de Métricas
# =============================================================================


class ColetorMetricas:
    """Coleta e persiste métricas de processamento."""

    def __init__(self, flush_threshold: int = 100):
        """
        Inicializa coletor.

        Args:
            flush_threshold: Quantidade de métricas antes de flush automático
        """
        self.metricas_pendentes: List[dict] = []
        self.flush_threshold = flush_threshold

    async def registrar(self, grupo_id: UUID, metricas: MetricasProcessamento) -> None:
        """
        Registra métricas de um processamento.

        Args:
            grupo_id: ID do grupo
            metricas: Métricas coletadas
        """
        self.metricas_pendentes.append(
            {
                "grupo_id": str(grupo_id),
                "data": date.today().isoformat(),
                "metricas": metricas,
            }
        )

        # Flush automático
        if len(self.metricas_pendentes) >= self.flush_threshold:
            await self.flush()

    async def flush(self) -> int:
        """
        Persiste métricas pendentes no banco.

        Returns:
            Quantidade de grupos atualizados
        """
        if not self.metricas_pendentes:
            return 0

        # Agregar por grupo/data
        agregado = {}
        for item in self.metricas_pendentes:
            key = (item["data"], item["grupo_id"])
            if key not in agregado:
                agregado[key] = {
                    "mensagens_processadas": 0,
                    "vagas_extraidas": 0,
                    "tokens_input": 0,
                    "tokens_output": 0,
                    "tempos": [],
                    "confiancas": [],
                    "custos": [],
                }

            m = item["metricas"]
            agregado[key]["mensagens_processadas"] += 1
            agregado[key]["vagas_extraidas"] += m.vagas_extraidas
            agregado[key]["tokens_input"] += m.tokens_input
            agregado[key]["tokens_output"] += m.tokens_output
            agregado[key]["tempos"].append(m.tempo_total_ms)
            agregado[key]["custos"].append(m.custo_estimado)
            if m.confianca:
                agregado[key]["confiancas"].append(m.confianca)

        # Upsert no banco
        count = 0
        for (data, grupo_id), valores in agregado.items():
            try:
                await self._upsert_metricas_grupo(data, grupo_id, valores)
                count += 1
            except Exception as e:
                logger.error(f"Erro ao persistir métricas {grupo_id}: {e}")

        logger.info(
            f"Métricas persistidas: {count} grupos, {len(self.metricas_pendentes)} registros"
        )
        self.metricas_pendentes = []

        return count

    async def _upsert_metricas_grupo(self, data: str, grupo_id: str, valores: dict) -> None:
        """
        Atualiza ou insere métricas do grupo.

        Args:
            data: Data no formato ISO
            grupo_id: ID do grupo
            valores: Valores agregados
        """
        # Calcular médias
        tempo_medio = (
            sum(valores["tempos"]) // len(valores["tempos"]) if valores["tempos"] else None
        )
        confianca_media = (
            sum(valores["confiancas"]) / len(valores["confiancas"])
            if valores["confiancas"]
            else None
        )
        custo_total = sum(valores["custos"])

        # Usar RPC para upsert atômico
        supabase.rpc(
            "incrementar_metricas_grupo",
            {
                "p_data": data,
                "p_grupo_id": grupo_id,
                "p_mensagens": valores["mensagens_processadas"],
                "p_vagas": valores["vagas_extraidas"],
                "p_tokens_in": valores["tokens_input"],
                "p_tokens_out": valores["tokens_output"],
                "p_tempo_medio": tempo_medio,
                "p_confianca": confianca_media,
                "p_custo": custo_total,
            },
        ).execute()


# Instância global
coletor_metricas = ColetorMetricas()


# =============================================================================
# Funções Auxiliares de Consulta
# =============================================================================


async def obter_metricas_dia(data_consulta: Optional[date] = None) -> dict:
    """
    Obtém métricas consolidadas de um dia.

    Args:
        data_consulta: Data a consultar (default: hoje)

    Returns:
        Métricas consolidadas
    """
    if not data_consulta:
        data_consulta = date.today()

    result = (
        supabase.table("metricas_pipeline_diarias")
        .select("*")
        .eq("data", data_consulta.isoformat())
        .single()
        .execute()
    )

    return result.data or {}


async def obter_metricas_periodo(dias: int = 7) -> dict:
    """
    Obtém métricas de um período.

    Args:
        dias: Quantidade de dias a consultar

    Returns:
        Métricas agregadas do período
    """
    data_inicio = (date.today() - timedelta(days=dias)).isoformat()

    result = (
        supabase.table("metricas_pipeline_diarias")
        .select("*")
        .gte("data", data_inicio)
        .order("data", desc=True)
        .execute()
    )

    if not result.data:
        return {"periodo": f"{dias}d", "dados": []}

    # Calcular totais
    totais = {
        "mensagens": sum(r.get("mensagens_processadas", 0) or 0 for r in result.data),
        "vagas_importadas": sum(r.get("vagas_importadas", 0) or 0 for r in result.data),
        "vagas_revisao": sum(r.get("vagas_revisao", 0) or 0 for r in result.data),
        "vagas_duplicadas": sum(r.get("vagas_duplicadas", 0) or 0 for r in result.data),
        "custo_usd": sum(float(r.get("custo_total_usd", 0) or 0) for r in result.data),
        "grupos_ativos": max((r.get("grupos_ativos", 0) or 0) for r in result.data),
    }

    # Taxas
    if totais["mensagens"] > 0:
        totais["taxa_conversao"] = totais["vagas_importadas"] / totais["mensagens"]

    total_vagas = totais["vagas_importadas"] + totais["vagas_duplicadas"]
    if total_vagas > 0:
        totais["taxa_duplicacao"] = totais["vagas_duplicadas"] / total_vagas

    return {
        "periodo": f"{dias}d",
        "data_inicio": data_inicio,
        "totais": totais,
        "por_dia": result.data,
    }


async def obter_top_grupos(dias: int = 7, limite: int = 10) -> List[dict]:
    """
    Obtém grupos com mais vagas importadas.

    Args:
        dias: Período a considerar
        limite: Máximo de grupos

    Returns:
        Lista de grupos ordenados por vagas
    """
    data_inicio = (date.today() - timedelta(days=dias)).isoformat()

    # Query agregada
    result = supabase.rpc(
        "top_grupos_vagas", {"p_data_inicio": data_inicio, "p_limite": limite}
    ).execute()

    return result.data or []


async def obter_status_fila() -> dict:
    """
    Obtém status atual da fila de processamento.

    Returns:
        Status com pendentes, em processamento, etc.
    """
    result = supabase.rpc("status_fila_grupos").execute()
    return result.data[0] if result.data else {}


async def consolidar_metricas_dia(data_consolidar: Optional[date] = None) -> bool:
    """
    Consolida métricas de grupos para métricas de pipeline.

    Args:
        data_consolidar: Data a consolidar (default: ontem)

    Returns:
        True se consolidação foi bem-sucedida
    """
    if not data_consolidar:
        data_consolidar = date.today() - timedelta(days=1)

    try:
        supabase.rpc(
            "consolidar_metricas_pipeline", {"p_data": data_consolidar.isoformat()}
        ).execute()

        logger.info(f"Métricas consolidadas para {data_consolidar}")
        return True

    except Exception as e:
        logger.error(f"Erro ao consolidar métricas: {e}")
        return False
