# E01 - Estrutura e Tipos

**Epico:** E01
**Nome:** Estrutura e Tipos
**Dependencias:** Nenhuma
**Prioridade:** Alta (fundacao)

---

## Objetivo

Criar a estrutura de diretorios e os tipos (dataclasses/enums) que serao usados por todos os outros epicos. Este e o epico fundacional - todos os outros dependem dele.

---

## Entregaveis

### 1. Estrutura de Diretorios

```
app/services/notifications/
├── __init__.py           # Exports publicos
├── types.py              # Todos os tipos
└── exceptions.py         # Excecoes customizadas
```

### 2. Arquivo: `types.py`

```python
"""
Tipos do sistema de notificacoes centralizadas.

Sprint 41 - NotificationHub
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List
from uuid import uuid4


class AlertCategory(Enum):
    """Categoria de alerta que define comportamento."""
    CRITICAL = "critical"      # Imediato, 24/7, cooldown 15min
    ATTENTION = "attention"    # 08-20h, cooldown 30min
    DIGEST = "digest"          # Batched a cada hora
    INFO = "info"              # Baixa prioridade, cooldown 60min


class AlertDomain(Enum):
    """Dominio/subsistema que gerou o alerta."""
    WHATSAPP = "whatsapp"       # Conexao, criptografia
    CHIPS = "chips"             # Pool, health
    BUSINESS = "business"       # Funil, conversoes
    PIPELINE = "pipeline"       # Grupos pipeline
    HANDOFF = "handoff"         # Handoff humano
    SYSTEM = "system"           # Sistema geral
    BRIEFING = "briefing"       # Briefing
    CAMPAIGN = "campaign"       # Campanhas
    SHIFT = "shift"             # Plantoes


class AlertSeverity(Enum):
    """Severidade visual do alerta."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Notification:
    """Uma notificacao a ser enviada ao Slack."""
    id: str = field(default_factory=lambda: str(uuid4()))
    domain: AlertDomain = AlertDomain.SYSTEM
    category: AlertCategory = AlertCategory.ATTENTION
    alert_type: str = ""
    title: str = ""
    message: str = ""
    severity: AlertSeverity = AlertSeverity.WARNING
    metadata: Dict[str, Any] = field(default_factory=dict)
    correlation_key: Optional[str] = None
    source_file: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Serializa para persistencia."""
        return {
            "id": self.id,
            "domain": self.domain.value,
            "category": self.category.value,
            "alert_type": self.alert_type,
            "title": self.title,
            "message": self.message,
            "severity": self.severity.value,
            "metadata": self.metadata,
            "correlation_key": self.correlation_key,
            "source_file": self.source_file,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class NotificationResult:
    """Resultado de tentativa de envio de notificacao."""
    sent: bool
    notification_id: str
    suppressed_reason: Optional[str] = None  # "cooldown", "correlated", "digest_batched", "outside_window"
    digest_scheduled: bool = False

    def to_dict(self) -> dict:
        return {
            "sent": self.sent,
            "notification_id": self.notification_id,
            "suppressed_reason": self.suppressed_reason,
            "digest_scheduled": self.digest_scheduled,
        }


@dataclass
class DigestBatch:
    """Batch de notificacoes para digest."""
    notifications: List[Notification] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def count(self) -> int:
        return len(self.notifications)

    def add(self, notification: Notification) -> None:
        self.notifications.append(notification)

    def to_dict(self) -> dict:
        return {
            "notifications": [n.to_dict() for n in self.notifications],
            "created_at": self.created_at.isoformat(),
            "count": self.count,
        }
```

### 3. Arquivo: `exceptions.py`

```python
"""
Excecoes do sistema de notificacoes.

Sprint 41 - NotificationHub
"""


class NotificationError(Exception):
    """Erro base para notificacoes."""
    pass


class CooldownActiveError(NotificationError):
    """Notificacao esta em cooldown."""
    def __init__(self, alert_type: str, remaining_seconds: int):
        self.alert_type = alert_type
        self.remaining_seconds = remaining_seconds
        super().__init__(f"Alerta '{alert_type}' em cooldown por mais {remaining_seconds}s")


class CorrelatedAlertError(NotificationError):
    """Notificacao suprimida por correlacao."""
    def __init__(self, alert_type: str, correlated_with: str):
        self.alert_type = alert_type
        self.correlated_with = correlated_with
        super().__init__(f"Alerta '{alert_type}' suprimido por correlacao com '{correlated_with}'")


class OutsideOperatingWindowError(NotificationError):
    """Notificacao fora da janela operacional."""
    def __init__(self, current_hour: int, window_start: int, window_end: int):
        self.current_hour = current_hour
        self.window_start = window_start
        self.window_end = window_end
        super().__init__(f"Fora da janela operacional ({window_start}h-{window_end}h), hora atual: {current_hour}h")


class SlackWebhookError(NotificationError):
    """Erro ao enviar para Slack."""
    def __init__(self, status_code: int, response: str):
        self.status_code = status_code
        self.response = response
        super().__init__(f"Erro Slack: HTTP {status_code} - {response[:100]}")
```

### 4. Arquivo: `__init__.py`

```python
"""
NotificationHub - Sistema Centralizado de Notificacoes.

Sprint 41

Uso:
    from app.services.notifications import notification_hub, AlertDomain, AlertCategory

    await notification_hub.notify(
        domain=AlertDomain.WHATSAPP,
        alert_type="desconectado",
        title="WhatsApp Desconectado",
        message="Conexao perdida com Evolution API",
        category=AlertCategory.CRITICAL,
    )
"""

from .types import (
    AlertCategory,
    AlertDomain,
    AlertSeverity,
    Notification,
    NotificationResult,
    DigestBatch,
)

from .exceptions import (
    NotificationError,
    CooldownActiveError,
    CorrelatedAlertError,
    OutsideOperatingWindowError,
    SlackWebhookError,
)

__all__ = [
    # Enums
    "AlertCategory",
    "AlertDomain",
    "AlertSeverity",
    # Dataclasses
    "Notification",
    "NotificationResult",
    "DigestBatch",
    # Exceptions
    "NotificationError",
    "CooldownActiveError",
    "CorrelatedAlertError",
    "OutsideOperatingWindowError",
    "SlackWebhookError",
]
```

---

## Testes Obrigatorios

### Arquivo: `tests/services/notifications/__init__.py`

```python
"""Testes do modulo notifications."""
```

### Arquivo: `tests/services/notifications/test_types.py`

```python
"""Testes para tipos do NotificationHub."""
import pytest
from datetime import datetime, timezone
from uuid import UUID

from app.services.notifications import (
    AlertCategory,
    AlertDomain,
    AlertSeverity,
    Notification,
    NotificationResult,
    DigestBatch,
)


class TestAlertCategory:
    """Testes para enum AlertCategory."""

    def test_todos_valores_existem(self):
        """Verifica que todas as categorias existem."""
        assert AlertCategory.CRITICAL.value == "critical"
        assert AlertCategory.ATTENTION.value == "attention"
        assert AlertCategory.DIGEST.value == "digest"
        assert AlertCategory.INFO.value == "info"
        assert len(AlertCategory) == 4

    def test_category_eh_string_enum(self):
        """Categoria pode ser usada como string."""
        assert str(AlertCategory.CRITICAL.value) == "critical"


class TestAlertDomain:
    """Testes para enum AlertDomain."""

    def test_todos_dominios_existem(self):
        """Verifica que todos os dominios existem."""
        dominios = [
            "whatsapp", "chips", "business", "pipeline",
            "handoff", "system", "briefing", "campaign", "shift"
        ]
        assert len(AlertDomain) == len(dominios)
        for d in dominios:
            assert any(ad.value == d for ad in AlertDomain)


class TestAlertSeverity:
    """Testes para enum AlertSeverity."""

    def test_todas_severidades_existem(self):
        """Verifica que todas as severidades existem."""
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.ERROR.value == "error"
        assert AlertSeverity.CRITICAL.value == "critical"
        assert len(AlertSeverity) == 4


class TestNotification:
    """Testes para dataclass Notification."""

    def test_criacao_minima(self):
        """Cria notificacao com valores padrao."""
        notif = Notification()

        assert notif.id is not None
        assert UUID(notif.id)  # ID valido
        assert notif.domain == AlertDomain.SYSTEM
        assert notif.category == AlertCategory.ATTENTION
        assert notif.severity == AlertSeverity.WARNING
        assert notif.created_at is not None

    def test_criacao_completa(self):
        """Cria notificacao com todos os campos."""
        notif = Notification(
            domain=AlertDomain.WHATSAPP,
            category=AlertCategory.CRITICAL,
            alert_type="desconectado",
            title="WhatsApp Offline",
            message="Conexao perdida",
            severity=AlertSeverity.CRITICAL,
            metadata={"instance": "julia-prod"},
            correlation_key="whatsapp:desconectado",
            source_file="monitor_whatsapp.py",
        )

        assert notif.domain == AlertDomain.WHATSAPP
        assert notif.category == AlertCategory.CRITICAL
        assert notif.alert_type == "desconectado"
        assert notif.metadata["instance"] == "julia-prod"

    def test_to_dict(self):
        """Verifica serializacao."""
        notif = Notification(
            domain=AlertDomain.CHIPS,
            alert_type="pool_baixo",
            title="Pool Baixo",
            message="Menos de 3 chips ativos",
        )

        d = notif.to_dict()

        assert d["domain"] == "chips"
        assert d["alert_type"] == "pool_baixo"
        assert "created_at" in d
        assert d["id"] == notif.id

    def test_to_dict_serializacao_completa(self):
        """Verifica que to_dict serializa todos os campos."""
        notif = Notification(
            domain=AlertDomain.BUSINESS,
            category=AlertCategory.ATTENTION,
            alert_type="handoff_spike",
            title="Spike de Handoff",
            message="Muitos handoffs",
            severity=AlertSeverity.WARNING,
            metadata={"hospital_id": "hosp-123"},
            correlation_key="business:handoff",
            source_file="alerts.py",
        )

        d = notif.to_dict()

        assert d["domain"] == "business"
        assert d["category"] == "attention"
        assert d["alert_type"] == "handoff_spike"
        assert d["title"] == "Spike de Handoff"
        assert d["message"] == "Muitos handoffs"
        assert d["severity"] == "warning"
        assert d["metadata"]["hospital_id"] == "hosp-123"
        assert d["correlation_key"] == "business:handoff"
        assert d["source_file"] == "alerts.py"


class TestNotificationResult:
    """Testes para dataclass NotificationResult."""

    def test_resultado_enviado(self):
        """Resultado de notificacao enviada."""
        result = NotificationResult(
            sent=True,
            notification_id="abc123"
        )

        assert result.sent is True
        assert result.suppressed_reason is None
        assert result.digest_scheduled is False

    def test_resultado_suprimido_cooldown(self):
        """Resultado de notificacao em cooldown."""
        result = NotificationResult(
            sent=False,
            notification_id="abc123",
            suppressed_reason="cooldown"
        )

        assert result.sent is False
        assert result.suppressed_reason == "cooldown"

    def test_resultado_suprimido_correlacao(self):
        """Resultado de notificacao suprimida por correlacao."""
        result = NotificationResult(
            sent=False,
            notification_id="abc123",
            suppressed_reason="correlated"
        )

        assert result.sent is False
        assert result.suppressed_reason == "correlated"

    def test_resultado_digest(self):
        """Resultado de notificacao adicionada ao digest."""
        result = NotificationResult(
            sent=False,
            notification_id="abc123",
            digest_scheduled=True
        )

        assert result.sent is False
        assert result.digest_scheduled is True

    def test_to_dict(self):
        """Verifica serializacao do resultado."""
        result = NotificationResult(
            sent=True,
            notification_id="xyz789",
            suppressed_reason=None,
            digest_scheduled=False
        )

        d = result.to_dict()

        assert d["sent"] is True
        assert d["notification_id"] == "xyz789"
        assert d["suppressed_reason"] is None
        assert d["digest_scheduled"] is False


class TestDigestBatch:
    """Testes para dataclass DigestBatch."""

    def test_batch_vazio(self):
        """Cria batch vazio."""
        batch = DigestBatch()

        assert batch.count == 0
        assert len(batch.notifications) == 0

    def test_adicionar_notificacao(self):
        """Adiciona notificacao ao batch."""
        batch = DigestBatch()
        notif = Notification(alert_type="test")

        batch.add(notif)

        assert batch.count == 1
        assert batch.notifications[0] == notif

    def test_adicionar_multiplas_notificacoes(self):
        """Adiciona multiplas notificacoes ao batch."""
        batch = DigestBatch()
        batch.add(Notification(alert_type="test1"))
        batch.add(Notification(alert_type="test2"))
        batch.add(Notification(alert_type="test3"))

        assert batch.count == 3

    def test_to_dict(self):
        """Verifica serializacao do batch."""
        batch = DigestBatch()
        batch.add(Notification(alert_type="test1"))
        batch.add(Notification(alert_type="test2"))

        d = batch.to_dict()

        assert d["count"] == 2
        assert len(d["notifications"]) == 2
        assert "created_at" in d

    def test_count_property(self):
        """Verifica que count e uma property."""
        batch = DigestBatch()
        assert batch.count == 0

        batch.add(Notification())
        assert batch.count == 1

        batch.add(Notification())
        assert batch.count == 2
```

### Arquivo: `tests/services/notifications/test_exceptions.py`

```python
"""Testes para excecoes do NotificationHub."""
import pytest

from app.services.notifications import (
    NotificationError,
    CooldownActiveError,
    CorrelatedAlertError,
    OutsideOperatingWindowError,
    SlackWebhookError,
)


class TestNotificationError:
    """Testes para NotificationError base."""

    def test_heranca_exception(self):
        """NotificationError herda de Exception."""
        err = NotificationError("teste")
        assert isinstance(err, Exception)

    def test_mensagem_simples(self):
        """Mensagem simples funciona."""
        err = NotificationError("Erro generico")
        assert str(err) == "Erro generico"


class TestCooldownActiveError:
    """Testes para CooldownActiveError."""

    def test_mensagem_formatada(self):
        """Verifica mensagem de erro formatada."""
        err = CooldownActiveError("desconectado", 300)

        assert "desconectado" in str(err)
        assert "300" in str(err)
        assert err.alert_type == "desconectado"
        assert err.remaining_seconds == 300

    def test_heranca_notification_error(self):
        """Herda de NotificationError."""
        err = CooldownActiveError("test", 60)
        assert isinstance(err, NotificationError)

    def test_atributos_acessiveis(self):
        """Atributos sao acessiveis."""
        err = CooldownActiveError("pool_vazio", 900)
        assert err.alert_type == "pool_vazio"
        assert err.remaining_seconds == 900


class TestCorrelatedAlertError:
    """Testes para CorrelatedAlertError."""

    def test_mensagem_formatada(self):
        """Verifica mensagem de erro formatada."""
        err = CorrelatedAlertError("criptografia", "desconectado")

        assert "criptografia" in str(err)
        assert "desconectado" in str(err)
        assert err.alert_type == "criptografia"
        assert err.correlated_with == "desconectado"

    def test_heranca_notification_error(self):
        """Herda de NotificationError."""
        err = CorrelatedAlertError("test", "other")
        assert isinstance(err, NotificationError)


class TestOutsideOperatingWindowError:
    """Testes para OutsideOperatingWindowError."""

    def test_mensagem_formatada(self):
        """Verifica mensagem de erro formatada."""
        err = OutsideOperatingWindowError(23, 8, 20)

        assert "23" in str(err)
        assert "8" in str(err)
        assert "20" in str(err)
        assert err.current_hour == 23
        assert err.window_start == 8
        assert err.window_end == 20

    def test_heranca_notification_error(self):
        """Herda de NotificationError."""
        err = OutsideOperatingWindowError(5, 8, 20)
        assert isinstance(err, NotificationError)

    def test_diferentes_horarios(self):
        """Testa com diferentes horarios."""
        err = OutsideOperatingWindowError(3, 9, 18)
        assert err.current_hour == 3
        assert err.window_start == 9
        assert err.window_end == 18


class TestSlackWebhookError:
    """Testes para SlackWebhookError."""

    def test_mensagem_formatada(self):
        """Verifica mensagem de erro formatada."""
        err = SlackWebhookError(500, "Internal Server Error")

        assert "500" in str(err)
        assert "Internal Server Error" in str(err)
        assert err.status_code == 500
        assert err.response == "Internal Server Error"

    def test_heranca_notification_error(self):
        """Herda de NotificationError."""
        err = SlackWebhookError(400, "Bad Request")
        assert isinstance(err, NotificationError)

    def test_resposta_longa_truncada(self):
        """Resposta longa e truncada na mensagem."""
        resposta_longa = "x" * 200
        err = SlackWebhookError(500, resposta_longa)

        # Mensagem deve ter no maximo 100 chars da resposta
        assert len(str(err)) < len(resposta_longa) + 50

    def test_diferentes_status_codes(self):
        """Testa com diferentes status codes."""
        err_400 = SlackWebhookError(400, "Bad Request")
        err_401 = SlackWebhookError(401, "Unauthorized")
        err_429 = SlackWebhookError(429, "Too Many Requests")
        err_503 = SlackWebhookError(503, "Service Unavailable")

        assert err_400.status_code == 400
        assert err_401.status_code == 401
        assert err_429.status_code == 429
        assert err_503.status_code == 503
```

---

## Checklist de Conclusao

### Implementacao
- [ ] Criar diretorio `app/services/notifications/`
- [ ] Criar arquivo `types.py` com todos os tipos
- [ ] Criar arquivo `exceptions.py` com excecoes
- [ ] Criar arquivo `__init__.py` com exports

### Testes
- [ ] Criar diretorio `tests/services/notifications/`
- [ ] Criar `tests/services/notifications/__init__.py`
- [ ] Criar `tests/services/notifications/test_types.py`
- [ ] Criar `tests/services/notifications/test_exceptions.py`
- [ ] Rodar `uv run pytest tests/services/notifications/ -v`
- [ ] 100% dos testes passando

### Qualidade
- [ ] Rodar `uv run mypy app/services/notifications/`
- [ ] Zero erros de tipo
- [ ] Rodar `uv run ruff check app/services/notifications/`
- [ ] Zero erros de lint

---

## Definition of Done (E01)

Este epico esta **COMPLETO** quando:

1. [ ] Estrutura de diretorios criada
2. [ ] Todos os tipos definidos em `types.py`
3. [ ] Todas as excecoes definidas em `exceptions.py`
4. [ ] Exports em `__init__.py`
5. [ ] 100% dos testes passando (0 skipped)
6. [ ] Zero erros de mypy
7. [ ] Zero erros de ruff
