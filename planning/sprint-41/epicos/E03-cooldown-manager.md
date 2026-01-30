# E03 - CooldownManager Unificado

**Epico:** E03
**Nome:** CooldownManager Unificado
**Dependencias:** E01, E02
**Prioridade:** Alta

---

## Objetivo

Implementar um gerenciador de cooldown unificado que substitui os 3 sistemas existentes de cooldown (`alertas.py`, `business_events/alerts.py`, `monitor_whatsapp.py`).

---

## Entregaveis

### Arquivo: `cooldown.py`

```python
"""
CooldownManager - Gerenciamento unificado de cooldown.

Sprint 41

Substitui os sistemas de cooldown de:
- alertas.py (cache_key: alerta:cooldown:{tipo})
- business_events/alerts.py (cache_key: alert:cooldown:{hash})
- monitor_whatsapp.py (cache_key: monitor:whatsapp:ultimo_alerta)
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.services.redis import cache_get_json, cache_set_json

from .types import Notification, AlertCategory
from .config import CATEGORY_CONFIG, REDIS_KEYS, get_cooldown_minutes

logger = logging.getLogger(__name__)


class CooldownManager:
    """
    Gerencia cooldown unificado para todas as notificacoes.

    Funcionalidades:
    - Cooldown por categoria (CRITICAL=15min, ATTENTION=30min, etc)
    - Cooldown com escopo (por hospital_id, chip_id quando aplicavel)
    - Verificacao e registro atomicos

    Chave Redis: notif:cooldown:{domain}:{alert_type}:{scope?}
    """

    def __init__(self):
        self._prefix = REDIS_KEYS["cooldown_prefix"]

    def _make_key(self, notification: Notification) -> str:
        """
        Gera chave Redis para cooldown.

        Formato: notif:cooldown:{domain}:{alert_type}:{scope?}

        Args:
            notification: Notificacao

        Returns:
            Chave Redis
        """
        base = f"{self._prefix}{notification.domain.value}:{notification.alert_type}"

        # Adicionar escopo se aplicavel
        scope = self._extract_scope(notification)
        if scope:
            return f"{base}:{scope}"
        return base

    def _extract_scope(self, notification: Notification) -> Optional[str]:
        """
        Extrai escopo do metadata da notificacao.

        Args:
            notification: Notificacao

        Returns:
            Escopo (primeiros 8 chars) ou None
        """
        if notification.metadata.get("hospital_id"):
            return notification.metadata["hospital_id"][:8]
        elif notification.metadata.get("chip_id"):
            return notification.metadata["chip_id"][:8]
        elif notification.metadata.get("instance"):
            return notification.metadata["instance"][:8]
        return None

    async def is_in_cooldown(self, notification: Notification) -> bool:
        """
        Verifica se notificacao esta em cooldown.

        Args:
            notification: Notificacao a verificar

        Returns:
            True se em cooldown, False se pode enviar
        """
        # DIGEST nao tem cooldown individual
        if notification.category == AlertCategory.DIGEST:
            return False

        key = self._make_key(notification)

        try:
            data = await cache_get_json(key)
            if not data:
                return False

            last_sent = datetime.fromisoformat(data["timestamp"])
            cooldown_minutes = get_cooldown_minutes(notification.category)
            cooldown = timedelta(minutes=cooldown_minutes)

            # Converter para UTC se nao tiver timezone
            if last_sent.tzinfo is None:
                last_sent = last_sent.replace(tzinfo=timezone.utc)

            elapsed = datetime.now(timezone.utc) - last_sent
            in_cooldown = elapsed < cooldown

            if in_cooldown:
                remaining = cooldown - elapsed
                logger.debug(
                    f"Alerta {notification.alert_type} em cooldown "
                    f"(restam {remaining.seconds}s)"
                )

            return in_cooldown

        except Exception as e:
            logger.warning(f"Erro ao verificar cooldown: {e}")
            return False  # Fail open

    async def set_cooldown(self, notification: Notification) -> None:
        """
        Registra envio de notificacao para cooldown.

        Args:
            notification: Notificacao enviada
        """
        if notification.category == AlertCategory.DIGEST:
            return

        key = self._make_key(notification)
        cooldown_minutes = get_cooldown_minutes(notification.category)
        ttl = cooldown_minutes * 60 * 2  # 2x cooldown para margem

        try:
            await cache_set_json(key, {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "notification_id": notification.id,
                "alert_type": notification.alert_type,
                "category": notification.category.value,
                "domain": notification.domain.value,
            }, ttl=ttl)

            logger.debug(f"Cooldown registrado: {notification.alert_type} ({cooldown_minutes}min)")

        except Exception as e:
            logger.error(f"Erro ao registrar cooldown: {e}")

    async def get_remaining_seconds(self, notification: Notification) -> int:
        """
        Retorna segundos restantes de cooldown.

        Args:
            notification: Notificacao a verificar

        Returns:
            Segundos restantes (0 se nao em cooldown)
        """
        if notification.category == AlertCategory.DIGEST:
            return 0

        key = self._make_key(notification)

        try:
            data = await cache_get_json(key)
            if not data:
                return 0

            last_sent = datetime.fromisoformat(data["timestamp"])
            cooldown_minutes = get_cooldown_minutes(notification.category)
            cooldown = timedelta(minutes=cooldown_minutes)

            # Converter para UTC se nao tiver timezone
            if last_sent.tzinfo is None:
                last_sent = last_sent.replace(tzinfo=timezone.utc)

            elapsed = datetime.now(timezone.utc) - last_sent

            if elapsed >= cooldown:
                return 0

            return int((cooldown - elapsed).total_seconds())

        except Exception as e:
            logger.warning(f"Erro ao obter tempo restante: {e}")
            return 0

    async def clear_cooldown(self, notification: Notification) -> bool:
        """
        Remove cooldown de uma notificacao (para testes/admin).

        Args:
            notification: Notificacao a limpar

        Returns:
            True se removeu, False se nao existia
        """
        from app.services.redis import redis_client

        key = self._make_key(notification)

        try:
            result = await redis_client.delete(key)
            if result > 0:
                logger.info(f"Cooldown removido: {notification.alert_type}")
            return result > 0
        except Exception as e:
            logger.error(f"Erro ao limpar cooldown: {e}")
            return False

    async def get_cooldown_info(self, notification: Notification) -> dict:
        """
        Retorna informacoes completas sobre cooldown.

        Args:
            notification: Notificacao a verificar

        Returns:
            Dict com informacoes do cooldown
        """
        key = self._make_key(notification)
        in_cooldown = await self.is_in_cooldown(notification)
        remaining = await self.get_remaining_seconds(notification)
        cooldown_minutes = get_cooldown_minutes(notification.category)

        return {
            "key": key,
            "in_cooldown": in_cooldown,
            "remaining_seconds": remaining,
            "cooldown_minutes": cooldown_minutes,
            "category": notification.category.value,
            "alert_type": notification.alert_type,
        }


# Singleton
cooldown_manager = CooldownManager()
```

---

## Testes Obrigatorios

### Arquivo: `tests/services/notifications/test_cooldown.py`

```python
"""Testes para CooldownManager."""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.notifications import (
    Notification,
    AlertCategory,
    AlertDomain,
)
from app.services.notifications.cooldown import CooldownManager, cooldown_manager


@pytest.fixture
def manager():
    """Fixture para CooldownManager."""
    return CooldownManager()


@pytest.fixture
def notification_critical():
    """Notificacao CRITICAL para testes."""
    return Notification(
        domain=AlertDomain.WHATSAPP,
        category=AlertCategory.CRITICAL,
        alert_type="desconectado",
        title="Test",
        message="Test message",
    )


@pytest.fixture
def notification_attention():
    """Notificacao ATTENTION para testes."""
    return Notification(
        domain=AlertDomain.BUSINESS,
        category=AlertCategory.ATTENTION,
        alert_type="handoff_spike",
        title="Test",
        message="Test message",
        metadata={"hospital_id": "hosp-123-456-789"},
    )


@pytest.fixture
def notification_digest():
    """Notificacao DIGEST para testes."""
    return Notification(
        domain=AlertDomain.SHIFT,
        category=AlertCategory.DIGEST,
        alert_type="plantao_reservado",
        title="Test",
        message="Test message",
    )


@pytest.fixture
def notification_info():
    """Notificacao INFO para testes."""
    return Notification(
        domain=AlertDomain.WHATSAPP,
        category=AlertCategory.INFO,
        alert_type="reconectado",
        title="Test",
        message="Test message",
    )


class TestMakeKey:
    """Testes para _make_key."""

    def test_key_basica(self, manager, notification_critical):
        """Gera chave basica sem escopo."""
        key = manager._make_key(notification_critical)
        assert key == "notif:cooldown:whatsapp:desconectado"

    def test_key_com_hospital_id(self, manager, notification_attention):
        """Gera chave com escopo de hospital."""
        key = manager._make_key(notification_attention)
        assert key == "notif:cooldown:business:handoff_spike:hosp-123"

    def test_key_com_chip_id(self, manager):
        """Gera chave com escopo de chip."""
        notif = Notification(
            domain=AlertDomain.CHIPS,
            alert_type="trust_critico",
            metadata={"chip_id": "chip-abc-def-123"},
        )
        key = manager._make_key(notif)
        assert key == "notif:cooldown:chips:trust_critico:chip-abc"

    def test_key_com_instance(self, manager):
        """Gera chave com escopo de instance."""
        notif = Notification(
            domain=AlertDomain.WHATSAPP,
            alert_type="desconectado",
            metadata={"instance": "julia-prod-12345"},
        )
        key = manager._make_key(notif)
        assert key == "notif:cooldown:whatsapp:desconectado:julia-pr"


class TestExtractScope:
    """Testes para _extract_scope."""

    def test_sem_scope(self, manager, notification_critical):
        """Retorna None quando nao ha scope."""
        scope = manager._extract_scope(notification_critical)
        assert scope is None

    def test_hospital_id(self, manager, notification_attention):
        """Extrai hospital_id."""
        scope = manager._extract_scope(notification_attention)
        assert scope == "hosp-123"

    def test_chip_id(self, manager):
        """Extrai chip_id."""
        notif = Notification(metadata={"chip_id": "chip-xyz-123"})
        scope = manager._extract_scope(notif)
        assert scope == "chip-xyz"

    def test_instance(self, manager):
        """Extrai instance."""
        notif = Notification(metadata={"instance": "julia-prod"})
        scope = manager._extract_scope(notif)
        assert scope == "julia-pr"

    def test_prioridade_hospital_sobre_chip(self, manager):
        """Hospital_id tem prioridade sobre chip_id."""
        notif = Notification(metadata={
            "hospital_id": "hosp-abc",
            "chip_id": "chip-xyz"
        })
        scope = manager._extract_scope(notif)
        assert scope == "hosp-abc"


class TestIsInCooldown:
    """Testes para is_in_cooldown."""

    @pytest.mark.asyncio
    async def test_nao_em_cooldown_sem_registro(self, manager, notification_critical):
        """Nao esta em cooldown se nunca enviado."""
        with patch("app.services.notifications.cooldown.cache_get_json", new_callable=AsyncMock) as mock:
            mock.return_value = None

            result = await manager.is_in_cooldown(notification_critical)

            assert result is False
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_em_cooldown_enviado_recentemente(self, manager, notification_critical):
        """Esta em cooldown se enviado ha pouco tempo."""
        with patch("app.services.notifications.cooldown.cache_get_json", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            result = await manager.is_in_cooldown(notification_critical)

            assert result is True

    @pytest.mark.asyncio
    async def test_fora_cooldown_apos_tempo(self, manager, notification_critical):
        """Nao esta em cooldown apos tempo expirar."""
        with patch("app.services.notifications.cooldown.cache_get_json", new_callable=AsyncMock) as mock:
            # CRITICAL tem cooldown de 15 min, simula 20 min atras
            vinte_min_atras = datetime.now(timezone.utc) - timedelta(minutes=20)
            mock.return_value = {
                "timestamp": vinte_min_atras.isoformat(),
            }

            result = await manager.is_in_cooldown(notification_critical)

            assert result is False

    @pytest.mark.asyncio
    async def test_digest_nunca_em_cooldown(self, manager, notification_digest):
        """DIGEST nunca esta em cooldown."""
        # Nao precisa mockar, deve retornar False imediatamente
        result = await manager.is_in_cooldown(notification_digest)
        assert result is False

    @pytest.mark.asyncio
    async def test_erro_retorna_false(self, manager, notification_critical):
        """Em caso de erro, retorna False (fail open)."""
        with patch("app.services.notifications.cooldown.cache_get_json", new_callable=AsyncMock) as mock:
            mock.side_effect = Exception("Redis error")

            result = await manager.is_in_cooldown(notification_critical)

            assert result is False


class TestSetCooldown:
    """Testes para set_cooldown."""

    @pytest.mark.asyncio
    async def test_registra_cooldown(self, manager, notification_critical):
        """Registra cooldown no Redis."""
        with patch("app.services.notifications.cooldown.cache_set_json", new_callable=AsyncMock) as mock:
            await manager.set_cooldown(notification_critical)

            mock.assert_called_once()
            call_args = mock.call_args
            key = call_args[0][0]
            data = call_args[0][1]
            ttl = call_args[1]["ttl"]

            assert key == "notif:cooldown:whatsapp:desconectado"
            assert "timestamp" in data
            assert data["alert_type"] == "desconectado"
            assert ttl == 15 * 60 * 2  # 2x cooldown

    @pytest.mark.asyncio
    async def test_digest_nao_registra_cooldown(self, manager, notification_digest):
        """DIGEST nao registra cooldown."""
        with patch("app.services.notifications.cooldown.cache_set_json", new_callable=AsyncMock) as mock:
            await manager.set_cooldown(notification_digest)

            mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_ttl_proporcional_ao_cooldown(self, manager, notification_info):
        """TTL e 2x o cooldown da categoria."""
        with patch("app.services.notifications.cooldown.cache_set_json", new_callable=AsyncMock) as mock:
            await manager.set_cooldown(notification_info)

            # INFO tem cooldown de 60 min, TTL deve ser 120 min
            ttl = mock.call_args[1]["ttl"]
            assert ttl == 60 * 60 * 2


class TestGetRemainingSeconds:
    """Testes para get_remaining_seconds."""

    @pytest.mark.asyncio
    async def test_retorna_zero_sem_cooldown(self, manager, notification_critical):
        """Retorna 0 se nao em cooldown."""
        with patch("app.services.notifications.cooldown.cache_get_json", new_callable=AsyncMock) as mock:
            mock.return_value = None

            result = await manager.get_remaining_seconds(notification_critical)

            assert result == 0

    @pytest.mark.asyncio
    async def test_retorna_segundos_restantes(self, manager, notification_critical):
        """Retorna segundos restantes de cooldown."""
        # CRITICAL = 15min cooldown, simula envio ha 5 min
        cinco_min_atras = datetime.now(timezone.utc) - timedelta(minutes=5)

        with patch("app.services.notifications.cooldown.cache_get_json", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "timestamp": cinco_min_atras.isoformat(),
            }

            result = await manager.get_remaining_seconds(notification_critical)

            # Deve ter ~10 minutos restantes (600 segundos)
            assert 550 <= result <= 610

    @pytest.mark.asyncio
    async def test_retorna_zero_cooldown_expirado(self, manager, notification_critical):
        """Retorna 0 se cooldown expirou."""
        # CRITICAL = 15min cooldown, simula envio ha 20 min
        vinte_min_atras = datetime.now(timezone.utc) - timedelta(minutes=20)

        with patch("app.services.notifications.cooldown.cache_get_json", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "timestamp": vinte_min_atras.isoformat(),
            }

            result = await manager.get_remaining_seconds(notification_critical)

            assert result == 0

    @pytest.mark.asyncio
    async def test_digest_retorna_zero(self, manager, notification_digest):
        """DIGEST sempre retorna 0."""
        result = await manager.get_remaining_seconds(notification_digest)
        assert result == 0


class TestClearCooldown:
    """Testes para clear_cooldown."""

    @pytest.mark.asyncio
    async def test_remove_cooldown_existente(self, manager, notification_critical):
        """Remove cooldown que existe."""
        with patch("app.services.notifications.cooldown.redis_client") as mock_client:
            mock_client.delete = AsyncMock(return_value=1)

            result = await manager.clear_cooldown(notification_critical)

            assert result is True
            mock_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_retorna_false_se_nao_existe(self, manager, notification_critical):
        """Retorna False se cooldown nao existe."""
        with patch("app.services.notifications.cooldown.redis_client") as mock_client:
            mock_client.delete = AsyncMock(return_value=0)

            result = await manager.clear_cooldown(notification_critical)

            assert result is False


class TestGetCooldownInfo:
    """Testes para get_cooldown_info."""

    @pytest.mark.asyncio
    async def test_retorna_info_completa(self, manager, notification_critical):
        """Retorna informacoes completas."""
        with patch("app.services.notifications.cooldown.cache_get_json", new_callable=AsyncMock) as mock:
            mock.return_value = None

            info = await manager.get_cooldown_info(notification_critical)

            assert "key" in info
            assert "in_cooldown" in info
            assert "remaining_seconds" in info
            assert "cooldown_minutes" in info
            assert "category" in info
            assert "alert_type" in info

            assert info["key"] == "notif:cooldown:whatsapp:desconectado"
            assert info["in_cooldown"] is False
            assert info["remaining_seconds"] == 0
            assert info["cooldown_minutes"] == 15
            assert info["category"] == "critical"


class TestSingleton:
    """Testes para singleton."""

    def test_singleton_exportado(self):
        """cooldown_manager e um singleton."""
        assert cooldown_manager is not None
        assert isinstance(cooldown_manager, CooldownManager)
```

---

## Checklist de Conclusao

### Implementacao
- [ ] Criar arquivo `cooldown.py`
- [ ] Implementar classe `CooldownManager`
- [ ] Implementar `_make_key`
- [ ] Implementar `_extract_scope`
- [ ] Implementar `is_in_cooldown`
- [ ] Implementar `set_cooldown`
- [ ] Implementar `get_remaining_seconds`
- [ ] Implementar `clear_cooldown`
- [ ] Implementar `get_cooldown_info`
- [ ] Exportar singleton `cooldown_manager`
- [ ] Atualizar `__init__.py`

### Testes
- [ ] Criar `tests/services/notifications/test_cooldown.py`
- [ ] Testar geracao de chaves
- [ ] Testar extracao de escopo
- [ ] Testar verificacao de cooldown
- [ ] Testar registro de cooldown
- [ ] Testar tempo restante
- [ ] Testar limpeza de cooldown
- [ ] 100% dos testes passando

### Qualidade
- [ ] Zero erros de mypy
- [ ] Zero erros de ruff

---

## Definition of Done (E03)

Este epico esta **COMPLETO** quando:

1. [ ] `CooldownManager` implementado com todos os metodos
2. [ ] Singleton `cooldown_manager` exportado
3. [ ] Suporte a escopo (hospital_id, chip_id, instance)
4. [ ] 100% dos testes passando (0 skipped)
5. [ ] Zero erros de tipo/lint
