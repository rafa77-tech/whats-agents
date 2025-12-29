# Epic 07: Sistema de Alertas

## Objetivo

Implementar alertas proativos para situações críticas de negócio, notificando via Slack.

## Contexto

### Alertas P0 (Recomendação do Professor - Thresholds que não dão falso positivo)

| Alerta | Regra | Volume Mínimo |
|--------|-------|---------------|
| **Spike de Handoff** | `handoffs_24h >= max(5, 2x média 7d do hospital)` | 5 handoffs |
| **Spike de Declines** | `offer_declined / offer_made > 40%` nas últimas 24h | 10 ofertas |
| **Queda de Aceite** | `offer_accepted / offer_made` caiu > 30% vs média 7d | Volume mínimo |

**Por que esses 3 juntos:** Te avisam "algo mudou" antes de virar incêndio.

### Princípios

1. **Conservador:** Alertar pouco, mas alertar certo
2. **Acionável:** Toda notificação tem ação clara
3. **Contextual:** Inclui dados para investigação
4. **Não-repetitivo:** Cooldown entre alertas iguais

---

## Story 7.1: Detector de Anomalias

### Objetivo
Criar detector que compara métricas atuais com baseline.

### Tarefas

1. **Criar módulo de detecção**:

```python
# app/services/business_events/alerts.py

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List
from enum import Enum

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


class AlertType(Enum):
    """Tipos de alerta."""
    HANDOFF_SPIKE = "handoff_spike"
    RECUSA_SPIKE = "recusa_spike"
    CONVERSION_DROP = "conversion_drop"


class AlertSeverity(Enum):
    """Severidade do alerta."""
    WARNING = "warning"   # Atenção
    CRITICAL = "critical"  # Ação imediata


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
    detected_at: datetime = None

    def __post_init__(self):
        if self.detected_at is None:
            self.detected_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """Serializa para storage/notificação."""
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


async def _get_event_count(
    event_type: str,
    hours: int,
    hospital_id: Optional[str] = None,
) -> int:
    """Conta eventos nas últimas N horas."""
    since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

    try:
        query = (
            supabase.table("business_events")
            .select("event_id", count="exact")
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


async def detect_handoff_spike(
    min_handoffs: int = 5,
) -> List[Alert]:
    """
    Detecta spike de handoffs por hospital.

    Regra (Professor): handoffs_24h >= max(5, 2x média 7d do hospital)

    Args:
        min_handoffs: Mínimo de handoffs para considerar (default 5)

    Returns:
        Lista de alertas detectados
    """
    alerts = []

    try:
        # Buscar hospitais com handoffs nos últimos 7 dias
        since_7d = (datetime.utcnow() - timedelta(days=7)).isoformat()

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
            # Handoffs nas últimas 24h
            handoffs_24h = await _get_event_count("handoff_created", 24, hospital_id)

            # Média diária nos últimos 7 dias
            handoffs_7d = await _get_event_count("handoff_created", 168, hospital_id)  # 7*24h
            avg_daily_7d = handoffs_7d / 7

            # Regra: handoffs_24h >= max(5, 2x média 7d)
            threshold = max(min_handoffs, avg_daily_7d * 2)

            if handoffs_24h >= threshold:
                hospital_name = await _get_hospital_name(hospital_id)

                alerts.append(Alert(
                    alert_type=AlertType.HANDOFF_SPIKE,
                    severity=AlertSeverity.CRITICAL if handoffs_24h >= threshold * 1.5 else AlertSeverity.WARNING,
                    title=f"Spike de Handoff: {hospital_name}",
                    description=(
                        f"Hospital {hospital_name} teve {handoffs_24h} handoffs nas últimas 24h. "
                        f"Threshold: {threshold:.0f} (2x média 7d: {avg_daily_7d:.1f}/dia)."
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

    Regra (Professor): offer_declined / offer_made > 40% nas últimas 24h, com offers >= 10

    Args:
        min_offers: Mínimo de ofertas para considerar
        threshold_pct: Taxa máxima aceitável de declines (default 40%)

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
                        f"Taxa de recusa nas últimas 24h: {decline_rate:.1f}% "
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
    Detecta queda na taxa de conversão vs média histórica.

    Regra (Professor): offer_accepted / offer_made caiu > 30% vs média 7d

    Args:
        min_offers: Mínimo de ofertas para considerar
        drop_pct: Queda percentual vs média 7d para alertar (default 30%)

    Returns:
        Lista de alertas detectados
    """
    alerts = []

    try:
        # Últimas 24h
        offers_24h = await _get_event_count("offer_made", 24)
        accepted_24h = await _get_event_count("offer_accepted", 24)

        # Média dos últimos 7 dias (excluindo últimas 24h)
        offers_7d = await _get_event_count("offer_made", 168)  # 7*24h
        accepted_7d = await _get_event_count("offer_accepted", 168)

        if offers_24h >= min_offers and offers_7d > offers_24h:
            # Taxa atual
            current_rate = (accepted_24h / offers_24h) * 100

            # Taxa média 7d (excluindo hoje)
            offers_prev = offers_7d - offers_24h
            accepted_prev = accepted_7d - accepted_24h
            if offers_prev > 0:
                avg_rate_7d = (accepted_prev / offers_prev) * 100
            else:
                avg_rate_7d = 0

            # Calcular queda percentual
            if avg_rate_7d > 0:
                drop = ((avg_rate_7d - current_rate) / avg_rate_7d) * 100

                if drop >= drop_pct:
                    alerts.append(Alert(
                        alert_type=AlertType.CONVERSION_DROP,
                        severity=AlertSeverity.CRITICAL if drop >= 50 else AlertSeverity.WARNING,
                        title="Queda na Taxa de Aceite",
                        description=(
                            f"Taxa de aceite caiu {drop:.1f}% vs média 7d. "
                            f"Atual: {current_rate:.1f}%, Média 7d: {avg_rate_7d:.1f}%. "
                            f"(aceitaram {accepted_24h} de {offers_24h} ofertas hoje)."
                        ),
                        current_value=current_rate,
                        baseline_value=avg_rate_7d,
                        threshold_pct=drop,
                    ))

    except Exception as e:
        logger.error(f"Erro ao detectar queda de conversão: {e}")

    return alerts


async def detect_all_anomalies() -> List[Alert]:
    """Executa todos os detectores de anomalia."""
    all_alerts = []

    all_alerts.extend(await detect_handoff_spike())
    all_alerts.extend(await detect_decline_spike())
    all_alerts.extend(await detect_conversion_drop())

    return all_alerts


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
```

### DoD

- [ ] Classe `Alert` com todos campos necessários
- [ ] Detector `detect_handoff_spike` implementado
- [ ] Detector `detect_conversion_drop` implementado
- [ ] Função `detect_all_anomalies` agregadora
- [ ] Thresholds configuráveis

---

## Story 7.2: Notificador Slack

### Objetivo
Enviar alertas para canal do Slack.

### Tarefas

1. **Criar formatador de mensagem Slack**:

```python
# app/services/business_events/alerts.py (continuação)

from app.services.slack.client import enviar_mensagem_slack

ALERT_CHANNEL = "#alertas-julia"  # Configurar via env


def _format_slack_message(alert: Alert) -> dict:
    """Formata alerta para Slack Block Kit."""

    # Emoji por severidade
    emoji = "🚨" if alert.severity == AlertSeverity.CRITICAL else "⚠️"

    # Cor por severidade
    color = "#FF0000" if alert.severity == AlertSeverity.CRITICAL else "#FFA500"

    return {
        "attachments": [
            {
                "color": color,
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"{emoji} {alert.title}",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": alert.description,
                        },
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": (
                                    f"*Severidade:* {alert.severity.value.upper()} | "
                                    f"*Tipo:* {alert.alert_type.value} | "
                                    f"*Detectado:* {alert.detected_at.strftime('%H:%M')}"
                                ),
                            },
                        ],
                    },
                    {
                        "type": "divider",
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": _get_action_text(alert),
                        },
                    },
                ],
            },
        ],
    }


def _get_action_text(alert: Alert) -> str:
    """Retorna texto de ação sugerida."""
    if alert.alert_type == AlertType.HANDOFF_SPIKE:
        return (
            "*Ações sugeridas:*\n"
            "• Verificar conversas recentes do hospital\n"
            "• Revisar se há problema com ofertas/preços\n"
            "• Considerar pausar campanhas temporariamente"
        )

    elif alert.alert_type == AlertType.CONVERSION_DROP:
        return (
            "*Ações sugeridas:*\n"
            "• Revisar qualidade das ofertas recentes\n"
            "• Verificar se valores estão competitivos\n"
            "• Analisar feedback de médicos"
        )

    return "*Ação:* Investigar causa"


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

        await enviar_mensagem_slack(
            channel=ALERT_CHANNEL,
            text=alert.title,  # Fallback
            **message,
        )

        logger.info(f"Alerta enviado ao Slack: {alert.title}")
        return True

    except Exception as e:
        logger.error(f"Erro ao enviar alerta ao Slack: {e}")
        return False
```

### DoD

- [ ] Formatador de mensagem Slack
- [ ] Emoji e cor por severidade
- [ ] Ações sugeridas por tipo de alerta
- [ ] Função `send_alert_to_slack` implementada
- [ ] Canal configurável via env

---

## Story 7.3: Cooldown de Alertas

### Objetivo
Evitar spam de alertas repetidos.

### Tarefas

1. **Implementar cooldown com Redis**:

```python
# app/services/business_events/alerts.py (continuação)

import hashlib
from app.services.redis_client import redis_client

ALERT_COOLDOWN_SECONDS = 3600  # 1 hora


def _get_alert_key(alert: Alert) -> str:
    """Gera chave única para o alerta."""
    # Hash baseado em tipo + hospital
    content = f"{alert.alert_type.value}:{alert.hospital_id or 'global'}"
    return f"alert:cooldown:{hashlib.md5(content.encode()).hexdigest()[:12]}"


async def is_in_cooldown(alert: Alert) -> bool:
    """Verifica se alerta está em cooldown."""
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
        Número de alertas enviados
    """
    sent = 0

    for alert in alerts:
        # Verificar cooldown
        if await is_in_cooldown(alert):
            logger.debug(f"Alerta em cooldown: {alert.title}")
            continue

        # Enviar
        if await send_alert_to_slack(alert):
            await set_cooldown(alert)
            sent += 1

    return sent
```

### DoD

- [ ] Função `is_in_cooldown` implementada
- [ ] Função `set_cooldown` implementada
- [ ] Cooldown de 1h entre alertas iguais
- [ ] Chave única por tipo + hospital

---

## Story 7.4: Scheduler de Verificação

### Objetivo
Rodar verificação de alertas periodicamente.

### Tarefas

1. **Criar job de verificação**:

```python
# app/workers/alert_checker.py

import asyncio
import logging
from datetime import datetime

from app.services.business_events.alerts import (
    detect_all_anomalies,
    process_and_notify_alerts,
)

logger = logging.getLogger(__name__)

CHECK_INTERVAL_MINUTES = 15


async def check_alerts_job():
    """Job que verifica alertas periodicamente."""
    logger.info("Iniciando verificação de alertas...")

    try:
        # Detectar anomalias
        alerts = await detect_all_anomalies()

        if alerts:
            logger.info(f"Detectados {len(alerts)} alertas potenciais")

            # Processar e notificar (com cooldown)
            sent = await process_and_notify_alerts(alerts)
            logger.info(f"Enviados {sent} alertas ao Slack")
        else:
            logger.debug("Nenhuma anomalia detectada")

    except Exception as e:
        logger.error(f"Erro no job de alertas: {e}")


async def run_alert_scheduler():
    """Roda o scheduler de alertas."""
    logger.info(f"Alert scheduler iniciado (intervalo: {CHECK_INTERVAL_MINUTES}min)")

    while True:
        await check_alerts_job()
        await asyncio.sleep(CHECK_INTERVAL_MINUTES * 60)
```

2. **Integrar no startup da aplicação**:

```python
# app/main.py (adição)

from app.workers.alert_checker import run_alert_scheduler

@app.on_event("startup")
async def startup_alert_scheduler():
    """Inicia scheduler de alertas."""
    asyncio.create_task(run_alert_scheduler())
```

### DoD

- [ ] Job `check_alerts_job` implementado
- [ ] Scheduler roda a cada 15 minutos
- [ ] Integrado no startup da aplicação
- [ ] Logs informativos

---

## Story 7.5: Persistência de Alertas

### Objetivo
Salvar histórico de alertas para análise posterior.

### Tarefas

1. **Criar tabela de alertas**:

```sql
-- Migration: create_alerts_table
-- Sprint 17 - E07

CREATE TABLE IF NOT EXISTS public.business_alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),

    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,

    hospital_id UUID REFERENCES public.hospitais(id) ON DELETE SET NULL,
    current_value NUMERIC,
    baseline_value NUMERIC,
    threshold_pct NUMERIC,

    notified BOOLEAN DEFAULT FALSE,
    notified_at TIMESTAMPTZ,

    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by TEXT,
    acknowledged_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_business_alerts_ts ON business_alerts(ts DESC);
CREATE INDEX idx_business_alerts_type ON business_alerts(alert_type);
CREATE INDEX idx_business_alerts_hospital ON business_alerts(hospital_id) WHERE hospital_id IS NOT NULL;

COMMENT ON TABLE business_alerts IS 'Sprint 17: Histórico de alertas de negócio';
```

2. **Persistir alertas antes de notificar**:

```python
# app/services/business_events/alerts.py (adição)

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
            return response.data[0]["alert_id"]
        return None

    except Exception as e:
        logger.error(f"Erro ao persistir alerta: {e}")
        return None


async def mark_alert_notified(alert_id: str) -> None:
    """Marca alerta como notificado."""
    try:
        supabase.table("business_alerts").update({
            "notified": True,
            "notified_at": datetime.utcnow().isoformat(),
        }).eq("alert_id", alert_id).execute()
    except Exception as e:
        logger.error(f"Erro ao marcar alerta notificado: {e}")
```

### DoD

- [ ] Tabela `business_alerts` criada
- [ ] Função `persist_alert` implementada
- [ ] Função `mark_alert_notified` implementada
- [ ] Histórico disponível para consulta

---

## Checklist do Épico

- [ ] **S17.E07.1** - Detector de anomalias
- [ ] **S17.E07.2** - Notificador Slack
- [ ] **S17.E07.3** - Cooldown de alertas
- [ ] **S17.E07.4** - Scheduler de verificação
- [ ] **S17.E07.5** - Persistência de alertas
- [ ] Alertas chegam no Slack
- [ ] Cooldown evita spam
- [ ] Ações sugeridas são úteis
- [ ] Histórico persistido para análise
