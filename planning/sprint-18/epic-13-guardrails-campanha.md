# E13 - Guardrails de Campanha

**Prioridade:** P0 (Critica)
**Estimativa:** 1 dia
**Dependencias:** Policy Engine (Sprint 15), Business Events (Sprint 17)

---

## Objetivo

Criar camada de guardrails que **impossibilita** o sistema de violar opt-out, cooling-off ou limites de contato, mesmo com bugs no codigo. Guardrail atua **ANTES** de qualquer tentativa de envio.

### Por que P0?

- Violacao de opt-out = risco legal e reputacional
- Sistema atual depende de cada ponto de envio verificar corretamente
- Guardrails centralizados = defesa em profundidade
- **Impossivel de burlar**, mesmo com bug

---

## Principios de Design

### 1. Pre-Send Enforcement

Guardrail atua **ANTES** de:
- Gerar texto da mensagem
- Chamar Twilio/Evolution API
- Qualquer operacao custosa

```
[Decisao de enviar] → [GUARDRAIL] → [Gerar texto] → [Enviar]
                          ↓
                       BLOQUEIO
                          ↓
                   campaign_blocked event
```

### 2. Aplica-se a Todos os Tipos de Outbound

| Tipo | Origem | Guardrail? |
|------|--------|------------|
| Campanhas | `campaign` | Sim |
| Followups automaticos | `ai_followup` | Sim |
| Reativacoes | `ai_reactivation` | Sim |
| Operacoes via Slack | `slack_ops` | **Bypass permitido** |
| Console humano | `human_console` | **Bypass permitido** |

### 3. Bypass Controlado

Humanos (via Slack ou console) podem fazer bypass, mas:
- Sempre emite evento de auditoria
- Loga quem fez e por que
- Nunca e silencioso

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Campaign Guardrails Layer                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    CampaignGuardrailService                          │   │
│  │                                                                      │   │
│  │  can_send_outbound(cliente_id, origin) -> GuardrailResult            │   │
│  │                                                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐     │   │
│  │  │                      Origin Types                           │     │   │
│  │  │  campaign | ai_followup | ai_reactivation | slack_ops |     │     │   │
│  │  │  human_console                                              │     │   │
│  │  └─────────────────────────────────────────────────────────────┘     │   │
│  │                                                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐     │   │
│  │  │                    Verificacoes (ordem)                     │     │   │
│  │  │                                                             │     │   │
│  │  │  1. permission_state == opted_out                           │     │   │
│  │  │     → BLOQUEIA (exceto slack_ops/human_console com bypass)  │     │   │
│  │  │                                                             │     │   │
│  │  │  2. permission_state == cooling_off → BLOQUEIA              │     │   │
│  │  │  3. next_allowed_at > now()         → BLOQUEIA              │     │   │
│  │  │  4. contact_count_7d >= TETO        → BLOQUEIA              │     │   │
│  │  │                                                             │     │   │
│  │  └─────────────────────────────────────────────────────────────┘     │   │
│  │                                                                      │   │
│  │  Se BLOQUEADO → emit business_event("campaign_blocked", ...)         │   │
│  │  Se BYPASS    → emit business_event("guardrail_bypassed", ...)       │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                        Pontos de Integracao                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐      │
│  │ campanha.py │   │ fila_msgs   │   │ agente.py   │   │ slack/      │      │
│  │ (campaign)  │   │ (followup)  │   │ (reactivate)│   │ (slack_ops) │      │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘      │
│         │                 │                 │                 │             │
│         └─────────────────┴────────┬────────┴─────────────────┘             │
│                                    │                                        │
│                                    ▼                                        │
│                      can_send_outbound(cliente_id, origin)                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Regras de Bloqueio

| # | Condicao | Resultado | Bypass? |
|---|----------|-----------|---------|
| 1 | `permission_state = opted_out` | BLOQUEIA | Somente slack_ops/human_console |
| 2 | `permission_state = cooling_off` | BLOQUEIA | Nao |
| 3 | `next_allowed_at > now()` | BLOQUEIA | Nao |
| 4 | `contact_count_7d >= MAX_CONTACTS_7D` | BLOQUEIA | Nao |

**Configuracao padrao:**
```python
MAX_CONTACTS_7D = 5  # Maximo de mensagens outbound em 7 dias
```

---

## Tipos de Dados

```python
# app/services/guardrails/types.py

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime


class OutboundOrigin(Enum):
    """Origem do envio outbound."""
    CAMPAIGN = "campaign"              # Campanha automatizada
    AI_FOLLOWUP = "ai_followup"        # Followup automatico da Julia
    AI_REACTIVATION = "ai_reactivation"  # Reativacao automatica
    SLACK_OPS = "slack_ops"            # Operador via Slack
    HUMAN_CONSOLE = "human_console"    # Console humano direto

    @property
    def allows_bypass(self) -> bool:
        """Retorna se esta origem permite bypass de guardrails."""
        return self in {OutboundOrigin.SLACK_OPS, OutboundOrigin.HUMAN_CONSOLE}

    @property
    def is_automated(self) -> bool:
        """Retorna se e origem automatizada (sem humano)."""
        return self in {
            OutboundOrigin.CAMPAIGN,
            OutboundOrigin.AI_FOLLOWUP,
            OutboundOrigin.AI_REACTIVATION
        }


class BlockReason(Enum):
    """Motivo do bloqueio."""
    OPTED_OUT = "opted_out"
    COOLING_OFF = "cooling_off"
    NEXT_ALLOWED = "next_allowed_at"
    CONTACT_LIMIT = "contact_count_7d"


class GuardrailDecision(Enum):
    """Decisao do guardrail."""
    ALLOWED = "allowed"          # Pode enviar
    BLOCKED = "blocked"          # Bloqueado
    BYPASSED = "bypassed"        # Bloquearia, mas humano fez bypass


@dataclass
class GuardrailResult:
    """Resultado da verificacao de guardrails."""
    decision: GuardrailDecision
    origin: OutboundOrigin
    cliente_id: str
    block_reason: Optional[BlockReason] = None
    block_details: Optional[str] = None
    bypass_reason: Optional[str] = None
    bypass_by: Optional[str] = None
    checked_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def allowed(self) -> bool:
        """Pode enviar? (allowed ou bypassed)"""
        return self.decision in {GuardrailDecision.ALLOWED, GuardrailDecision.BYPASSED}

    @property
    def was_bypassed(self) -> bool:
        """Foi bypass?"""
        return self.decision == GuardrailDecision.BYPASSED

    def to_dict(self) -> dict:
        return {
            "decision": self.decision.value,
            "allowed": self.allowed,
            "origin": self.origin.value,
            "cliente_id": self.cliente_id,
            "block_reason": self.block_reason.value if self.block_reason else None,
            "block_details": self.block_details,
            "was_bypassed": self.was_bypassed,
            "bypass_reason": self.bypass_reason,
            "bypass_by": self.bypass_by,
            "checked_at": self.checked_at.isoformat(),
        }
```

---

## Servico Principal

```python
# app/services/guardrails/campaign.py

"""
Guardrails de campanha - camada de protecao impossivel de burlar.

Sprint 18 - Data Integrity

IMPORTANTE:
- Chamado ANTES de qualquer tentativa de envio
- Aplica-se a campanhas, followups e reativacoes
- Bypass permitido SOMENTE para operadores humanos (slack_ops, human_console)
- Bypass SEMPRE gera evento de auditoria
"""
import logging
from datetime import datetime
from typing import Optional

from app.services.policy.repository import load_doctor_state
from app.services.policy.types import PermissionState
from app.services.business_events import emit_event
from .types import (
    GuardrailResult, GuardrailDecision, BlockReason,
    OutboundOrigin
)

logger = logging.getLogger(__name__)

# Configuracao
MAX_CONTACTS_7D = 5  # Teto de contatos em 7 dias


async def can_send_outbound(
    cliente_id: str,
    origin: OutboundOrigin,
    campanha_id: Optional[str] = None,
    bypass_reason: Optional[str] = None,
    bypass_by: Optional[str] = None,
) -> GuardrailResult:
    """
    Verifica se pode enviar mensagem outbound para cliente.

    IMPORTANTE: Esta funcao DEVE ser chamada ANTES de:
    - Gerar texto da mensagem
    - Chamar Evolution API / Twilio
    - Qualquer operacao custosa

    Args:
        cliente_id: ID do cliente/medico
        origin: Origem do envio (campaign, ai_followup, slack_ops, etc)
        campanha_id: ID da campanha (opcional, para logging)
        bypass_reason: Motivo do bypass (obrigatorio para bypass)
        bypass_by: Quem autorizou o bypass (obrigatorio para bypass)

    Returns:
        GuardrailResult com decision, allowed, e detalhes
    """
    try:
        # Carregar estado do medico
        state = await load_doctor_state(cliente_id)

        if not state:
            # Sem estado = conservador para automaticos, permite para humanos
            if origin.is_automated:
                logger.warning(f"Guardrail: estado nao encontrado para {cliente_id}, bloqueando automatico")
                return GuardrailResult(
                    decision=GuardrailDecision.BLOCKED,
                    origin=origin,
                    cliente_id=cliente_id,
                    block_reason=BlockReason.OPTED_OUT,  # Conservador
                    block_details="Estado nao encontrado, bloqueio preventivo",
                )
            else:
                logger.warning(f"Guardrail: estado nao encontrado para {cliente_id}, permitindo humano")
                return GuardrailResult(
                    decision=GuardrailDecision.ALLOWED,
                    origin=origin,
                    cliente_id=cliente_id,
                )

        now = datetime.utcnow()

        # 1. Verificar opted_out (TERMINAL - bypass permitido para humanos)
        if state.permission_state == PermissionState.OPTED_OUT:
            if origin.allows_bypass and bypass_reason and bypass_by:
                # Bypass permitido, mas sempre com auditoria
                result = GuardrailResult(
                    decision=GuardrailDecision.BYPASSED,
                    origin=origin,
                    cliente_id=cliente_id,
                    block_reason=BlockReason.OPTED_OUT,
                    block_details="Medico fez opt-out (bypass autorizado)",
                    bypass_reason=bypass_reason,
                    bypass_by=bypass_by,
                )
                await _emit_bypass_event(result, campanha_id)
                return result
            else:
                result = GuardrailResult(
                    decision=GuardrailDecision.BLOCKED,
                    origin=origin,
                    cliente_id=cliente_id,
                    block_reason=BlockReason.OPTED_OUT,
                    block_details="Medico fez opt-out, contato proibido",
                )
                await _emit_blocked_event(result, campanha_id)
                return result

        # 2. Verificar cooling_off (SEM bypass)
        if state.permission_state == PermissionState.COOLING_OFF:
            until_str = ""
            if state.cooling_off_until:
                until_str = f" ate {state.cooling_off_until.isoformat()}"
            result = GuardrailResult(
                decision=GuardrailDecision.BLOCKED,
                origin=origin,
                cliente_id=cliente_id,
                block_reason=BlockReason.COOLING_OFF,
                block_details=f"Medico em cooling_off{until_str}",
            )
            await _emit_blocked_event(result, campanha_id)
            return result

        # 3. Verificar next_allowed_at (SEM bypass)
        if state.next_allowed_at and now < state.next_allowed_at:
            result = GuardrailResult(
                decision=GuardrailDecision.BLOCKED,
                origin=origin,
                cliente_id=cliente_id,
                block_reason=BlockReason.NEXT_ALLOWED,
                block_details=f"Proximo contato permitido em {state.next_allowed_at.isoformat()}",
            )
            await _emit_blocked_event(result, campanha_id)
            return result

        # 4. Verificar limite de contatos (SEM bypass)
        if state.contact_count_7d >= MAX_CONTACTS_7D:
            result = GuardrailResult(
                decision=GuardrailDecision.BLOCKED,
                origin=origin,
                cliente_id=cliente_id,
                block_reason=BlockReason.CONTACT_LIMIT,
                block_details=f"Limite de {MAX_CONTACTS_7D} contatos/semana atingido ({state.contact_count_7d})",
            )
            await _emit_blocked_event(result, campanha_id)
            return result

        # Passou em todas as verificacoes
        return GuardrailResult(
            decision=GuardrailDecision.ALLOWED,
            origin=origin,
            cliente_id=cliente_id,
        )

    except Exception as e:
        logger.error(f"Erro ao verificar guardrails para {cliente_id}: {e}")
        # Em caso de erro, SEMPRE bloqueia para automaticos
        return GuardrailResult(
            decision=GuardrailDecision.BLOCKED,
            origin=origin,
            cliente_id=cliente_id,
            block_reason=BlockReason.OPTED_OUT,  # Conservador
            block_details=f"Erro ao verificar guardrails: {str(e)}",
        )


async def _emit_blocked_event(
    result: GuardrailResult,
    campanha_id: Optional[str] = None
) -> None:
    """Emite evento de campanha bloqueada."""
    try:
        await emit_event(
            event_type="campaign_blocked",
            cliente_id=result.cliente_id,
            data={
                "origin": result.origin.value,
                "block_reason": result.block_reason.value if result.block_reason else "unknown",
                "block_details": result.block_details,
                "campanha_id": campanha_id,
                "checked_at": result.checked_at.isoformat(),
            }
        )
        logger.info(
            f"Campanha bloqueada: cliente={result.cliente_id}, "
            f"origin={result.origin.value}, reason={result.block_reason.value if result.block_reason else 'unknown'}"
        )
    except Exception as e:
        logger.error(f"Erro ao emitir evento campaign_blocked: {e}")


async def _emit_bypass_event(
    result: GuardrailResult,
    campanha_id: Optional[str] = None
) -> None:
    """Emite evento de bypass de guardrail (auditoria)."""
    try:
        await emit_event(
            event_type="guardrail_bypassed",
            cliente_id=result.cliente_id,
            data={
                "origin": result.origin.value,
                "block_reason": result.block_reason.value if result.block_reason else "unknown",
                "bypass_reason": result.bypass_reason,
                "bypass_by": result.bypass_by,
                "campanha_id": campanha_id,
                "checked_at": result.checked_at.isoformat(),
            }
        )
        logger.warning(
            f"GUARDRAIL BYPASS: cliente={result.cliente_id}, "
            f"by={result.bypass_by}, reason={result.bypass_reason}"
        )
    except Exception as e:
        logger.error(f"Erro ao emitir evento guardrail_bypassed: {e}")


# Funcoes auxiliares para compatibilidade
async def can_send_campaign_message(
    cliente_id: str,
    campanha_id: Optional[str] = None,
) -> GuardrailResult:
    """
    Compatibilidade: verifica se pode enviar campanha.

    Usa origin=CAMPAIGN (sem bypass).
    """
    return await can_send_outbound(
        cliente_id=cliente_id,
        origin=OutboundOrigin.CAMPAIGN,
        campanha_id=campanha_id,
    )


async def check_opted_out(cliente_id: str) -> bool:
    """Verifica se cliente fez opt-out."""
    state = await load_doctor_state(cliente_id)
    if not state:
        return False
    return state.permission_state == PermissionState.OPTED_OUT


async def check_cooling_off(cliente_id: str) -> bool:
    """Verifica se cliente esta em cooling_off."""
    state = await load_doctor_state(cliente_id)
    if not state:
        return False
    return state.permission_state == PermissionState.COOLING_OFF
```

---

## Modulo __init__.py

```python
# app/services/guardrails/__init__.py

"""
Guardrails - Camada de protecao impossivel de burlar.

Sprint 18 - Data Integrity
"""

from .types import (
    GuardrailResult, GuardrailDecision, BlockReason,
    OutboundOrigin,
)
from .campaign import (
    can_send_outbound,
    can_send_campaign_message,
    check_opted_out,
    check_cooling_off,
    MAX_CONTACTS_7D,
)

__all__ = [
    # Types
    "GuardrailResult",
    "GuardrailDecision",
    "BlockReason",
    "OutboundOrigin",
    # Functions
    "can_send_outbound",
    "can_send_campaign_message",
    "check_opted_out",
    "check_cooling_off",
    "MAX_CONTACTS_7D",
]
```

---

## Integracao: campanha.py

```python
# Modificar app/services/campanha.py

from app.services.guardrails import can_send_outbound, OutboundOrigin

async def enviar_mensagem_prospeccao(
    cliente_id: str,
    telefone: str,
    nome: str,
    campanha_id: str = None,
    usar_aberturas_variadas: bool = True
) -> dict:
    """Envia mensagem de prospeccao com abertura variada."""

    # GUARDRAIL: Verificar ANTES de gerar texto ou qualquer operacao
    guardrail = await can_send_outbound(
        cliente_id=cliente_id,
        origin=OutboundOrigin.CAMPAIGN,
        campanha_id=campanha_id,
    )

    if not guardrail.allowed:
        logger.warning(
            f"Prospeccao bloqueada: cliente={cliente_id}, "
            f"reason={guardrail.block_reason.value if guardrail.block_reason else 'unknown'}"
        )
        return {
            "success": False,
            "blocked": True,
            "block_reason": guardrail.block_reason.value if guardrail.block_reason else None,
            "block_details": guardrail.block_details,
        }

    # Agora sim, gerar texto e enviar
    # ... resto do codigo existente ...
```

---

## Integracao: fila_mensagens.py

```python
# Modificar app/services/fila_mensagens.py

from app.services.guardrails import can_send_outbound, OutboundOrigin

async def processar_fila_mensagens():
    """Job que processa mensagens agendadas."""

    for msg in response.data:
        try:
            # ... buscar conversa e cliente ...

            # GUARDRAIL: Verificar ANTES de enviar
            guardrail = await can_send_outbound(
                cliente_id=cliente_id,
                origin=OutboundOrigin.AI_FOLLOWUP,
            )

            if not guardrail.allowed:
                logger.info(
                    f"Mensagem {msg['id']} bloqueada: {guardrail.block_reason.value}"
                )
                supabase.table("fila_mensagens").update({
                    "status": "bloqueada",
                    "erro": f"Guardrail: {guardrail.block_details}"
                }).eq("id", msg["id"]).execute()
                continue

            # Agora sim, enviar
            # ... resto do processamento ...
```

---

## Integracao: agente.py (reativacao)

```python
# Modificar app/services/agente.py

from app.services.guardrails import can_send_outbound, OutboundOrigin

async def processar_reativacao(cliente_id: str, mensagem: str):
    """Processa reativacao automatica."""

    # GUARDRAIL: Verificar ANTES de qualquer coisa
    guardrail = await can_send_outbound(
        cliente_id=cliente_id,
        origin=OutboundOrigin.AI_REACTIVATION,
    )

    if not guardrail.allowed:
        logger.info(f"Reativacao bloqueada para {cliente_id}: {guardrail.block_reason}")
        return {"blocked": True, "reason": guardrail.block_details}

    # Agora sim, processar reativacao
    # ...
```

---

## Integracao: Slack (com bypass)

```python
# app/tools/slack/mensagens.py

from app.services.guardrails import can_send_outbound, OutboundOrigin

async def enviar_mensagem_via_slack(
    cliente_id: str,
    mensagem: str,
    operador: str,
    bypass_optout: bool = False,
    bypass_reason: str = None,
):
    """Envia mensagem via comando Slack (operador humano)."""

    # GUARDRAIL: Verificar, mas permitir bypass para humanos
    guardrail = await can_send_outbound(
        cliente_id=cliente_id,
        origin=OutboundOrigin.SLACK_OPS,
        bypass_reason=bypass_reason if bypass_optout else None,
        bypass_by=operador if bypass_optout else None,
    )

    if not guardrail.allowed:
        if guardrail.block_reason == BlockReason.OPTED_OUT and not bypass_optout:
            # Informar operador que pode fazer bypass
            return {
                "blocked": True,
                "can_bypass": True,
                "message": f"Medico fez opt-out. Use --bypass com motivo para enviar mesmo assim.",
            }
        else:
            return {
                "blocked": True,
                "can_bypass": False,
                "message": guardrail.block_details,
            }

    if guardrail.was_bypassed:
        logger.warning(f"BYPASS por {operador}: {bypass_reason}")

    # Enviar mensagem
    # ...
```

---

## Testes

```python
# tests/guardrails/test_campaign.py

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from app.services.guardrails.types import (
    GuardrailResult, GuardrailDecision, BlockReason, OutboundOrigin
)
from app.services.guardrails.campaign import (
    can_send_outbound, MAX_CONTACTS_7D,
)
from app.services.policy.types import DoctorState, PermissionState


class TestCanSendOutbound:
    """Testes para can_send_outbound."""

    @pytest.mark.asyncio
    async def test_allows_active_for_campaign(self):
        """Permite campanha para medico ativo."""
        state = DoctorState(
            cliente_id="test-123",
            permission_state=PermissionState.ACTIVE,
            contact_count_7d=2,
        )
        with patch("app.services.guardrails.campaign.load_doctor_state", new_callable=AsyncMock, return_value=state):
            result = await can_send_outbound("test-123", OutboundOrigin.CAMPAIGN)

            assert result.decision == GuardrailDecision.ALLOWED
            assert result.allowed is True

    @pytest.mark.asyncio
    async def test_blocks_opted_out_for_campaign(self):
        """Bloqueia campanha para medico opted_out."""
        state = DoctorState(
            cliente_id="test-123",
            permission_state=PermissionState.OPTED_OUT,
        )
        with patch("app.services.guardrails.campaign.load_doctor_state", new_callable=AsyncMock, return_value=state), \
             patch("app.services.guardrails.campaign.emit_event", new_callable=AsyncMock):
            result = await can_send_outbound("test-123", OutboundOrigin.CAMPAIGN)

            assert result.decision == GuardrailDecision.BLOCKED
            assert result.block_reason == BlockReason.OPTED_OUT
            assert result.allowed is False

    @pytest.mark.asyncio
    async def test_allows_bypass_for_slack_ops_with_reason(self):
        """Permite bypass para slack_ops com motivo."""
        state = DoctorState(
            cliente_id="test-123",
            permission_state=PermissionState.OPTED_OUT,
        )
        with patch("app.services.guardrails.campaign.load_doctor_state", new_callable=AsyncMock, return_value=state), \
             patch("app.services.guardrails.campaign.emit_event", new_callable=AsyncMock) as mock_emit:
            result = await can_send_outbound(
                "test-123",
                OutboundOrigin.SLACK_OPS,
                bypass_reason="Medico ligou pedindo vaga urgente",
                bypass_by="operador@empresa.com",
            )

            assert result.decision == GuardrailDecision.BYPASSED
            assert result.allowed is True
            assert result.was_bypassed is True
            assert result.bypass_by == "operador@empresa.com"
            # Deve ter emitido guardrail_bypassed
            mock_emit.assert_called_once()

    @pytest.mark.asyncio
    async def test_blocks_slack_ops_without_bypass_params(self):
        """Bloqueia slack_ops se nao informar bypass params."""
        state = DoctorState(
            cliente_id="test-123",
            permission_state=PermissionState.OPTED_OUT,
        )
        with patch("app.services.guardrails.campaign.load_doctor_state", new_callable=AsyncMock, return_value=state), \
             patch("app.services.guardrails.campaign.emit_event", new_callable=AsyncMock):
            result = await can_send_outbound("test-123", OutboundOrigin.SLACK_OPS)

            # Sem bypass_reason e bypass_by, deve bloquear
            assert result.decision == GuardrailDecision.BLOCKED

    @pytest.mark.asyncio
    async def test_no_bypass_for_cooling_off(self):
        """Nao permite bypass para cooling_off."""
        state = DoctorState(
            cliente_id="test-123",
            permission_state=PermissionState.COOLING_OFF,
            cooling_off_until=datetime.utcnow() + timedelta(days=7),
        )
        with patch("app.services.guardrails.campaign.load_doctor_state", new_callable=AsyncMock, return_value=state), \
             patch("app.services.guardrails.campaign.emit_event", new_callable=AsyncMock):
            result = await can_send_outbound(
                "test-123",
                OutboundOrigin.SLACK_OPS,
                bypass_reason="Tentando bypass",
                bypass_by="operador@empresa.com",
            )

            # Cooling_off nao tem bypass
            assert result.decision == GuardrailDecision.BLOCKED
            assert result.block_reason == BlockReason.COOLING_OFF


class TestOutboundOrigin:
    """Testes para OutboundOrigin."""

    def test_campaign_not_allows_bypass(self):
        assert OutboundOrigin.CAMPAIGN.allows_bypass is False

    def test_ai_followup_not_allows_bypass(self):
        assert OutboundOrigin.AI_FOLLOWUP.allows_bypass is False

    def test_slack_ops_allows_bypass(self):
        assert OutboundOrigin.SLACK_OPS.allows_bypass is True

    def test_human_console_allows_bypass(self):
        assert OutboundOrigin.HUMAN_CONSOLE.allows_bypass is True

    def test_campaign_is_automated(self):
        assert OutboundOrigin.CAMPAIGN.is_automated is True

    def test_slack_ops_not_automated(self):
        assert OutboundOrigin.SLACK_OPS.is_automated is False
```

---

## Metricas de Sucesso

| Metrica | Meta | Como Medir |
|---------|------|------------|
| Bloqueios opted_out | 100% | Zero mensagens automaticas para opted_out |
| Eventos campaign_blocked | 100% capturados | Query em business_events |
| Eventos guardrail_bypassed | 100% auditados | Query em business_events |
| Bypasses com motivo | 100% | Todos os bypasses tem bypass_reason |

---

## Checklist de Implementacao

### Estrutura
- [ ] Criar `app/services/guardrails/types.py` com OutboundOrigin
- [ ] Criar `app/services/guardrails/campaign.py` com can_send_outbound
- [ ] Criar `app/services/guardrails/__init__.py`

### Integracoes
- [ ] Integrar em `app/services/campanha.py` (origin=CAMPAIGN)
- [ ] Integrar em `app/services/fila_mensagens.py` (origin=AI_FOLLOWUP)
- [ ] Integrar em `app/services/agente.py` (origin=AI_REACTIVATION)
- [ ] Integrar em `app/tools/slack/` (origin=SLACK_OPS com bypass)

### Testes
- [ ] Testar bloqueio para cada origin
- [ ] Testar bypass para slack_ops/human_console
- [ ] Testar que bypass sem params e bloqueado
- [ ] Testar emissao de eventos de auditoria

### Validacao
- [ ] Testar com medico opted_out real
- [ ] Verificar eventos campaign_blocked e guardrail_bypassed
- [ ] Confirmar que automaticos NUNCA passam para opted_out
