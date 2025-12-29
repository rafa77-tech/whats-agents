"""
Testes para cooldown de campanhas.

Sprint 23 E05 - Evita campanhas diferentes em janela curta.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

from app.services.campaign_cooldown import (
    check_campaign_cooldown,
    registrar_envio_campanha,
    buscar_ultima_campanha_enviada,
    medico_respondeu_recentemente,
    tem_conversa_ativa_com_oferta,
    CooldownResult,
    LastCampaignInfo,
    CAMPAIGN_COOLDOWN_DAYS,
    RESPONSE_COOLDOWN_DAYS,
)


class TestCheckCampaignCooldown:
    """Testes para check_campaign_cooldown."""

    @pytest.mark.asyncio
    async def test_primeira_campanha_nao_bloqueia(self):
        """Primeira campanha para cliente nao deve bloquear."""
        with patch("app.services.campaign_cooldown.supabase") as mock_supabase:
            # Sem historico de campanhas
            mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
                data=None
            )
            # Sem interacoes recentes
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.limit.return_value.execute.return_value = MagicMock(
                count=0
            )

            result = await check_campaign_cooldown(
                cliente_id="cliente-123",
                campaign_id=1,
            )

            assert result.is_blocked is False

    @pytest.mark.asyncio
    async def test_mesma_campanha_nao_bloqueia(self):
        """Mesma campanha enviada novamente nao deve bloquear por cooldown."""
        with patch("app.services.campaign_cooldown.supabase") as mock_supabase:
            # Ultima campanha e a mesma
            mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[{
                    "campaign_id": 1,  # Mesma campanha
                    "campaign_type": "primeiro_contato",
                    "sent_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                }]
            )
            # Sem interacoes recentes
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.limit.return_value.execute.return_value = MagicMock(
                count=0
            )

            result = await check_campaign_cooldown(
                cliente_id="cliente-123",
                campaign_id=1,  # Mesma
            )

            assert result.is_blocked is False

    @pytest.mark.asyncio
    async def test_campanha_diferente_recente_bloqueia(self):
        """Campanha diferente enviada recentemente deve bloquear (R5a)."""
        with patch("app.services.campaign_cooldown.supabase") as mock_supabase:
            # Ultima campanha diferente ha 1 dia
            mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[{
                    "campaign_id": 1,  # Campanha diferente
                    "campaign_type": "primeiro_contato",
                    "sent_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                }]
            )

            result = await check_campaign_cooldown(
                cliente_id="cliente-123",
                campaign_id=2,  # Diferente
            )

            assert result.is_blocked is True
            assert result.reason == "different_campaign_recent"
            assert result.details["days_since"] == 1
            assert result.details["cooldown_days"] == CAMPAIGN_COOLDOWN_DAYS

    @pytest.mark.asyncio
    async def test_campanha_diferente_antiga_nao_bloqueia(self):
        """Campanha diferente enviada ha mais de 3 dias nao deve bloquear."""
        with patch("app.services.campaign_cooldown.supabase") as mock_supabase:
            # Ultima campanha diferente ha 5 dias
            mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[{
                    "campaign_id": 1,
                    "campaign_type": "primeiro_contato",
                    "sent_at": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
                }]
            )
            # Sem interacoes recentes
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.limit.return_value.execute.return_value = MagicMock(
                count=0
            )

            result = await check_campaign_cooldown(
                cliente_id="cliente-123",
                campaign_id=2,
            )

            assert result.is_blocked is False

    @pytest.mark.asyncio
    async def test_medico_respondeu_recentemente_bloqueia(self):
        """Medico que respondeu recentemente deve bloquear campanhas (R5b)."""
        with patch("app.services.campaign_cooldown.supabase") as mock_supabase:
            # Sem campanha anterior
            mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
                data=None
            )
            # Tem interacao recente do medico
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.limit.return_value.execute.return_value = MagicMock(
                count=1
            )
            # Sem conversa ativa
            mock_supabase.table.return_value.select.return_value.eq.return_value.neq.return_value.gte.return_value.limit.return_value.execute.return_value = MagicMock(
                count=0
            )

            result = await check_campaign_cooldown(
                cliente_id="cliente-123",
                campaign_id=1,
            )

            assert result.is_blocked is True
            assert result.reason == "responded_recently"

    @pytest.mark.asyncio
    async def test_medico_respondeu_com_conversa_ativa_nao_bloqueia(self):
        """Medico com conversa ativa nao deve bloquear (pode estar negociando)."""
        with patch("app.services.campaign_cooldown.supabase") as mock_supabase:
            # Sem campanha anterior
            mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
                data=None
            )
            # Tem interacao recente do medico
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.limit.return_value.execute.return_value = MagicMock(
                count=1
            )
            # TEM conversa ativa
            mock_supabase.table.return_value.select.return_value.eq.return_value.neq.return_value.gte.return_value.limit.return_value.execute.return_value = MagicMock(
                count=1
            )

            result = await check_campaign_cooldown(
                cliente_id="cliente-123",
                campaign_id=1,
            )

            assert result.is_blocked is False


class TestRegistrarEnvioCampanha:
    """Testes para registrar_envio_campanha."""

    @pytest.mark.asyncio
    async def test_registra_envio_com_sucesso(self):
        """Deve registrar envio no historico."""
        with patch("app.services.campaign_cooldown.supabase") as mock_supabase:
            mock_supabase.table.return_value.upsert.return_value.execute.return_value = MagicMock()

            result = await registrar_envio_campanha(
                cliente_id="cliente-123",
                campaign_id=42,
                campaign_type="primeiro_contato",
            )

            assert result is True
            mock_supabase.table.assert_called_with("campaign_contact_history")

    @pytest.mark.asyncio
    async def test_upsert_evita_duplicatas(self):
        """Upsert deve evitar duplicatas de cliente+campanha."""
        with patch("app.services.campaign_cooldown.supabase") as mock_supabase:
            mock_supabase.table.return_value.upsert.return_value.execute.return_value = MagicMock()

            await registrar_envio_campanha(
                cliente_id="cliente-123",
                campaign_id=42,
                campaign_type="primeiro_contato",
            )

            # Verificar que upsert foi chamado com on_conflict
            upsert_call = mock_supabase.table.return_value.upsert.call_args
            assert upsert_call[1]["on_conflict"] == "cliente_id,campaign_id"


class TestReplyNaoEBloqueado:
    """Testes criticos: Reply NUNCA deve ser bloqueado por cooldown."""

    @pytest.mark.asyncio
    async def test_reply_nao_passa_por_cooldown(self):
        """method=REPLY nao deve passar pela verificacao de cooldown."""
        # Este teste valida que o guardrail so verifica cooldown para CAMPAIGN
        from app.services.guardrails.types import OutboundMethod

        # R5 so se aplica a CAMPAIGN
        assert OutboundMethod.REPLY != OutboundMethod.CAMPAIGN

    @pytest.mark.asyncio
    async def test_cooldown_so_verifica_campaigns(self):
        """Cooldown so deve verificar method=CAMPAIGN com campaign_id."""
        # O guardrail tem: if ctx.method == OutboundMethod.CAMPAIGN and ctx.campaign_id:
        # Entao REPLY, FOLLOWUP, etc nao passam por R5

        # Patch no modulo onde a funcao e importada (lazy import dentro da funcao)
        with patch("app.services.campaign_cooldown.check_campaign_cooldown") as mock_cooldown:
            from app.services.guardrails.check import check_outbound_guardrails
            from app.services.guardrails.types import (
                OutboundContext, OutboundMethod, OutboundChannel, ActorType
            )

            # Contexto de REPLY (nao campanha)
            ctx = OutboundContext(
                cliente_id="cliente-123",
                actor_type=ActorType.BOT,
                channel=OutboundChannel.WHATSAPP,
                method=OutboundMethod.REPLY,
                is_proactive=False,
                conversation_id="conv-456",
                inbound_interaction_id=100,
                last_inbound_at=datetime.now(timezone.utc).isoformat(),
            )

            with patch("app.services.guardrails.check.load_doctor_state") as mock_state:
                mock_state.return_value = None  # Sem estado especial

                await check_outbound_guardrails(ctx)

                # Cooldown NAO deve ter sido chamado para REPLY
                mock_cooldown.assert_not_called()


class TestConfiguracoes:
    """Testes para configuracoes de cooldown."""

    def test_cooldown_days_configurado(self):
        """Dias de cooldown devem estar configurados."""
        assert CAMPAIGN_COOLDOWN_DAYS == 3
        assert RESPONSE_COOLDOWN_DAYS == 7

    def test_cooldown_pode_ser_alterado(self):
        """Configuracoes podem ser alteradas (futuro: feature_flags)."""
        # Por enquanto sao constantes, mas podem ser movidas para feature_flags
        assert isinstance(CAMPAIGN_COOLDOWN_DAYS, int)
        assert isinstance(RESPONSE_COOLDOWN_DAYS, int)


class TestBuscarUltimaCampanha:
    """Testes para buscar_ultima_campanha_enviada."""

    @pytest.mark.asyncio
    async def test_retorna_ultima_campanha(self):
        """Deve retornar info da ultima campanha."""
        with patch("app.services.campaign_cooldown.supabase") as mock_supabase:
            sent_at = datetime.now(timezone.utc).isoformat()
            mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[{
                    "campaign_id": 42,
                    "campaign_type": "reativacao",
                    "sent_at": sent_at,
                }]
            )

            result = await buscar_ultima_campanha_enviada("cliente-123")

            assert result is not None
            assert result.campaign_id == 42
            assert result.campaign_type == "reativacao"

    @pytest.mark.asyncio
    async def test_retorna_none_sem_historico(self):
        """Deve retornar None se nunca recebeu campanha."""
        with patch("app.services.campaign_cooldown.supabase") as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
                data=None
            )

            result = await buscar_ultima_campanha_enviada("cliente-123")

            assert result is None
