# E07 - NotificationHub

**Epico:** E07
**Nome:** NotificationHub (Orquestrador Principal)
**Dependencias:** E01, E02, E03, E04, E05, E06
**Prioridade:** Critica

---

## Objetivo

Implementar o hub central de notificacoes que orquestra todos os componentes: cooldown, correlacao, digest e formatacao.

---

## Contexto

Este e o componente principal da Sprint 41. Ele:
1. Recebe todas as notificacoes do sistema
2. Aplica cooldown unificado
3. Verifica correlacao entre alertas
4. Roteia para digest ou envio imediato
5. Formata e envia via Slack

Substitui as 36 chamadas diretas a `enviar_slack()` espalhadas pelo codigo.

---

## Fluxo de Processamento

```
notify()
  │
  ├─► Validar notificacao
  │
  ├─► Verificar cooldown ──► Em cooldown? ──► return (suprimido)
  │
  ├─► Verificar correlacao ──► Correlacionado? ──► return (suprimido)
  │
  ├─► Verificar categoria
  │     │
  │     ├─► CRITICAL/ATTENTION ──► Enviar imediatamente
  │     │
  │     └─► DIGEST/INFO ──► Adicionar ao digest
  │
  ├─► Formatar mensagem
  │
  ├─► Enviar ao Slack
  │
  └─► Registrar cooldown/correlacao
```

---

## Entregaveis

### Arquivo: `hub.py`

```python
"""
NotificationHub - Hub central de notificacoes.

Sprint 41

Orquestra:
- CooldownManager: Evita spam
- CorrelationManager: Suprime alertas relacionados
- DigestManager: Agrupa notificacoes de baixa prioridade
- SlackFormatter: Formata mensagens

Uso:
    from app.services.notifications import notification_hub

    await notification_hub.notify(
        domain=AlertDomain.WHATSAPP,
        category=AlertCategory.CRITICAL,
        alert_type="desconectado",
        title="WhatsApp Offline",
        message="Conexao perdida",
    )
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from app.services.slack import enviar_slack

from .types import (
    Notification,
    NotificationResult,
    AlertCategory,
    AlertDomain,
    AlertSeverity,
    DigestBatch,
)
from .config import (
    CATEGORY_CONFIG,
    get_category_for_alert_type,
    get_cooldown_minutes,
    get_domain_for_alert_type,
    is_within_operating_window,
)
from .cooldown import cooldown_manager
from .correlation import correlation_manager
from .digest import digest_manager
from .formatters import slack_formatter

logger = logging.getLogger(__name__)


class NotificationHub:
    """
    Hub central para todas as notificacoes do sistema.

    Responsabilidades:
    - Roteamento por categoria
    - Aplicacao de cooldown
    - Deteccao de correlacao
    - Agrupamento em digest
    - Formatacao e envio

    Todos os componentes sao injetados para facilitar testes.
    """

    def __init__(
        self,
        cooldown=None,
        correlation=None,
        digest=None,
        formatter=None,
        sender=None,
    ):
        """
        Inicializa o hub com componentes.

        Args:
            cooldown: CooldownManager (usa singleton se None)
            correlation: CorrelationManager (usa singleton se None)
            digest: DigestManager (usa singleton se None)
            formatter: SlackFormatter (usa singleton se None)
            sender: Funcao para enviar ao Slack (usa enviar_slack se None)
        """
        self._cooldown = cooldown or cooldown_manager
        self._correlation = correlation or correlation_manager
        self._digest = digest or digest_manager
        self._formatter = formatter or slack_formatter
        self._sender = sender or enviar_slack

    async def notify(
        self,
        domain: AlertDomain,
        category: AlertCategory,
        alert_type: str,
        title: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        severity: AlertSeverity = AlertSeverity.MEDIUM,
        source: Optional[str] = None,
        actions: Optional[list] = None,
        force: bool = False,
    ) -> NotificationResult:
        """
        Envia notificacao pelo hub.

        Args:
            domain: Dominio do alerta (WHATSAPP, FUNNEL, etc)
            category: Categoria (CRITICAL, ATTENTION, DIGEST, INFO)
            alert_type: Tipo especifico (desconectado, conversion_drop, etc)
            title: Titulo da notificacao
            message: Mensagem detalhada
            metadata: Dados adicionais (opcional)
            severity: Severidade (HIGH, MEDIUM, LOW)
            source: Fonte do alerta (opcional)
            actions: Botoes de acao (opcional)
            force: Ignorar cooldown e correlacao

        Returns:
            NotificationResult com status do envio
        """
        # Criar notificacao
        notification = Notification(
            domain=domain,
            category=category,
            alert_type=alert_type,
            title=title,
            message=message,
            metadata=metadata or {},
            severity=severity,
            source=source,
            actions=actions or [],
        )

        return await self._process(notification, force=force)

    async def notify_from_dict(
        self,
        data: Dict[str, Any],
        force: bool = False,
    ) -> NotificationResult:
        """
        Envia notificacao a partir de dict.

        Util para migracao de callers existentes.

        Args:
            data: Dict com campos da notificacao
            force: Ignorar cooldown e correlacao

        Returns:
            NotificationResult
        """
        # Inferir categoria e dominio se nao fornecidos
        alert_type = data.get("alert_type", data.get("tipo", "unknown"))

        domain = data.get("domain")
        if domain is None:
            domain = get_domain_for_alert_type(alert_type)
        elif isinstance(domain, str):
            domain = AlertDomain(domain)

        category = data.get("category")
        if category is None:
            category = get_category_for_alert_type(alert_type)
        elif isinstance(category, str):
            category = AlertCategory(category)

        notification = Notification(
            domain=domain,
            category=category,
            alert_type=alert_type,
            title=data.get("title", data.get("titulo", alert_type)),
            message=data.get("message", data.get("mensagem", "")),
            metadata=data.get("metadata", data.get("contexto", {})),
            severity=AlertSeverity(data.get("severity", "medium")),
            source=data.get("source", data.get("fonte")),
            actions=data.get("actions", []),
        )

        return await self._process(notification, force=force)

    async def _process(
        self,
        notification: Notification,
        force: bool = False,
    ) -> NotificationResult:
        """
        Processa notificacao pelo pipeline.

        Args:
            notification: Notificacao a processar
            force: Ignorar cooldown e correlacao

        Returns:
            NotificationResult
        """
        logger.debug(
            f"Processando notificacao: {notification.alert_type} "
            f"(categoria: {notification.category.value})"
        )

        # 1. Verificar janela operacional para ATTENTION
        if not force and notification.category == AlertCategory.ATTENTION:
            if not is_within_operating_window():
                logger.info(
                    f"Notificacao {notification.alert_type} fora da janela operacional"
                )
                return NotificationResult(
                    notification_id=notification.id,
                    sent=False,
                    suppressed=True,
                    reason="outside_operating_window",
                )

        # 2. Verificar cooldown
        if not force:
            is_cooling = await self._cooldown.is_in_cooldown(notification)
            if is_cooling:
                remaining = await self._cooldown.get_remaining_seconds(notification)
                logger.info(
                    f"Notificacao {notification.alert_type} em cooldown "
                    f"({remaining}s restantes)"
                )
                return NotificationResult(
                    notification_id=notification.id,
                    sent=False,
                    suppressed=True,
                    reason="cooldown",
                    cooldown_remaining=remaining,
                )

        # 3. Verificar correlacao
        if not force:
            correlated_with = await self._correlation.check_correlation(notification)
            if correlated_with:
                logger.info(
                    f"Notificacao {notification.alert_type} suprimida "
                    f"por correlacao com {correlated_with}"
                )
                return NotificationResult(
                    notification_id=notification.id,
                    sent=False,
                    suppressed=True,
                    reason="correlation",
                    correlated_with=correlated_with,
                )

        # 4. Rotear por categoria
        if notification.category in (AlertCategory.CRITICAL, AlertCategory.ATTENTION):
            # Envio imediato
            result = await self._send_immediate(notification)
        else:
            # Adicionar ao digest
            result = await self._add_to_digest(notification)

        # 5. Registrar cooldown e correlacao se enviou
        if result.sent:
            await self._cooldown.set_cooldown(notification)
            await self._correlation.record_sent(notification)

        return result

    async def _send_immediate(self, notification: Notification) -> NotificationResult:
        """
        Envia notificacao imediatamente.

        Args:
            notification: Notificacao a enviar

        Returns:
            NotificationResult
        """
        try:
            # Formatar
            formatted = self._formatter.format(notification)

            # Enviar
            success = await self._sender(formatted)

            if success:
                logger.info(
                    f"Notificacao enviada: {notification.alert_type} "
                    f"(id: {notification.id[:8]})"
                )
                return NotificationResult(
                    notification_id=notification.id,
                    sent=True,
                    suppressed=False,
                )
            else:
                logger.error(f"Falha ao enviar notificacao: {notification.alert_type}")
                return NotificationResult(
                    notification_id=notification.id,
                    sent=False,
                    suppressed=False,
                    reason="send_failed",
                )

        except Exception as e:
            logger.exception(f"Erro ao enviar notificacao: {e}")
            return NotificationResult(
                notification_id=notification.id,
                sent=False,
                suppressed=False,
                reason=f"error: {str(e)}",
            )

    async def _add_to_digest(self, notification: Notification) -> NotificationResult:
        """
        Adiciona notificacao ao digest.

        Args:
            notification: Notificacao a adicionar

        Returns:
            NotificationResult
        """
        try:
            await self._digest.add(notification)

            logger.debug(
                f"Notificacao adicionada ao digest: {notification.alert_type}"
            )

            return NotificationResult(
                notification_id=notification.id,
                sent=False,  # Sera enviado no flush
                suppressed=False,
                reason="queued_for_digest",
                digest_queued=True,
            )

        except Exception as e:
            logger.exception(f"Erro ao adicionar ao digest: {e}")
            return NotificationResult(
                notification_id=notification.id,
                sent=False,
                suppressed=False,
                reason=f"digest_error: {str(e)}",
            )

    async def flush_digest(self) -> NotificationResult:
        """
        Processa e envia digest pendente.

        Chamado pelo scheduler periodicamente.

        Returns:
            NotificationResult com contagem
        """
        try:
            batch = await self._digest.get_pending()

            if batch.count == 0:
                logger.debug("Nenhuma notificacao pendente no digest")
                return NotificationResult(
                    notification_id="digest_flush",
                    sent=False,
                    suppressed=False,
                    reason="empty_digest",
                )

            # Formatar batch
            formatted = self._formatter.format_digest(batch)

            # Enviar
            success = await self._sender(formatted)

            if success:
                # Limpar digest
                await self._digest.clear()

                logger.info(f"Digest enviado: {batch.count} notificacoes")
                return NotificationResult(
                    notification_id="digest_flush",
                    sent=True,
                    suppressed=False,
                    metadata={"count": batch.count},
                )
            else:
                logger.error("Falha ao enviar digest")
                return NotificationResult(
                    notification_id="digest_flush",
                    sent=False,
                    suppressed=False,
                    reason="send_failed",
                )

        except Exception as e:
            logger.exception(f"Erro ao processar digest: {e}")
            return NotificationResult(
                notification_id="digest_flush",
                sent=False,
                suppressed=False,
                reason=f"error: {str(e)}",
            )

    async def get_status(self) -> Dict[str, Any]:
        """
        Retorna status do hub.

        Returns:
            Dict com metricas
        """
        digest_count = await self._digest.count()

        return {
            "digest_pending": digest_count,
            "operating_window": is_within_operating_window(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# Singleton
notification_hub = NotificationHub()


# Funcao de conveniencia para retrocompatibilidade
async def notify(
    alert_type: str,
    title: str,
    message: str,
    **kwargs,
) -> NotificationResult:
    """
    Funcao de conveniencia para enviar notificacao.

    Infere domain e category automaticamente a partir do alert_type.

    Args:
        alert_type: Tipo do alerta
        title: Titulo
        message: Mensagem
        **kwargs: Argumentos adicionais

    Returns:
        NotificationResult
    """
    domain = kwargs.pop("domain", None) or get_domain_for_alert_type(alert_type)
    category = kwargs.pop("category", None) or get_category_for_alert_type(alert_type)

    return await notification_hub.notify(
        domain=domain,
        category=category,
        alert_type=alert_type,
        title=title,
        message=message,
        **kwargs,
    )
```

---

## Testes Obrigatorios

### Arquivo: `tests/services/notifications/test_hub.py`

```python
"""Testes para NotificationHub."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.notifications import (
    Notification,
    NotificationResult,
    AlertCategory,
    AlertDomain,
    AlertSeverity,
    DigestBatch,
)
from app.services.notifications.hub import (
    NotificationHub,
    notification_hub,
    notify,
)


@pytest.fixture
def mock_cooldown():
    """Mock para CooldownManager."""
    mock = MagicMock()
    mock.is_in_cooldown = AsyncMock(return_value=False)
    mock.set_cooldown = AsyncMock()
    mock.get_remaining_seconds = AsyncMock(return_value=0)
    return mock


@pytest.fixture
def mock_correlation():
    """Mock para CorrelationManager."""
    mock = MagicMock()
    mock.check_correlation = AsyncMock(return_value=None)
    mock.record_sent = AsyncMock()
    return mock


@pytest.fixture
def mock_digest():
    """Mock para DigestManager."""
    mock = MagicMock()
    mock.add = AsyncMock()
    mock.get_pending = AsyncMock(return_value=DigestBatch(
        notifications=[],
        window_start=datetime.now(timezone.utc),
        window_end=datetime.now(timezone.utc),
    ))
    mock.clear = AsyncMock()
    mock.count = AsyncMock(return_value=0)
    return mock


@pytest.fixture
def mock_formatter():
    """Mock para SlackFormatter."""
    mock = MagicMock()
    mock.format = MagicMock(return_value={"text": "test", "blocks": []})
    mock.format_digest = MagicMock(return_value={"text": "digest", "blocks": []})
    return mock


@pytest.fixture
def mock_sender():
    """Mock para funcao de envio."""
    return AsyncMock(return_value=True)


@pytest.fixture
def hub(mock_cooldown, mock_correlation, mock_digest, mock_formatter, mock_sender):
    """Hub com mocks injetados."""
    return NotificationHub(
        cooldown=mock_cooldown,
        correlation=mock_correlation,
        digest=mock_digest,
        formatter=mock_formatter,
        sender=mock_sender,
    )


class TestNotify:
    """Testes para notify()."""

    @pytest.mark.asyncio
    async def test_envia_critical_imediatamente(self, hub, mock_sender):
        """Notificacao CRITICAL e enviada imediatamente."""
        result = await hub.notify(
            domain=AlertDomain.WHATSAPP,
            category=AlertCategory.CRITICAL,
            alert_type="desconectado",
            title="WhatsApp Offline",
            message="Conexao perdida",
        )

        assert result.sent is True
        mock_sender.assert_called_once()

    @pytest.mark.asyncio
    async def test_envia_attention_imediatamente(self, hub, mock_sender):
        """Notificacao ATTENTION e enviada imediatamente."""
        with patch("app.services.notifications.hub.is_within_operating_window", return_value=True):
            result = await hub.notify(
                domain=AlertDomain.FUNNEL,
                category=AlertCategory.ATTENTION,
                alert_type="conversion_drop",
                title="Queda Conversao",
                message="Taxa caiu",
            )

        assert result.sent is True
        mock_sender.assert_called_once()

    @pytest.mark.asyncio
    async def test_digest_vai_para_fila(self, hub, mock_digest, mock_sender):
        """Notificacao DIGEST vai para fila."""
        result = await hub.notify(
            domain=AlertDomain.SHIFT,
            category=AlertCategory.DIGEST,
            alert_type="plantao_reservado",
            title="Plantao Reservado",
            message="Dr Silva reservou",
        )

        assert result.sent is False
        assert result.digest_queued is True
        mock_digest.add.assert_called_once()
        mock_sender.assert_not_called()

    @pytest.mark.asyncio
    async def test_info_vai_para_fila(self, hub, mock_digest, mock_sender):
        """Notificacao INFO vai para fila."""
        result = await hub.notify(
            domain=AlertDomain.SYSTEM,
            category=AlertCategory.INFO,
            alert_type="backup_ok",
            title="Backup OK",
            message="Backup concluido",
        )

        assert result.sent is False
        assert result.digest_queued is True
        mock_digest.add.assert_called_once()


class TestCooldown:
    """Testes para cooldown."""

    @pytest.mark.asyncio
    async def test_suprimido_por_cooldown(self, hub, mock_cooldown, mock_sender):
        """Notificacao em cooldown e suprimida."""
        mock_cooldown.is_in_cooldown.return_value = True
        mock_cooldown.get_remaining_seconds.return_value = 300

        result = await hub.notify(
            domain=AlertDomain.WHATSAPP,
            category=AlertCategory.CRITICAL,
            alert_type="desconectado",
            title="WhatsApp Offline",
            message="Conexao perdida",
        )

        assert result.sent is False
        assert result.suppressed is True
        assert result.reason == "cooldown"
        assert result.cooldown_remaining == 300
        mock_sender.assert_not_called()

    @pytest.mark.asyncio
    async def test_force_ignora_cooldown(self, hub, mock_cooldown, mock_sender):
        """force=True ignora cooldown."""
        mock_cooldown.is_in_cooldown.return_value = True

        result = await hub.notify(
            domain=AlertDomain.WHATSAPP,
            category=AlertCategory.CRITICAL,
            alert_type="desconectado",
            title="WhatsApp Offline",
            message="Conexao perdida",
            force=True,
        )

        assert result.sent is True
        mock_cooldown.is_in_cooldown.assert_not_called()

    @pytest.mark.asyncio
    async def test_registra_cooldown_apos_envio(self, hub, mock_cooldown):
        """Registra cooldown apos envio bem-sucedido."""
        result = await hub.notify(
            domain=AlertDomain.WHATSAPP,
            category=AlertCategory.CRITICAL,
            alert_type="desconectado",
            title="WhatsApp Offline",
            message="Conexao perdida",
        )

        assert result.sent is True
        mock_cooldown.set_cooldown.assert_called_once()


class TestCorrelation:
    """Testes para correlacao."""

    @pytest.mark.asyncio
    async def test_suprimido_por_correlacao(self, hub, mock_correlation, mock_sender):
        """Notificacao correlacionada e suprimida."""
        mock_correlation.check_correlation.return_value = "desconectado"

        result = await hub.notify(
            domain=AlertDomain.WHATSAPP,
            category=AlertCategory.ATTENTION,
            alert_type="criptografia",
            title="Erro Criptografia",
            message="PreKeyError",
        )

        assert result.sent is False
        assert result.suppressed is True
        assert result.reason == "correlation"
        assert result.correlated_with == "desconectado"
        mock_sender.assert_not_called()

    @pytest.mark.asyncio
    async def test_force_ignora_correlacao(self, hub, mock_correlation, mock_sender):
        """force=True ignora correlacao."""
        mock_correlation.check_correlation.return_value = "desconectado"

        result = await hub.notify(
            domain=AlertDomain.WHATSAPP,
            category=AlertCategory.CRITICAL,
            alert_type="criptografia",
            title="Erro Criptografia",
            message="PreKeyError",
            force=True,
        )

        assert result.sent is True
        mock_correlation.check_correlation.assert_not_called()

    @pytest.mark.asyncio
    async def test_registra_correlacao_apos_envio(self, hub, mock_correlation):
        """Registra correlacao apos envio bem-sucedido."""
        result = await hub.notify(
            domain=AlertDomain.WHATSAPP,
            category=AlertCategory.CRITICAL,
            alert_type="desconectado",
            title="WhatsApp Offline",
            message="Conexao perdida",
        )

        assert result.sent is True
        mock_correlation.record_sent.assert_called_once()


class TestOperatingWindow:
    """Testes para janela operacional."""

    @pytest.mark.asyncio
    async def test_attention_fora_da_janela(self, hub, mock_sender):
        """ATTENTION fora da janela e suprimido."""
        with patch("app.services.notifications.hub.is_within_operating_window", return_value=False):
            result = await hub.notify(
                domain=AlertDomain.FUNNEL,
                category=AlertCategory.ATTENTION,
                alert_type="conversion_drop",
                title="Queda Conversao",
                message="Taxa caiu",
            )

        assert result.sent is False
        assert result.suppressed is True
        assert result.reason == "outside_operating_window"
        mock_sender.assert_not_called()

    @pytest.mark.asyncio
    async def test_critical_ignora_janela(self, hub, mock_sender):
        """CRITICAL ignora janela operacional."""
        with patch("app.services.notifications.hub.is_within_operating_window", return_value=False):
            result = await hub.notify(
                domain=AlertDomain.WHATSAPP,
                category=AlertCategory.CRITICAL,
                alert_type="desconectado",
                title="WhatsApp Offline",
                message="Conexao perdida",
            )

        assert result.sent is True


class TestNotifyFromDict:
    """Testes para notify_from_dict()."""

    @pytest.mark.asyncio
    async def test_infere_categoria_e_dominio(self, hub):
        """Infere categoria e dominio do alert_type."""
        with patch.object(hub, "_process", new_callable=AsyncMock) as mock_process:
            mock_process.return_value = NotificationResult(
                notification_id="test",
                sent=True,
                suppressed=False,
            )

            await hub.notify_from_dict({
                "alert_type": "desconectado",
                "title": "WhatsApp Offline",
                "message": "Conexao perdida",
            })

            call_args = mock_process.call_args[0][0]
            assert call_args.alert_type == "desconectado"
            # Categoria e dominio inferidos de config

    @pytest.mark.asyncio
    async def test_aceita_campos_legados(self, hub):
        """Aceita campos com nomes legados (tipo, titulo, mensagem)."""
        with patch.object(hub, "_process", new_callable=AsyncMock) as mock_process:
            mock_process.return_value = NotificationResult(
                notification_id="test",
                sent=True,
                suppressed=False,
            )

            await hub.notify_from_dict({
                "tipo": "handoff_spike",
                "titulo": "Spike de Handoff",
                "mensagem": "Muitos handoffs",
                "contexto": {"taxa": 15},
            })

            call_args = mock_process.call_args[0][0]
            assert call_args.alert_type == "handoff_spike"
            assert call_args.title == "Spike de Handoff"
            assert call_args.metadata == {"taxa": 15}


class TestFlushDigest:
    """Testes para flush_digest()."""

    @pytest.mark.asyncio
    async def test_envia_digest_pendente(self, hub, mock_digest, mock_sender, mock_formatter):
        """Envia notificacoes pendentes do digest."""
        mock_digest.get_pending.return_value = DigestBatch(
            notifications=[
                Notification(
                    domain=AlertDomain.SHIFT,
                    category=AlertCategory.DIGEST,
                    alert_type="plantao_reservado",
                    title="Plantao 1",
                    message="Msg",
                ),
                Notification(
                    domain=AlertDomain.SHIFT,
                    category=AlertCategory.DIGEST,
                    alert_type="plantao_reservado",
                    title="Plantao 2",
                    message="Msg",
                ),
            ],
            window_start=datetime.now(timezone.utc),
            window_end=datetime.now(timezone.utc),
        )

        result = await hub.flush_digest()

        assert result.sent is True
        mock_formatter.format_digest.assert_called_once()
        mock_sender.assert_called_once()
        mock_digest.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_nao_envia_digest_vazio(self, hub, mock_digest, mock_sender):
        """Nao envia se digest esta vazio."""
        mock_digest.get_pending.return_value = DigestBatch(
            notifications=[],
            window_start=datetime.now(timezone.utc),
            window_end=datetime.now(timezone.utc),
        )

        result = await hub.flush_digest()

        assert result.sent is False
        assert result.reason == "empty_digest"
        mock_sender.assert_not_called()


class TestGetStatus:
    """Testes para get_status()."""

    @pytest.mark.asyncio
    async def test_retorna_status(self, hub, mock_digest):
        """Retorna status do hub."""
        mock_digest.count.return_value = 5

        with patch("app.services.notifications.hub.is_within_operating_window", return_value=True):
            status = await hub.get_status()

        assert status["digest_pending"] == 5
        assert status["operating_window"] is True
        assert "timestamp" in status


class TestErrorHandling:
    """Testes para tratamento de erros."""

    @pytest.mark.asyncio
    async def test_erro_no_envio(self, hub, mock_sender):
        """Trata erro no envio graciosamente."""
        mock_sender.side_effect = Exception("Connection failed")

        result = await hub.notify(
            domain=AlertDomain.WHATSAPP,
            category=AlertCategory.CRITICAL,
            alert_type="desconectado",
            title="WhatsApp Offline",
            message="Conexao perdida",
        )

        assert result.sent is False
        assert "error" in result.reason

    @pytest.mark.asyncio
    async def test_erro_no_digest(self, hub, mock_digest):
        """Trata erro ao adicionar ao digest."""
        mock_digest.add.side_effect = Exception("Redis error")

        result = await hub.notify(
            domain=AlertDomain.SHIFT,
            category=AlertCategory.DIGEST,
            alert_type="plantao_reservado",
            title="Plantao",
            message="Msg",
        )

        assert result.sent is False
        assert "digest_error" in result.reason


class TestConvenienceFunction:
    """Testes para funcao notify()."""

    @pytest.mark.asyncio
    async def test_notify_infere_automaticamente(self):
        """Funcao notify() infere domain e category."""
        with patch.object(notification_hub, "notify", new_callable=AsyncMock) as mock:
            mock.return_value = NotificationResult(
                notification_id="test",
                sent=True,
                suppressed=False,
            )

            await notify(
                alert_type="desconectado",
                title="WhatsApp Offline",
                message="Conexao perdida",
            )

            mock.assert_called_once()


class TestSingleton:
    """Testes para singleton."""

    def test_singleton_exportado(self):
        """notification_hub e um singleton."""
        assert notification_hub is not None
        assert isinstance(notification_hub, NotificationHub)
```

---

## Checklist de Conclusao

### Implementacao
- [ ] Criar arquivo `hub.py`
- [ ] Implementar `NotificationHub`
- [ ] Implementar `notify()`
- [ ] Implementar `notify_from_dict()`
- [ ] Implementar `_process()`
- [ ] Implementar `_send_immediate()`
- [ ] Implementar `_add_to_digest()`
- [ ] Implementar `flush_digest()`
- [ ] Implementar `get_status()`
- [ ] Funcao de conveniencia `notify()`
- [ ] Exportar singleton
- [ ] Atualizar `__init__.py`

### Testes
- [ ] Criar `tests/services/notifications/test_hub.py`
- [ ] Testar envio por categoria
- [ ] Testar cooldown
- [ ] Testar correlacao
- [ ] Testar janela operacional
- [ ] Testar notify_from_dict
- [ ] Testar flush_digest
- [ ] Testar tratamento de erros
- [ ] 100% dos testes passando

### Qualidade
- [ ] Zero erros de mypy
- [ ] Zero erros de ruff

---

## Definition of Done (E07)

1. [ ] `NotificationHub` implementado
2. [ ] Singleton exportado
3. [ ] Pipeline completo funcionando (cooldown → correlacao → roteamento → envio)
4. [ ] Flush de digest funcionando
5. [ ] Funcao de conveniencia `notify()` funcionando
6. [ ] 100% dos testes passando (0 skipped)
7. [ ] Zero erros de tipo/lint
