"""
Service for creating and managing dashboard notifications.
"""

import json
import os
from datetime import datetime
from typing import Optional

from app.services.supabase import supabase


async def criar_notificacao(
    tipo: str,
    titulo: str,
    corpo: str,
    prioridade: str = "medium",
    dados: Optional[dict] = None,
    user_ids: Optional[list] = None,
):
    """
    Cria notificacao para usuarios do dashboard.
    Se user_ids for None, notifica todos os usuarios ativos.
    """
    if user_ids is None:
        # Buscar todos os usuarios ativos
        users = (
            supabase.table("dashboard_users")
            .select("id")
            .eq("is_active", True)
            .execute()
        )
        user_ids = [u["id"] for u in (users.data or [])]

    if not user_ids:
        return []

    notifications = []
    for user_id in user_ids:
        notifications.append(
            {
                "user_id": user_id,
                "type": tipo,
                "title": titulo,
                "body": corpo,
                "priority": prioridade,
                "data": dados,
                "read": False,
                "created_at": datetime.now().isoformat(),
            }
        )

    result = supabase.table("dashboard_notifications").insert(notifications).execute()

    # Enviar push para quem tem subscription
    for user_id in user_ids:
        await enviar_push_para_usuario(
            user_id,
            {
                "title": titulo,
                "body": corpo,
                "priority": prioridade,
                "data": dados or {},
            },
        )

    return result.data


async def enviar_push_para_usuario(user_id: str, payload: dict):
    """Envia push notification para um usuario."""
    try:
        from pywebpush import WebPushException, webpush

        # Buscar subscription
        result = (
            supabase.table("dashboard_push_subscriptions")
            .select("subscription")
            .eq("user_id", user_id)
            .maybeSingle()
            .execute()
        )

        if not result.data:
            return

        subscription = result.data["subscription"]
        vapid_private_key = os.environ.get("VAPID_PRIVATE_KEY")

        if not vapid_private_key:
            return

        webpush(
            subscription_info=subscription,
            data=json.dumps(payload),
            vapid_private_key=vapid_private_key,
            vapid_claims={"sub": "mailto:support@revoluna.com"},
        )
    except ImportError:
        # pywebpush not installed
        pass
    except Exception as e:
        # Se subscription expirou (410), remover
        if hasattr(e, "response") and getattr(e.response, "status_code", 0) == 410:
            supabase.table("dashboard_push_subscriptions").delete().eq(
                "user_id", user_id
            ).execute()


async def notificar_handoff_solicitado(
    conversa_id: str, medico_nome: str, motivo: str
):
    """Notifica sobre handoff solicitado."""
    await criar_notificacao(
        tipo="handoff_request",
        titulo=f"Handoff: {medico_nome}",
        corpo=motivo,
        prioridade="high",
        dados={"conversation_id": conversa_id},
    )


async def notificar_rate_limit_warning(percent_hour: int, percent_day: int):
    """Notifica sobre rate limit proximo do limite."""
    maior = max(percent_hour, percent_day)
    periodo = "hora" if percent_hour >= percent_day else "dia"

    await criar_notificacao(
        tipo="rate_limit_warning",
        titulo="Rate Limit Alto",
        corpo=f"{maior}% do limite de {periodo} utilizado",
        prioridade="high" if maior >= 90 else "medium",
        dados={"percent_hour": percent_hour, "percent_day": percent_day},
    )


async def notificar_circuit_aberto(servico: str):
    """Notifica sobre circuit breaker aberto."""
    await criar_notificacao(
        tipo="circuit_open",
        titulo=f"Circuit Breaker: {servico}",
        corpo=f"Integracao {servico} esta com problemas",
        prioridade="critical",
        dados={"service": servico},
    )


async def notificar_conversao(medico_id: str, medico_nome: str, vaga_titulo: str):
    """Notifica sobre nova conversao (plantao confirmado)."""
    await criar_notificacao(
        tipo="new_conversion",
        titulo=f"Conversao: {medico_nome}",
        corpo=f"Confirmou interesse em {vaga_titulo}",
        prioridade="medium",
        dados={"doctor_id": medico_id},
    )


async def notificar_campanha_completa(
    campanha_id: str, campanha_nome: str, total_envios: int
):
    """Notifica sobre campanha finalizada."""
    await criar_notificacao(
        tipo="campaign_complete",
        titulo=f"Campanha finalizada",
        corpo=f"{campanha_nome}: {total_envios} envios",
        prioridade="low",
        dados={"campaign_id": campanha_id},
    )


async def notificar_alerta_sistema(titulo: str, mensagem: str):
    """Notifica sobre alerta de sistema."""
    await criar_notificacao(
        tipo="system_alert",
        titulo=titulo,
        corpo=mensagem,
        prioridade="critical",
    )
