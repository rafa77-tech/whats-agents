"""
Teste de integração: Campanha -> Meta Template E2E.

Sprint 70 — Epic 70.3: Verifica o fluxo completo:
  campanha com meta_template_name
  -> fila_mensagens.metadata
  -> fila_worker cria contexto com metadata
  -> multi_chip extrai template_info
  -> chip sender envia via provider.send_template()

Também testa auto-template selection quando sem template explícito.
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
from app.services.whatsapp_providers.base import MessageResult


class TestCampaignMetaE2EFlow:
    """Testa fluxo completo: campanha → fila → ctx.metadata → sender → Graph API."""

    @pytest.mark.asyncio
    async def test_fluxo_completo_com_template_explicito(self):
        """
        Simula o fluxo:
        1. fila_mensagens tem metadata com meta_template
        2. fila_worker passa metadata para criar_contexto_campanha
        3. multi_chip extrai template_info
        4. sender chama provider.send_template
        """
        # 1. Simular dados da fila_mensagens (como o worker recebe)
        mensagem_fila = {
            "id": "msg-001",
            "cliente_id": "cli-001",
            "conteudo": "Oi Dr! Temos uma vaga pra vc",
            "conversa_id": "conv-001",
            "metadata": {
                "campanha_id": "camp-001",
                "meta_template": {
                    "name": "oferta_plantao_v2",
                    "language": "pt_BR",
                    "components": [
                        {
                            "type": "body",
                            "parameters": [
                                {"type": "text", "text": "Dr. Silva"},
                                {"type": "text", "text": "São Luiz Jabaquara"},
                            ],
                        }
                    ],
                },
            },
            "clientes": {"telefone": "5511999998888"},
        }

        # 2. Worker cria contexto (simulando fila_worker.py L192-198)
        metadata = mensagem_fila.get("metadata", {})
        campaign_id = metadata.get("campanha_id")
        ctx = criar_contexto_campanha(
            cliente_id=mensagem_fila["cliente_id"],
            campaign_id=campaign_id,
            conversation_id=mensagem_fila["conversa_id"],
            metadata=metadata,
        )

        # Verificar que metadata está no contexto
        assert ctx.metadata is not None
        assert ctx.metadata["meta_template"]["name"] == "oferta_plantao_v2"

        # 3. Simular multi_chip extraindo template_info (como multi_chip.py L122-124)
        template_info = None
        if hasattr(ctx, "metadata") and ctx.metadata:
            template_info = ctx.metadata.get("meta_template")

        assert template_info is not None
        assert template_info["name"] == "oferta_plantao_v2"

        # 4. Simular sender chamando provider
        mock_provider = AsyncMock()
        mock_provider.send_template.return_value = MessageResult(
            success=True, message_id="wamid.abc123", provider="meta"
        )

        chip = {
            "id": "chip-meta-1",
            "telefone": "5511999990001",
            "provider": "meta",
            "meta_waba_id": "waba123",
        }

        with patch(
            "app.services.meta.window_tracker.window_tracker"
        ) as mock_tracker:
            mock_tracker.esta_na_janela = AsyncMock(return_value=False)

            from app.services.chips.sender import _enviar_meta_fallback

            result = await _enviar_meta_fallback(
                provider=mock_provider,
                chip=chip,
                telefone="5511999998888",
                texto="Oi Dr! Temos uma vaga pra vc",
                template_info=template_info,
            )

        assert result.success
        assert result.message_id == "wamid.abc123"
        mock_provider.send_template.assert_called_once_with(
            "5511999998888",
            "oferta_plantao_v2",
            "pt_BR",
            template_info["components"],
        )

    @pytest.mark.asyncio
    async def test_fluxo_sem_template_metadata_vazia(self):
        """Campanha sem meta_template na metadata — template_info é None."""
        metadata = {"campanha_id": "camp-002"}
        ctx = criar_contexto_campanha(
            cliente_id="cli-002",
            campaign_id="camp-002",
            metadata=metadata,
        )

        template_info = None
        if hasattr(ctx, "metadata") and ctx.metadata:
            template_info = ctx.metadata.get("meta_template")

        assert template_info is None

    @pytest.mark.asyncio
    async def test_fluxo_sem_metadata_nenhuma(self):
        """Campanha sem metadata (Evolution chip) — metadata é None."""
        ctx = criar_contexto_campanha(
            cliente_id="cli-003",
            campaign_id="camp-003",
        )

        template_info = None
        if hasattr(ctx, "metadata") and ctx.metadata:
            template_info = ctx.metadata.get("meta_template")

        assert template_info is None


class TestAutoTemplateSelection:
    """Testa auto-seleção de template quando sem template explícito."""

    @pytest.mark.asyncio
    async def test_auto_seleciona_template_marketing(self):
        """Quando cost_optimizer pede marketing_template e não há template_info,
        busca template APPROVED do banco."""
        from app.services.chips.sender import _buscar_template_auto

        fake_templates = [
            {
                "name": "promo_geral",
                "category": "MARKETING",
                "status": "APPROVED",
                "language": "pt_BR",
                "components": [{"type": "body", "text": "Promo!"}],
            },
            {
                "name": "confirmacao_plantao",
                "category": "UTILITY",
                "status": "APPROVED",
                "language": "pt_BR",
            },
        ]

        chip = {"id": "chip-1", "meta_waba_id": "waba123"}

        with patch(
            "app.services.meta.template_service.template_service"
        ) as mock_tmpl_svc:
            mock_tmpl_svc.listar_templates = AsyncMock(return_value=fake_templates)

            result = await _buscar_template_auto(chip, "marketing_template")

            assert result is not None
            assert result["name"] == "promo_geral"
            mock_tmpl_svc.listar_templates.assert_called_once_with(
                "waba123", status="APPROVED"
            )

    @pytest.mark.asyncio
    async def test_auto_seleciona_template_utility(self):
        """Busca template UTILITY quando cost_optimizer pede utility_template."""
        from app.services.chips.sender import _buscar_template_auto

        fake_templates = [
            {
                "name": "confirmacao_plantao",
                "category": "UTILITY",
                "status": "APPROVED",
                "language": "pt_BR",
                "components": [],
            },
        ]

        chip = {"id": "chip-1", "meta_waba_id": "waba123"}

        with patch(
            "app.services.meta.template_service.template_service"
        ) as mock_tmpl_svc:
            mock_tmpl_svc.listar_templates = AsyncMock(return_value=fake_templates)

            result = await _buscar_template_auto(chip, "utility_template")

            assert result is not None
            assert result["name"] == "confirmacao_plantao"

    @pytest.mark.asyncio
    async def test_auto_retorna_none_sem_templates(self):
        """Retorna None quando não há templates compatíveis."""
        from app.services.chips.sender import _buscar_template_auto

        chip = {"id": "chip-1", "meta_waba_id": "waba123"}

        with patch(
            "app.services.meta.template_service.template_service"
        ) as mock_tmpl_svc:
            mock_tmpl_svc.listar_templates = AsyncMock(return_value=[])

            result = await _buscar_template_auto(chip, "marketing_template")

            assert result is None

    @pytest.mark.asyncio
    async def test_auto_retorna_none_sem_waba_id(self):
        """Retorna None quando chip não tem meta_waba_id."""
        from app.services.chips.sender import _buscar_template_auto

        chip = {"id": "chip-1", "provider": "evolution"}

        result = await _buscar_template_auto(chip, "marketing_template")

        assert result is None
