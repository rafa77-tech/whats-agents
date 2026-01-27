# E05 - DigestManager

**Epico:** E05
**Nome:** DigestManager
**Dependencias:** E01, E02
**Prioridade:** Media

---

## Objetivo

Implementar batching de notificacoes DIGEST. Em vez de enviar notificacoes individuais para eventos de baixa prioridade (plantao reservado, handoff resolvido, etc), agrupa-las em um resumo periodico.

---

## Entregaveis

### Arquivo: `digest.py`

```python
"""
DigestManager - Batching de notificacoes de baixa prioridade.

Sprint 41

Notificacoes DIGEST sao agrupadas e enviadas em resumos periodicos
em vez de notificacoes individuais.
"""
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

from app.services.redis import cache_get_json, cache_set_json, redis_client

from .types import Notification, DigestBatch, AlertDomain
from .config import REDIS_KEYS, CATEGORY_CONFIG, AlertCategory

logger = logging.getLogger(__name__)


class DigestManager:
    """
    Gerencia batching de notificacoes DIGEST.

    Funcionalidades:
    - Adiciona notificacoes ao batch pendente
    - Retorna batch para envio
    - Agrupa por dominio para formatacao

    Chave Redis: notif:digest:pending
    """

    def __init__(self):
        self._key = REDIS_KEYS["digest_pending"]
        self._digest_interval = CATEGORY_CONFIG[AlertCategory.DIGEST].get(
            "digest_interval_minutes", 60
        )

    async def add(self, notification: Notification) -> None:
        """
        Adiciona notificacao ao batch pendente.

        Args:
            notification: Notificacao a adicionar
        """
        try:
            # Buscar batch atual
            data = await cache_get_json(self._key)
            if data is None:
                data = {"notifications": [], "created_at": datetime.now(timezone.utc).isoformat()}

            # Adicionar notificacao
            data["notifications"].append(notification.to_dict())

            # Salvar com TTL de 2h (janela para envio)
            await cache_set_json(self._key, data, ttl=7200)

            logger.debug(
                f"Notificacao adicionada ao digest: {notification.alert_type} "
                f"(total: {len(data['notifications'])})"
            )

        except Exception as e:
            logger.error(f"Erro ao adicionar ao digest: {e}")

    async def get_pending(self) -> List[Notification]:
        """
        Retorna notificacoes pendentes no batch.

        Returns:
            Lista de notificacoes pendentes
        """
        try:
            data = await cache_get_json(self._key)
            if not data or not data.get("notifications"):
                return []

            notifications = []
            for item in data["notifications"]:
                try:
                    notif = Notification(
                        id=item.get("id", ""),
                        domain=AlertDomain(item.get("domain", "system")),
                        category=AlertCategory(item.get("category", "digest")),
                        alert_type=item.get("alert_type", ""),
                        title=item.get("title", ""),
                        message=item.get("message", ""),
                        metadata=item.get("metadata", {}),
                        correlation_key=item.get("correlation_key"),
                        source_file=item.get("source_file"),
                    )
                    notifications.append(notif)
                except Exception as e:
                    logger.warning(f"Erro ao deserializar notificacao: {e}")
                    continue

            return notifications

        except Exception as e:
            logger.error(f"Erro ao obter notificacoes pendentes: {e}")
            return []

    async def get_pending_count(self) -> int:
        """
        Retorna quantidade de notificacoes pendentes.

        Returns:
            Quantidade de notificacoes
        """
        try:
            data = await cache_get_json(self._key)
            if not data:
                return 0
            return len(data.get("notifications", []))
        except Exception:
            return 0

    async def clear(self) -> int:
        """
        Limpa batch de notificacoes pendentes.

        Returns:
            Quantidade de notificacoes removidas
        """
        try:
            data = await cache_get_json(self._key)
            count = len(data.get("notifications", [])) if data else 0

            await redis_client.delete(self._key)

            if count > 0:
                logger.info(f"Digest limpo: {count} notificacoes removidas")

            return count

        except Exception as e:
            logger.error(f"Erro ao limpar digest: {e}")
            return 0

    async def mark_sent(self, notification_ids: List[str]) -> int:
        """
        Remove notificacoes especificas do batch.

        Args:
            notification_ids: IDs das notificacoes enviadas

        Returns:
            Quantidade removida
        """
        try:
            data = await cache_get_json(self._key)
            if not data:
                return 0

            original_count = len(data.get("notifications", []))

            # Filtrar notificacoes nao enviadas
            data["notifications"] = [
                n for n in data["notifications"]
                if n.get("id") not in notification_ids
            ]

            removed = original_count - len(data["notifications"])

            if data["notifications"]:
                await cache_set_json(self._key, data, ttl=7200)
            else:
                await redis_client.delete(self._key)

            logger.debug(f"Digest: {removed} notificacoes marcadas como enviadas")

            return removed

        except Exception as e:
            logger.error(f"Erro ao marcar notificacoes enviadas: {e}")
            return 0

    def group_by_domain(self, notifications: List[Notification]) -> Dict[str, List[Notification]]:
        """
        Agrupa notificacoes por dominio.

        Args:
            notifications: Lista de notificacoes

        Returns:
            Dict com dominio como chave e lista de notificacoes
        """
        grouped: Dict[str, List[Notification]] = {}

        for notif in notifications:
            domain = notif.domain.value
            if domain not in grouped:
                grouped[domain] = []
            grouped[domain].append(notif)

        return grouped

    def group_by_type(self, notifications: List[Notification]) -> Dict[str, List[Notification]]:
        """
        Agrupa notificacoes por tipo.

        Args:
            notifications: Lista de notificacoes

        Returns:
            Dict com tipo como chave e lista de notificacoes
        """
        grouped: Dict[str, List[Notification]] = {}

        for notif in notifications:
            alert_type = notif.alert_type
            if alert_type not in grouped:
                grouped[alert_type] = []
            grouped[alert_type].append(notif)

        return grouped

    async def get_digest_info(self) -> dict:
        """
        Retorna informacoes sobre o digest atual.

        Returns:
            Dict com informacoes do digest
        """
        try:
            data = await cache_get_json(self._key)

            if not data:
                return {
                    "pending_count": 0,
                    "created_at": None,
                    "domains": {},
                    "types": {},
                }

            notifications = await self.get_pending()
            by_domain = self.group_by_domain(notifications)
            by_type = self.group_by_type(notifications)

            return {
                "pending_count": len(notifications),
                "created_at": data.get("created_at"),
                "domains": {k: len(v) for k, v in by_domain.items()},
                "types": {k: len(v) for k, v in by_type.items()},
                "digest_interval_minutes": self._digest_interval,
            }

        except Exception as e:
            logger.error(f"Erro ao obter info do digest: {e}")
            return {"error": str(e)}


# Singleton
digest_manager = DigestManager()
```

---

## Testes Obrigatorios

### Arquivo: `tests/services/notifications/test_digest.py`

```python
"""Testes para DigestManager."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from app.services.notifications import (
    Notification,
    AlertCategory,
    AlertDomain,
)
from app.services.notifications.digest import DigestManager, digest_manager


@pytest.fixture
def manager():
    """Fixture para DigestManager."""
    return DigestManager()


@pytest.fixture
def notification_plantao():
    """Notificacao de plantao reservado."""
    return Notification(
        id="notif-001",
        domain=AlertDomain.SHIFT,
        category=AlertCategory.DIGEST,
        alert_type="plantao_reservado",
        title="Plantao Reservado",
        message="Dr. Silva reservou plantao no Hospital ABC",
    )


@pytest.fixture
def notification_handoff():
    """Notificacao de handoff resolvido."""
    return Notification(
        id="notif-002",
        domain=AlertDomain.HANDOFF,
        category=AlertCategory.DIGEST,
        alert_type="handoff_resolvido",
        title="Handoff Resolvido",
        message="Handoff finalizado com sucesso",
    )


class TestAdd:
    """Testes para add."""

    @pytest.mark.asyncio
    async def test_adiciona_primeira_notificacao(self, manager, notification_plantao):
        """Adiciona primeira notificacao ao batch vazio."""
        with patch("app.services.notifications.digest.cache_get_json", new_callable=AsyncMock) as mock_get:
            with patch("app.services.notifications.digest.cache_set_json", new_callable=AsyncMock) as mock_set:
                mock_get.return_value = None

                await manager.add(notification_plantao)

                mock_set.assert_called_once()
                call_data = mock_set.call_args[0][1]
                assert len(call_data["notifications"]) == 1
                assert call_data["notifications"][0]["alert_type"] == "plantao_reservado"

    @pytest.mark.asyncio
    async def test_adiciona_a_batch_existente(self, manager, notification_plantao, notification_handoff):
        """Adiciona a batch que ja tem notificacoes."""
        with patch("app.services.notifications.digest.cache_get_json", new_callable=AsyncMock) as mock_get:
            with patch("app.services.notifications.digest.cache_set_json", new_callable=AsyncMock) as mock_set:
                # Batch ja tem uma notificacao
                mock_get.return_value = {
                    "notifications": [notification_plantao.to_dict()],
                    "created_at": datetime.now(timezone.utc).isoformat()
                }

                await manager.add(notification_handoff)

                call_data = mock_set.call_args[0][1]
                assert len(call_data["notifications"]) == 2


class TestGetPending:
    """Testes para get_pending."""

    @pytest.mark.asyncio
    async def test_retorna_lista_vazia_sem_dados(self, manager):
        """Retorna lista vazia quando nao ha dados."""
        with patch("app.services.notifications.digest.cache_get_json", new_callable=AsyncMock) as mock:
            mock.return_value = None

            result = await manager.get_pending()

            assert result == []

    @pytest.mark.asyncio
    async def test_retorna_notificacoes(self, manager, notification_plantao):
        """Retorna notificacoes pendentes."""
        with patch("app.services.notifications.digest.cache_get_json", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "notifications": [notification_plantao.to_dict()],
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            result = await manager.get_pending()

            assert len(result) == 1
            assert result[0].alert_type == "plantao_reservado"


class TestGetPendingCount:
    """Testes para get_pending_count."""

    @pytest.mark.asyncio
    async def test_retorna_zero_sem_dados(self, manager):
        """Retorna 0 quando nao ha dados."""
        with patch("app.services.notifications.digest.cache_get_json", new_callable=AsyncMock) as mock:
            mock.return_value = None

            result = await manager.get_pending_count()

            assert result == 0

    @pytest.mark.asyncio
    async def test_retorna_contagem(self, manager, notification_plantao, notification_handoff):
        """Retorna contagem correta."""
        with patch("app.services.notifications.digest.cache_get_json", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "notifications": [
                    notification_plantao.to_dict(),
                    notification_handoff.to_dict()
                ]
            }

            result = await manager.get_pending_count()

            assert result == 2


class TestClear:
    """Testes para clear."""

    @pytest.mark.asyncio
    async def test_limpa_batch(self, manager):
        """Limpa batch e retorna contagem."""
        with patch("app.services.notifications.digest.cache_get_json", new_callable=AsyncMock) as mock_get:
            with patch("app.services.notifications.digest.redis_client") as mock_client:
                mock_get.return_value = {"notifications": [{"id": "1"}, {"id": "2"}]}
                mock_client.delete = AsyncMock()

                result = await manager.clear()

                assert result == 2
                mock_client.delete.assert_called_once()


class TestMarkSent:
    """Testes para mark_sent."""

    @pytest.mark.asyncio
    async def test_remove_notificacoes_enviadas(self, manager, notification_plantao, notification_handoff):
        """Remove notificacoes marcadas como enviadas."""
        with patch("app.services.notifications.digest.cache_get_json", new_callable=AsyncMock) as mock_get:
            with patch("app.services.notifications.digest.cache_set_json", new_callable=AsyncMock) as mock_set:
                mock_get.return_value = {
                    "notifications": [
                        notification_plantao.to_dict(),
                        notification_handoff.to_dict()
                    ]
                }

                result = await manager.mark_sent(["notif-001"])

                assert result == 1
                call_data = mock_set.call_args[0][1]
                assert len(call_data["notifications"]) == 1
                assert call_data["notifications"][0]["id"] == "notif-002"


class TestGroupByDomain:
    """Testes para group_by_domain."""

    def test_agrupa_por_dominio(self, manager, notification_plantao, notification_handoff):
        """Agrupa notificacoes por dominio."""
        notifications = [notification_plantao, notification_handoff]

        grouped = manager.group_by_domain(notifications)

        assert "shift" in grouped
        assert "handoff" in grouped
        assert len(grouped["shift"]) == 1
        assert len(grouped["handoff"]) == 1

    def test_mesmo_dominio_agrupado(self, manager):
        """Notificacoes do mesmo dominio sao agrupadas."""
        notif1 = Notification(domain=AlertDomain.SHIFT, alert_type="plantao_reservado")
        notif2 = Notification(domain=AlertDomain.SHIFT, alert_type="confirmacao_plantao")

        grouped = manager.group_by_domain([notif1, notif2])

        assert len(grouped) == 1
        assert len(grouped["shift"]) == 2


class TestGroupByType:
    """Testes para group_by_type."""

    def test_agrupa_por_tipo(self, manager, notification_plantao, notification_handoff):
        """Agrupa notificacoes por tipo."""
        notifications = [notification_plantao, notification_handoff]

        grouped = manager.group_by_type(notifications)

        assert "plantao_reservado" in grouped
        assert "handoff_resolvido" in grouped


class TestGetDigestInfo:
    """Testes para get_digest_info."""

    @pytest.mark.asyncio
    async def test_info_batch_vazio(self, manager):
        """Retorna info para batch vazio."""
        with patch("app.services.notifications.digest.cache_get_json", new_callable=AsyncMock) as mock:
            mock.return_value = None

            info = await manager.get_digest_info()

            assert info["pending_count"] == 0
            assert info["created_at"] is None

    @pytest.mark.asyncio
    async def test_info_com_notificacoes(self, manager, notification_plantao, notification_handoff):
        """Retorna info com notificacoes."""
        with patch("app.services.notifications.digest.cache_get_json", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "notifications": [
                    notification_plantao.to_dict(),
                    notification_handoff.to_dict()
                ],
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            info = await manager.get_digest_info()

            assert info["pending_count"] == 2
            assert "shift" in info["domains"]
            assert "handoff" in info["domains"]


class TestSingleton:
    """Testes para singleton."""

    def test_singleton_exportado(self):
        """digest_manager e um singleton."""
        assert digest_manager is not None
        assert isinstance(digest_manager, DigestManager)
```

---

## Checklist de Conclusao

### Implementacao
- [ ] Criar arquivo `digest.py`
- [ ] Implementar `DigestManager`
- [ ] Implementar `add`
- [ ] Implementar `get_pending`
- [ ] Implementar `get_pending_count`
- [ ] Implementar `clear`
- [ ] Implementar `mark_sent`
- [ ] Implementar `group_by_domain`
- [ ] Implementar `group_by_type`
- [ ] Implementar `get_digest_info`
- [ ] Exportar singleton
- [ ] Atualizar `__init__.py`

### Testes
- [ ] Criar `tests/services/notifications/test_digest.py`
- [ ] 100% dos testes passando

### Qualidade
- [ ] Zero erros de mypy
- [ ] Zero erros de ruff

---

## Definition of Done (E05)

1. [ ] `DigestManager` implementado
2. [ ] Singleton exportado
3. [ ] Agrupamento por dominio e tipo funcionando
4. [ ] 100% dos testes passando (0 skipped)
5. [ ] Zero erros de tipo/lint
