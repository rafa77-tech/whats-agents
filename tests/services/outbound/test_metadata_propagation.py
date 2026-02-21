"""
Testes de propagacao de metadata no pipeline outbound.

Sprint 70 — Epic 70.1: Verifica que meta_template info
flui de fila_mensagens.metadata ate enviar_via_chip(template_info).
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.guardrails.types import (
    OutboundContext,
    OutboundChannel,
    OutboundMethod,
    ActorType,
)
from app.services.outbound.context_factories import criar_contexto_campanha


class TestOutboundContextMetadata:
    """Testa que OutboundContext aceita e armazena metadata."""

    def test_metadata_default_none(self):
        ctx = OutboundContext(
            cliente_id="c1",
            actor_type=ActorType.SYSTEM,
            channel=OutboundChannel.JOB,
            method=OutboundMethod.CAMPAIGN,
            is_proactive=True,
        )
        assert ctx.metadata is None

    def test_metadata_com_template(self):
        meta = {"meta_template": {"name": "oferta_plantao", "language": "pt_BR"}}
        ctx = OutboundContext(
            cliente_id="c1",
            actor_type=ActorType.SYSTEM,
            channel=OutboundChannel.JOB,
            method=OutboundMethod.CAMPAIGN,
            is_proactive=True,
            metadata=meta,
        )
        assert ctx.metadata is not None
        assert ctx.metadata["meta_template"]["name"] == "oferta_plantao"

    def test_hasattr_metadata_sempre_true(self):
        """Verifica que hasattr(ctx, 'metadata') retorna True (fix do bug)."""
        ctx = OutboundContext(
            cliente_id="c1",
            actor_type=ActorType.SYSTEM,
            channel=OutboundChannel.JOB,
            method=OutboundMethod.CAMPAIGN,
            is_proactive=True,
        )
        assert hasattr(ctx, "metadata")


class TestCriarContextoCampanhaMetadata:
    """Testa que criar_contexto_campanha propaga metadata."""

    def test_sem_metadata(self):
        ctx = criar_contexto_campanha(
            cliente_id="c1",
            campaign_id="camp1",
        )
        assert ctx.metadata is None

    def test_com_metadata(self):
        meta = {
            "campanha_id": "camp1",
            "meta_template": {
                "name": "oferta_plantao",
                "language": "pt_BR",
                "components": [{"type": "body", "parameters": []}],
            },
        }
        ctx = criar_contexto_campanha(
            cliente_id="c1",
            campaign_id="camp1",
            metadata=meta,
        )
        assert ctx.metadata is not None
        assert ctx.metadata["meta_template"]["name"] == "oferta_plantao"
        assert ctx.campaign_id == "camp1"


class TestMultiChipTemplateExtraction:
    """Testa que multi_chip.py extrai template_info da metadata do contexto."""

    @pytest.mark.asyncio
    async def test_template_info_extraido_da_metadata(self):
        """Pipeline: ctx.metadata.meta_template -> enviar_via_chip(template_info)."""
        meta_template = {
            "name": "oferta_plantao_v2",
            "language": "pt_BR",
            "components": [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": "Dr. Silva"}],
                }
            ],
        }
        ctx = criar_contexto_campanha(
            cliente_id="c1",
            campaign_id="camp1",
            conversation_id="conv1",
            metadata={"campanha_id": "camp1", "meta_template": meta_template},
        )

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.message_id = "wamid.123"
        mock_result.provider = "meta"

        mock_chip = {
            "id": "chip1",
            "telefone": "5511999990001",
            "provider": "meta",
            "meta_phone_number_id": "123",
            "meta_access_token": "tok",
        }

        mock_selector = AsyncMock()
        mock_selector.selecionar_chip = AsyncMock(return_value=mock_chip)
        mock_selector.registrar_envio = AsyncMock()

        with (
            patch(
                "app.services.chips.selector.chip_selector",
                mock_selector,
            ),
            patch(
                "app.services.chips.sender.enviar_via_chip",
                new_callable=AsyncMock,
            ) as mock_enviar,
        ):
            mock_enviar.return_value = mock_result

            from app.services.outbound.multi_chip import _enviar_via_multi_chip

            result = await _enviar_via_multi_chip(
                telefone="5511999998888",
                texto="Oi Dr!",
                ctx=ctx,
            )

            # Verifica que enviar_via_chip foi chamado com template_info correto
            mock_enviar.assert_called_once()
            call_kwargs = mock_enviar.call_args
            assert call_kwargs[1]["template_info"] == meta_template

    @pytest.mark.asyncio
    async def test_sem_metadata_template_info_none(self):
        """Sem metadata, template_info deve ser None."""
        ctx = criar_contexto_campanha(
            cliente_id="c1",
            campaign_id="camp1",
            conversation_id="conv1",
        )

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.message_id = "wamid.456"
        mock_result.provider = "evolution"

        mock_chip = {
            "id": "chip2",
            "telefone": "5511999990002",
            "provider": "evolution",
        }

        mock_selector = AsyncMock()
        mock_selector.selecionar_chip = AsyncMock(return_value=mock_chip)
        mock_selector.registrar_envio = AsyncMock()

        with (
            patch(
                "app.services.chips.selector.chip_selector",
                mock_selector,
            ),
            patch(
                "app.services.chips.sender.enviar_via_chip",
                new_callable=AsyncMock,
            ) as mock_enviar,
        ):
            mock_enviar.return_value = mock_result

            from app.services.outbound.multi_chip import _enviar_via_multi_chip

            await _enviar_via_multi_chip(
                telefone="5511999998888",
                texto="Oi Dr!",
                ctx=ctx,
            )

            call_kwargs = mock_enviar.call_args
            assert call_kwargs[1]["template_info"] is None
