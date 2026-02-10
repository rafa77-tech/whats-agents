"""
Testes para sistema de alertas de negocio.

Sprint 17 - E07
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone

from app.services.business_events.alerts import (
    Alert,
    AlertType,
    AlertSeverity,
    detect_handoff_spike,
    detect_decline_spike,
    detect_conversion_drop,
    detect_all_anomalies,
    send_alert_to_slack,
    is_in_cooldown,
    set_cooldown,
    process_and_notify_alerts,
    persist_alert,
    _get_alert_key,
    _format_slack_message,
    _get_action_text,
)


class TestAlertDataclass:
    """Testes para Alert dataclass."""

    def test_cria_alerta_basico(self):
        """Cria alerta com campos obrigatorios."""
        alert = Alert(
            alert_type=AlertType.HANDOFF_SPIKE,
            severity=AlertSeverity.WARNING,
            title="Teste",
            description="Descricao",
        )

        assert alert.alert_type == AlertType.HANDOFF_SPIKE
        assert alert.severity == AlertSeverity.WARNING
        assert alert.title == "Teste"
        assert alert.detected_at is not None

    def test_to_dict_completo(self):
        """Serializa corretamente para dict."""
        alert = Alert(
            alert_type=AlertType.RECUSA_SPIKE,
            severity=AlertSeverity.CRITICAL,
            title="Spike de Recusas",
            description="Taxa alta",
            hospital_id="hosp-123",
            hospital_name="Hospital Teste",
            current_value=45.0,
            baseline_value=40.0,
            threshold_pct=40.0,
        )

        result = alert.to_dict()

        assert result["alert_type"] == "recusa_spike"
        assert result["severity"] == "critical"
        assert result["title"] == "Spike de Recusas"
        assert result["hospital_id"] == "hosp-123"
        assert result["current_value"] == 45.0

    def test_alert_types_enum(self):
        """AlertType tem todos os tipos esperados."""
        assert AlertType.HANDOFF_SPIKE.value == "handoff_spike"
        assert AlertType.RECUSA_SPIKE.value == "recusa_spike"
        assert AlertType.CONVERSION_DROP.value == "conversion_drop"

    def test_alert_severity_enum(self):
        """AlertSeverity tem severidades esperadas."""
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.CRITICAL.value == "critical"


class TestDetectHandoffSpike:
    """Testes para detect_handoff_spike."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.alerts.supabase")
    async def test_detecta_spike_quando_acima_threshold(self, mock_supabase):
        """Detecta spike quando handoffs excedem threshold."""
        # Mock: hospitais com eventos
        mock_hospitals = MagicMock()
        mock_hospitals.data = [{"hospital_id": "hosp-1"}]

        # Mock: contagem de eventos (10 em 24h, 21 em 7d = 3/dia media)
        mock_count_24h = MagicMock()
        mock_count_24h.count = 10

        mock_count_7d = MagicMock()
        mock_count_7d.count = 21

        mock_hospital_name = MagicMock()
        mock_hospital_name.data = [{"nome": "Hospital ABC"}]

        def mock_table(table_name):
            mock = MagicMock()
            if table_name == "hospitais":
                mock.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_hospital_name
            else:
                mock.select.return_value.eq.return_value.gte.return_value.not_.is_.return_value.execute.return_value = mock_hospitals
            return mock

        mock_supabase.table.side_effect = mock_table

        # Simplificar: mockar _get_event_count diretamente
        with patch("app.services.business_events.alerts._get_event_count") as mock_count:
            mock_count.side_effect = [10, 21]  # 24h, 7d

            with patch("app.services.business_events.alerts._get_hospital_name") as mock_name:
                mock_name.return_value = "Hospital ABC"

                alerts = await detect_handoff_spike(min_handoffs=5)

        # Threshold = max(5, 3*2) = 6, handoffs_24h = 10 >= 6
        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.HANDOFF_SPIKE
        assert alerts[0].hospital_name == "Hospital ABC"

    @pytest.mark.asyncio
    @patch("app.services.business_events.alerts.supabase")
    async def test_nao_detecta_quando_abaixo_threshold(self, mock_supabase):
        """Nao detecta quando handoffs abaixo do threshold."""
        mock_response = MagicMock()
        mock_response.data = [{"hospital_id": "hosp-1"}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.not_.is_.return_value.execute.return_value = mock_response

        with patch("app.services.business_events.alerts._get_event_count") as mock_count:
            mock_count.side_effect = [3, 21]  # 3 em 24h, 21 em 7d

            alerts = await detect_handoff_spike(min_handoffs=5)

        # Threshold = max(5, 3*2) = 6, handoffs_24h = 3 < 6
        assert len(alerts) == 0

    @pytest.mark.asyncio
    @patch("app.services.business_events.alerts.supabase")
    async def test_trata_erro_graciosamente(self, mock_supabase):
        """Retorna lista vazia em caso de erro."""
        mock_supabase.table.side_effect = Exception("DB Error")

        alerts = await detect_handoff_spike()

        assert alerts == []


class TestDetectDeclineSpike:
    """Testes para detect_decline_spike."""

    @pytest.mark.asyncio
    async def test_detecta_spike_acima_40_porcento(self):
        """Detecta quando taxa de recusa > 40%."""
        with patch("app.services.business_events.alerts._get_event_count") as mock_count:
            # 10 ofertas, 5 recusas = 50%
            mock_count.side_effect = [10, 5]

            alerts = await detect_decline_spike(min_offers=10, threshold_pct=40.0)

        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.RECUSA_SPIKE
        assert alerts[0].current_value == 50.0

    @pytest.mark.asyncio
    async def test_nao_detecta_abaixo_threshold(self):
        """Nao detecta quando taxa abaixo do threshold."""
        with patch("app.services.business_events.alerts._get_event_count") as mock_count:
            # 10 ofertas, 3 recusas = 30%
            mock_count.side_effect = [10, 3]

            alerts = await detect_decline_spike(min_offers=10, threshold_pct=40.0)

        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_ignora_volume_baixo(self):
        """Ignora quando volume de ofertas insuficiente."""
        with patch("app.services.business_events.alerts._get_event_count") as mock_count:
            # 5 ofertas < 10 minimo
            mock_count.side_effect = [5, 4]

            alerts = await detect_decline_spike(min_offers=10)

        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_severidade_critical_acima_60_porcento(self):
        """Severidade CRITICAL quando taxa > 60%."""
        with patch("app.services.business_events.alerts._get_event_count") as mock_count:
            # 10 ofertas, 7 recusas = 70%
            mock_count.side_effect = [10, 7]

            alerts = await detect_decline_spike(min_offers=10, threshold_pct=40.0)

        assert alerts[0].severity == AlertSeverity.CRITICAL


class TestDetectConversionDrop:
    """Testes para detect_conversion_drop."""

    @pytest.mark.asyncio
    async def test_detecta_queda_30_porcento(self):
        """Detecta queda de 30%+ vs media 7d."""
        with patch("app.services.business_events.alerts._get_event_count") as mock_count:
            # Hoje: 10 ofertas, 2 aceites = 20%
            # 7d total: 70 ofertas, 35 aceites
            # Historico (excl hoje): 60 ofertas, 33 aceites = 55%
            # Queda: (55 - 20) / 55 = 63%
            mock_count.side_effect = [10, 2, 70, 35]

            alerts = await detect_conversion_drop(min_offers=10, drop_pct=30.0)

        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.CONVERSION_DROP

    @pytest.mark.asyncio
    async def test_nao_detecta_sem_queda(self):
        """Nao detecta quando taxa estavel."""
        with patch("app.services.business_events.alerts._get_event_count") as mock_count:
            # Hoje: 10 ofertas, 5 aceites = 50%
            # 7d: 70 ofertas, 35 aceites
            # Historico: 60 ofertas, 30 aceites = 50%
            # Sem queda
            mock_count.side_effect = [10, 5, 70, 35]

            alerts = await detect_conversion_drop(min_offers=10, drop_pct=30.0)

        assert len(alerts) == 0


class TestDetectAllAnomalies:
    """Testes para detect_all_anomalies."""

    @pytest.mark.asyncio
    async def test_agrega_todos_detectores(self):
        """Executa todos os detectores e agrega resultados."""
        with patch("app.services.business_events.alerts.detect_handoff_spike") as mock_handoff, \
             patch("app.services.business_events.alerts.detect_decline_spike") as mock_decline, \
             patch("app.services.business_events.alerts.detect_conversion_drop") as mock_conversion:

            mock_handoff.return_value = [Alert(
                alert_type=AlertType.HANDOFF_SPIKE,
                severity=AlertSeverity.WARNING,
                title="Handoff 1",
                description="Desc",
            )]
            mock_decline.return_value = [Alert(
                alert_type=AlertType.RECUSA_SPIKE,
                severity=AlertSeverity.CRITICAL,
                title="Recusa 1",
                description="Desc",
            )]
            mock_conversion.return_value = []

            alerts = await detect_all_anomalies()

        assert len(alerts) == 2


class TestSlackNotification:
    """Testes para notificacao Slack."""

    def test_format_slack_message_warning(self):
        """Formata mensagem para alerta WARNING."""
        alert = Alert(
            alert_type=AlertType.HANDOFF_SPIKE,
            severity=AlertSeverity.WARNING,
            title="Spike de Handoff",
            description="5 handoffs em 24h",
        )

        message = _format_slack_message(alert)

        assert "Spike de Handoff" in message["text"]
        assert message["attachments"][0]["color"] == "#FFA500"  # Laranja

    def test_format_slack_message_critical(self):
        """Formata mensagem para alerta CRITICAL."""
        alert = Alert(
            alert_type=AlertType.RECUSA_SPIKE,
            severity=AlertSeverity.CRITICAL,
            title="Spike Critico",
            description="Taxa muito alta",
        )

        message = _format_slack_message(alert)

        assert message["attachments"][0]["color"] == "#FF0000"  # Vermelho

    def test_get_action_text_handoff(self):
        """Retorna acoes para handoff spike."""
        alert = Alert(
            alert_type=AlertType.HANDOFF_SPIKE,
            severity=AlertSeverity.WARNING,
            title="Test",
            description="Test",
        )

        text = _get_action_text(alert)

        assert "conversas recentes" in text.lower()

    def test_get_action_text_recusa(self):
        """Retorna acoes para recusa spike."""
        alert = Alert(
            alert_type=AlertType.RECUSA_SPIKE,
            severity=AlertSeverity.WARNING,
            title="Test",
            description="Test",
        )

        text = _get_action_text(alert)

        assert "abordagem" in text.lower()

    @pytest.mark.asyncio
    async def test_send_alert_to_slack_sucesso(self):
        """Sprint 47: Alerta é logado (Slack removido), sempre retorna True."""
        alert = Alert(
            alert_type=AlertType.HANDOFF_SPIKE,
            severity=AlertSeverity.WARNING,
            title="Teste",
            description="Desc",
        )

        result = await send_alert_to_slack(alert)

        # Sprint 47: send_alert_to_slack agora apenas loga, sempre sucesso
        assert result is True

    @pytest.mark.asyncio
    async def test_send_alert_to_slack_falha(self):
        """Sprint 47: Alerta é logado (Slack removido), sempre retorna True."""
        # Sprint 47: Não há mais falha pois não envia para Slack
        alert = Alert(
            alert_type=AlertType.HANDOFF_SPIKE,
            severity=AlertSeverity.CRITICAL,  # Mesmo critical apenas loga
            title="Teste",
            description="Desc",
        )

        result = await send_alert_to_slack(alert)

        # Sprint 47: send_alert_to_slack agora apenas loga, sempre sucesso
        assert result is True


class TestCooldown:
    """Testes para cooldown de alertas."""

    def test_get_alert_key_por_hospital(self):
        """Gera chave unica por tipo + hospital."""
        alert1 = Alert(
            alert_type=AlertType.HANDOFF_SPIKE,
            severity=AlertSeverity.WARNING,
            title="Test",
            description="Test",
            hospital_id="hosp-1",
        )
        alert2 = Alert(
            alert_type=AlertType.HANDOFF_SPIKE,
            severity=AlertSeverity.WARNING,
            title="Test",
            description="Test",
            hospital_id="hosp-2",
        )

        key1 = _get_alert_key(alert1)
        key2 = _get_alert_key(alert2)

        assert key1 != key2
        assert key1.startswith("alert:cooldown:")

    def test_get_alert_key_global(self):
        """Gera chave para alerta sem hospital."""
        alert = Alert(
            alert_type=AlertType.RECUSA_SPIKE,
            severity=AlertSeverity.WARNING,
            title="Test",
            description="Test",
        )

        key = _get_alert_key(alert)

        assert "global" in key or key.startswith("alert:cooldown:")

    @pytest.mark.asyncio
    @patch("app.services.business_events.alerts.redis_client")
    async def test_is_in_cooldown_true(self, mock_redis):
        """Retorna True quando em cooldown."""
        mock_redis.exists = AsyncMock(return_value=1)

        alert = Alert(
            alert_type=AlertType.HANDOFF_SPIKE,
            severity=AlertSeverity.WARNING,
            title="Test",
            description="Test",
        )

        result = await is_in_cooldown(alert)

        assert result is True

    @pytest.mark.asyncio
    @patch("app.services.business_events.alerts.redis_client")
    async def test_is_in_cooldown_false(self, mock_redis):
        """Retorna False quando nao em cooldown."""
        mock_redis.exists = AsyncMock(return_value=0)

        alert = Alert(
            alert_type=AlertType.HANDOFF_SPIKE,
            severity=AlertSeverity.WARNING,
            title="Test",
            description="Test",
        )

        result = await is_in_cooldown(alert)

        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.business_events.alerts.redis_client")
    async def test_set_cooldown(self, mock_redis):
        """Define cooldown corretamente."""
        mock_redis.setex = AsyncMock()

        alert = Alert(
            alert_type=AlertType.HANDOFF_SPIKE,
            severity=AlertSeverity.WARNING,
            title="Test",
            description="Test",
        )

        await set_cooldown(alert)

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 3600  # 1 hora


class TestProcessAndNotify:
    """Testes para process_and_notify_alerts."""

    @pytest.mark.asyncio
    async def test_respeita_cooldown(self):
        """Nao envia alertas em cooldown."""
        alert = Alert(
            alert_type=AlertType.HANDOFF_SPIKE,
            severity=AlertSeverity.WARNING,
            title="Test",
            description="Test",
        )

        with patch("app.services.business_events.alerts.is_in_cooldown") as mock_cooldown, \
             patch("app.services.business_events.alerts.send_alert_to_slack") as mock_send, \
             patch("app.services.business_events.alerts.persist_alert") as mock_persist:

            mock_cooldown.return_value = True

            sent = await process_and_notify_alerts([alert])

        assert sent == 0
        mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_envia_e_define_cooldown(self):
        """Envia alerta e define cooldown."""
        alert = Alert(
            alert_type=AlertType.HANDOFF_SPIKE,
            severity=AlertSeverity.WARNING,
            title="Test",
            description="Test",
        )

        with patch("app.services.business_events.alerts.is_in_cooldown") as mock_cooldown, \
             patch("app.services.business_events.alerts.send_alert_to_slack") as mock_send, \
             patch("app.services.business_events.alerts.set_cooldown") as mock_set, \
             patch("app.services.business_events.alerts.persist_alert") as mock_persist, \
             patch("app.services.business_events.alerts.mark_alert_notified") as mock_mark:

            mock_cooldown.return_value = False
            mock_send.return_value = True
            mock_persist.return_value = "alert-123"

            sent = await process_and_notify_alerts([alert])

        assert sent == 1
        mock_send.assert_called_once()
        mock_set.assert_called_once()
        mock_persist.assert_called_once()
        mock_mark.assert_called_once_with("alert-123")


class TestPersistence:
    """Testes para persistencia de alertas."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.alerts.supabase")
    async def test_persist_alert_sucesso(self, mock_supabase):
        """Persiste alerta no banco."""
        mock_response = MagicMock()
        mock_response.data = [{"alert_id": "uuid-123"}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_response

        alert = Alert(
            alert_type=AlertType.HANDOFF_SPIKE,
            severity=AlertSeverity.WARNING,
            title="Test",
            description="Desc",
            hospital_id="hosp-1",
            current_value=10.0,
        )

        alert_id = await persist_alert(alert)

        assert alert_id == "uuid-123"
        mock_supabase.table.assert_called_with("business_alerts")

    @pytest.mark.asyncio
    @patch("app.services.business_events.alerts.supabase")
    async def test_persist_alert_erro(self, mock_supabase):
        """Retorna None em caso de erro."""
        mock_supabase.table.side_effect = Exception("DB Error")

        alert = Alert(
            alert_type=AlertType.HANDOFF_SPIKE,
            severity=AlertSeverity.WARNING,
            title="Test",
            description="Desc",
        )

        alert_id = await persist_alert(alert)

        assert alert_id is None
