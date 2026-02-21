"""
Warming Orchestrator - Orquestração do ciclo de aquecimento.

Coordena todos os componentes do warmer:
- Trust Score para decisões
- Human Simulator para comportamento natural
- Conversation Generator para conteúdo
- Pairing Engine para pares
- Scheduler para agendamento
- Transições de fase

Sprint 65: Fix timestamp transição, warming_day, critérios grupos, structured logging.
"""

import logging
import asyncio
from typing import Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from app.core.timezone import agora_brasilia
from app.services.supabase import supabase
from app.services.warmer.trust_score import (
    calcular_trust_score,
)
from app.services.warmer.scheduler import (
    scheduler,
    AtividadeAgendada,
)
from app.services.warmer.executor import executar_atividade as _executor_executar

logger = logging.getLogger(__name__)


class FaseWarmup(str, Enum):
    """Fases do processo de warmup."""

    REPOUSO = "repouso"
    SETUP = "setup"
    PRIMEIROS_CONTATOS = "primeiros_contatos"
    EXPANSAO = "expansao"
    PRE_OPERACAO = "pre_operacao"
    TESTE_GRADUACAO = "teste_graduacao"
    OPERACAO = "operacao"


@dataclass
class CriteriosTransicao:
    """Critérios para transição de fase."""

    dias_minimos: int
    msgs_enviadas_min: int
    msgs_recebidas_min: int
    taxa_resposta_min: float
    trust_score_min: int
    conversas_bidirecionais_min: int
    grupos_min: int = 0
    erros_max_24h: int = 5


# Critérios de transição por fase
# Sprint 65: grupos_min=0 em todas as fases (ENTRAR_GRUPO não implementado).
# Compensado com +5 em conversas_bidirecionais_min nas fases que tinham grupos_min > 0.
CRITERIOS_FASE = {
    FaseWarmup.SETUP: CriteriosTransicao(
        dias_minimos=1,
        msgs_enviadas_min=5,
        msgs_recebidas_min=3,
        taxa_resposta_min=0.3,
        trust_score_min=40,
        conversas_bidirecionais_min=2,
    ),
    FaseWarmup.PRIMEIROS_CONTATOS: CriteriosTransicao(
        dias_minimos=3,
        msgs_enviadas_min=20,
        msgs_recebidas_min=10,
        taxa_resposta_min=0.4,
        trust_score_min=50,
        conversas_bidirecionais_min=5,
    ),
    FaseWarmup.EXPANSAO: CriteriosTransicao(
        dias_minimos=7,
        msgs_enviadas_min=50,
        msgs_recebidas_min=25,
        taxa_resposta_min=0.4,
        trust_score_min=55,
        conversas_bidirecionais_min=12,  # Sprint 65: compensação por grupos_min=0
    ),
    FaseWarmup.PRE_OPERACAO: CriteriosTransicao(
        dias_minimos=14,
        msgs_enviadas_min=100,
        msgs_recebidas_min=40,
        taxa_resposta_min=0.35,
        trust_score_min=60,
        conversas_bidirecionais_min=18,  # Sprint 65: compensação por grupos_min=0
    ),
    FaseWarmup.TESTE_GRADUACAO: CriteriosTransicao(
        dias_minimos=21,
        msgs_enviadas_min=150,
        msgs_recebidas_min=50,
        taxa_resposta_min=0.3,
        trust_score_min=70,
        conversas_bidirecionais_min=23,  # Sprint 65: compensação por grupos_min=0
    ),
    FaseWarmup.OPERACAO: CriteriosTransicao(
        dias_minimos=28,
        msgs_enviadas_min=200,
        msgs_recebidas_min=60,
        taxa_resposta_min=0.25,
        trust_score_min=75,
        conversas_bidirecionais_min=28,  # Sprint 65: compensação por grupos_min=0
    ),
}

# Sequência de fases
SEQUENCIA_FASES = [
    FaseWarmup.REPOUSO,
    FaseWarmup.SETUP,
    FaseWarmup.PRIMEIROS_CONTATOS,
    FaseWarmup.EXPANSAO,
    FaseWarmup.PRE_OPERACAO,
    FaseWarmup.TESTE_GRADUACAO,
    FaseWarmup.OPERACAO,
]


class WarmingOrchestrator:
    """Orquestrador principal do sistema de aquecimento."""

    def __init__(self):
        self._ciclo_lock = asyncio.Lock()
        self._chip_locks: dict[str, asyncio.Lock] = {}

    async def iniciar_chip(self, chip_id: str) -> dict:
        """
        Inicia processo de warmup para um chip.

        Args:
            chip_id: ID do chip

        Returns:
            Dict com status da inicialização
        """
        logger.info(f"[Orchestrator] Iniciando warmup para chip {chip_id[:8]}...")

        # Verificar se chip existe e está conectado
        result = (
            supabase.table("chips")
            .select("id, telefone, status, fase_warmup")
            .eq("id", chip_id)
            .single()
            .execute()
        )

        if not result.data:
            return {"success": False, "error": "Chip não encontrado"}

        chip = result.data

        if chip["status"] != "connected":
            return {"success": False, "error": f"Chip não conectado (status: {chip['status']})"}

        # Se já está em warmup, retornar fase atual
        fase_atual = chip.get("fase_warmup", "repouso")
        if fase_atual != "repouso":
            return {
                "success": True,
                "message": "Chip já em warmup",
                "fase": fase_atual,
            }

        # Iniciar na fase setup
        supabase.table("chips").update(
            {
                "fase_warmup": FaseWarmup.SETUP.value,
                "warming_started_at": agora_brasilia().isoformat(),
                "warming_day": 0,
            }
        ).eq("id", chip_id).execute()

        # Calcular trust score inicial
        trust_result = await calcular_trust_score(chip_id)

        # Planejar primeiro dia
        atividades = await scheduler.planejar_dia(chip_id)
        await scheduler.salvar_agenda(atividades)

        # Registrar transição
        await self._registrar_transicao(
            chip_id,
            FaseWarmup.REPOUSO.value,
            FaseWarmup.SETUP.value,
            "inicio_warmup",
        )

        logger.info(
            f"[Orchestrator] Chip {chip_id[:8]}... iniciado em setup, "
            f"trust={trust_result['score']}, {len(atividades)} atividades agendadas"
        )

        return {
            "success": True,
            "fase": FaseWarmup.SETUP.value,
            "trust_score": trust_result["score"],
            "atividades_agendadas": len(atividades),
        }

    async def pausar_chip(self, chip_id: str, motivo: str = "pausa_manual") -> dict:
        """
        Pausa warmup de um chip.

        Args:
            chip_id: ID do chip
            motivo: Motivo da pausa

        Returns:
            Dict com status
        """
        # Cancelar atividades pendentes
        canceladas = await scheduler.cancelar_atividades(chip_id, motivo)

        # Atualizar status
        supabase.table("chips").update(
            {
                "fase_warmup": FaseWarmup.REPOUSO.value,
                "warmup_pausado_em": agora_brasilia().isoformat(),
                "warmup_motivo_pausa": motivo,
            }
        ).eq("id", chip_id).execute()

        logger.info(f"[Orchestrator] Chip {chip_id[:8]}... pausado: {motivo}")

        return {
            "success": True,
            "atividades_canceladas": canceladas,
        }

    async def verificar_transicao(self, chip_id: str) -> Optional[str]:
        """
        Verifica se chip pode transicionar de fase.

        Sprint 65: Usa warming_started_at ao invés de created_at para calcular idade.

        Args:
            chip_id: ID do chip

        Returns:
            Nova fase se pode transicionar, None caso contrário
        """
        # Buscar dados do chip
        result = supabase.table("chips").select("*").eq("id", chip_id).single().execute()

        if not result.data:
            return None

        chip = result.data
        fase_atual = FaseWarmup(chip.get("fase_warmup", "repouso"))

        # Se já está em operação, não há transição
        if fase_atual == FaseWarmup.OPERACAO:
            return None

        # Encontrar próxima fase
        idx_atual = SEQUENCIA_FASES.index(fase_atual)
        proxima_fase = SEQUENCIA_FASES[idx_atual + 1]

        # Buscar critérios da próxima fase
        criterios = CRITERIOS_FASE.get(proxima_fase)
        if not criterios:
            return None

        # Sprint 65: Calcular idade usando warming_started_at (não created_at)
        # Fallback chain: warming_started_at → fase_iniciada_em → created_at
        warming_ref = (
            chip.get("warming_started_at") or chip.get("fase_iniciada_em") or chip.get("created_at")
        )
        warming_ref_dt = datetime.fromisoformat(str(warming_ref).replace("Z", "+00:00"))
        idade_dias = (agora_brasilia() - warming_ref_dt).days

        # Verificar cada critério
        if idade_dias < criterios.dias_minimos:
            return None

        if chip.get("msgs_enviadas_total", 0) < criterios.msgs_enviadas_min:
            return None

        if chip.get("msgs_recebidas_total", 0) < criterios.msgs_recebidas_min:
            return None

        taxa_resposta = chip.get("taxa_resposta", 0)
        if isinstance(taxa_resposta, str):
            taxa_resposta = float(taxa_resposta)
        if taxa_resposta < criterios.taxa_resposta_min:
            return None

        if chip.get("trust_score", 0) < criterios.trust_score_min:
            return None

        if chip.get("conversas_bidirecionais", 0) < criterios.conversas_bidirecionais_min:
            return None

        if chip.get("grupos_count", 0) < criterios.grupos_min:
            return None

        if chip.get("erros_ultimas_24h", 0) > criterios.erros_max_24h:
            return None

        # Todos os critérios atendidos!
        return proxima_fase.value

    async def executar_transicao(
        self,
        chip_id: str,
        nova_fase: str,
        automatico: bool = True,
    ) -> dict:
        """
        Executa transição de fase.

        Args:
            chip_id: ID do chip
            nova_fase: Nova fase
            automatico: Se foi automático ou manual

        Returns:
            Dict com resultado
        """
        # Buscar fase atual
        result = supabase.table("chips").select("fase_warmup").eq("id", chip_id).single().execute()

        fase_atual = result.data.get("fase_warmup", "repouso") if result.data else "repouso"

        # Atualizar chip
        supabase.table("chips").update(
            {
                "fase_warmup": nova_fase,
                "fase_iniciada_em": agora_brasilia().isoformat(),
            }
        ).eq("id", chip_id).execute()

        # Registrar transição
        motivo = "transicao_automatica" if automatico else "transicao_manual"
        await self._registrar_transicao(chip_id, fase_atual, nova_fase, motivo)

        # Recalcular trust score
        trust_result = await calcular_trust_score(chip_id)

        # Cancelar atividades antigas e replanejar
        await scheduler.cancelar_atividades(chip_id, "transicao_fase")
        atividades = await scheduler.planejar_dia(chip_id)
        await scheduler.salvar_agenda(atividades)

        logger.info(
            f"[Orchestrator] Chip {chip_id[:8]}... transicionou: {fase_atual} -> {nova_fase}"
        )

        return {
            "success": True,
            "fase_anterior": fase_atual,
            "fase_nova": nova_fase,
            "trust_score": trust_result["score"],
            "atividades_agendadas": len(atividades),
        }

    async def _registrar_transicao(
        self,
        chip_id: str,
        fase_de: str,
        fase_para: str,
        motivo: str,
    ):
        """Registra transição no histórico."""
        supabase.table("chip_transitions").insert(
            {
                "chip_id": chip_id,
                "fase_de": fase_de,
                "fase_para": fase_para,
                "motivo": motivo,
            }
        ).execute()

    async def executar_atividade(
        self,
        atividade: AtividadeAgendada,
    ) -> dict:
        """
        Executa uma atividade agendada.

        Delega ao executor.executar_atividade que envia mensagens reais
        via enviar_via_chip (Evolution API / Z-API).

        Args:
            atividade: Atividade a executar

        Returns:
            Dict com resultado
        """
        chip_id = atividade.chip_id

        # Lock por chip para evitar processamento duplicado (atômico)
        if chip_id not in self._chip_locks:
            self._chip_locks[chip_id] = asyncio.Lock()

        chip_lock = self._chip_locks[chip_id]

        if chip_lock.locked():
            return {"success": False, "error": "Chip já em processamento"}

        async with chip_lock:
            success = await _executor_executar(atividade)
            resultado = {
                "success": success,
                "tipo": atividade.tipo.value,
            }

            # Marcar atividade como executada
            if atividade.id:
                await scheduler.marcar_executada(
                    atividade.id,
                    success,
                    resultado,
                )

            return resultado

    async def _garantir_planejamento_diario(self):
        """Garante que chips em warming tenham atividades planejadas para hoje."""
        chips_ativos = (
            supabase.table("chips")
            .select("id, fase_warmup")
            .neq("fase_warmup", "repouso")
            .execute()
        )

        planejados = 0
        for chip in chips_ativos.data or []:
            chip_id = chip["id"]
            stats = await scheduler.obter_estatisticas(chip_id)

            if stats["total"] == 0:
                atividades = await scheduler.planejar_dia(chip_id)
                if atividades:
                    await scheduler.salvar_agenda(atividades)
                    planejados += len(atividades)
                    logger.info(
                        f"[Orchestrator] Auto-planejadas {len(atividades)} atividades "
                        f"para chip {chip_id[:8]}... fase={chip['fase_warmup']}"
                    )

        return planejados

    async def _atualizar_warming_days(self):
        """
        Atualiza warming_day para todos os chips em warmup.

        Sprint 65: Calcula dias desde warming_started_at e persiste no banco.
        """
        chips_result = (
            supabase.table("chips")
            .select("id, warming_started_at")
            .in_("status", ["warming", "active"])
            .not_.is_("warming_started_at", "null")
            .execute()
        )

        agora = agora_brasilia()
        atualizados = 0
        for chip in chips_result.data or []:
            try:
                warming_started = datetime.fromisoformat(
                    chip["warming_started_at"].replace("Z", "+00:00")
                )
                warming_day = (agora - warming_started).days

                supabase.table("chips").update({"warming_day": warming_day}).eq(
                    "id", chip["id"]
                ).execute()
                atualizados += 1
            except (ValueError, TypeError, KeyError) as e:
                logger.warning(
                    f"[Orchestrator] Erro ao calcular warming_day para chip {chip['id'][:8]}: {e}"
                )

        if atualizados:
            logger.info(f"[Orchestrator] warming_day atualizado para {atualizados} chips")

    async def ciclo_warmup(self):
        """
        Executa ciclo principal de warmup.

        Este método deve ser chamado periodicamente (ex: a cada 5 minutos).
        Sprint 65: Adiciona warming_day update e structured logging.
        """
        if self._ciclo_lock.locked():
            logger.warning("[Orchestrator] Ciclo já em execução")
            return

        async with self._ciclo_lock:
            logger.info("[Orchestrator] Iniciando ciclo de warmup")

            # 1. Garantir que chips ativos tenham atividades planejadas para hoje
            planejados = await self._garantir_planejamento_diario()
            if planejados:
                logger.info(f"[Orchestrator] {planejados} atividades auto-planejadas")

            # 2. Sprint 65: Atualizar warming_day
            await self._atualizar_warming_days()

            # 3. Buscar atividades pendentes
            atividades = await scheduler.obter_proximas_atividades(limite=20)

            logger.info(f"[Orchestrator] {len(atividades)} atividades para executar")

            # 4. Executar atividades e coletar resultados
            resultados = []
            for atividade in atividades:
                try:
                    resultado = await self.executar_atividade(atividade)
                    resultados.append(resultado)
                    logger.debug(
                        f"[Orchestrator] Atividade {atividade.tipo.value}: "
                        f"{'OK' if resultado.get('success') else 'FALHA'}"
                    )
                except Exception as e:
                    logger.error(
                        f"[Orchestrator] Erro em atividade {atividade.tipo.value} "
                        f"chip={atividade.chip_id[:8]}: {e}",
                        exc_info=True,
                    )
                    resultados.append({"success": False, "error": str(e)})

                # Delay entre atividades
                await asyncio.sleep(2)

            # 5. Verificar transições de fase
            chips_result = (
                supabase.table("chips")
                .select("id")
                .neq("fase_warmup", "repouso")
                .neq("fase_warmup", "operacao")
                .execute()
            )

            transicoes = 0
            for chip in chips_result.data or []:
                try:
                    nova_fase = await self.verificar_transicao(chip["id"])
                    if nova_fase:
                        await self.executar_transicao(chip["id"], nova_fase)
                        transicoes += 1
                except Exception as e:
                    logger.error(
                        f"[Orchestrator] Erro ao verificar transição chip={chip['id'][:8]}: {e}",
                        exc_info=True,
                    )

            # 6. Recalcular trust scores
            for chip in chips_result.data or []:
                try:
                    await calcular_trust_score(chip["id"])
                except Exception as e:
                    logger.error(
                        f"[Orchestrator] Erro ao calcular trust chip={chip['id'][:8]}: {e}",
                        exc_info=True,
                    )

            # Sprint 65: Structured logging — resumo do ciclo
            executadas = sum(1 for r in resultados if r.get("success"))
            falhas = sum(1 for r in resultados if not r.get("success"))
            total = len(resultados)

            logger.info(
                f"[Orchestrator] Ciclo concluído: "
                f"{executadas}/{total} OK, {falhas} falhas, "
                f"{planejados} auto-planejadas, {transicoes} transições"
            )

    async def obter_status_pool(self) -> dict:
        """
        Obtém status geral do pool de chips.

        Sprint 65: Inclui warming_day nos dados.

        Returns:
            Dict com estatísticas do pool
        """
        result = (
            supabase.table("chips")
            .select(
                "telefone, fase_warmup, trust_score, trust_level, status, "
                "warming_day, msgs_enviadas_hoje, evolution_connected, provider"
            )
            .execute()
        )

        stats = {
            "total": 0,
            "por_fase": {},
            "por_status": {},
            "trust_medio": 0,
            "prontos_operacao": 0,
            "chips": [],
        }

        trust_total = 0

        for chip in result.data or []:
            stats["total"] += 1

            fase = chip.get("fase_warmup", "repouso")
            stats["por_fase"][fase] = stats["por_fase"].get(fase, 0) + 1

            status = chip.get("status", "unknown")
            stats["por_status"][status] = stats["por_status"].get(status, 0) + 1

            trust = chip.get("trust_score", 0)
            trust_total += trust

            if fase == "operacao" and trust >= 75:
                stats["prontos_operacao"] += 1

            stats["chips"].append(
                {
                    "telefone_masked": chip.get("telefone", "????")[-4:],
                    "status": status,
                    "fase": fase,
                    "warming_day": chip.get("warming_day", 0),
                    "trust": trust,
                    "trust_level": chip.get("trust_level", "unknown"),
                    "msgs_hoje": chip.get("msgs_enviadas_hoje", 0),
                    "connected": chip.get("evolution_connected", False),
                    "provider": chip.get("provider", "evolution"),
                }
            )

        if stats["total"] > 0:
            stats["trust_medio"] = round(trust_total / stats["total"], 1)

        return stats


# Instância global
orchestrator = WarmingOrchestrator()


async def iniciar_warmup(chip_id: str) -> dict:
    """Função de conveniência para iniciar warmup."""
    return await orchestrator.iniciar_chip(chip_id)


async def pausar_warmup(chip_id: str, motivo: str = "pausa_manual") -> dict:
    """Função de conveniência para pausar warmup."""
    return await orchestrator.pausar_chip(chip_id, motivo)


async def executar_ciclo():
    """Função de conveniência para executar ciclo."""
    await orchestrator.ciclo_warmup()


async def status_pool() -> dict:
    """Função de conveniência para status do pool."""
    return await orchestrator.obter_status_pool()
