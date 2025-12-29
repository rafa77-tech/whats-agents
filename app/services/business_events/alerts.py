"""
Sistema de alertas de negocio.

Sprint 17 - E07

Detecta anomalias e notifica via Slack.
"""
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from enum import Enum

from app.services.supabase import supabase
from app.services.redis import redis_client
from app.services.slack import enviar_slack

logger = logging.getLogger(__name__)


# =============================================================================
# E07.1: Tipos e Dataclasses
# =============================================================================


class AlertType(Enum):
    """Tipos de alerta."""
    HANDOFF_SPIKE = "handoff_spike"
    RECUSA_SPIKE = "recusa_spike"
    CONVERSION_DROP = "conversion_drop"
    # Alertas P0 de confirmação de plantão (Sprint 17)
    CONFIRMATION_OVERDUE = "confirmation_overdue"     # pendentes > 24h
    SHIFT_TRANSITION_FAILED = "shift_transition_failed"  # reservadas vencidas não transicionaram


class AlertSeverity(Enum):
    """Severidade do alerta."""
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Um alerta detectado."""
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    description: str
    hospital_id: Optional[str] = None
    hospital_name: Optional[str] = None
    current_value: float = 0.0
    baseline_value: float = 0.0
    threshold_pct: float = 0.0
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Serializa para storage/notificacao."""
        return {
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "hospital_id": self.hospital_id,
            "hospital_name": self.hospital_name,
            "current_value": self.current_value,
            "baseline_value": self.baseline_value,
            "threshold_pct": self.threshold_pct,
            "detected_at": self.detected_at.isoformat(),
        }


# =============================================================================
# E07.1: Funcoes Auxiliares
# =============================================================================


async def _get_event_count(
    event_type: str,
    hours: int,
    hospital_id: Optional[str] = None,
) -> int:
    """Conta eventos nas ultimas N horas."""
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    try:
        query = (
            supabase.table("business_events")
            .select("id", count="exact")
            .eq("event_type", event_type)
            .gte("ts", since)
        )

        if hospital_id:
            query = query.eq("hospital_id", hospital_id)

        response = query.execute()
        return response.count or 0

    except Exception as e:
        logger.error(f"Erro ao contar eventos: {e}")
        return 0


async def _get_hospital_name(hospital_id: str) -> str:
    """Busca nome do hospital."""
    try:
        response = (
            supabase.table("hospitais")
            .select("nome")
            .eq("id", hospital_id)
            .limit(1)
            .execute()
        )

        if response.data:
            return response.data[0].get("nome", hospital_id[:8])
        return hospital_id[:8]

    except Exception:
        return hospital_id[:8]


# =============================================================================
# E07.1: Detectores de Anomalias
# =============================================================================


async def detect_handoff_spike(
    min_handoffs: int = 5,
) -> List[Alert]:
    """
    Detecta spike de handoffs por hospital.

    Regra: handoffs_24h >= max(5, 2x media 7d do hospital)

    Args:
        min_handoffs: Minimo de handoffs para considerar (default 5)

    Returns:
        Lista de alertas detectados
    """
    alerts = []

    try:
        since_7d = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

        response = (
            supabase.table("business_events")
            .select("hospital_id")
            .eq("event_type", "handoff_created")
            .gte("ts", since_7d)
            .not_.is_("hospital_id", "null")
            .execute()
        )

        hospital_ids = list(set(row["hospital_id"] for row in response.data or []))

        for hospital_id in hospital_ids:
            handoffs_24h = await _get_event_count("handoff_created", 24, hospital_id)
            handoffs_7d = await _get_event_count("handoff_created", 168, hospital_id)
            avg_daily_7d = handoffs_7d / 7

            threshold = max(min_handoffs, avg_daily_7d * 2)

            if handoffs_24h >= threshold:
                hospital_name = await _get_hospital_name(hospital_id)

                alerts.append(Alert(
                    alert_type=AlertType.HANDOFF_SPIKE,
                    severity=AlertSeverity.CRITICAL if handoffs_24h >= threshold * 1.5 else AlertSeverity.WARNING,
                    title=f"Spike de Handoff: {hospital_name}",
                    description=(
                        f"Hospital {hospital_name} teve {handoffs_24h} handoffs nas ultimas 24h. "
                        f"Threshold: {threshold:.0f} (2x media 7d: {avg_daily_7d:.1f}/dia)."
                    ),
                    hospital_id=hospital_id,
                    hospital_name=hospital_name,
                    current_value=handoffs_24h,
                    baseline_value=avg_daily_7d,
                    threshold_pct=threshold,
                ))

    except Exception as e:
        logger.error(f"Erro ao detectar handoff spike: {e}")

    return alerts


async def detect_decline_spike(
    min_offers: int = 10,
    threshold_pct: float = 40.0,
) -> List[Alert]:
    """
    Detecta spike de recusas de oferta.

    Regra: offer_declined / offer_made > 40% nas ultimas 24h, com offers >= 10

    Args:
        min_offers: Minimo de ofertas para considerar
        threshold_pct: Taxa maxima aceitavel de declines (default 40%)

    Returns:
        Lista de alertas detectados
    """
    alerts = []

    try:
        offers = await _get_event_count("offer_made", 24)
        declined = await _get_event_count("offer_declined", 24)

        if offers >= min_offers:
            decline_rate = (declined / offers) * 100

            if decline_rate > threshold_pct:
                alerts.append(Alert(
                    alert_type=AlertType.RECUSA_SPIKE,
                    severity=AlertSeverity.CRITICAL if decline_rate > 60 else AlertSeverity.WARNING,
                    title="Spike de Recusas de Oferta",
                    description=(
                        f"Taxa de recusa nas ultimas 24h: {decline_rate:.1f}% "
                        f"(recusaram {declined} de {offers} ofertas). "
                        f"Threshold: > {threshold_pct}%."
                    ),
                    current_value=decline_rate,
                    baseline_value=threshold_pct,
                    threshold_pct=threshold_pct,
                ))

    except Exception as e:
        logger.error(f"Erro ao detectar spike de recusas: {e}")

    return alerts


async def detect_conversion_drop(
    min_offers: int = 10,
    drop_pct: float = 30.0,
) -> List[Alert]:
    """
    Detecta queda na taxa de conversao vs media historica.

    Regra: offer_accepted / offer_made caiu > 30% vs media 7d

    Args:
        min_offers: Minimo de ofertas para considerar
        drop_pct: Queda percentual vs media 7d para alertar (default 30%)

    Returns:
        Lista de alertas detectados
    """
    alerts = []

    try:
        offers_24h = await _get_event_count("offer_made", 24)
        accepted_24h = await _get_event_count("offer_accepted", 24)

        offers_7d = await _get_event_count("offer_made", 168)
        accepted_7d = await _get_event_count("offer_accepted", 168)

        if offers_24h >= min_offers and offers_7d > offers_24h:
            current_rate = (accepted_24h / offers_24h) * 100

            offers_prev = offers_7d - offers_24h
            accepted_prev = accepted_7d - accepted_24h
            if offers_prev > 0:
                avg_rate_7d = (accepted_prev / offers_prev) * 100
            else:
                avg_rate_7d = 0

            if avg_rate_7d > 0:
                drop = ((avg_rate_7d - current_rate) / avg_rate_7d) * 100

                if drop >= drop_pct:
                    alerts.append(Alert(
                        alert_type=AlertType.CONVERSION_DROP,
                        severity=AlertSeverity.CRITICAL if drop >= 50 else AlertSeverity.WARNING,
                        title="Queda na Taxa de Aceite",
                        description=(
                            f"Taxa de aceite caiu {drop:.1f}% vs media 7d. "
                            f"Atual: {current_rate:.1f}%, Media 7d: {avg_rate_7d:.1f}%. "
                            f"(aceitaram {accepted_24h} de {offers_24h} ofertas hoje)."
                        ),
                        current_value=current_rate,
                        baseline_value=avg_rate_7d,
                        threshold_pct=drop,
                    ))

    except Exception as e:
        logger.error(f"Erro ao detectar queda de conversao: {e}")

    return alerts


async def detect_confirmation_overdue(
    max_hours: int = 24,
) -> List[Alert]:
    """
    Detecta vagas pendentes de confirmação há mais de N horas.

    Regra P0: pendente_confirmacao_em < now() - 24h = alerta

    Args:
        max_hours: Máximo de horas para confirmar (default 24h)

    Returns:
        Lista de alertas detectados
    """
    alerts = []

    try:
        limite = (datetime.now(timezone.utc) - timedelta(hours=max_hours)).isoformat()

        result = supabase.table("vagas").select(
            "id", count="exact"
        ).eq(
            "status", "pendente_confirmacao"
        ).lt(
            "pendente_confirmacao_em", limite
        ).execute()

        count = result.count or 0

        if count > 0:
            alerts.append(Alert(
                alert_type=AlertType.CONFIRMATION_OVERDUE,
                severity=AlertSeverity.CRITICAL if count >= 5 else AlertSeverity.WARNING,
                title="Confirmações de Plantão Atrasadas",
                description=(
                    f"{count} plantão(ões) aguardando confirmação há mais de {max_hours}h. "
                    f"Acesse /jobs/pendentes-confirmacao para revisar."
                ),
                current_value=float(count),
                baseline_value=0,
                threshold_pct=0,
            ))

    except Exception as e:
        logger.error(f"Erro ao detectar confirmações atrasadas: {e}")

    return alerts


async def detect_shift_transition_failed(
    buffer_hours: int = 2,
) -> List[Alert]:
    """
    Detecta vagas reservadas que deveriam ter transicionado mas não transitaram.

    Regra P0: Se existem reservadas com fim_plantao < now() - buffer,
    significa que o job de transição falhou.

    Args:
        buffer_hours: Buffer após fim do plantão (default 2h)

    Returns:
        Lista de alertas detectados
    """
    alerts = []

    try:
        from app.services.confirmacao_plantao import BUFFER_HORAS

        # Usar RPC para contar (calcula data+hora corretamente)
        limite = (datetime.now(timezone.utc) - timedelta(hours=buffer_hours)).isoformat()

        result = supabase.rpc("contar_reservadas_vencidas", {
            "limite_ts": limite
        }).execute()

        count = result.data if isinstance(result.data, int) else 0

        if count > 0:
            alerts.append(Alert(
                alert_type=AlertType.SHIFT_TRANSITION_FAILED,
                severity=AlertSeverity.CRITICAL,
                title="Job de Transição de Plantões Falhou",
                description=(
                    f"{count} plantão(ões) reservado(s) com data vencida não foram "
                    f"transicionados para pendente_confirmacao. "
                    f"Verifique se o job processar_confirmacao_plantao está rodando."
                ),
                current_value=float(count),
                baseline_value=0,
                threshold_pct=0,
            ))

    except Exception as e:
        logger.error(f"Erro ao detectar falha de transição: {e}")

    return alerts


async def detect_all_anomalies() -> List[Alert]:
    """Executa todos os detectores de anomalia."""
    all_alerts = []

    all_alerts.extend(await detect_handoff_spike())
    all_alerts.extend(await detect_decline_spike())
    all_alerts.extend(await detect_conversion_drop())
    # Alertas P0 de confirmação de plantão
    all_alerts.extend(await detect_confirmation_overdue())
    all_alerts.extend(await detect_shift_transition_failed())

    return all_alerts


# =============================================================================
# E07.2: Notificador Slack
# =============================================================================


def _get_action_text(alert: Alert) -> str:
    """Retorna texto de acao sugerida."""
    if alert.alert_type == AlertType.HANDOFF_SPIKE:
        return (
            "*Acoes sugeridas:*\n"
            "- Verificar conversas recentes do hospital\n"
            "- Revisar se ha problema com ofertas/precos\n"
            "- Considerar pausar campanhas temporariamente"
        )

    elif alert.alert_type == AlertType.RECUSA_SPIKE:
        return (
            "*Acoes sugeridas:*\n"
            "- Revisar abordagem das ofertas\n"
            "- Verificar se valores estao competitivos\n"
            "- Analisar padroes de recusa (horarios, hospitais)"
        )

    elif alert.alert_type == AlertType.CONVERSION_DROP:
        return (
            "*Acoes sugeridas:*\n"
            "- Revisar qualidade das ofertas recentes\n"
            "- Verificar se valores estao competitivos\n"
            "- Analisar feedback de medicos"
        )

    elif alert.alert_type == AlertType.CONFIRMATION_OVERDUE:
        return (
            "*Acoes sugeridas:*\n"
            "- Revisar plantoes pendentes no Slack\n"
            "- Confirmar se plantoes ocorreram\n"
            "- GET /jobs/pendentes-confirmacao"
        )

    elif alert.alert_type == AlertType.SHIFT_TRANSITION_FAILED:
        return (
            "*Acoes sugeridas:*\n"
            "- Verificar se scheduler esta rodando\n"
            "- POST /jobs/processar-confirmacao-plantao\n"
            "- Verificar logs do julia-scheduler"
        )

    return "*Acao:* Investigar causa"


def _format_slack_message(alert: Alert) -> dict:
    """Formata alerta para Slack."""
    emoji = "🚨" if alert.severity == AlertSeverity.CRITICAL else "⚠️"
    color = "#FF0000" if alert.severity == AlertSeverity.CRITICAL else "#FFA500"

    fields = [
        {
            "title": "Descricao",
            "value": alert.description,
            "short": False,
        },
        {
            "title": "Severidade",
            "value": alert.severity.value.upper(),
            "short": True,
        },
        {
            "title": "Tipo",
            "value": alert.alert_type.value,
            "short": True,
        },
    ]

    if alert.hospital_name:
        fields.append({
            "title": "Hospital",
            "value": alert.hospital_name,
            "short": True,
        })

    fields.append({
        "title": "Acoes",
        "value": _get_action_text(alert).replace("*", "").replace("\n", " "),
        "short": False,
    })

    return {
        "text": f"{emoji} {alert.title}",
        "attachments": [
            {
                "color": color,
                "title": alert.title,
                "fields": fields,
                "footer": f"Alerta detectado as {alert.detected_at.strftime('%H:%M')}",
                "ts": int(alert.detected_at.timestamp()),
            },
        ],
    }


async def send_alert_to_slack(alert: Alert) -> bool:
    """
    Envia alerta para Slack.

    Args:
        alert: Alerta a enviar

    Returns:
        True se enviado com sucesso
    """
    try:
        message = _format_slack_message(alert)
        result = await enviar_slack(message)

        if result:
            logger.info(f"Alerta enviado ao Slack: {alert.title}")
        return result

    except Exception as e:
        logger.error(f"Erro ao enviar alerta ao Slack: {e}")
        return False


# =============================================================================
# E07.3: Cooldown de Alertas
# =============================================================================


ALERT_COOLDOWN_SECONDS = 3600  # 1 hora


def _get_alert_key(alert: Alert) -> str:
    """Gera chave unica para o alerta."""
    content = f"{alert.alert_type.value}:{alert.hospital_id or 'global'}"
    return f"alert:cooldown:{hashlib.md5(content.encode()).hexdigest()[:12]}"


async def is_in_cooldown(alert: Alert) -> bool:
    """Verifica se alerta esta em cooldown."""
    key = _get_alert_key(alert)

    try:
        exists = await redis_client.exists(key)
        return exists > 0
    except Exception:
        return False


async def set_cooldown(alert: Alert) -> None:
    """Define cooldown para alerta."""
    key = _get_alert_key(alert)

    try:
        await redis_client.setex(
            key,
            ALERT_COOLDOWN_SECONDS,
            alert.detected_at.isoformat(),
        )
    except Exception as e:
        logger.warning(f"Erro ao definir cooldown: {e}")


async def process_and_notify_alerts(alerts: List[Alert]) -> int:
    """
    Processa lista de alertas e notifica (respeitando cooldown).

    Args:
        alerts: Lista de alertas detectados

    Returns:
        Numero de alertas enviados
    """
    sent = 0

    for alert in alerts:
        if await is_in_cooldown(alert):
            logger.debug(f"Alerta em cooldown: {alert.title}")
            continue

        alert_id = await persist_alert(alert)

        if await send_alert_to_slack(alert):
            await set_cooldown(alert)
            if alert_id:
                await mark_alert_notified(alert_id)
            sent += 1

    return sent


# =============================================================================
# E07.5: Persistencia de Alertas
# =============================================================================


async def persist_alert(alert: Alert) -> Optional[str]:
    """Persiste alerta no banco."""
    try:
        data = {
            "alert_type": alert.alert_type.value,
            "severity": alert.severity.value,
            "title": alert.title,
            "description": alert.description,
            "hospital_id": alert.hospital_id,
            "current_value": alert.current_value,
            "baseline_value": alert.baseline_value,
            "threshold_pct": alert.threshold_pct,
        }

        response = (
            supabase.table("business_alerts")
            .insert(data)
            .execute()
        )

        if response.data:
            return response.data[0].get("alert_id")
        return None

    except Exception as e:
        logger.error(f"Erro ao persistir alerta: {e}")
        return None


async def mark_alert_notified(alert_id: str) -> None:
    """Marca alerta como notificado."""
    try:
        supabase.table("business_alerts").update({
            "notified": True,
            "notified_at": datetime.now(timezone.utc).isoformat(),
        }).eq("alert_id", alert_id).execute()
    except Exception as e:
        logger.error(f"Erro ao marcar alerta notificado: {e}")


async def get_recent_alerts(
    hours: int = 24,
    alert_type: Optional[str] = None,
) -> List[dict]:
    """
    Busca alertas recentes.

    Args:
        hours: Janela de tempo
        alert_type: Filtrar por tipo

    Returns:
        Lista de alertas
    """
    try:
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        query = (
            supabase.table("business_alerts")
            .select("*")
            .gte("ts", since)
            .order("ts", desc=True)
        )

        if alert_type:
            query = query.eq("alert_type", alert_type)

        response = query.execute()
        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao buscar alertas: {e}")
        return []
