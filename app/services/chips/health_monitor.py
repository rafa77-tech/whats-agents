"""
Health Monitor - Monitoramento proativo de chips em producao.

Sprint 26 - E04

Detecta:
- Taxa de resposta caindo
- Erros aumentando
- Desconexoes
- Trust Score degradando
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict

from app.services.supabase import supabase
from app.services.slack import enviar_slack

logger = logging.getLogger(__name__)


async def notificar_slack(mensagem: str, canal: str = "operacoes") -> bool:
    """Helper para enviar notificacao Slack."""
    emoji = ":robot_face:" if canal == "operacoes" else ":rotating_light:"
    try:
        return await enviar_slack({
            "text": mensagem,
            "username": "Julia Health Monitor",
            "icon_emoji": emoji,
        })
    except Exception as e:
        logger.warning(f"[HealthMonitor] Erro ao notificar Slack: {e}")
        return False


class HealthMonitor:
    """Monitor de saude dos chips."""

    def __init__(self):
        self._running = False
        self.thresholds = {
            "taxa_resposta_minima": 0.20,  # 20%
            "erros_por_hora_max": 5,
            "trust_drop_alerta": 10,  # Queda de 10 pontos em 24h
            "desconexao_timeout_minutos": 30,
        }

    async def verificar_saude_chips(self) -> List[Dict]:
        """
        Verifica saude de todos os chips ativos.

        Returns:
            Lista de alertas gerados
        """
        result = supabase.table("chips").select("*").eq(
            "status", "active"
        ).execute()

        alertas = []

        for chip in result.data or []:
            chip_alertas = await self._verificar_chip(chip)
            alertas.extend(chip_alertas)

        return alertas

    async def _verificar_chip(self, chip: Dict) -> List[Dict]:
        """Verifica saude de um chip individual."""
        alertas = []

        # 1. Verificar conexao
        if not chip.get("evolution_connected"):
            alertas.append(await self._criar_alerta(
                chip_id=chip["id"],
                tipo="desconectado",
                severity="critical",
                message=f"Chip {chip['telefone']} desconectado",
            ))

        # 2. Verificar taxa de resposta
        taxa = chip.get("taxa_resposta") or 0
        if taxa < self.thresholds["taxa_resposta_minima"]:
            alertas.append(await self._criar_alerta(
                chip_id=chip["id"],
                tipo="taxa_resposta_baixa",
                severity="warning",
                message=f"Chip {chip['telefone']}: Taxa de resposta {taxa:.1%} < 20%",
            ))

        # 3. Verificar erros
        erros = chip.get("erros_ultimas_24h") or 0
        limite_erros = self.thresholds["erros_por_hora_max"] * 24
        if erros > limite_erros:
            alertas.append(await self._criar_alerta(
                chip_id=chip["id"],
                tipo="muitos_erros",
                severity="warning",
                message=f"Chip {chip['telefone']}: {erros} erros nas ultimas 24h",
            ))

        # 4. Verificar queda de Trust Score
        queda = await self._verificar_queda_trust(chip)
        if queda >= self.thresholds["trust_drop_alerta"]:
            alertas.append(await self._criar_alerta(
                chip_id=chip["id"],
                tipo="trust_caindo",
                severity="warning",
                message=f"Chip {chip['telefone']}: Trust Score caiu {queda} pontos nas ultimas 24h",
            ))

        # 5. Verificar Trust Score critico
        trust = chip.get("trust_score") or 50
        if trust < 40:
            alertas.append(await self._criar_alerta(
                chip_id=chip["id"],
                tipo="trust_critico",
                severity="critical",
                message=f"Chip {chip['telefone']}: Trust Score critico ({trust})",
            ))

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
        existing = supabase.table("chip_alerts").select("id").eq(
            "chip_id", chip_id
        ).eq(
            "tipo", tipo
        ).eq(
            "resolved", False
        ).execute()

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
        result = supabase.table("chip_alerts").insert({
            "chip_id": chip_id,
            "tipo": tipo,
            "severity": severity,
            "message": message,
        }).execute()

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

        result = supabase.table("chip_trust_history").select(
            "score"
        ).eq(
            "chip_id", chip["id"]
        ).gte(
            "recorded_at", ontem
        ).order(
            "recorded_at", desc=False
        ).limit(1).execute()

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
        result = supabase.table("chips").select("*").eq(
            "status", "active"
        ).execute()

        chips = result.data or []

        # Classificar por saude
        saudaveis = [c for c in chips if (c.get("trust_score") or 0) >= 80]
        atencao = [c for c in chips if 60 <= (c.get("trust_score") or 0) < 80]
        criticos = [c for c in chips if (c.get("trust_score") or 0) < 60]

        # Buscar alertas nao resolvidos
        alertas = supabase.table("chip_alerts").select("*").eq(
            "resolved", False
        ).execute()

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
                sum(c.get("trust_score") or 0 for c in chips) / len(chips)
                if chips else 0
            ),
            "msgs_hoje": sum(c.get("msgs_enviadas_hoje") or 0 for c in chips),
            "chips_conectados": len([c for c in chips if c.get("evolution_connected")]),
            "chips_desconectados": len([c for c in chips if not c.get("evolution_connected")]),
        }

    async def resolver_alerta(self, alerta_id: str, resolved_by: str = "manual") -> Dict:
        """
        Resolve um alerta.

        Args:
            alerta_id: ID do alerta
            resolved_by: Quem resolveu

        Returns:
            Resultado da operacao
        """
        result = supabase.table("chip_alerts").update({
            "resolved": True,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "resolved_by": resolved_by,
        }).eq("id", alerta_id).execute()

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

            # Filtrar apenas novos alertas
            novos = [a for a in alertas if not a.get("duplicado")]

            # Notificar alertas criticos
            criticos = [a for a in novos if a["severity"] == "critical"]
            if criticos:
                mensagens = "\n".join([f"- {a['message']}" for a in criticos])
                await notificar_slack(
                    f":rotating_light: *{len(criticos)} alerta(s) critico(s)*\n{mensagens}",
                    canal="alertas"
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


# Singleton
health_monitor = HealthMonitor()
