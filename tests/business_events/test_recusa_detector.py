"""
Testes para detector de recusa.

Sprint 17 - E05
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.business_events.recusa_detector import (
    detectar_recusa,
    RecusaResult,
)


class TestDetectarRecusa:
    """Testes para detecção de recusa."""

    @pytest.mark.parametrize("mensagem,esperado", [
        # Recusa explícita - alta confiança
        ("não tenho interesse", True),
        ("nao tenho interesse", True),
        ("Não quero esse plantão", True),
        ("não vou poder", True),
        ("nao vou poder", True),
        ("passo essa", True),
        ("passa essa", True),
        ("não me interessa", True),
        ("declino a oferta", True),
        ("recuso", True),
        ("não aceito", True),
        ("obrigada, mas não", True),

        # Desculpas - média confiança
        ("já tenho compromisso nesse dia", True),
        ("ja tenho compromisso", True),
        ("tenho outro plantão", True),
        ("já estou escalado", True),
        ("estou de férias", True),
        ("muito longe pra mim", True),
        ("valor baixo demais", True),
        ("não faço noturno", True),
        ("não trabalho nesse dia", True),
        ("horário ruim pra mim", True),
        ("não faço urgência", True),

        # NÃO são recusa
        ("não entendi, pode explicar?", False),
        ("nao entendi", False),
        ("não recebi a mensagem", False),
        ("qual o valor mesmo?", False),
        ("onde fica o hospital?", False),
        ("me fala mais sobre a vaga", False),
        ("pode repetir?", False),
        ("me manda mais detalhes", False),
        ("preciso pensar", False),
        ("vou ver", False),
        ("deixa eu ver", False),

        # Neutros
        ("ok", False),
        ("vou pensar", False),
        ("tá bom", False),
        ("blz", False),
        ("pode ser", False),
    ])
    def test_detectar_recusa_parametrizado(self, mensagem, esperado):
        """Detecta recusas corretamente."""
        result = detectar_recusa(mensagem)
        assert result.is_recusa == esperado, f"Falhou para: '{mensagem}'"

    def test_recusa_explicita_alta_confianca(self):
        """Recusa explícita tem alta confiança."""
        result = detectar_recusa("não tenho interesse")
        assert result.is_recusa is True
        assert result.confianca >= 0.8
        assert result.tipo == "explicita"
        assert result.padrao_matched is not None

    def test_desculpa_media_confianca(self):
        """Desculpa tem média confiança."""
        result = detectar_recusa("já tenho compromisso")
        assert result.is_recusa is True
        assert 0.5 <= result.confianca < 0.8
        assert result.tipo == "desculpa"
        assert result.padrao_matched is not None

    def test_nao_recusa_alta_confianca_negativa(self):
        """Não-recusa tem alta confiança de que não é recusa."""
        result = detectar_recusa("não entendi a proposta")
        assert result.is_recusa is False
        assert result.confianca >= 0.8

    def test_mensagem_vazia(self):
        """Mensagem vazia não é recusa."""
        result = detectar_recusa("")
        assert result.is_recusa is False
        assert result.confianca == 0.5

    def test_mensagem_none(self):
        """Mensagem None não é recusa."""
        result = detectar_recusa(None)
        assert result.is_recusa is False

    def test_case_insensitive(self):
        """Detecção é case insensitive."""
        result_lower = detectar_recusa("não tenho interesse")
        result_upper = detectar_recusa("NÃO TENHO INTERESSE")
        result_mixed = detectar_recusa("Não Tenho Interesse")

        assert result_lower.is_recusa is True
        assert result_upper.is_recusa is True
        assert result_mixed.is_recusa is True


class TestBuscarUltimaOferta:
    """Testes para busca de última oferta."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.recusa_detector.supabase")
    async def test_busca_ultima_oferta_encontrada(self, mock_supabase):
        """Busca última oferta do médico com sucesso."""
        mock_response = MagicMock()
        mock_response.data = [{
            "id": "evt-123",
            "vaga_id": "vaga-456",
            "hospital_id": "hosp-789",
            "ts": "2025-01-10T10:00:00Z",
        }]
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value = mock_response

        from app.services.business_events.recusa_detector import buscar_ultima_oferta
        oferta = await buscar_ultima_oferta("cliente-123")

        assert oferta is not None
        assert oferta["vaga_id"] == "vaga-456"
        assert oferta["hospital_id"] == "hosp-789"

    @pytest.mark.asyncio
    @patch("app.services.business_events.recusa_detector.supabase")
    async def test_busca_ultima_oferta_nao_encontrada(self, mock_supabase):
        """Retorna None se não houver oferta."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value = mock_response

        from app.services.business_events.recusa_detector import buscar_ultima_oferta
        oferta = await buscar_ultima_oferta("cliente-123")

        assert oferta is None

    @pytest.mark.asyncio
    @patch("app.services.business_events.recusa_detector.supabase")
    async def test_busca_ultima_oferta_erro(self, mock_supabase):
        """Retorna None em caso de erro."""
        mock_supabase.table.side_effect = Exception("DB Error")

        from app.services.business_events.recusa_detector import buscar_ultima_oferta
        oferta = await buscar_ultima_oferta("cliente-123")

        assert oferta is None


class TestProcessarPossivelRecusa:
    """Testes para processamento de recusa."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.recusa_detector.should_emit_event")
    @patch("app.services.business_events.recusa_detector.buscar_ultima_oferta")
    @patch("app.services.business_events.recusa_detector.emit_event")
    async def test_emite_offer_declined(
        self, mock_emit, mock_buscar, mock_should_emit
    ):
        """Emite offer_declined quando detecta recusa com oferta recente."""
        mock_should_emit.return_value = True
        mock_buscar.return_value = {
            "id": "evt-123",
            "vaga_id": "vaga-456",
            "hospital_id": "hosp-789",
            "ts": "2025-01-10T10:00:00Z",
        }
        mock_emit.return_value = "new-event-id"

        from app.services.business_events.recusa_detector import processar_possivel_recusa
        result = await processar_possivel_recusa(
            cliente_id="cliente-123",
            mensagem="não tenho interesse",
            conversation_id="conv-456",
        )

        assert result is True
        mock_emit.assert_called_once()
        event = mock_emit.call_args[0][0]
        assert event.event_type.value == "offer_declined"
        assert event.vaga_id == "vaga-456"
        assert event.event_props["tipo_recusa"] == "explicita"

    @pytest.mark.asyncio
    @patch("app.services.business_events.recusa_detector.should_emit_event")
    @patch("app.services.business_events.recusa_detector.buscar_ultima_oferta")
    async def test_nao_emite_sem_oferta_recente(
        self, mock_buscar, mock_should_emit
    ):
        """Não emite offer_declined se não houver oferta recente."""
        mock_should_emit.return_value = True
        mock_buscar.return_value = None  # Sem oferta

        from app.services.business_events.recusa_detector import processar_possivel_recusa
        result = await processar_possivel_recusa(
            cliente_id="cliente-123",
            mensagem="não quero",
        )

        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.business_events.recusa_detector.should_emit_event")
    async def test_nao_emite_se_nao_e_recusa(self, mock_should_emit):
        """Não emite para mensagem que não é recusa."""
        mock_should_emit.return_value = True

        from app.services.business_events.recusa_detector import processar_possivel_recusa
        result = await processar_possivel_recusa(
            cliente_id="cliente-123",
            mensagem="ok, vou ver",
        )

        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.business_events.recusa_detector.should_emit_event")
    async def test_nao_emite_quando_rollout_inativo(self, mock_should_emit):
        """Não emite quando rollout está inativo."""
        mock_should_emit.return_value = False

        from app.services.business_events.recusa_detector import processar_possivel_recusa
        result = await processar_possivel_recusa(
            cliente_id="cliente-123",
            mensagem="não quero",
        )

        assert result is False
        mock_should_emit.assert_called_once_with("cliente-123", "offer_declined")

    @pytest.mark.asyncio
    @patch("app.services.business_events.recusa_detector.should_emit_event")
    async def test_baixa_confianca_nao_emite(self, mock_should_emit):
        """Não emite quando confiança é baixa."""
        mock_should_emit.return_value = True

        from app.services.business_events.recusa_detector import processar_possivel_recusa
        result = await processar_possivel_recusa(
            cliente_id="cliente-123",
            mensagem="vou pensar",  # Neutro, confiança 0.5
        )

        assert result is False
