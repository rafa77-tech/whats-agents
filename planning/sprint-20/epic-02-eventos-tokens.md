# Epic 02: Eventos e Tokens JWT

## Objetivo

Adicionar novos tipos de eventos para auditoria do handoff e implementar geracao/validacao de tokens JWT para links de confirmacao.

## Contexto

O sistema de business_events (Sprint 17) ja existe. Precisamos:
1. Adicionar 7 novos EventTypes
2. Criar modulo de geracao de tokens JWT assinados
3. Criar validador de tokens com verificacao de uso unico

---

## Story 2.1: Novos EventTypes

### Objetivo
Adicionar eventos de handoff ao enum existente.

### Arquivo: `app/services/business_events/types.py`

```python
# Adicionar ao enum EventType existente:

class EventType(Enum):
    # ... eventos existentes ...

    # Handoff externo (Sprint 20)
    HANDOFF_CREATED = "handoff_created"              # Ponte criada
    HANDOFF_CONTACTED = "handoff_contacted"          # Msg enviada ao divulgador
    HANDOFF_CONFIRM_CLICKED = "handoff_confirm_clicked"  # Link clicado
    HANDOFF_CONFIRMED = "handoff_confirmed"          # Plantao confirmado
    HANDOFF_NOT_CONFIRMED = "handoff_not_confirmed"  # Plantao nao fechou
    HANDOFF_EXPIRED = "handoff_expired"              # Expirou sem resposta
    HANDOFF_FOLLOWUP_SENT = "handoff_followup_sent"  # Follow-up enviado
```

### DoD

- [ ] 7 novos EventTypes adicionados
- [ ] Enum compila sem erros
- [ ] Testes existentes continuam passando

---

## Story 2.2: Modulo de Tokens JWT

### Objetivo
Criar modulo para gerar e validar tokens de confirmacao.

### Arquivo: `app/services/external_handoff/tokens.py`

```python
"""
Geracao e validacao de tokens JWT para confirmacao de handoff.

Sprint 20 - E02 - Tokens seguros e single-use.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import uuid4

import jwt

from app.core.config import settings
from app.services.supabase import supabase

logger = logging.getLogger(__name__)

# Configuracoes
TOKEN_EXPIRY_HOURS = 48
ALGORITHM = "HS256"


def gerar_token_confirmacao(
    handoff_id: str,
    action: str,  # 'confirmed' ou 'not_confirmed'
) -> str:
    """
    Gera token JWT assinado para confirmacao de handoff.

    Args:
        handoff_id: UUID do handoff
        action: Acao que o token executa

    Returns:
        Token JWT assinado

    Exemplo de uso:
        token = gerar_token_confirmacao("uuid-123", "confirmed")
        link = f"https://app.com/handoff/confirm?t={token}"
    """
    # JTI unico para garantir single-use
    jti = str(uuid4())

    payload = {
        "handoff_id": handoff_id,
        "action": action,
        "jti": jti,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS),
    }

    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,  # Usar secret dedicado ou ANTHROPIC_API_KEY como fallback
        algorithm=ALGORITHM,
    )

    logger.debug(f"Token gerado para handoff {handoff_id[:8]}, action={action}, jti={jti[:8]}")

    return token


def gerar_par_links(handoff_id: str, base_url: str = None) -> Tuple[str, str]:
    """
    Gera par de links (confirmar/nao confirmar) para o handoff.

    Args:
        handoff_id: UUID do handoff
        base_url: URL base (default: settings.APP_BASE_URL)

    Returns:
        Tuple (link_confirmar, link_nao_confirmar)
    """
    base = base_url or settings.APP_BASE_URL or "https://api.revoluna.com"

    token_confirm = gerar_token_confirmacao(handoff_id, "confirmed")
    token_not_confirm = gerar_token_confirmacao(handoff_id, "not_confirmed")

    link_confirmar = f"{base}/handoff/confirm?t={token_confirm}"
    link_nao_confirmar = f"{base}/handoff/confirm?t={token_not_confirm}"

    return link_confirmar, link_nao_confirmar


async def validar_token(token: str) -> Tuple[bool, Optional[dict], Optional[str]]:
    """
    Valida token JWT e verifica se ja foi usado.

    Args:
        token: Token JWT

    Returns:
        Tuple (valido, payload, erro)
        - valido: True se token e valido e nao foi usado
        - payload: Dados do token se valido
        - erro: Mensagem de erro se invalido
    """
    try:
        # Decodificar e validar assinatura/expiracao
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        handoff_id = payload.get("handoff_id")
        action = payload.get("action")
        jti = payload.get("jti")

        if not all([handoff_id, action, jti]):
            return False, None, "Token incompleto"

        # Verificar se ja foi usado
        response = supabase.table("handoff_used_tokens") \
            .select("jti") \
            .eq("jti", jti) \
            .execute()

        if response.data:
            logger.warning(f"Token ja usado: jti={jti[:8]}")
            return False, payload, "Token ja utilizado"

        return True, payload, None

    except jwt.ExpiredSignatureError:
        logger.warning("Token expirado")
        return False, None, "Link expirado"

    except jwt.InvalidTokenError as e:
        logger.warning(f"Token invalido: {e}")
        return False, None, "Link invalido"


async def marcar_token_usado(
    jti: str,
    handoff_id: str,
    action: str,
    ip_address: str = None,
) -> bool:
    """
    Marca token como usado (single-use).

    Args:
        jti: JWT ID
        handoff_id: UUID do handoff
        action: Acao executada
        ip_address: IP de origem (opcional)

    Returns:
        True se marcado com sucesso
    """
    try:
        supabase.table("handoff_used_tokens").insert({
            "jti": jti,
            "handoff_id": handoff_id,
            "action": action,
            "ip_address": ip_address,
        }).execute()

        logger.info(f"Token marcado como usado: jti={jti[:8]}")
        return True

    except Exception as e:
        # Pode falhar por unique constraint se race condition
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            logger.warning(f"Token ja marcado (race condition): jti={jti[:8]}")
            return False

        logger.error(f"Erro ao marcar token: {e}")
        return False
```

### DoD

- [ ] Funcao `gerar_token_confirmacao` criada
- [ ] Funcao `gerar_par_links` criada
- [ ] Funcao `validar_token` criada
- [ ] Funcao `marcar_token_usado` criada
- [ ] Logs informativos em todas operacoes

---

## Story 2.3: Configuracao JWT

### Objetivo
Garantir que existe secret para assinar tokens.

### Arquivo: `app/core/config.py`

```python
# Adicionar ao Settings:

class Settings(BaseSettings):
    # ... campos existentes ...

    # JWT para handoff (Sprint 20)
    JWT_SECRET_KEY: str = Field(
        default="",
        description="Secret para assinar tokens JWT de handoff"
    )

    APP_BASE_URL: str = Field(
        default="https://api.revoluna.com",
        description="URL base da aplicacao para links"
    )

    @property
    def jwt_secret(self) -> str:
        """Retorna JWT secret, usando ANTHROPIC_API_KEY como fallback."""
        return self.JWT_SECRET_KEY or self.ANTHROPIC_API_KEY
```

### DoD

- [ ] Campo JWT_SECRET_KEY adicionado
- [ ] Campo APP_BASE_URL adicionado
- [ ] Fallback para ANTHROPIC_API_KEY funcionando

---

## Story 2.4: Testes de Token

### Arquivo: `tests/external_handoff/test_tokens.py`

```python
"""Testes para geracao e validacao de tokens."""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import jwt

from app.services.external_handoff.tokens import (
    gerar_token_confirmacao,
    gerar_par_links,
    validar_token,
    marcar_token_usado,
    TOKEN_EXPIRY_HOURS,
    ALGORITHM,
)


class TestGerarToken:
    """Testes de geracao de token."""

    def test_gera_token_valido(self):
        """Token deve ser JWT valido."""
        with patch("app.services.external_handoff.tokens.settings") as mock_settings:
            mock_settings.JWT_SECRET_KEY = "test-secret"

            token = gerar_token_confirmacao("handoff-123", "confirmed")

            # Deve decodificar sem erros
            payload = jwt.decode(token, "test-secret", algorithms=[ALGORITHM])
            assert payload["handoff_id"] == "handoff-123"
            assert payload["action"] == "confirmed"
            assert "jti" in payload
            assert "exp" in payload

    def test_token_tem_expiracao_correta(self):
        """Token deve expirar em 48h."""
        with patch("app.services.external_handoff.tokens.settings") as mock_settings:
            mock_settings.JWT_SECRET_KEY = "test-secret"

            token = gerar_token_confirmacao("handoff-123", "confirmed")
            payload = jwt.decode(token, "test-secret", algorithms=[ALGORITHM])

            exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
            now = datetime.now(timezone.utc)

            # Deve expirar entre 47h e 49h (margem para tempo de execucao)
            delta = exp - now
            assert timedelta(hours=47) < delta < timedelta(hours=49)


class TestGerarParLinks:
    """Testes de geracao de par de links."""

    def test_gera_dois_links_diferentes(self):
        """Deve gerar links distintos para confirmar/nao confirmar."""
        with patch("app.services.external_handoff.tokens.settings") as mock_settings:
            mock_settings.JWT_SECRET_KEY = "test-secret"
            mock_settings.APP_BASE_URL = "https://test.com"

            link_sim, link_nao = gerar_par_links("handoff-123")

            assert link_sim.startswith("https://test.com/handoff/confirm?t=")
            assert link_nao.startswith("https://test.com/handoff/confirm?t=")
            assert link_sim != link_nao


class TestValidarToken:
    """Testes de validacao de token."""

    @pytest.mark.asyncio
    async def test_token_valido(self):
        """Token valido e nao usado deve passar."""
        with patch("app.services.external_handoff.tokens.settings") as mock_settings, \
             patch("app.services.external_handoff.tokens.supabase") as mock_supabase:
            mock_settings.JWT_SECRET_KEY = "test-secret"
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

            token = gerar_token_confirmacao("handoff-123", "confirmed")
            valido, payload, erro = await validar_token(token)

            assert valido is True
            assert payload["handoff_id"] == "handoff-123"
            assert erro is None

    @pytest.mark.asyncio
    async def test_token_ja_usado(self):
        """Token ja usado deve ser rejeitado."""
        with patch("app.services.external_handoff.tokens.settings") as mock_settings, \
             patch("app.services.external_handoff.tokens.supabase") as mock_supabase:
            mock_settings.JWT_SECRET_KEY = "test-secret"
            # Simula token ja usado
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{"jti": "xxx"}]
            )

            token = gerar_token_confirmacao("handoff-123", "confirmed")
            valido, payload, erro = await validar_token(token)

            assert valido is False
            assert "ja utilizado" in erro

    @pytest.mark.asyncio
    async def test_token_expirado(self):
        """Token expirado deve ser rejeitado."""
        with patch("app.services.external_handoff.tokens.settings") as mock_settings:
            mock_settings.JWT_SECRET_KEY = "test-secret"

            # Criar token expirado manualmente
            payload = {
                "handoff_id": "handoff-123",
                "action": "confirmed",
                "jti": "test-jti",
                "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            }
            token = jwt.encode(payload, "test-secret", algorithm=ALGORITHM)

            valido, _, erro = await validar_token(token)

            assert valido is False
            assert "expirado" in erro.lower()

    @pytest.mark.asyncio
    async def test_token_invalido(self):
        """Token com assinatura invalida deve ser rejeitado."""
        with patch("app.services.external_handoff.tokens.settings") as mock_settings:
            mock_settings.JWT_SECRET_KEY = "test-secret"

            # Token assinado com secret diferente
            payload = {"handoff_id": "handoff-123", "action": "confirmed", "jti": "test"}
            token = jwt.encode(payload, "wrong-secret", algorithm=ALGORITHM)

            valido, _, erro = await validar_token(token)

            assert valido is False
            assert "invalido" in erro.lower()
```

### DoD

- [ ] Testes para geracao de token
- [ ] Testes para validacao (valido, usado, expirado, invalido)
- [ ] Testes para par de links
- [ ] Cobertura > 90%

---

## Checklist do Epico

- [ ] **S20.E02.1** - EventTypes adicionados
- [ ] **S20.E02.2** - Modulo tokens.py criado
- [ ] **S20.E02.3** - Configuracao JWT adicionada
- [ ] **S20.E02.4** - Testes passando
- [ ] Tokens sendo gerados corretamente
- [ ] Validacao funcionando
- [ ] Single-use garantido
