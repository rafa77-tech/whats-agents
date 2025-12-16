"""
Testes do executor de briefings.

Sprint 11 - Epic 05: Execucao e Historico
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.briefing_executor import (
    StatusPasso,
    PassoResult,
    ExecutionResult,
    BriefingExecutor,
    mapear_passo_para_tool,
    extrair_parametros_passo,
    TOOL_KEYWORDS,
    executar_briefing,
)
from app.services.briefing_analyzer import AnaliseResult, PassoPlano, TipoDemanda
from app.services.briefing_aprovacao import StatusAprovacao


class TestStatusPasso:
    """Testes do enum StatusPasso."""

    def test_status_existem(self):
        """Todos os status esperados existem."""
        assert StatusPasso.PENDENTE.value == "pendente"
        assert StatusPasso.EXECUTANDO.value == "executando"
        assert StatusPasso.CONCLUIDO.value == "concluido"
        assert StatusPasso.FALHOU.value == "falhou"
        assert StatusPasso.PULADO.value == "pulado"
        assert StatusPasso.AGUARDANDO_AJUDA.value == "aguardando_ajuda"


class TestPassoResult:
    """Testes do dataclass PassoResult."""

    def test_cria_passo_result_basico(self):
        """Cria PassoResult basico."""
        resultado = PassoResult(
            numero=1,
            descricao="Buscar medicos",
            status=StatusPasso.PENDENTE
        )
        assert resultado.numero == 1
        assert resultado.status == StatusPasso.PENDENTE
        assert resultado.inicio is None

    def test_duracao_segundos(self):
        """Calcula duracao corretamente."""
        inicio = datetime(2025, 12, 15, 14, 30, 0)
        fim = datetime(2025, 12, 15, 14, 30, 45)

        resultado = PassoResult(
            numero=1,
            descricao="Teste",
            status=StatusPasso.CONCLUIDO,
            inicio=inicio,
            fim=fim
        )

        assert resultado.duracao_segundos() == 45.0

    def test_duracao_sem_fim(self):
        """Duracao None se sem fim."""
        resultado = PassoResult(
            numero=1,
            descricao="Teste",
            status=StatusPasso.EXECUTANDO,
            inicio=datetime.now()
        )

        assert resultado.duracao_segundos() is None


class TestExecutionResult:
    """Testes do dataclass ExecutionResult."""

    def test_cria_execution_result(self):
        """Cria ExecutionResult corretamente."""
        resultado = ExecutionResult(
            briefing_id="bp1",
            doc_nome="briefing-teste",
            inicio=datetime.now()
        )

        assert resultado.briefing_id == "bp1"
        assert resultado.status == StatusAprovacao.EXECUTANDO
        assert resultado.passos_resultados == []

    def test_to_dict(self):
        """Converte para dicionario."""
        resultado = ExecutionResult(
            briefing_id="bp1",
            doc_nome="teste",
            inicio=datetime(2025, 12, 15, 14, 30),
            fim=datetime(2025, 12, 15, 14, 35),
            status=StatusAprovacao.CONCLUIDO,
            passos_resultados=[
                PassoResult(
                    numero=1,
                    descricao="Passo 1",
                    status=StatusPasso.CONCLUIDO,
                    inicio=datetime(2025, 12, 15, 14, 30),
                    fim=datetime(2025, 12, 15, 14, 31)
                )
            ],
            metricas={"total": 1}
        )

        d = resultado.to_dict()

        assert d["briefing_id"] == "bp1"
        assert d["status"] == "concluido"
        assert d["inicio"] == "2025-12-15T14:30:00"
        assert len(d["passos_resultados"]) == 1
        assert d["passos_resultados"][0]["status"] == "concluido"


class TestToolKeywords:
    """Testes das keywords de tools."""

    def test_keywords_enviar_mensagem(self):
        """Keywords de enviar mensagem existem."""
        assert "enviar" in TOOL_KEYWORDS["enviar_mensagem"]
        assert "mensagem" in TOOL_KEYWORDS["enviar_mensagem"]
        assert "whatsapp" in TOOL_KEYWORDS["enviar_mensagem"]

    def test_keywords_buscar_medico(self):
        """Keywords de buscar medico existem."""
        assert "buscar medico" in TOOL_KEYWORDS["buscar_medico"]

    def test_keywords_listar_medicos(self):
        """Keywords de listar medicos existem."""
        assert "listar medicos" in TOOL_KEYWORDS["listar_medicos"]

    def test_keywords_buscar_vagas(self):
        """Keywords de buscar vagas existem."""
        assert "buscar vagas" in TOOL_KEYWORDS["buscar_vagas"]


class TestMapearPassoParaTool:
    """Testes da funcao mapear_passo_para_tool."""

    def test_mapeia_enviar_mensagem(self):
        """Mapeia passo de enviar mensagem."""
        passo = PassoPlano(numero=1, descricao="Enviar mensagem para os medicos")
        assert mapear_passo_para_tool(passo) == "enviar_mensagem"

    def test_mapeia_buscar_vagas(self):
        """Mapeia passo de buscar vagas."""
        passo = PassoPlano(numero=1, descricao="Buscar vagas disponiveis no Sao Luiz")
        assert mapear_passo_para_tool(passo) == "buscar_vagas"

    def test_mapeia_listar_medicos(self):
        """Mapeia passo de listar medicos."""
        passo = PassoPlano(numero=1, descricao="Listar medicos da regiao ABC")
        assert mapear_passo_para_tool(passo) == "listar_medicos"

    def test_mapeia_metricas(self):
        """Mapeia passo de metricas."""
        passo = PassoPlano(numero=1, descricao="Verificar metricas de performance")
        assert mapear_passo_para_tool(passo) == "buscar_metricas"

    def test_nao_mapeia_desconhecido(self):
        """Retorna None para passo nao mapeavel."""
        passo = PassoPlano(numero=1, descricao="Fazer algo manual que nao tem tool")
        assert mapear_passo_para_tool(passo) is None

    def test_case_insensitive(self):
        """Mapeamento eh case insensitive."""
        passo = PassoPlano(numero=1, descricao="ENVIAR MENSAGEM URGENTE")
        assert mapear_passo_para_tool(passo) == "enviar_mensagem"


class TestExtrairParametrosPasso:
    """Testes da funcao extrair_parametros_passo."""

    def test_retorna_dict_vazio(self):
        """Por enquanto retorna dict vazio (TODO: usar LLM)."""
        passo = PassoPlano(numero=1, descricao="Enviar para 11999887766")
        params = extrair_parametros_passo(passo, "enviar_mensagem")
        assert params == {}


class TestBriefingExecutor:
    """Testes do BriefingExecutor."""

    def test_init(self):
        """Inicializa executor corretamente."""
        executor = BriefingExecutor("C123", "U456")
        assert executor.channel_id == "C123"
        assert executor.user_id == "U456"

    @pytest.mark.asyncio
    async def test_executar_passo_com_tool(self):
        """Executa passo que tem tool mapeada."""
        executor = BriefingExecutor("C123", "U456")
        passo = PassoPlano(numero=1, descricao="Buscar vagas disponiveis")

        with patch("app.tools.slack.executar_tool", new_callable=AsyncMock) as mock_tool:
            mock_tool.return_value = {"success": True, "vagas": []}

            with patch("app.services.briefing_executor.adicionar_linha_historico", new_callable=AsyncMock):
                resultado = await executor._executar_passo(passo, "doc1")

        assert resultado.status == StatusPasso.CONCLUIDO
        assert resultado.tool_usada == "buscar_vagas"
        mock_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_executar_passo_sem_tool(self):
        """Pula passo que nao tem tool."""
        executor = BriefingExecutor("C123", "U456")
        passo = PassoPlano(numero=1, descricao="Fazer algo manual impossivel")

        with patch("app.services.briefing_executor.adicionar_linha_historico", new_callable=AsyncMock):
            resultado = await executor._executar_passo(passo, "doc1")

        assert resultado.status == StatusPasso.PULADO
        assert resultado.tool_usada is None

    @pytest.mark.asyncio
    async def test_executar_passo_requer_ajuda(self):
        """Marca como aguardando ajuda quando requer_ajuda=True."""
        executor = BriefingExecutor("C123", "U456")
        passo = PassoPlano(
            numero=1,
            descricao="Passo que precisa de ajuda",
            requer_ajuda=True,
            tipo_ajuda="decisao"
        )

        with patch("app.services.briefing_executor.adicionar_linha_historico", new_callable=AsyncMock):
            resultado = await executor._executar_passo(passo, "doc1")

        assert resultado.status == StatusPasso.AGUARDANDO_AJUDA

    @pytest.mark.asyncio
    async def test_executar_passo_tool_falha(self):
        """Marca como falhou quando tool retorna erro."""
        executor = BriefingExecutor("C123", "U456")
        passo = PassoPlano(numero=1, descricao="Buscar vagas")

        with patch("app.tools.slack.executar_tool", new_callable=AsyncMock) as mock_tool:
            mock_tool.return_value = {"success": False, "error": "Erro de conexao"}

            with patch("app.services.briefing_executor.adicionar_linha_historico", new_callable=AsyncMock):
                resultado = await executor._executar_passo(passo, "doc1")

        assert resultado.status == StatusPasso.FALHOU
        assert "conexao" in resultado.erro

    def test_calcular_metricas(self):
        """Calcula metricas corretamente."""
        executor = BriefingExecutor("C123", "U456")

        resultado = ExecutionResult(
            briefing_id="bp1",
            doc_nome="teste",
            inicio=datetime(2025, 12, 15, 14, 30),
            fim=datetime(2025, 12, 15, 14, 35),
            passos_resultados=[
                PassoResult(1, "P1", StatusPasso.CONCLUIDO),
                PassoResult(2, "P2", StatusPasso.CONCLUIDO),
                PassoResult(3, "P3", StatusPasso.FALHOU),
                PassoResult(4, "P4", StatusPasso.PULADO),
            ]
        )

        metricas = executor._calcular_metricas(resultado)

        assert metricas["total_passos"] == 4
        assert metricas["passos_concluidos"] == 2
        assert metricas["passos_falhos"] == 1
        assert metricas["passos_pulados"] == 1
        assert metricas["taxa_sucesso"] == 0.5
        assert metricas["duracao_segundos"] == 300  # 5 minutos

    @pytest.mark.asyncio
    async def test_executar_briefing_completo(self):
        """Executa briefing completo com multiplos passos."""
        plano = AnaliseResult(
            doc_id="doc1",
            doc_nome="campanha-teste",
            resumo_demanda="Teste",
            passos=[
                PassoPlano(numero=1, descricao="Buscar vagas disponiveis"),
                PassoPlano(numero=2, descricao="Listar medicos"),
            ]
        )

        with patch("app.tools.slack.executar_tool", new_callable=AsyncMock) as mock_tool:
            mock_tool.return_value = {"success": True}

            with patch("app.services.briefing_executor.supabase"):
                with patch("app.services.briefing_executor.adicionar_linha_historico", new_callable=AsyncMock):
                    with patch("app.services.briefing_executor.enviar_slack", new_callable=AsyncMock):
                        executor = BriefingExecutor("C123", "U456")
                        resultado = await executor.executar("bp1", plano)

        assert resultado.status == StatusAprovacao.CONCLUIDO
        assert len(resultado.passos_resultados) == 2
        assert resultado.metricas["passos_concluidos"] == 2


class TestExecutarBriefingConveniencia:
    """Testes da funcao de conveniencia executar_briefing."""

    @pytest.mark.asyncio
    async def test_funcao_conveniencia(self):
        """Funcao de conveniencia executa briefing."""
        plano = AnaliseResult(
            doc_id="doc1",
            doc_nome="teste",
            passos=[]
        )

        with patch("app.services.briefing_executor.supabase"):
            with patch("app.services.briefing_executor.enviar_slack", new_callable=AsyncMock):
                resultado = await executar_briefing("bp1", plano, "C123", "U456")

        assert resultado.briefing_id == "bp1"
        assert resultado.doc_nome == "teste"


class TestNotificacoes:
    """Testes das funcoes de notificacao."""

    @pytest.mark.asyncio
    async def test_notifica_progresso_apenas_falhas(self):
        """Notifica apenas passos que falharam."""
        executor = BriefingExecutor("C123", "U456")

        passo_ok = PassoPlano(numero=1, descricao="Passo OK")
        resultado_ok = PassoResult(1, "OK", StatusPasso.CONCLUIDO)

        passo_erro = PassoPlano(numero=2, descricao="Passo com erro")
        resultado_erro = PassoResult(2, "Erro", StatusPasso.FALHOU)

        with patch("app.services.briefing_executor.enviar_slack", new_callable=AsyncMock) as mock_slack:
            # Passo OK nao notifica
            await executor._notificar_progresso("doc", passo_ok, resultado_ok)
            mock_slack.assert_not_called()

            # Passo com erro notifica
            await executor._notificar_progresso("doc", passo_erro, resultado_erro)
            mock_slack.assert_called_once()

    @pytest.mark.asyncio
    async def test_notifica_conclusao(self):
        """Notifica conclusao do briefing."""
        executor = BriefingExecutor("C123", "U456")

        resultado = ExecutionResult(
            briefing_id="bp1",
            doc_nome="campanha",
            inicio=datetime.now(),
            fim=datetime.now(),
            status=StatusAprovacao.CONCLUIDO,
            metricas={
                "total_passos": 5,
                "passos_concluidos": 4,
                "passos_falhos": 1,
                "passos_aguardando": 0,
                "duracao_segundos": 120,
            }
        )

        with patch("app.services.briefing_executor.enviar_slack", new_callable=AsyncMock) as mock_slack:
            await executor._notificar_conclusao(resultado)

        mock_slack.assert_called_once()
        chamada = mock_slack.call_args[0][0]
        assert "campanha" in chamada["text"]
        assert "4/5" in chamada["text"]
