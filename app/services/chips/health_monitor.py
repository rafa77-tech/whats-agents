"""
Health Monitor - Monitoramento proativo de chips em producao.

Sprint 26 - E04
Sprint 36 - T11.1: Auto-demove de chips com trust crítico
Sprint 36 - T11.3: Alerta proativo de pool baixo

Detecta:
- Taxa de resposta caindo
- Erros aumentando
- Desconexoes
- Trust Score degradando
- Pool de chips baixo (proativo)

Acoes:
- Auto-demove de chips críticos
- Alerta proativo de pool baixo
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


async def notificar_slack(mensagem: str, canal: str = "operacoes") -> bool:
    """
    Loga mensagem de health monitor (Slack removido Sprint 47).

    Notificações são logadas e visualizadas no dashboard.
    """
    log_fn = logger.warning if canal == "alertas" else logger.info
    log_fn(f"[HealthMonitor] {mensagem}")
    return True


class HealthMonitor:
    """Monitor de saude dos chips."""

    def __init__(self):
        self._running = False
        self.thresholds = {
            "taxa_resposta_minima": 0.20,  # 20%
            "erros_por_hora_max": 5,
            "trust_drop_alerta": 10,  # Queda de 10 pontos em 24h
            "desconexao_timeout_minutos": 30,
            # Sprint 36 - T11.1: Auto-demove
            "trust_auto_demove": 20,  # Trust < 20 = demove automático
            "falhas_consecutivas_demove": 10,  # 10+ falhas consecutivas
            # Sprint 36 - T11.3: Pool baixo
            "pool_minimo_prospeccao": 3,  # Mínimo de chips para prospecção
            "pool_minimo_followup": 2,  # Mínimo de chips para followup
            "pool_minimo_resposta": 2,  # Mínimo de chips para resposta
            "pool_alerta_percentage": 0.3,  # Alerta se < 30% dos chips saudáveis
        }
        self._last_pool_alert: Dict[str, datetime] = {}  # Evitar spam de alertas

    async def verificar_saude_chips(self) -> List[Dict]:
        """
        Verifica saude de todos os chips ativos.

        Returns:
            Lista de alertas gerados
        """
        result = supabase.table("chips").select("*").eq("status", "active").execute()

        alertas = []

        for chip in result.data or []:
            chip_alertas = await self._verificar_chip(chip)
            alertas.extend(chip_alertas)

        return alertas

    async def _verificar_chip(self, chip: Dict) -> List[Dict]:
        """Verifica saude de um chip individual."""
        alertas = []

        # 1. Verificar conexao
        # Para Z-API, não usa evolution_connected (não é Evolution API)
        # Para Evolution, verifica evolution_connected
        provider = chip.get("provider") or "evolution"
        is_connected = chip.get("evolution_connected") if provider != "z-api" else True

        if not is_connected:
            alertas.append(
                await self._criar_alerta(
                    chip_id=chip["id"],
                    tipo="desconectado",
                    severity="critical",
                    message=f"Chip {chip['telefone']} desconectado ({provider})",
                )
            )

        # 2. Verificar taxa de resposta
        taxa = chip.get("taxa_resposta") or 0
        if taxa < self.thresholds["taxa_resposta_minima"]:
            alertas.append(
                await self._criar_alerta(
                    chip_id=chip["id"],
                    tipo="taxa_resposta_baixa",
                    severity="warning",
                    message=f"Chip {chip['telefone']}: Taxa de resposta {taxa:.1%} < 20%",
                )
            )

        # 3. Verificar erros
        erros = chip.get("erros_ultimas_24h") or 0
        limite_erros = self.thresholds["erros_por_hora_max"] * 24
        if erros > limite_erros:
            alertas.append(
                await self._criar_alerta(
                    chip_id=chip["id"],
                    tipo="muitos_erros",
                    severity="warning",
                    message=f"Chip {chip['telefone']}: {erros} erros nas ultimas 24h",
                )
            )

        # 4. Verificar queda de Trust Score
        queda = await self._verificar_queda_trust(chip)
        if queda >= self.thresholds["trust_drop_alerta"]:
            alertas.append(
                await self._criar_alerta(
                    chip_id=chip["id"],
                    tipo="trust_caindo",
                    severity="warning",
                    message=f"Chip {chip['telefone']}: Trust Score caiu {queda} pontos nas ultimas 24h",
                )
            )

        # 5. Verificar Trust Score critico
        trust = chip.get("trust_score") or 50
        if trust < 40:
            alertas.append(
                await self._criar_alerta(
                    chip_id=chip["id"],
                    tipo="trust_critico",
                    severity="critical",
                    message=f"Chip {chip['telefone']}: Trust Score critico ({trust})",
                )
            )

        return alertas

    async def _criar_alerta(
        self,
        chip_id: str,
        tipo: str,
        severity: str,
        message: str,
    ) -> Dict:
        """Cria alerta se nao existir um ativo do mesmo tipo."""
        # Verificar se ja existe alerta ativo
        existing = (
            supabase.table("chip_alerts")
            .select("id")
            .eq("chip_id", chip_id)
            .eq("tipo", tipo)
            .eq("resolved", False)
            .execute()
        )

        if existing.data:
            # Ja existe alerta ativo
            return {
                "chip_id": chip_id,
                "tipo": tipo,
                "severity": severity,
                "message": message,
                "duplicado": True,
            }

        # Criar novo alerta
        result = (
            supabase.table("chip_alerts")
            .insert(
                {
                    "chip_id": chip_id,
                    "tipo": tipo,
                    "severity": severity,
                    "message": message,
                }
            )
            .execute()
        )

        return {
            "chip_id": chip_id,
            "tipo": tipo,
            "severity": severity,
            "message": message,
            "id": result.data[0]["id"] if result.data else None,
            "duplicado": False,
        }

    async def _verificar_queda_trust(self, chip: Dict) -> int:
        """Verifica queda de Trust Score nas ultimas 24h."""
        ontem = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        result = (
            supabase.table("chip_trust_history")
            .select("score")
            .eq("chip_id", chip["id"])
            .gte("recorded_at", ontem)
            .order("recorded_at", desc=False)
            .limit(1)
            .execute()
        )

        if result.data:
            score_ontem = result.data[0]["score"]
            return max(0, score_ontem - (chip.get("trust_score") or 0))

        return 0

    async def gerar_relatorio(self) -> Dict:
        """
        Gera relatorio de saude do pool.

        Returns:
            {
                "timestamp": "...",
                "pool": {...},
                "alertas_ativos": [...],
                "chips_saudaveis": N,
                "chips_atencao": N,
                "chips_criticos": N
            }
        """
        result = supabase.table("chips").select("*").eq("status", "active").execute()

        chips = result.data or []

        # Classificar por saude
        saudaveis = [c for c in chips if (c.get("trust_score") or 0) >= 80]
        atencao = [c for c in chips if 60 <= (c.get("trust_score") or 0) < 80]
        criticos = [c for c in chips if (c.get("trust_score") or 0) < 60]

        # Buscar alertas nao resolvidos
        alertas = supabase.table("chip_alerts").select("*").eq("resolved", False).execute()

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pool": {
                "total": len(chips),
                "saudaveis": len(saudaveis),
                "atencao": len(atencao),
                "criticos": len(criticos),
            },
            "alertas_ativos": alertas.data or [],
            "alertas_count": len(alertas.data or []),
            "trust_medio": (
                sum(c.get("trust_score") or 0 for c in chips) / len(chips) if chips else 0
            ),
            "msgs_hoje": sum(c.get("msgs_enviadas_hoje") or 0 for c in chips),
            "chips_conectados": len([c for c in chips if c.get("evolution_connected")]),
            "chips_desconectados": len([c for c in chips if not c.get("evolution_connected")]),
        }

    async def auto_demover_chip(self, chip: Dict, motivo: str) -> Dict:
        """
        Sprint 36 - T11.1: Remove chip do pool automaticamente.

        Demove chips com trust crítico ou muitas falhas consecutivas.

        Args:
            chip: Dict com dados do chip
            motivo: Motivo do demove

        Returns:
            {
                "sucesso": bool,
                "chip_id": str,
                "telefone": str,
                "motivo": str,
                "status_anterior": str
            }
        """
        chip_id = chip["id"]
        telefone = chip.get("telefone", "N/A")
        status_anterior = chip.get("status", "active")

        try:
            # 1. Atualizar status do chip para 'demoved'
            supabase.table("chips").update(
                {
                    "status": "demoved",
                    "demoved_at": datetime.now(timezone.utc).isoformat(),
                    "demoved_motivo": motivo,
                    "demoved_by": "health_monitor_auto",
                }
            ).eq("id", chip_id).execute()

            # 2. Criar alerta
            await self._criar_alerta(
                chip_id=chip_id,
                tipo="auto_demoved",
                severity="critical",
                message=f"Chip {telefone} removido automaticamente: {motivo}",
            )

            # 3. Notificar Slack
            await notificar_slack(
                f":warning: *Auto-demove de chip*\n"
                f"• Chip: {telefone}\n"
                f"• Motivo: {motivo}\n"
                f"• Trust Score: {chip.get('trust_score', 'N/A')}\n"
                f"• Action: Chip removido do pool ativo",
                canal="alertas",
            )

            logger.warning(f"[HealthMonitor] Auto-demove: chip={telefone}, motivo={motivo}")

            return {
                "sucesso": True,
                "chip_id": chip_id,
                "telefone": telefone,
                "motivo": motivo,
                "status_anterior": status_anterior,
            }

        except Exception as e:
            logger.error(f"[HealthMonitor] Erro no auto-demove: {e}")
            return {
                "sucesso": False,
                "chip_id": chip_id,
                "telefone": telefone,
                "motivo": motivo,
                "erro": str(e),
            }

    async def verificar_auto_demove(self, chip: Dict) -> Optional[Dict]:
        """
        Sprint 36 - T11.1: Verifica se chip deve ser removido automaticamente.

        Critérios para auto-demove:
        - Trust Score < 20
        - Falhas consecutivas >= 10 (via circuit breaker)
        - Sprint 66: Chip Meta com quality rating RED

        Args:
            chip: Dict com dados do chip

        Returns:
            Resultado do demove ou None se não necessário
        """
        trust = chip.get("trust_score") or 50
        telefone = chip.get("telefone", "N/A")

        # Sprint 66: Chip Meta com quality RED → auto-degradar
        if chip.get("provider") == "meta" and chip.get("meta_quality_rating") == "RED":
            logger.warning(
                f"[HealthMonitor] Chip Meta {telefone} quality RED → auto-demove"
            )
            # Criar alerta específico
            try:
                supabase.table("chip_alerts").insert(
                    {
                        "chip_id": chip["id"],
                        "severity": "critical",
                        "tipo": "meta_quality_degraded",
                        "message": f"Chip Meta {telefone} quality rating RED",
                    }
                ).execute()
            except Exception:
                pass
            return await self.auto_demover_chip(
                chip, motivo="Meta quality rating RED"
            )

        # Verificar Trust Score crítico
        if trust < self.thresholds["trust_auto_demove"]:
            logger.warning(
                f"[HealthMonitor] Chip {telefone} candidato a auto-demove: "
                f"trust={trust} < {self.thresholds['trust_auto_demove']}"
            )
            return await self.auto_demover_chip(chip, motivo=f"Trust Score crítico ({trust})")

        # Verificar circuit breaker (via dados do chip ou estado em memória)
        from app.services.chips.circuit_breaker import ChipCircuitBreaker

        circuit = ChipCircuitBreaker.get_circuit(chip["id"], telefone)
        if circuit.falhas_consecutivas >= self.thresholds["falhas_consecutivas_demove"]:
            logger.warning(
                f"[HealthMonitor] Chip {telefone} candidato a auto-demove: "
                f"{circuit.falhas_consecutivas} falhas consecutivas"
            )
            return await self.auto_demover_chip(
                chip, motivo=f"{circuit.falhas_consecutivas} falhas consecutivas"
            )

        return None

    async def verificar_pool_baixo(self) -> List[Dict]:
        """
        Sprint 36 - T11.3: Verifica se pool está com poucos chips disponíveis.

        Alerta quando:
        - Menos de X chips disponíveis para cada tipo de operação
        - Menos de 30% dos chips totais estão saudáveis

        Returns:
            Lista de alertas gerados
        """
        alertas = []
        datetime.now(timezone.utc)

        # Buscar chips ativos (Sprint 66: incluir chips Meta que não usam evolution_connected)
        result = (
            supabase.table("chips")
            .select("*")
            .eq("status", "active")
            .execute()
        )

        # Filtrar: Evolution precisa de evolution_connected, Meta sempre conectado
        chips = [
            c for c in (result.data or [])
            if c.get("provider") == "meta" or c.get("evolution_connected")
        ]

        if not chips:
            # Crítico: nenhum chip disponível
            alertas.append(
                await self._criar_alerta_pool(
                    tipo="pool_vazio",
                    severity="critical",
                    message="Pool de chips está vazio! Nenhum chip conectado disponível.",
                )
            )
            return alertas

        # Contar chips por capacidade (com trust adequado)
        chips_prospeccao = [
            c for c in chips if c.get("pode_prospectar") and (c.get("trust_score") or 0) >= 60
        ]
        chips_followup = [
            c for c in chips if c.get("pode_followup") and (c.get("trust_score") or 0) >= 40
        ]
        chips_resposta = [
            c for c in chips if c.get("pode_responder") and (c.get("trust_score") or 0) >= 20
        ]

        # Verificar mínimos por operação
        verificacoes = [
            ("prospeccao", chips_prospeccao, self.thresholds["pool_minimo_prospeccao"]),
            ("followup", chips_followup, self.thresholds["pool_minimo_followup"]),
            ("resposta", chips_resposta, self.thresholds["pool_minimo_resposta"]),
        ]

        for operacao, chips_disponiveis, minimo in verificacoes:
            if len(chips_disponiveis) < minimo:
                alerta = await self._criar_alerta_pool(
                    tipo=f"pool_baixo_{operacao}",
                    severity="warning" if len(chips_disponiveis) > 0 else "critical",
                    message=(
                        f"Pool baixo para {operacao}: "
                        f"{len(chips_disponiveis)}/{minimo} chips disponíveis"
                    ),
                )
                if not alerta.get("duplicado"):
                    alertas.append(alerta)

        # Verificar percentual de chips saudáveis
        chips_saudaveis = [c for c in chips if (c.get("trust_score") or 0) >= 80]
        percentual_saudavel = len(chips_saudaveis) / len(chips) if chips else 0

        if percentual_saudavel < self.thresholds["pool_alerta_percentage"]:
            alerta = await self._criar_alerta_pool(
                tipo="pool_degradado",
                severity="warning",
                message=(
                    f"Pool degradado: apenas {len(chips_saudaveis)}/{len(chips)} "
                    f"chips saudáveis ({percentual_saudavel:.0%})"
                ),
            )
            if not alerta.get("duplicado"):
                alertas.append(alerta)

        # Notificar se houver alertas novos
        novos_alertas = [a for a in alertas if not a.get("duplicado")]
        if novos_alertas:
            await self._notificar_pool_baixo(novos_alertas, chips)

        return alertas

    async def _criar_alerta_pool(
        self,
        tipo: str,
        severity: str,
        message: str,
    ) -> Dict:
        """Cria alerta de pool (sem chip específico)."""
        # Verificar cooldown de alertas (evitar spam)
        agora = datetime.now(timezone.utc)
        ultima = self._last_pool_alert.get(tipo)
        if ultima and (agora - ultima).total_seconds() < 3600:  # 1 hora
            return {"tipo": tipo, "duplicado": True}

        self._last_pool_alert[tipo] = agora

        # Verificar se já existe alerta ativo
        existing = (
            supabase.table("chip_alerts")
            .select("id")
            .eq("tipo", tipo)
            .eq("resolved", False)
            .is_("chip_id", "null")
            .execute()
        )

        if existing.data:
            return {"tipo": tipo, "severity": severity, "message": message, "duplicado": True}

        # Criar alerta (sem chip_id pois é do pool geral)
        result = (
            supabase.table("chip_alerts")
            .insert(
                {
                    "chip_id": None,
                    "tipo": tipo,
                    "severity": severity,
                    "message": message,
                }
            )
            .execute()
        )

        return {
            "tipo": tipo,
            "severity": severity,
            "message": message,
            "id": result.data[0]["id"] if result.data else None,
            "duplicado": False,
        }

    async def _notificar_pool_baixo(self, alertas: List[Dict], chips: List[Dict]) -> None:
        """Notifica Slack sobre pool baixo."""
        mensagens = "\n".join([f"• {a['message']}" for a in alertas])
        severity_max = (
            "critical" if any(a["severity"] == "critical" for a in alertas) else "warning"
        )

        emoji = ":rotating_light:" if severity_max == "critical" else ":warning:"

        await notificar_slack(
            f"{emoji} *Alerta de Pool de Chips*\n\n"
            f"{mensagens}\n\n"
            f"*Status atual:*\n"
            f"• Total conectados: {len(chips)}\n"
            f"• Trust >= 80: {len([c for c in chips if (c.get('trust_score') or 0) >= 80])}\n"
            f"• Trust >= 60: {len([c for c in chips if (c.get('trust_score') or 0) >= 60])}\n"
            f"• Trust >= 40: {len([c for c in chips if (c.get('trust_score') or 0) >= 40])}\n\n"
            f"_Considere ativar novos chips ou investigar os problemas._",
            canal="alertas",
        )

    async def resolver_alerta(self, alerta_id: str, resolved_by: str = "manual") -> Dict:
        """
        Resolve um alerta.

        Args:
            alerta_id: ID do alerta
            resolved_by: Quem resolveu

        Returns:
            Resultado da operacao
        """
        (
            supabase.table("chip_alerts")
            .update(
                {
                    "resolved": True,
                    "resolved_at": datetime.now(timezone.utc).isoformat(),
                    "resolved_by": resolved_by,
                }
            )
            .eq("id", alerta_id)
            .execute()
        )

        return {"sucesso": True, "alerta_id": alerta_id}

    async def listar_alertas(
        self,
        chip_id: str = None,
        severity: str = None,
        resolved: bool = False,
    ) -> List[Dict]:
        """
        Lista alertas com filtros.

        Args:
            chip_id: Filtrar por chip
            severity: Filtrar por severidade
            resolved: Incluir resolvidos

        Returns:
            Lista de alertas
        """
        query = supabase.table("chip_alerts").select("*, chips(telefone)")

        if chip_id:
            query = query.eq("chip_id", chip_id)

        if severity:
            query = query.eq("severity", severity)

        if not resolved:
            query = query.eq("resolved", False)

        result = query.order("created_at", desc=True).execute()

        return result.data or []

    async def executar_ciclo(self):
        """Executa um ciclo de verificacao."""
        logger.debug("[HealthMonitor] Iniciando ciclo de verificacao")

        try:
            alertas = await self.verificar_saude_chips()

            # Sprint 36 - T11.1: Verificar auto-demove para chips ativos
            result = supabase.table("chips").select("*").eq("status", "active").execute()

            chips_demovidos = 0
            for chip in result.data or []:
                demove_result = await self.verificar_auto_demove(chip)
                if demove_result and demove_result.get("sucesso"):
                    chips_demovidos += 1

            if chips_demovidos > 0:
                logger.warning(f"[HealthMonitor] Auto-demove: {chips_demovidos} chip(s) removidos")

            # Sprint 36 - T11.3: Verificar pool baixo
            alertas_pool = await self.verificar_pool_baixo()
            alertas.extend(alertas_pool)

            # Filtrar apenas novos alertas
            novos = [a for a in alertas if not a.get("duplicado")]

            # Notificar alertas criticos
            criticos = [a for a in novos if a["severity"] == "critical"]
            if criticos:
                mensagens = "\n".join([f"- {a['message']}" for a in criticos])
                await notificar_slack(
                    f":rotating_light: *{len(criticos)} alerta(s) critico(s)*\n{mensagens}",
                    canal="alertas",
                )

            # Log resumo
            relatorio = await self.gerar_relatorio()
            logger.info(
                f"[HealthMonitor] Chips: "
                f"{relatorio['pool']['saudaveis']} saudaveis, "
                f"{relatorio['pool']['atencao']} atencao, "
                f"{relatorio['pool']['criticos']} criticos. "
                f"Alertas ativos: {relatorio['alertas_count']}"
            )

        except Exception as e:
            logger.error(f"[HealthMonitor] Erro no ciclo: {e}")

    async def iniciar(self, intervalo_segundos: int = 300):
        """
        Inicia monitoramento continuo.

        Args:
            intervalo_segundos: Intervalo entre verificacoes (default 5 min)
        """
        self._running = True
        logger.info(f"[HealthMonitor] Iniciando com intervalo de {intervalo_segundos}s")

        while self._running:
            await self.executar_ciclo()
            await asyncio.sleep(intervalo_segundos)

    def parar(self):
        """Para o monitor."""
        self._running = False
        logger.info("[HealthMonitor] Parando...")

    async def resetar_erros_24h(self) -> Dict:
        """
        Sprint 36 - T08.4: Reseta contador de erros_24h automaticamente.

        Chips que não tiveram erros nas últimas 6 horas têm seus contadores
        resetados para permitir recuperação gradual.

        Returns:
            {
                "chips_resetados": int,
                "detalhes": List[Dict]
            }
        """
        agora = datetime.now(timezone.utc)
        seis_horas_atras = (agora - timedelta(hours=6)).isoformat()

        try:
            # Buscar chips ativos com erros mas sem erro recente
            # (último erro > 6 horas atrás)
            result = (
                supabase.table("chips")
                .select("id, telefone, erros_ultimas_24h, ultimo_erro, trust_score")
                .eq("status", "active")
                .gt("erros_ultimas_24h", 0)
                .execute()
            )

            chips_para_resetar = []
            for chip in result.data or []:
                ultimo_erro = chip.get("ultimo_erro")

                # Se não tem último erro registrado ou foi há mais de 6h
                if not ultimo_erro or ultimo_erro < seis_horas_atras:
                    chips_para_resetar.append(chip)

            if not chips_para_resetar:
                logger.debug("[HealthMonitor] Nenhum chip para resetar erros_24h")
                return {"chips_resetados": 0, "detalhes": []}

            # Resetar erros
            detalhes = []
            for chip in chips_para_resetar:
                chip_id = chip["id"]
                erros_anteriores = chip.get("erros_ultimas_24h", 0)

                # Resetar para 0
                supabase.table("chips").update(
                    {
                        "erros_ultimas_24h": 0,
                        "updated_at": agora.isoformat(),
                    }
                ).eq("id", chip_id).execute()

                detalhes.append(
                    {
                        "chip_id": chip_id,
                        "telefone": chip.get("telefone", "")[-4:],
                        "erros_anteriores": erros_anteriores,
                        "trust_score": chip.get("trust_score"),
                    }
                )

            logger.info(
                f"[HealthMonitor] T08.4: Resetados erros_24h de {len(chips_para_resetar)} chips"
            )

            return {
                "chips_resetados": len(chips_para_resetar),
                "detalhes": detalhes,
            }

        except Exception as e:
            logger.error(f"[HealthMonitor] Erro ao resetar erros_24h: {e}")
            return {"chips_resetados": 0, "erro": str(e)}

    async def executar_manutencao_diaria(self) -> Dict:
        """
        Sprint 36 - T08.4: Executa manutenção diária dos chips.

        Deve ser chamado por um job diário.

        Returns:
            Resultado consolidado das manutenções
        """
        logger.info("[HealthMonitor] Iniciando manutenção diária")

        resultado = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "erros_resetados": {},
            "alertas_resolvidos": 0,
        }

        try:
            # 1. T08.4: Resetar contadores de erro
            resultado["erros_resetados"] = await self.resetar_erros_24h()

            # 2. Resolver alertas antigos (> 48h)
            dois_dias_atras = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()

            alertas_antigos = (
                supabase.table("chip_alerts")
                .select("id")
                .eq("resolved", False)
                .lt("created_at", dois_dias_atras)
                .execute()
            )

            for alerta in alertas_antigos.data or []:
                await self.resolver_alerta(alerta["id"], resolved_by="auto_expire")
                resultado["alertas_resolvidos"] += 1

            logger.info(
                f"[HealthMonitor] Manutenção diária concluída: "
                f"{resultado['erros_resetados'].get('chips_resetados', 0)} chips resetados, "
                f"{resultado['alertas_resolvidos']} alertas resolvidos"
            )

            return resultado

        except Exception as e:
            logger.error(f"[HealthMonitor] Erro na manutenção diária: {e}")
            resultado["erro"] = str(e)
            return resultado


# Singleton
health_monitor = HealthMonitor()
