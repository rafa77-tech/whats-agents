"""
Testes da tool processar_briefing.

Sprint 11 - Epic 01: Briefing sob Demanda
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.tools.slack.briefing import (
    TOOL_PROCESSAR_BRIEFING,
    handle_processar_briefing,
    _listar_briefings,
    _ler_briefing,
)
from app.services.google_docs import DocInfo, DocContent


class TestToolSchema:
    """Testes do schema da tool."""

    def test_tool_name(self):
        """Tool tem nome correto."""
        assert TOOL_PROCESSAR_BRIEFING["name"] == "processar_briefing"

    def test_tool_has_description(self):
        """Tool tem descricao."""
        assert "description" in TOOL_PROCESSAR_BRIEFING
        assert len(TOOL_PROCESSAR_BRIEFING["description"]) > 50

    def test_tool_has_input_schema(self):
        """Tool tem schema de input."""
        assert "input_schema" in TOOL_PROCESSAR_BRIEFING
        assert TOOL_PROCESSAR_BRIEFING["input_schema"]["type"] == "object"

    def test_tool_no_required_params(self):
        """Tool nao tem parametros obrigatorios."""
        schema = TOOL_PROCESSAR_BRIEFING["input_schema"]
        assert schema.get("required", []) == []

    def test_tool_has_expected_properties(self):
        """Tool tem propriedades esperadas."""
        props = TOOL_PROCESSAR_BRIEFING["input_schema"]["properties"]
        assert "nome_documento" in props
        assert "acao" in props

    def test_acao_enum_values(self):
        """Acao tem valores enum corretos."""
        props = TOOL_PROCESSAR_BRIEFING["input_schema"]["properties"]
        acao_enum = props["acao"]["enum"]
        assert "listar" in acao_enum
        assert "ler" in acao_enum
        assert "analisar" in acao_enum


class TestListarBriefings:
    """Testes da funcao _listar_briefings."""

    @pytest.mark.asyncio
    async def test_listar_vazio(self):
        """Lista vazia retorna mensagem apropriada."""
        with patch("app.tools.slack.briefing.listar_documentos", new_callable=AsyncMock) as mock:
            mock.return_value = []

            resultado = await _listar_briefings()

            assert resultado["success"] is True
            assert resultado["documentos"] == []
            assert "nenhum" in resultado["mensagem"].lower()

    @pytest.mark.asyncio
    async def test_listar_com_docs(self):
        """Lista com documentos retorna informacoes corretas."""
        docs = [
            DocInfo(
                id="doc1",
                nome="campanha-sao-luiz",
                ultima_modificacao=datetime(2025, 12, 15, 14, 30),
                url="https://docs.google.com/document/d/doc1"
            ),
            DocInfo(
                id="doc2",
                nome="mapeamento-bh",
                ultima_modificacao=datetime(2025, 12, 14, 10, 0),
                url="https://docs.google.com/document/d/doc2"
            ),
        ]

        with patch("app.tools.slack.briefing.listar_documentos", new_callable=AsyncMock) as mock:
            mock.return_value = docs

            resultado = await _listar_briefings()

            assert resultado["success"] is True
            assert resultado["total"] == 2
            assert len(resultado["documentos"]) == 2
            assert resultado["documentos"][0]["nome"] == "campanha-sao-luiz"
            assert resultado["documentos"][1]["nome"] == "mapeamento-bh"


class TestHandlerComNome:
    """Testes do handler com nome de documento."""

    @pytest.mark.asyncio
    async def test_sem_nome_lista_docs(self):
        """Sem nome de documento, lista briefings disponiveis."""
        with patch("app.tools.slack.briefing.listar_documentos", new_callable=AsyncMock) as mock:
            mock.return_value = []

            resultado = await handle_processar_briefing({})

            assert resultado["success"] is True
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_acao_listar_explicita(self):
        """Acao listar explicita funciona."""
        with patch("app.tools.slack.briefing.listar_documentos", new_callable=AsyncMock) as mock:
            mock.return_value = []

            resultado = await handle_processar_briefing({"acao": "listar"})

            assert resultado["success"] is True
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_nome_sem_match(self):
        """Nome sem match retorna documentos disponiveis."""
        docs = [
            DocInfo(
                id="doc1",
                nome="campanha-sao-luiz",
                ultima_modificacao=datetime.now(),
                url="https://..."
            ),
        ]

        with patch("app.tools.slack.briefing.buscar_documento_por_nome", new_callable=AsyncMock) as mock_busca:
            with patch("app.tools.slack.briefing.listar_documentos", new_callable=AsyncMock) as mock_lista:
                mock_busca.return_value = []
                mock_lista.return_value = docs

                resultado = await handle_processar_briefing({"nome_documento": "inexistente"})

                assert resultado["success"] is False
                assert "nao encontrei" in resultado["error"].lower()
                assert "campanha-sao-luiz" in resultado["documentos_disponiveis"]

    @pytest.mark.asyncio
    async def test_multiplos_matches(self):
        """Multiplos matches pede confirmacao."""
        docs = [
            DocInfo(id="doc1", nome="campanha-sao-luiz-dez", ultima_modificacao=datetime.now(), url="..."),
            DocInfo(id="doc2", nome="campanha-sao-luiz-nov", ultima_modificacao=datetime.now(), url="..."),
        ]

        with patch("app.tools.slack.briefing.buscar_documento_por_nome", new_callable=AsyncMock) as mock:
            mock.return_value = docs

            resultado = await handle_processar_briefing({"nome_documento": "sao-luiz"})

            assert resultado["success"] is False
            assert resultado["multiplos_matches"] is True
            assert len(resultado["matches"]) == 2


class TestLerBriefing:
    """Testes da funcao _ler_briefing."""

    @pytest.mark.asyncio
    async def test_ler_documento(self):
        """Le documento corretamente."""
        doc_info = DocInfo(
            id="doc1",
            nome="campanha-teste",
            ultima_modificacao=datetime(2025, 12, 15, 14, 30),
            url="https://..."
        )
        doc_content = DocContent(
            info=doc_info,
            conteudo="Conteudo do briefing...",
            hash="abc123",
            ja_processado=False,
            secao_plano_existente=None
        )

        with patch("app.tools.slack.briefing.ler_documento", new_callable=AsyncMock) as mock:
            mock.return_value = doc_content

            resultado = await _ler_briefing(doc_info)

            assert resultado["success"] is True
            assert resultado["acao"] == "ler"
            assert resultado["documento"]["nome"] == "campanha-teste"
            assert resultado["conteudo"] == "Conteudo do briefing..."
            assert resultado["documento"]["ja_processado"] is False

    @pytest.mark.asyncio
    async def test_ler_documento_ja_processado(self):
        """Le documento que ja foi processado."""
        doc_info = DocInfo(
            id="doc1",
            nome="campanha-teste",
            ultima_modificacao=datetime(2025, 12, 15, 14, 30),
            url="https://..."
        )
        doc_content = DocContent(
            info=doc_info,
            conteudo="Conteudo...\n## Plano da Julia\n...",
            hash="abc123",
            ja_processado=True,
            secao_plano_existente="## Plano da Julia\n..."
        )

        with patch("app.tools.slack.briefing.ler_documento", new_callable=AsyncMock) as mock:
            mock.return_value = doc_content

            resultado = await _ler_briefing(doc_info)

            assert resultado["success"] is True
            assert resultado["documento"]["ja_processado"] is True
            assert "ja tem um plano" in resultado["mensagem"].lower()

    @pytest.mark.asyncio
    async def test_ler_documento_erro(self):
        """Erro ao ler documento retorna erro."""
        doc_info = DocInfo(
            id="doc1",
            nome="campanha-teste",
            ultima_modificacao=datetime.now(),
            url="https://..."
        )

        with patch("app.tools.slack.briefing.ler_documento", new_callable=AsyncMock) as mock:
            mock.return_value = None

            resultado = await _ler_briefing(doc_info)

            assert resultado["success"] is False
            assert "erro" in resultado["error"].lower()


class TestIniciarAnalise:
    """Testes da funcao _iniciar_analise_briefing."""

    @pytest.mark.asyncio
    async def test_documento_muito_grande(self):
        """Documento muito grande retorna erro."""
        doc_info = DocInfo(
            id="doc1",
            nome="briefing-gigante",
            ultima_modificacao=datetime.now(),
            url="https://..."
        )
        doc_content = DocContent(
            info=doc_info,
            conteudo="x" * 20000,  # 20k caracteres
            hash="abc",
            ja_processado=False
        )

        with patch("app.tools.slack.briefing.ler_documento", new_callable=AsyncMock) as mock:
            mock.return_value = doc_content

            from app.tools.slack.briefing import _iniciar_analise_briefing
            resultado = await _iniciar_analise_briefing(doc_info)

            assert resultado["success"] is False
            assert "grande" in resultado["error"].lower()

    @pytest.mark.asyncio
    async def test_documento_vazio(self):
        """Documento vazio retorna erro."""
        doc_info = DocInfo(
            id="doc1",
            nome="briefing-vazio",
            ultima_modificacao=datetime.now(),
            url="https://..."
        )
        doc_content = DocContent(
            info=doc_info,
            conteudo="   ",  # Praticamente vazio
            hash="abc",
            ja_processado=False
        )

        with patch("app.tools.slack.briefing.ler_documento", new_callable=AsyncMock) as mock:
            mock.return_value = doc_content

            from app.tools.slack.briefing import _iniciar_analise_briefing
            resultado = await _iniciar_analise_briefing(doc_info)

            assert resultado["success"] is False
            assert "vazio" in resultado["error"].lower()

    @pytest.mark.asyncio
    async def test_documento_ja_processado(self):
        """Documento ja processado pergunta se quer refazer."""
        doc_info = DocInfo(
            id="doc1",
            nome="briefing-teste",
            ultima_modificacao=datetime.now(),
            url="https://..."
        )
        doc_content = DocContent(
            info=doc_info,
            conteudo="Conteudo do briefing\n## Plano da Julia\nPlano existente...",
            hash="abc",
            ja_processado=True,
            secao_plano_existente="## Plano da Julia\nPlano existente..."
        )

        with patch("app.tools.slack.briefing.ler_documento", new_callable=AsyncMock) as mock:
            mock.return_value = doc_content

            from app.tools.slack.briefing import _iniciar_analise_briefing
            resultado = await _iniciar_analise_briefing(doc_info)

            assert resultado["success"] is True
            assert resultado["acao"] == "ja_processado"
            assert "nova analise" in resultado["mensagem"].lower()
