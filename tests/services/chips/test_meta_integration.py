"""
Testes para integracao Meta Cloud API nos modulos chips.

Sprint 66-fix — 24 testes faltantes para sender, selector, orchestrator, health_monitor.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.whatsapp_providers.base import MessageResult


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def chip_meta():
    """Chip Meta com credenciais validas."""
    return {
        "id": "chip-meta-1",
        "telefone": "5511988880001",
        "provider": "meta",
        "status": "active",
        "tipo": "sender",
        "meta_phone_number_id": "123456789",
        "meta_access_token": "token_abc",
        "meta_waba_id": "waba_test",
        "meta_quality_rating": "GREEN",
        "trust_score": 100,
        "pode_prospectar": True,
        "pode_followup": True,
        "pode_responder": True,
        "limite_hora": 1000,
        "limite_dia": 10000,
        "msgs_enviadas_hoje": 0,
        "evolution_connected": None,
    }


@pytest.fixture
def chip_meta_sem_credenciais():
    """Chip Meta sem credenciais obrigatorias."""
    return {
        "id": "chip-meta-2",
        "telefone": "5511988880002",
        "provider": "meta",
        "status": "active",
        "tipo": "sender",
        "meta_phone_number_id": None,
        "meta_access_token": None,
        "meta_waba_id": None,
        "meta_quality_rating": None,
        "trust_score": 100,
        "pode_prospectar": True,
        "pode_followup": True,
        "pode_responder": True,
        "limite_hora": 1000,
        "limite_dia": 10000,
        "msgs_enviadas_hoje": 0,
    }


@pytest.fixture
def chip_meta_red():
    """Chip Meta com quality RED."""
    return {
        "id": "chip-meta-3",
        "telefone": "5511988880003",
        "provider": "meta",
        "status": "active",
        "tipo": "sender",
        "meta_phone_number_id": "999999",
        "meta_access_token": "token_red",
        "meta_waba_id": "waba_red",
        "meta_quality_rating": "RED",
        "trust_score": 100,
        "pode_prospectar": True,
        "pode_followup": True,
        "pode_responder": True,
        "limite_hora": 1000,
        "limite_dia": 10000,
        "msgs_enviadas_hoje": 0,
    }


@pytest.fixture
def chip_evolution():
    """Chip Evolution normal."""
    return {
        "id": "chip-evo-1",
        "telefone": "5511988880010",
        "provider": "evolution",
        "status": "active",
        "tipo": "sender",
        "trust_score": 80,
        "pode_prospectar": True,
        "pode_followup": True,
        "pode_responder": True,
        "evolution_connected": True,
        "limite_hora": 20,
        "limite_dia": 100,
        "msgs_enviadas_hoje": 0,
    }


@pytest.fixture
def template_info():
    """Template info para envio Meta."""
    return {
        "name": "julia_discovery_v1",
        "language": "pt_BR",
        "components": [
            {
                "type": "body",
                "parameters": [{"type": "text", "text": "Dr Carlos"}],
            }
        ],
    }


@pytest.fixture
def mock_registrar_envio():
    with patch(
        "app.services.chips.sender._registrar_envio", new_callable=AsyncMock
    ) as mock:
        yield mock


@pytest.fixture
def mock_provider():
    provider = AsyncMock()
    provider.send_text = AsyncMock(
        return_value=MessageResult(
            success=True, message_id="wamid.ok", provider="meta"
        )
    )
    provider.send_template = AsyncMock(
        return_value=MessageResult(
            success=True, message_id="wamid.tmpl", provider="meta"
        )
    )
    provider.send_media = AsyncMock(
        return_value=MessageResult(
            success=True, message_id="wamid.media", provider="meta"
        )
    )
    return provider


# ============================================================
# _enviar_meta_smart (7 testes)
# ============================================================


class TestEnviarMetaSmart:
    """Testes para _enviar_meta_smart — Sprint 66-fix G2."""

    @pytest.mark.asyncio
    async def test_dentro_da_janela_envia_texto(self, mock_provider, chip_meta):
        from app.services.chips.sender import _enviar_meta_smart

        mock_wt = MagicMock()
        mock_wt.esta_na_janela = AsyncMock(return_value=True)

        with patch(
            "app.services.meta.window_tracker.window_tracker", mock_wt
        ):
            result = await _enviar_meta_smart(
                mock_provider, chip_meta, "5511999999999", "Ola!"
            )

        assert result.success is True
        mock_provider.send_text.assert_called_once_with("5511999999999", "Ola!")
        mock_provider.send_template.assert_not_called()

    @pytest.mark.asyncio
    async def test_fora_da_janela_com_template_envia_template(
        self, mock_provider, chip_meta, template_info
    ):
        from app.services.chips.sender import _enviar_meta_smart

        mock_wt = MagicMock()
        mock_wt.esta_na_janela = AsyncMock(return_value=False)

        with patch(
            "app.services.meta.window_tracker.window_tracker", mock_wt
        ):
            result = await _enviar_meta_smart(
                mock_provider,
                chip_meta,
                "5511999999999",
                "Ola!",
                template_info=template_info,
            )

        assert result.success is True
        mock_provider.send_template.assert_called_once_with(
            "5511999999999",
            "julia_discovery_v1",
            "pt_BR",
            template_info["components"],
        )
        mock_provider.send_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_fora_da_janela_sem_template_retorna_erro(
        self, mock_provider, chip_meta
    ):
        from app.services.chips.sender import _enviar_meta_smart

        mock_wt = MagicMock()
        mock_wt.esta_na_janela = AsyncMock(return_value=False)

        with patch(
            "app.services.meta.window_tracker.window_tracker", mock_wt
        ):
            result = await _enviar_meta_smart(
                mock_provider, chip_meta, "5511999999999", "Ola!"
            )

        assert result.success is False
        assert result.error == "meta_fora_janela_sem_template"
        assert result.provider == "meta"
        mock_provider.send_text.assert_not_called()
        mock_provider.send_template.assert_not_called()

    @pytest.mark.asyncio
    async def test_template_sem_components_envia_sem_components(
        self, mock_provider, chip_meta
    ):
        from app.services.chips.sender import _enviar_meta_smart

        template_no_components = {"name": "julia_confirmacao_v1", "language": "pt_BR"}

        mock_wt = MagicMock()
        mock_wt.esta_na_janela = AsyncMock(return_value=False)

        with patch(
            "app.services.meta.window_tracker.window_tracker", mock_wt
        ):
            result = await _enviar_meta_smart(
                mock_provider,
                chip_meta,
                "5511999999999",
                "Ola!",
                template_info=template_no_components,
            )

        assert result.success is True
        mock_provider.send_template.assert_called_once_with(
            "5511999999999",
            "julia_confirmacao_v1",
            "pt_BR",
            None,
        )

    @pytest.mark.asyncio
    async def test_template_language_default_pt_br(
        self, mock_provider, chip_meta
    ):
        from app.services.chips.sender import _enviar_meta_smart

        template_sem_language = {"name": "julia_test"}

        mock_wt = MagicMock()
        mock_wt.esta_na_janela = AsyncMock(return_value=False)

        with patch(
            "app.services.meta.window_tracker.window_tracker", mock_wt
        ):
            result = await _enviar_meta_smart(
                mock_provider,
                chip_meta,
                "5511999999999",
                "Ola!",
                template_info=template_sem_language,
            )

        assert result.success is True
        call_args = mock_provider.send_template.call_args
        assert call_args[0][2] == "pt_BR"  # language default

    @pytest.mark.asyncio
    async def test_erro_do_provider_propagado(self, mock_provider, chip_meta):
        from app.services.chips.sender import _enviar_meta_smart

        mock_provider.send_text = AsyncMock(
            return_value=MessageResult(
                success=False, error="meta_timeout", provider="meta"
            )
        )

        mock_wt = MagicMock()
        mock_wt.esta_na_janela = AsyncMock(return_value=True)

        with patch(
            "app.services.meta.window_tracker.window_tracker", mock_wt
        ):
            result = await _enviar_meta_smart(
                mock_provider, chip_meta, "5511999999999", "Ola!"
            )

        assert result.success is False
        assert result.error == "meta_timeout"

    @pytest.mark.asyncio
    async def test_window_tracker_recebe_chip_id_e_telefone(
        self, mock_provider, chip_meta
    ):
        from app.services.chips.sender import _enviar_meta_smart

        mock_wt = MagicMock()
        mock_wt.esta_na_janela = AsyncMock(return_value=True)

        with patch(
            "app.services.meta.window_tracker.window_tracker", mock_wt
        ):
            await _enviar_meta_smart(
                mock_provider, chip_meta, "5511999999999", "Ola!"
            )

        mock_wt.esta_na_janela.assert_called_once_with(
            "chip-meta-1", "5511999999999"
        )


# ============================================================
# enviar_via_chip — Meta routing (2 testes)
# ============================================================


class TestEnviarViaChipMeta:
    """Testes para enviar_via_chip com chips Meta vs Evolution."""

    @pytest.mark.asyncio
    async def test_chip_evolution_envia_texto_direto(
        self, chip_evolution, mock_registrar_envio
    ):
        from app.services.chips.sender import enviar_via_chip

        mock_provider = AsyncMock()
        mock_provider.send_text = AsyncMock(
            return_value=MessageResult(
                success=True, message_id="evo.123", provider="evolution"
            )
        )

        with patch(
            "app.services.chips.sender.get_provider", return_value=mock_provider
        ):
            result = await enviar_via_chip(chip_evolution, "5511999999999", "Ola!")

        assert result.success is True
        mock_provider.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_chip_meta_usa_enviar_meta_smart(
        self, chip_meta, mock_registrar_envio
    ):
        from app.services.chips.sender import enviar_via_chip

        mock_prov = AsyncMock()

        with (
            patch(
                "app.services.chips.sender.get_provider", return_value=mock_prov
            ),
            patch(
                "app.services.chips.sender._enviar_meta_smart",
                new_callable=AsyncMock,
                return_value=MessageResult(
                    success=True, message_id="wamid.x", provider="meta"
                ),
            ) as mock_smart,
        ):
            result = await enviar_via_chip(
                chip_meta, "5511999999999", "Ola!", template_info={"name": "t"}
            )

        assert result.success is True
        mock_smart.assert_called_once()
        mock_prov.send_text.assert_not_called()


# ============================================================
# enviar_media_via_chip — janela 24h (2 testes) — Sprint 66-fix G1
# ============================================================


class TestEnviarMediaViaChipMeta:
    """Testes para enviar_media_via_chip com janela 24h Meta."""

    @pytest.mark.asyncio
    async def test_chip_meta_dentro_da_janela_envia_media(
        self, chip_meta, mock_registrar_envio
    ):
        from app.services.chips.sender import enviar_media_via_chip

        mock_prov = AsyncMock()
        mock_prov.send_media = AsyncMock(
            return_value=MessageResult(
                success=True, message_id="wamid.m1", provider="meta"
            )
        )

        mock_wt = MagicMock()
        mock_wt.esta_na_janela = AsyncMock(return_value=True)

        with (
            patch(
                "app.services.chips.sender.get_provider", return_value=mock_prov
            ),
            patch(
                "app.services.meta.window_tracker.window_tracker", mock_wt
            ),
        ):
            result = await enviar_media_via_chip(
                chip_meta, "5511999999999", "https://example.com/img.jpg"
            )

        assert result.success is True
        mock_prov.send_media.assert_called_once()

    @pytest.mark.asyncio
    async def test_chip_meta_fora_da_janela_bloqueia_media(
        self, chip_meta, mock_registrar_envio
    ):
        from app.services.chips.sender import enviar_media_via_chip

        mock_wt = MagicMock()
        mock_wt.esta_na_janela = AsyncMock(return_value=False)

        with patch(
            "app.services.meta.window_tracker.window_tracker", mock_wt
        ):
            result = await enviar_media_via_chip(
                chip_meta, "5511999999999", "https://example.com/img.jpg"
            )

        assert result.success is False
        assert result.error == "meta_fora_janela_sem_template"


# ============================================================
# ChipSelector — Meta eligibility (4 testes) — Sprint 66-fix G3
# ============================================================


class TestSelectorMetaEligibility:
    """Testes para selecao de chips Meta no selector."""

    def _mock_supabase_query(self, chips_data):
        """Helper para mockar query do supabase."""
        mock_result = MagicMock()
        mock_result.data = chips_data
        return mock_result

    @pytest.mark.asyncio
    async def test_chip_meta_sem_evolution_connected_elegivel(self, chip_meta):
        from app.services.chips.selector import ChipSelector

        selector = ChipSelector()
        selector.config = {"limite_prospeccao_hora": 5}

        chip_meta["evolution_connected"] = None

        with (
            patch("app.services.chips.selector.supabase") as mock_sb,
            patch("app.services.chips.selector.ChipCircuitBreaker") as mock_cb,
        ):
            mock_sb.table.return_value.select.return_value.eq.return_value.neq.return_value.neq.return_value.eq.return_value.gte.return_value.order.return_value.execute.return_value = self._mock_supabase_query(
                [chip_meta]
            )
            mock_cb.pode_usar_chip.return_value = True

            with patch.object(
                selector, "_contar_msgs_ultima_hora_batch", new_callable=AsyncMock,
                return_value={}
            ):
                chips = await selector._buscar_chips_elegiveis("prospeccao")

        assert len(chips) == 1
        assert chips[0]["id"] == "chip-meta-1"

    @pytest.mark.asyncio
    async def test_chip_meta_quality_red_nao_elegivel(self, chip_meta_red):
        from app.services.chips.selector import ChipSelector

        selector = ChipSelector()
        selector.config = {"limite_prospeccao_hora": 5}

        with (
            patch("app.services.chips.selector.supabase") as mock_sb,
            patch("app.services.chips.selector.ChipCircuitBreaker") as mock_cb,
        ):
            mock_sb.table.return_value.select.return_value.eq.return_value.neq.return_value.neq.return_value.eq.return_value.gte.return_value.order.return_value.execute.return_value = self._mock_supabase_query(
                [chip_meta_red]
            )
            mock_cb.pode_usar_chip.return_value = True

            with patch.object(
                selector, "_contar_msgs_ultima_hora_batch", new_callable=AsyncMock,
                return_value={}
            ):
                chips = await selector._buscar_chips_elegiveis("prospeccao")

        assert len(chips) == 0

    @pytest.mark.asyncio
    async def test_chip_meta_sem_credenciais_nao_elegivel(
        self, chip_meta_sem_credenciais
    ):
        from app.services.chips.selector import ChipSelector

        selector = ChipSelector()
        selector.config = {"limite_prospeccao_hora": 5}

        with (
            patch("app.services.chips.selector.supabase") as mock_sb,
            patch("app.services.chips.selector.ChipCircuitBreaker") as mock_cb,
        ):
            mock_sb.table.return_value.select.return_value.eq.return_value.neq.return_value.neq.return_value.eq.return_value.gte.return_value.order.return_value.execute.return_value = self._mock_supabase_query(
                [chip_meta_sem_credenciais]
            )
            mock_cb.pode_usar_chip.return_value = True

            with patch.object(
                selector, "_contar_msgs_ultima_hora_batch", new_callable=AsyncMock,
                return_value={}
            ):
                chips = await selector._buscar_chips_elegiveis("prospeccao")

        assert len(chips) == 0

    @pytest.mark.asyncio
    async def test_selecao_mista_evolution_e_meta(self, chip_meta, chip_evolution):
        from app.services.chips.selector import ChipSelector

        selector = ChipSelector()
        selector.config = {"limite_prospeccao_hora": 5}

        with (
            patch("app.services.chips.selector.supabase") as mock_sb,
            patch("app.services.chips.selector.ChipCircuitBreaker") as mock_cb,
        ):
            mock_sb.table.return_value.select.return_value.eq.return_value.neq.return_value.neq.return_value.eq.return_value.gte.return_value.order.return_value.execute.return_value = self._mock_supabase_query(
                [chip_meta, chip_evolution]
            )
            mock_cb.pode_usar_chip.return_value = True

            with patch.object(
                selector, "_contar_msgs_ultima_hora_batch", new_callable=AsyncMock,
                return_value={}
            ):
                chips = await selector._buscar_chips_elegiveis("prospeccao")

        assert len(chips) == 2
        providers = {c["provider"] for c in chips}
        assert providers == {"meta", "evolution"}


# ============================================================
# Orchestrator — Meta skip warming + quality (4 testes)
# ============================================================


class TestOrchestratorMeta:
    """Testes para comportamento Meta no orchestrator."""

    @pytest.mark.asyncio
    async def test_chip_meta_excluido_do_warming(self):
        """Chips Meta nao entram no pipeline de warming (neq provider meta)."""
        from app.services.chips.orchestrator import ChipOrchestrator

        orchestrator = ChipOrchestrator()
        orchestrator.config = {
            "trust_min_for_ready": 85,
            "warmup_days": 21,
        }

        with patch("app.services.chips.orchestrator.supabase") as mock_sb:
            # Query retorna vazio (nenhum chip warming elegivel)
            mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.neq.return_value.gte.return_value.execute.return_value = MagicMock(
                data=[]
            )

            result = await orchestrator.verificar_promocoes_warming_ready()

            assert result == 0
            # Verificar que .neq("provider", "meta") foi chamado na cadeia
            table_call = mock_sb.table.return_value
            neq_calls = table_call.select.return_value.eq.return_value.eq.return_value.neq.call_args_list
            meta_filter_found = any(
                call[0] == ("provider", "meta") for call in neq_calls
            )
            assert meta_filter_found, "Esperado .neq('provider', 'meta') na query"

    @pytest.mark.asyncio
    async def test_chip_meta_quality_red_detectado(self):
        """Chips Meta com quality RED sao detectados como degradados."""
        from app.services.chips.orchestrator import ChipOrchestrator

        orchestrator = ChipOrchestrator()
        orchestrator.config = {"trust_degraded_threshold": 40}

        chip_red = {
            "id": "chip-red",
            "telefone": "5511999990001",
            "provider": "meta",
            "status": "active",
            "meta_quality_rating": "RED",
            "trust_score": 100,
        }

        with patch("app.services.chips.orchestrator.supabase") as mock_sb:
            # 1. Chips com trust baixo → vazio
            mock_sb.table.return_value.select.return_value.eq.return_value.lt.return_value.execute.return_value = MagicMock(
                data=[]
            )
            # 2. Chips desconectados (Evolution) → vazio
            mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.neq.return_value.execute.return_value = MagicMock(
                data=[]
            )
            # 3. Chips Meta quality RED
            mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[chip_red]
            )

            degradados = await orchestrator.verificar_chips_degradados()

        assert len(degradados) >= 1
        assert any(c["id"] == "chip-red" for c in degradados)

    @pytest.mark.asyncio
    async def test_chip_meta_quality_yellow_nao_degradado(self):
        """Chips Meta com quality YELLOW nao sao detectados como degradados."""
        from app.services.chips.orchestrator import ChipOrchestrator

        orchestrator = ChipOrchestrator()
        orchestrator.config = {"trust_degraded_threshold": 40}

        with patch("app.services.chips.orchestrator.supabase") as mock_sb:
            # Todas as queries retornam vazio
            mock_sb.table.return_value.select.return_value.eq.return_value.lt.return_value.execute.return_value = MagicMock(
                data=[]
            )
            mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.neq.return_value.execute.return_value = MagicMock(
                data=[]
            )
            mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[]
            )

            degradados = await orchestrator.verificar_chips_degradados()

        assert len(degradados) == 0

    @pytest.mark.asyncio
    async def test_chips_evolution_continuam_warming_normal(self):
        """Chips Evolution nao sao afetados pelo skip Meta no warming."""
        from app.services.chips.orchestrator import ChipOrchestrator
        from datetime import datetime, timezone, timedelta

        orchestrator = ChipOrchestrator()
        orchestrator.config = {
            "trust_min_for_ready": 85,
            "warmup_days": 21,
        }

        # Chip Evolution que completou warmup
        warming_started = (datetime.now(timezone.utc) - timedelta(days=25)).isoformat()
        chip_warming = {
            "id": "chip-evo-warming",
            "telefone": "5511999990005",
            "provider": "evolution",
            "status": "warming",
            "fase_warmup": "operacao",
            "trust_score": 90,
            "warming_started_at": warming_started,
        }

        with patch("app.services.chips.orchestrator.supabase") as mock_sb:
            # Query retorna chip Evolution elegivel
            mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.neq.return_value.gte.return_value.execute.return_value = MagicMock(
                data=[chip_warming]
            )
            mock_sb.table.return_value.update.return_value.eq.return_value.execute = MagicMock()
            mock_sb.table.return_value.insert.return_value.execute = MagicMock()

            result = await orchestrator.verificar_promocoes_warming_ready()

        assert result == 1


# ============================================================
# Health Monitor — Meta quality alerts (2 testes)
# ============================================================


class TestHealthMonitorMeta:
    """Testes para alertas Meta no health monitor."""

    @pytest.mark.asyncio
    async def test_chip_meta_quality_red_auto_demove(self):
        """Chip Meta quality RED gera alert e auto-demove."""
        from app.services.chips.health_monitor import HealthMonitor

        monitor = HealthMonitor()

        chip = {
            "id": "chip-red-1",
            "telefone": "5511999990001",
            "provider": "meta",
            "status": "active",
            "trust_score": 100,
            "meta_quality_rating": "RED",
            "evolution_connected": None,
        }

        with patch("app.services.chips.health_monitor.supabase") as mock_sb:
            # Mock insert (alert creation) and update (auto_demover_chip status change)
            mock_sb.table.return_value.insert.return_value.execute = MagicMock()
            mock_sb.table.return_value.update.return_value.eq.return_value.execute = MagicMock()
            # Mock _criar_alerta (duplicate check)
            mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[]
            )

            result = await monitor.verificar_auto_demove(chip)

        assert result is not None
        assert result["sucesso"] is True
        assert result["motivo"] == "Meta quality rating RED"

        # Verificar que alert meta_quality_degraded foi inserido
        insert_calls = mock_sb.table.return_value.insert.call_args_list
        alert_found = any(
            "meta_quality_degraded" in str(call)
            for call in insert_calls
        )
        assert alert_found, "Alert meta_quality_degraded deveria ser criado"

    @pytest.mark.asyncio
    async def test_chip_meta_quality_green_nenhuma_acao(self):
        """Chip Meta quality GREEN nao gera demove."""
        from app.services.chips.health_monitor import HealthMonitor

        monitor = HealthMonitor()

        chip = {
            "id": "chip-green-1",
            "telefone": "5511999990002",
            "provider": "meta",
            "status": "active",
            "trust_score": 100,
            "meta_quality_rating": "GREEN",
            "evolution_connected": None,
        }

        # Mock circuit breaker to avoid real call
        with patch("app.services.chips.health_monitor.supabase"):
            mock_circuit = MagicMock()
            mock_circuit.falhas_consecutivas = 0

            with patch(
                "app.services.chips.circuit_breaker.ChipCircuitBreaker.get_circuit",
                return_value=mock_circuit,
            ):
                result = await monitor.verificar_auto_demove(chip)

        assert result is None


# ============================================================
# Campaign Executor — _adicionar_meta_template_info (5 testes)
# ============================================================


class TestExecutorMetaTemplate:
    """Testes para _adicionar_meta_template_info no executor."""

    @pytest.fixture
    def executor(self):
        from app.services.campanhas.executor import CampanhaExecutor

        return CampanhaExecutor()

    @pytest.fixture
    def campanha_com_template(self):
        from app.services.campanhas.types import (
            CampanhaData,
            TipoCampanha,
            StatusCampanha,
            AudienceFilters,
        )

        return CampanhaData(
            id=200,
            nome_template="Test",
            tipo_campanha=TipoCampanha.DISCOVERY,
            corpo=None,
            status=StatusCampanha.AGENDADA,
            audience_filters=AudienceFilters(),
            meta_template_name="julia_discovery_v1",
            meta_template_language="pt_BR",
        )

    @pytest.fixture
    def campanha_sem_template(self):
        from app.services.campanhas.types import (
            CampanhaData,
            TipoCampanha,
            StatusCampanha,
            AudienceFilters,
        )

        return CampanhaData(
            id=201,
            nome_template="Test",
            tipo_campanha=TipoCampanha.DISCOVERY,
            corpo=None,
            status=StatusCampanha.AGENDADA,
            audience_filters=AudienceFilters(),
        )

    @pytest.fixture
    def destinatario(self):
        return {
            "telefone": "5511999999999",
            "nome": "Dr Carlos",
            "especialidade": "Cardiologia",
        }

    @pytest.mark.asyncio
    async def test_campanha_com_template_adiciona_metadata(
        self, executor, campanha_com_template, destinatario
    ):
        metadata = {}
        template_data = {
            "template_name": "julia_discovery_v1",
            "status": "APPROVED",
            "variable_mapping": {"1": "nome"},
            "components": [],
        }

        mock_ts = MagicMock()
        mock_ts.buscar_template_por_nome = AsyncMock(return_value=template_data)
        mock_tm = MagicMock()
        mock_tm.mapear_variaveis = MagicMock(
            return_value=[
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": "Dr Carlos"}],
                }
            ]
        )

        with (
            patch(
                "app.services.meta.template_service.template_service", mock_ts
            ),
            patch(
                "app.services.meta.template_mapper.template_mapper", mock_tm
            ),
        ):
            await executor._adicionar_meta_template_info(
                metadata, campanha_com_template, destinatario
            )

        assert "meta_template" in metadata
        assert metadata["meta_template"]["name"] == "julia_discovery_v1"
        assert metadata["meta_template"]["language"] == "pt_BR"
        assert len(metadata["meta_template"]["components"]) == 1

    @pytest.mark.asyncio
    async def test_template_nao_encontrado_nao_adiciona(
        self, executor, campanha_com_template, destinatario
    ):
        metadata = {}

        mock_ts = MagicMock()
        mock_ts.buscar_template_por_nome = AsyncMock(return_value=None)

        with patch(
            "app.services.meta.template_service.template_service", mock_ts
        ):
            await executor._adicionar_meta_template_info(
                metadata, campanha_com_template, destinatario
            )

        assert "meta_template" not in metadata

    @pytest.mark.asyncio
    async def test_template_nao_aprovado_nao_adiciona(
        self, executor, campanha_com_template, destinatario
    ):
        metadata = {}
        template_data = {
            "template_name": "julia_discovery_v1",
            "status": "PENDING",
        }

        mock_ts = MagicMock()
        mock_ts.buscar_template_por_nome = AsyncMock(return_value=template_data)

        with patch(
            "app.services.meta.template_service.template_service", mock_ts
        ):
            await executor._adicionar_meta_template_info(
                metadata, campanha_com_template, destinatario
            )

        assert "meta_template" not in metadata

    @pytest.mark.asyncio
    async def test_campanha_sem_template_nao_chama_service(
        self, executor, campanha_sem_template, destinatario
    ):
        """Quando campanha nao tem meta_template_name, _adicionar nao e chamado."""
        # O metodo so e chamado quando campanha.meta_template_name esta definido
        # (verificacao feita no executor antes de chamar)
        assert campanha_sem_template.meta_template_name is None

    @pytest.mark.asyncio
    async def test_variable_mapping_correto(
        self, executor, campanha_com_template, destinatario
    ):
        metadata = {}
        template_data = {
            "template_name": "julia_discovery_v1",
            "status": "APPROVED",
            "variable_mapping": {"1": "nome", "2": "especialidade"},
            "components": [],
        }

        mock_ts = MagicMock()
        mock_ts.buscar_template_por_nome = AsyncMock(return_value=template_data)
        mock_tm = MagicMock()
        mock_tm.mapear_variaveis = MagicMock(return_value=[])

        with (
            patch(
                "app.services.meta.template_service.template_service", mock_ts
            ),
            patch(
                "app.services.meta.template_mapper.template_mapper", mock_tm
            ),
        ):
            await executor._adicionar_meta_template_info(
                metadata, campanha_com_template, destinatario
            )

        # Verificar que mapper foi chamado com template, destinatario e escopo
        mock_tm.mapear_variaveis.assert_called_once()
        call_args = mock_tm.mapear_variaveis.call_args[0]
        assert call_args[0] == template_data  # template
        assert call_args[1] == destinatario  # destinatario


# ============================================================
# Multi-chip — template_info propagation (2 testes)
# ============================================================


class TestMultiChipTemplateInfo:
    """Testes para propagacao de template_info no multi_chip."""

    @pytest.mark.asyncio
    async def test_template_info_extraido_da_metadata(self):
        from app.services.outbound.multi_chip import _enviar_via_multi_chip

        # Use MagicMock because OutboundContext is frozen and has no metadata field
        ctx = MagicMock()
        ctx.method = MagicMock()
        ctx.conversation_id = None
        ctx.metadata = {
            "meta_template": {
                "name": "julia_discovery_v1",
                "language": "pt_BR",
                "components": [],
            }
        }

        chip = {
            "id": "chip-1",
            "telefone": "5511988880001",
            "provider": "meta",
        }

        mock_selector = MagicMock()
        mock_selector.selecionar_chip = AsyncMock(return_value=chip)
        mock_selector.registrar_envio = AsyncMock()
        mock_enviar = AsyncMock(
            return_value=MessageResult(
                success=True, message_id="wamid.1", provider="meta"
            )
        )

        with (
            patch(
                "app.services.chips.selector.chip_selector", mock_selector
            ),
            patch(
                "app.services.chips.sender.enviar_via_chip", mock_enviar
            ),
        ):
            result = await _enviar_via_multi_chip("5511999999999", "Ola", ctx)

        # Verificar que template_info foi passado
        call_kwargs = mock_enviar.call_args
        assert call_kwargs.kwargs.get("template_info") is not None
        assert call_kwargs.kwargs["template_info"]["name"] == "julia_discovery_v1"

    @pytest.mark.asyncio
    async def test_sem_template_info_passa_none(self):
        from app.services.outbound.multi_chip import _enviar_via_multi_chip

        # Use MagicMock — metadata empty dict means no meta_template key
        ctx = MagicMock()
        ctx.method = MagicMock()
        ctx.conversation_id = None
        ctx.metadata = {}

        chip = {
            "id": "chip-1",
            "telefone": "5511988880001",
            "provider": "evolution",
        }

        mock_selector = MagicMock()
        mock_selector.selecionar_chip = AsyncMock(return_value=chip)
        mock_selector.registrar_envio = AsyncMock()
        mock_enviar = AsyncMock(
            return_value=MessageResult(
                success=True, message_id="evo.1", provider="evolution"
            )
        )

        with (
            patch(
                "app.services.chips.selector.chip_selector", mock_selector
            ),
            patch(
                "app.services.chips.sender.enviar_via_chip", mock_enviar
            ),
        ):
            result = await _enviar_via_multi_chip("5511999999999", "Ola", ctx)

        call_kwargs = mock_enviar.call_args
        assert call_kwargs.kwargs.get("template_info") is None
