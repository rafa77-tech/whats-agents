"""
Testes para o agente Julia no Slack.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.agente_slack import AgenteSlack, processar_mensagem_slack
from app.tools.slack_tools import (
    SLACK_TOOLS,
    TOOLS_CRITICAS,
    executar_tool,
    _buscar_medico_por_identificador,
    _calcular_datas_periodo,
)


class TestSlackTools:
    """Testes das tools disponíveis."""

    def test_tools_definidas(self):
        """Verifica se todas as tools estão definidas."""
        assert len(SLACK_TOOLS) >= 10, "Deve ter pelo menos 10 tools"

        nomes = [t["name"] for t in SLACK_TOOLS]
        assert "enviar_mensagem" in nomes
        assert "buscar_metricas" in nomes
        assert "comparar_periodos" in nomes
        assert "buscar_medico" in nomes
        assert "listar_medicos" in nomes
        assert "bloquear_medico" in nomes
        assert "buscar_vagas" in nomes
        assert "status_sistema" in nomes

    def test_tools_formato_claude(self):
        """Verifica se tools estão no formato correto para Claude."""
        for tool in SLACK_TOOLS:
            assert "name" in tool, f"Tool sem name: {tool}"
            assert "description" in tool, f"Tool sem description: {tool}"
            assert "input_schema" in tool, f"Tool sem input_schema: {tool}"
            assert tool["input_schema"]["type"] == "object"

    def test_tools_criticas_definidas(self):
        """Verifica se tools críticas estão corretamente marcadas."""
        assert "enviar_mensagem" in TOOLS_CRITICAS
        assert "bloquear_medico" in TOOLS_CRITICAS
        assert "reservar_vaga" in TOOLS_CRITICAS
        assert "pausar_julia" in TOOLS_CRITICAS

        # Tools de leitura NÃO devem ser críticas
        assert "buscar_metricas" not in TOOLS_CRITICAS
        assert "buscar_medico" not in TOOLS_CRITICAS
        assert "status_sistema" not in TOOLS_CRITICAS


class TestAgenteSlack:
    """Testes do agente conversacional."""

    def test_agente_inicializa(self):
        """Verifica inicialização do agente."""
        agente = AgenteSlack(user_id="U123", channel_id="C456")

        assert agente.user_id == "U123"
        assert agente.channel_id == "C456"
        assert agente.mensagens == []
        assert agente.sessao is None

    @pytest.mark.asyncio
    @patch("app.services.agente_slack.supabase")
    async def test_criar_sessao(self, mock_supabase):
        """Verifica criação de nova sessão."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        agente = AgenteSlack(user_id="U123", channel_id="C456")
        await agente._carregar_sessao()

        assert agente.sessao is not None
        assert agente.sessao["user_id"] == "U123"
        assert agente.sessao["channel_id"] == "C456"
        assert agente.sessao["mensagens"] == []

    def test_preparar_contexto_vazio(self):
        """Verifica contexto inicial."""
        agente = AgenteSlack(user_id="U123", channel_id="C456")
        agente.sessao = {"contexto": {}}

        contexto = agente._preparar_contexto()

        assert "Data/hora:" in contexto

    def test_preparar_contexto_com_metricas(self):
        """Verifica contexto com métricas anteriores."""
        agente = AgenteSlack(user_id="U123", channel_id="C456")
        agente.sessao = {
            "contexto": {
                "ultimo_buscar_metricas": {
                    "success": True,
                    "metricas": {
                        "enviadas": 45,
                        "respostas": 12
                    }
                }
            }
        }

        contexto = agente._preparar_contexto()

        assert "12 respostas de 45 envios" in contexto

    def test_gerar_preview_enviar_mensagem(self):
        """Verifica preview para enviar mensagem."""
        agente = AgenteSlack(user_id="U123", channel_id="C456")

        preview = agente._gerar_preview_confirmacao(
            "enviar_mensagem",
            {"telefone": "11999887766", "instrucao": "oferecer vaga"}
        )

        # Telefone agora eh formatado: `11 99988-7766`
        assert "99988-7766" in preview
        assert "oferecer vaga" in preview
        assert "enviar" in preview.lower()

    def test_gerar_preview_bloquear(self):
        """Verifica preview para bloqueio."""
        agente = AgenteSlack(user_id="U123", channel_id="C456")

        preview = agente._gerar_preview_confirmacao(
            "bloquear_medico",
            {"telefone": "11999887766"}
        )

        # Telefone agora eh formatado: `11 99988-7766`
        assert "99988-7766" in preview
        assert "bloquear" in preview.lower()

    def test_formatar_sucesso_enviar(self):
        """Verifica formatação de sucesso para envio."""
        agente = AgenteSlack(user_id="U123", channel_id="C456")

        resposta = agente._formatar_sucesso(
            "enviar_mensagem",
            {"success": True, "nome": "Dr Carlos", "telefone": "11999887766"}
        )

        assert "Dr Carlos" in resposta
        assert "mandei" in resposta.lower() or "pronto" in resposta.lower()

    def test_formatar_sucesso_bloquear(self):
        """Verifica formatação de sucesso para bloqueio."""
        agente = AgenteSlack(user_id="U123", channel_id="C456")

        resposta = agente._formatar_sucesso(
            "bloquear_medico",
            {"success": True, "nome": "Dr Carlos"}
        )

        assert "Dr Carlos" in resposta
        assert "bloqueado" in resposta.lower()


class TestConfirmacao:
    """Testes do fluxo de confirmação."""

    @pytest.mark.asyncio
    async def test_detecta_confirmacao_sim(self):
        """Verifica detecção de confirmação positiva."""
        agente = AgenteSlack(user_id="U123", channel_id="C456")
        agente.sessao = {
            "acao_pendente": {
                "tool_name": "bloquear_medico",
                "tool_input": {"telefone": "11999"},
                "tool_id": "abc123"
            },
            "contexto": {}
        }

        # Mock da execução
        with patch("app.services.agente_slack.executar_tool") as mock_exec:
            mock_exec.return_value = {"success": True, "nome": "Dr Carlos"}

            resposta = await agente._processar_confirmacao("sim")

            assert resposta is not None
            assert "bloqueado" in resposta.lower() or "Dr Carlos" in resposta
            mock_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_detecta_cancelamento(self):
        """Verifica detecção de cancelamento."""
        agente = AgenteSlack(user_id="U123", channel_id="C456")
        agente.sessao = {
            "acao_pendente": {
                "tool_name": "bloquear_medico",
                "tool_input": {"telefone": "11999"},
                "tool_id": "abc123"
            },
            "contexto": {}
        }

        resposta = await agente._processar_confirmacao("nao")

        assert resposta is not None
        assert "cancelado" in resposta.lower()
        assert agente.sessao["acao_pendente"] is None

    @pytest.mark.asyncio
    async def test_mensagem_normal_sem_acao_pendente(self):
        """Verifica que mensagem normal não é tratada como confirmação."""
        agente = AgenteSlack(user_id="U123", channel_id="C456")
        agente.sessao = {"acao_pendente": None, "contexto": {}}

        resposta = await agente._processar_confirmacao("sim")

        assert resposta is None  # Não era confirmação


class TestToolExecution:
    """Testes de execução de tools."""

    @pytest.mark.asyncio
    @patch("app.tools.slack_tools.supabase")
    async def test_buscar_metricas_hoje(self, mock_supabase):
        """Verifica busca de métricas."""
        # Mock das queries
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(count=10)

        result = await executar_tool("buscar_metricas", {"periodo": "hoje"}, "U123")

        assert result["success"] is True
        assert "metricas" in result

    @pytest.mark.asyncio
    @patch("app.tools.slack_tools.supabase")
    async def test_status_sistema(self, mock_supabase):
        """Verifica status do sistema."""
        mock_supabase.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"status": "ativo"}]
        )
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(count=5)
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(count=20)

        result = await executar_tool("status_sistema", {}, "U123")

        assert result["success"] is True
        assert "status" in result

    @pytest.mark.asyncio
    async def test_tool_inexistente(self):
        """Verifica erro para tool inexistente."""
        result = await executar_tool("tool_que_nao_existe", {}, "U123")

        assert result["success"] is False
        assert "error" in result


class TestCalculoDatas:
    """Testes de cálculo de datas para períodos."""

    def test_calcular_periodo_hoje(self):
        """Verifica cálculo para hoje."""
        inicio, fim = _calcular_datas_periodo("hoje")

        assert inicio.hour == 0
        assert inicio.minute == 0
        assert fim >= inicio

    def test_calcular_periodo_ontem(self):
        """Verifica cálculo para ontem."""
        inicio, fim = _calcular_datas_periodo("ontem")

        assert inicio.hour == 0
        assert fim.hour == 0
        assert inicio < fim

    def test_calcular_periodo_semana(self):
        """Verifica cálculo para semana."""
        from datetime import datetime, timezone, timedelta

        inicio, fim = _calcular_datas_periodo("semana")
        agora = datetime.now(timezone.utc)

        # Deve ser aproximadamente 7 dias atrás
        diff = (fim - inicio).days
        assert diff >= 6 and diff <= 8

    def test_calcular_periodo_semana_passada(self):
        """Verifica cálculo para semana passada."""
        inicio, fim = _calcular_datas_periodo("semana_passada")

        # Semana passada: 14 dias atrás até 7 dias atrás
        diff = (fim - inicio).days
        assert diff >= 6 and diff <= 8

    def test_calcular_periodo_mes(self):
        """Verifica cálculo para mês."""
        inicio, fim = _calcular_datas_periodo("mes")

        diff = (fim - inicio).days
        assert diff >= 29 and diff <= 31


class TestCompararPeriodos:
    """Testes da tool comparar_periodos."""

    @pytest.mark.asyncio
    @patch("app.tools.slack_tools.supabase")
    async def test_comparar_semana_vs_semana_passada(self, mock_supabase):
        """Verifica comparação entre semanas."""
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value = MagicMock(count=10)

        result = await executar_tool(
            "comparar_periodos",
            {"periodo1": "semana", "periodo2": "semana_passada"},
            "U123"
        )

        assert result["success"] is True
        assert "periodo1" in result
        assert "periodo2" in result
        assert "variacao" in result
        assert "tendencia" in result["variacao"]


class TestInterpretacaoIntencao:
    """Testes de interpretação de intenção (cenários de uso)."""

    def test_variacoes_enviar_mensagem(self):
        """Documenta variações que devem ser interpretadas como enviar_mensagem."""
        variacoes = [
            "manda msg pro 11999887766",
            "contata o 11999887766",
            "fala com o Dr Carlos",
            "envia uma mensagem pro 11999",
            "manda uma msg oferecendo a vaga",
        ]
        # Estas variações devem ser interpretadas pelo LLM
        # Este teste documenta os casos esperados
        assert len(variacoes) > 0

    def test_variacoes_metricas(self):
        """Documenta variações que devem ser interpretadas como buscar_metricas."""
        variacoes = [
            "como foi hoje?",
            "quantos responderam?",
            "qual a taxa de resposta?",
            "como ta essa semana?",
            "me mostra os numeros",
        ]
        assert len(variacoes) > 0

    def test_variacoes_bloquear(self):
        """Documenta variações que devem ser interpretadas como bloquear_medico."""
        variacoes = [
            "bloqueia o 11999",
            "tira ele da lista",
            "nao manda mais msg pro Dr Carlos",
            "para de contatar esse numero",
        ]
        assert len(variacoes) > 0
