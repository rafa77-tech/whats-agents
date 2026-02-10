"""
Worker para processamento de mensagens de grupos WhatsApp.

Sprint 14 - E11 - Worker e Orquestração

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


class GruposWorker:
    """Worker para processar mensagens de grupos."""

    def __init__(self, batch_size: int = 50, intervalo_segundos: int = 10, max_workers: int = 5):
        """
        Inicializa o worker.

        Args:
            batch_size: Quantidade de itens a processar por ciclo
            intervalo_segundos: Intervalo entre ciclos
            max_workers: Máximo de processamentos paralelos
        """
        self.batch_size = batch_size
        self.intervalo = intervalo_segundos
        self.max_workers = max_workers
        self.pipeline = PipelineGrupos()
        self.running = False
        self._stats = {"ciclos": 0, "processados": 0, "erros": 0}

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

        Returns:
            Estatísticas do ciclo
        """
        self._stats["ciclos"] += 1
        stats = {"processados": 0, "erros": 0}

        # Processar cada estágio em ordem
        # Cada estágio tem seu handler no pipeline
        estagios = [
            (EstagioPipeline.PENDENTE, "processar_pendente"),
            (EstagioPipeline.HEURISTICA, "processar_pendente"),  # Heurística é parte do pendente
            (EstagioPipeline.CLASSIFICACAO, "processar_classificacao"),
            (EstagioPipeline.EXTRACAO, "processar_extracao"),
            (EstagioPipeline.NORMALIZACAO, "processar_normalizacao"),
            (EstagioPipeline.DEDUPLICACAO, "processar_deduplicacao"),
            (EstagioPipeline.IMPORTACAO, "processar_importacao"),
        ]

        for estagio, handler_name in estagios:
            # Buscar itens pendentes neste estágio
            itens = await buscar_proximos_pendentes(estagio, self.batch_size)

            if not itens:
                continue

            logger.info(f"Processando {len(itens)} itens em {estagio.value}")

            # Processar em paralelo (limitado por semaphore)
            semaphore = asyncio.Semaphore(self.max_workers)
            handler = getattr(self.pipeline, handler_name)

            async def processar_item(item: dict, estagio_atual: EstagioPipeline):
                async with semaphore:
                    try:
                        resultado = await handler(item)
                        proximo_estagio = mapear_acao_para_estagio(resultado.acao)

                        # Se extração criou múltiplas vagas, criar itens separados
                        if resultado.vagas_criadas and len(resultado.vagas_criadas) > 0:
                            await criar_itens_para_vagas(
                                mensagem_id=resultado.mensagem_id, vagas_ids=resultado.vagas_criadas
                            )
                            # Item original marcado como finalizado (vagas já criadas)
                            await atualizar_estagio(
                                item_id=UUID(item["id"]),
                                novo_estagio=EstagioPipeline.FINALIZADO,
                            )
                        else:
                            # Fluxo normal - atualizar estágio
                            await atualizar_estagio(
                                item_id=UUID(item["id"]),
                                novo_estagio=EstagioPipeline(proximo_estagio),
                                vaga_grupo_id=resultado.vaga_grupo_id,
                                erro=resultado.motivo if resultado.acao == "erro" else None,
                            )

                        stats["processados"] += 1
                        self._stats["processados"] += 1

                    except Exception as e:
                        logger.error(f"Erro ao processar item {item['id']}: {e}")
                        # Mantém no mesmo estágio para retry
                        await atualizar_estagio(
                            item_id=UUID(item["id"]), novo_estagio=estagio_atual, erro=str(e)[:500]
                        )
                        stats["erros"] += 1
                        self._stats["erros"] += 1

            # Executar todos em paralelo
            await asyncio.gather(*[processar_item(item, estagio) for item in itens])

        if stats["processados"] > 0 or stats["erros"] > 0:
            logger.info(f"Ciclo concluído: {stats}")

        return stats

    @property
    def stats(self) -> dict:
        """Retorna estatísticas do worker."""
        return self._stats.copy()


# =============================================================================
# Função para execução via job/endpoint
# =============================================================================


async def processar_ciclo_grupos(batch_size: int = 50, max_workers: int = 5) -> dict:
    """
    Processa um ciclo de mensagens de grupos.

    Função chamada pelo endpoint de job.

    Args:
        batch_size: Quantidade de itens por estágio
        max_workers: Processamentos paralelos

    Returns:
        Resultado do processamento
    """
    worker = GruposWorker(batch_size=batch_size, max_workers=max_workers)

    try:
        stats = await worker.processar_ciclo()

        # Obter estatísticas da fila
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

    # Estatísticas da fila
    fila_stats = await obter_estatisticas_fila()

    # Itens travados (>1h sem atualização)
    travados = await obter_itens_travados(horas=1)

    # Determinar status
    status = "healthy"
    if len(travados) > 100:
        status = "degraded"
    if len(travados) > 500:
        status = "unhealthy"

    return {
        "status": status,
        "fila": fila_stats,
        "travados": len(travados),
        "timestamp": datetime.now(UTC).isoformat(),
    }
