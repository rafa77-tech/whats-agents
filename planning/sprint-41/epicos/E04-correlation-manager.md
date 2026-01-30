# E04 - CorrelationManager

**Epico:** E04
**Nome:** CorrelationManager
**Dependencias:** E01, E02
**Prioridade:** Alta

---

## Objetivo

Implementar deteccao de alertas correlacionados. Quando um alerta de um cluster e enviado, os alertas relacionados sao suprimidos na mesma janela de tempo.

---

## Contexto

Atualmente, quando o WhatsApp desconecta, podem ser disparados 4+ alertas:
- `desconectado` (monitor_whatsapp.py)
- `sem_respostas` (alertas.py)
- `criptografia` (monitor_whatsapp.py)
- `conversion_drop` (business_events/alerts.py)

Com a correlacao, apenas o primeiro (mais prioritario) sera enviado, os demais serao suprimidos.

---

## Entregaveis

### Arquivo: `correlation.py`

```python
"""
CorrelationManager - Deteccao e supressao de alertas correlacionados.

Sprint 41

Clusters de correlacao:
- whatsapp: desconectado, criptografia, evolution_down, sem_respostas
- chips: pool_vazio, pool_baixo_prospeccao, pool_baixo_followup, trust_critico
- funnel: handoff_spike, recusa_spike, conversion_drop
- performance: performance_critica, tempo_resposta_alto
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from app.services.redis import cache_get_json, cache_set_json

from .types import Notification
from .config import CORRELATION_CLUSTERS, REDIS_KEYS, get_cluster_for_alert

logger = logging.getLogger(__name__)


class CorrelationManager:
    """
    Gerencia correlacao entre alertas.

    Funcionalidades:
    - Detecta se alerta pertence a um cluster
    - Verifica se ja foi enviado alerta do mesmo cluster na janela
    - Registra envio para supressao futura

    Chave Redis: notif:corr:{cluster}:{window_key}
    """

    def __init__(self):
        self._prefix = REDIS_KEYS["correlation_prefix"]

    def _get_window_key(self, cluster_name: str) -> str:
        """
        Gera chave de janela baseada no tempo.

        Args:
            cluster_name: Nome do cluster

        Returns:
            Chave de janela (hora atual truncada)
        """
        window_minutes = CORRELATION_CLUSTERS[cluster_name]["window_minutes"]
        now = datetime.now(timezone.utc)

        # Truncar para janela
        # Ex: window=30min, 14:45 -> 14:30
        minutes = (now.minute // window_minutes) * window_minutes
        window_time = now.replace(minute=minutes, second=0, microsecond=0)

        return window_time.strftime("%Y%m%d%H%M")

    def _make_key(self, cluster_name: str) -> str:
        """
        Gera chave Redis para correlacao.

        Args:
            cluster_name: Nome do cluster

        Returns:
            Chave Redis
        """
        window_key = self._get_window_key(cluster_name)
        return f"{self._prefix}{cluster_name}:{window_key}"

    def get_cluster(self, notification: Notification) -> Optional[str]:
        """
        Retorna cluster ao qual o alerta pertence.

        Args:
            notification: Notificacao

        Returns:
            Nome do cluster ou None
        """
        return get_cluster_for_alert(notification.alert_type)

    async def check_correlation(self, notification: Notification) -> Optional[str]:
        """
        Verifica se alerta esta correlacionado com outro ja enviado.

        Args:
            notification: Notificacao a verificar

        Returns:
            alert_type do alerta correlacionado, ou None se pode enviar
        """
        cluster_name = self.get_cluster(notification)
        if not cluster_name:
            return None  # Nao pertence a nenhum cluster

        key = self._make_key(cluster_name)

        try:
            data = await cache_get_json(key)
            if not data:
                return None  # Nenhum alerta do cluster enviado nesta janela

            # Verificar se o proprio tipo ja foi enviado
            if notification.alert_type == data.get("alert_type"):
                return None  # Mesmo tipo pode ser reenviado (cooldown cuida disso)

            # Verificar prioridade
            cluster_config = CORRELATION_CLUSTERS[cluster_name]
            priority_order = cluster_config.get("priority_order", [])

            if priority_order:
                sent_type = data.get("alert_type")
                current_type = notification.alert_type

                # Se o enviado tem maior prioridade, suprimir o atual
                if sent_type in priority_order and current_type in priority_order:
                    sent_priority = priority_order.index(sent_type)
                    current_priority = priority_order.index(current_type)

                    if sent_priority < current_priority:
                        logger.info(
                            f"Alerta {current_type} suprimido por correlacao "
                            f"com {sent_type} (cluster: {cluster_name})"
                        )
                        return sent_type

            # Alerta diferente do cluster ja foi enviado, suprimir
            return data.get("alert_type")

        except Exception as e:
            logger.warning(f"Erro ao verificar correlacao: {e}")
            return None  # Fail open

    async def record_sent(self, notification: Notification) -> None:
        """
        Registra que alerta foi enviado para correlacao.

        Args:
            notification: Notificacao enviada
        """
        cluster_name = self.get_cluster(notification)
        if not cluster_name:
            return  # Nao pertence a nenhum cluster

        key = self._make_key(cluster_name)
        window_minutes = CORRELATION_CLUSTERS[cluster_name]["window_minutes"]
        ttl = window_minutes * 60 + 60  # Janela + 1 min margem

        try:
            await cache_set_json(key, {
                "alert_type": notification.alert_type,
                "notification_id": notification.id,
                "cluster": cluster_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }, ttl=ttl)

            logger.debug(
                f"Correlacao registrada: {notification.alert_type} "
                f"(cluster: {cluster_name}, janela: {window_minutes}min)"
            )

        except Exception as e:
            logger.error(f"Erro ao registrar correlacao: {e}")

    async def get_cluster_status(self, cluster_name: str) -> dict:
        """
        Retorna status do cluster.

        Args:
            cluster_name: Nome do cluster

        Returns:
            Dict com informacoes do cluster
        """
        if cluster_name not in CORRELATION_CLUSTERS:
            return {"error": "Cluster nao encontrado"}

        key = self._make_key(cluster_name)

        try:
            data = await cache_get_json(key)

            return {
                "cluster": cluster_name,
                "key": key,
                "has_sent_alert": data is not None,
                "sent_alert_type": data.get("alert_type") if data else None,
                "window_minutes": CORRELATION_CLUSTERS[cluster_name]["window_minutes"],
                "types_in_cluster": CORRELATION_CLUSTERS[cluster_name]["types"],
            }
        except Exception as e:
            return {"error": str(e)}

    async def clear_cluster(self, cluster_name: str) -> bool:
        """
        Limpa registro de correlacao do cluster (para testes/admin).

        Args:
            cluster_name: Nome do cluster

        Returns:
            True se removeu, False caso contrario
        """
        from app.services.redis import redis_client

        if cluster_name not in CORRELATION_CLUSTERS:
            return False

        key = self._make_key(cluster_name)

        try:
            result = await redis_client.delete(key)
            if result > 0:
                logger.info(f"Correlacao do cluster {cluster_name} removida")
            return result > 0
        except Exception as e:
            logger.error(f"Erro ao limpar correlacao: {e}")
            return False


# Singleton
correlation_manager = CorrelationManager()
```

---

## Testes Obrigatorios

### Arquivo: `tests/services/notifications/test_correlation.py`

```python
"""Testes para CorrelationManager."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from app.services.notifications import (
    Notification,
    AlertCategory,
    AlertDomain,
)
from app.services.notifications.correlation import CorrelationManager, correlation_manager


@pytest.fixture
def manager():
    """Fixture para CorrelationManager."""
    return CorrelationManager()


@pytest.fixture
def notification_whatsapp_desconectado():
    """Notificacao desconectado (cluster whatsapp)."""
    return Notification(
        domain=AlertDomain.WHATSAPP,
        category=AlertCategory.CRITICAL,
        alert_type="desconectado",
        title="WhatsApp Offline",
        message="Conexao perdida",
    )


@pytest.fixture
def notification_whatsapp_criptografia():
    """Notificacao criptografia (cluster whatsapp)."""
    return Notification(
        domain=AlertDomain.WHATSAPP,
        category=AlertCategory.ATTENTION,
        alert_type="criptografia",
        title="Erro de Criptografia",
        message="PreKeyError detectado",
    )


@pytest.fixture
def notification_sem_cluster():
    """Notificacao sem cluster."""
    return Notification(
        domain=AlertDomain.SHIFT,
        category=AlertCategory.DIGEST,
        alert_type="plantao_reservado",
        title="Plantao Reservado",
        message="Dr. Silva reservou plantao",
    )


class TestGetCluster:
    """Testes para get_cluster."""

    def test_desconectado_cluster_whatsapp(self, manager, notification_whatsapp_desconectado):
        """desconectado pertence ao cluster whatsapp."""
        cluster = manager.get_cluster(notification_whatsapp_desconectado)
        assert cluster == "whatsapp"

    def test_criptografia_cluster_whatsapp(self, manager, notification_whatsapp_criptografia):
        """criptografia pertence ao cluster whatsapp."""
        cluster = manager.get_cluster(notification_whatsapp_criptografia)
        assert cluster == "whatsapp"

    def test_plantao_sem_cluster(self, manager, notification_sem_cluster):
        """plantao_reservado nao pertence a nenhum cluster."""
        cluster = manager.get_cluster(notification_sem_cluster)
        assert cluster is None

    def test_pool_vazio_cluster_chips(self, manager):
        """pool_vazio pertence ao cluster chips."""
        notif = Notification(alert_type="pool_vazio")
        cluster = manager.get_cluster(notif)
        assert cluster == "chips"


class TestCheckCorrelation:
    """Testes para check_correlation."""

    @pytest.mark.asyncio
    async def test_sem_cluster_retorna_none(self, manager, notification_sem_cluster):
        """Alerta sem cluster nao e correlacionado."""
        result = await manager.check_correlation(notification_sem_cluster)
        assert result is None

    @pytest.mark.asyncio
    async def test_primeiro_alerta_do_cluster(self, manager, notification_whatsapp_desconectado):
        """Primeiro alerta do cluster nao e correlacionado."""
        with patch("app.services.notifications.correlation.cache_get_json", new_callable=AsyncMock) as mock:
            mock.return_value = None

            result = await manager.check_correlation(notification_whatsapp_desconectado)

            assert result is None

    @pytest.mark.asyncio
    async def test_alerta_correlacionado_suprimido(self, manager, notification_whatsapp_criptografia):
        """Alerta de menor prioridade e suprimido."""
        with patch("app.services.notifications.correlation.cache_get_json", new_callable=AsyncMock) as mock:
            # desconectado ja foi enviado (maior prioridade)
            mock.return_value = {
                "alert_type": "desconectado",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            result = await manager.check_correlation(notification_whatsapp_criptografia)

            # criptografia deve ser suprimido
            assert result == "desconectado"

    @pytest.mark.asyncio
    async def test_mesmo_tipo_nao_suprimido(self, manager, notification_whatsapp_desconectado):
        """Mesmo tipo de alerta nao e suprimido (cooldown cuida)."""
        with patch("app.services.notifications.correlation.cache_get_json", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "alert_type": "desconectado",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            result = await manager.check_correlation(notification_whatsapp_desconectado)

            # Mesmo tipo nao deve ser suprimido pela correlacao
            assert result is None


class TestRecordSent:
    """Testes para record_sent."""

    @pytest.mark.asyncio
    async def test_registra_alerta_com_cluster(self, manager, notification_whatsapp_desconectado):
        """Registra alerta que pertence a cluster."""
        with patch("app.services.notifications.correlation.cache_set_json", new_callable=AsyncMock) as mock:
            await manager.record_sent(notification_whatsapp_desconectado)

            mock.assert_called_once()
            call_args = mock.call_args
            data = call_args[0][1]

            assert data["alert_type"] == "desconectado"
            assert data["cluster"] == "whatsapp"

    @pytest.mark.asyncio
    async def test_nao_registra_sem_cluster(self, manager, notification_sem_cluster):
        """Nao registra alerta sem cluster."""
        with patch("app.services.notifications.correlation.cache_set_json", new_callable=AsyncMock) as mock:
            await manager.record_sent(notification_sem_cluster)

            mock.assert_not_called()


class TestGetClusterStatus:
    """Testes para get_cluster_status."""

    @pytest.mark.asyncio
    async def test_cluster_existente(self, manager):
        """Retorna status de cluster existente."""
        with patch("app.services.notifications.correlation.cache_get_json", new_callable=AsyncMock) as mock:
            mock.return_value = None

            status = await manager.get_cluster_status("whatsapp")

            assert status["cluster"] == "whatsapp"
            assert status["has_sent_alert"] is False
            assert "window_minutes" in status
            assert "types_in_cluster" in status

    @pytest.mark.asyncio
    async def test_cluster_inexistente(self, manager):
        """Retorna erro para cluster inexistente."""
        status = await manager.get_cluster_status("cluster_invalido")
        assert "error" in status


class TestClearCluster:
    """Testes para clear_cluster."""

    @pytest.mark.asyncio
    async def test_limpa_cluster_existente(self, manager):
        """Limpa cluster que tem registro."""
        with patch("app.services.notifications.correlation.redis_client") as mock_client:
            mock_client.delete = AsyncMock(return_value=1)

            result = await manager.clear_cluster("whatsapp")

            assert result is True

    @pytest.mark.asyncio
    async def test_cluster_invalido(self, manager):
        """Retorna False para cluster invalido."""
        result = await manager.clear_cluster("cluster_invalido")
        assert result is False


class TestSingleton:
    """Testes para singleton."""

    def test_singleton_exportado(self):
        """correlation_manager e um singleton."""
        assert correlation_manager is not None
        assert isinstance(correlation_manager, CorrelationManager)
```

---

## Checklist de Conclusao

### Implementacao
- [ ] Criar arquivo `correlation.py`
- [ ] Implementar `CorrelationManager`
- [ ] Implementar `_get_window_key`
- [ ] Implementar `_make_key`
- [ ] Implementar `get_cluster`
- [ ] Implementar `check_correlation`
- [ ] Implementar `record_sent`
- [ ] Implementar `get_cluster_status`
- [ ] Implementar `clear_cluster`
- [ ] Exportar singleton
- [ ] Atualizar `__init__.py`

### Testes
- [ ] Criar `tests/services/notifications/test_correlation.py`
- [ ] Testar deteccao de cluster
- [ ] Testar supressao por prioridade
- [ ] Testar registro de envio
- [ ] 100% dos testes passando

### Qualidade
- [ ] Zero erros de mypy
- [ ] Zero erros de ruff

---

## Definition of Done (E04)

1. [ ] `CorrelationManager` implementado
2. [ ] Singleton exportado
3. [ ] Supressao por prioridade funcionando
4. [ ] 100% dos testes passando (0 skipped)
5. [ ] Zero erros de tipo/lint
