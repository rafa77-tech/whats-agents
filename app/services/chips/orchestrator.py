"""
Chip Orchestrator - Gerenciamento do pool de chips.

Sprint 26 - E01
Sprint 44 - T03.1: Distributed Lock para ciclo de orquestração

Responsavel por:
- Manter pool saudavel (producao, ready, warming)
- Auto-replace de chips degradados
- Auto-provision quando necessario
- Promocao automatica (warming -> ready -> active)
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict

from app.services.supabase import supabase
from app.services.salvy.client import salvy_client
from app.core.distributed_lock import DistributedLock, LockNotAcquiredError

logger = logging.getLogger(__name__)


async def notificar_slack(mensagem: str, canal: str = "operacoes") -> bool:
    """
    Loga mensagem de orquestração (Slack removido Sprint 47).

    Notificações são logadas e visualizadas no dashboard.
    """
    log_fn = logger.warning if canal == "alertas" else logger.info
    log_fn(f"[Orchestrator] {mensagem}")
    return True


class ChipOrchestrator:
    """Orquestrador central do pool de chips."""

    def __init__(self):
        self.config: Optional[Dict] = None
        self._running = False

    async def carregar_config(self) -> Dict:
        """Carrega configuracao do pool."""
        result = supabase.table("pool_config").select("*").limit(1).execute()
        if result.data:
            self.config = result.data[0]
        else:
            # Config padrao
            self.config = {
                "producao_min": 3,
                "producao_max": 10,
                "ready_min": 2,
                "warmup_buffer": 5,
                "warmup_days": 21,
                "trust_min_for_ready": 85,
                "trust_degraded_threshold": 40,
                "trust_critical_threshold": 20,
                "auto_provision": False,
                "default_ddd": 11,
            }
            logger.warning("[Orchestrator] Usando config padrao - pool_config vazio")
        return self.config

    # ════════════════════════════════════════════════════════════
    # POOL STATUS
    # ════════════════════════════════════════════════════════════

    async def obter_status_pool(self) -> Dict:
        """
        Retorna status completo do pool.

        Returns:
            {
                "producao": {"count": N, "min": M, "max": X, "chips": [...]},
                "ready": {"count": N, "min": M, "chips": [...]},
                "warming": {"count": N, "buffer": M, "chips": [...]},
                "degraded": {"count": N, "chips": [...]},
                "saude": "saudavel" | "atencao" | "critico"
            }
        """
        if not self.config:
            await self.carregar_config()

        # Buscar todos os chips relevantes
        result = (
            supabase.table("chips")
            .select(
                "id, telefone, instance_name, status, trust_score, trust_level, "
                "fase_warmup, warming_started_at, msgs_enviadas_hoje, evolution_connected"
            )
            .in_("status", ["warming", "ready", "active", "degraded"])
            .execute()
        )

        chips = result.data or []

        # Agrupar por status
        producao = [c for c in chips if c["status"] == "active"]
        ready = [c for c in chips if c["status"] == "ready"]
        warming = [c for c in chips if c["status"] == "warming"]
        degraded = [c for c in chips if c["status"] == "degraded"]

        # Determinar saude do pool
        saude = "saudavel"
        if len(producao) < self.config["producao_min"]:
            saude = "critico"
        elif len(ready) < self.config["ready_min"]:
            saude = "atencao"
        elif len(warming) < self.config["warmup_buffer"] // 2:
            saude = "atencao"

        return {
            "producao": {
                "count": len(producao),
                "min": self.config["producao_min"],
                "max": self.config["producao_max"],
                "chips": producao,
            },
            "ready": {
                "count": len(ready),
                "min": self.config["ready_min"],
                "chips": ready,
            },
            "warming": {
                "count": len(warming),
                "buffer": self.config["warmup_buffer"],
                "chips": warming,
            },
            "degraded": {
                "count": len(degraded),
                "chips": degraded,
            },
            "saude": saude,
            "totais": {
                "total_chips": len(chips),
                "trust_medio": (
                    sum(c["trust_score"] or 0 for c in producao) / len(producao) if producao else 0
                ),
            },
        }

    async def verificar_deficits(self) -> Dict:
        """
        Verifica deficits no pool.

        Returns:
            {"producao": N, "ready": N, "warming": N}
        """
        status = await self.obter_status_pool()

        return {
            "producao": max(0, self.config["producao_min"] - status["producao"]["count"]),
            "ready": max(0, self.config["ready_min"] - status["ready"]["count"]),
            "warming": max(0, self.config["warmup_buffer"] - status["warming"]["count"]),
        }

    # ════════════════════════════════════════════════════════════
    # AUTO-REPLACE
    # ════════════════════════════════════════════════════════════

    async def verificar_chips_degradados(self) -> List[Dict]:
        """
        Identifica chips ativos que precisam ser substituidos.

        Criterios:
        - Trust Score abaixo do threshold degradado
        - Status 'banned'
        - Desconectado
        """
        if not self.config:
            await self.carregar_config()

        threshold = self.config["trust_degraded_threshold"]

        # Chips ativos com trust baixo
        result = (
            supabase.table("chips")
            .select("*")
            .eq("status", "active")
            .lt("trust_score", threshold)
            .execute()
        )

        degradados = result.data or []

        # Chips desconectados
        desconectados = (
            supabase.table("chips")
            .select("*")
            .eq("status", "active")
            .eq("evolution_connected", False)
            .execute()
        )

        for chip in desconectados.data or []:
            if chip["id"] not in [d["id"] for d in degradados]:
                degradados.append(chip)

        return degradados

    async def substituir_chip(self, chip_degradado: Dict) -> Optional[Dict]:
        """
        Substitui chip degradado por um ready.

        Fluxo:
        1. Buscar melhor chip ready
        2. Migrar conversas ativas
        3. Promover novo chip para active
        4. Rebaixar chip degradado

        Args:
            chip_degradado: Chip a ser substituido

        Returns:
            Novo chip promovido ou None se nao houver ready
        """
        logger.warning(
            f"[Orchestrator] Iniciando substituicao de {chip_degradado['telefone']} "
            f"(Trust: {chip_degradado.get('trust_score', 'N/A')})"
        )

        # 1. Buscar melhor chip ready
        result = (
            supabase.table("chips")
            .select("*")
            .eq("status", "ready")
            .gte("trust_score", self.config["trust_min_for_ready"])
            .order("trust_score", desc=True)
            .limit(1)
            .execute()
        )

        if not result.data:
            logger.error("[Orchestrator] Nenhum chip ready disponivel para substituicao!")

            await notificar_slack(
                f":rotating_light: *CRITICO*: Chip `{chip_degradado['telefone']}` degradado "
                f"(Trust: {chip_degradado.get('trust_score', 'N/A')}) mas NAO HA CHIPS READY!\n"
                f"Pool precisa de atencao imediata.",
                canal="alertas",
            )
            return None

        novo_chip = result.data[0]

        # 2. Migrar conversas ativas
        conversas_migradas = await self._migrar_conversas(chip_degradado["id"], novo_chip["id"])

        # 3. Promover novo chip
        now = datetime.now(timezone.utc).isoformat()
        supabase.table("chips").update(
            {
                "status": "active",
                "promoted_to_active_at": now,
            }
        ).eq("id", novo_chip["id"]).execute()

        # 4. Rebaixar chip degradado
        supabase.table("chips").update(
            {
                "status": "degraded",
            }
        ).eq("id", chip_degradado["id"]).execute()

        # 5. Registrar operacao
        supabase.table("orchestrator_operations").insert(
            {
                "operacao": "auto_replace",
                "chip_id": chip_degradado["id"],
                "chip_destino_id": novo_chip["id"],
                "motivo": f"Trust Score {chip_degradado.get('trust_score', 'N/A')} < {self.config['trust_degraded_threshold']}",
                "metadata": {
                    "conversas_migradas": conversas_migradas,
                    "trust_degradado": chip_degradado.get("trust_score"),
                    "trust_novo": novo_chip.get("trust_score"),
                },
            }
        ).execute()

        # 6. Notificar
        await notificar_slack(
            f":arrows_counterclockwise: *Auto-Replace executado*\n"
            f"- Degradado: `{chip_degradado['telefone']}` (Trust: {chip_degradado.get('trust_score', 'N/A')})\n"
            f"- Promovido: `{novo_chip['telefone']}` (Trust: {novo_chip.get('trust_score', 'N/A')})\n"
            f"- Conversas migradas: {conversas_migradas}",
            canal="operacoes",
        )

        logger.info(
            f"[Orchestrator] Substituicao concluida: "
            f"{chip_degradado['telefone']} -> {novo_chip['telefone']}"
        )

        return novo_chip

    async def _migrar_conversas(self, chip_antigo_id: str, chip_novo_id: str) -> int:
        """
        Migra conversas ativas para novo chip.

        Args:
            chip_antigo_id: Chip de origem
            chip_novo_id: Chip de destino

        Returns:
            Numero de conversas migradas
        """
        now = datetime.now(timezone.utc).isoformat()

        # Buscar conversas ativas
        result = (
            supabase.table("conversation_chips")
            .select("id")
            .eq("chip_id", chip_antigo_id)
            .eq("active", True)
            .execute()
        )

        count = len(result.data or [])

        if count > 0:
            # Atualizar todas de uma vez
            supabase.table("conversation_chips").update(
                {
                    "chip_id": chip_novo_id,
                    "migrated_at": now,
                    "migrated_from": chip_antigo_id,
                }
            ).eq("chip_id", chip_antigo_id).eq("active", True).execute()

            # Registrar operacao de migracao
            supabase.table("orchestrator_operations").insert(
                {
                    "operacao": "migration",
                    "chip_id": chip_antigo_id,
                    "chip_destino_id": chip_novo_id,
                    "motivo": f"Migracao de {count} conversas",
                    "metadata": {"count": count},
                }
            ).execute()

        logger.info(f"[Orchestrator] {count} conversas migradas")

        return count

    # ════════════════════════════════════════════════════════════
    # AUTO-PROVISION
    # ════════════════════════════════════════════════════════════

    async def verificar_provisioning(self):
        """
        Verifica se precisa provisionar novos chips.

        Provisiona quando:
        - warming < warmup_buffer
        - ready < ready_min (e nao ha chips warming suficientes)
        """
        if not self.config or not self.config.get("auto_provision"):
            return

        deficits = await self.verificar_deficits()

        # Prioridade: manter warming buffer
        if deficits["warming"] > 0:
            logger.info(
                f"[Orchestrator] Provisionando {deficits['warming']} chips (warming deficit)"
            )

            # Max 3 por ciclo
            for _ in range(min(deficits["warming"], 3)):
                await self._provisionar_novo_chip()

    async def _provisionar_novo_chip(self, ddd: Optional[int] = None) -> Optional[Dict]:
        """
        Provisiona novo chip via Salvy.

        Args:
            ddd: DDD desejado (usa default se nao especificado)

        Returns:
            Chip criado ou None
        """
        ddd = ddd or self.config.get("default_ddd", 11)

        try:
            # 1. Criar numero na Salvy
            salvy_number = await salvy_client.criar_numero(ddd=ddd)

            # 2. Gerar nome de instancia
            instance_name = f"julia-{salvy_number.phone_number[-8:]}"

            # 3. Criar registro no banco
            result = (
                supabase.table("chips")
                .insert(
                    {
                        "telefone": salvy_number.phone_number,
                        "salvy_id": salvy_number.id,
                        "salvy_status": salvy_number.status,
                        "salvy_created_at": salvy_number.created_at.isoformat(),
                        "instance_name": instance_name,
                        "status": "provisioned",
                        "tipo": "julia",
                        "trust_score": 50,  # Score inicial
                        "trust_level": "verde",
                    }
                )
                .execute()
            )

            chip = result.data[0] if result.data else None

            if chip:
                # Registrar operacao
                supabase.table("orchestrator_operations").insert(
                    {
                        "operacao": "auto_provision",
                        "chip_id": chip["id"],
                        "motivo": "Pool buffer baixo",
                        "metadata": {"ddd": ddd, "salvy_id": salvy_number.id},
                    }
                ).execute()

                logger.info(f"[Orchestrator] Chip provisionado: {salvy_number.phone_number}")

                await notificar_slack(
                    f":sparkles: *Novo chip provisionado*: `{salvy_number.phone_number}`",
                    canal="operacoes",
                )

            return chip

        except Exception as e:
            logger.error(f"[Orchestrator] Erro ao provisionar: {e}")

            await notificar_slack(f":x: *Erro no auto-provisioning*: {str(e)}", canal="alertas")

            return None

    # ════════════════════════════════════════════════════════════
    # PROMOCAO AUTOMATICA
    # ════════════════════════════════════════════════════════════

    async def verificar_promocoes_warming_ready(self) -> int:
        """
        Verifica chips warming que podem ser promovidos para ready.

        Criterios:
        - Trust Score >= trust_min_for_ready
        - Dias de warmup >= warmup_days
        - Fase = 'operacao'

        Returns:
            Numero de chips promovidos
        """
        if not self.config:
            await self.carregar_config()

        # Buscar candidatos
        result = (
            supabase.table("chips")
            .select("*")
            .eq("status", "warming")
            .eq("fase_warmup", "operacao")
            .gte("trust_score", self.config["trust_min_for_ready"])
            .execute()
        )

        promovidos = 0

        for chip in result.data or []:
            # Verificar dias de warmup
            if not chip.get("warming_started_at"):
                continue

            warming_started = datetime.fromisoformat(
                chip["warming_started_at"].replace("Z", "+00:00")
            )
            dias = (datetime.now(timezone.utc) - warming_started).days

            if dias >= self.config["warmup_days"]:
                # Promover para ready
                now = datetime.now(timezone.utc).isoformat()

                supabase.table("chips").update(
                    {
                        "status": "ready",
                        "ready_at": now,
                    }
                ).eq("id", chip["id"]).execute()

                # Registrar
                supabase.table("orchestrator_operations").insert(
                    {
                        "operacao": "promotion_warming_ready",
                        "chip_id": chip["id"],
                        "motivo": f"Trust {chip['trust_score']} >= {self.config['trust_min_for_ready']}, {dias} dias",
                    }
                ).execute()

                promovidos += 1

                logger.info(
                    f"[Orchestrator] Chip {chip['telefone']} promovido para READY "
                    f"(Trust: {chip['trust_score']}, Dias: {dias})"
                )

        if promovidos > 0:
            await notificar_slack(
                f":white_check_mark: *{promovidos} chip(s) promovido(s) para READY*\n"
                f"Disponiveis para producao quando necessario.",
                canal="operacoes",
            )

        return promovidos

    async def verificar_promocoes_ready_active(self) -> int:
        """
        Verifica se precisa promover chips ready para active.

        Apenas quando producao < producao_min.

        Returns:
            Numero de chips promovidos
        """
        status = await self.obter_status_pool()

        deficit = self.config["producao_min"] - status["producao"]["count"]

        if deficit <= 0:
            return 0  # Pool de producao ok

        # Buscar melhores ready
        result = (
            supabase.table("chips")
            .select("*")
            .eq("status", "ready")
            .order("trust_score", desc=True)
            .limit(deficit)
            .execute()
        )

        promovidos = 0
        now = datetime.now(timezone.utc).isoformat()

        for chip in result.data or []:
            supabase.table("chips").update(
                {
                    "status": "active",
                    "promoted_to_active_at": now,
                }
            ).eq("id", chip["id"]).execute()

            supabase.table("orchestrator_operations").insert(
                {
                    "operacao": "promotion_ready_active",
                    "chip_id": chip["id"],
                    "motivo": f"Deficit de producao: {deficit}",
                }
            ).execute()

            promovidos += 1

            logger.info(f"[Orchestrator] Chip {chip['telefone']} promovido para ACTIVE")

        if promovidos > 0:
            await notificar_slack(
                f":rocket: *{promovidos} chip(s) promovido(s) para PRODUCAO*\n"
                f"Pool de producao normalizado.",
                canal="operacoes",
            )

        return promovidos

    # ════════════════════════════════════════════════════════════
    # OPERACOES MANUAIS
    # ════════════════════════════════════════════════════════════

    async def promover_chip_manual(self, chip_id: str, para_status: str) -> Dict:
        """
        Promove chip manualmente.

        Args:
            chip_id: ID do chip
            para_status: 'ready' ou 'active'

        Returns:
            Resultado da operacao
        """
        result = supabase.table("chips").select("*").eq("id", chip_id).single().execute()
        if not result.data:
            return {"sucesso": False, "erro": "Chip nao encontrado"}

        chip = result.data
        now = datetime.now(timezone.utc).isoformat()

        updates = {"status": para_status}
        if para_status == "ready":
            updates["ready_at"] = now
        elif para_status == "active":
            updates["promoted_to_active_at"] = now

        supabase.table("chips").update(updates).eq("id", chip_id).execute()

        supabase.table("orchestrator_operations").insert(
            {
                "operacao": "manual_promote",
                "chip_id": chip_id,
                "motivo": f"Promocao manual para {para_status}",
            }
        ).execute()

        logger.info(
            f"[Orchestrator] Chip {chip['telefone']} promovido manualmente para {para_status}"
        )

        return {"sucesso": True, "chip": chip, "novo_status": para_status}

    async def rebaixar_chip_manual(self, chip_id: str, motivo: str = "Manual") -> Dict:
        """
        Rebaixa chip manualmente para degraded.

        Args:
            chip_id: ID do chip
            motivo: Motivo do rebaixamento

        Returns:
            Resultado da operacao
        """
        result = supabase.table("chips").select("*").eq("id", chip_id).single().execute()
        if not result.data:
            return {"sucesso": False, "erro": "Chip nao encontrado"}

        chip = result.data

        supabase.table("chips").update({"status": "degraded"}).eq("id", chip_id).execute()

        supabase.table("orchestrator_operations").insert(
            {
                "operacao": "manual_demote",
                "chip_id": chip_id,
                "motivo": motivo,
            }
        ).execute()

        logger.info(f"[Orchestrator] Chip {chip['telefone']} rebaixado manualmente")

        return {"sucesso": True, "chip": chip, "novo_status": "degraded"}

    # ════════════════════════════════════════════════════════════
    # LOOP PRINCIPAL
    # ════════════════════════════════════════════════════════════

    async def executar_ciclo(self):
        """
        Executa um ciclo completo de verificacao.

        Sprint 44 T03.1: Usa distributed lock para evitar execução
        simultânea em múltiplos workers/processos.

        Ordem:
        1. Adquirir lock distribuído
        2. Carregar config
        3. Verificar e substituir degradados
        4. Verificar promocoes warming -> ready
        5. Verificar promocoes ready -> active
        6. Verificar provisioning
        7. Log status
        """
        # Sprint 44 T03.1: Lock distribuído para evitar execução simultânea
        try:
            async with DistributedLock("chip_orchestrator_cycle", timeout=300):
                await self._executar_ciclo_impl()
        except LockNotAcquiredError:
            logger.info("[Orchestrator] Outro processo já está executando o ciclo")
        except Exception as e:
            logger.error(f"[Orchestrator] Erro no ciclo: {e}")

    async def _executar_ciclo_impl(self):
        """Implementação do ciclo (chamada protegida pelo lock)."""
        logger.debug("[Orchestrator] Iniciando ciclo")

        # 1. Carregar config
        await self.carregar_config()

        # 2. Verificar chips degradados e substituir
        degradados = await self.verificar_chips_degradados()
        for chip in degradados:
            await self.substituir_chip(chip)

        # 3. Verificar promocoes warming -> ready
        await self.verificar_promocoes_warming_ready()

        # 4. Verificar promocoes ready -> active
        await self.verificar_promocoes_ready_active()

        # 5. Verificar provisioning
        await self.verificar_provisioning()

        # 6. Log status
        status = await self.obter_status_pool()
        logger.info(
            f"[Orchestrator] Pool: "
            f"producao={status['producao']['count']}/{status['producao']['min']}, "
            f"ready={status['ready']['count']}/{status['ready']['min']}, "
            f"warming={status['warming']['count']}/{status['warming']['buffer']}, "
            f"saude={status['saude']}"
        )

        # Alertar se saude nao ok
        if status["saude"] == "critico":
            await notificar_slack(
                f":rotating_light: *Pool em estado CRITICO*\n"
                f"- Producao: {status['producao']['count']}/{status['producao']['min']}\n"
                f"- Ready: {status['ready']['count']}/{status['ready']['min']}\n"
                f"- Warming: {status['warming']['count']}/{status['warming']['buffer']}",
                canal="alertas",
            )

    async def iniciar(self, intervalo_segundos: int = 60):
        """
        Inicia loop do orchestrator.

        Args:
            intervalo_segundos: Intervalo entre ciclos (default 1 min)
        """
        self._running = True
        logger.info(f"[Orchestrator] Iniciando com intervalo de {intervalo_segundos}s")

        while self._running:
            await self.executar_ciclo()
            await asyncio.sleep(intervalo_segundos)

    def parar(self):
        """Para o orchestrator."""
        self._running = False
        logger.info("[Orchestrator] Parando...")


# Singleton
chip_orchestrator = ChipOrchestrator()
