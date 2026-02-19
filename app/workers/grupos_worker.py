"""
Worker para processamento de mensagens de grupos WhatsApp.

Sprint 14 - E11 - Worker e Orquestração
Sprint 63 - Escalabilidade: estágios em paralelo, semáforos por tipo, guard de ciclo

Processa mensagens em batch através do pipeline:
Pendente -> Heurística -> Classificação -> Extração -> Normalização -> Deduplicação -> Importação
"""

import asyncio
from uuid import UUID

from app.core.logging import get_logger
from app.services.grupos.fila import (
    EstagioPipeline,
    buscar_proximos_pendentes,
    atualizar_estagio,
    obter_estatisticas_fila,
    criar_itens_para_vagas,
)
from app.services.grupos.pipeline_worker import PipelineGrupos, mapear_acao_para_estagio

logger = get_logger(__name__)


# =============================================================================
# Budget de concorrência por tipo de estágio
# =============================================================================

# Estágios que chamam LLM (Anthropic rate limit)
_ESTAGIOS_LLM = {EstagioPipeline.CLASSIFICACAO, EstagioPipeline.EXTRACAO}

# Estágios que chamam APIs externas (CNES, Google Places)
_ESTAGIOS_API_EXTERNA = {EstagioPipeline.NORMALIZACAO}

# Estágios apenas banco/CPU (rápidos)
_ESTAGIOS_DB = {
    EstagioPipeline.PENDENTE,
    EstagioPipeline.HEURISTICA,
    EstagioPipeline.DEDUPLICACAO,
    EstagioPipeline.IMPORTACAO,
}

# Limites por tipo
BUDGET_LLM = 5
BUDGET_API_EXTERNA = 10
BUDGET_DB = 20


def _semaforo_para_estagio(
    estagio: EstagioPipeline,
    semaforos: dict[str, asyncio.Semaphore],
) -> asyncio.Semaphore:
    """Retorna o semáforo adequado para o tipo de estágio."""
    if estagio in _ESTAGIOS_LLM:
        return semaforos["llm"]
    if estagio in _ESTAGIOS_API_EXTERNA:
        return semaforos["api_externa"]
    return semaforos["db"]


class GruposWorker:
    """Worker para processar mensagens de grupos."""

    def __init__(self, batch_size: int = 50, intervalo_segundos: int = 10, max_workers: int = 20):
        """
        Inicializa o worker.

        Args:
            batch_size: Quantidade de itens a processar por ciclo por estágio
            intervalo_segundos: Intervalo entre ciclos
            max_workers: Máximo global de processamentos paralelos (fallback)
        """
        self.batch_size = batch_size
        self.intervalo = intervalo_segundos
        self.max_workers = max_workers
        self.pipeline = PipelineGrupos()
        self.running = False
        self._stats = {"ciclos": 0, "processados": 0, "erros": 0}

        # Semáforos por tipo de recurso (persistem entre ciclos)
        self._semaforos: dict[str, asyncio.Semaphore] = {
            "llm": asyncio.Semaphore(BUDGET_LLM),
            "api_externa": asyncio.Semaphore(BUDGET_API_EXTERNA),
            "db": asyncio.Semaphore(BUDGET_DB),
        }

    async def start(self):
        """Inicia o worker em loop contínuo."""
        self.running = True
        logger.info(f"GruposWorker iniciado (batch={self.batch_size}, workers={self.max_workers})")

        while self.running:
            try:
                await self.processar_ciclo()
            except Exception as e:
                logger.error(f"Erro no ciclo do worker: {e}", exc_info=True)

            await asyncio.sleep(self.intervalo)

    async def stop(self):
        """Para o worker."""
        self.running = False
        logger.info(f"GruposWorker parado. Stats: {self._stats}")

    async def processar_ciclo(self) -> dict:
        """
        Processa um ciclo completo de todas as filas.

        Estágios rodam em paralelo (não sequencial) com semáforos por tipo
        de recurso para evitar sobrecarga de LLM ou APIs externas.

        Returns:
            Estatísticas do ciclo
        """
        self._stats["ciclos"] += 1
        stats = {"processados": 0, "erros": 0, "por_estagio": {}}

        estagios = [
            (EstagioPipeline.PENDENTE, "processar_pendente"),
            (EstagioPipeline.HEURISTICA, "processar_pendente"),
            (EstagioPipeline.CLASSIFICACAO, "processar_classificacao"),
            (EstagioPipeline.EXTRACAO, "processar_extracao"),
            (EstagioPipeline.NORMALIZACAO, "processar_normalizacao"),
            (EstagioPipeline.DEDUPLICACAO, "processar_deduplicacao"),
            (EstagioPipeline.IMPORTACAO, "processar_importacao"),
        ]

        async def processar_estagio(
            estagio: EstagioPipeline,
            handler_name: str,
        ) -> dict:
            """Processa todos os itens de um estágio."""
            estagio_stats = {"processados": 0, "erros": 0}

            itens = await buscar_proximos_pendentes(estagio, self.batch_size)
            if not itens:
                return estagio_stats

            logger.info(f"Processando {len(itens)} itens em {estagio.value}")

            handler = getattr(self.pipeline, handler_name)
            semaphore = _semaforo_para_estagio(estagio, self._semaforos)

            async def processar_item(item: dict):
                async with semaphore:
                    try:
                        resultado = await handler(item)
                        proximo_estagio = mapear_acao_para_estagio(resultado.acao)

                        if resultado.vagas_criadas and len(resultado.vagas_criadas) > 0:
                            await criar_itens_para_vagas(
                                mensagem_id=resultado.mensagem_id,
                                vagas_ids=resultado.vagas_criadas,
                            )
                            await atualizar_estagio(
                                item_id=UUID(item["id"]),
                                novo_estagio=EstagioPipeline.FINALIZADO,
                            )
                        else:
                            await atualizar_estagio(
                                item_id=UUID(item["id"]),
                                novo_estagio=EstagioPipeline(proximo_estagio),
                                vaga_grupo_id=resultado.vaga_grupo_id,
                                erro=resultado.motivo if resultado.acao == "erro" else None,
                            )

                        estagio_stats["processados"] += 1

                    except Exception as e:
                        logger.error(f"Erro ao processar item {item['id']}: {e}")
                        await atualizar_estagio(
                            item_id=UUID(item["id"]),
                            novo_estagio=estagio,
                            erro=str(e)[:500],
                        )
                        estagio_stats["erros"] += 1

            await asyncio.gather(*[processar_item(item) for item in itens])
            return estagio_stats

        # Rodar todos os estágios em paralelo
        resultados = await asyncio.gather(*[
            processar_estagio(estagio, handler_name)
            for estagio, handler_name in estagios
        ])

        # Consolidar estatísticas
        for (estagio, _), resultado in zip(estagios, resultados):
            stats["processados"] += resultado["processados"]
            stats["erros"] += resultado["erros"]
            if resultado["processados"] > 0 or resultado["erros"] > 0:
                stats["por_estagio"][estagio.value] = resultado

        self._stats["processados"] += stats["processados"]
        self._stats["erros"] += stats["erros"]

        if stats["processados"] > 0 or stats["erros"] > 0:
            logger.info(f"Ciclo concluído: {stats['processados']} ok, {stats['erros']} erros")

        return stats

    @property
    def stats(self) -> dict:
        """Retorna estatísticas do worker."""
        return self._stats.copy()


# =============================================================================
# Guard contra ciclos sobrepostos
# =============================================================================

_ciclo_lock = asyncio.Lock()


async def processar_ciclo_grupos(batch_size: int = 50, max_workers: int = 20) -> dict:
    """
    Processa um ciclo de mensagens de grupos.

    Usa lock para evitar ciclos sobrepostos (se o scheduler dispara
    antes do ciclo anterior terminar, o novo ciclo é ignorado).

    Args:
        batch_size: Quantidade de itens por estágio
        max_workers: Processamentos paralelos (fallback)

    Returns:
        Resultado do processamento
    """
    if _ciclo_lock.locked():
        logger.debug("Ciclo de grupos ignorado: ciclo anterior ainda em andamento")
        return {"sucesso": True, "skipped": True, "motivo": "ciclo_anterior_em_andamento"}

    async with _ciclo_lock:
        worker = GruposWorker(batch_size=batch_size, max_workers=max_workers)

        try:
            stats = await worker.processar_ciclo()
            fila_stats = await obter_estatisticas_fila()

            return {"sucesso": True, "ciclo": stats, "fila": fila_stats}

        except Exception as e:
            logger.error(f"Erro ao processar ciclo de grupos: {e}", exc_info=True)
            return {"sucesso": False, "erro": str(e)}


async def obter_status_worker() -> dict:
    """
    Obtém status atual do processamento de grupos.

    Returns:
        Status com métricas da fila
    """
    from datetime import datetime, UTC
    from app.services.grupos.fila import obter_itens_travados

    fila_stats = await obter_estatisticas_fila()
    travados = await obter_itens_travados(horas=1)

    status = "healthy"
    if len(travados) > 100:
        status = "degraded"
    if len(travados) > 500:
        status = "unhealthy"

    return {
        "status": status,
        "fila": fila_stats,
        "travados": len(travados),
        "ciclo_em_andamento": _ciclo_lock.locked(),
        "timestamp": datetime.now(UTC).isoformat(),
    }
