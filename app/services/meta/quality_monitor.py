"""
Quality Monitor para chips Meta WhatsApp Business API.

Sprint 67 (Epic 67.1, Chunk 5).

Monitora qualidade dos chips Meta via Graph API,
registra histórico, auto-degrada/recovery com anti-flap,
e alerta via Slack.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.core.config import settings
from app.services.supabase import supabase
from app.services.http_client import get_http_client
from app.services.meta.quality_rules import (
    calcular_trust_recovery,
    verificar_anti_flap,
    deve_reativar_chip,
    deve_desativar_chip,
)

logger = logging.getLogger(__name__)


class MetaQualityMonitor:
    """
    Monitora qualidade de chips Meta via Graph API.

    - Poll periódico (cron */15)
    - Registra histórico em meta_quality_history
    - Auto-degrada e auto-recovery com anti-flap
    - Alerta Slack em mudanças de qualidade
    - Kill switch para WABA inteiro em caso de RED
    """

    def __init__(self):
        self.api_version = settings.META_GRAPH_API_VERSION

    async def verificar_quality_chips(self) -> dict:
        """
        Verifica qualidade de todos os chips Meta ativos.

        Returns:
            Dict com resumo: total, verificados, degradados, recuperados, erros.
        """
        resultado = {
            "total": 0,
            "verificados": 0,
            "degradados": 0,
            "recuperados": 0,
            "erros": 0,
        }

        try:
            resp = (
                supabase.table("chips")
                .select(
                    "id, telefone, meta_phone_number_id, meta_waba_id, meta_access_token, meta_quality_rating, trust_score, status"
                )
                .eq("provider", "meta")
                .in_("status", ["active", "warming", "ready"])
                .not_.is_("meta_phone_number_id", "null")
                .execute()
            )

            chips = resp.data or []
            resultado["total"] = len(chips)

            for chip in chips:
                try:
                    await self._verificar_chip(chip, resultado)
                    resultado["verificados"] += 1
                except Exception as e:
                    resultado["erros"] += 1
                    logger.error(
                        "Erro ao verificar quality chip %s: %s",
                        chip["id"],
                        e,
                    )

        except Exception as e:
            logger.error("Erro ao listar chips Meta para quality check: %s", e)
            resultado["erros"] += 1

        logger.info(
            "Quality check concluído: %d/%d verificados, %d degradados, %d recuperados, %d erros",
            resultado["verificados"],
            resultado["total"],
            resultado["degradados"],
            resultado["recuperados"],
            resultado["erros"],
        )

        return resultado

    async def _verificar_chip(self, chip: dict, resultado: dict) -> None:
        """Verifica qualidade de um chip individual."""
        quality_data = await self._consultar_quality_api(chip)
        if not quality_data:
            return

        new_rating = quality_data.get("quality_rating", "UNKNOWN")
        messaging_tier = quality_data.get("messaging_tier")
        previous_rating = chip.get("meta_quality_rating") or "UNKNOWN"

        # Registrar no histórico
        await self._registrar_quality(
            chip_id=chip["id"],
            waba_id=chip.get("meta_waba_id", ""),
            quality_rating=new_rating,
            previous_rating=previous_rating,
            messaging_tier=messaging_tier,
        )

        # Se mudou, processar
        if new_rating != previous_rating:
            logger.info(
                "Quality change chip %s: %s → %s",
                chip["telefone"],
                previous_rating,
                new_rating,
            )

            # Auto-degradar
            if deve_desativar_chip(previous_rating, new_rating):
                await self._auto_degradar_chip(chip, new_rating, previous_rating)
                resultado["degradados"] += 1

            # Auto-recovery
            elif deve_reativar_chip(previous_rating, new_rating):
                await self._auto_recovery_chip(chip, new_rating, previous_rating)
                resultado["recuperados"] += 1

            # Alertar Slack
            await self._alertar_slack(chip, previous_rating, new_rating)

            # Detectar padrão de degradação
            await self._detectar_padrao_degradacao(chip)

        # Atualizar rating no chip
        supabase.table("chips").update(
            {
                "meta_quality_rating": new_rating,
                "meta_messaging_tier": messaging_tier,
                "meta_tier_updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", chip["id"]).execute()

    async def _consultar_quality_api(self, chip: dict) -> Optional[dict]:
        """
        Consulta qualidade via Meta Graph API.

        GET /{phone_number_id}?fields=quality_rating,messaging_limit_tier
        """
        phone_id = chip.get("meta_phone_number_id")
        token = chip.get("meta_access_token")

        if not phone_id or not token:
            return None

        try:
            client = await get_http_client()
            resp = await client.get(
                f"https://graph.facebook.com/{self.api_version}/{phone_id}",
                params={"fields": "quality_rating,messaging_limit_tier"},
                headers={"Authorization": f"Bearer {token}"},
                timeout=15.0,
            )

            if resp.status_code != 200:
                logger.warning(
                    "Quality API error chip %s: %d %s",
                    chip["id"],
                    resp.status_code,
                    resp.text[:200],
                )
                return None

            data = resp.json()
            return {
                "quality_rating": data.get("quality_rating", "UNKNOWN"),
                "messaging_tier": data.get("messaging_limit_tier"),
            }

        except Exception as e:
            logger.error("Erro ao consultar Quality API chip %s: %s", chip["id"], e)
            return None

    async def _registrar_quality(
        self,
        chip_id: str,
        waba_id: str,
        quality_rating: str,
        previous_rating: str,
        messaging_tier: Optional[str] = None,
        source: str = "api_poll",
    ) -> None:
        """Registra entrada no histórico de qualidade."""
        try:
            supabase.table("meta_quality_history").insert(
                {
                    "chip_id": chip_id,
                    "waba_id": waba_id,
                    "quality_rating": quality_rating,
                    "previous_rating": previous_rating,
                    "messaging_tier": messaging_tier,
                    "source": source,
                }
            ).execute()
        except Exception as e:
            logger.error("Erro ao registrar quality history: %s", e)

    async def _obter_ultimo_rating(self, chip_id: str) -> Optional[str]:
        """Obtém último rating registrado para um chip."""
        try:
            resp = (
                supabase.table("meta_quality_history")
                .select("quality_rating")
                .eq("chip_id", chip_id)
                .order("checked_at", desc=True)
                .limit(1)
                .execute()
            )
            if resp.data:
                return resp.data[0]["quality_rating"]
        except Exception as e:
            logger.error("Erro ao obter último rating: %s", e)
        return None

    async def _auto_degradar_chip(self, chip: dict, new_rating: str, previous_rating: str) -> None:
        """Desativa chip por degradação de qualidade."""
        logger.warning(
            "Auto-degradando chip %s (%s → %s)",
            chip["telefone"],
            previous_rating,
            new_rating,
        )

        try:
            supabase.table("chips").update(
                {
                    "status": "cooldown",
                    "cooldown_until": (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat(),
                    "trust_score": 0,
                }
            ).eq("id", chip["id"]).execute()
        except Exception as e:
            logger.error("Erro ao degradar chip %s: %s", chip["id"], e)

    async def _auto_recovery_chip(self, chip: dict, new_rating: str, previous_rating: str) -> None:
        """Reativa chip após melhora de qualidade, respeitando anti-flap."""
        in_cooldown = await verificar_anti_flap(chip["id"])
        if in_cooldown:
            logger.info(
                "Chip %s em anti-flap cooldown, recovery adiado",
                chip["telefone"],
            )
            return

        new_trust = calcular_trust_recovery(
            previous_rating,
            new_rating,
            chip.get("trust_score", 50),
        )

        logger.info(
            "Auto-recovery chip %s (%s → %s), trust=%d",
            chip["telefone"],
            previous_rating,
            new_rating,
            new_trust,
        )

        try:
            supabase.table("chips").update(
                {
                    "status": "active",
                    "trust_score": new_trust,
                    "cooldown_until": None,
                }
            ).eq("id", chip["id"]).execute()
        except Exception as e:
            logger.error("Erro ao recovery chip %s: %s", chip["id"], e)

    async def _alertar_slack(self, chip: dict, previous_rating: str, new_rating: str) -> None:
        """Envia alerta de mudança de qualidade no Slack."""
        try:
            from app.services.slack import enviar_notificacao_slack

            emoji_map = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴", "UNKNOWN": "⚪"}
            emoji_prev = emoji_map.get(previous_rating, "⚪")
            emoji_new = emoji_map.get(new_rating, "⚪")

            texto = (
                f"📊 *Quality Change* — Chip `{chip.get('telefone', 'N/A')}`\n"
                f"{emoji_prev} {previous_rating} → {emoji_new} {new_rating}"
            )

            if new_rating == "RED":
                texto += "\n⚠️ *Chip desativado automaticamente*"

            await enviar_notificacao_slack(texto)

        except Exception as e:
            logger.warning("Erro ao alertar Slack quality change: %s", e)

    async def _detectar_padrao_degradacao(self, chip: dict) -> None:
        """Detecta padrão de degradação frequente (3+ em 7 dias)."""
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            resp = (
                supabase.table("meta_quality_history")
                .select("quality_rating", count="exact")
                .eq("chip_id", chip["id"])
                .in_("quality_rating", ["YELLOW", "RED"])
                .gte("checked_at", cutoff.isoformat())
                .execute()
            )

            count = resp.count or 0
            if count >= 3:
                logger.warning(
                    "Padrão de degradação detectado chip %s: %d eventos em 7 dias",
                    chip["telefone"],
                    count,
                )

        except Exception as e:
            logger.warning("Erro ao detectar padrão degradação: %s", e)

    async def kill_switch_waba(self, waba_id: str) -> dict:
        """
        Kill switch: desativa todos os chips de um WABA.

        Uso em emergência quando toda a conta está comprometida.
        """
        try:
            resp = (
                supabase.table("chips")
                .update(
                    {
                        "status": "cooldown",
                        "cooldown_until": (
                            datetime.now(timezone.utc) + timedelta(hours=24)
                        ).isoformat(),
                    }
                )
                .eq("meta_waba_id", waba_id)
                .in_("status", ["active", "warming", "ready"])
                .execute()
            )

            affected = len(resp.data) if resp.data else 0
            logger.critical(
                "KILL SWITCH ativado para WABA %s: %d chips desativados",
                waba_id,
                affected,
            )

            return {"waba_id": waba_id, "chips_desativados": affected}

        except Exception as e:
            logger.error("Erro no kill switch WABA %s: %s", waba_id, e)
            return {"waba_id": waba_id, "error": str(e)}

    async def obter_historico(
        self,
        chip_id: Optional[str] = None,
        waba_id: Optional[str] = None,
        limit: int = 50,
    ) -> list:
        """Obtém histórico de qualidade."""
        try:
            query = supabase.table("meta_quality_history").select("*")

            if chip_id:
                query = query.eq("chip_id", chip_id)
            if waba_id:
                query = query.eq("waba_id", waba_id)

            resp = query.order("checked_at", desc=True).limit(limit).execute()
            return resp.data or []

        except Exception as e:
            logger.error("Erro ao obter histórico quality: %s", e)
            return []


# Singleton
quality_monitor = MetaQualityMonitor()
