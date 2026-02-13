"""
Testes de caracterização para app/services/agente.py

Sprint 58 - Epic 0: Safety Net
Captura o comportamento atual de gerar_resposta_julia e processar_mensagem_completo.

Foca em:
- Contratos de interface (parâmetros de entrada, tipos de retorno)
- ProcessamentoResult shape
- Fluxos de decisão da Policy Engine (handoff, wait, respond)
- Timeout e fallback behavior
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


# =============================================================================
# Fixtures locais
# =============================================================================


@pytest.fixture
def medico():
    return {
        "id": str(uuid4()),
        "primeiro_nome": "Dr. Teste",
        "telefone": "5511999999999",
        "especialidade_nome": "Cardiologia",
        "especialidade_id": str(uuid4()),
        "stage_jornada": "novo",
        "crm": "123456-SP",
        "status": "ativo",
    }


@pytest.fixture
def conversa(medico):
    return {
        "id": str(uuid4()),
        "cliente_id": medico["id"],
        "telefone": medico["telefone"],
        "status": "ativa",
        "controlled_by": "ai",
        "last_message_at": "2025-01-15T10:00:00Z",
    }


@pytest.fixture
def contexto():
    return {
        "medico": "Dr. Teste - Cardiologista",
        "vagas": "3 vagas disponíveis",
        "historico": "Mensagem anterior...",
        "historico_raw": [],
        "primeira_msg": False,
        "data_hora_atual": "15/01/2025 10:00",
        "dia_semana": "quarta-feira",
        "especialidade": "Cardiologia",
        "handoff_recente": "",
        "memorias": "",
        "diretrizes": "",
        "campanha": None,
    }


@pytest.fixture
def mock_conhecimento():
    """Mock do OrquestradorConhecimento."""
    with patch("app.services.agente.OrquestradorConhecimento") as MockOrq:
        mock_instance = MagicMock()
        mock_situacao = MagicMock()
        mock_situacao.resumo = "Conhecimento dinâmico mockado"
        mock_situacao.objecao.tem_objecao = False
        mock_situacao.objecao.tipo = None
        mock_situacao.objecao.subtipo = None
        mock_situacao.objecao.confianca = 0
        mock_situacao.perfil.perfil = "curioso"
        mock_situacao.objetivo.objetivo = "buscar_vagas"
        mock_instance.analisar_situacao = AsyncMock(return_value=mock_situacao)
        MockOrq.return_value = mock_instance
        yield MockOrq


@pytest.fixture
def mock_llm_services():
    """Mock dos serviços LLM."""
    with (
        patch("app.services.agente.gerar_resposta", new_callable=AsyncMock) as mock_gerar,
        patch(
            "app.services.agente.gerar_resposta_com_tools", new_callable=AsyncMock
        ) as mock_tools,
        patch("app.services.agente.continuar_apos_tool", new_callable=AsyncMock) as mock_cont,
        patch("app.services.agente.montar_prompt_julia", new_callable=AsyncMock) as mock_prompt,
        patch(
            "app.services.agente.converter_historico_para_messages"
        ) as mock_hist,
    ):
        mock_gerar.return_value = "Oi Dr! Tudo bem?"
        mock_tools.return_value = {"text": "Oi Dr! Tudo bem?", "tool_use": [], "stop_reason": "end_turn"}
        mock_cont.return_value = {"text": "Achei vagas pra vc!", "tool_use": []}
        mock_prompt.return_value = "System prompt mockado"
        mock_hist.return_value = []
        yield {
            "gerar_resposta": mock_gerar,
            "gerar_resposta_com_tools": mock_tools,
            "continuar_apos_tool": mock_cont,
            "montar_prompt": mock_prompt,
            "converter_historico": mock_hist,
        }


# =============================================================================
# gerar_resposta_julia
# =============================================================================


class TestGerarRespostaJulia:
    """Testa gerar_resposta_julia - geração de respostas."""

    @pytest.mark.asyncio
    async def test_retorna_string(self, medico, conversa, contexto, mock_conhecimento, mock_llm_services):
        from app.services.agente import gerar_resposta_julia

        with (
            patch(
                "app.services.conversation_mode.response_validator.validar_resposta_julia",
                return_value=(True, None),
            ),
            patch("app.services.conversation_mode.response_validator.get_fallback_response"),
            patch("app.services.llm.cache.get_cached_response", new_callable=AsyncMock, return_value=None),
            patch("app.services.llm.cache.cache_response", new_callable=AsyncMock),
        ):
            resposta = await gerar_resposta_julia(
                mensagem="Oi, tem vaga?",
                contexto=contexto,
                medico=medico,
                conversa=conversa,
            )
            assert isinstance(resposta, str)
            assert len(resposta) > 0

    @pytest.mark.asyncio
    async def test_sem_tools(self, medico, conversa, contexto, mock_conhecimento, mock_llm_services):
        from app.services.agente import gerar_resposta_julia

        with (
            patch(
                "app.services.conversation_mode.response_validator.validar_resposta_julia",
                return_value=(True, None),
            ),
            patch("app.services.conversation_mode.response_validator.get_fallback_response"),
            patch("app.services.llm.cache.get_cached_response", new_callable=AsyncMock, return_value=None),
            patch("app.services.llm.cache.cache_response", new_callable=AsyncMock),
        ):
            resposta = await gerar_resposta_julia(
                mensagem="Oi!",
                contexto=contexto,
                medico=medico,
                conversa=conversa,
                usar_tools=False,
            )
            assert isinstance(resposta, str)
            # Quando usar_tools=False, chama gerar_resposta (sem tools)
            mock_llm_services["gerar_resposta"].assert_called_once()

    @pytest.mark.asyncio
    async def test_com_cache_hit(self, medico, conversa, contexto, mock_conhecimento, mock_llm_services):
        from app.services.agente import gerar_resposta_julia

        with (
            patch(
                "app.services.conversation_mode.response_validator.validar_resposta_julia",
                return_value=(True, None),
            ),
            patch("app.services.conversation_mode.response_validator.get_fallback_response"),
            patch("app.services.llm.cache.get_cached_response", new_callable=AsyncMock, return_value="Cached response"),
            patch("app.services.llm.cache.cache_response", new_callable=AsyncMock),
        ):
            resposta = await gerar_resposta_julia(
                mensagem="Oi!",
                contexto=contexto,
                medico=medico,
                conversa=conversa,
                usar_tools=False,
            )
            assert resposta == "Cached response"
            # LLM não deve ser chamado quando cache hit
            mock_llm_services["gerar_resposta"].assert_not_called()

    @pytest.mark.asyncio
    async def test_timeout_retorna_fallback(self, medico, conversa, contexto, mock_conhecimento):
        import asyncio
        from app.services.agente import gerar_resposta_julia, RESPOSTA_TIMEOUT_FALLBACK

        async def slow_impl(**kwargs):
            await asyncio.sleep(10)
            return "never reaches"

        with (
            patch("app.services.agente._gerar_resposta_julia_impl", side_effect=slow_impl),
            patch("app.services.llm.cache.get_cached_response", new_callable=AsyncMock, return_value=None),
            patch("app.services.llm.cache.cache_response", new_callable=AsyncMock),
            patch("app.services.agente.TIMEOUT_GERACAO_RESPOSTA", 0.01),
        ):
            resposta = await gerar_resposta_julia(
                mensagem="Oi!",
                contexto=contexto,
                medico=medico,
                conversa=conversa,
            )
            assert resposta == RESPOSTA_TIMEOUT_FALLBACK

    @pytest.mark.asyncio
    async def test_com_policy_decision(self, medico, conversa, contexto, mock_conhecimento, mock_llm_services):
        from app.services.agente import gerar_resposta_julia
        from app.services.policy import PolicyDecision, PrimaryAction, Tone

        decision = PolicyDecision(
            primary_action=PrimaryAction.OFFER,
            allowed_actions=["oferta"],
            forbidden_actions=[],
            tone=Tone.LEVE,
            requires_human=False,
            constraints_text="Seja breve",
            reasoning="Teste",
            rule_id="test_rule",
        )

        with (
            patch(
                "app.services.conversation_mode.response_validator.validar_resposta_julia",
                return_value=(True, None),
            ),
            patch("app.services.conversation_mode.response_validator.get_fallback_response"),
            patch("app.services.llm.cache.get_cached_response", new_callable=AsyncMock, return_value=None),
            patch("app.services.llm.cache.cache_response", new_callable=AsyncMock),
        ):
            resposta = await gerar_resposta_julia(
                mensagem="Oi!",
                contexto=contexto,
                medico=medico,
                conversa=conversa,
                policy_decision=decision,
            )
            assert isinstance(resposta, str)


# =============================================================================
# processar_mensagem_completo
# =============================================================================


class TestProcessarMensagemCompleto:
    """Testa processar_mensagem_completo - fluxo principal."""

    @pytest.mark.asyncio
    async def test_retorna_processamento_result(self, medico, conversa, mock_conhecimento):
        from app.services.agente import processar_mensagem_completo, ProcessamentoResult

        with (
            patch("app.services.contexto.montar_contexto_completo", new_callable=AsyncMock) as mock_ctx,
            patch("app.services.agente.load_doctor_state", new_callable=AsyncMock) as mock_state,
            patch("app.services.agente.save_doctor_state_updates", new_callable=AsyncMock),
            patch("app.services.agente.PolicyDecide") as MockPolicy,
            patch("app.services.agente.StateUpdate") as MockStateUpdate,
            patch("app.services.agente.log_policy_decision") as mock_log_pd,
            patch("app.services.agente.log_policy_effect"),
            patch("app.services.agente.get_mode_router") as mock_mode_router,
            patch("app.services.agente.CapabilitiesGate") as MockGate,
            patch("app.services.agente.gerar_resposta_julia", new_callable=AsyncMock) as mock_gerar,
            patch("app.services.agente.safe_create_task"),
        ):
            mock_ctx.return_value = {
                "medico": "Dr. Teste",
                "vagas": "",
                "historico": "",
                "historico_raw": [],
                "primeira_msg": False,
                "data_hora_atual": "",
                "dia_semana": "",
                "campanha": None,
            }

            mock_doctor_state = MagicMock()
            mock_doctor_state.permission_state.value = "active"
            mock_doctor_state.temperature = 50
            mock_state.return_value = mock_doctor_state

            mock_state_updater = MagicMock()
            mock_state_updater.on_inbound_message.return_value = {"temperature": 55}
            mock_state_updater.on_outbound_message.return_value = {"last_outbound_at": "now"}
            MockStateUpdate.return_value = mock_state_updater

            from app.services.policy import PrimaryAction

            mock_decision = MagicMock()
            mock_decision.primary_action = PrimaryAction.OFFER
            mock_decision.requires_human = False
            mock_decision.constraints_text = ""
            mock_decision.reasoning = "Normal"
            mock_decision.rule_id = "default"
            MockPolicy.return_value.decide = AsyncMock(return_value=mock_decision)

            mock_log_pd.return_value = "pd-123"

            # Mode router
            mock_mode_info = MagicMock()
            mock_mode_info.mode.value = "prospeccao"
            mock_mode_info.pending_transition = None
            mock_mode_router.return_value.process = AsyncMock(return_value=mock_mode_info)

            # Gate
            MockGate.return_value = MagicMock()

            mock_gerar.return_value = "Oi Dr! Tudo bem?"

            result = await processar_mensagem_completo(
                mensagem_texto="Oi, tudo bem?",
                medico=medico,
                conversa=conversa,
            )

            assert isinstance(result, ProcessamentoResult)
            assert result.resposta == "Oi Dr! Tudo bem?"
            assert result.policy_decision_id == "pd-123"

    @pytest.mark.asyncio
    async def test_conversa_humana_nao_processa(self, medico, conversa):
        from app.services.agente import processar_mensagem_completo, ProcessamentoResult

        conversa_humana = {**conversa, "controlled_by": "human"}
        result = await processar_mensagem_completo(
            mensagem_texto="Oi!",
            medico=medico,
            conversa=conversa_humana,
        )
        assert isinstance(result, ProcessamentoResult)
        assert result.resposta is None

    @pytest.mark.asyncio
    async def test_handoff_retorna_mensagem_padrao(self, medico, conversa, mock_conhecimento):
        from app.services.agente import processar_mensagem_completo, ProcessamentoResult

        with (
            patch("app.services.contexto.montar_contexto_completo", new_callable=AsyncMock) as mock_ctx,
            patch("app.services.agente.load_doctor_state", new_callable=AsyncMock) as mock_state,
            patch("app.services.agente.save_doctor_state_updates", new_callable=AsyncMock),
            patch("app.services.agente.PolicyDecide") as MockPolicy,
            patch("app.services.agente.StateUpdate") as MockStateUpdate,
            patch("app.services.agente.log_policy_decision", return_value="pd-123"),
            patch("app.services.agente.log_policy_effect"),
            patch("app.services.handoff.criar_handoff", new_callable=AsyncMock),
        ):
            mock_ctx.return_value = {
                "medico": "",
                "vagas": "",
                "historico": "",
                "historico_raw": [],
                "primeira_msg": False,
                "data_hora_atual": "",
                "dia_semana": "",
                "campanha": None,
            }

            mock_doctor_state = MagicMock()
            mock_doctor_state.permission_state.value = "active"
            mock_doctor_state.temperature = 50
            mock_state.return_value = mock_doctor_state

            mock_state_updater = MagicMock()
            mock_state_updater.on_inbound_message.return_value = {}
            MockStateUpdate.return_value = mock_state_updater

            mock_decision = MagicMock()
            mock_decision.requires_human = True
            mock_decision.reasoning = "Médico irritado"
            mock_decision.rule_id = "grave_objection"
            MockPolicy.return_value.decide = AsyncMock(return_value=mock_decision)

            result = await processar_mensagem_completo(
                mensagem_texto="Quero falar com alguém de verdade",
                medico=medico,
                conversa=conversa,
            )

            assert isinstance(result, ProcessamentoResult)
            assert "supervisora" in result.resposta
            assert result.policy_decision_id == "pd-123"

    @pytest.mark.asyncio
    async def test_wait_nao_retorna_resposta(self, medico, conversa, mock_conhecimento):
        from app.services.agente import processar_mensagem_completo
        from app.services.policy import PrimaryAction

        with (
            patch("app.services.contexto.montar_contexto_completo", new_callable=AsyncMock) as mock_ctx,
            patch("app.services.agente.load_doctor_state", new_callable=AsyncMock) as mock_state,
            patch("app.services.agente.save_doctor_state_updates", new_callable=AsyncMock),
            patch("app.services.agente.PolicyDecide") as MockPolicy,
            patch("app.services.agente.StateUpdate") as MockStateUpdate,
            patch("app.services.agente.log_policy_decision", return_value="pd-456"),
            patch("app.services.agente.log_policy_effect"),
        ):
            mock_ctx.return_value = {
                "medico": "",
                "vagas": "",
                "historico": "",
                "historico_raw": [],
                "primeira_msg": False,
                "data_hora_atual": "",
                "dia_semana": "",
                "campanha": None,
            }

            mock_doctor_state = MagicMock()
            mock_doctor_state.permission_state.value = "active"
            mock_doctor_state.temperature = 50
            mock_state.return_value = mock_doctor_state

            mock_state_updater = MagicMock()
            mock_state_updater.on_inbound_message.return_value = {}
            MockStateUpdate.return_value = mock_state_updater

            mock_decision = MagicMock()
            mock_decision.requires_human = False
            mock_decision.primary_action = PrimaryAction.WAIT
            mock_decision.reasoning = "Cooling off"
            mock_decision.rule_id = "cooling_off"
            MockPolicy.return_value.decide = AsyncMock(return_value=mock_decision)

            result = await processar_mensagem_completo(
                mensagem_texto="...",
                medico=medico,
                conversa=conversa,
            )

            assert result.resposta is None
            assert result.policy_decision_id == "pd-456"
            assert result.rule_matched == "cooling_off"

    @pytest.mark.asyncio
    async def test_erro_retorna_result_vazio(self, medico, conversa):
        from app.services.agente import processar_mensagem_completo, ProcessamentoResult

        with patch(
            "app.services.contexto.montar_contexto_completo",
            new_callable=AsyncMock,
            side_effect=Exception("Erro genérico"),
        ):
            result = await processar_mensagem_completo(
                mensagem_texto="Oi!",
                medico=medico,
                conversa=conversa,
            )
            assert isinstance(result, ProcessamentoResult)
            assert result.resposta is None


# =============================================================================
# Helpers e constantes
# =============================================================================


class TestConstantesEHelpers:
    """Testa constantes e funções auxiliares."""

    def test_julia_tools_lista(self):
        from app.services.agente import JULIA_TOOLS

        assert isinstance(JULIA_TOOLS, list)
        assert len(JULIA_TOOLS) == 7  # 5 base + 2 intermediação

        nomes = [t["name"] for t in JULIA_TOOLS]
        assert "buscar_vagas" in nomes
        assert "reservar_plantao" in nomes
        assert "buscar_info_hospital" in nomes
        assert "agendar_lembrete" in nomes
        assert "salvar_memoria" in nomes
        assert "criar_handoff_externo" in nomes
        assert "registrar_status_intermediacao" in nomes

    def test_resposta_timeout_fallback(self):
        from app.services.agente import RESPOSTA_TIMEOUT_FALLBACK

        assert isinstance(RESPOSTA_TIMEOUT_FALLBACK, str)
        assert len(RESPOSTA_TIMEOUT_FALLBACK) > 0

    def test_resposta_parece_incompleta(self):
        from app.services.agente import _resposta_parece_incompleta

        # Respostas completas
        assert not _resposta_parece_incompleta("Oi! Tudo bem?")
        assert not _resposta_parece_incompleta("")
        assert not _resposta_parece_incompleta("Qualquer resposta", stop_reason="tool_use")

        # Respostas incompletas
        assert _resposta_parece_incompleta("Vou verificar o que temos:")
        assert _resposta_parece_incompleta("Deixa eu ver...")

    @pytest.mark.asyncio
    async def test_processar_tool_call_desconhecida(self):
        from app.services.agente import processar_tool_call

        result = await processar_tool_call(
            tool_name="tool_inexistente",
            tool_input={},
            medico={},
            conversa={},
        )
        assert result["success"] is False
        assert "desconhecida" in result["error"]

    def test_processamento_result_dataclass(self):
        from app.services.agente import ProcessamentoResult

        result = ProcessamentoResult()
        assert result.resposta is None
        assert result.policy_decision_id is None
        assert result.rule_matched is None

        result2 = ProcessamentoResult(
            resposta="Oi!",
            policy_decision_id="pd-123",
            rule_matched="test_rule",
        )
        assert result2.resposta == "Oi!"
        assert result2.policy_decision_id == "pd-123"
